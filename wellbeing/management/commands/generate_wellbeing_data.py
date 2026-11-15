from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from wellbeing.jobs import generate_dataset


class Command(BaseCommand):
    help = "Generate the synthetic check-in → VR scene → re-check training dataset."

    def add_arguments(self, parser):
        parser.add_argument("--astronauts", type=int, default=60)
        parser.add_argument("--days", type=int, default=180, help="Mission length in days.")
        parser.add_argument("--per-week", type=float, default=3.5, help="Average check-ins per week.")
        parser.add_argument("--seed", type=int, default=7)
        parser.add_argument("--output", type=Path, default=None,
                            help="CSV path (default: settings.WELLBEING_DATASET_PATH).")

    def handle(self, *args, **options):
        result = generate_dataset(options["output"] or settings.WELLBEING_DATASET_PATH, options["astronauts"],
                                  options["days"], options["per_week"], options["seed"])
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {result['rows']} sessions from {result['astronauts']} synthetic astronauts to {result['path']}"
        ))
