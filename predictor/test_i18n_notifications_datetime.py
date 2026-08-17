from __future__ import annotations

import json

from django.contrib.auth import get_user_model
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, TestCase
from django.urls import reverse

from accounts.rbac import ensure_roles_and_permissions
from student_satisfaction_project.i18n_residual_middleware import (
    EnglishResidualTranslationMiddleware,
    translate_residual_text,
    translate_visible_html_datetimes,
)


User = get_user_model()


class NotificationAndDateI18nV14C216Tests(TestCase):
    @classmethod
    def setUpTestData(cls):
        ensure_roles_and_permissions()

    def test_login_notification_is_english(self):
        self.assertEqual(
            translate_residual_text("Connexion réussie"),
            "Login successful",
        )
        self.assertEqual(
            translate_residual_text(
                "Bienvenue admindev. Votre session est active."
            ),
            "Welcome admindev. Your session is active.",
        )

    def test_training_notification_is_english(self):
        value = (
            "Entraînement #20 terminé : Accuracy test 70.75%, "
            "F1 test 66.28%, F1 CV 65.38% ± 1.63%, "
            "2000 échantillons."
        )
        result = translate_residual_text(value)

        self.assertEqual(
            result,
            "Training #20 completed: test accuracy 70.75%, "
            "test F1 66.28%, CV F1 65.38% ± 1.63%, "
            "2,000 samples.",
        )

    def test_prediction_notification_is_english(self):
        self.assertEqual(
            translate_residual_text("Nouvelle prédiction"),
            "New prediction",
        )
        self.assertEqual(
            translate_residual_text(
                "Avis #28 : Satisfait (87.2% de confiance)."
            ),
            "Feedback #28: Satisfied (87.2% confidence).",
        )
        self.assertEqual(
            translate_residual_text(
                "Avis #29 : Non satisfait (91.4% de confiance)."
            ),
            "Feedback #29: Dissatisfied (91.4% confidence).",
        )

    def test_french_datetime_is_rendered_with_english_clock(self):
        self.assertEqual(
            translate_visible_html_datetimes(
                "<td>16/08/2026 16:30</td>"
            ),
            "<td>Aug 16, 2026, 4:30 PM</td>",
        )
        self.assertEqual(
            translate_visible_html_datetimes(
                "<td>17/08/2026 09:05</td>"
            ),
            "<td>Aug 17, 2026, 9:05 AM</td>",
        )

    def test_date_only_is_english(self):
        self.assertEqual(
            translate_visible_html_datetimes(
                "<span>16/08/2026</span>"
            ),
            "<span>Aug 16, 2026</span>",
        )

    def test_scripts_are_not_date_rewritten(self):
        source = (
            "<script>"
            "const value = '16/08/2026 16:30';"
            "</script>"
            "<span>16/08/2026 16:30</span>"
        )
        result = translate_visible_html_datetimes(source)

        self.assertIn(
            "const value = '16/08/2026 16:30';",
            result,
        )
        self.assertIn(
            "<span>Aug 16, 2026, 4:30 PM</span>",
            result,
        )

    def test_notification_json_is_translated_only_in_english(self):
        factory = RequestFactory()
        request = factory.get("/notifications/")
        request.LANGUAGE_CODE = "en"

        payload = {
            "notifications": [
                {
                    "title": "Connexion réussie",
                    "message": (
                        "Bienvenue admindev. Votre session est active."
                    ),
                    "created_at": "2026-08-17T15:30:00+03:00",
                },
                {
                    "title": "Nouvelle prédiction",
                    "message": (
                        "Avis #28 : Satisfait "
                        "(87.2% de confiance)."
                    ),
                    "created_at": "2026-08-17T15:31:00+03:00",
                },
            ]
        }

        middleware = EnglishResidualTranslationMiddleware(
            lambda _: JsonResponse(payload)
        )
        response = middleware(request)
        data = json.loads(response.content.decode("utf-8"))

        self.assertEqual(
            data["notifications"][0]["title"],
            "Login successful",
        )
        self.assertEqual(
            data["notifications"][0]["message"],
            "Welcome admindev. Your session is active.",
        )
        self.assertEqual(
            data["notifications"][1]["title"],
            "New prediction",
        )
        self.assertEqual(
            data["notifications"][1]["message"],
            "Feedback #28: Satisfied (87.2% confidence).",
        )

        # Machine timestamp stays ISO; browser formats it.
        self.assertEqual(
            data["notifications"][0]["created_at"],
            "2026-08-17T15:30:00+03:00",
        )

    def test_french_response_is_untouched(self):
        factory = RequestFactory()
        request = factory.get("/notifications/")
        request.LANGUAGE_CODE = "fr"

        middleware = EnglishResidualTranslationMiddleware(
            lambda _: HttpResponse(
                "<span>16/08/2026 16:30</span>"
                "<strong>Connexion réussie</strong>",
                content_type="text/html; charset=utf-8",
            )
        )
        response = middleware(request)

        self.assertIn(
            "16/08/2026 16:30",
            response.content.decode("utf-8"),
        )
        self.assertIn(
            "Connexion réussie",
            response.content.decode("utf-8"),
        )
