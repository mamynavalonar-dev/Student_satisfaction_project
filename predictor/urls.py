# predictor/urls.py
from django.urls import path

from . import views


urlpatterns = [
    path("", views.login_register_view, name="login_register"),
    path("dashboard/", views.home, name="home"),
    path("logout/", views.logout_view, name="logout"),

    path("predict/", views.predict, name="predict"),
    path("predict/batch/", views.batch_predict, name="batch_predict"),
    path(
        "predict/batch/download/<uuid:token>/",
        views.batch_predict_download,
        name="batch_predict_download",
    ),
    path("train/", views.train_model_view, name="train_model"),
    path("statistics/", views.statistics, name="statistics"),

    path("notifications/", views.notifications_feed, name="notifications_feed"),
    path("notifications/<int:pk>/read/", views.notification_mark_read, name="notification_mark_read"),
    path("notifications/read-all/", views.notifications_mark_all_read, name="notifications_mark_all_read"),

    path("data/", views.data_management, name="data_management"),
    path("data/<int:pk>/", views.feedback_detail, name="feedback_detail"),
    path("data/<int:pk>/edit/", views.feedback_update, name="feedback_update"),
    path("data/<int:pk>/delete/", views.feedback_delete, name="feedback_delete"),
    path("export/", views.export_data, name="export_data"),
]
