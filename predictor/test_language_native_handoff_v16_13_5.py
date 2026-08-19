from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class LanguageNativeHandoffV16135Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.language_js = (
            root
            / "static"
            / "ux"
            / "language_same_document_v16_13_6.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_native_cross_document_handoff_remains_retired(self):
        self.assertNotIn(
            "language_native_handoff_v16_13_5.css",
            self.base,
        )

        self.assertNotIn(
            "sidebar_action_stability_v16_13_3.js",
            self.base,
        )

    def test_same_document_language_is_now_v16137(self):
        self.assertIn(
            "V16.13.7_LANGUAGE_VISUAL_INTEGRITY_START",
            self.language_js,
        )

        self.assertIn(
            'method: "POST"',
            self.language_js,
        )

        self.assertIn(
            "fetch(",
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

    def test_visual_integrity_guards_are_present(self):
        for token in (
            "syncStableShellPrecisely",
            "captureUiState",
            "restoreUiState",
            ".mobile-bottom-label",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )
