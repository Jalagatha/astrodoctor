from django.contrib import admin

from .models import CheckIn, DailyRecord


@admin.register(DailyRecord)
class DailyRecordAdmin(admin.ModelAdmin):
    list_display = ("day", "resting_hr", "spo2", "sleep_h", "mood", "radiation_msv")
    ordering = ("day",)
    search_fields = ("=day",)


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ("day", "mood", "stress", "sleep_h", "created_at")
    ordering = ("-created_at",)
    readonly_fields = ("client_id", "created_at")

