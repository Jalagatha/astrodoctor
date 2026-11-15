from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .catalog import DURATION_CHOICES, SCENES, SCENES_BY_KEY, default_time_block
from .forms import CheckInForm, GenerateDatasetForm, ReCheckForm, StartSessionForm, TrainModelForm
from .jobs import JobBusy, active_job, dataset_info, save_upload, start_job
from .models import TrainingJob, VRSession, WellbeingCheckIn
from .presentation import display_name, gauge, greeting, home_stats, mood_chart, outcome_deltas, reason_items
from .recommender import ModelUnavailable
from .services import create_recommendation, end_session, model_bundle, start_session, theme_summary

staff_required = user_passes_test(lambda user: user.is_authenticated and user.is_staff)


def _model_status():
    try:
        bundle = model_bundle()
    except ModelUnavailable as exc:
        return None, str(exc)
    return bundle, None


@login_required
def home(request):
    sessions = VRSession.objects.filter(user=request.user).select_related("checkin")
    completed = list(sessions.filter(status=VRSession.RECHECKED)[:60])
    _, model_error = _model_status()
    now = timezone.now()
    return render(request, "wellbeing/home.html", {
        "open_session": sessions.filter(status__in=[VRSession.RECOMMENDED, VRSession.STARTED, VRSession.ENDED]).first(),
        "recent": sessions[:6],
        "themes": theme_summary(request.user),
        "completed_count": len(completed),
        "stats": home_stats(completed),
        "chart": mood_chart(completed),
        "last_checkin": WellbeingCheckIn.objects.filter(user=request.user).first(),
        "greeting": greeting(now), "name": display_name(request.user),
        "model_error": model_error,
    })


@login_required
def checkin(request):
    _, model_error = _model_status()
    last = WellbeingCheckIn.objects.filter(user=request.user).first()
    initial = {"time_block": default_time_block(timezone.now().hour)}
    if last:
        initial["mission_day"] = last.mission_day
    initial["sleep_hours"] = last.sleep_hours if last else 7.0
    form = CheckInForm(request.POST or None, initial=initial)
    if request.method == "POST" and not model_error and form.is_valid():
        entry = form.save(commit=False)
        entry.user = request.user
        entry.save()
        try:
            session = create_recommendation(entry)
        except ModelUnavailable as exc:  # model removed between the check above and now
            entry.delete()
            messages.error(request, str(exc))
            return redirect("wellbeing_checkin")
        return redirect("wellbeing_session", pk=session.pk)
    return render(request, "wellbeing/checkin.html", {"form": form, "model_error": model_error})


def _own_session(request, pk):
    return get_object_or_404(VRSession.objects.select_related("checkin"), pk=pk, user=request.user)


@login_required
def session_detail(request, pk):
    session = _own_session(request, pk)
    if session.status == VRSession.ENDED:
        return redirect("wellbeing_recheck", pk=pk)
    context = {"session": session, "checkin": session.checkin}
    if session.status == VRSession.RECOMMENDED:
        expected = [item["predicted"] + item["adjustment"] for item in session.ranking]
        low, high = min(expected), max(expected)
        context["options"] = [
            {**item, "scene": SCENES_BY_KEY[item["key"]], "expected": value,
             "bar": round(15 + 85 * (value - low) / ((high - low) or 1))}
            for item, value in zip(session.ranking, expected)
        ]
        # Show the recommendation first, then the rest by expected benefit (the
        # engine's own order includes a random exploration draw, which reads oddly).
        context["options"].sort(key=lambda option: (
            option["key"] != session.recommended_scene, option["blocked"] is not None, -option["expected"]))
        context["durations"] = DURATION_CHOICES
        context["start_form"] = StartSessionForm(context=session.checkin.context())
        top = context["options"][0]
        context["top"] = top
        context["gauge"] = gauge(top["expected"])
        context["reason_items"] = reason_items(session.reasons)
        return render(request, "wellbeing/recommendation.html", context)
    if session.status == VRSession.STARTED:
        elapsed = (timezone.now() - session.started_at).total_seconds()
        context["remaining_seconds"] = max(0, int(session.planned_minutes * 60 - elapsed))
        return render(request, "wellbeing/player.html", context)
    if session.status == VRSession.RECHECKED:
        context["deltas"] = outcome_deltas(session)
        context["gauge"] = gauge(max(session.gain, 0), 3.0)
    return render(request, "wellbeing/summary.html", context)


@login_required
@require_POST
def session_start(request, pk):
    session = _own_session(request, pk)
    if session.status != VRSession.RECOMMENDED:
        return redirect("wellbeing_session", pk=pk)
    form = StartSessionForm(request.POST, context=session.checkin.context())
    if not form.is_valid():
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)
        return redirect("wellbeing_session", pk=pk)
    try:
        start_session(session, form.cleaned_data["scene"], form.cleaned_data["minutes"])
    except ModelUnavailable as exc:
        messages.error(request, str(exc))
    return redirect("wellbeing_session", pk=pk)


@login_required
@require_POST
def session_end(request, pk):
    session = _own_session(request, pk)
    if session.status == VRSession.STARTED:
        end_session(session)
    return redirect("wellbeing_session", pk=pk)


@login_required
@require_POST
def session_skip(request, pk):
    session = _own_session(request, pk)
    if session.status == VRSession.RECOMMENDED:
        session.status = VRSession.CANCELLED
        session.save(update_fields=["status"])
        messages.success(request, "Check-in saved. No session was run.")
    return redirect("home")


@login_required
def recheck(request, pk):
    session = _own_session(request, pk)
    if session.status != VRSession.ENDED:
        return redirect("wellbeing_session", pk=pk)
    form = ReCheckForm(request.POST or None, instance=session)
    if request.method == "POST" and form.is_valid():
        session = form.save(commit=False)
        session.rechecked_at = timezone.now()
        session.status = VRSession.RECHECKED
        session.save()
        return redirect("wellbeing_session", pk=pk)
    return render(request, "wellbeing/recheck.html", {"form": form, "session": session, "checkin": session.checkin})


def _model_page(request, generate_form=None, train_form=None, status=200):
    bundle, model_error = _model_status()
    dataset = dataset_info()
    job = active_job()
    return render(request, "wellbeing/model.html", {
        "card": bundle.get("card", {}) if bundle else {}, "model_error": model_error, "scenes": SCENES,
        "recorded_sessions": VRSession.objects.filter(status=VRSession.RECHECKED).count(),
        "dataset": dataset, "active_job": job,
        "jobs": TrainingJob.objects.select_related("created_by")[:10],
        "generate_form": generate_form or GenerateDatasetForm(),
        "train_form": train_form or TrainModelForm(dataset_available=dataset is not None),
    }, status=status)


@staff_required
def model_card(request):
    return _model_page(request)


def _start(request, kind, params):
    try:
        job = start_job(kind, params, request.user)
    except JobBusy as exc:
        messages.error(request, str(exc))
        return
    if job.status == TrainingJob.FAILED:
        messages.error(request, f"{job.get_kind_display()} failed: {job.error}")
    elif job.status == TrainingJob.SUCCEEDED:
        messages.success(request, f"{job.get_kind_display()} finished.")
    else:
        messages.success(request, f"{job.get_kind_display()} started. This page updates when it finishes.")


@staff_required
@require_POST
def model_generate(request):
    form = GenerateDatasetForm(request.POST)
    if not form.is_valid():
        return _model_page(request, generate_form=form, status=400)
    _start(request, TrainingJob.GENERATE, form.cleaned_data)
    return redirect("wellbeing_model")


@staff_required
@require_POST
def model_train(request):
    form = TrainModelForm(request.POST, request.FILES, dataset_available=dataset_info() is not None)
    if not form.is_valid():
        return _model_page(request, train_form=form, status=400)
    if form.cleaned_data["source"] == "upload":
        path = save_upload(form.cleaned_data["frame"])
        source = f"Upload: {form.cleaned_data['upload'].name}"
    else:
        path, source = settings.WELLBEING_DATASET_PATH, "Synthetic dataset"
    _start(request, TrainingJob.TRAIN, {
        "data_path": str(path), "source": source, "include_sessions": form.cleaned_data["include_sessions"],
    })
    return redirect("wellbeing_model")


@staff_required
def model_dataset_download(request):
    path = Path(settings.WELLBEING_DATASET_PATH)
    if not path.exists():
        raise Http404
    return FileResponse(path.open("rb"), as_attachment=True, filename=path.name, content_type="text/csv")
