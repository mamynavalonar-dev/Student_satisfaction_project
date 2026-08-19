from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class LanguagePartialSwitchV16134Tests(SimpleTestCase):
    """
    Historical compatibility guard.

    V16.13.4 used an earlier monolithic language-switch implementation.
    It was superseded by the V16.13.6/V16.13.7 same-document language
    flow. These tests intentionally keep the historical module name so
    the complete suite verifies that the retired implementation does not
    accidentally return while the current implementation remains covered.
    """

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

        self.language_js = (
            root
            / "static"
            / "ux"
            / "language_same_document_v16_13_6.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_language_post_is_intercepted_same_document(self):
        # Current contract: Django still receives a real POST, while the
        # browser document is updated without a full-page replacement.
        for token in (
            "V16.13.7_LANGUAGE_VISUAL_INTEGRITY_START",
            'method: "POST"',
            "fetch(",
            "partial.applyHtml(",
            "document.startViewTransition",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

        # The old V16.13.4 controller must stay retired.
        self.assertNotIn(
            "V16.13.4_LANGUAGE_PARTIAL_SWITCH_START",
            self.language_js,
        )

    def test_django_cookie_flow_is_preserved(self):
        # Django remains the source of truth for language cookie + CSRF.
        for token in (
            "new FormData(",
            "credentials:",
            '"same-origin"',
            "redirect:",
            '"follow"',
            "body:",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

    def test_partial_navigation_exposes_fresh_api(self):
        self.assertIn(
            "window.StudentSatisfactionPartialNavigationV1613",
            self.partial_js,
        )
        self.assertIn(
            "applyHtml",
            self.partial_js,
        )
        self.assertIn(
            "CACHE.clear()",
            self.partial_js,
        )
        self.assertNotIn(
            "navigateFresh",
            self.partial_js,
        )

    def test_persistent_shell_text_is_synchronized(self):
        # V16.13.7 synchronizes only stable shell fragments and deliberately
        # avoids replacing runtime-controlled switches/indicators wholesale.
        for token in (
            "syncStableShellPrecisely",
            "copyTranslatedAttributes",
            "syncRouteGroup",
            '".page-header .brand"',
            '"[data-animated-nav]"',
            '"[data-mobile-drawer]"',
            '".mobile-bottom-nav"',
            '"footer"',
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

        self.assertNotIn(
            "syncPersistentShell",
            self.partial_js,
        )

    def test_main_partial_navigation_architecture_remains(self):
        for token in (
            "V16.13_PARTIAL_NAVIGATION_START",
            "replaceMain",
            "history.pushState",
            "executePageScripts",
            "hardNavigate",
            "prefetchAnchor",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.partial_js,
                )

    def test_language_control_is_resynchronized_after_partial_refresh(self):
        for token in (
            "syncSwitches",
            "document",
            ".documentElement",
            ".lang",
            "refreshIndicatorGeometry",
            '"v1613:navigated"',
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )

    def test_native_reload_exists_only_as_failure_fallback(self):
        for token in (
            "nativeFallback",
            "form.requestSubmit",
            ".prototype",
            ".submit",
            ".call(",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.language_js,
                )
