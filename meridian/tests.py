import io
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from .audit import verify
from .engine import replay
from .ingestion import import_workbook
from .models import Assessment, Astronaut, AuditEntry, DemoAccount, Exposure, Finding, MissionAccess, MissionCheckIn, Observation

WORKBOOK = Path(settings.BASE_DIR) / "demo_data/Meridian_Synthetic_Dataset.xlsx"


class MeridianTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from health.models import DatasetLock
        DatasetLock.objects.get_or_create(pk=1)
        with WORKBOOK.open("rb") as file:
            cls.report = import_workbook(file)
        replay()
        User = get_user_model()
        cls.crew_a = User.objects.create_user(username="astronaut-a")
        cls.crew_b = User.objects.create_user(username="astronaut-b")
        cls.medical = User.objects.create_user(username="medical")
        cls.scientist = User.objects.create_user(username="scientist")
        cls.rule_admin = User.objects.create_user(username="rule-admin")
        cls.ground = User.objects.create_user(username="ground")
        cls.staff = User.objects.create_user(username="staff-only", is_staff=True)
        for user, role, astronaut in [(cls.crew_a, "astronaut", "AST-01"), (cls.crew_b, "astronaut", "AST-02"), (cls.medical, "medical_officer", None), (cls.scientist, "scientist", None), (cls.rule_admin, "rule_administrator", None), (cls.ground, "flight_surgeon", None)]:
            MissionAccess.objects.create(user=user, role=role, astronaut_id=astronaut)

    def test_workbook_counts_and_quality(self):
        self.assertEqual(Astronaut.objects.count(), 3)
        self.assertEqual(DemoAccount.objects.count(), 7)
        self.assertEqual(Observation.objects.count(), 442)
        self.assertEqual(Exposure.objects.count(), 4)
        self.assertEqual(self.report.report["rejected"], [])
        self.assertEqual(Observation.objects.filter(accepted=False).count(), 1)
        self.assertEqual(Assessment.objects.count(), 90)

    def test_documented_scenarios(self):
        result = Assessment.objects.get(astronaut_id="AST-01", mission_day=22)
        self.assertEqual([d["level"] for d in result.domains[:2]], ["OBSERVE", "OBSERVE"])
        for domain in result.domains[:2]:
            self.assertTrue(domain["links"])
            self.assertTrue(all(link["evidence_tag"] == "hypothesized" for link in domain["links"]))
            self.assertTrue(all(link["exposure_id"] in {"EXP-001", "EXP-002"} for link in domain["links"]))
            for metric in domain["metrics"]:
                self.assertTrue(all(day < 22 for day in metric["baseline_days"]))
        for day in range(10, 14):
            gap = Assessment.objects.get(astronaut_id="AST-02", mission_day=day)
            self.assertEqual([d["level"] for d in gap.domains[:2]], ["UNKNOWN", "UNKNOWN"])
            self.assertEqual(gap.domains[0]["metrics"][0]["data_age"], day - 9)
        self.assertFalse(Finding.objects.filter(astronaut_id="AST-03", mission_day=15).exists())
        extreme = Observation.objects.get(astronaut_id="AST-03", mission_day=15, indicator_code="resting_hr")
        self.assertFalse(extreme.accepted)
        next_day = Assessment.objects.get(astronaut_id="AST-03", mission_day=16)
        self.assertNotIn(15, next_day.domains[0]["metrics"][0]["baseline_days"])

    def test_reimport_is_idempotent_and_conflicts_keep_original(self):
        with WORKBOOK.open("rb") as file:
            report = import_workbook(file)
        self.assertEqual(report.report["counts"]["observations_daily"]["unchanged"], 442)
        self.assertEqual(replay(), 0)
        original = Observation.objects.get(pk="OBS-00001").value
        book = load_workbook(WORKBOOK)
        book["observations_daily"]["E2"] = 75
        output = io.BytesIO(); book.save(output); output.seek(0)
        report = import_workbook(output)
        self.assertEqual(report.report["counts"]["observations_daily"]["rejected"], 1)
        self.assertEqual(Observation.objects.get(pk="OBS-00001").value, original)

    def test_scoped_views_and_scientist_summary(self):
        self.client.force_login(self.crew_a)
        own = reverse("mission_overview", args=["AST-01"])
        self.assertContains(self.client.get(own + "?day=22"), "mission-snapshot")
        self.assertEqual(self.client.get(reverse("mission_overview", args=["AST-02"])).status_code, 403)
        self.assertTrue(AuditEntry.objects.filter(action="access_denied").exists())
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(own).status_code, 403)
        self.client.force_login(self.scientist)
        response = self.client.get(reverse("mission_aggregate"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "AST-01")
        self.assertNotContains(response, "Demo Astronaut A")
        self.assertEqual(self.client.get(own).status_code, 403)

    def test_finding_actions_require_reason_scope_and_idempotency(self):
        finding = Finding.objects.filter(astronaut_id="AST-01", mission_day=22).first()
        url = reverse("mission_action", args=[finding.pk])
        self.client.force_login(self.crew_a)
        payload = {"client_id": str(uuid.uuid4()), "action": "dismiss", "reason": ""}
        self.assertEqual(self.client.post(url, json.dumps(payload), content_type="application/json").status_code, 400)
        payload["reason"] = "Reviewed synthetic scenario"
        self.assertTrue(self.client.post(url, json.dumps(payload), content_type="application/json").json()["created"])
        self.assertFalse(self.client.post(url, json.dumps(payload), content_type="application/json").json()["created"])
        finding.refresh_from_db()
        self.assertEqual(finding.level, "OBSERVE")
        self.assertEqual(finding.status, "dismissed")
        self.client.force_login(self.ground)
        self.assertEqual(self.client.post(url, json.dumps(payload), content_type="application/json").status_code, 403)
        self.client.force_login(self.crew_b)
        self.assertEqual(self.client.get(reverse("mission_finding", args=[finding.pk])).status_code, 403)

    def test_checkin_keeps_missing_wearables_and_retries_idempotently(self):
        self.client.force_login(self.crew_a)
        payload = {"client_id": str(uuid.uuid4()), "mission_day": 31, "sleep_quality": 3, "fatigue_score": 2, "mood_score": 4, "workload_score": 3}
        url = reverse("mission_checkin", args=["AST-01"])
        response = self.client.post(url, json.dumps(payload), content_type="application/json")
        self.assertEqual(response.status_code, 200, response.content)
        self.assertFalse(self.client.post(url, json.dumps(payload), content_type="application/json").json()["created"])
        self.assertEqual(MissionCheckIn.objects.count(), 1)
        self.assertEqual(Observation.objects.filter(astronaut_id="AST-01", mission_day=31).count(), 4)
        result = Assessment.objects.get(astronaut_id="AST-01", mission_day=31)
        self.assertEqual(result.domains[0]["level"], "UNKNOWN")
        self.assertEqual(result.domains[1]["level"], "UNKNOWN")

    def test_audit_detects_change_and_role_pages_render(self):
        self.assertTrue(verify()["passed"])
        AuditEntry.objects.filter(pk=AuditEntry.objects.first().pk).update(payload={"changed": True})
        self.assertFalse(verify()["passed"])
        for user, pages in [(self.medical, ["mission_home", "mission_audit", "mission_rules"]), (self.rule_admin, ["mission_import", "mission_rules"]), (self.ground, ["mission_home"])]:
            self.client.force_login(user)
            for page in pages:
                self.assertEqual(self.client.get(reverse(page)).status_code, 200)
        self.client.force_login(self.crew_a)
        self.assertEqual(self.client.get(reverse("mission_import")).status_code, 403)
        self.assertEqual(self.client.get(reverse("dashboard")).url, reverse("mission_home"))

    def test_bad_ranges_return_400_and_anonymous_access_redirects(self):
        self.client.force_login(self.crew_a)
        for query in ("?day=nan", "?days=900", "?day=-1"):
            self.assertEqual(self.client.get(reverse("mission_overview", args=["AST-01"]) + query).status_code, 400)
        self.client.logout()
        self.assertEqual(self.client.get(reverse("mission_home")).status_code, 302)
        self.assertEqual(self.client.get(reverse("mission_offline")).status_code, 200)
