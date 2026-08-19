from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase


class LanguageVisualIntegrityV16137Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.js = (
            root
            / "static"
            / "ux"
            / "language_same_document_v16_13_6.js"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "language_same_document_v16_13_6.css"
        ).read_text(encoding="utf-8")

    def test_profile_owner_cannot_be_matched_as_profile_menu(self):
        self.assertIn(
            "owner and Profile share the same href",
            self.js,
        )

        self.assertIn(
            'syncRouteGroup(\n'
            '            nextDoc,\n'
            '            ".mobile-drawer-tools"',
            self.js,
        )

        self.assertIn(
            'copyTranslatedAttributes(\n'
            '            document.querySelector(\n'
            '                ".mobile-drawer-owner"',
            self.js,
        )

    def test_runtime_switch_dom_is_never_replaced(self):
        self.assertIn(
            "runtime switch DOM is kept intact",
            self.js,
        )

        self.assertNotIn(
            '.mobile-drawer-locale").innerHTML',
            self.js,
        )

        self.assertNotIn(
            '.v168-language-switch").innerHTML',
            self.js,
        )

    def test_bottom_nav_icons_and_slider_are_not_replaced(self):
        self.assertIn(
            ".mobile-bottom-label",
            self.js,
        )

        self.assertNotIn(
            "currentBottom.innerHTML",
            self.js,
        )

        self.assertNotIn(
            "currentLink.innerHTML = nextLink.innerHTML",
            self.js,
        )

    def test_drawer_state_is_preserved_across_language_change(self):
        for token in (
            "captureUiState",
            "restoreUiState",
            "mobile-nav-open",
            "student-satisfaction-mobile-drawer-open",
            'aria-hidden",\n'
            '                "false"',
            'aria-expanded",\n'
            '                "true"',
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.js,
                )

    def test_language_switch_keeps_focus_away_from_skip_link(self):
        self.assertIn(
            "drawer-language",
            self.js,
        )

        self.assertIn(
            "topbar-language",
            self.js,
        )

        self.assertIn(
            "preventScroll",
            self.js,
        )

        self.assertIn(
            ".skip-link:not(:focus-visible)",
            self.css,
        )

    def test_indicator_geometry_is_refreshed_after_label_translation(self):
        self.assertIn(
            "refreshIndicatorGeometry",
            self.js,
        )

        self.assertIn(
            '"v1613:navigated"',
            self.js,
        )

        self.assertIn(
            'new Event(\n'
            '                                "resize"',
            self.js,
        )
