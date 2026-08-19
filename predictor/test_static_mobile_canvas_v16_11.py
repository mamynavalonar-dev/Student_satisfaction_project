from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class StaticMobileCanvasV1611Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.mobile_js = (
            root / "static" / "ux" / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

        self.css = (
            root / "static" / "ux" / "static_mobile_canvas_v16_11.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root / "static" / "ux" / "static_mobile_canvas_v16_11.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_canvas_is_server_rendered_once(self):
        self.assertEqual(
            self.base.count(
                'class="mobile-app-canvas"'
            ),
            1,
        )
        self.assertIn(
            "data-mobile-app-canvas",
            self.base,
        )

    def test_canvas_wraps_header_main_and_footer(self):
        start = self.base.index(
            'class="mobile-app-canvas"'
        )
        end = self.base.index(
            "<!-- V16.11_STATIC_CANVAS_END -->",
            start,
        )

        segment = self.base[start:end]

        self.assertIn(
            'class="page-header',
            segment,
        )
        self.assertIn(
            'class="main-content',
            segment,
        )
        self.assertIn(
            "<footer",
            segment,
        )

    def test_mobile_controls_remain_outside_canvas(self):
        canvas_pos = self.base.index(
            'class="mobile-app-canvas"'
        )
        drawer_pos = self.base.index(
            "data-mobile-drawer"
        )
        bottom_pos = self.base.index(
            "mobile-bottom-nav"
        )

        self.assertLess(
            drawer_pos,
            canvas_pos,
        )
        self.assertLess(
            bottom_pos,
            canvas_pos,
        )

    def test_old_dynamic_builder_becomes_noop(self):
        self.assertIn(
            'if (document.querySelector(".mobile-app-canvas")) return;',
            self.mobile_js,
        )

    def test_early_open_geometry_is_available_before_paint(self):
        self.assertIn(
            "V16.11_EARLY_STATIC_CANVAS_BOOT",
            self.base,
        )
        self.assertIn(
            "v1611-drawer-preopen",
            self.base,
        )
        self.assertIn(
            "html.v1611-drawer-preopen .mobile-app-canvas",
            self.css,
        )
        self.assertIn(
            "transition: none !important",
            self.css,
        )

    def test_v16101_assets_are_no_longer_loaded(self):
        self.assertNotIn(
            "drawer_load_stability_v16_10_1.css",
            self.base,
        )
        self.assertNotIn(
            "drawer_load_stability_v16_10_1.js",
            self.base,
        )
        self.assertNotIn(
            "V16.10.1_EARLY_DRAWER_BOOT",
            self.base,
        )

    def test_navigation_lock_keeps_scaled_geometry(self):
        self.assertIn(
            "v1611-navigation-lock",
            self.css,
        )
        self.assertIn(
            "v1611-navigation-lock",
            self.js,
        )
        self.assertIn(
            "scale(var(--mobile-card-scale, .74))",
            self.css,
        )
