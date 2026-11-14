import copy
import json
import math
import uuid
from functools import wraps
from zipfile import BadZipFile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from openpyxl.utils.exceptions import InvalidFileException
from health.models import DatasetLock
from .access import ScopeDenied, access_for, require_scope
from .audit import record, verify
from .engine import replay
from .ingestion import import_workbook, positive_int
from .models import AlertAction, Assessment, Astronaut, AuditEntry, Exposure, Finding, ImportReport, MissionCheckIn, Observation, RuleVersion, TriageProtocol
from .rules import GLYPHS, INDICATORS, LEVEL_ORDER
from .workflows import display_level, latest_override, NON_URGENT, packet as queue_packet


def mission_view(function):
    @login_required
    @never_cache
    @wraps(function)
    def wrapped(request, *args, **kwargs):
        try:
            return function(request, *args, **kwargs)
        except ScopeDenied:
            if request.path.endswith(("/action/", "/check-in/")):
                return JsonResponse({"error": "Your account does not have access to this astronaut or action."}, status=403)
            return render(request, "meridian/denied.html", status=403)
        except Astronaut.DoesNotExist:
            raise Http404
    return wrapped


def active_rule():
    return RuleVersion.objects.order_by("-created_at").first()


def overview_payload(user, astronaut_id, day=None, days=30, excluded=False):
    astronaut = require_scope(user, astronaut_id)
    rule = active_rule()
    latest_day = Observation.objects.filter(astronaut=astronaut).aggregate(day=Max("mission_day"))["day"] or 1
    day = min(day or latest_day, latest_day)
    assessment = Assessment.objects.filter(astronaut=astronaut, mission_day=day, rule=rule).first()
    start = max(1, day - days + 1)
    rows = Observation.objects.filter(astronaut=astronaut, mission_day__range=(start, day))
    excluded_count = rows.filter(accepted=False).count()
    if not excluded:
        rows = rows.filter(accepted=True)
    observations = list(rows.values("id", "mission_day", "indicator_code", "value", "unit", "accepted", "exclusion_reason", "source_type"))
    prompts = list(Observation.objects.filter(astronaut=astronaut, mission_day=day, accepted=False).values("id", "indicator_code", "value", "exclusion_reason"))
    exposures = list(Exposure.objects.filter(Q(scope="crew") | Q(scope=astronaut_id), start_day__lte=day, end_day__gte=start).values())
    findings = []
    domains = copy.deepcopy(assessment.domains) if assessment else []
    for item in Finding.objects.filter(astronaut=astronaut, mission_day=day, rule=rule).prefetch_related("overrides"):
        override = latest_override(item)
        displayed = display_level(item)
        details = copy.deepcopy(item.details)
        details["glyph"] = GLYPHS[displayed]
        entry = {"id": item.pk, "domain": item.domain, "level": displayed, "assessed_level": item.level, "status": item.status, "mission_day": item.mission_day, "details": details,
                 "override": {"reason": override.reason, "actor": override.actor_id, "at": override.created_at.isoformat()} if override else None}
        findings.append(entry)
        if override:
            for domain in domains:
                if domain["domain"] == item.domain:
                    domain.update(level=displayed, assessed_level=item.level, glyph=GLYPHS[displayed], override=entry["override"])
    access = access_for(user)
    return {"owner": user.pk, "astronaut": {"id": astronaut.pk, "display_name": astronaut.display_name}, "day": day, "latest_day": latest_day,
            "days": days, "domains": domains, "observations": observations,
            "exposures": exposures, "findings": findings, "quality_prompts": prompts, "excluded_count": excluded_count,
            "rule": rule.pk if rule else None, "placeholder": True, "origin": "SYNTHETIC", "can_write": user.is_superuser or (access and access.role in {"astronaut", "medical_officer"}),
            "limitations": "Demonstration rules only. No validated urgent protocol or clinical predictions. Environmental magnitudes are placeholders."}


@mission_view
def home(request):
    access = access_for(request.user)
    if access and access.role == "astronaut":
        return redirect("mission_overview", astronaut_id=access.astronaut_id)
    if access and access.role == "scientist":
        return redirect("mission_aggregate")
    if access and access.role == "rule_administrator":
        return redirect("mission_rules")
    if request.user.is_superuser or (access and access.role in {"medical_officer", "flight_surgeon"}):
        crew = []
        latest_day = Observation.objects.aggregate(day=Max("mission_day"))["day"] or 1
        try:
            selected_day = min(positive_int(request.GET.get("day", latest_day)), latest_day)
        except (ValueError, TypeError, OverflowError) as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        rule = active_rule()
        for astronaut in Astronaut.objects.all():
            assessment = Assessment.objects.filter(astronaut=astronaut, rule=rule, mission_day=selected_day).first()
            domains = copy.deepcopy(assessment.domains) if assessment else []
            if assessment:
                for item in Finding.objects.filter(astronaut=astronaut, mission_day=assessment.mission_day, rule=rule).prefetch_related("overrides"):
                    for domain in domains:
                        if domain["domain"] == item.domain:
                            domain["level"] = display_level(item)
            level = min((domain["level"] for domain in domains), key=lambda value: LEVEL_ORDER[value], default="UNKNOWN")
            crew.append({"astronaut": astronaut, "level": level, "day": assessment.mission_day if assessment else None,
                         "findings": Finding.objects.filter(astronaut=astronaut, mission_day=selected_day, rule=rule, status__in=["open", "acknowledged", "escalated"]).count(),
                         "data_status": "Partial" if any(d["level"] == "UNKNOWN" for d in domains) else "Full" if domains else "Unknown"})
        crew.sort(key=lambda item: LEVEL_ORDER[item["level"]])
        return render(request, "meridian/crew.html", {"crew": crew, "selected_day": selected_day, "latest_day": latest_day, "mission_access": access, "import_report": ImportReport.objects.order_by("-pk").first()})
    return render(request, "meridian/denied.html", status=403)


@mission_view
@ensure_csrf_cookie
def overview(request, astronaut_id):
    try:
        day = positive_int(request.GET["day"]) if "day" in request.GET else None
        days = int(request.GET.get("days", 30))
        if days not in (7, 14, 30):
            raise ValueError("Choose 7, 14, or 30 days.")
        payload = overview_payload(request.user, astronaut_id, day, days, request.GET.get("excluded") == "1")
    except (ValueError, OverflowError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    if request.GET.get("format") == "json":
        return JsonResponse(payload)
    return render(request, "meridian/overview.html", {"snapshot": payload, "astronaut": payload["astronaut"], "mission_access": access_for(request.user)})


@mission_view
def finding(request, pk):
    item = get_object_or_404(Finding, pk=pk)
    require_scope(request.user, item.astronaut_id)
    access = access_for(request.user)
    details = copy.deepcopy(item.details)
    details["glyph"] = GLYPHS[display_level(item)]
    return render(request, "meridian/finding.html", {"finding": item, "details": details,
        "can_write": request.user.is_superuser or (access and access.role in {"astronaut", "medical_officer"}),
        "can_override": request.user.is_superuser or (access and access.role == "medical_officer"),
        "displayed_level": display_level(item), "overrides": item.overrides.select_related("actor"), "override_levels": NON_URGENT, "client_id": str(uuid.uuid4())})


@mission_view
@require_POST
def finding_action(request, pk):
    item = get_object_or_404(Finding, pk=pk)
    require_scope(request.user, item.astronaut_id, write=True)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("Action must be an object.")
        action = payload.get("action")
        reason = str(payload.get("reason", "")).strip()
        key = uuid.UUID(str(payload.get("client_id")))
        if action not in {"acknowledge", "dismiss", "escalate"}:
            raise ValueError("Unsupported action.")
        if action == "dismiss" and not reason:
            raise ValueError("A dismissal reason is required.")
        if len(reason) > 2000:
            raise ValueError("Reason must be 2000 characters or fewer.")
        with transaction.atomic():
            DatasetLock.objects.select_for_update().get(pk=1)
            existing = AlertAction.objects.filter(client_id=key).first()
            if existing:
                if existing.actor_id != request.user.pk or existing.finding_id != item.pk or existing.action != action or existing.reason != reason:
                    raise ValueError("This action identifier belongs to different content.")
                return JsonResponse({"ok": True, "created": False})
            saved_action = AlertAction.objects.create(client_id=key, finding=item, actor=request.user, action=action, reason=reason)
            item.status = {"acknowledge": "acknowledged", "dismiss": "dismissed", "escalate": "escalated"}[action]
            item.save(update_fields=["status"])
            record(request.user.pk, f"alert_{action}", item.astronaut_id, {"finding": item.pk, "reason": reason, "original_level": item.level, "client_id": str(key)})
            queue_packet("finding_action", item.astronaut_id, saved_action.pk, {"finding_id": item.pk, "action": action, "reason": reason, "assessed_level": item.level, "displayed_level": display_level(item), "actor": request.user.pk}, 1 if action == "escalate" else 3)
        return JsonResponse({"ok": True, "created": True, "status": item.status})
    except (ValueError, TypeError, AttributeError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@mission_view
@require_POST
def check_in(request, astronaut_id):
    astronaut = require_scope(request.user, astronaut_id, write=True)
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("Check-in must be an object.")
        key = uuid.UUID(str(payload.get("client_id")))
        day = positive_int(payload.get("mission_day"))
        values = {}
        for code in ("sleep_quality", "fatigue_score", "mood_score", "workload_score"):
            value = float(payload.get(code))
            if not math.isfinite(value) or value % 1 or not 1 <= value <= 5:
                raise ValueError("Self-report scores must be whole numbers from 1 to 5.")
            values[code] = value
        for code in ("resting_hr", "sleep_hours"):
            value = payload.get(code)
            if value not in (None, ""):
                value = float(value)
                low, high = INDICATORS[code]["range"]
                if not math.isfinite(value) or not low <= value <= high:
                    raise ValueError(f"{INDICATORS[code]['label']} is outside the placeholder plausibility range.")
                values[code] = value
        symptoms = str(payload.get("symptoms", "")).strip()
        if len(symptoms) > 2000:
            raise ValueError("Symptoms note must be 2000 characters or fewer.")
        values["symptoms"] = symptoms
        with transaction.atomic():
            DatasetLock.objects.select_for_update().get(pk=1)
            existing = MissionCheckIn.objects.filter(client_id=key).first()
            if existing:
                if existing.actor_id != request.user.pk or existing.astronaut_id != astronaut_id or existing.mission_day != day or existing.values != values:
                    raise ValueError("This check-in identifier belongs to different content.")
                return JsonResponse({"ok": True, "created": False})
            latest = Observation.objects.filter(astronaut=astronaut).aggregate(day=Max("mission_day"))["day"] or 0
            if day <= latest:
                raise ValueError(f"Record a new mission day after {latest}; historical observations are preserved.")
            MissionCheckIn.objects.create(client_id=key, astronaut=astronaut, actor=request.user, mission_day=day, values=values)
            for code, value in values.items():
                if code == "symptoms":
                    continue
                Observation.objects.create(id=f"checkin-{key}-{code}", astronaut=astronaut, mission_day=day, indicator_code=code,
                    value=value, unit=INDICATORS[code]["unit"], source_type="manual_self_report", entered_by=request.user)
            record(request.user.pk, "checkin_saved", astronaut_id, {"client_id": str(key), "day": day, "observed_indicators": [code for code in values if code != "symptoms"]})
            replay()
            queue_packet("observations", astronaut_id, str(key), {"day": day, "values": values, "actor": request.user.pk}, 2)
        return JsonResponse({"ok": True, "created": True, "day": day})
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@mission_view
def alerts(request, astronaut_id):
    astronaut = require_scope(request.user, astronaut_id)
    status = request.GET.get("status", "open")
    items = Finding.objects.filter(astronaut=astronaut, rule=active_rule()).prefetch_related("overrides")
    if status in {"open", "acknowledged", "dismissed", "resolved", "escalated"}:
        items = items.filter(status=status)
    items = list(items)
    for item in items:
        item.displayed_level = display_level(item)
    if request.GET.get("level") in LEVEL_ORDER:
        items = [item for item in items if item.displayed_level == request.GET["level"]]
    items.sort(key=lambda item: (LEVEL_ORDER[item.displayed_level], -item.mission_day))
    return render(request, "meridian/alerts.html", {"astronaut": astronaut, "findings": items, "status": status})


@mission_view
def import_data(request):
    require_scope(request.user, roles=["rule_administrator"])
    if request.method == "POST":
        upload = request.FILES.get("dataset")
        try:
            if not upload:
                raise ValueError("Choose the Meridian .xlsx workbook.")
            report = import_workbook(upload, request.user.pk)
            new_findings = replay()
        except (ValueError, OSError, BadZipFile, InvalidFileException) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Imported workbook. Created {new_findings} new findings. Review the load report below.")
        return redirect("mission_import")
    return render(request, "meridian/import.html", {"report": ImportReport.objects.order_by("-pk").first()})


@mission_view
def audit(request):
    require_scope(request.user, roles=["medical_officer", "rule_administrator"])
    result = None
    if request.method == "POST":
        result = verify()
        record(request.user.pk, "audit_verification", payload=result)
    entries = AuditEntry.objects.order_by("-pk")
    if request.GET.get("astronaut"):
        entries = entries.filter(scope=request.GET["astronaut"])
    if request.GET.get("action"):
        entries = entries.filter(action=request.GET["action"])
    return render(request, "meridian/audit.html", {"entries": entries[:200], "verification": result})


@mission_view
def rules(request):
    require_scope(request.user, roles=["medical_officer", "rule_administrator"])
    return render(request, "meridian/rules.html", {"rules": RuleVersion.objects.order_by("-created_at"), "protocols": TriageProtocol.objects.all()})


@mission_view
def aggregate(request):
    require_scope(request.user, roles=["scientist"])
    # Only crew-level summaries; no astronaut IDs, names, individual rows or daily values.
    from django.db.models import Avg, Count
    totals = list(Observation.objects.filter(accepted=True).values("indicator_code", "unit").annotate(mean=Avg("value"), samples=Count("pk")))
    return render(request, "meridian/aggregate.html", {"totals": totals})


def offline(request):
    return render(request, "meridian/offline.html", {"offline_shell": True})


@login_required
@never_cache
def session_identity(request):
    return JsonResponse({"owner": request.user.pk})
