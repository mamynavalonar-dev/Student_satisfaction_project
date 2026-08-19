from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class NavigationThemeV165Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.theme_js = (
            root / "static" / "ux" / "theme_accessibility.js"
        ).read_text(encoding="utf-8")

        self.theme_css = (
            root / "static" / "ux" / "theme_accessibility.css"
        ).read_text(encoding="utf-8")

        self.nav_js = (
            root / "static" / "ux" / "navigation_performance_v16_5.js"
        ).read_text(encoding="utf-8")

        self.nav_css = (
            root / "static" / "ux" / "navigation_performance_v16_5.css"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_base_loads_navigation_performance_assets(self):
        self.assertIn(
            "ux/navigation_performance_v16_5.css",
            self.base,
        )
        self.assertIn(
            "ux/navigation_performance_v16_5.js",
            self.base,
        )

    def test_theme_is_one_tap_visible_toggle(self):
        self.assertIn(
            "V16.5_ONE_TAP_THEME",
            self.theme_js,
        )
        self.assertIn(
            "toggleVisibleTheme",
            self.theme_js,
        )
        self.assertIn(
            'effective === "dark" ? "light" : "dark"',
            self.theme_js,
        )
        self.assertNotIn(
            'current === "auto" ? "light" : current === "light" ? "dark" : "auto"',
            self.theme_js,
        )

    def test_dark_notification_and_file_input_hardening_exists(self):
        for token in (
            "V16.5_THEME_HARDENING_START",
            ".notification-panel-header",
            ".notification-item-title",
            ".notification-item-message",
            "::file-selector-button",
            "overflow-x: hidden !important",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.theme_css)

    def test_navigation_feedback_is_immediate(self):
        for token in (
            '"pointerdown"',
            "moveDesktopIndicator",
            "markBottomPending",
            "app-navigating",
            'hint.rel = "prefetch"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.nav_js)

    def test_indicator_and_navigation_motion_contract(self):
        for token in (
            "--nav-motion-fast: 165ms",
            "@view-transition",
            "v165-nav-progress",
            "prefers-reduced-motion",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.nav_css)
