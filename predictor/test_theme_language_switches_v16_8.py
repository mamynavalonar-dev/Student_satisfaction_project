from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class ThemeLanguageSwitchesV168Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "theme_language_switches_v16_8.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "theme_language_switches_v16_8.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_assets_are_loaded(self):
        self.assertIn(
            "ux/theme_language_switches_v16_8.css",
            self.base,
        )
        self.assertIn(
            "ux/theme_language_switches_v16_8.js",
            self.base,
        )

    def test_theme_switch_keeps_supplied_geometry(self):
        for token in (
            "--switch-width: 48px",
            "--switch-height: 20px",
            "--circle-diameter: 32px",
            ".ui-switch.v168-theme-switch",
            "input:checked",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_theme_switch_is_direct_light_dark_and_persistent(self):
        for token in (
            'const THEME_KEY = "student-satisfaction-theme"',
            "setThemeExplicit",
            'localStorage.setItem(THEME_KEY, theme)',
            'root.dataset.appTheme = theme',
            '"app-theme-change"',
            'checkbox.checked ? "dark" : "light"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)

    def test_language_switch_uses_fr_en_not_yes_no(self):
        self.assertIn(
            'content: "FR"',
            self.css,
        )
        self.assertIn(
            'content: "EN"',
            self.css,
        )
        self.assertNotIn(
            'content: "YES"',
            self.css,
        )
        self.assertNotIn(
            'content: "NO"',
            self.css,
        )

    def test_language_switch_preserves_django_set_language_form(self):
        for token in (
            'button[name="language"][value="${language}"]',
            "form.requestSubmit(submitter)",
            "persistDrawerOpenIfNeeded",
            'checkbox.checked ? "en" : "fr"',
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)

    def test_progressive_enhancement_keeps_legacy_controls_as_fallback(self):
        for token in (
            ".v168-legacy-control",
            "v168-enhanced-locale",
            "[data-theme-toggle]",
            "[data-mobile-theme-cycle]",
            ".app-locale-switch, .mobile-drawer-locale",
        ):
            source = self.css if token == ".v168-legacy-control" else self.js
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_switches_have_keyboard_accessibility_contract(self):
        self.assertIn(
            'checkbox.setAttribute("role", "switch")',
            self.js,
        )
        self.assertIn(
            "input:focus-visible",
            self.css,
        )
        self.assertNotIn(
            ".ui-switch input {\n  display: none;",
            self.css,
        )
