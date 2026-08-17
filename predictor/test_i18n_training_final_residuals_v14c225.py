from __future__ import annotations

from datetime import datetime

from django.test import SimpleTestCase
from django.utils.translation import override

from predictor.views import _format_training_chart_datetime
from student_satisfaction_project.i18n_residual_middleware import (
    translate_residual_text,
)


class TrainingFinalResidualsV14C225Tests(SimpleTestCase):
    def test_chart_datetime_english_afternoon(self):
        value = datetime(2026, 8, 16, 17, 4)

        self.assertEqual(
            _format_training_chart_datetime(value, "en"),
            "Aug 16, 2026, 5:04 PM",
        )

    def test_chart_datetime_english_morning(self):
        value = datetime(2026, 8, 17, 9, 5)

        self.assertEqual(
            _format_training_chart_datetime(value, "en-us"),
            "Aug 17, 2026, 9:05 AM",
        )

    def test_chart_datetime_french_unchanged(self):
        value = datetime(2026, 8, 16, 17, 4)

        self.assertEqual(
            _format_training_chart_datetime(value, "fr"),
            "2026-08-16 17:04",
        )

    def test_scikit_warning_is_fully_english(self):
        value = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer."
        )

        with override("en"):
            result = translate_residual_text(value)

        self.assertIn("Saved with scikit-learn 1.7.0", result)
        self.assertIn("current environment 1.9.0", result)
        self.assertIn("Retrain this model before", result)

        self.assertNotIn("Enregistré", result)
        self.assertNotIn("environnement actuel", result)
        self.assertNotIn("Réentraînez", result)

    def test_dot_joblib_variant_is_english(self):
        with override("en"):
            result = translate_residual_text(
                "Fichier .joblib introuvable."
            )

        self.assertEqual(
            result,
            "Missing .joblib file.",
        )

    def test_plain_joblib_variant_remains_english(self):
        with override("en"):
            result = translate_residual_text(
                "Fichier joblib introuvable."
            )

        self.assertNotIn("introuvable", result.lower())
        self.assertIn("joblib", result.lower())

    def test_dot_joblib_french_mode_is_unchanged(self):
        with override("fr"):
            result = translate_residual_text(
                "Fichier .joblib introuvable."
            )

        self.assertEqual(
            result,
            "Fichier .joblib introuvable.",
        )
