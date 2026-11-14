import io
import uuid

import pandas as pd
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from engine import analyse, simulate
from .models import CheckIn, DailyRecord
from .services import import_dataset, parse_dataset, save_checkin, save_frame


class DatasetImportTests(TestCase):
    def setUp(self):
        frame = simulate(days=21)
        frame = frame.drop(columns=["radiation_msv"])
        self.csv_bytes = frame.to_csv(index=False).encode()

    def test_csv_import_accepts_optional_radiation_and_sorts_days(self):
        frame = parse_dataset(SimpleUploadedFile("crew.csv", self.csv_bytes))

        self.assertEqual(len(frame), 21)
        self.assertEqual(frame.day.iloc[0], 1)
        self.assertTrue(frame.radiation_msv.isna().all())

    def test_excel_import_and_required_columns(self):
        output = io.BytesIO()
        pd.read_csv(io.BytesIO(self.csv_bytes)).to_excel(output, index=False)
        frame = parse_dataset(SimpleUploadedFile("crew.xlsx", output.getvalue()))
        self.assertEqual(len(frame), 21)

        incomplete = pd.read_csv(io.BytesIO(self.csv_bytes)).drop(columns=["spo2"])
        upload = SimpleUploadedFile("incomplete.csv", incomplete.to_csv(index=False).encode())
        with self.assertRaisesRegex(ValueError, "spo2"):
            parse_dataset(upload)

    def test_import_rejects_duplicate_days_and_short_baselines(self):
        source = pd.read_csv(io.BytesIO(self.csv_bytes))
        source.loc[1, "day"] = source.loc[0, "day"]
        upload = SimpleUploadedFile("duplicate.csv", source.to_csv(index=False).encode())
        with self.assertRaisesRegex(ValueError, "only once"):
            parse_dataset(upload)

        short = pd.read_csv(io.BytesIO(self.csv_bytes)).head(20)
        upload = SimpleUploadedFile("short.csv", short.to_csv(index=False).encode())
        with self.assertRaisesRegex(ValueError, "at least 21"):
            parse_dataset(upload)

    def test_append_rejects_conflicting_days_and_replace_clears_checkins(self):
        frame = parse_dataset(SimpleUploadedFile("crew.csv", self.csv_bytes))
        import_dataset(frame, "replace")
        with self.assertRaisesRegex(ValueError, "already exist"):
            import_dataset(frame, "append")
        CheckIn.objects.create(
            day=21,
            mood=7,
            stress=4,
            sleep_h=7,
            symptoms=[],
        )
        import_dataset(frame, "replace")
        self.assertEqual(DailyRecord.objects.count(), 21)
        self.assertEqual(CheckIn.objects.count(), 0)


class CheckInTests(TestCase):
    def setUp(self):
        from .models import DatasetLock

        DatasetLock.objects.get_or_create(pk=1)
        save_frame(simulate(days=21))

    def test_checkin_appends_a_day_and_retries_idempotently(self):
        client_id = uuid.uuid4()
        first, created = save_checkin(client_id, 8, 3, 7.5, ["Headache"])
        retry, retry_created = save_checkin(client_id, 8, 3, 7.5, ["Headache"])

        self.assertTrue(created)
        self.assertFalse(retry_created)
        self.assertEqual(first.day, 22)
        self.assertEqual(retry.pk, first.pk)
        self.assertEqual(DailyRecord.objects.count(), 22)
        self.assertEqual(first.symptoms, ["Headache"])

    def test_checkin_rejects_out_of_range_values(self):
        with self.assertRaisesRegex(ValueError, "between 1 and 10"):
            save_checkin(uuid.uuid4(), 11, 3, 7, [])


class AnalysisTests(TestCase):
    def test_analysis_marks_missing_radiation_as_unavailable(self):
        frame = simulate(days=21).drop(columns=["radiation_msv"])

        result = analyse(frame)

        self.assertIsNone(result["radiation_pct"])
        self.assertIsNone(result["radiation_projected"])

    def test_analysis_rejects_empty_dataset(self):
        with self.assertRaisesRegex(ValueError, "daily record"):
            analyse(pd.DataFrame())


class DashboardTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="operator",
            password="test-password",
            is_staff=True,
        )
        self.client = Client()

    def test_dashboard_requires_staff_login(self):
        response = self.client.get(reverse("dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("login"), response.url)

    def test_dashboard_renders_import_and_analysis_views(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Start with a dataset")

        from .models import DatasetLock

        DatasetLock.objects.get_or_create(pk=1)
        save_frame(simulate(days=21))
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, "Health overview")
        self.assertContains(response, "Indicator trends")
        self.assertContains(response, "checkin-form")

    def test_pwa_manifest_and_offline_page_are_available(self):
        self.assertEqual(self.client.get(reverse("manifest")).status_code, 200)
        self.assertContains(self.client.get(reverse("offline")), "Connection unavailable")

    def test_checkin_api_saves_valid_data_and_rejects_bad_payload(self):
        from .models import DatasetLock

        DatasetLock.objects.get_or_create(pk=1)
        save_frame(simulate(days=21))
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("check_in"),
            data='{"client_id":"c1fba3b7-59a6-4e8d-a3de-587137d13dc9","mood":8,"stress":3,"sleep_h":7.5,"symptoms":["Headache"]}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["day"], 22)
        self.assertEqual(DailyRecord.objects.count(), 22)

        response = self.client.post(reverse("check_in"), data="[]", content_type="application/json")
        self.assertEqual(response.status_code, 400)


class OfflineShellTests(TestCase):
    def test_service_worker_precaches_offline_form_assets(self):
        response = self.client.get(reverse("service_worker"))
        self.assertEqual(response.status_code, 200)
        for asset in ("/offline/", "/static/health/app.js", "/static/health/app.css", "/static/health/icon.svg"):
            self.assertContains(response, asset)
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertContains(response, 'key.startsWith("astrodoctor-shell-")')


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
        for text in ("Meet the developers", 'id="appearance-theme"', 'id="appearance-background"', "health/ui.js"):
            self.assertContains(response, text)
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


class DatasetTrainingTests(TestCase):
    def setUp(self):
        from .models import DatasetLock

        DatasetLock.objects.get_or_create(pk=1)
        self.frame = simulate(days=42)
        save_frame(self.frame)
        self.user = get_user_model().objects.create_user(username="trainer", is_staff=True)
        self.client.force_login(self.user)

    def test_training_uses_only_early_rows_and_persists_report(self):
        from .services import analyse_dataset, train_dataset

        trained = train_dataset(28)
        self.assertAlmostEqual(trained.means["resting_hr"], self.frame.resting_hr.iloc[:28].mean())
        self.assertAlmostEqual(trained.deviations["resting_hr"], self.frame.resting_hr.iloc[:28].std())
        self.assertEqual(trained.report["evaluation_rows"], 14)
        self.assertEqual(len(trained.report["indicators"]), 9)
        self.assertAlmostEqual(analyse_dataset(self.frame)["baseline"]["resting_hr"], trained.means["resting_hr"])
        self.assertNotAlmostEqual(analyse(self.frame)["baseline"]["resting_hr"], trained.means["resting_hr"])

    def test_holdout_changes_do_not_change_fitted_statistics(self):
        from .services import train_dataset

        first = train_dataset(21)
        DailyRecord.objects.filter(day__gt=21).update(resting_hr=200)
        second = train_dataset(21)
        self.assertEqual(first.means, second.means)
        self.assertEqual(first.deviations, second.deviations)
        self.assertEqual(second.report["hard_limit_rows"], 21)

    def test_training_preserves_hard_limits(self):
        from .services import analyse_dataset, records_frame, train_dataset

        DailyRecord.objects.all().update(resting_hr=110)
        trained = train_dataset(21)
        result = analyse_dataset(records_frame())
        self.assertEqual(result["levels"]["Cardiovascular"], "Red")
        self.assertTrue(trained.report["warnings"])
        self.assertTrue(any("100 bpm" in alert["why"] for alert in result["alerts"]))

    def test_invalid_split_does_not_replace_existing_model(self):
        from .models import DatasetCalibration
        from .services import train_dataset

        trained = train_dataset(21)
        for split in (20, 36, "bad", "21.5", None):
            with self.assertRaises(ValueError):
                train_dataset(split)
        self.assertEqual(DatasetCalibration.objects.get().trained_at, trained.trained_at)

    def test_import_invalidates_training_and_checkin_keeps_it(self):
        from .models import DatasetCalibration
        from .services import train_dataset

        train_dataset(21)
        save_checkin(uuid.uuid4(), 7, 4, 7, [])
        self.assertTrue(DatasetCalibration.objects.exists())
        import_dataset(self.frame, "replace")
        self.assertFalse(DatasetCalibration.objects.exists())

    def test_training_ui_permissions_and_validation(self):
        response = self.client.get(reverse("dashboard"))
        self.assertContains(response, 'id="training-dialog"')
        response = self.client.post(reverse("dataset_training"), {"baseline_rows": "21"})
        self.assertRedirects(response, reverse("dashboard"))
        self.assertContains(self.client.get(reverse("dashboard")), "Trained baseline active")
        self.assertEqual(self.client.post(reverse("dataset_training"), {"baseline_rows": "100"}).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.post(reverse("dataset_training"), {"baseline_rows": "21"}).status_code, 302)
        self.user.is_staff = False
        self.user.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse("dataset_training")).status_code, 302)

    def test_short_dataset_cannot_train_and_reports_reason(self):
        from .services import train_dataset

        DailyRecord.objects.filter(day__gt=21).delete()
        with self.assertRaisesRegex(ValueError, "7 later rows"):
            train_dataset(21)
        self.assertContains(self.client.get(reverse("dataset_training")), "Training needs at least 28 rows")
