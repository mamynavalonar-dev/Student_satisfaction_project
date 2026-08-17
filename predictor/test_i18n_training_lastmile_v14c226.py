from __future__ import annotations

from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.rbac import ensure_roles_and_permissions
from student_satisfaction_project.i18n_training_lastmile import (
    TrainingEnglishLastMileMiddleware,
    translate_training_lastmile_html,
)


User = get_user_model()


class TrainingLastMileV14C226UnitTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def test_exact_scikit_warning_is_english(self):
        source = (
            "Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer."
        )

        self.assertEqual(
            translate_training_lastmile_html(source),
            "Saved with scikit-learn 1.7.0; "
            "current environment 1.9.0. "
            "Retrain this model before activation.",
        )

    def test_required_course_types_are_visibly_english(self):
        source = (
            "<td>"
            "<code>présentiel</code>, "
            "<code>distanciel</code>, "
            "<code>hybride</code>"
            "</td>"
        )

        result = translate_training_lastmile_html(source)

        self.assertIn(
            '>In person</code>',
            result,
        )
        self.assertIn(
            '>Online</code>',
            result,
        )
        self.assertIn(
            '>Hybrid</code>',
            result,
        )

        self.assertIn(
            'data-csv-value="présentiel"',
            result,
        )
        self.assertIn(
            'data-csv-value="distanciel"',
            result,
        )
        self.assertIn(
            'data-csv-value="hybride"',
            result,
        )

    def test_french_http_response_is_not_modified(self):
        factory = RequestFactory()
        request = factory.get("/train/")
        request.LANGUAGE_CODE = "fr"

        original = (
            "<code>présentiel</code>, "
            "<code>distanciel</code>, "
            "<code>hybride</code>"
        )

        middleware = TrainingEnglishLastMileMiddleware(
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


class TrainingLastMileV14C226IntegrationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()
        cls.user = User.objects.create_superuser(
            username="v14c226-root",
            email="v14c226@example.com",
            password="V14C226!safe-pass",
        )

    def setUp(self):
        self.client.force_login(self.user)
        self.client.post(
            reverse("set_language"),
            {
                "language": "en",
                "next": reverse("train_model"),
            },
        )

    def test_required_data_format_course_types_render_in_english(self):
        response = self.client.get(
            reverse("train_model")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        source = response.content.decode(
            "utf-8",
            errors="replace",
        )

        self.assertIn(
            'data-csv-value="présentiel">In person</code>',
            source,
        )
        self.assertIn(
            'data-csv-value="distanciel">Online</code>',
            source,
        )
        self.assertIn(
            'data-csv-value="hybride">Hybrid</code>',
            source,
        )

        self.assertNotIn(
            "<code>présentiel</code>, "
            "<code>distanciel</code>, "
            "<code>hybride</code>",
            source,
        )
