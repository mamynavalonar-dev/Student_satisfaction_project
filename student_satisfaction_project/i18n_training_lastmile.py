from __future__ import annotations

import re


_SKLEARN_WARNING = re.compile(
    r"Enregistré avec scikit-learn\s+"
    r"(?P<saved>[0-9]+(?:\.[0-9]+)*),\s*"
    r"environnement actuel\s+"
    r"(?P<current>[0-9]+(?:\.[0-9]+)*)\.\s*"
    r"Réentraînez\s+ce modèle avant de l['’]activer\.?",
    re.IGNORECASE,
)

_SKLEARN_WARNING_ALT = re.compile(
    r"Enregistré avec scikit-learn\s+"
    r"(?P<saved>[0-9]+(?:\.[0-9]+)*),\s*"
    r"environnement actuel\s+"
    r"(?P<current>[0-9]+(?:\.[0-9]+)*)\.\s*"
    r"Réentra[iî]ner\s+ce modèle avant de l['’]activer\.?",
    re.IGNORECASE,
)

_REQUIRED_COURSE_TYPES = re.compile(
    r"<code>\s*présentiel\s*</code>\s*,\s*"
    r"<code>\s*distanciel\s*</code>\s*,\s*"
    r"<code>\s*hybride\s*</code>",
    re.IGNORECASE,
)


def translate_training_lastmile_html(html: str) -> str:
    """
    Final display-only English cleanup for Training.

    Stored values and accepted CSV tokens are not changed.
    The original technical values are retained in data-csv-value attributes.
    """
    def sklearn_replacement(match):
        return (
            f"Saved with scikit-learn {match.group('saved')}; "
            f"current environment {match.group('current')}. "
            "Retrain this model before activation."
        )

    html = _SKLEARN_WARNING.sub(
        sklearn_replacement,
        html,
    )
    html = _SKLEARN_WARNING_ALT.sub(
        sklearn_replacement,
        html,
    )

    html = _REQUIRED_COURSE_TYPES.sub(
        '<code data-csv-value="présentiel">In person</code>, '
        '<code data-csv-value="distanciel">Online</code>, '
        '<code data-csv-value="hybride">Hybrid</code>',
        html,
    )

    return html


class TrainingEnglishLastMileMiddleware:
    """
    Runs after the existing residual translation on the response path.

    Only English HTML responses are modified.
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

        translated = translate_training_lastmile_html(
            original
        )

        if translated != original:
            response.content = translated.encode(charset)

            if response.has_header("ETag"):
                del response["ETag"]

            if response.has_header("Content-Length"):
                response["Content-Length"] = str(
                    len(response.content)
                )

        return response
