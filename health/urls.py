from django.urls import path

from . import views

urlpatterns = [
    path("dataset/train/", views.dataset_training, name="dataset_training"),
    path("accounts/profile/", views.my_profile, name="my_profile"),
    path("accounts/profile/photo/", views.my_profile_photo, name="my_profile_photo"),
    path("developers/", views.developer_team, name="developer_team"),
    path("developers/<int:slot>/edit/", views.developer_edit, name="developer_edit"),
    path("developers/<int:slot>/photo/", views.developer_photo, name="developer_photo"),
    path("crew/", views.crew_list, name="crew_list"),
    path("crew/new/", views.crew_edit, name="crew_create"),
    path("crew/<int:pk>/", views.crew_detail, name="crew_detail"),
    path("crew/<int:pk>/edit/", views.crew_edit, name="crew_edit"),
    path("crew/<int:pk>/photo/", views.crew_photo, name="crew_photo"),
    path("", views.dashboard, name="dashboard"),
    path("import/", views.import_data, name="import_data"),
    path("demo/", views.load_demo, name="load_demo"),
    path("check-in/", views.check_in, name="check_in"),
    path("manifest.webmanifest", views.manifest, name="manifest"),
    path("service-worker.js", views.service_worker, name="service_worker"),
    path("offline/", views.offline, name="offline"),
]
