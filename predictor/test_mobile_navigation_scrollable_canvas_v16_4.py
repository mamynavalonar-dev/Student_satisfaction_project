from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileNavigationScrollableCanvasV164Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.css = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_v16.css"
        ).read_text(encoding="utf-8")

        self.js = (
            root
            / "static"
            / "ux"
            / "mobile_navigation_v16.js"
        ).read_text(encoding="utf-8")

    def test_base_still_compiles(self):
        get_template("base.html")

    def test_open_canvas_is_vertically_scrollable(self):
        for token in (
            "V16.4_SCROLLABLE_FLOATING_CANVAS_START",
            "overflow-y: auto !important",
            "-webkit-overflow-scrolling: touch",
            "touch-action: pan-y",
            "overscroll-behavior-y: contain",
            "pointer-events: auto !important",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_scrim_no_longer_blocks_card_touch_scroll(self):
        self.assertIn(
            "body.mobile-nav-open .mobile-nav-scrim",
            self.css,
        )
        self.assertIn(
            "pointer-events: none !important",
            self.css,
        )

    def test_horizontal_drag_is_suppressed(self):
        self.assertIn(
            "overscroll-behavior-x: none",
            self.css,
        )

    def test_scroll_session_resets_when_drawer_opens(self):
        for token in (
            "V16.4_SCROLLABLE_FLOATING_CANVAS_START",
            "canvas.scrollTop = 0",
            "MutationObserver",
            "mobile-nav-open",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.js)
