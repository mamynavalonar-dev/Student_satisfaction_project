from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class SidebarActionStabilityV16133Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.partial_js = (
            root
            / "static"
            / "ux"
            / "partial_navigation_v16_13.js"
        ).read_text(encoding="utf-8")

        self.theme_js = (
            root
            / "static"
            / "ux"
            / "theme_language_switches_v16_8.js"
        ).read_text(encoding="utf-8")

        self.language_js = (
            root
            / "static"
            / "ux"
            / "language_same_document_v16_13_6.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_profile_and_administration_remain_partial(self):
        self.assertIn(
            "[data-mobile-drawer] a.mobile-drawer-link[href]",
            self.partial_js,
        )

    def test_theme_remains_same_document(self):
        self.assertIn(
            "V16.13.3_SMOOTH_THEME_CHANGE",
            self.theme_js,
        )

        self.assertIn(
            "document.startViewTransition",
            self.theme_js,
        )

    def test_language_handoff_is_replaced_by_v16137(self):
        self.assertNotIn(
            "sidebar_action_stability_v16_13_3.js",
            self.base,
        )

        self.assertIn(
            "V16.13.7_LANGUAGE_VISUAL_INTEGRITY_START",
            self.language_js,
        )

        self.assertIn(
            "partial.applyHtml(",
            self.language_js,
        )

        self.assertIn(
            "document.startViewTransition",
            self.language_js,
        )

    def test_drawer_state_contract_is_preserved(self):
        for token in (
            "captureUiState",
            "restoreUiState",
            "mobile-nav-open",
            "DRAWER_KEY",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

    def test_no_business_logic_is_added(self):
        for token in (
            "train_model",
            "predict_proba",
            "user_can(",
            "APIView",
        ):
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    self.language_js,
                )
