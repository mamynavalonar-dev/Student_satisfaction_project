from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileNavigationReferenceV163Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root
            / "template"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_v16.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

    def test_base_template_still_compiles(self):
        get_template("base.html")

    def test_reference_alignment_css_exists(self):
        for token in (
            "V16.3_REFERENCE_ALIGNMENT_START",
            "--mobile-card-top",
            "--mobile-card-x",
            "--mobile-card-scale",
            "transform-origin: top left",
            "var(--mobile-card-top)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_reference_alignment_is_dynamic(self):
        for token in (
            "syncReferenceAlignment",
            "getBoundingClientRect",
            "--mobile-card-top",
            "MutationObserver",
            "mobile-nav-open",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)

    def test_drawer_is_full_screen_background(self):
        self.assertIn(
            ".mobile-side-drawer",
            self.css,
        )
        self.assertIn(
            "width: 100vw !important",
            self.css,
        )
        self.assertIn(
            "height: 100dvh !important",
            self.css,
        )
        self.assertIn(
            "border-radius: 0 !important",
            self.css,
        )

    def test_bottom_navigation_slots_are_balanced(self):
        self.assertIn(
            "flex: 1 1 0 !important",
            self.css,
        )
        self.assertIn(
            "flex: 2.10 1 0 !important",
            self.css,
        )

    def test_data_icon_is_not_the_broken_database_icon(self):
        start = self.base.index(
            "V16_MOBILE_NAVIGATION"
        )
        mobile = self.base[start:]

        self.assertNotIn(
            'class="bi bi-database"',
            mobile,
        )
