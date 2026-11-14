import secrets
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from meridian.engine import replay
from meridian.ingestion import import_workbook
from meridian.models import DemoAccount, MissionAccess


class Command(BaseCommand):
    help = "Import the synthetic Meridian workbook, replay assessments, optionally create local demo accounts."

    def add_arguments(self, parser):
        parser.add_argument("--workbook", default=str(settings.BASE_DIR / "demo_data/Meridian_Synthetic_Dataset.xlsx"))
        parser.add_argument("--demo-accounts", action="store_true")

    def handle(self, *args, **options):
        try:
            with Path(options["workbook"]).open("rb") as source:
                result = import_workbook(source, "seed_meridian")
        except (OSError, ValueError) as exc:
            raise CommandError(str(exc))
        count = replay()
        for sheet, counts in result.report["counts"].items():
            self.stdout.write(f"{sheet}: {counts}")
        self.stdout.write(f"Excluded quality observations: {result.report['excluded_observations']}; new findings: {count}")
        for rejection in result.report["rejected"]:
            self.stderr.write(str(rejection))
        if options["demo_accounts"]:
            if not settings.DEBUG:
                raise CommandError("Demo account creation is restricted to DEBUG development settings.")
            User = get_user_model()
            for definition in DemoAccount.objects.all():
                if User.objects.filter(username=definition.pk).exists():
                    self.stdout.write(f"{definition.pk}: existing account left unchanged; assign scope explicitly in admin if needed.")
                    continue
                password = secrets.token_urlsafe(16)
                user = User.objects.create_user(username=definition.pk, password=password, first_name=definition.display_name)
                MissionAccess.objects.create(user=user, role=definition.role, astronaut=definition.astronaut)
                self.stdout.write(f"DEMO ONLY username={user.username} password={password} role={definition.role}")
