from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class PartialNavigationIndicatorV16131Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root
            / "template"
            / "base.html"
        ).read_text(
            encoding="utf-8"
        )

        self.partial_js = (
            root
            / "static"
            / "ux"
            / "partial_navigation_v16_13.js"
        ).read_text(
            encoding="utf-8"
        )

        self.fix_js = (
            root
            / "static"
            / "ux"
            / "partial_navigation_indicator_v16_13_1.js"
        ).read_text(
            encoding="utf-8"
        )

        self.fix_css = (
            root
            / "static"
            / "ux"
            / "partial_navigation_indicator_v16_13_1.css"
        ).read_text(
            encoding="utf-8"
        )

    def test_base_compiles(self):
        get_template(
            "base.html"
        )

    def test_v1613_partial_navigation_is_still_present(self):
        self.assertIn(
            "V16.13_PARTIAL_NAVIGATION_START",
            self.partial_js,
        )
        self.assertIn(
            "fetch(",
            self.partial_js,
        )
        self.assertIn(
            "history.pushState",
            self.partial_js,
        )

    def test_indicator_fix_loads_before_partial_navigation(self):
        fix_pos = self.base.index(
            "ux/partial_navigation_indicator_v16_13_1.js"
        )

        partial_pos = self.base.index(
            "ux/partial_navigation_v16_13.js"
        )

        self.assertLess(
            fix_pos,
            partial_pos,
        )

    def test_no_navigation_or_main_replacement_is_implemented_here(self):
        forbidden = (
            "fetch(",
            "window.location.assign",
            "history.pushState",
            "innerHTML =",
            "replaceMain",
        )

        for token in forbidden:
            with self.subTest(
                token=token
            ):
                self.assertNotIn(
                    token,
                    self.fix_js,
                )

    def test_all_three_indicator_groups_are_synchronized(self):
        for token in (
            "[data-animated-nav]",
            ".mobile-drawer-link[href]",
            ".mobile-bottom-link[href]",
            ".nav-indicator",
            ".mobile-drawer-slider",
            ".mobile-bottom-slider",
        ):
            with self.subTest(
                token=token
            ):
                self.assertIn(
                    token,
                    self.fix_js,
                )

    def test_click_and_navigated_event_both_resync(self):
        self.assertIn(
            '"click"',
            self.fix_js,
        )
        self.assertIn(
            '"v1613:navigated"',
            self.fix_js,
        )
        self.assertIn(
            '"popstate"',
            self.fix_js,
        )

    def test_route_matching_tolerates_trailing_slash(self):
        self.assertIn(
            "normalizePath",
            self.fix_js,
        )
        self.assertIn(
            'path.endsWith("/")',
            self.fix_js,
        )

    def test_indicator_has_smooth_transform(self):
        self.assertIn(
            "transform 180ms",
            self.fix_css,
        )
        self.assertIn(
            "prefers-reduced-motion",
            self.fix_css,
        )
