import shutil
import tempfile
from pathlib import Path

import numpy as np
from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from .catalog import SCENE_KEYS, blocked_reason, mission_phase, wellbeing_gain
from .features import FEATURE_COLUMNS, encode_all_scenes
from .models import VRSession
from .recommender import PRIOR_SD, load_bundle, personal_adjustments, rank_scenes, recommend, recommend_duration
from .simulator import generate
from .training import save, train

CONTEXT = {"mood": 2, "energy": 2, "stress": 4, "homesickness": 3, "sleep_hours": 5.5,
           "mission_phase": "routine", "time_block": "pre_sleep"}

_TMP = Path(tempfile.mkdtemp(prefix="wellbeing-tests-"))
MODEL_PATH = _TMP / "model.joblib"


def setUpModule():
    bundle, card = train(generate(astronauts=15, mission_days=90, seed=3))
    save(bundle, card, MODEL_PATH)


def tearDownModule():
    shutil.rmtree(_TMP, ignore_errors=True)


class SoundscapeFileTests(SimpleTestCase):
    def test_every_scene_has_a_soundscape_file(self):
        from django.conf import settings

        folder = Path(settings.BASE_DIR) / "static" / "wellbeing" / "audio"
        for key in SCENE_KEYS:
            path = folder / f"{key}.mp3"
            self.assertTrue(path.exists(), f"missing soundscape for {key}")
            self.assertGreater(path.stat().st_size, 100_000)


class CatalogTests(SimpleTestCase):
    def test_phase_thresholds(self):
        self.assertEqual([mission_phase(d) for d in (1, 30, 31, 120, 121)],
                         ["adaptation", "adaptation", "routine", "routine", "late"])

    def test_gain_counts_mood_fully_and_stress_half(self):
        self.assertEqual(wellbeing_gain(2, 4, 4, 2), 3.0)

    def test_active_play_blocked_before_sleep(self):
        self.assertIsNotNone(blocked_reason("active", CONTEXT))
        self.assertIsNone(blocked_reason("active", {**CONTEXT, "time_block": "morning"}))


class SimulatorAndTrainingTests(SimpleTestCase):
    def test_generation_is_reproducible_and_complete(self):
        first, second = generate(astronauts=3, mission_days=30, seed=1), generate(astronauts=3, mission_days=30, seed=1)
        self.assertTrue(first.equals(second))
        self.assertTrue(set(first["scene"]) <= set(SCENE_KEYS))
        self.assertTrue(first[["mood", "mood_after", "stress_after", "enjoyment"]].isin(range(1, 6)).all().all())

    def test_oracle_columns_are_not_features(self):
        self.assertFalse(any(column.startswith("oracle_") or column == "gain" for column in FEATURE_COLUMNS))
        self.assertEqual(list(encode_all_scenes(CONTEXT).columns), list(FEATURE_COLUMNS))

    def test_saved_model_card_reports_policy_beating_random(self):
        card = load_bundle(MODEL_PATH)["card"]
        self.assertGreater(card["policy"]["expected_gain_model"], card["policy"]["expected_gain_random"])
        self.assertTrue((MODEL_PATH.parent / "model_card.json").exists())


class BanditTests(SimpleTestCase):
    def test_no_history_gives_prior(self):
        personal = personal_adjustments([])
        self.assertTrue(all(p.mean == 0 and p.sd == PRIOR_SD for p in personal.values()))

    def test_positive_residuals_raise_scene_and_shrink_uncertainty(self):
        personal = personal_adjustments([("nature", 1.0)] * 6, residual_sd=0.8)
        self.assertGreater(personal["nature"].mean, 0.3)
        self.assertLess(personal["nature"].sd, PRIOR_SD)
        self.assertEqual(personal["calm"].mean, 0)

    def test_blocked_scenes_rank_last(self):
        predictions = {key: 0.0 for key in SCENE_KEYS} | {"active": 5.0}
        ranked = rank_scenes(predictions, personal_adjustments([]), CONTEXT, explore=False)
        self.assertEqual(ranked[-1].key, "active")
        self.assertIsNotNone(ranked[-1].blocked)

    def test_personal_history_can_overturn_population_ranking(self):
        bundle = load_bundle(MODEL_PATH)
        base = recommend(bundle, CONTEXT, [], explore=False).recommended
        other = next(key for key in SCENE_KEYS if key not in (base, "active"))
        history = [(other, 2.5)] * 20 + [(base, -2.0)] * 20
        self.assertEqual(recommend(bundle, CONTEXT, history, explore=False).recommended, other)

    def test_duration_rules(self):
        self.assertEqual(recommend_duration("calm", CONTEXT), 15)
        self.assertEqual(recommend_duration("calm", {**CONTEXT, "energy": 4, "time_block": "evening"}), 25)
        self.assertEqual(recommend_duration("learning", {**CONTEXT, "energy": 4, "time_block": "work"}), 10)


@override_settings(WELLBEING_MODEL_PATH=MODEL_PATH)
class WorkflowViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("ast1", password="pw-12345-x")
        self.client = Client()
        self.client.force_login(self.user)

    def checkin(self, **overrides):
        data = {"mood": 2, "energy": 3, "stress": 4, "homesickness": 2, "sleep_hours": 6.5,
                "mission_day": 45, "time_block": "evening", **overrides}
        return self.client.post(reverse("wellbeing_checkin"), data)

    def test_full_cycle_records_outcome_and_residual(self):
        response = self.checkin()
        session = VRSession.objects.get()
        self.assertRedirects(response, reverse("wellbeing_session", args=[session.pk]))
        self.assertEqual(session.checkin.mission_phase, "routine")
        self.assertEqual(len(session.ranking), len(SCENE_KEYS))
        page = self.client.get(reverse("wellbeing_session", args=[session.pk]))
        self.assertContains(page, "Or choose another world")

        self.client.post(reverse("wellbeing_session_start", args=[session.pk]), {"scene": "nature", "minutes": 20})
        session.refresh_from_db()
        self.assertEqual((session.status, session.scene, session.planned_minutes), ("started", "nature", 20))
        self.assertIsNotNone(session.predicted_gain)
        player = self.client.get(reverse("wellbeing_session", args=[session.pk]))
        self.assertContains(player, "data-session-timer")
        # 3D world for the chosen scene, with the illustration kept as the no-WebGL fallback.
        self.assertContains(player, 'data-vr3d data-scene="nature"')
        self.assertContains(player, 'data-breathing="true"')
        self.assertContains(player, 'type="module" src="/static/wellbeing/vr3d.js"')
        self.assertContains(player, "wb-art-nature")
        # Soundscape for the chosen world, with an on/off toggle and volume control.
        self.assertContains(player, 'data-ambience="/static/wellbeing/audio/nature.mp3"')
        self.assertContains(player, "data-sound-toggle")
        self.assertContains(player, "data-sound-volume")
        self.assertContains(player, "wellbeing/ambience.js")

        self.client.post(reverse("wellbeing_session_end", args=[session.pk]))
        self.assertRedirects(self.client.get(reverse("wellbeing_session", args=[session.pk])),
                             reverse("wellbeing_recheck", args=[session.pk]))
        self.client.post(reverse("wellbeing_recheck", args=[session.pk]),
                         {"mood_after": 4, "energy_after": 3, "stress_after": 2, "enjoyment": 5})
        session.refresh_from_db()
        self.assertEqual(session.status, "rechecked")
        self.assertEqual(session.gain, 3.0)
        self.assertAlmostEqual(session.residual, 3.0 - session.predicted_gain)
        self.assertContains(self.client.get(reverse("home")), "Forest rain")

    def test_invalid_checkin_shows_errors(self):
        response = self.checkin(mood=9, sleep_hours=30)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(VRSession.objects.exists())

    def test_blocked_scene_cannot_be_started(self):
        self.checkin(time_block="pre_sleep")
        session = VRSession.objects.get()
        self.assertNotEqual(session.recommended_scene, "active")
        self.client.post(reverse("wellbeing_session_start", args=[session.pk]), {"scene": "active", "minutes": 20})
        session.refresh_from_db()
        self.assertEqual(session.status, "recommended")

    def test_sessions_are_private(self):
        self.checkin()
        session = VRSession.objects.get()
        other = get_user_model().objects.create_user("ast2", password="pw-12345-x")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("wellbeing_session", args=[session.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse("wellbeing_session_start", args=[session.pk]), {"scene": "calm", "minutes": 10}).status_code, 404)

    def test_skip_cancels_recommendation(self):
        self.checkin()
        session = VRSession.objects.get()
        self.client.post(reverse("wellbeing_session_skip", args=[session.pk]))
        session.refresh_from_db()
        self.assertEqual(session.status, "cancelled")

    def test_model_page_is_staff_only(self):
        self.assertEqual(self.client.get(reverse("wellbeing_model")).status_code, 302)
        self.user.is_staff = True
        self.user.save()
        self.assertContains(self.client.get(reverse("wellbeing_model")), "Achievable uplift")

    @override_settings(WELLBEING_MODEL_PATH=_TMP / "missing.joblib")
    def test_missing_model_is_explained(self):
        response = self.checkin()
        self.assertContains(response, "No trained recommender found")
        self.assertFalse(VRSession.objects.exists())

    def test_seeded_recommendation_is_deterministic(self):
        bundle = load_bundle(MODEL_PATH)
        picks = {recommend(bundle, CONTEXT, [], rng=np.random.default_rng(5)).recommended for _ in range(3)}
        self.assertEqual(len(picks), 1)


@override_settings(WELLBEING_MODEL_PATH=_TMP / "ui" / "model.joblib", WELLBEING_DATASET_PATH=_TMP / "ui" / "data.csv",
                   WELLBEING_UPLOAD_DIR=_TMP / "ui" / "uploads", WELLBEING_JOBS_SYNC=True)
class ModelManagementViewTests(TestCase):
    def setUp(self):
        from .models import TrainingJob

        self.TrainingJob = TrainingJob
        self.staff = get_user_model().objects.create_user("ops", password="pw-12345-x", is_staff=True)
        self.client = Client()
        self.client.force_login(self.staff)

    def generate(self, **overrides):
        data = {"astronauts": 12, "days": 90, "per_week": 3.5, "seed": 2, **overrides}
        return self.client.post(reverse("wellbeing_model_generate"), data)

    def test_generate_then_train_from_the_page(self):
        self.assertRedirects(self.generate(), reverse("wellbeing_model"))
        generate_job = self.TrainingJob.objects.get(kind="generate")
        self.assertEqual(generate_job.status, "succeeded", generate_job.error)
        self.assertTrue((_TMP / "ui" / "data.csv").exists())
        download = self.client.get(reverse("wellbeing_dataset_download"))
        self.assertEqual(download.status_code, 200)
        self.assertIn(b"astronaut_id", b"".join(download.streaming_content))

        self.client.post(reverse("wellbeing_model_train"), {"source": "dataset", "include_sessions": "on"})
        train_job = self.TrainingJob.objects.get(kind="train")
        self.assertEqual(train_job.status, "succeeded", train_job.error)
        self.assertTrue(train_job.result["version"].startswith("scene-rec-"))
        page = self.client.get(reverse("wellbeing_model"))
        self.assertContains(page, train_job.result["version"])
        self.assertContains(page, "Recent runs")

    def test_train_from_uploaded_csv(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        csv = generate(astronauts=8, mission_days=90, seed=4).drop(columns=[f"oracle_{k}" for k in SCENE_KEYS])
        upload = SimpleUploadedFile("pilot.csv", csv.to_csv(index=False).encode(), content_type="text/csv")
        self.client.post(reverse("wellbeing_model_train"), {"source": "upload", "upload": upload})
        job = self.TrainingJob.objects.get(kind="train")
        self.assertEqual(job.status, "succeeded", job.error)
        self.assertEqual(job.params["source"], "Upload: pilot.csv")
        self.assertNotIn("policy", job.result)  # no oracle columns in real-style data
        self.assertContains(self.client.get(reverse("wellbeing_model")), "Policy scores")

    def test_invalid_upload_is_rejected_with_reason(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("bad.csv", b"astronaut_id,mood\nA,3\n", content_type="text/csv")
        response = self.client.post(reverse("wellbeing_model_train"), {"source": "upload", "upload": upload})
        self.assertContains(response, "missing columns", status_code=400)
        self.assertFalse(self.TrainingJob.objects.exists())

    def test_generate_validates_ranges(self):
        response = self.generate(astronauts=1)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.TrainingJob.objects.exists())

    def test_only_one_job_at_a_time(self):
        self.TrainingJob.objects.create(kind="train", status="running", params={})
        self.generate()
        self.assertEqual(self.TrainingJob.objects.filter(kind="generate").count(), 0)

    def test_actions_are_staff_only(self):
        self.client.force_login(get_user_model().objects.create_user("crew", password="pw-12345-x"))
        self.assertEqual(self.generate().status_code, 302)
        self.assertEqual(self.client.get(reverse("wellbeing_dataset_download")).status_code, 302)
        self.assertFalse(self.TrainingJob.objects.exists())
