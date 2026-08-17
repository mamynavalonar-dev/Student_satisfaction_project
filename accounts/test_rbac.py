from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase

from .rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_MODELS,
    CAP_STATISTICS,
    CAP_TRAIN,
    CAP_USERS,
    ROLE_ADMIN,
    ROLE_ANALYST,
    ROLE_ML_MANAGER,
    ROLE_SUPER_ADMIN,
    ROLE_USER,
    assign_role,
    ensure_roles_and_permissions,
    get_user_role,
    user_can,
)


User = get_user_model()


class RbacRoleV14B1Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def make_user(self, username, role):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Rbac!MotDePasse2026x",
        )
        assign_role(user, role)
        return user

    def test_roles_and_custom_permissions_are_initialized(self):
        from django.contrib.auth.models import Group

        names = set(
            Group.objects.filter(
                name__in=(
                    ROLE_ADMIN,
                    ROLE_ML_MANAGER,
                    ROLE_ANALYST,
                    ROLE_USER,
                )
            ).values_list("name", flat=True)
        )
        self.assertEqual(
            names,
            {ROLE_ADMIN, ROLE_ML_MANAGER, ROLE_ANALYST, ROLE_USER},
        )

        analyst = self.make_user("analyst-perms", ROLE_ANALYST)
        self.assertTrue(user_can(analyst, CAP_BATCH))
        self.assertTrue(user_can(analyst, CAP_STATISTICS))
        self.assertTrue(user_can(analyst, CAP_DATA))
        self.assertFalse(user_can(analyst, CAP_TRAIN))

    def test_superuser_is_always_super_administrator(self):
        user = User.objects.create_superuser(
            username="root-rbac",
            email="root-rbac@example.com",
            password="Root!MotDePasse2026x",
        )
        self.assertEqual(get_user_role(user), ROLE_SUPER_ADMIN)
        self.assertTrue(user_can(user, CAP_USERS))
        self.assertTrue(user_can(user, CAP_MODELS))

    def test_assigning_admin_role_sets_staff(self):
        user = self.make_user("admin-role", ROLE_ADMIN)
        user.refresh_from_db()
        self.assertTrue(user.is_staff)
        self.assertEqual(get_user_role(user), ROLE_ADMIN)

    def test_assigning_non_admin_role_removes_staff(self):
        user = self.make_user("demote-role", ROLE_ADMIN)
        assign_role(user, ROLE_ANALYST)
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertEqual(get_user_role(user), ROLE_ANALYST)

    def test_registered_account_receives_user_role(self):
        response = self.client.post(
            reverse("login_register"),
            {
                "form_type": "register",
                "register-username": "registered-rbac",
                "register-email": "registered-rbac@example.com",
                "register-password1": "Orbite!73-Quartz-Lune",
                "register-password2": "Orbite!73-Quartz-Lune",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        user = User.objects.get(username="registered-rbac")
        self.assertEqual(get_user_role(user), ROLE_USER)

    def test_user_role_cannot_open_training(self):
        user = self.make_user("simple-user", ROLE_USER)
        self.client.force_login(user)

        response = self.client.get(reverse("train_model"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Accès refusé", status_code=403)

    def test_analyst_can_open_statistics_but_not_training(self):
        user = self.make_user("analyst-web", ROLE_ANALYST)
        self.client.force_login(user)

        statistics = self.client.get(reverse("statistics"))
        training = self.client.get(reverse("train_model"))

        self.assertEqual(statistics.status_code, 200)
        self.assertEqual(training.status_code, 403)

    def test_ml_manager_can_open_training(self):
        user = self.make_user("ml-manager-web", ROLE_ML_MANAGER)
        self.client.force_login(user)

        response = self.client.get(reverse("train_model"))

        self.assertEqual(response.status_code, 200)

    def test_navigation_hides_privileged_links_for_user(self):
        user = self.make_user("nav-user", ROLE_USER)
        self.client.force_login(user)

        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'href="/train/"')
        self.assertNotContains(response, 'href="/data/"')
        self.assertNotContains(response, 'href="/statistics/"')
        self.assertContains(response, "Utilisateur")

    def test_admin_can_open_user_management(self):
        admin = self.make_user("app-admin", ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(reverse("accounts:user_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Gestion des utilisateurs")

    def test_regular_user_cannot_open_user_management(self):
        user = self.make_user("no-admin", ROLE_USER)
        self.client.force_login(user)

        response = self.client.get(reverse("accounts:user_list"))

        self.assertEqual(response.status_code, 403)

    def test_admin_can_create_an_analyst_account(self):
        admin = self.make_user("creator-admin", ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.post(
            reverse("accounts:user_create"),
            {
                "username": "new-analyst",
                "first_name": "New",
                "last_name": "Analyst",
                "email": "new-analyst@example.com",
                "role": ROLE_ANALYST,
                "is_active": "on",
                "password1": "Violet!83-Quartz-Lune",
                "password2": "Violet!83-Quartz-Lune",
            },
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        created = User.objects.get(username="new-analyst")
        self.assertEqual(get_user_role(created), ROLE_ANALYST)
        self.assertTrue(created.is_active)

    def test_admin_cannot_modify_superuser_from_application(self):
        admin = self.make_user("limited-admin", ROLE_ADMIN)
        root = User.objects.create_superuser(
            username="protected-root",
            email="protected-root@example.com",
            password="Protected!2026x",
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("accounts:user_role_edit", args=[root.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Super Administrateur ne peut pas être modifié")
        root.refresh_from_db()
        self.assertTrue(root.is_superuser)

    def test_admin_cannot_change_own_role(self):
        admin = self.make_user("self-admin", ROLE_ADMIN)
        self.client.force_login(admin)

        response = self.client.get(
            reverse("accounts:user_role_edit", args=[admin.pk]),
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "propre rôle")
        admin.refresh_from_db()
        self.assertEqual(get_user_role(admin), ROLE_ADMIN)


class RbacApiV14B1Tests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def make_user(self, username, role):
        user = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="ApiRbac!2026x",
        )
        assign_role(user, role)
        return user

    def valid_input(self):
        return {
            "qualite_enseignement": 7,
            "charge_travail": 4,
            "interactivite": 7,
            "type_cours": "présentiel",
            "niveau_etudiant": "M1",
        }

    def test_batch_api_denies_user_role(self):
        user = self.make_user("api-user-role", ROLE_USER)
        self.client.force_authenticate(user=user)

        response = self.client.post(
            reverse("api:predict_batch"),
            {"rows": [self.valid_input()]},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

    def test_batch_api_accepts_analyst_role(self):
        analyst = self.make_user("api-analyst-role", ROLE_ANALYST)
        self.client.force_authenticate(user=analyst)

        result_df = pd.DataFrame(
            [
                {
                    **self.valid_input(),
                    "predicted_satisfaction": 1,
                    "prediction_label": "Satisfait",
                    "probability_satisfied": 87.17,
                    "probability_unsatisfied": 12.83,
                    "confidence": 87.17,
                }
            ]
        )

        with (
            patch("api.views.load_current_model", return_value={"schema_version": 3}),
            patch("api.views.predict_satisfaction_batch", return_value=result_df),
        ):
            response = self.client.post(
                reverse("api:predict_batch"),
                {"rows": [self.valid_input()]},
                format="json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["summary"]["total"], 1)
