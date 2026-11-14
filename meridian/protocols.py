"""Validated branching structure; medical content is supplied by protocol owners."""
import hashlib
import json

from django.db import transaction
from health.models import DatasetLock
from .audit import record
from .models import TriageProtocol


def protocol_hash(definition):
    return hashlib.sha256(json.dumps(definition, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_protocol(definition, demonstration=True):
    if not isinstance(definition, dict) or not isinstance(definition.get("questions"), list):
        raise ValueError("Protocol requires a questions list.")
    questions = definition["questions"]
    if not 1 <= len(questions) <= 50:
        raise ValueError("Protocol must contain 1 to 50 questions.")
    codes = []
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Each question must be an object.")
        code, prompt = question.get("code"), question.get("prompt")
        if not isinstance(code, str) or not code or len(code) > 80 or not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 2000:
            raise ValueError("Each question needs a code and prompt within the size limits.")
        if code in codes:
            raise ValueError("Question codes must be unique.")
        codes.append(code)
        options = question.get("options")
        if not isinstance(options, list) or not 1 <= len(options) <= 12:
            raise ValueError("Each question needs 1 to 12 answer options.")
        values = set()
        for option in options:
            if not isinstance(option, dict):
                raise ValueError("Answer options must be objects.")
            value, label = option.get("value"), option.get("label")
            if not isinstance(value, str) or not value or len(value) > 80 or value in values or not isinstance(label, str) or not label.strip() or len(label) > 240:
                raise ValueError("Options need unique values and nonempty labels within the size limits.")
            values.add(value)
            if not isinstance(option.get("urgent", False), bool):
                raise ValueError("Urgent flags must be booleans.")
            if option.get("urgent") and demonstration:
                raise ValueError("A demonstration checklist cannot define urgent medical criteria.")
    steps = definition.get("emergency_steps", [])
    if not isinstance(steps, list) or not all(isinstance(step, str) and step.strip() and len(step) <= 2000 for step in steps):
        raise ValueError("Emergency steps must be a list of text instructions.")
    graph = {}
    for question in questions:
        graph[question["code"]] = []
        for option in question["options"]:
            target = option.get("next")
            if target is not None and (not isinstance(target, str) or target not in codes):
                raise ValueError("Every next question must exist, or be null to finish.")
            if option.get("urgent") and not steps:
                raise ValueError("Urgent branches require supplied emergency protocol steps.")
            if target:
                graph[question["code"]].append(target)
    visited, active = set(), set()
    def visit(code):
        if code in active:
            raise ValueError("Protocol branches must terminate; cycles are not allowed.")
        if code in visited:
            return
        active.add(code)
        for target in graph[code]:
            visit(target)
        active.remove(code)
        visited.add(code)
    visit(codes[0])
    if len(visited) != len(codes):
        raise ValueError("All questions must be reachable from the first question.")


def load_protocol(identifier, title, definition, actor, demonstration=True, approved_by="", approval_reference=""):
    validate_protocol(definition, demonstration)
    if not demonstration and (not approved_by.strip() or not approval_reference.strip()):
        raise ValueError("A reviewed protocol requires an approver and approval reference.")
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        existing = TriageProtocol.objects.filter(pk=identifier).first()
        values = {"title": title, "definition": definition, "content_hash": protocol_hash(definition), "demonstration": demonstration,
                  "approved_by": approved_by, "approval_reference": approval_reference}
        if existing:
            if any(getattr(existing, key) != value for key, value in values.items()):
                raise ValueError("Protocol versions are immutable. Use a new version identifier.")
            return existing
        protocol = TriageProtocol(pk=identifier, **values)
        protocol.full_clean()
        protocol.save()
        record(actor, "protocol_loaded", payload={"version": identifier, "hash": protocol.content_hash, "demonstration": demonstration, "approved_by": approved_by, "approval_reference": approval_reference})
        return protocol
