from __future__ import annotations

import re


_STATISTICS_RESIDUALS = (
    (
        re.compile(
            r"Cette\s+mesure\s+décrit\s+ce\s+que\s+le",
            re.IGNORECASE,
        ),
        "This measure describes what the",
    ),
    (
        re.compile(
            r"Elle\s+est\s+différente\s+des",
            re.IGNORECASE,
        ),
        "It differs from",
    ),
    (
        re.compile(
            r"et\s+ne\s+constitue\s+pas\s+une\s+preuve\s+de\s+causalité\.?",
            re.IGNORECASE,
        ),
        "and is not evidence of causality.",
    ),
)


def translate_statistics_lastmile_html(html: str) -> str:
    """Translate only the remaining Statistics display fragments."""
    translated = html

    for pattern, replacement in _STATISTICS_RESIDUALS:
        translated = pattern.sub(
            replacement,
            translated,
        )

    return translated


class StatisticsEnglishLastMileMiddleware:
    """
    Final English HTML cleanup for the Statistics explanatory copy.

    No JSON/API payload and no French response is modified.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        language = str(
            getattr(request, "LANGUAGE_CODE", "") or ""
        ).lower()

        if not language.startswith("en"):
            return response

        if getattr(response, "streaming", False):
            return response

        content_type = str(
            response.get("Content-Type", "") or ""
        ).lower()

        if not content_type.startswith("text/html"):
            return response

        charset = getattr(response, "charset", None) or "utf-8"

        try:
            original = response.content.decode(charset)
        except (UnicodeDecodeError, LookupError):
            original = response.content.decode(
                "utf-8",
                errors="replace",
            )
            charset = "utf-8"

        translated = translate_statistics_lastmile_html(
            original
        )

        if translated == original:
            return response

        response.content = translated.encode(charset)

        if response.has_header("ETag"):
            del response["ETag"]

        if response.has_header("Content-Length"):
            response["Content-Length"] = str(
                len(response.content)
            )

        return response
