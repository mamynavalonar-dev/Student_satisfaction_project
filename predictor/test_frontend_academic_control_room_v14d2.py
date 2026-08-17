from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from student_satisfaction_project.i18n_statistics_lastmile import (
    StatisticsEnglishLastMileMiddleware,
    translate_statistics_lastmile_html,
)


class AcademicControlRoomV14D2Tests(SimpleTestCase):
    def test_summary_card_visibility_override_exists(self):
        css = (
            settings.BASE_DIR
            / "static"
            / "ux"
            / "academic_control_room_v14d.css"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "V14D2_SUMMARY_CARD_VISIBILITY",
            css,
        )
        self.assertIn(
            ".main-content .card.stats-card",
            css,
        )
        self.assertIn(
            "background: var(--acr-cobalt) !important;",
            css,
        )
        self.assertIn(
            "color: #ffffff !important;",
            css,
        )

    def test_statistics_residual_fragment_translates(self):
        source = (
            "Cette mesure décrit ce que le "
            "<strong>active MLP uses for prediction</strong>. "
            "Elle est différente des "
            "“Observed Associations” "
            "et ne constitue pas une preuve de causalité."
        )

        result = translate_statistics_lastmile_html(source)

        self.assertIn(
            "This measure describes what the",
            result,
        )
        self.assertIn(
            "It differs from",
            result,
        )
        self.assertIn(
            "and is not evidence of causality.",
            result,
        )

        self.assertNotIn(
            "Cette mesure décrit",
            result,
        )
        self.assertNotIn(
            "Elle est différente",
            result,
        )

    def test_statistics_fragment_with_extra_whitespace_translates(self):
        source = (
            "Cette   mesure décrit\nce que   le "
            "<strong>active MLP uses for prediction</strong>"
        )

        result = translate_statistics_lastmile_html(source)

        self.assertIn(
            "This measure describes what the",
            result,
        )

    def test_english_html_response_is_modified(self):
        factory = RequestFactory()
        request = factory.get("/statistics/")
        request.LANGUAGE_CODE = "en"

        middleware = StatisticsEnglishLastMileMiddleware(
            lambda _: HttpResponse(
                "Cette mesure décrit ce que le "
                "<strong>active MLP uses for prediction</strong>.",
                content_type="text/html; charset=utf-8",
            )
        )

        response = middleware(request)
        source = response.content.decode("utf-8")

        self.assertIn(
            "This measure describes what the",
            source,
        )
        self.assertNotIn(
            "Cette mesure décrit",
            source,
        )

    def test_french_html_response_is_untouched(self):
        factory = RequestFactory()
        request = factory.get("/statistics/")
        request.LANGUAGE_CODE = "fr"

        original = (
            "Cette mesure décrit ce que le "
            "<strong>MLP actif utilise pour prédire</strong>."
        )

        middleware = StatisticsEnglishLastMileMiddleware(
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
