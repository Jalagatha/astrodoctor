from django.urls import path
from . import views, workflow_views

urlpatterns = [
    path("finding/<int:pk>/override/", workflow_views.override, name="mission_override"),
    path("finding/<int:pk>/triage/", workflow_views.triage_start, name="mission_triage_start"),
    path("triage/", workflow_views.triage_list, name="mission_triage_list"),
    path("triage/<int:pk>/", workflow_views.triage_session, name="mission_triage_session"),
    path("ground/", workflow_views.ground, name="mission_ground"),
    path("ground/<int:pk>/", workflow_views.ground_packet, name="mission_ground_packet"),
    path("guidance/", workflow_views.guidance, name="mission_guidance"),
    path("guidance/<int:pk>/read/", workflow_views.guidance_read, name="mission_guidance_read"),
    path("session/", views.session_identity, name="mission_session"),
    path("", views.home, name="mission_home"),
    path("import/", views.import_data, name="mission_import"),
    path("audit/", views.audit, name="mission_audit"),
    path("rules/", views.rules, name="mission_rules"),
    path("aggregate/", views.aggregate, name="mission_aggregate"),
    path("offline/", views.offline, name="mission_offline"),
    path("astronaut/<str:astronaut_id>/", views.overview, name="mission_overview"),
    path("astronaut/<str:astronaut_id>/alerts/", views.alerts, name="mission_alerts"),
    path("astronaut/<str:astronaut_id>/check-in/", views.check_in, name="mission_checkin"),
    path("finding/<int:pk>/", views.finding, name="mission_finding"),
    path("finding/<int:pk>/action/", views.finding_action, name="mission_action"),
]
