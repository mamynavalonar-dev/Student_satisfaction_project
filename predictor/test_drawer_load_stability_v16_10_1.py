from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class DrawerLoadStabilityV16101Tests(SimpleTestCase):
    """
    Historical compatibility guard.

    V16.10.1 was intentionally superseded by V16.11 static canvas.
    This file stays so the full test suite keeps checking that the old
    cross-document layer does NOT accidentally return.
    """

    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.nav_css = (
            root
            / "static"
            / "ux"
            / "navigation_performance_v16_5.css"
        ).read_text(encoding="utf-8")

        self.v1611_css = (
            root
            / "static"
            / "ux"
            / "static_mobile_canvas_v16_11.css"
        ).read_text(encoding="utf-8")

        self.v1611_js = (
            root
            / "static"
            / "ux"
            / "static_mobile_canvas_v16_11.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_v16101_external_layer_remains_retired(self):
        for token in (
            "ux/drawer_load_stability_v16_10_1.css",
            "ux/drawer_load_stability_v16_10_1.js",
            "V16.10.1_EARLY_DRAWER_BOOT",
        ):
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    self.base,
                )

    def test_v1611_is_the_active_static_canvas_replacement(self):
        for token in (
            "ux/static_mobile_canvas_v16_11.css",
            "ux/static_mobile_canvas_v16_11.js",
            "V16.11_EARLY_STATIC_CANVAS_BOOT",
            'class="mobile-app-canvas"',
            "data-mobile-app-canvas",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.base,
                )

    def test_cross_document_view_transition_remains_disabled(self):
        self.assertNotIn(
            "navigation: auto",
            self.nav_css,
        )
        self.assertIn(
            "navigation: none",
            self.nav_css,
        )

    def test_v1611_keeps_prepaint_and_navigation_lock_contract(self):
        for token in (
            "html.v1611-drawer-preopen .mobile-app-canvas",
            "transition: none !important",
            "v1611-navigation-lock",
            "scale(var(--mobile-card-scale, .74))",
        ):
            source = (
                self.v1611_css
                + "\n"
                + self.v1611_js
            )
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    source,
                )

    def test_v1611_restore_uses_server_rendered_canvas(self):
        for token in (
            "finishServerCanvasRestore",
            "forceOpenSemantics",
            "v1611-drawer-settling",
            "v1611-drawer-preopen",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.v1611_js,
                )
