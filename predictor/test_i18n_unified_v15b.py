from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory, SimpleTestCase

from student_satisfaction_project.i18n_final_artifact_middleware import (
    FinalEnglishArtifactWarningMiddleware,
)
from student_satisfaction_project.i18n_middleware import (
    UnifiedEnglishI18nMiddleware,
)
from student_satisfaction_project.i18n_residual_middleware import (
    EnglishResidualTranslationMiddleware,
)
from student_satisfaction_project.i18n_statistics_lastmile import (
    StatisticsEnglishLastMileMiddleware,
)
from student_satisfaction_project.i18n_training_lastmile import (
    TrainingEnglishLastMileMiddleware,
)


OLD_MIDDLEWARE = (
    "student_satisfaction_project.i18n_statistics_lastmile."
    "StatisticsEnglishLastMileMiddleware",
    "student_satisfaction_project.i18n_final_artifact_middleware."
    "FinalEnglishArtifactWarningMiddleware",
    "student_satisfaction_project.i18n_training_lastmile."
    "TrainingEnglishLastMileMiddleware",
    "student_satisfaction_project.i18n_residual_middleware."
    "EnglishResidualTranslationMiddleware",
)

UNIFIED_MIDDLEWARE = (
    "student_satisfaction_project.i18n_middleware."
    "UnifiedEnglishI18nMiddleware"
)


def old_effective_chain(get_response):
    """
    Recreate the effective response order from the former settings order:
    residual -> training -> final artifact -> statistics.
    """
    chain = get_response
    chain = EnglishResidualTranslationMiddleware(chain)
    chain = TrainingEnglishLastMileMiddleware(chain)
    chain = FinalEnglishArtifactWarningMiddleware(chain)
    chain = StatisticsEnglishLastMileMiddleware(chain)
    return chain


class UnifiedEnglishI18nV15BTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _english_request(self, path="/test/"):
        request = self.factory.get(path)
        request.LANGUAGE_CODE = "en"
        return request

    def _french_request(self, path="/test/"):
        request = self.factory.get(path)
        request.LANGUAGE_CODE = "fr"
        return request

    def test_settings_register_only_the_unified_custom_i18n_middleware(self):
        self.assertEqual(
            settings.MIDDLEWARE.count(UNIFIED_MIDDLEWARE),
            1,
        )

        for dotted in OLD_MIDDLEWARE:
            with self.subTest(dotted=dotted):
                self.assertNotIn(
                    dotted,
                    settings.MIDDLEWARE,
                )

        locale_index = settings.MIDDLEWARE.index(
            "django.middleware.locale.LocaleMiddleware"
        )
        unified_index = settings.MIDDLEWARE.index(
            UNIFIED_MIDDLEWARE
        )

        # The orchestrator may be outside LocaleMiddleware on request;
        # it reads request.LANGUAGE_CODE only after the inner response,
        # when LocaleMiddleware has already selected the language.
        self.assertLess(
            unified_index,
            locale_index,
        )

    def test_english_html_output_matches_the_pre_v15b_pipeline(self):
        html = (
            "<html><body>"
            "<p>Connexion réussie. Bon retour, admindev.</p>"
            "<p>Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer.</p>"
            "<p>Cette mesure décrit ce que le "
            "<strong>active MLP uses for prediction</strong>.</p>"
            "<td><code>présentiel</code>, "
            "<code>distanciel</code>, "
            "<code>hybride</code></td>"
            "</body></html>"
        )

        def make_response(_request):
            response = HttpResponse(
                html,
                content_type="text/html; charset=utf-8",
            )
            response["ETag"] = '"v15b-test"'
            response["Content-Length"] = str(
                len(response.content)
            )
            return response

        old_response = old_effective_chain(
            make_response
        )(
            self._english_request("/old/")
        )

        unified_response = UnifiedEnglishI18nMiddleware(
            make_response
        )(
            self._english_request("/unified/")
        )

        self.assertEqual(
            unified_response.content,
            old_response.content,
        )
        self.assertEqual(
            unified_response.get("ETag"),
            old_response.get("ETag"),
        )
        self.assertEqual(
            unified_response.get("Content-Length"),
            old_response.get("Content-Length"),
        )

        text = unified_response.content.decode("utf-8")

        self.assertIn(
            "Login successful. Welcome back, admindev.",
            text,
        )
        self.assertIn(
            "Saved with scikit-learn 1.7.0",
            text,
        )
        self.assertIn(
            "This measure describes what the",
            text,
        )
        self.assertIn(
            ">In person</code>",
            text,
        )

    def test_english_json_output_matches_the_pre_v15b_pipeline(self):
        payload = {
            "notifications": [
                {
                    "title": "Connexion réussie",
                    "message": (
                        "Bienvenue admindev. "
                        "Votre session est active."
                    ),
                    "created_at": "2026-08-17T15:30:00+03:00",
                }
            ]
        }

        def make_response(_request):
            return JsonResponse(payload)

        old_response = old_effective_chain(
            make_response
        )(
            self._english_request("/old-json/")
        )

        unified_response = UnifiedEnglishI18nMiddleware(
            make_response
        )(
            self._english_request("/unified-json/")
        )

        self.assertEqual(
            unified_response.content,
            old_response.content,
        )

        # Generic JsonResponse: preserve pre-V15B behavior exactly.
        # Real notification JSON translation remains covered by the existing
        # notification/residual middleware tests below.
        body = unified_response.content.decode("utf-8")

        self.assertIn(
            "2026-08-17T15:30:00+03:00",
            body,
        )

    def test_french_html_is_identical_to_pre_v15b_pipeline(self):
        html = (
            "<p>Connexion réussie. Bon retour, admindev.</p>"
            "<p>Enregistré avec scikit-learn 1.7.0, "
            "environnement actuel 1.9.0. "
            "Réentraînez ce modèle avant de l'activer.</p>"
        )

        def make_response(_request):
            return HttpResponse(
                html,
                content_type="text/html; charset=utf-8",
            )

        old_response = old_effective_chain(
            make_response
        )(
            self._french_request("/old-fr/")
        )

        unified_response = UnifiedEnglishI18nMiddleware(
            make_response
        )(
            self._french_request("/unified-fr/")
        )

        self.assertEqual(
            unified_response.content,
            old_response.content,
        )
        self.assertEqual(
            unified_response.content.decode("utf-8"),
            html,
        )

    def test_plain_text_is_identical_to_pre_v15b_pipeline(self):
        content = "Connexion réussie"

        def make_response(_request):
            return HttpResponse(
                content,
                content_type="text/plain; charset=utf-8",
            )

        old_response = old_effective_chain(
            make_response
        )(
            self._english_request("/old-text/")
        )

        unified_response = UnifiedEnglishI18nMiddleware(
            make_response
        )(
            self._english_request("/unified-text/")
        )

        self.assertEqual(
            unified_response.content,
            old_response.content,
        )
        self.assertEqual(
            unified_response.content.decode("utf-8"),
            content,
        )
