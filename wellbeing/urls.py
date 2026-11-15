from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("wellbeing/check-in/", views.checkin, name="wellbeing_checkin"),
    path("wellbeing/session/<int:pk>/", views.session_detail, name="wellbeing_session"),
    path("wellbeing/session/<int:pk>/start/", views.session_start, name="wellbeing_session_start"),
    path("wellbeing/session/<int:pk>/end/", views.session_end, name="wellbeing_session_end"),
    path("wellbeing/session/<int:pk>/skip/", views.session_skip, name="wellbeing_session_skip"),
    path("wellbeing/session/<int:pk>/recheck/", views.recheck, name="wellbeing_recheck"),
    path("wellbeing/model/", views.model_card, name="wellbeing_model"),
    path("wellbeing/model/generate/", views.model_generate, name="wellbeing_model_generate"),
    path("wellbeing/model/train/", views.model_train, name="wellbeing_model_train"),
    path("wellbeing/model/dataset.csv", views.model_dataset_download, name="wellbeing_dataset_download"),
]
