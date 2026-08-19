from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileNavigationV167Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.mobile_js = (
            root / "static" / "ux" / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

        self.indicator_js = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_indicators_v16_6.js"
        ).read_text(encoding="utf-8")

        self.indicator_css = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_indicators_v16_6.css"
        ).read_text(encoding="utf-8")

    def test_base_still_compiles(self):
        get_template("base.html")

    def test_drawer_link_click_does_not_force_close(self):
        self.assertIn(
            "V16.7_DRAWER_PERSISTENCE",
            self.mobile_js,
        )
        self.assertIn(
            "keepDrawerOpenAcrossNavigation",
            self.mobile_js,
        )
        self.assertIn(
            'drawer.addEventListener(\n            "click",\n            keepDrawerOpenAcrossNavigation\n        );',
            self.mobile_js,
        )
        # The old drawer-specific auto-close handler must be gone.
        self.assertNotIn(
            'drawer.addEventListener("click", (event) => {',
            self.mobile_js,
        )

    def test_mobile_to_desktop_transition_may_still_close_drawer(self):
        # This is legitimate and must not be confused with link auto-close.
        self.assertIn(
            "const mediaChanged = (event) =>",
            self.mobile_js,
        )
        self.assertIn(
            'setState(false, { restoreFocus: false });',
            self.mobile_js,
        )

    def test_drawer_open_state_is_persisted(self):
        for token in (
            "MOBILE_DRAWER_OPEN_KEY",
            "sessionStorage.setItem",
            "sessionStorage.removeItem",
            "keepDrawerOpenAcrossNavigation",
            "restorePersistedDrawerState",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.mobile_js)

    def test_x_still_closes_drawer(self):
        self.assertIn(
            'close.addEventListener("click"',
            self.mobile_js,
        )
        self.assertIn(
            "setState(false)",
            self.mobile_js,
        )

    def test_bottom_slider_has_no_first_link_fallback(self):
        self.assertIn(
            "V16.7_GHOST_SLIDER_FIX_START",
            self.indicator_js,
        )
        self.assertNotIn(
            '|| bottomNav.querySelector(".mobile-bottom-link")',
            self.indicator_js,
        )

    def test_bottom_slider_hides_without_matching_route(self):
        self.assertIn(
            ".mobile-bottom-slider.is-hidden",
            self.indicator_css,
        )
        self.assertIn(
            '"is-hidden"',
            self.indicator_js,
        )
