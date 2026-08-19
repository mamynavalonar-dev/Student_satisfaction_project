from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class MobileMetricCardsLayoutV161391Tests(SimpleTestCase):
    def setUp(self):
        root = Path(settings.BASE_DIR)
        self.base = (root / "template" / "base.html").read_text(encoding="utf-8")
        self.css = (root / "static" / "ux" / "mobile_metric_cards_layout_v16_13_9_1.css").read_text(encoding="utf-8")

    def test_base_compiles(self):
        get_template("base.html")

    def test_asset_is_loaded(self):
        self.assertIn(
            "ux/mobile_metric_cards_layout_v16_13_9_1.css",
            self.base,
        )

    def test_patch_is_mobile_only_and_metric_scoped(self):
        for token in (
            "V16.13.9.1_MOBILE_METRIC_CARDS_LAYOUT_START",
            "@media (max-width: 820px)",
            ".row:has(> [class*=\"col\"] > .stats-card)",
            "grid-template-columns: repeat(2, minmax(0, 1fr))",
            ".stats-card .card-body",
            "order: 1",
            "order: 2",
        ):
            with self.subTest(token=token):
                self.assertIn(token, self.css)

    def test_patch_does_not_touch_navigation_or_drawer_logic(self):
        for forbidden in (
            "mobile-nav-open",
            "v1611-drawer",
            "translate3d(",
            "fetch(",
            "requestSubmit(",
            "startViewTransition",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.css)
