from pathlib import Path

from django.test import SimpleTestCase

ROOT = Path(__file__).resolve().parents[1]


class FrontendConsoleSafetyV175Tests(SimpleTestCase):
    def _read(self, relative_path: str) -> str:
        return (ROOT / relative_path).read_text(encoding="utf-8")

    def test_indicator_script_declares_root_before_use(self):
        source = self._read("static/ux/partial_navigation_indicator_v16_13_1.js")
        declaration = "const root = document.documentElement;"
        use = "root.dataset.navIndicatorSync ="
        self.assertIn(declaration, source)
        self.assertIn(use, source)
        self.assertLess(source.index(declaration), source.index(use))

    def test_indicator_script_has_safe_event_target_lookup(self):
        source = self._read("static/ux/partial_navigation_indicator_v16_13_1.js")
        self.assertIn("const closestFromTarget = (", source)
        self.assertNotIn("event.target.closest(", source)

    def test_navigation_performance_has_safe_event_target_lookup(self):
        source = self._read("static/ux/navigation_performance_v16_5.js")
        self.assertIn("const closestAnchor = (target) =>", source)
        self.assertNotIn("event.target.closest(", source)

    def test_partial_navigation_has_safe_event_target_lookup(self):
        source = self._read("static/ux/partial_navigation_v16_13.js")
        self.assertIn("const closestFromTarget = (", source)
        self.assertNotIn("event.target.closest(", source)
