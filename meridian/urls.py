from django.urls import path
from . import views

urlpatterns = [
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
