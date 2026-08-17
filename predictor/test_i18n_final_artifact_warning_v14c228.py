from __future__ import annotations

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from student_satisfaction_project.i18n_final_artifact_middleware import (
    FinalEnglishArtifactWarningMiddleware,
    translate_final_artifact_warning,
)


class FinalArtifactWarningV14C228Tests(SimpleTestCase):
    def test_exact_warning_is_fully_english(self):
        source = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer."
        )

        self.assertEqual(
            translate_final_artifact_warning(source),
            "Saved with scikit-learn 1.7.0, "
            "current environment 1.9.0. "
            "Retrain this model before activation.",
        )

    def test_warning_with_html_entity_apostrophe_is_translated(self):
        source = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l&#x27;activer."
        )

        result = translate_final_artifact_warning(source)

        self.assertNotIn("Enregistré", result)
        self.assertNotIn("environnement actuel", result)
        self.assertNotIn("Réentraînez", result)
        self.assertIn(
            "Retrain this model before activation.",
            result,
        )

    def test_warning_split_by_whitespace_is_translated(self):
        source = (
            "Enregistré   avec   scikit-learn 1.7.0,\n"
            "environnement   actuel 1.9.0.\n"
            "Réentraînez ce modèle avant de l'activer."
        )

        result = translate_final_artifact_warning(source)

        self.assertIn(
            "Saved with scikit-learn 1.7.0",
            result,
        )
        self.assertIn(
            "current environment 1.9.0",
            result,
        )
        self.assertIn(
            "Retrain this model before activation.",
            result,
        )

    def test_english_response_is_modified(self):
        factory = RequestFactory()
        request = factory.get("/train/")
        request.LANGUAGE_CODE = "en"

        middleware = FinalEnglishArtifactWarningMiddleware(
            lambda _: HttpResponse(
                (
                    "Enregistré avec scikit-learn 1.7.0, "
                    "environnement actuel 1.9.0. "
                    "Réentraînez ce modèle avant de l'activer."
                ),
                content_type="text/html; charset=utf-8",
            )
        )

        response = middleware(request)
        source = response.content.decode("utf-8")

        self.assertNotIn("Enregistré", source)
        self.assertNotIn("Réentraînez", source)
        self.assertIn(
            "Saved with scikit-learn 1.7.0",
            source,
        )

    def test_french_response_is_not_modified(self):
        factory = RequestFactory()
        request = factory.get("/train/")
        request.LANGUAGE_CODE = "fr"

        original = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer."
        )

        middleware = FinalEnglishArtifactWarningMiddleware(
            lambda _: HttpResponse(
                original,
                content_type="text/html; charset=utf-8",
            )
        )

        response = middleware(request)

        self.assertEqual(
            response.content.decode("utf-8"),
            original,
        )
