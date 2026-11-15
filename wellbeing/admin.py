from django.contrib import admin

from .models import TrainingJob, VRSession, WellbeingCheckIn


@admin.register(WellbeingCheckIn)
class WellbeingCheckInAdmin(admin.ModelAdmin):
    list_display = ("user", "mission_day", "mission_phase", "time_block", "mood", "energy", "stress", "homesickness", "sleep_hours", "created_at")
    list_filter = ("mission_phase", "time_block")


@admin.register(VRSession)
class VRSessionAdmin(admin.ModelAdmin):
    list_display = ("user", "recommended_scene", "scene", "status", "exploring", "planned_minutes", "mood_after", "model_version")
    list_filter = ("status", "scene", "exploring")
    readonly_fields = ("ranking", "reasons", "model_version")


@admin.register(TrainingJob)
class TrainingJobAdmin(admin.ModelAdmin):
    list_display = ("kind", "status", "created_by", "created_at", "finished_at")
    list_filter = ("kind", "status")
    readonly_fields = ("params", "result", "error")
