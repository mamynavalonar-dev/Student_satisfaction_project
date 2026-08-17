from __future__ import annotations

import html
import re

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import translation

from accounts.rbac import ensure_roles_and_permissions
from student_satisfaction_project.i18n_residual_middleware import (
    EnglishResidualTranslationMiddleware,
    translate_residual_text,
)


User = get_user_model()


def visible_text(response):
    source = response.content.decode("utf-8", errors="replace")
    source = re.sub(
        r"<script\b.*?</script>",
        " ",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(
        r"<style\b.*?</style>",
        " ",
        source,
        flags=re.I | re.S,
    )
    source = re.sub(r"<[^>]+>", " ", source)
    source = html.unescape(source)
    return re.sub(r"\s+", " ", source).strip()


class FinalResidualMiddlewareV14C214Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def setUp(self):
        self.user = User.objects.create_superuser(
            username="lastmile-i18n-root",
            email="lastmile-i18n-root@example.com",
            password="Lastmile!I18n-2026x",
        )
        self.client.force_login(self.user)
        self.client.post(
            reverse("set_language"),
            {
                "language": "en",
                "next": reverse("train_model"),
            },
        )

    def test_training_full_structure_is_preserved(self):
        response = self.client.get(reverse("train_model"))
        self.assertEqual(response.status_code, 200)

        text = visible_text(response)

        for phrase in (
            "Model Training",
            "New Training",
            "Required Data Format",
            "Current Model Status",
            "Training History",
            "Model Management and Comparison",
            "Model Performance Over Time",
        ):
            self.assertIn(phrase, text)

    def test_training_known_residuals_are_translated(self):
        response = self.client.get(reverse("train_model"))
        text = visible_text(response)

        forbidden = (
            "Le fichier CSV doit contenir",
            "Sélection automatique",
            "Le CSV est d'abord séparé",
            "Entier",
            "Texte",
            "Binaire",
            "Aucun Modèle Chargé",
            "Aucun modèle n'est actuellement chargé",
            "Veuillez en entraîner",
            "Couches candidates",
            "Alpha candidat",
            "Aucun entraînement précédent",
            "Activation possible uniquement",
            "Aucun entraînement enregistré",
            "signifie qu'un ancien artefact",
            "Ce graphique compare la précision",
        )

        for phrase in forbidden:
            self.assertNotIn(phrase, text)

        for phrase in (
            "The CSV file must contain the columns:",
            "Automatic selection:",
            "The CSV is first split into 80% training / 20% final test.",
            "Integer",
            "Text",
            "Binary",
            "No Model Loaded",
            "No model is currently loaded.",
            "Candidate layers:",
            "Candidate alpha:",
            "No previous training",
            "Activation is only possible when the .joblib file exists",
            "No training run recorded.",
            "This chart compares successive training accuracies",
        ):
            self.assertIn(phrase, text)

    def test_training_javascript_residuals_are_translated(self):
        response = self.client.get(reverse("train_model"))
        source = response.content.decode("utf-8", errors="replace")

        for phrase in (
            "Training in progress...",
            "Training has started...",
            "Please select a CSV file.",
            "Model Accuracy (%)",
            "No evolution data available",
            "Error while parsing training-history data:",
        ):
            self.assertIn(phrase, source)

        for phrase in (
            "Training en cours...",
            "L'entraînement a commencé...",
            "Veuillez sélectionner un fichier au format CSV.",
            "Accuracy du Modèle (%)",
            "Aucune donnée d'évolution disponible",
        ):
            self.assertNotIn(phrase, source)

    def test_statistics_residual_translator_handles_actual_block(self):
        snippet = (
            'Cette mesure décrit ce que le '
            '<strong>MLP actif utilise pour prédire</strong>. '
            'Elle est différente des « Observed Associations » '
            'et ne constitue pas une preuve de causalité. '
            'Méthode : Importance par permutation · '
            'Référence : jeu de test enregistré avec le modèle.'
        )
        result = translate_residual_text(snippet)

        self.assertIn(
            "This measure describes what the",
            result,
        )
        self.assertIn(
            "active MLP uses for prediction",
            result,
        )
        self.assertIn(
            "It differs from “Observed Associations”",
            result,
        )
        self.assertIn("Method: Permutation importance", result)
        self.assertIn(
            "Reference: test set stored with the model.",
            result,
        )

    def test_javascript_escaped_apostrophe_is_translated(self):
        result = translate_residual_text(
            "Aucune donnée d\\'évolution disponible"
        )
        self.assertEqual(
            result,
            "No evolution data available",
        )

    def test_sklearn_version_does_not_duplicate_period(self):
        value = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraîner ce modèle avant de l'activer."
        )
        result = translate_residual_text(value)

        self.assertNotIn("1.9.0..", result)
        self.assertEqual(
            result,
            "Saved with scikit-learn 1.7.0; "
            "current environment 1.9.0. "
            "Retrain this model before activation.",
        )

    def test_historical_warning_is_display_translated(self):
        value = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraîner ce modèle avant de l'activer."
        )
        result = translate_residual_text(value)

        self.assertEqual(
            result,
            "Saved with scikit-learn 1.7.0; "
            "current environment 1.9.0. "
            "Retrain this model before activation.",
        )

    def test_login_toast_is_display_translated(self):
        result = translate_residual_text(
            "Connexion réussie. Bon retour, admindev."
        )
        self.assertEqual(
            result,
            "Login successful. Welcome back, admindev.",
        )

    def test_french_mode_is_untouched_by_middleware(self):
        self.client.post(
            reverse("set_language"),
            {
                "language": "fr",
                "next": reverse("train_model"),
            },
        )

        response = self.client.get(reverse("train_model"))
        text = visible_text(response)

        self.assertContains(response, 'lang="fr"')
        self.assertIn("Entraînement", text)

    def test_non_english_request_is_not_modified(self):
        factory = RequestFactory()
        request = factory.get("/test/")
        request.LANGUAGE_CODE = "fr"

        from django.http import HttpResponse

        middleware = EnglishResidualTranslationMiddleware(
            lambda _: HttpResponse(
                "Aucun Modèle Chargé",
                content_type="text/html; charset=utf-8",
            )
        )
        response = middleware(request)

        self.assertEqual(
            response.content.decode("utf-8"),
            "Aucun Modèle Chargé",
        )
