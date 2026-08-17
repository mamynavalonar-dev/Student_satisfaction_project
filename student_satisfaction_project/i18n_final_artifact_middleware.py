from __future__ import annotations

import re


_WARNING_PATTERNS = (
    (
        re.compile(
            r"Enregistré\s+avec\s+scikit-learn",
            re.IGNORECASE,
        ),
        "Saved with scikit-learn",
    ),
    (
        re.compile(
            r"environnement\s+actuel",
            re.IGNORECASE,
        ),
        "current environment",
    ),
    (
        re.compile(
            r"Réentra[iî]ne[rz]\s+ce\s+modèle\s+avant\s+de\s+"
            r"l(?:['’]|&apos;|&#39;|&#x27;)activer\.?",
            re.IGNORECASE,
        ),
        "Retrain this model before activation.",
    ),
)


def translate_final_artifact_warning(html: str) -> str:
    """Translate the final legacy-artifact warning fragments in rendered EN HTML."""
    translated = html

    for pattern, replacement in _WARNING_PATTERNS:
        translated = pattern.sub(
            replacement,
            translated,
        )

    return translated


class FinalEnglishArtifactWarningMiddleware:
    """
    Final response pass for the one remaining legacy artifact warning.

    The middleware is intentionally first in MIDDLEWARE so its response
    processing runs last. It modifies English HTML only.
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

        translated = translate_final_artifact_warning(
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
