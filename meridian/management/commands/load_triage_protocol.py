import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from meridian.protocols import load_protocol


class Command(BaseCommand):
    help = "Load an immutable triage protocol version. Demo content is explicitly unapproved."

    def add_arguments(self, parser):
        parser.add_argument("file")
        parser.add_argument("--demonstration", action="store_true")
        parser.add_argument("--approved-by", default="")
        parser.add_argument("--approval-reference", default="")

    def handle(self, *args, **options):
        try:
            raw = json.loads(Path(options["file"]).read_text())
            protocol = load_protocol(raw["id"], raw["title"], raw["definition"], "load_triage_protocol", options["demonstration"], options["approved_by"], options["approval_reference"])
        except (ValueError, KeyError, TypeError, OSError) as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"Loaded {protocol.pk}: {'DEMONSTRATION — unapproved' if protocol.demonstration else 'supplied approval metadata recorded'}. Hash {protocol.content_hash}")
