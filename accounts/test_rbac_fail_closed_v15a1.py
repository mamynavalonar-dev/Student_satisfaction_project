from __future__ import annotations

from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .api_permissions import (
    CanUseBatchPrediction,
    CanViewFeedbackData,
    CanViewModelManagement,
)
from .rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_EXPORT,
    CAP_MODELS,
    CAP_ROLES,
    CAP_STATISTICS,
    CAP_TRAIN,
    CAP_USERS,
    ensure_roles_and_permissions,
    has_explicit_managed_role,
    user_can,
)


User = get_user_model()


class RbacFailClosedV15A1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def make_ungrouped_user(self, suffix):
        user = User.objects.create_user(
            username=f"v15a1-{suffix}",
            email=f"v15a1-{suffix}@example.com",
            password="V15A1!FailClosed-2026",
        )
        user.groups.clear()
        user.user_permissions.clear()

        for attr in (
            "_perm_cache",
            "_user_perm_cache",
            "_group_perm_cache",
        ):
            if hasattr(user, attr):
                delattr(user, attr)

        user.refresh_from_db()
        return user

    def test_ungrouped_account_has_no_managed_role(self):
        user = self.make_ungrouped_user("role")
        self.assertFalse(has_explicit_managed_role(user))

    def test_ungrouped_account_has_no_privileged_capability(self):
        user = self.make_ungrouped_user("caps")

        for capability in (
            CAP_BATCH,
            CAP_STATISTICS,
            CAP_DATA,
            CAP_EXPORT,
            CAP_TRAIN,
            CAP_MODELS,
            CAP_USERS,
            CAP_ROLES,
        ):
            with self.subTest(capability=capability):
                self.assertFalse(user_can(user, capability))

    def test_ungrouped_account_fails_closed_on_web_routes(self):
        user = self.make_ungrouped_user("web")
        self.client.force_login(user)

        for url_name in (
            "batch_predict",
            "statistics",
            "data_management",
            "train_model",
        ):
            with self.subTest(url_name=url_name):
                response = self.client.get(reverse(url_name))
                self.assertEqual(response.status_code, 403)

    def test_ungrouped_account_can_still_open_home(self):
        user = self.make_ungrouped_user("home")
        self.client.force_login(user)

        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)

    def test_ungrouped_account_fails_closed_in_api_permissions(self):
        user = self.make_ungrouped_user("api")
        request = SimpleNamespace(user=user)

        for permission in (
            CanUseBatchPrediction(),
            CanViewModelManagement(),
            CanViewFeedbackData(),
        ):
            with self.subTest(
                permission=permission.__class__.__name__
            ):
                self.assertFalse(
                    permission.has_permission(request, None)
                )

    def test_superuser_still_has_privileged_capabilities(self):
        root = User.objects.create_superuser(
            username="v15a1-root",
            email="v15a1-root@example.com",
            password="V15A1!Root-2026",
        )

        for capability in (
            CAP_BATCH,
            CAP_STATISTICS,
            CAP_DATA,
            CAP_EXPORT,
            CAP_TRAIN,
            CAP_MODELS,
            CAP_USERS,
            CAP_ROLES,
        ):
            with self.subTest(capability=capability):
                self.assertTrue(user_can(root, capability))
