from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileNavigationReferenceV162Tests(SimpleTestCase):
    def setUp(self):
        self.base = (
            Path(settings.BASE_DIR)
            / "template"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.css = (
            Path(settings.BASE_DIR)
            / "static"
            / "ux"
            / "mobile_navigation_v16.css"
        ).read_text(encoding="utf-8")

        self.js = (
            Path(settings.BASE_DIR)
            / "static"
            / "ux"
            / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_data_icon_is_visible_supported_icon(self):
        start = self.base.index("V16_MOBILE_NAVIGATION")
        mobile = self.base[start:]

        self.assertNotIn(
            'class="bi bi-database"',
            mobile,
        )
        self.assertGreaterEqual(
            mobile.count('class="bi bi-grid"'),
            2,
        )

    def test_reference_uses_full_screen_background_drawer(self):
        for token in (
            "V16.2_REFERENCE_DRAWER",
            "inset: 0",
            "width: 100vw",
            "height: 100dvh",
            "border-radius: 0",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_reference_uses_single_floating_application_canvas(self):
        for token in (
            ".mobile-app-canvas",
            "translate3d(min(67vw, 244px), 0, 0)",
            "scale(.74)",
            "border-radius: 24px",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

        self.assertIn(
            "V16.2_REFERENCE_CANVAS",
            self.js,
        )
        self.assertIn(
            'canvas.className = "mobile-app-canvas"',
            self.js,
        )

    def test_bottom_navigation_has_equal_inactive_slots(self):
        self.assertIn(
            "flex: 1 1 0",
            self.css,
        )
        self.assertIn(
            "flex: 2.15 1 0",
            self.css,
        )

    def test_drawer_has_reference_top_profile_and_close_geometry(self):
        self.assertIn(
            ".mobile-drawer-identity::before",
            self.css,
        )
        self.assertIn(
            "border-radius: 50%",
            self.css,
        )
        self.assertIn(
            "width: min(55vw, 205px)",
            self.css,
        )
