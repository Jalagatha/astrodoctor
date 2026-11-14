from django.contrib import admin
from .models import Astronaut, MissionAccess, RuleVersion


@admin.register(MissionAccess)
class AccessAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "astronaut"]
    list_filter = ["role"]


@admin.register(Astronaut)
class AstronautAdmin(admin.ModelAdmin):
    list_display = ["id", "display_name", "status", "origin_label"]


@admin.register(RuleVersion)
class RulesAdmin(admin.ModelAdmin):
    readonly_fields = ["id", "parameters", "content_hash", "placeholder", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
