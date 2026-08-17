from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils.translation import override

from accounts.rbac import ensure_roles_and_permissions
from predictor.neural_network_model import _localized_artifact_reason


User = get_user_model()


class ArtifactSourceI18nV14C227Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def test_sklearn_reason_is_generated_directly_in_english(self):
        with override("en"):
            result = _localized_artifact_reason(
                "sklearn_version",
                saved="1.7.0",
                current="1.9.0",
            )

        self.assertEqual(
            result,
            "Saved with scikit-learn 1.7.0; "
            "current environment 1.9.0. "
            "Retrain this model before activation.",
        )

    def test_sklearn_reason_remains_french_in_french(self):
        with override("fr"):
            result = _localized_artifact_reason(
                "sklearn_version",
                saved="1.7.0",
                current="1.9.0",
            )

        self.assertEqual(
            result,
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer.",
        )

    def test_missing_joblib_is_generated_directly_in_english(self):
        with override("en"):
            self.assertEqual(
                _localized_artifact_reason("missing_joblib"),
                "Missing .joblib file.",
            )

    def test_required_course_types_are_in_template(self):
        from django.conf import settings

        path = (
            settings.BASE_DIR
            / "template"
            / "predictor"
            / "train.html"
        )
        source = path.read_text(encoding="utf-8")

        self.assertIn("V14C227_REQUIRED_COURSE_TYPES", source)
        self.assertIn(">In person</code>", source)
        self.assertIn(">Online</code>", source)
        self.assertIn(">Hybrid</code>", source)
        self.assertIn('data-csv-value="présentiel"', source)
        self.assertIn('data-csv-value="distanciel"', source)
        self.assertIn('data-csv-value="hybride"', source)

    def test_training_page_renders_english_course_labels(self):
        user = User.objects.create_superuser(
            username="v14c227-root",
            email="v14c227@example.com",
            password="V14C227!safe-pass",
        )
        self.client.force_login(user)

        self.client.post(
            reverse("set_language"),
            {
                "language": "en",
                "next": reverse("train_model"),
            },
        )

        response = self.client.get(reverse("train_model"))
        self.assertEqual(response.status_code, 200)

        source = response.content.decode(
            "utf-8",
            errors="replace",
        )

        self.assertIn(">In person</code>", source)
        self.assertIn(">Online</code>", source)
        self.assertIn(">Hybrid</code>", source)
