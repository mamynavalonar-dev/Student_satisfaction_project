from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class PartialNavigationV1613Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "partial_navigation_v16_13.js"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "partial_navigation_v16_13.css"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_page_head_markers_wrap_extra_css(self):
        start = self.base.index(
            'name="v1613-page-head-start"'
        )
        block = self.base.index(
            "{% block extra_css %}",
            start,
        )
        end = self.base.index(
            'name="v1613-page-head-end"',
            block,
        )

        self.assertLess(start, block)
        self.assertLess(block, end)

    def test_page_scripts_are_wrapped(self):
        self.assertIn(
            'id="v1613-page-scripts"',
            self.base,
        )
        self.assertIn(
            "{% block scripts %}",
            self.base,
        )

    def test_assets_are_loaded(self):
        self.assertIn(
            "ux/partial_navigation_v16_13.css",
            self.base,
        )
        self.assertIn(
            "ux/partial_navigation_v16_13.js",
            self.base,
        )

    def test_primary_navigation_uses_fetch_history_api(self):
        for token in (
            'fetch(',
            'history.pushState(',
            '"popstate"',
            'main.main-content',
            'X-Student-Satisfaction-Partial',
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.js,
                )

    def test_page_scripts_are_reinitialized(self):
        for token in (
            "executePageScripts",
            '"DOMContentLoaded"',
            'readyListeners',
            "v1613-page-scripts",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.js,
                )

    def test_page_css_is_loaded_before_old_css_is_removed(self):
        self.assertIn(
            "syncPageHead",
            self.js,
        )
        self.assertIn(
            "await Promise.all",
            self.js,
        )
        self.assertIn(
            "oldNodes.forEach",
            self.js,
        )

    def test_drawer_and_bottom_shell_are_not_replaced(self):
        self.assertNotIn(
            'document.body.innerHTML =',
            self.js,
        )
        self.assertNotIn(
            'location.reload(',
            self.js,
        )
        self.assertIn(
            "replaceMain",
            self.js,
        )

    def test_prefetch_and_fallback_exist(self):
        self.assertIn(
            "prefetchAnchor",
            self.js,
        )
        self.assertIn(
            "hardNavigate",
            self.js,
        )

    def test_progress_respects_reduced_motion(self):
        self.assertIn(
            "prefers-reduced-motion",
            self.css,
        )
