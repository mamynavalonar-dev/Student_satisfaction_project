from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileNavigationV16Tests(SimpleTestCase):
    def setUp(self):
        self.base = (
            Path(settings.BASE_DIR)
            / "template"
            / "base.html"
        ).read_text(encoding="utf-8")

        self.css = (
            Path(settings.BASE_DIR)
            / "static"
            / "ux"
            / "mobile_navigation_v16.css"
        ).read_text(encoding="utf-8")

        self.js = (
            Path(settings.BASE_DIR)
            / "static"
            / "ux"
            / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

    def test_base_template_still_compiles(self):
        get_template("base.html")

    def test_base_loads_mobile_navigation_assets(self):
        self.assertIn(
            "ux/mobile_navigation_v16.css",
            self.base,
        )
        self.assertIn(
            "ux/mobile_navigation_v16.js",
            self.base,
        )

    def test_drawer_and_bottom_navigation_are_present(self):
        for token in (
            "V16_MOBILE_NAVIGATION",
            "data-mobile-menu-toggle",
            "data-mobile-drawer",
            "data-mobile-nav-scrim",
            "mobile-bottom-nav",
            "data-mobile-bottom-link",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.base)

    def test_rbac_conditions_are_preserved_in_mobile_navigation(self):
        for token in (
            "{% if can_train_models %}",
            "{% if can_view_data %}",
            "{% if can_view_statistics %}",
            "{% if can_manage_users %}",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.base)

    def test_bottom_navigation_uses_expanding_active_pill_contract(self):
        for token in (
            ".mobile-bottom-link.is-active",
            "flex-grow: 1.9",
            ".mobile-bottom-label",
            "border-radius: 999px",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_side_drawer_uses_reference_peek_motion(self):
        for token in (
            ".mobile-side-drawer",
            "body.mobile-nav-open .mobile-side-drawer",
            "translateX(min(69vw, 292px))",
            "scale(.955)",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_mobile_navigation_keeps_desktop_nav_and_hides_it_only_mobile(self):
        self.assertIn(".nav-container", self.css)
        self.assertIn("display: none !important;", self.css)
        self.assertIn("@media (max-width: 820px)", self.css)

    def test_accessibility_and_keyboard_contract(self):
        for token in (
            'event.key === "Escape"',
            "focusableSelector",
            'event.key !== "Tab"',
            'aria-current',
            "prefers-reduced-motion",
        ):
            with self.subTest(token=token):
                source = self.js if token != "prefers-reduced-motion" else self.css
                self.assertIn(token, source)
