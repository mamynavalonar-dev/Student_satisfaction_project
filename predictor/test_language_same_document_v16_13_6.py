from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class LanguageSameDocumentV16136Tests(SimpleTestCase):
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

        self.switch_js = (
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

    def test_v168_still_delegates_language_change(self):
        self.assertIn(
            "V16.13.6_LANGUAGE_DELEGATE",
            self.switch_js,
        )
        self.assertIn(
            "StudentSatisfactionLanguageV16136",
            self.switch_js,
        )

    def test_language_is_still_same_document(self):
        for token in (
            'method: "POST"',
            "new FormData(",
            "fetch(",
            "partial.applyHtml(",
            "document.startViewTransition",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

    def test_shell_sync_is_precise(self):
        for token in (
            "V16.13.7_LANGUAGE_VISUAL_INTEGRITY_START",
            "syncStableShellPrecisely",
            "syncRouteGroup",
            ".mobile-drawer-nav",
            ".mobile-drawer-tools",
            ".mobile-bottom-label",
            "captureUiState",
            "restoreUiState",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

        self.assertNotIn(
            'syncLinks(nextDoc, "[data-mobile-drawer]")',
            self.language_js,
        )

        self.assertNotIn(
            'syncLinks(nextDoc, ".mobile-bottom-nav")',
            self.language_js,
        )

        self.assertNotIn(
            "currentLink.innerHTML = nextLink.innerHTML",
            self.language_js,
        )

        self.assertNotIn(
            "createTreeWalker",
            self.language_js,
        )

    def test_v1613_engine_is_preserved(self):
        for token in (
            "V16.13_PARTIAL_NAVIGATION_START",
            "V16.13.6_PUBLIC_PARTIAL_API",
            "replaceMain",
            "executePageScripts",
            "history.pushState",
            "[data-mobile-drawer] a.mobile-drawer-link[href]",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.partial_js,
                )
