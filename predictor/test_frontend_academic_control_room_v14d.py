from __future__ import annotations

from django.conf import settings
from django.test import SimpleTestCase


class AcademicControlRoomV14DTests(SimpleTestCase):
    def test_base_links_v14d_stylesheet(self):
        base = (
            settings.BASE_DIR
            / "template"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "ux/academic_control_room_v14d.css",
            base,
        )

    def test_v14d_stylesheet_contains_design_contract(self):
        css = (
            settings.BASE_DIR
            / "static"
            / "ux"
            / "academic_control_room_v14d.css"
        ).read_text(encoding="utf-8")

        for token in (
            "--acr-cobalt",
            "--acr-serif",
            ".main-content .card",
            ".main-content .table",
            "focus-visible",
            "prefers-reduced-motion",
            'html[data-app-theme="dark"]',
        ):
            self.assertIn(token, css)

    def test_v14d_avoids_generic_purple_gradient(self):
        css = (
            settings.BASE_DIR
            / "static"
            / "ux"
            / "academic_control_room_v14d.css"
        ).read_text(encoding="utf-8").lower()

        self.assertNotIn("linear-gradient", css)
        self.assertNotIn("#8b5cf6", css)
        self.assertNotIn("#a855f7", css)
