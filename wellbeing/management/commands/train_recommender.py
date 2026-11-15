import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from wellbeing.jobs import train_and_save


class Command(BaseCommand):
    help = "Train and evaluate the scene-recommendation model, then save it for inference."

    def add_arguments(self, parser):
        parser.add_argument("--data", type=Path, default=None,
                            help="Training CSV (default: settings.WELLBEING_DATASET_PATH).")
        parser.add_argument("--output", type=Path, default=None, help="Model path (default: settings.WELLBEING_MODEL_PATH).")
        parser.add_argument("--include-sessions", action="store_true",
                            help="Also train on completed re-checks recorded in the database.")

    def handle(self, *args, **options):
        path = options["data"] or Path(settings.WELLBEING_DATASET_PATH)
        if not path.exists():
            raise CommandError(f"{path} not found. Run `python manage.py generate_wellbeing_data` first.")
        model_path = options["output"] or Path(settings.WELLBEING_MODEL_PATH)
        self.stdout.write(f"Training on {path} ...")
        try:
            card = train_and_save(path, options["include_sessions"], model_path)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc
        summary = {key: card[key] for key in ("data", "prediction", "policy", "personalisation_simulation") if key in card}
        self.stdout.write(json.dumps(summary, indent=2))
        self.stdout.write(self.style.SUCCESS(f"Saved {card['version']} to {model_path}"))
