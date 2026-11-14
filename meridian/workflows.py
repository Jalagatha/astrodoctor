import uuid

from django.db import transaction
from django.utils import timezone
from health.models import DatasetLock
from .access import require_scope
from .audit import record
from .models import (Finding, FindingOverride, GroundPacket, GroundGuidance, GuidanceRead, GroundLinkState,
                     TriageProtocol, TriageSession, TriageAnswer)
from .protocols import protocol_hash

NON_URGENT = ("NORMAL", "OBSERVE", "ATTENTION", "UNKNOWN")


def client_key(value):
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("A valid request identifier is required. Reload the form and try again.") from exc


def required_text(value, limit, label):
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > limit:
        raise ValueError(f"{label} is required and must be at most {limit} characters.")
    return value.strip()


def latest_override(finding):
    if finding.level == "URGENT":
        return None
    return next(iter(finding.overrides.all()), None)


def display_level(finding):
    override = latest_override(finding)
    return override.displayed_level if override else finding.level


def packet(kind, astronaut_id, identifier, payload, priority=2):
    key = uuid.uuid5(uuid.NAMESPACE_URL, f"meridian:{kind}:{identifier}")
    item, created = GroundPacket.objects.get_or_create(client_id=key, defaults={"astronaut_id": astronaut_id, "kind": kind, "payload": payload, "priority": priority})
    if created:
        record("outbox", "ground_packet_queued", astronaut_id, {"packet": item.pk, "kind": kind, "key": str(key), "priority": priority})
    return item


def queue_finding(finding):
    return packet("finding", finding.astronaut_id, f"{finding.pk}:{finding.rule_id}", {
        "finding_id": finding.pk, "mission_day": finding.mission_day, "domain": finding.domain,
        "assessed_level": finding.level, "rule_version": finding.rule_id, "details": finding.details,
    }, 0 if finding.level == "URGENT" else 1 if finding.level == "ATTENTION" else 3)


def save_override(user, finding_id, key, level, reason):
    key = client_key(key)
    reason = required_text(reason, 2000, "Override reason")
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        finding = Finding.objects.get(pk=finding_id)
        require_scope(user, finding.astronaut_id, roles=["medical_officer"])
        if finding.level == "URGENT":
            record(user.pk, "urgent_override_refused", finding.astronaut_id, {"finding": finding.pk})
            # Audit is preserved by returning the error after the transaction commits.
            refused = True
        else:
            refused = False
            if level not in NON_URGENT:
                raise ValueError("Choose a non-URGENT displayed level.")
            existing = FindingOverride.objects.filter(client_id=key).first()
            if existing:
                if (existing.actor_id, existing.finding_id, existing.displayed_level, existing.reason) != (user.pk, finding.pk, level, reason):
                    raise ValueError("Request identifier conflicts with an existing override.")
                return existing
            result = FindingOverride.objects.create(client_id=key, finding=finding, actor=user, original_level=finding.level,
                previous_display_level=display_level(finding), displayed_level=level, reason=reason)
            record(user.pk, "finding_override", finding.astronaut_id, {"override": result.pk, "finding": finding.pk, "assessed": finding.level, "previous_display": result.previous_display_level, "displayed": level, "reason": reason})
            packet("override", finding.astronaut_id, result.pk, {"finding_id": finding.pk, "assessed_level": finding.level, "previous_display_level": result.previous_display_level, "displayed_level": level, "reason": reason, "actor": user.pk}, 1 if level == "ATTENTION" else 3)
    if refused:
        raise ValueError("URGENT alerts follow the emergency protocol and cannot be overridden.")
    return result


def usable_protocol(protocol):
    if protocol.content_hash != protocol_hash(protocol.definition):
        raise ValueError("Protocol integrity check failed. The session cannot continue.")
    if not protocol.demonstration and not (protocol.approved_by and protocol.approval_reference):
        raise ValueError("The protocol has no recorded approval reference.")


def start_triage(user, finding_id, protocol_id, key):
    key = client_key(key)
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        finding = Finding.objects.get(pk=finding_id)
        require_scope(user, finding.astronaut_id, write=True)
        protocol = TriageProtocol.objects.get(pk=protocol_id)
        usable_protocol(protocol)
        if protocol.demonstration and finding.astronaut.origin_label != "SYNTHETIC":
            raise ValueError("The demonstration checklist is only available for synthetic data.")
        existing = TriageSession.objects.filter(client_id=key).first()
        if existing:
            if (existing.started_by_id, existing.finding_id, existing.protocol_id) != (user.pk, finding.pk, protocol.pk):
                raise ValueError("Request identifier conflicts with an existing triage session.")
            return existing
        session = TriageSession.objects.create(client_id=key, finding=finding, protocol=protocol, started_by=user, current_question=protocol.definition["questions"][0]["code"])
        record(user.pk, "triage_started", finding.astronaut_id, {"session": session.pk, "finding": finding.pk, "protocol": protocol.pk, "protocol_hash": protocol.content_hash, "demonstration": protocol.demonstration})
        return session


def answer_triage(user, session_id, key, question_code, answer_value):
    key = client_key(key)
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        session = TriageSession.objects.select_related("finding", "protocol").get(pk=session_id)
        require_scope(user, session.finding.astronaut_id, write=True)
        usable_protocol(session.protocol)
        existing = TriageAnswer.objects.filter(client_id=key).first()
        if existing:
            if (existing.actor_id, existing.session_id, existing.question_code, existing.answer_value) != (user.pk, session.pk, question_code, answer_value):
                raise ValueError("Request identifier conflicts with an existing answer.")
            return session
        if session.status != "active" or not session.current_question or session.current_question != question_code:
            raise ValueError("This question is no longer active. Reload the session to continue.")
        question = next(q for q in session.protocol.definition["questions"] if q["code"] == question_code)
        option = next((o for o in question["options"] if o["value"] == answer_value), None)
        if not option:
            raise ValueError("Choose one of the protocol's answer options.")
        answer = TriageAnswer.objects.create(client_id=key, session=session, actor=user, question_code=question_code,
            question_text=question["prompt"], answer_value=answer_value, answer_label=option["label"], urgent=option.get("urgent", False))
        session.current_question = option.get("next") or ""
        if answer.urgent and not session.urgent_at:
            session.urgent_at = timezone.now()
        session.save(update_fields=["current_question", "urgent_at"])
        record(user.pk, "triage_answer", session.finding.astronaut_id, {"session": session.pk, "answer": answer.pk, "question": question_code, "value": answer_value, "urgent": answer.urgent})
        if answer.urgent:
            packet("triage_urgent", session.finding.astronaut_id, answer.pk, {"session_id": session.pk, "protocol": session.protocol_id, "question": question_code, "answer": option["label"], "urgent_at": session.urgent_at.isoformat()}, 0)
        return session


def transition_triage(user, session_id, action):
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        session = TriageSession.objects.select_related("finding", "protocol").get(pk=session_id)
        require_scope(user, session.finding.astronaut_id, write=True)
        usable_protocol(session.protocol)
        if action == "finish":
            if session.status == "completed":
                return session
            if session.status != "active" or session.current_question:
                raise ValueError("Complete the active questions before finishing the session.")
            session.status = "completed"
            session.completed_at = timezone.now()
            packet("triage_summary", session.finding.astronaut_id, session.pk, {
                "session_id": session.pk, "finding_id": session.finding_id, "protocol": session.protocol_id,
                "protocol_hash": session.protocol.content_hash, "demonstration": session.protocol.demonstration,
                "assessed_level": session.finding.level, "displayed_level": display_level(session.finding),
                "urgent": bool(session.urgent_at), "completed_at": session.completed_at.isoformat(),
                "answers": [{"question": a.question_text, "answer": a.answer_label, "actor": a.actor_id, "at": a.created_at.isoformat()} for a in session.answers.all()],
            }, 0 if session.urgent_at else 2)
        elif action == "pause" and session.status == "active":
            session.status = "paused"
        elif action == "resume" and session.status == "paused":
            session.status = "active"
        else:
            raise ValueError("This session cannot make that transition.")
        session.save(update_fields=["status", "completed_at"])
        record(user.pk, f"triage_{action}", session.finding.astronaut_id, {"session": session.pk, "protocol": session.protocol_id})
        return session


def set_ground_link(user, available):
    require_scope(user, roles=["medical_officer"])
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        link, _ = GroundLinkState.objects.get_or_create(pk=1)
        link.available = available
        link.save(update_fields=["available"])
        record(user.pk, "simulated_ground_link", payload={"available": available})


def deliver_ground(user):
    require_scope(user, roles=["medical_officer"])
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        link, _ = GroundLinkState.objects.get_or_create(pk=1)
        if not link.available:
            raise ValueError("The simulated ground link is offline. Packets remain queued.")
        pending = list(GroundPacket.objects.filter(delivered_at__isnull=True).order_by("priority", "id"))
        for item in pending:
            item.delivered_at = timezone.now()
            item.save(update_fields=["delivered_at"])
            record(user.pk, "ground_packet_delivered", item.astronaut_id, {"packet": item.pk, "key": str(item.client_id), "priority": item.priority, "transport": "local simulation"})
        if pending:
            link.last_sync_at = timezone.now()
            link.save(update_fields=["last_sync_at"])
        return len(pending)


def send_guidance(user, packet_id, key, text):
    key = client_key(key)
    text = required_text(text, 4000, "Guidance")
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        item = GroundPacket.objects.get(pk=packet_id)
        require_scope(user, item.astronaut_id, roles=["flight_surgeon"])
        link = GroundLinkState.objects.filter(pk=1, available=True).first()
        if not link or not item.delivered_at:
            raise ValueError("Guidance requires an available simulated link and a delivered summary.")
        existing = GroundGuidance.objects.filter(client_id=key).first()
        if existing:
            if (existing.author_id, existing.packet_id, existing.text) != (user.pk, item.pk, text):
                raise ValueError("Request identifier conflicts with existing guidance.")
            return existing
        result = GroundGuidance.objects.create(client_id=key, packet=item, author=user, text=text)
        record(user.pk, "ground_guidance", item.astronaut_id, {"guidance": result.pk, "packet": item.pk, "text": text})
        return result


def read_guidance(user, guidance_id):
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        item = GroundGuidance.objects.select_related("packet").get(pk=guidance_id)
        require_scope(user, item.packet.astronaut_id, write=True)
        receipt, created = GuidanceRead.objects.get_or_create(guidance=item, actor=user)
        if created:
            record(user.pk, "guidance_read", item.packet.astronaut_id, {"guidance": item.pk})
        return receipt
