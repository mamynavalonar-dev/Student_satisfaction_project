from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class NavigationCurtainV1612Tests(SimpleTestCase):
    """
    Historical compatibility guard.

    V16.12's cross-document navigation curtain was superseded by V16.13
    partial navigation and the V16.11 server-rendered static mobile canvas.
    Keeping this historical module verifies both that the old curtain does
    not return and that its replacement contracts remain present.
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

        self.partial_css = (
            root
            / "static"
            / "ux"
            / "partial_navigation_v16_13.css"
        ).read_text(encoding="utf-8")

        self.canvas_css = (
            root
            / "static"
            / "ux"
            / "static_mobile_canvas_v16_11.css"
        ).read_text(encoding="utf-8")

        self.theme_css = (
            root
            / "static"
            / "ux"
            / "theme_accessibility.css"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_critical_boot_and_css_are_inline_in_head(self):
        # The obsolete curtain boot/CSS must stay gone.
        self.assertNotIn(
            "V16.12_NAVIGATION_CURTAIN_EARLY_BOOT",
            self.base,
        )
        self.assertNotIn(
            "V16.12_NAVIGATION_CURTAIN_CRITICAL_CSS",
            self.base,
        )

        # Prepaint geometry is now owned by the server-rendered V16.11 canvas.
        self.assertIn(
            "V16.11_EARLY_STATIC_CANVAS_BOOT",
            self.base,
        )

        head_end = self.base.index("</head>")

        self.assertLess(
            self.base.index(
                "V16.11_EARLY_STATIC_CANVAS_BOOT"
            ),
            head_end,
        )

    def test_curtain_is_first_class_server_markup(self):
        self.assertNotIn(
            "V16.12_NAVIGATION_CURTAIN_BODY",
            self.base,
        )
        self.assertNotIn(
            'id="app-navigation-curtain-v1612"',
            self.base,
        )

        # The application canvas itself is server-rendered exactly once.
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

    def test_navigation_js_is_loaded(self):
        self.assertNotIn(
            "ux/navigation_curtain_v16_12.js",
            self.base,
        )
        self.assertIn(
            "ux/partial_navigation_v16_13.js",
            self.base,
        )
        self.assertIn(
            "ux/partial_navigation_v16_13.css",
            self.base,
        )

    def test_primary_desktop_and_mobile_nav_are_covered(self):
        for token in (
            "[data-animated-nav] a[href]",
            ".mobile-drawer-link[href]",
            ".mobile-bottom-link[href]",
            ".brand[href]",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.partial_js,
                )

    def test_old_page_paints_before_real_navigation(self):
        # V16.13 handles normal links same-document and keeps a hard
        # navigation fallback only when partial replacement is impossible.
        for token in (
            "V16.13_PARTIAL_NAVIGATION_START",
            "requestAnimationFrame(() => {",
            "hardNavigate",
            "window.location.assign(",
            "history.pushState",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.partial_js,
                )

        self.assertNotIn(
            "app-navigation-pending-v1612",
            self.partial_js,
        )

    def test_new_page_keeps_pending_state_before_body(self):
        # There is no longer a cross-document pending-curtain state.
        self.assertNotIn(
            "student-satisfaction-navigation-pending-v1612",
            self.base,
        )
        self.assertNotIn(
            "app-navigation-pending-v1612",
            self.base,
        )

        # Drawer prepaint state is instead restored before body paint.
        self.assertIn(
            "v1611-drawer-preopen",
            self.base,
        )
        self.assertIn(
            "v1611-drawer-settling",
            self.base,
        )

    def test_theme_aware_non_white_dark_surface(self):
        # Theme state is owned by the global accessibility/theme layer,
        # not by a navigation curtain.
        self.assertIn(
            "document.documentElement.dataset.appTheme",
            self.base,
        )
        self.assertIn(
            'html[data-app-theme="dark"]',
            self.theme_css,
        )
        self.assertIn(
            "--app-bg: #0f1722",
            self.theme_css,
        )
        self.assertIn(
            "--app-surface: #182231",
            self.theme_css,
        )

    def test_mobile_drawer_context_only_covers_card_area(self):
        # The V16.12 curtain context is gone, while V16.11 keeps the
        # reference card geometry needed by the drawer interaction.
        self.assertNotIn(
            "app-navigation-drawer-context-v1612",
            self.base,
        )

        for token in (
            ".mobile-app-canvas",
            "var(--mobile-card-x, 64vw)",
            "var(--mobile-card-top, 94px)",
            "border-radius:",
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token,
                    self.canvas_css,
                )

    def test_reduced_motion_is_respected(self):
        self.assertIn(
            "prefers-reduced-motion",
            self.partial_css,
        )
