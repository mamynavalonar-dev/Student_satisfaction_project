from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileVisualStateRecoveryV161381Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.indicator_js = (
            root
            / "static"
            / "ux"
            / "partial_navigation_indicator_v16_13_1.js"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "mobile_visual_state_recovery_v16_13_8.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "mobile_visual_state_recovery_v16_13_8.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_recovery_assets_are_loaded(self):
        self.assertIn(
            "ux/mobile_visual_state_recovery_v16_13_8.css",
            self.base,
        )
        self.assertIn(
            "ux/mobile_visual_state_recovery_v16_13_8.js",
            self.base,
        )

    def test_bottom_indicator_is_horizontal_only(self):
        for token in (
            'group.indicatorSelector === ".mobile-bottom-slider"',
            'indicator.style.removeProperty("height")',
            'translate3d(${position.x}px, 0, 0)',
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.indicator_js,
                )

    def test_current_freeze_layers_are_cleaned(self):
        for token in (
            "v169-drawer-preopen",
            "v169-navigation-lock",
            "v1610-drawer-settling",
            "v1611-drawer-preopen",
            "v1611-drawer-settling",
            "v1611-navigation-lock",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.js,
                )

        self.assertNotIn(
            "v16101-drawer-preopen",
            self.js,
        )

    def test_recovery_never_closes_or_opens_drawer(self):
        for forbidden in (
            'body.classList.remove("mobile-nav-open")',
            'body.classList.add("mobile-nav-open")',
            'body.classList.toggle("mobile-nav-open"',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.js,
                )

    def test_closed_canvas_is_identity_geometry(self):
        for token in (
            "body:not(.mobile-nav-open)",
            ".mobile-app-canvas",
            "position: relative !important",
            "width: 100% !important",
            "height: auto !important",
            "transform: none !important",
            "border-radius: 0 !important",
            "box-shadow: none !important",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.css,
                )

    def test_close_is_observed_from_existing_controller(self):
        for token in (
            "[data-mobile-menu-close]",
            "MutationObserver",
            "scheduleClosedNormalization",
            "drawerIsOpen()",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.js,
                )

    def test_recovery_does_not_reimplement_navigation_language_or_theme(self):
        for forbidden in (
            "fetch(",
            "history.pushState",
            "set_language",
            "FormData(",
            "innerHTML =",
            "startViewTransition",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(
                    forbidden,
                    self.js,
                )
