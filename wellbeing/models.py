from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .catalog import MISSION_PHASES, SCENES, SCENES_BY_KEY, TIME_BLOCKS, mission_phase, wellbeing_gain

SCALE = [MinValueValidator(1), MaxValueValidator(5)]
SCENE_CHOICES = [(scene.key, f"{scene.theme}: {scene.title}") for scene in SCENES]


class WellbeingCheckIn(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wellbeing_checkins")
    created_at = models.DateTimeField(auto_now_add=True)
    mission_day = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(1000)])
    mission_phase = models.CharField(max_length=20, choices=MISSION_PHASES, editable=False)
    time_block = models.CharField(max_length=20, choices=TIME_BLOCKS)
    mood = models.PositiveSmallIntegerField(validators=SCALE)
    energy = models.PositiveSmallIntegerField(validators=SCALE)
    stress = models.PositiveSmallIntegerField(validators=SCALE)
    homesickness = models.PositiveSmallIntegerField(validators=SCALE)
    sleep_hours = models.FloatField(validators=[MinValueValidator(0), MaxValueValidator(14)])

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        self.mission_phase = mission_phase(self.mission_day)
        super().save(*args, **kwargs)

    @property
    def phase_short(self) -> str:
        return self.get_mission_phase_display().split(" (")[0]

    def context(self) -> dict:
        return {
            "mood": self.mood, "energy": self.energy, "stress": self.stress,
            "homesickness": self.homesickness, "sleep_hours": float(self.sleep_hours),
            "mission_phase": self.mission_phase, "time_block": self.time_block,
        }

    def __str__(self):
        return f"{self.user} · mission day {self.mission_day}"


class VRSession(models.Model):
    RECOMMENDED, STARTED, ENDED, RECHECKED, CANCELLED = "recommended", "started", "ended", "rechecked", "cancelled"
    STATUSES = [(RECOMMENDED, "Recommended"), (STARTED, "In session"), (ENDED, "Awaiting re-check"),
                (RECHECKED, "Complete"), (CANCELLED, "Skipped")]

    checkin = models.OneToOneField(WellbeingCheckIn, on_delete=models.CASCADE, related_name="session")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="vr_sessions")
    status = models.CharField(max_length=20, choices=STATUSES, default=RECOMMENDED)

    # Adaptive engine output, frozen at recommendation time.
    model_version = models.CharField(max_length=60)
    recommended_scene = models.CharField(max_length=20, choices=SCENE_CHOICES)
    recommended_minutes = models.PositiveSmallIntegerField()
    exploring = models.BooleanField(default=False)
    ranking = models.JSONField(default=list)
    reasons = models.JSONField(default=list)

    # What the astronaut actually ran.
    scene = models.CharField(max_length=20, choices=SCENE_CHOICES, blank=True)
    predicted_gain = models.FloatField(null=True, blank=True)  # population prediction for `scene`
    planned_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    minutes_completed = models.FloatField(null=True, blank=True)

    # Re-check.
    mood_after = models.PositiveSmallIntegerField(null=True, blank=True, validators=SCALE)
    energy_after = models.PositiveSmallIntegerField(null=True, blank=True, validators=SCALE)
    stress_after = models.PositiveSmallIntegerField(null=True, blank=True, validators=SCALE)
    enjoyment = models.PositiveSmallIntegerField(null=True, blank=True, validators=SCALE)
    rechecked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-checkin__created_at"]

    @property
    def scene_info(self):
        return SCENES_BY_KEY.get(self.scene or self.recommended_scene)

    @property
    def recommended_info(self):
        return SCENES_BY_KEY[self.recommended_scene]

    @property
    def followed_recommendation(self):
        return self.scene == self.recommended_scene

    @property
    def gain(self):
        if self.mood_after is None or self.stress_after is None:
            return None
        return wellbeing_gain(self.checkin.mood, self.mood_after, self.checkin.stress, self.stress_after)

    @property
    def residual(self):
        gain = self.gain
        if gain is None or self.predicted_gain is None:
            return None
        return gain - self.predicted_gain

    @property
    def is_open(self):
        return self.status in (self.RECOMMENDED, self.STARTED, self.ENDED)

    def __str__(self):
        return f"{self.user} · {self.scene or self.recommended_scene} · {self.get_status_display()}"


class TrainingJob(models.Model):
    """A dataset-generation or model-training run started from the Model page."""
    GENERATE, TRAIN = "generate", "train"
    KINDS = [(GENERATE, "Generate dataset"), (TRAIN, "Train model")]
    QUEUED, RUNNING, SUCCEEDED, FAILED = "queued", "running", "succeeded", "failed"
    STATUSES = [(QUEUED, "Queued"), (RUNNING, "Running"), (SUCCEEDED, "Succeeded"), (FAILED, "Failed")]

    kind = models.CharField(max_length=20, choices=KINDS)
    status = models.CharField(max_length=20, choices=STATUSES, default=QUEUED)
    params = models.JSONField(default=dict)
    result = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_active(self):
        return self.status in (self.QUEUED, self.RUNNING)

    @property
    def duration_seconds(self):
        if self.started_at and self.finished_at:
            return round((self.finished_at - self.started_at).total_seconds())
        return None

    def __str__(self):
        return f"{self.get_kind_display()} · {self.get_status_display()}"
