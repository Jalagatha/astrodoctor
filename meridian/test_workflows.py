import copy
import io
import json
import uuid
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .audit import verify
from .engine import replay
from .ingestion import import_workbook
from .models import (AuditEntry, Finding, FindingOverride, GroundPacket, GroundGuidance, GuidanceRead,
                     MissionAccess, TriageAnswer, TriageSession, TriageProtocol)
from .protocols import load_protocol, validate_protocol
from .views import overview_payload
from .workflows import (answer_triage, deliver_ground, display_level, read_guidance, save_override,
                        send_guidance, set_ground_link, start_triage, transition_triage)


class WorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        from health.models import DatasetLock
        DatasetLock.objects.get_or_create(pk=1)
        with (settings.BASE_DIR / "demo_data/Meridian_Synthetic_Dataset.xlsx").open("rb") as file:
            import_workbook(file)
        replay()
        cls.finding = Finding.objects.filter(astronaut_id="AST-01", mission_day=22, domain="Sleep").get()
        raw = json.loads((settings.BASE_DIR / "demo_data/triage_workflow_demo.json").read_text())
        cls.protocol = load_protocol(raw["id"], raw["title"], raw["definition"], "tests")
        User = get_user_model()
        cls.crew = User.objects.create_user("workflow-crew")
        cls.other = User.objects.create_user("workflow-other")
        cls.medical = User.objects.create_user("workflow-medical")
        cls.ground = User.objects.create_user("workflow-ground")
        cls.scientist = User.objects.create_user("workflow-scientist")
        for user, role, scope in [(cls.crew, "astronaut", "AST-01"), (cls.other, "astronaut", "AST-02"), (cls.medical, "medical_officer", None), (cls.ground, "flight_surgeon", None), (cls.scientist, "scientist", None)]:
            MissionAccess.objects.create(user=user, role=role, astronaut_id=scope)

    def test_override_preserves_assessment_updates_views_and_is_idempotent(self):
        key = uuid.uuid4()
        first = save_override(self.medical, self.finding.pk, key, "ATTENTION", "Review pending")
        again = save_override(self.medical, self.finding.pk, key, "ATTENTION", "Review pending")
        self.assertEqual(first.pk, again.pk)
        self.finding.refresh_from_db()
        self.assertEqual(self.finding.level, "OBSERVE")
        self.assertEqual(display_level(self.finding), "ATTENTION")
        result = overview_payload(self.crew, "AST-01", day=22)
        domain = next(d for d in result["domains"] if d["domain"] == "Sleep")
        self.assertEqual(domain["level"], "ATTENTION")
        self.assertEqual(domain["assessed_level"], "OBSERVE")
        self.assertEqual(GroundPacket.objects.filter(kind="override").count(), 1)
        self.assertTrue(verify()["passed"])

    def test_override_reason_permission_and_urgent_guard(self):
        with self.assertRaises(ValueError):
            save_override(self.medical, self.finding.pk, uuid.uuid4(), "NORMAL", " ")
        self.client.force_login(self.crew)
        url = reverse("mission_override", args=[self.finding.pk])
        data = {"client_id": uuid.uuid4(), "level": "NORMAL", "reason": "Attempt"}
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.client.force_login(self.ground)
        self.assertEqual(self.client.post(url, data).status_code, 403)
        self.finding.level = "URGENT"
        self.finding.save()
        with self.assertRaisesRegex(ValueError, "cannot be overridden"):
            save_override(self.medical, self.finding.pk, uuid.uuid4(), "NORMAL", "Attempt")
        self.assertFalse(FindingOverride.objects.exists())
        self.assertTrue(AuditEntry.objects.filter(action="urgent_override_refused").exists())

    def test_branch_pause_resume_finish_and_retry(self):
        key = uuid.uuid4()
        session = start_triage(self.crew, self.finding.pk, self.protocol.pk, key)
        self.assertEqual(start_triage(self.crew, self.finding.pk, self.protocol.pk, key).pk, session.pk)
        answer_key = uuid.uuid4()
        answer_triage(self.crew, session.pk, answer_key, "review", "pending")
        self.assertEqual(answer_triage(self.crew, session.pk, answer_key, "review", "pending").current_question, "followup")
        self.assertEqual(TriageAnswer.objects.count(), 1)
        transition_triage(self.crew, session.pk, "pause")
        with self.assertRaises(ValueError):
            answer_triage(self.crew, session.pk, uuid.uuid4(), "followup", "request_review")
        transition_triage(self.medical, session.pk, "resume")
        with self.assertRaises(ValueError):
            transition_triage(self.medical, session.pk, "finish")
        answer_triage(self.medical, session.pk, uuid.uuid4(), "followup", "request_review")
        completed = transition_triage(self.medical, session.pk, "finish")
        transition_triage(self.medical, session.pk, "finish")
        self.assertEqual(completed.status, "completed")
        summary = GroundPacket.objects.get(kind="triage_summary")
        self.assertEqual(len(summary.payload["answers"]), 2)
        self.assertTrue(summary.payload["demonstration"])
        self.assertEqual(summary.payload["protocol_hash"], self.protocol.content_hash)

    def test_stale_form_scope_and_invalid_answers(self):
        session = start_triage(self.crew, self.finding.pk, self.protocol.pk, uuid.uuid4())
        self.client.force_login(self.other)
        url = reverse("mission_triage_session", args=[session.pk])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.ground)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {"action": "pause"}).status_code, 403)
        with self.assertRaises(ValueError):
            answer_triage(self.crew, session.pk, uuid.uuid4(), "review", "unlisted")
        with self.assertRaises(ValueError):
            answer_triage(self.crew, session.pk, uuid.uuid4(), "followup", "request_review")
        answer_triage(self.crew, session.pk, uuid.uuid4(), "review", "reviewed")
        with self.assertRaises(ValueError):
            answer_triage(self.crew, session.pk, uuid.uuid4(), "review", "pending")

    def test_protocol_versions_are_immutable_and_hash_is_verified(self):
        changed = copy.deepcopy(self.protocol.definition)
        changed["questions"][0]["prompt"] = "Changed question"
        with self.assertRaisesRegex(ValueError, "immutable"):
            load_protocol(self.protocol.pk, self.protocol.title, changed, "tests")
        session = start_triage(self.crew, self.finding.pk, self.protocol.pk, uuid.uuid4())
        TriageProtocol.objects.filter(pk=self.protocol.pk).update(definition=changed)
        with self.assertRaisesRegex(ValueError, "integrity"):
            answer_triage(self.crew, session.pk, uuid.uuid4(), "review", "pending")

    def test_protocol_validation_rejects_cycles_unknown_branches_and_demo_urgent(self):
        for target in ("review", "missing"):
            changed = copy.deepcopy(self.protocol.definition)
            changed["questions"][0]["options"][0]["next"] = target
            with self.assertRaises(ValueError):
                validate_protocol(changed)
        changed = copy.deepcopy(self.protocol.definition)
        changed["questions"][0]["options"][0]["urgent"] = True
        with self.assertRaisesRegex(ValueError, "demonstration"):
            validate_protocol(changed)
        with self.assertRaisesRegex(ValueError, "approver"):
            load_protocol("reviewed-test", "Test only", self.protocol.definition, "tests", demonstration=False)

    def test_supplied_urgent_branch_pins_steps_and_queues_priority_packet(self):
        definition = {"questions": [{"code": "test", "prompt": "Test fixture only", "options": [{"value": "match", "label": "Match test fixture", "next": None, "urgent": True}]}], "emergency_steps": ["TEST FIXTURE: supplied instruction"]}
        protocol = load_protocol("test-only-reviewed", "Test fixture", definition, "tests", False, "Test reviewer", "TEST ONLY")
        session = start_triage(self.medical, self.finding.pk, protocol.pk, uuid.uuid4())
        answered = answer_triage(self.medical, session.pk, uuid.uuid4(), "test", "match")
        self.assertIsNotNone(answered.urgent_at)
        self.assertEqual(GroundPacket.objects.get(kind="triage_urgent").priority, 0)
        self.client.force_login(self.crew)
        response = self.client.get(reverse("mission_triage_session", args=[session.pk]))
        self.assertContains(response, "TEST FIXTURE: supplied instruction")

    def test_ground_offline_priority_and_idempotent_delivery(self):
        save_override(self.medical, self.finding.pk, uuid.uuid4(), "ATTENTION", "Review")
        with self.assertRaisesRegex(ValueError, "offline"):
            deliver_ground(self.medical)
        self.assertFalse(GroundPacket.objects.filter(delivered_at__isnull=False).exists())
        set_ground_link(self.medical, True)
        pending = list(GroundPacket.objects.order_by("priority", "id").values_list("pk", flat=True))
        self.assertEqual(deliver_ground(self.medical), len(pending))
        self.assertEqual(deliver_ground(self.medical), 0)
        actual = [entry.payload["packet"] for entry in AuditEntry.objects.filter(action="ground_packet_delivered")]
        self.assertEqual(actual, pending)

    def test_guidance_scope_receipts_and_measurements_are_unchanged(self):
        item = GroundPacket.objects.filter(astronaut_id="AST-01").first()
        self.client.force_login(self.ground)
        self.assertEqual(self.client.get(reverse("mission_ground_packet", args=[item.pk])).status_code, 404)
        set_ground_link(self.medical, True)
        deliver_ground(self.medical)
        before = Finding.objects.get(pk=self.finding.pk).level
        key = uuid.uuid4()
        guidance = send_guidance(self.ground, item.pk, key, "Synthetic review message")
        self.assertEqual(send_guidance(self.ground, item.pk, key, "Synthetic review message").pk, guidance.pk)
        self.assertEqual(Finding.objects.get(pk=self.finding.pk).level, before)
        self.client.force_login(self.other)
        self.assertNotContains(self.client.get(reverse("mission_guidance")), "Synthetic review message")
        self.assertEqual(self.client.post(reverse("mission_guidance_read", args=[guidance.pk])).status_code, 403)
        read_guidance(self.crew, guidance.pk)
        read_guidance(self.crew, guidance.pk)
        read_guidance(self.medical, guidance.pk)
        self.assertEqual(GuidanceRead.objects.count(), 2)
        with self.assertRaises(ValueError):
            send_guidance(self.ground, item.pk, key, "Changed content")

    def test_workflow_pages_render_for_expected_roles(self):
        self.client.force_login(self.medical)
        for name in ("mission_triage_list", "mission_ground", "mission_guidance"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertContains(self.client.get(reverse("mission_finding", args=[self.finding.pk])), "Medical-officer override")
        response = self.client.get(reverse("mission_triage_start", args=[self.finding.pk]))
        self.assertContains(response, "DEMONSTRATION ONLY")
        self.client.force_login(self.scientist)
        for name in ("mission_triage_list", "mission_ground", "mission_guidance"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403)
