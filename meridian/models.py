from django.conf import settings
from django.db import models


class Astronaut(models.Model):
    id = models.CharField(primary_key=True, max_length=40)
    display_name = models.CharField(max_length=120)
    mission_role = models.CharField(max_length=60)
    baseline_start_day = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=30, default="active")
    origin_label = models.CharField(max_length=20, default="SYNTHETIC")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.id} · {self.display_name}"


ROLES = [(r, r.replace("_", " ").title()) for r in ("astronaut", "medical_officer", "flight_surgeon", "scientist", "rule_administrator")]


class MissionAccess(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mission_access")
    role = models.CharField(max_length=30, choices=ROLES)
    astronaut = models.ForeignKey(Astronaut, null=True, blank=True, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.CheckConstraint(condition=(models.Q(role="astronaut", astronaut__isnull=False) | (~models.Q(role="astronaut") & models.Q(astronaut__isnull=True))), name="mission_role_scope")]

    def __str__(self):
        return f"{self.user} · {self.role}"


class DemoAccount(models.Model):
    id = models.CharField(primary_key=True, max_length=40)
    display_name = models.CharField(max_length=120)
    role = models.CharField(max_length=30, choices=ROLES)
    astronaut = models.ForeignKey(Astronaut, null=True, blank=True, on_delete=models.PROTECT)


class Observation(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    astronaut = models.ForeignKey(Astronaut, on_delete=models.PROTECT, related_name="observations")
    mission_day = models.PositiveIntegerField()
    indicator_code = models.CharField(max_length=40)
    value = models.FloatField()
    unit = models.CharField(max_length=40)
    source_type = models.CharField(max_length=60)
    quality_flag = models.CharField(max_length=60, default="ok")
    quality_score = models.FloatField(default=1)
    accepted = models.BooleanField(default=True)
    exclusion_reason = models.CharField(max_length=240, blank=True)
    origin_label = models.CharField(max_length=20, default="SYNTHETIC")
    scenario_tag = models.CharField(max_length=80, blank=True)
    entered_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)

    class Meta:
        ordering = ["mission_day", "id"]
        indexes = [models.Index(fields=["astronaut", "mission_day", "indicator_code"])]


class Exposure(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    scope = models.CharField(max_length=40)
    exposure_type = models.CharField(max_length=60)
    start_day = models.PositiveIntegerField()
    end_day = models.PositiveIntegerField()
    magnitude = models.CharField(max_length=120, blank=True)
    unit = models.CharField(max_length=60, blank=True)
    source = models.CharField(max_length=120)
    origin_label = models.CharField(max_length=20, default="SYNTHETIC")
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["start_day", "id"]


class RuleVersion(models.Model):
    id = models.CharField(primary_key=True, max_length=80)
    parameters = models.JSONField()
    content_hash = models.CharField(max_length=64)
    placeholder = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Assessment(models.Model):
    astronaut = models.ForeignKey(Astronaut, on_delete=models.PROTECT)
    mission_day = models.PositiveIntegerField()
    rule = models.ForeignKey(RuleVersion, on_delete=models.PROTECT)
    domains = models.JSONField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["astronaut", "mission_day", "rule"], name="mission_assessment_version")]
        ordering = ["mission_day"]


class Finding(models.Model):
    astronaut = models.ForeignKey(Astronaut, on_delete=models.PROTECT)
    mission_day = models.PositiveIntegerField()
    domain = models.CharField(max_length=80)
    level = models.CharField(max_length=20)
    rule = models.ForeignKey(RuleVersion, on_delete=models.PROTECT)
    details = models.JSONField()
    status = models.CharField(max_length=20, default="open")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["astronaut", "mission_day", "domain", "rule"], name="mission_finding_version")]
        ordering = ["-mission_day", "id"]


class AlertAction(models.Model):
    client_id = models.UUIDField(unique=True)
    finding = models.ForeignKey(Finding, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    action = models.CharField(max_length=30)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class MissionCheckIn(models.Model):
    client_id = models.UUIDField(unique=True)
    astronaut = models.ForeignKey(Astronaut, on_delete=models.PROTECT)
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    mission_day = models.PositiveIntegerField()
    values = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)


class AuditEntry(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=120)
    action = models.CharField(max_length=80)
    scope = models.CharField(max_length=80, blank=True)
    payload = models.JSONField()
    previous_hash = models.CharField(max_length=64)
    content_hash = models.CharField(max_length=64)

    class Meta:
        ordering = ["id"]


class ImportReport(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=180)
    content_hash = models.CharField(max_length=64)
    report = models.JSONField()
