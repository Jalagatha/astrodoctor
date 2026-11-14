import hashlib
import json

from django.db import transaction
from health.models import DatasetLock
from .models import AuditEntry


def digest(actor, action, scope, payload, previous_hash):
    return hashlib.sha256(json.dumps([actor, action, scope, payload, previous_hash], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def record(actor, action, scope="", payload=None):
    with transaction.atomic():
        DatasetLock.objects.select_for_update().get(pk=1)
        previous = AuditEntry.objects.order_by("-id").first()
        previous_hash = previous.content_hash if previous else "0" * 64
        actor = str(actor)
        payload = payload or {}
        return AuditEntry.objects.create(actor=actor, action=action, scope=scope, payload=payload, previous_hash=previous_hash, content_hash=digest(actor, action, scope, payload, previous_hash))


def verify():
    previous = "0" * 64
    count = 0
    for entry in AuditEntry.objects.iterator():
        if entry.previous_hash != previous or entry.content_hash != digest(entry.actor, entry.action, entry.scope, entry.payload, previous):
            return {"passed": False, "count": count, "first_break": entry.pk}
        previous = entry.content_hash
        count += 1
    return {"passed": True, "count": count, "first_break": None}
