from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileSlidingIndicatorsV166Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.css = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_indicators_v16_6.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_indicators_v16_6.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_base_loads_v166_assets(self):
        self.assertIn(
            "ux/mobile_navigation_indicators_v16_6.css",
            self.base,
        )
        self.assertIn(
            "ux/mobile_navigation_indicators_v16_6.js",
            self.base,
        )

    def test_account_owner_is_visible_and_links_to_profile(self):
        for token in (
            "V16.6_ACCOUNT_OWNER_LINK",
            "{% url 'accounts:profile' %}",
            "mobile-drawer-owner-icon",
            "mobile-drawer-owner-name",
            "{{ user.username }}",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.base)

    def test_notification_bell_has_dark_theme_contract(self):
        for token in (
            'html[data-app-theme="dark"] .notification-bell',
            "background: #202d3f !important",
            "border-color: #405269 !important",
            ".notification-badge",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_bottom_slider_is_independent_and_animated(self):
        for token in (
            ".mobile-bottom-slider",
            "transition:",
            "transform 235ms",
            "activateBottomLink",
            "positionBottomSlider",
        ):
            source = self.css if token.startswith(".") or "235ms" in token or token == "transition:" else self.js
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_drawer_slider_is_independent_and_animated(self):
        for token in (
            ".mobile-drawer-slider",
            "positionDrawerSlider",
            "activateDrawerLink",
            "translate3d",
        ):
            source = self.css if token.startswith(".") else self.js
            with self.subTest(token=token):
                self.assertIn(token, source)

    def test_old_drawer_active_dot_is_disabled(self):
        self.assertIn(
            ".mobile-drawer-link.is-active::after",
            self.css,
        )
        self.assertIn(
            "display: none !important",
            self.css,
        )
