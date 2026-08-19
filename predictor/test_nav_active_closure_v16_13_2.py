from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class NavActiveClosureV16132Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)

        self.base = (
            root / "template" / "base.html"
        ).read_text(encoding="utf-8")

        self.partial_js = (
            root / "static" / "ux" / "partial_navigation_v16_13.js"
        ).read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_v1613_partial_navigation_remains_intact(self):
        self.assertIn(
            "V16.13_PARTIAL_NAVIGATION_START",
            self.partial_js,
        )
        self.assertIn("fetch(", self.partial_js)
        self.assertIn("history.pushState", self.partial_js)

    def test_legacy_controller_is_dynamic(self):
        self.assertIn(
            "V16.13.2_DYNAMIC_ACTIVE_LINK",
            self.base,
        )
        self.assertIn(
            "const getActiveLink = () =>",
            self.base,
        )

    def test_static_active_link_capture_is_gone(self):
        self.assertNotIn(
            "const activeLink = links.find",
            self.base,
        )

    def test_restore_paths_use_current_active_link(self):
        self.assertIn(
            "moveIndicator(getActiveLink())",
            self.base,
        )
        self.assertIn(
            "moveIndicator(getActiveLink(), false)",
            self.base,
        )

    def test_mutation_observer_tracks_v1613_class_changes(self):
        self.assertIn(
            "MutationObserver",
            self.base,
        )
        self.assertIn(
            'attributeFilter: ["class", "aria-current"]',
            self.base,
        )

    def test_v1613_event_confirms_indicator_position(self):
        self.assertIn(
            '"v1613:navigated"',
            self.base,
        )
