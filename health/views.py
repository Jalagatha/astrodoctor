import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.views.decorators.cache import never_cache

staff_required = user_passes_test(lambda user: user.is_authenticated and user.is_staff)


def manifest(request):
    return JsonResponse(
        {
            "name": "Astro-Doctor",
            "short_name": "Astro-Doctor",
            "description": "Crew wellbeing check-ins and adaptive VR scene recommendations",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "background_color": "#04060f",
            "theme_color": "#060a1a",
            "icons": [
                {"src": "/static/health/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
            ],
        },
        content_type="application/manifest+json",
    )


def service_worker(request):
    shell = json.dumps(["/offline/", static("wellbeing/shell.css"), static("wellbeing/wellbeing.css"), static("wellbeing/experience.js"), static("wellbeing/session.js"), static("health/app.css"), static("health/ui.js"), static("health/camera.js"), static("health/icon.svg")])
    script = """
const CACHE = "astrodoctor-shell-v12";
const SHELL = __SHELL__;
self.addEventListener("install", event => {
  // cache: "reload" skips the browser's HTTP cache so the shell is always fresh.
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL.map(url => new Request(url, { cache: "reload" })))));
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
    // Network first so style and script updates show immediately; the cached
    // copy is only a fallback for when the device is offline.
    event.respondWith(fetch(request).then(response => {
      if (response.ok) {
        const copy = response.clone();
        event.waitUntil(caches.open(CACHE).then(cache => cache.put(request, copy)));
      }
      return response;
    }).catch(() => caches.match(request).then(cached => cached || Response.error())));
    return;
  }
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/offline/")));
  }
});
"""
    return HttpResponse(
        script.replace("__SHELL__", shell),
        content_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


def offline(request):
    return render(request, "health/offline.html", {"offline_shell": True})


@staff_required
def crew_list(request):
    from .models import CrewMember

    crew = list(CrewMember.objects.all())
    for member in crew:
        member.clock = member.mission_clock()
    counts = {key: sum(member.status == key for member in crew) for key, _ in CrewMember._meta.get_field("status").choices}
    return render(request, "health/crew_list.html", {
        "crew": crew, "counts": counts,
        "missions": len({member.mission.strip().lower() for member in crew if member.mission.strip()}),
        "status_choices": CrewMember._meta.get_field("status").choices,
    })


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
    layout = [
        (("Identity", "Who they are"), ["full_name", "call_sign", "role", "status"]),
        (("Mission", "Assignment"), ["mission", "mission_start", "agency", "nationality"]),
        (("Personal", "Contact and background"), ["date_of_birth", "email", "biography"]),
    ]
    sections = [(heading, [form[name] for name in names]) for heading, names in layout]
    return render(request, "health/crew_form.html", {"form": form, "member": member, "sections": sections})


@staff_required
def crew_detail(request, pk):
    from django.shortcuts import get_object_or_404
    from .models import CrewMember

    member = get_object_or_404(CrewMember, pk=pk)
    return render(request, "health/crew_detail.html", {"member": member, "clock": member.mission_clock()})


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
        "stack": [("Django", "Web app & PWA"), ("scikit-learn", "Scene recommender"), ("Thompson sampling", "Personal learning"),
                  ("Three.js", "3D theme worlds"), ("Web Audio", "Soundscapes"), ("PostgreSQL", "Mission data")],
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
    layout = [
        (("Identity", "Who they are"), ["full_name", "role"]),
        (("Links", "Where to find them"), ["email", "github", "website"]),
        (("About", "Their story"), ["biography"]),
    ]
    sections = [(heading, [form[name] for name in names]) for heading, names in layout]
    return render(request, "health/developer_form.html", {"form": form, "member": member, "slot": slot, "sections": sections})


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
    return render(request, "health/my_profile.html", {"form": form, "profile": profile, **_wellbeing_summary(request.user)})


def _wellbeing_summary(user):
    """Personal wellbeing figures shown on the profile card."""
    from wellbeing.models import VRSession, WellbeingCheckIn
    from wellbeing.presentation import display_name, home_stats

    completed = list(VRSession.objects.filter(user=user, status=VRSession.RECHECKED).select_related("checkin")[:200])
    return {
        "summary": home_stats(completed),
        "last_checkin": WellbeingCheckIn.objects.filter(user=user).first(),
        "first_name": display_name(user),
    }


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
