import json
from zipfile import BadZipFile

import pandas as pd
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from openpyxl.utils.exceptions import InvalidFileException

from engine import INDICATORS
from .models import CheckIn, DailyRecord
from .services import (
    SYMPTOMS,
    analyse_dataset,
    train_dataset,
    import_dataset,
    load_demo_dataset,
    parse_dataset,
    records_frame,
    save_checkin,
)

staff_required = user_passes_test(lambda user: user.is_authenticated and user.is_staff)


@login_required
@ensure_csrf_cookie
def dashboard(request):
    from meridian.models import Astronaut
    if Astronaut.objects.exists():
        return redirect("mission_home")
    if not request.user.is_staff:
        return redirect("mission_home")
    frame = records_frame()
    if frame.empty:
        return render(
            request,
            "health/dashboard.html",
            {"has_data": False, "recent_checkins": CheckIn.objects.all()[:5]},
        )

    result = analyse_dataset(frame)
    selected = request.GET.get("indicator", "resting_hr")
    if selected not in INDICATORS:
        selected = "resting_hr"
    chart = frame.loc[:, ["day", selected]].tail(60).copy()
    chart["baseline"] = result["baseline"][selected]
    chart_data = [
        {"day": int(row.day), "value": float(getattr(row, selected)), "baseline": float(row.baseline)}
        for row in chart.itertuples(index=False)
    ]
    top_level = max(result["levels"].values(), key=lambda level: ["Green", "Yellow", "Orange", "Red"].index(level))
    context = {
        "has_data": True,
        **training_context(frame),
        "result": result,
        "day": int(frame.iloc[-1]["day"]),
        "top_level": top_level,
        "domains": result["levels"].items(),
        "alerts": result["alerts"],
        "indicator_choices": [
            (key, f"{value[2]} ({value[3]})") for key, value in INDICATORS.items()
        ],
        "selected_indicator": selected,
        "chart_data": json.dumps(chart_data),
        "records_count": len(frame),
        "recent_checkins": CheckIn.objects.all()[:5],
        "dose_available": pd.notna(result["radiation_pct"]),
        "symptoms": sorted(SYMPTOMS),
    }
    return render(request, "health/dashboard.html", context)


@staff_required
@require_POST
def import_data(request):
    upload = request.FILES.get("dataset")
    if upload is None:
        messages.error(request, "Choose a CSV or Excel file first.")
        return redirect("dashboard")
    try:
        frame = parse_dataset(upload)
        mode = request.POST.get("mode", "")
        import_dataset(frame, mode)
    except (
        ValueError,
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeDecodeError,
        OSError,
        BadZipFile,
        InvalidFileException,
    ) as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request,
            f"Imported {len(frame)} daily rows ({'replaced' if mode == 'replace' else 'appended to'} the database).",
        )
    return redirect("dashboard")


@staff_required
@require_POST
def load_demo(request):
    if load_demo_dataset():
        messages.success(request, "Loaded the clearly labeled 180-day demonstration dataset.")
    else:
        messages.error(request, "The database already contains records; replace them by importing a dataset.")
    return redirect("dashboard")


@staff_required
@require_POST
def check_in(request):
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict):
            raise ValueError("Check-in data must be an object.")
        checkin, created = save_checkin(
            client_id=payload.get("client_id"),
            mood=payload.get("mood"),
            stress=payload.get("stress"),
            sleep_h=payload.get("sleep_h"),
            symptoms=payload.get("symptoms", []),
        )
    except (json.JSONDecodeError, ValueError) as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    return JsonResponse(
        {"ok": True, "created": created, "day": checkin.day, "message": f"Saved check-in for mission day {checkin.day}."}
    )


def manifest(request):
    return JsonResponse(
        {
            "name": "Astro-Doctor",
            "short_name": "Astro-Doctor",
            "description": "Crew health self-monitoring and check-ins",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#f2f6f7",
            "theme_color": "#103b46",
            "icons": [
                {"src": "/static/health/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
            ],
        },
        content_type="application/manifest+json",
    )


def service_worker(request):
    shell = json.dumps(["/offline/", "/mission/offline/", static("health/meridian.js"), static("health/app.js"), static("health/app.css"), static("health/ui.js"), static("health/camera.js"), static("health/icon.svg")])
    script = """
const CACHE = "astrodoctor-shell-v7";
const SHELL = __SHELL__;
self.addEventListener("install", event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener("activate", event => {
  event.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(key => key.startsWith("astrodoctor-shell-") && key !== CACHE).map(key => caches.delete(key)))));
  self.clients.claim();
});
self.addEventListener("fetch", event => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== "GET" || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/static/")) {
    event.respondWith(caches.match(request).then(cached => cached || fetch(request).then(response => {
      if (response.ok) caches.open(CACHE).then(cache => cache.put(request, response.clone()));
      return response;
    })));
    return;
  }
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match(url.pathname.startsWith("/mission/") ? "/mission/offline/" : "/offline/")));
  }
});
"""
    return HttpResponse(
        script.replace("__SHELL__", shell),
        content_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


def offline(request):
    return render(request, "health/offline.html", {"symptoms": sorted(SYMPTOMS), "offline_shell": True})


@staff_required
def crew_list(request):
    from .models import CrewMember

    return render(request, "health/crew_list.html", {"crew": CrewMember.objects.all()})


@staff_required
def crew_edit(request, pk=None):
    from django.shortcuts import get_object_or_404
    from .forms import CrewMemberForm
    from .models import CrewMember

    member = get_object_or_404(CrewMember, pk=pk) if pk else None
    form = CrewMemberForm(request.POST or None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        member = form.save()
        messages.success(request, f"Profile saved for {member.full_name}.")
        return redirect("crew_detail", pk=member.pk)
    return render(request, "health/crew_form.html", {"form": form, "member": member})


@staff_required
def crew_detail(request, pk):
    from django.shortcuts import get_object_or_404
    from .models import CrewMember

    return render(request, "health/crew_detail.html", {"member": get_object_or_404(CrewMember, pk=pk)})


@staff_required
def crew_photo(request, pk):
    from django.http import FileResponse, Http404
    from django.shortcuts import get_object_or_404
    from .models import CrewMember

    member = get_object_or_404(CrewMember, pk=pk)
    if not member.photo:
        raise Http404
    try:
        photo = member.photo.open("rb")
    except FileNotFoundError:
        raise Http404
    response = FileResponse(photo, content_type="image/jpeg")
    response["Cache-Control"] = "private, no-store"
    return response


@staff_required
def developer_team(request):
    from .models import Developer

    developers = {member.slot: member for member in Developer.objects.all()}
    return render(request, "health/developers.html", {
        "slots": [{"number": number, "member": developers.get(number)} for number in range(1, 6)],
        "developer_count": len(developers),
    })


@staff_required
def developer_edit(request, slot):
    from django.http import Http404
    from .forms import DeveloperForm
    from .models import Developer

    if slot not in range(1, 6):
        raise Http404
    member = Developer.objects.filter(slot=slot).first()
    form = DeveloperForm(request.POST if request.method == "POST" else None, request.FILES or None, instance=member)
    if request.method == "POST" and form.is_valid():
        # A unique slot and update_or_create keep concurrent submissions within five seats.
        values = dict(form.cleaned_data)
        if values.get("photo") is False:
            values["photo"] = ""
        Developer.objects.update_or_create(slot=slot, defaults=values)
        messages.success(request, "Developer profile saved.")
        return redirect("developer_team")
    return render(request, "health/developer_form.html", {"form": form, "member": member, "slot": slot})


@staff_required
def developer_photo(request, slot):
    from django.http import FileResponse, Http404
    from django.shortcuts import get_object_or_404
    from .models import Developer

    member = get_object_or_404(Developer, slot=slot)
    if not member.photo:
        raise Http404
    try:
        response = FileResponse(member.photo.open("rb"), content_type="image/jpeg")
    except FileNotFoundError:
        raise Http404
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@never_cache
def my_profile(request):
    from .forms import UserProfileForm
    from .models import UserProfile

    profile = UserProfile.objects.filter(user=request.user).first()
    form = UserProfileForm(request.POST if request.method == "POST" else None, request.FILES or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        values = dict(form.cleaned_data)
        if values.get("photo") is False:
            values["photo"] = ""
        UserProfile.objects.update_or_create(user=request.user, defaults=values)
        messages.success(request, "Your profile has been updated.")
        return redirect("my_profile")
    return render(request, "health/my_profile.html", {"form": form, "profile": profile})


@login_required
@never_cache
def my_profile_photo(request):
    from django.http import FileResponse, Http404
    from .models import UserProfile

    profile = UserProfile.objects.filter(user=request.user).first()
    if not profile or not profile.photo:
        raise Http404
    try:
        return FileResponse(profile.photo.open("rb"), content_type="image/jpeg")
    except FileNotFoundError:
        raise Http404



def training_context(frame=None):
    from .models import DatasetCalibration

    count = len(frame) if frame is not None else DailyRecord.objects.count()
    trained = DatasetCalibration.objects.filter(pk=1).first()
    return {"training_count": count, "max_baseline_rows": max(21, count - 7),
            "can_train": count >= 28, "trained": trained}


@staff_required
def dataset_training(request):
    error = None
    if request.method == "POST":
        try:
            trained = train_dataset(request.POST.get("baseline_rows"))
        except ValueError as exc:
            error = str(exc)
        else:
            messages.success(request, f"Trained baseline on {trained.baseline_rows} rows and evaluated {trained.report['evaluation_rows']} later rows. Applied to both dashboards.")
            return redirect("dashboard")
    return render(request, "health/training.html", {**training_context(), "training_error": error}, status=400 if error else 200)
