from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.demo import is_portfolio_demo_user
from accounts.rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_MODELS,
    CAP_PREDICT,
    CAP_STATISTICS,
    CAP_TRAIN,
    ROLE_ADMIN,
    ROLE_USER,
    assign_role,
    can_manage_target,
    get_user_role,
    user_can,
)
from predictor.models import ModelTraining, Notification, StudentFeedback
from predictor.neural_network_model import load_model_artifact


DEMO_USERNAME = "portfolio-demo-test"
DEMO_EMAIL = "portfolio-demo-test@example.invalid"
DEMO_PASSWORD = "Cobalt!73-Nebula-Lynx-2026"


@override_settings(
    PORTFOLIO_DEMO_ENABLED=True,
    PORTFOLIO_DEMO_USERNAME=DEMO_USERNAME,
    PORTFOLIO_DEMO_EMAIL=DEMO_EMAIL,
    PORTFOLIO_DEMO_PASSWORD=DEMO_PASSWORD,
    PORTFOLIO_MODEL_PATH="deployment/model/portfolio_model.joblib",
)
class PortfolioDemoV172Tests(TestCase):
    def make_user(self, username, role=ROLE_USER, *, email=None):
        User = get_user_model()
        user = User.objects.create_user(
            username=username,
            email=email or f"{username}@example.com",
            password="Standard!User-2026-Quartz",
        )
        assign_role(user, role)
        return user

    def test_packaged_model_exists_and_is_pipeline_v3_compatible(self):
        path = Path(settings.BASE_DIR) / settings.PORTFOLIO_MODEL_PATH
        self.assertTrue(path.is_file())

        model_data, resolved = load_model_artifact(
            settings.PORTFOLIO_MODEL_PATH
        )
        self.assertEqual(resolved.resolve(), path.resolve())
        self.assertEqual(model_data.get("schema_version"), 3)
        self.assertIn("pipeline", model_data)

    def test_demo_role_is_prediction_only(self):
        demo = self.make_user(DEMO_USERNAME, ROLE_USER, email=DEMO_EMAIL)

        self.assertTrue(is_portfolio_demo_user(demo))
        self.assertEqual(get_user_role(demo), ROLE_USER)
        self.assertTrue(user_can(demo, CAP_PREDICT))

        for capability in (
            CAP_BATCH,
            CAP_STATISTICS,
            CAP_DATA,
            CAP_TRAIN,
            CAP_MODELS,
        ):
            with self.subTest(capability=capability):
                self.assertFalse(user_can(demo, capability))

    def test_admin_cannot_mutate_demo_role_from_business_ui(self):
        admin = self.make_user("portfolio-admin", ROLE_ADMIN)
        demo = self.make_user(DEMO_USERNAME, ROLE_USER, email=DEMO_EMAIL)

        self.assertFalse(can_manage_target(admin, demo))

    def test_demo_cannot_edit_profile_or_change_password(self):
        demo = self.make_user(DEMO_USERNAME, ROLE_USER, email=DEMO_EMAIL)
        self.client.force_login(demo)

        profile_edit = self.client.get(reverse("accounts:profile_edit"))
        password_change = self.client.get(reverse("accounts:password_change"))

        self.assertEqual(profile_edit.status_code, 403)
        self.assertEqual(password_change.status_code, 403)

    @override_settings(
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend"
    )
    def test_demo_is_excluded_from_password_reset(self):
        self.make_user(DEMO_USERNAME, ROLE_USER, email=DEMO_EMAIL)

        response = self.client.post(
            reverse("accounts:password_reset"),
            {"email": DEMO_EMAIL},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)

    def test_demo_prediction_is_real_but_not_persisted(self):
        demo = self.make_user(DEMO_USERNAME, ROLE_USER, email=DEMO_EMAIL)
        self.client.force_login(demo)

        payload = {
            "qualite_enseignement": "7",
            "charge_travail": "4",
            "interactivite": "7",
            "type_cours": "présentiel",
            "niveau_etudiant": "M1",
        }
        result = {
            "prediction": 1,
            "probability_satisfied": 87.2,
            "probability_unsatisfied": 12.8,
            "satisfaction_text": "Satisfait",
            "prediction_probability": 87.2,
        }

        with (
            patch("predictor.views.load_current_model", return_value={"schema_version": 3}),
            patch("predictor.views.predict_satisfaction", return_value=result),
            patch("predictor.views.get_local_explanation", return_value=None),
        ):
            response = self.client.post(reverse("predict"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["prediction_result"], result)
        self.assertEqual(StudentFeedback.objects.count(), 0)
        self.assertEqual(Notification.objects.filter(user=demo).count(), 0)

    def test_normal_user_prediction_keeps_existing_persistence(self):
        user = self.make_user("normal-v172-user", ROLE_USER)
        self.client.force_login(user)

        payload = {
            "qualite_enseignement": "7",
            "charge_travail": "4",
            "interactivite": "7",
            "type_cours": "présentiel",
            "niveau_etudiant": "M1",
        }
        result = {
            "prediction": 1,
            "probability_satisfied": 87.2,
            "probability_unsatisfied": 12.8,
            "satisfaction_text": "Satisfait",
            "prediction_probability": 87.2,
        }

        with (
            patch("predictor.views.load_current_model", return_value={"schema_version": 3}),
            patch("predictor.views.predict_satisfaction", return_value=result),
            patch("predictor.views.get_local_explanation", return_value=None),
        ):
            response = self.client.post(reverse("predict"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(StudentFeedback.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(user=user).count(), 1)

    def test_bootstrap_command_is_idempotent_and_activates_packaged_model(self):
        call_command("bootstrap_portfolio")
        call_command("bootstrap_portfolio")

        User = get_user_model()
        demo = User.objects.get(username=DEMO_USERNAME)

        self.assertTrue(demo.check_password(DEMO_PASSWORD))
        self.assertFalse(demo.is_staff)
        self.assertFalse(demo.is_superuser)
        self.assertEqual(get_user_role(demo), ROLE_USER)
        self.assertTrue(is_portfolio_demo_user(demo))

        trainings = ModelTraining.objects.filter(
            model_file=settings.PORTFOLIO_MODEL_PATH
        )
        self.assertEqual(trainings.count(), 1)
        self.assertTrue(trainings.get().is_active)
        self.assertEqual(ModelTraining.objects.filter(is_active=True).count(), 1)
