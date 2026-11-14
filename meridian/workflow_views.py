import uuid

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .access import access_for, require_scope
from .models import Finding, GroundGuidance, GroundLinkState, GroundPacket, TriageProtocol, TriageSession
from .views import mission_view
from .workflows import (NON_URGENT, answer_triage, deliver_ground, display_level, read_guidance, save_override,
                        send_guidance, set_ground_link, start_triage, transition_triage, usable_protocol)


def can_write(user):
    access = access_for(user)
    return user.is_superuser or bool(access and access.role in {"astronaut", "medical_officer"})


@mission_view
@require_POST
def override(request, pk):
    item = get_object_or_404(Finding, pk=pk)
    require_scope(request.user, item.astronaut_id, roles=["medical_officer"])
    try:
        save_override(request.user, pk, request.POST.get("client_id"), request.POST.get("level"), request.POST.get("reason"))
    except ValueError as exc:
        messages.error(request, str(exc))
        return render(request, "meridian/override_error.html", {"finding": item, "reason": request.POST.get("reason", ""), "client_id": request.POST.get("client_id", str(uuid.uuid4())), "levels": NON_URGENT}, status=400)
    messages.success(request, "Displayed level updated. The original assessment and override history are preserved.")
    return redirect("mission_finding", pk=pk)


@mission_view
def triage_list(request):
    require_scope(request.user, roles=["astronaut", "medical_officer", "flight_surgeon"])
    access = access_for(request.user)
    sessions = TriageSession.objects.select_related("finding__astronaut", "protocol")
    if access and access.role == "astronaut" and not request.user.is_superuser:
        sessions = sessions.filter(finding__astronaut_id=access.astronaut_id)
    return render(request, "meridian/triage_list.html", {"sessions": sessions})


@mission_view
def triage_start(request, pk):
    item = get_object_or_404(Finding, pk=pk)
    require_scope(request.user, item.astronaut_id, write=True)
    protocols = TriageProtocol.objects.all()
    error = None
    if request.method == "POST":
        protocol = get_object_or_404(TriageProtocol, pk=request.POST.get("protocol", ""))
        try:
            session = start_triage(request.user, pk, protocol.pk, request.POST.get("client_id"))
        except ValueError as exc:
            error = str(exc)
        else:
            return redirect("mission_triage_session", pk=session.pk)
    return render(request, "meridian/triage_start.html", {"finding": item, "protocols": protocols, "client_id": str(uuid.uuid4()), "error": error}, status=400 if error else 200)


@mission_view
def triage_session(request, pk):
    session = get_object_or_404(TriageSession.objects.select_related("finding__astronaut", "protocol"), pk=pk)
    require_scope(request.user, session.finding.astronaut_id)
    error = None
    integrity_error = None
    try:
        usable_protocol(session.protocol)
    except ValueError as exc:
        integrity_error = str(exc)
    if request.method == "POST":
        require_scope(request.user, session.finding.astronaut_id, write=True)
        try:
            if request.POST.get("action") == "answer":
                answer_triage(request.user, pk, request.POST.get("client_id"), request.POST.get("question"), request.POST.get("answer"))
            else:
                transition_triage(request.user, pk, request.POST.get("action"))
        except ValueError as exc:
            error = str(exc)
        else:
            return redirect("mission_triage_session", pk=pk)
    question = next((q for q in session.protocol.definition["questions"] if q["code"] == session.current_question), None) if not integrity_error else None
    return render(request, "meridian/triage_session.html", {"session": session, "question": question, "answers": session.answers.select_related("actor"),
        "step": session.answers.count() + 1, "client_id": str(uuid.uuid4()), "can_write": can_write(request.user), "error": error,
        "integrity_error": integrity_error, "displayed_level": display_level(session.finding)}, status=400 if error else 200)


@mission_view
def ground(request):
    require_scope(request.user, roles=["medical_officer", "flight_surgeon"])
    access = access_for(request.user)
    medical = request.user.is_superuser or (access and access.role == "medical_officer")
    error = None
    if request.method == "POST":
        require_scope(request.user, roles=["medical_officer"])
        try:
            if request.POST.get("action") == "link":
                set_ground_link(request.user, request.POST.get("available") == "on")
                messages.success(request, "Simulated ground link updated.")
            elif request.POST.get("action") == "send":
                count = deliver_ground(request.user)
                messages.success(request, f"Delivered {count} packets to the local ground inbox.")
            else:
                raise ValueError("Choose a supported ground-link action.")
        except ValueError as exc:
            error = str(exc)
        else:
            return redirect("mission_ground")
    packets = GroundPacket.objects.select_related("astronaut")
    if not medical:
        packets = packets.filter(delivered_at__isnull=False)
    link = GroundLinkState.objects.filter(pk=1).first()
    return render(request, "meridian/ground.html", {"packets": packets[:200], "pending_count": GroundPacket.objects.filter(delivered_at__isnull=True).count() if medical else None,
        "link": link, "medical": medical, "error": error}, status=400 if error else 200)


@mission_view
def ground_packet(request, pk):
    item = get_object_or_404(GroundPacket.objects.select_related("astronaut"), pk=pk)
    require_scope(request.user, item.astronaut_id, roles=["medical_officer", "flight_surgeon"])
    access = access_for(request.user)
    ground_role = request.user.is_superuser or (access and access.role == "flight_surgeon")
    if access and access.role == "flight_surgeon" and not item.delivered_at and not request.user.is_superuser:
        # Pending packets have not reached the ground role.
        from django.http import Http404
        raise Http404
    error = None
    if request.method == "POST":
        require_scope(request.user, item.astronaut_id, roles=["flight_surgeon"])
        try:
            send_guidance(request.user, pk, request.POST.get("client_id"), request.POST.get("text"))
        except ValueError as exc:
            error = str(exc)
        else:
            messages.success(request, "Guidance saved separately and shared with the medical officer and astronaut.")
            return redirect("mission_ground_packet", pk=pk)
    return render(request, "meridian/ground_packet.html", {"packet": item, "ground_role": ground_role, "client_id": str(uuid.uuid4()), "error": error,
        "text": request.POST.get("text", ""), "guidance": item.guidance.select_related("author")}, status=400 if error else 200)


@mission_view
def guidance(request):
    require_scope(request.user, roles=["astronaut", "medical_officer", "flight_surgeon"])
    access = access_for(request.user)
    items = GroundGuidance.objects.select_related("packet__astronaut", "author").prefetch_related("read_receipts")
    if access and access.role == "astronaut" and not request.user.is_superuser:
        items = items.filter(packet__astronaut_id=access.astronaut_id)
    cards = [{"item": item, "read": any(r.actor_id == request.user.pk for r in item.read_receipts.all())} for item in items[:200]]
    return render(request, "meridian/guidance.html", {"cards": cards, "can_write": can_write(request.user)})


@mission_view
@require_POST
def guidance_read(request, pk):
    item = get_object_or_404(GroundGuidance.objects.select_related("packet"), pk=pk)
    require_scope(request.user, item.packet.astronaut_id, write=True)
    read_guidance(request.user, pk)
    return redirect("mission_guidance")
