from __future__ import annotations

import re

from django.conf import settings
from django.template.loader import get_template
from django.test import SimpleTestCase


class StatisticsGlobalImportanceV14D3Tests(SimpleTestCase):
    def test_statistics_template_compiles(self):
        get_template("predictor/statistics.html")

    def test_global_importance_copy_is_source_bilingual(self):
        source = (
            settings.BASE_DIR
            / "template"
            / "predictor"
            / "statistics.html"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "V14D3_GLOBAL_IMPORTANCE_COPY_SOURCE",
            source,
        )
        self.assertIn(
            "This measure describes what the active MLP uses for prediction.",
            source,
        )
        self.assertIn(
            "Cette mesure décrit ce que le MLP actif utilise pour prédire.",
            source,
        )
        self.assertIn(
            "It differs from “Observed Associations” and is not evidence of causality.",
            source,
        )

    def test_global_importance_alert_no_longer_contains_fragmented_copy(self):
        source = (
            settings.BASE_DIR
            / "template"
            / "predictor"
            / "statistics.html"
        ).read_text(encoding="utf-8")

        alert_pattern = re.compile(
            r'<div\b[^>]*class=(["\'])'
            r'(?=[^"\']*\balert\b)'
            r'(?=[^"\']*\balert-light\b)'
            r'(?=[^"\']*\bborder\b)'
            r'[^"\']*\1[^>]*>'
            r'(?P<body>.*?)'
            r'</div>',
            re.IGNORECASE | re.DOTALL,
        )

        candidates = [
            match.group("body")
            for match in alert_pattern.finditer(source)
            if (
                "active MLP uses for prediction" in match.group("body")
                or "MLP actif utilise pour prédire" in match.group("body")
            )
        ]

        self.assertEqual(len(candidates), 1)

        body = candidates[0]

        self.assertIn(
            "This measure describes what the active MLP uses for prediction.",
            body,
        )
        self.assertIn(
            "Cette mesure décrit ce que le MLP actif utilise pour prédire.",
            body,
        )
