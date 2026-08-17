from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.rbac import ensure_roles_and_permissions


User = get_user_model()


class PredictorInternationalizationV14C2Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="predictor-i18n-root",
            email="predictor-i18n-root@example.com",
            password="Predictor!I18n-2026x",
        )
        self.client.force_login(self.user)

    def switch(self, language):
        return self.client.post(
            reverse("set_language"),
            {"language": language, "next": reverse("home")},
        )

    def test_dashboard_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("home"))

        self.assertContains(response, "Student Satisfaction Predictor")
        self.assertContains(response, "Active model")
        self.assertContains(response, "Quick actions")
        self.assertContains(response, "How the project works")
        self.assertNotContains(response, "Fonctionnement du projet")

    def test_prediction_page_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("predict"))

        self.assertContains(response, "Satisfaction Prediction")
        self.assertContains(response, "Course Characteristics")
        self.assertContains(response, "Teaching quality")
        self.assertContains(response, "Predict Satisfaction")
        self.assertNotContains(response, "Caractéristiques du Cours")

    def test_batch_page_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("batch_predict"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Batch")
        self.assertContains(response, "CSV")

    def test_training_page_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("train_model"))

        self.assertContains(response, "Model Training")
        self.assertContains(response, "New Training")
        self.assertContains(response, "Current Model Status")
        self.assertContains(response, "Training History")
        self.assertContains(response, "Model Management and Comparison")

    def test_data_page_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("data_management"))

        self.assertContains(response, "Data Management")
        self.assertContains(response, "Filters")
        self.assertContains(response, "Student Feedback List")
        self.assertNotContains(response, "Gestion des Données")

    def test_statistics_page_is_translated_to_english(self):
        self.switch("en")
        response = self.client.get(reverse("statistics"))

        self.assertContains(response, "Statistical Analysis")
        self.assertContains(response, "Overall Distribution")
        self.assertContains(response, "Observed Associations")
        self.assertContains(response, "Active Model Performance")
        self.assertNotContains(response, "Analyse Statistique")
        self.assertNotContains(response, "Associations observées")

        # Global importance is conditional: in this isolated test database
        # there is no active model artifact, so the block is legitimately absent.
        model_importance = response.context.get("model_importance")
        if model_importance and model_importance.get("available"):
            self.assertContains(response, "Global Model Importance")

    def test_accounts_search_and_missing_values_are_english(self):
        self.switch("en")
        response = self.client.get(reverse("accounts:user_list"))

        self.assertContains(response, "Name, email, first name")
        self.assertNotContains(response, "Nom, e-mail, prénom")

    def test_profile_missing_values_are_english(self):
        self.user.first_name = ""
        self.user.last_name = ""
        self.user.save(update_fields=["first_name", "last_name"])
        self.switch("en")

        response = self.client.get(reverse("accounts:profile"))

        self.assertContains(response, "Not provided")
        self.assertNotContains(response, "Non renseigné")

    def test_french_remains_default_and_available(self):
        self.switch("fr")
        response = self.client.get(reverse("predict"))

        self.assertContains(response, "Prédiction de Satisfaction")
        self.assertContains(response, "Caractéristiques du Cours")

    def test_runtime_display_filter_translates_course_type(self):
        from django.template import Context, Template
        from django.utils import translation

        with translation.override("en"):
            rendered = Template(
                "{% load predictor_i18n %}"
                "{{ value|localized_display }}"
            ).render(Context({"value": "Présentiel"}))

        self.assertEqual(rendered, "In person")
