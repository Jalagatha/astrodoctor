import uuid

from django.db import models


def crew_photo_path(instance, filename):
    return f"crew/{uuid.uuid4().hex}.jpg"


class CrewMember(models.Model):
    full_name = models.CharField(max_length=120)
    call_sign = models.CharField(max_length=40, blank=True)
    role = models.CharField(max_length=100)
    agency = models.CharField(max_length=100, blank=True)
    nationality = models.CharField(max_length=80, blank=True)
    mission = models.CharField(max_length=120)
    mission_start = models.DateField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(blank=True)
    biography = models.TextField(blank=True, max_length=2000)
    photo = models.ImageField(upload_to=crew_photo_path, blank=True)
    status = models.CharField(max_length=20, choices=[("active", "Active crew"), ("training", "In training"), ("returned", "Returned")], default="active")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["full_name", "pk"]

    def __str__(self):
        return self.full_name

    @property
    def initials(self):
        return "".join(part[0] for part in self.full_name.split()[:2]).upper()

    def mission_clock(self, today=None):
        """('day', n) once the mission has started, ('countdown', n) before launch, else None."""
        if not self.mission_start:
            return None
        from datetime import date

        delta = ((today or date.today()) - self.mission_start).days
        return ("day", delta + 1) if delta >= 0 else ("countdown", -delta)

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date

        today = date.today()
        born = self.date_of_birth
        return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class Developer(models.Model):
    slot = models.PositiveSmallIntegerField(unique=True)
    full_name = models.CharField(max_length=120)
    role = models.CharField(max_length=100)
    biography = models.TextField(max_length=1000, blank=True)
    email = models.EmailField(blank=True)
    github = models.URLField(blank=True)
    website = models.URLField(blank=True)
    photo = models.ImageField(upload_to=crew_photo_path, blank=True)

    class Meta:
        ordering = ["slot"]
        constraints = [models.CheckConstraint(condition=models.Q(slot__gte=1, slot__lte=5), name="developer_slot_1_to_5")]

    @property
    def initials(self):
        return "".join(part[0] for part in self.full_name.split()[:2]).upper()

    def __str__(self):
        return self.full_name


class UserProfile(models.Model):
    from django.conf import settings

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="personal_profile")
    display_name = models.CharField(max_length=120, blank=True)
    job_title = models.CharField("Role / title", max_length=100, blank=True)
    biography = models.TextField(max_length=2000, blank=True)
    photo = models.ImageField(upload_to=crew_photo_path, blank=True)

    @property
    def initials(self):
        name = self.display_name or self.user.get_full_name() or self.user.get_username()
        return "".join(part[0] for part in name.split()[:2]).upper()
