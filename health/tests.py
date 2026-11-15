import io
import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import NoReverseMatch, reverse


class OfflineShellTests(TestCase):
    def test_service_worker_precaches_offline_page_assets(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        for asset in ("/offline/", "/static/health/app.css", "/static/wellbeing/shell.css", "/static/health/icon.svg"):
            self.assertContains(response, asset)
        self.assertNotContains(response, "/static/health/app.js")
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertContains(response, 'key.startsWith("astrodoctor-shell-")')
        # Static assets are network-first so CSS/JS updates are never hidden by the cache.
        script = response.content.decode()
        static_branch = script[script.index('url.pathname.startsWith("/static/")'):script.index('request.mode === "navigate"')]
        self.assertLess(static_branch.index("fetch(request)"), static_branch.index("caches.match(request)"))
        self.assertIn('cache: "reload"', script)

    def test_pwa_manifest_and_offline_page_are_available(self):
        self.assertEqual(self.client.get(reverse("manifest")).status_code, 200)
        page = self.client.get(reverse("offline"))
        self.assertContains(page, "You're offline")
        self.assertNotContains(page, "checkin-form")


class HealthDashboardRemovedTests(TestCase):
    def test_dashboard_routes_no_longer_exist(self):
        for name in ("dashboard", "import_data", "load_demo", "check_in", "dataset_training"):
            with self.assertRaises(NoReverseMatch):
                reverse(name)
        staff = get_user_model().objects.create_user("ops", password="pw-12345-x", is_staff=True)
        self.client.force_login(staff)
        self.assertEqual(self.client.get("/health/").status_code, 404)
        self.assertNotContains(self.client.get(reverse("home")), "Health dashboard")


class CrewProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="crew-admin", is_staff=True)
        self.client.force_login(self.user)
        self.payload = {"full_name": "Amina Okello", "role": "Mission specialist", "mission": "Artemis Test", "status": "active", "call_sign": "Orion"}

    def test_create_edit_and_view_profile(self):
        from .models import CrewMember

        response = self.client.post(reverse("crew_create"), self.payload)
        member = CrewMember.objects.get()
        self.assertRedirects(response, reverse("crew_detail", args=[member.pk]))
        self.assertContains(self.client.get(reverse("crew_list")), "Amina Okello")
        self.assertContains(self.client.get(reverse("crew_detail", args=[member.pk])), "Orion")
        response = self.client.post(reverse("crew_edit", args=[member.pk]), {**self.payload, "role": "Commander"})
        member.refresh_from_db()
        self.assertEqual(member.role, "Commander")
        self.assertEqual(response.status_code, 302)

    def test_mission_clock_age_and_redesigned_pages(self):
        from datetime import date, timedelta
        from .models import CrewMember

        today = date.today()
        flying = CrewMember.objects.create(full_name="Amina Okello", role="Engineer", mission="Expedition 74", status="active",
                                           mission_start=today - timedelta(days=9), date_of_birth=date(today.year - 30, 1, 1))
        CrewMember.objects.create(full_name="Lena Fischer", role="Specialist", mission="Artemis IV", status="training",
                                  mission_start=today + timedelta(days=5))
        self.assertEqual(flying.mission_clock(today), ("day", 10))
        self.assertEqual(CrewMember(mission_start=today + timedelta(days=5)).mission_clock(today), ("countdown", 5))
        self.assertIsNone(CrewMember().mission_clock(today))
        self.assertEqual(flying.age, 30)

        directory = self.client.get(reverse("crew_list"))
        self.assertContains(directory, "across 2 missions")
        self.assertContains(directory, "Day 10")
        self.assertContains(directory, "T−5 d")
        self.assertContains(directory, 'data-status="training"')
        self.assertContains(self.client.get(reverse("crew_detail", args=[flying.pk])), "Day 10")
        form = self.client.get(reverse("crew_edit", args=[flying.pk]))
        for heading in ("Who they are", "Assignment", "Contact and background"):
            self.assertContains(form, heading)

    def test_profile_requires_name_role_and_mission(self):
        response = self.client.post(reverse("crew_create"), {"status": "active"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "full_name", "This field is required.")

    def test_portrait_is_resized_and_protected(self):
        import tempfile
        from PIL import Image
        from .models import CrewMember

        output = io.BytesIO()
        Image.new("RGB", (1000, 900), "navy").save(output, "PNG")
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            upload = SimpleUploadedFile("portrait.png", output.getvalue(), content_type="image/png")
            self.client.post(reverse("crew_create"), {**self.payload, "photo": upload})
            member = CrewMember.objects.get()
            with member.photo.open() as stored:
                with Image.open(stored) as image:
                    self.assertEqual(image.format, "JPEG")
                    self.assertEqual(image.size, (800, 720))
            url = reverse("crew_photo", args=[member.pk])
            response = self.client.get(url)
            self.assertEqual(response["Cache-Control"], "private, no-store")
            response.close()
            response = self.client.get(reverse("crew_edit", args=[member.pk]))
            self.assertContains(response, 'name="photo-clear"')
            self.client.post(reverse("crew_edit", args=[member.pk]), {**self.payload, "photo-clear": "on"})
            member.refresh_from_db()
            self.assertFalse(member.photo)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.client.logout()
            self.assertEqual(self.client.get(url).status_code, 302)
            self.assertEqual(self.client.get(reverse("crew_list")).status_code, 302)

    def test_invalid_photo_and_non_staff_access_are_rejected(self):
        upload = SimpleUploadedFile("fake.png", b"not an image", content_type="image/png")
        response = self.client.post(reverse("crew_create"), {**self.payload, "photo": upload})
        self.assertIn("photo", response.context["form"].errors)
        self.user.is_staff = False
        self.user.save()
        self.assertEqual(self.client.get(reverse("crew_create")).status_code, 302)


class DeveloperTeamTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="developer-admin", is_staff=True)
        self.client.force_login(self.user)
        self.payload = {"full_name": "Ada Developer", "role": "Frontend engineer", "github": "https://github.com/example"}

    def test_five_slots_can_be_filled_and_edited(self):
        from .models import Developer

        self.assertContains(self.client.get(reverse("developer_team")), "0 of 5 profiles added")
        for slot in range(1, 6):
            response = self.client.post(reverse("developer_edit", args=[slot]), self.payload)
            self.assertRedirects(response, reverse("developer_team"))
        self.assertEqual(Developer.objects.count(), 5)
        self.assertContains(self.client.get(reverse("developer_team")), "5 of 5 profiles added")
        self.client.post(reverse("developer_edit", args=[1]), {**self.payload, "full_name": "Updated name"})
        self.assertEqual(Developer.objects.get(slot=1).full_name, "Updated name")
        self.assertEqual(Developer.objects.count(), 5)
        self.assertEqual(self.client.post(reverse("developer_edit", args=[6]), self.payload).status_code, 404)

    def test_redesigned_team_page_shows_seats_links_and_stack(self):
        from .models import Developer

        Developer.objects.create(slot=2, full_name="Ada Developer", role="Frontend engineer", github="https://github.com/example")
        page = self.client.get(reverse("developer_team"))
        self.assertContains(page, "1 of 5 profiles added")
        self.assertContains(page, "Seat 02")
        self.assertContains(page, "Open seat", count=4)
        self.assertContains(page, 'href="https://github.com/example" target="_blank" rel="noopener noreferrer"')
        self.assertContains(page, "What powers Astro-Doctor")
        form = self.client.get(reverse("developer_edit", args=[2]))
        for heading in ("Who they are", "Where to find them", "Their story"):
            self.assertContains(form, heading)

    def test_database_rejects_invalid_and_duplicate_slots(self):
        from django.db import IntegrityError, transaction
        from .models import Developer

        Developer.objects.create(slot=1, full_name="One", role="Engineer")
        for slot in (1, 0, 6):
            with self.assertRaises(IntegrityError), transaction.atomic():
                Developer.objects.create(slot=slot, full_name="Invalid", role="Engineer")

    def test_team_requires_staff_and_valid_links(self):
        response = self.client.post(reverse("developer_edit", args=[1]), {**self.payload, "website": "javascript:alert(1)"})
        self.assertIn("website", response.context["form"].errors)
        self.client.logout()
        for name, args in (("developer_team", []), ("developer_edit", [1]), ("developer_photo", [1])):
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 302)
        self.user.is_staff = False
        self.user.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.post(reverse("developer_edit", args=[1]), self.payload).status_code, 302)

    def test_developer_portrait_upload_and_removal(self):
        import tempfile
        from PIL import Image
        from .models import Developer

        output = io.BytesIO()
        Image.new("RGB", (20, 20), "teal").save(output, "PNG")
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            upload = SimpleUploadedFile("developer.png", output.getvalue(), content_type="image/png")
            response = self.client.post(reverse("developer_edit", args=[1]), {**self.payload, "photo": upload})
            self.assertEqual(response.status_code, 302)
            member = Developer.objects.get(slot=1)
            self.assertTrue(member.photo)
            response = self.client.get(reverse("developer_photo", args=[1]))
            self.assertEqual(response["Cache-Control"], "private, no-store")
            response.close()
            self.client.post(reverse("developer_edit", args=[1]), {**self.payload, "photo-clear": "on"})
            member.refresh_from_db()
            self.assertFalse(member.photo)
            self.assertEqual(self.client.get(reverse("developer_photo", args=[1])).status_code, 404)

    def test_footer_and_ui_assets_are_available(self):
        response = self.client.get(reverse("developer_team"))
        for text in ("Meet the developers", 'id="appearance-theme"', "health/ui.js"):
            self.assertContains(response, text)
        self.assertNotContains(response, 'id="appearance-background"')
        self.assertContains(self.client.get(reverse("service_worker")), "/static/health/ui.js")


class AccountProfileTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="crew-user", is_staff=False)
        self.client.force_login(self.user)

    def test_non_staff_user_can_save_without_any_photo_or_details(self):
        from .models import UserProfile

        response = self.client.get(reverse("my_profile"))
        self.assertContains(response, "My profile")
        self.assertContains(response, 'aria-label="Edit your profile"')
        self.assertFalse(UserProfile.objects.exists())
        response = self.client.post(reverse("my_profile"), {})
        self.assertRedirects(response, reverse("my_profile"))
        self.assertFalse(UserProfile.objects.get(user=self.user).photo)
        self.assertEqual(self.client.get(reverse("my_profile_photo")).status_code, 404)

    def test_profile_update_is_bound_to_current_user(self):
        from .models import UserProfile

        other = get_user_model().objects.create_user(username="other")
        other_profile = UserProfile.objects.create(user=other, display_name="Other person")
        self.client.post(reverse("my_profile"), {"display_name": "My name", "job_title": "Commander", "user": other.pk, "is_staff": "true"})
        self.assertEqual(UserProfile.objects.get(user=self.user).display_name, "My name")
        other_profile.refresh_from_db()
        self.assertEqual(other_profile.display_name, "Other person")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_uploaded_or_captured_photo_updates_avatar_and_can_be_removed(self):
        import tempfile
        from PIL import Image
        from .models import UserProfile

        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            for filename in ("upload.png", "camera-portrait.jpg"):
                output = io.BytesIO()
                Image.new("RGB", (30, 30), "teal").save(output, "JPEG" if filename.endswith("jpg") else "PNG")
                upload = SimpleUploadedFile(filename, output.getvalue(), content_type="image/jpeg" if filename.endswith("jpg") else "image/png")
                self.assertEqual(self.client.post(reverse("my_profile"), {"photo": upload}).status_code, 302)
                self.assertEqual(UserProfile.objects.filter(user=self.user).count(), 1)
                response = self.client.get(reverse("my_profile_photo"))
                self.assertEqual(response.status_code, 200)
                self.assertIn("no-store", response["Cache-Control"])
                response.close()
                self.assertContains(self.client.get(reverse("my_profile")), 'alt="Your profile photo"')
            other = get_user_model().objects.create_user(username="no-photo")
            self.client.force_login(other)
            self.assertEqual(self.client.get(reverse("my_profile_photo")).status_code, 404)
            self.client.force_login(self.user)
            self.client.post(reverse("my_profile"), {"photo-clear": "on"})
            self.assertFalse(UserProfile.objects.get(user=self.user).photo)

    def test_profile_requires_login_and_rejects_fake_photo(self):
        upload = SimpleUploadedFile("fake.jpg", b"invalid", content_type="image/jpeg")
        response = self.client.post(reverse("my_profile"), {"photo": upload})
        self.assertIn("photo", response.context["form"].errors)
        self.client.logout()
        for name in ("my_profile", "my_profile_photo"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 302)

    def test_cached_offline_shell_does_not_include_account_avatar(self):
        response = self.client.get(reverse("offline"))
        self.assertNotContains(response, 'class="account-avatar"')
        self.assertContains(self.client.get(reverse("service_worker")), "/static/health/camera.js")


