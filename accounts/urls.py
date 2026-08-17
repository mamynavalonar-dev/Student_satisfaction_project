from django.urls import path

from .views import (
    AccountPasswordChangeView,
    AccountPasswordResetCompleteView,
    AccountPasswordResetConfirmView,
    AccountPasswordResetDoneView,
    AccountPasswordResetView,
    ManagedUserCreateView,
    ProfileUpdateView,
    ProfileView,
    UserManagementView,
    UserRoleUpdateView,
)


app_name = "accounts"

urlpatterns = [
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/edit/", ProfileUpdateView.as_view(), name="profile_edit"),
    path("users/", UserManagementView.as_view(), name="user_list"),
    path("users/new/", ManagedUserCreateView.as_view(), name="user_create"),
    path(
        "users/<int:pk>/role/",
        UserRoleUpdateView.as_view(),
        name="user_role_edit",
    ),
    path(
        "password/change/",
        AccountPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "password/reset/",
        AccountPasswordResetView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        AccountPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/<uidb64>/<token>/",
        AccountPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        AccountPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
