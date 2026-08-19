
from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobilePolishV169Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.home = (
            root / "template" / "predictor" / "home.html"
        ).read_text(encoding="utf-8")

        self.data = (
            root / "template" / "predictor" / "data.html"
        ).read_text(encoding="utf-8")

        self.css = (
            root / "static" / "ux" / "mobile_polish_v16_9.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root / "static" / "ux" / "mobile_polish_v16_9.js"
        ).read_text(encoding="utf-8")

    def test_templates_compile(self):
        for name in (
            "base.html",
            "predictor/home.html",
            "predictor/data.html",
        ):
            with self.subTest(name=name):
                get_template(name)

    def test_assets_and_preopen_boot_are_loaded(self):
        self.assertIn(
            "V16.9_DRAWER_PREOPEN_BOOT",
            self.base,
        )
        self.assertIn(
            "ux/mobile_polish_v16_9.css",
            self.base,
        )
        self.assertIn(
            "ux/mobile_polish_v16_9.js",
            self.base,
        )

    def test_switches_fit_inside_drawer(self):
        for token in (
            "width: min(44vw, 172px) !important",
            "--switch-width: 42px !important",
            "width: 62px !important",
            "left: 33px !important",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_active_contents_shift_right(self):
        for token in (
            ".mobile-drawer-link.is-active > .bi",
            "translateX(6px)",
            ".mobile-bottom-link.is-active .bi",
            "translateX(3px)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_restore_is_bounce_free_contract(self):
        for token in (
            "html.v169-drawer-preopen",
            "visibility: hidden !important",
            "transition: none !important",
            "v169-navigation-lock",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

        for token in (
            "finishPreopenRestore",
            "alignFloatingCardNow",
            "v169-drawer-preopen",
            "v169-navigation-lock",
            "sessionStorage.setItem",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)

    def test_home_and_data_have_four_mobile_kpi_items(self):
        self.assertIn(
            "v169-responsive-kpi-grid",
            self.home,
        )
        self.assertEqual(
            self.home.count("v169-responsive-kpi-item"),
            4,
        )
        self.assertIn(
            "v169-responsive-kpi-grid",
            self.data,
        )
        self.assertEqual(
            self.data.count("v169-responsive-kpi-item"),
            4,
        )

    def test_mobile_kpis_are_two_by_two(self):
        for token in (
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            "nth-child(1)",
            "nth-child(2)",
            "nth-child(3)",
            "nth-child(4)",
            "min-height: 116px",
            "text-align: left !important",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)
