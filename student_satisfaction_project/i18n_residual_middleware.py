from __future__ import annotations

import json
import re
from typing import Any


# Final, display-only English residual translation.
# This middleware intentionally does NOT alter templates, database values,
# model artifacts, CSV tokens, or API business payloads.
#
# It runs only when LocaleMiddleware has selected English.
#
# The rules below are deliberately explicit.  They cover residual French
# strings left by legacy templates / historical records / inline JavaScript.


_TEXT_RULES: tuple[tuple[re.Pattern[str], str | object], ...] = (

    # ------------------------------------------------------------------
    # Notification center — stored French titles/messages
    # ------------------------------------------------------------------
    (
        re.compile(r"\bConnexion réussie\b", re.IGNORECASE),
        "Login successful",
    ),
    (
        re.compile(
            r"\bBienvenue\s+([^.<\n]+)\.\s*Votre session est active\.",
            re.IGNORECASE,
        ),
        lambda m: f"Welcome {m.group(1).strip()}. Your session is active.",
    ),
    (
        re.compile(r"\bModèle MLP entraîné\b", re.IGNORECASE),
        "MLP model trained",
    ),
    (
        re.compile(
            r"Entraînement\s+#(\d+)\s+terminé\s*:\s*"
            r"Accuracy test\s+([0-9.,]+)%\s*,\s*"
            r"F1 test\s+([0-9.,]+)%\s*,\s*"
            r"F1 CV\s+([0-9.,]+)%\s*±\s*([0-9.,]+)%\s*,\s*"
            r"(\d+)\s+échantillons?\.?",
            re.IGNORECASE,
        ),
        lambda m: (
            f"Training #{m.group(1)} completed: "
            f"test accuracy {m.group(2)}%, "
            f"test F1 {m.group(3)}%, "
            f"CV F1 {m.group(4)}% ± {m.group(5)}%, "
            f"{int(m.group(6)):,} samples."
        ),
    ),
    (
        re.compile(r"\bNouvelle prédiction\b", re.IGNORECASE),
        "New prediction",
    ),
    (
        re.compile(
            r"\bAvis\s+#(\d+)\s*:\s*Satisfait\s*"
            r"\(([0-9.,]+)%\s+de confiance\)\.?",
            re.IGNORECASE,
        ),
        lambda m: (
            f"Feedback #{m.group(1)}: "
            f"Satisfied ({m.group(2)}% confidence)."
        ),
    ),
    (
        re.compile(
            r"\bAvis\s+#(\d+)\s*:\s*Non satisfait\s*"
            r"\(([0-9.,]+)%\s+de confiance\)\.?",
            re.IGNORECASE,
        ),
        lambda m: (
            f"Feedback #{m.group(1)}: "
            f"Dissatisfied ({m.group(2)}% confidence)."
        ),
    ),
    (
        re.compile(r"\bPrédiction enregistrée\b", re.IGNORECASE),
        "Prediction recorded",
    ),
    (
        re.compile(r"\bModèle activé\b", re.IGNORECASE),
        "Model activated",
    ),
    (
        re.compile(r"\bExport terminé\b", re.IGNORECASE),
        "Export completed",
    ),
    (
        re.compile(r"\bDonnées exportées\b", re.IGNORECASE),
        "Data exported",
    ),
    (
        re.compile(r"\bCompte créé\b", re.IGNORECASE),
        "Account created",
    ),
    (
        re.compile(r"\bMot de passe modifié\b", re.IGNORECASE),
        "Password changed",
    ),

    # Force absolute notification timestamps to an English 12-hour clock.
    (
        re.compile(
            r"date\.toLocaleString\(\('en'\s*===\s*'en'\s*\?\s*"
            r"'en-US'\s*:\s*'fr-FR'\),\s*"
            r"\{\s*dateStyle:\s*'short'\s*,\s*"
            r"timeStyle:\s*'short'\s*\}\)"
        ),
        (
            "date.toLocaleString('en-US', { "
            "month: 'short', day: 'numeric', year: 'numeric', "
            "hour: 'numeric', minute: '2-digit', hour12: true })"
        ),
    ),
    # ------------------------------------------------------------------
    # Global shell / notifications / authentication
    # ------------------------------------------------------------------
    (
        re.compile(
            r"Connexion réussie\.\s*Bon retour,\s*([^<\n.]+)\.?",
            re.IGNORECASE,
        ),
        lambda m: f"Login successful. Welcome back, {m.group(1).strip()}.",
    ),
    (
        re.compile(r"\bThème Automatique\b", re.IGNORECASE),
        "Theme Automatic",
    ),
    (
        re.compile(r"Notifications\s+—\s+\$\{value\}\s+non lue\(s\)", re.IGNORECASE),
        "Notifications — ${value} unread",
    ),
    (
        re.compile(r"\bLecture notification\s*:", re.IGNORECASE),
        "Notification read:",
    ),

    # ------------------------------------------------------------------
    # Training — title, form help and automatic selection
    # ------------------------------------------------------------------
    (
        re.compile(r"Training\s*-\s*Modèle IA", re.IGNORECASE),
        "Training - AI Model",
    ),
    (
        re.compile(
            r"Le fichier CSV doit contenir les colonnes\s*:",
            re.IGNORECASE,
        ),
        "The CSV file must contain the columns:",
    ),
    (
        re.compile(r"satisfaction\s*\(\s*0\s+ou\s+1\s*\)", re.IGNORECASE),
        "satisfaction (0 or 1)",
    ),
    (
        re.compile(
            r"Notes optionnelles sur cet entraînement\.\.\.",
            re.IGNORECASE,
        ),
        "Optional notes for this training run...",
    ),
    (
        re.compile(r"\bSélection automatique\s*:", re.IGNORECASE),
        "Automatic selection:",
    ),
    (
        re.compile(
            r"\b(?:le|Le) CSV est d['’]abord séparé en train 80\s*%\s*/\s*"
            r"test final 20\s*%\.",
            re.IGNORECASE,
        ),
        "The CSV is first split into 80% training / 20% final test.",
    ),
    (
        re.compile(
            r"Le grid-search compare 4 configurations du MLP par validation "
            r"croisée stratifiée\s*(?:à\s*)?3 plis\s*"
            r"uniquement\s+(?:sur|of)\s+le train,\s*"
            r"puis le meilleur modèle est évalué une seule fois\s+"
            r"(?:sur|of)\s+le test final\.",
            re.IGNORECASE,
        ),
        (
            "Grid search compares 4 MLP configurations using 3-fold "
            "stratified cross-validation on the training set only, then "
            "the best model is evaluated once on the final test set."
        ),
    ),

    # ------------------------------------------------------------------
    # Required data format
    # ------------------------------------------------------------------
    (
        re.compile(r"(?<=>)\s*Entier\s*(?=<)", re.IGNORECASE),
        "Integer",
    ),
    (
        re.compile(r"(?<=>)\s*Texte\s*(?=<)", re.IGNORECASE),
        "Text",
    ),
    (
        re.compile(r"(?<=>)\s*Binaire\s*(?=<)", re.IGNORECASE),
        "Binary",
    ),
    (
        re.compile(r"\(satisfait\)\s*ou\s*", re.IGNORECASE),
        "satisfied / ",
    ),
    (
        re.compile(r"\(non satisfait\)", re.IGNORECASE),
        "dissatisfied",
    ),

    # ------------------------------------------------------------------
    # Current model status / neural-network configuration
    # ------------------------------------------------------------------
    (
        re.compile(r"\bAucun Modèle Chargé\b", re.IGNORECASE),
        "No Model Loaded",
    ),
    (
        re.compile(
            r"(?:No model|Aucun modèle)\s+n['’]est actuellement chargé\.\s*"
            r"Veuillez en entraîner un pour activer la fonctionnalité "
            r"de prédiction\.",
            re.IGNORECASE,
        ),
        "No model is currently loaded. Train one to enable prediction.",
    ),
    (
        re.compile(r"\bCouches candidates\s*:", re.IGNORECASE),
        "Candidate layers:",
    ),
    (
        re.compile(r"\bAlpha candidat\s*:", re.IGNORECASE),
        "Candidate alpha:",
    ),
    (
        re.compile(r"\bEarly Stopping\s*:", re.IGNORECASE),
        "Early Stopping:",
    ),
    (
        re.compile(r"(?<=>)\s*Activé\s*(?=<)", re.IGNORECASE),
        "Enabled",
    ),
    (
        re.compile(
            r"\(64,\s*32\)\s+ou\s+\(128,\s*64,\s*32\)",
            re.IGNORECASE,
        ),
        "(64, 32) or (128, 64, 32)",
    ),
    (
        re.compile(r"0\.0001\s+ou\s+0\.001", re.IGNORECASE),
        "0.0001 or 0.001",
    ),
    (
        re.compile(r"\bAucun entraînement précédent\b", re.IGNORECASE),
        "No previous training",
    ),

    # ------------------------------------------------------------------
    # Model management / historical values
    # ------------------------------------------------------------------
    (
        re.compile(
            r"Activation possible uniquement si le fichier\s+\.?joblib "
            r"existe et si son format est compatible\.",
            re.IGNORECASE,
        ),
        (
            "Activation is only possible when the .joblib file exists "
            "and its format is compatible."
        ),
    ),
    (
        re.compile(r"\b(\d+)\s+modèles\b", re.IGNORECASE),
        lambda m: f"{m.group(1)} models",
    ),
    (
        re.compile(r"\bAucun entraînement enregistré\.", re.IGNORECASE),
        "No training run recorded.",
    ),
    (
        re.compile(
            r"[«“]\s*—\s*[»”]?\s*signifie qu['’]un ancien artefact "
            r"ne contient pas les métriques détaillées\.\s*"
            r"L['’]activation ne supprime aucun fichier et ne réentraîne "
            r"pas le réseau\.",
            re.IGNORECASE,
        ),
        (
            "“—” means that a legacy artifact does not contain detailed "
            "metrics. Activation does not delete any file and does not "
            "retrain the network."
        ),
    ),
    (
        re.compile(
            r"Ce graphique compare la précision des entraînements successifs,\s*"
            r"du plus ancien au plus récent\.\s*"
            r"Chaque point correspond à un entraînement distinct\s*;\s*"
            r"il ne s['’]agit pas d['’]un apprentissage continu\.",
            re.IGNORECASE,
        ),
        (
            "This chart compares successive training accuracies from oldest "
            "to newest. Each point represents a distinct training run; this "
            "is not continuous learning."
        ),
    ),

    # Historical training notes
    (
        re.compile(r"\bEntraînement V12B\b", re.IGNORECASE),
        "V12B training",
    ),
    (
        re.compile(r"\bEntraînement final V8\b", re.IGNORECASE),
        "Final V8 training",
    ),
    (
        re.compile(r"\btest final après correction\b", re.IGNORECASE),
        "final test after correction",
    ),
    (
        re.compile(r"\bdu pipeline IA\b", re.IGNORECASE),
        "of the ML pipeline",
    ),
    (
        re.compile(r"\bpipeline IA\b", re.IGNORECASE),
        "ML pipeline",
    ),
    (
        re.compile(r"\bdataset synthétique\b", re.IGNORECASE),
        "synthetic dataset",
    ),
    (
        re.compile(r"\bsélection automatique\b", re.IGNORECASE),
        "automatic selection",
    ),
    (
        re.compile(r"\b(\d+)\s+plis stratifiés\b", re.IGNORECASE),
        lambda m: f"{m.group(1)} stratified folds",
    ),
    (
        re.compile(r"\b(\d+)\s+plis\b", re.IGNORECASE),
        lambda m: f"{m.group(1)} folds",
    ),
    (
        re.compile(r"\b(\([^)]*\))\s+neurones\b", re.IGNORECASE),
        lambda m: f"{m.group(1)} neurons",
    ),
    (
        re.compile(r"\bconforme\b", re.IGNORECASE),
        "compliant",
    ),
    (
        re.compile(
            r"Enregistré avec scikit-learn\s*"
            r"([0-9]+(?:\.[0-9]+)*),?\s*"
            r"environnement actuel\s*"
            r"([0-9]+(?:\.[0-9]+)*)\.?\s*"
            r"Réentra[iî]ne[rz]?\s+ce modèle avant de l['’]activer\.?",
            re.IGNORECASE,
        ),
        lambda m: (
            f"Saved with scikit-learn {m.group(1)}; "
            f"current environment {m.group(2)}. "
            "Retrain this model before activation."
        ),
    ),
    (
        re.compile(r"\bFichier joblib introuvable\.?", re.IGNORECASE),
        "Joblib file not found.",
    ),

    # ------------------------------------------------------------------
    # Training JavaScript visible messages
    # ------------------------------------------------------------------
    (
        re.compile(r"\bTraining en cours\.\.\.", re.IGNORECASE),
        "Training in progress...",
    ),
    (
        re.compile(
            r"L(?:\\['’]|['’])entraînement a commencé\.\.\.",
            re.IGNORECASE,
        ),
        "Training has started...",
    ),
    (
        re.compile(
            r"Le grid-search exécute plusieurs entraînements par validation "
            r"croisée\.\s*Le traitement peut prendre plusieurs minutes\s*;\s*"
            r"ne fermez pas cette page\.",
            re.IGNORECASE,
        ),
        (
            "Grid search runs multiple training jobs using cross-validation. "
            "Processing may take several minutes; do not close this page."
        ),
    ),
    (
        re.compile(
            r"Veuillez sélectionner un fichier au format CSV\.",
            re.IGNORECASE,
        ),
        "Please select a CSV file.",
    ),
    (
        re.compile(r"Accuracy du Modèle\s*\(%\)", re.IGNORECASE),
        "Model Accuracy (%)",
    ),
    (
        re.compile(
            r"Aucune donnée d(?:\\['’]|['’])évolution disponible",
            re.IGNORECASE,
        ),
        "No evolution data available",
    ),
    (
        re.compile(
            r"Error lors de l(?:\\['’]|['’])analyse des données "
            r"de l(?:\\['’]|['’])historique\s*:",
            re.IGNORECASE,
        ),
        "Error while parsing training-history data:",
    ),

    # ------------------------------------------------------------------
    # Statistics — limited sample / global importance
    # ------------------------------------------------------------------
    (
        re.compile(r"\bÉchantillon encore limité\s*:", re.IGNORECASE),
        "Limited sample:",
    ),
    (
        re.compile(
            r"seulement\s+(\d+)\s+prédiction(?:s)?\s+"
            r"enregistrée(?:s)?\.",
            re.IGNORECASE,
        ),
        lambda m: (
            f"only {m.group(1)} recorded "
            f"prediction{'s' if m.group(1) != '1' else ''}."
        ),
    ),
    (
        re.compile(
            r"Les taux par sous-groupes et les associations observées peuvent "
            r"varier fortement avec si peu de données\.\s*"
            r"Ils doivent être interprétés comme des indications descriptives,\s*"
            r"pas comme des conclusions générales\.",
            re.IGNORECASE,
        ),
        (
            "Subgroup rates and observed associations may vary substantially "
            "with so little data. They should be interpreted as descriptive "
            "indications, not general conclusions."
        ),
    ),
    (
        re.compile(r"Cette mesure décrit ce que le\s*", re.IGNORECASE),
        "This measure describes what the ",
    ),
    (
        re.compile(r"MLP actif utilise pour prédire", re.IGNORECASE),
        "active MLP uses for prediction",
    ),
    (
        re.compile(
            r"Elle est différente des\s*[«“]\s*"
            r"(?:Observed Associations|Associations observées)\s*[»”]\s*"
            r"et ne constitue pas une preuve de causalité\.",
            re.IGNORECASE,
        ),
        (
            "It differs from “Observed Associations” and is not evidence "
            "of causality."
        ),
    ),
    (
        re.compile(r"\bÉcart-type\s*:", re.IGNORECASE),
        "Standard deviation:",
    ),
    (
        re.compile(r"\bMéthode\s*:", re.IGNORECASE),
        "Method:",
    ),
    (
        re.compile(r"\bImportance par permutation\b", re.IGNORECASE),
        "Permutation importance",
    ),
    (
        re.compile(r"\bRéférence\s*:", re.IGNORECASE),
        "Reference:",
    ),
    (
        re.compile(
            r"\bjeu de test enregistré avec le modèle\b",
            re.IGNORECASE,
        ),
        "test set stored with the model",
    ),
    (
        re.compile(r"\bImportance globale indisponible\s*:", re.IGNORECASE),
        "Global importance unavailable:",
    ),
    (
        re.compile(r"\bPas assez de données\.", re.IGNORECASE),
        "Not enough data.",
    ),
    (
        re.compile(
            r"Ancien artefact\s*:\s*réentraînez le modèle pour disposer "
            r"de Precision,\s*Recall et F1\.",
            re.IGNORECASE,
        ),
        "Legacy artifact: retrain the model to obtain Precision, Recall and F1.",
    ),
    (
        re.compile(r"\bAucun modèle actif\b", re.IGNORECASE),
        "No active model",
    ),
    (
        re.compile(r"\bEntraîner un modèle\b", re.IGNORECASE),
        "Train a model",
    ),

    # ------------------------------------------------------------------
    # About-the-model residual seen after previous partial translations
    # ------------------------------------------------------------------
    (
        re.compile(r"Ce prédicteur utilise un\s*", re.IGNORECASE),
        "This predictor uses an ",
    ),
    (
        re.compile(r"réseau de neurones MLP", re.IGNORECASE),
        "MLP neural network",
    ),
    (
        re.compile(
            r"entraîné(?:\s+of)?\s+des données d['’]avis étudiants\.?",
            re.IGNORECASE,
        ),
        "trained on student feedback data.",
    ),
)



_MONTHS_EN = (
    "",
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
)


def _format_12_hour(hour: int, minute: int) -> str:
    suffix = "AM" if hour < 12 else "PM"
    display_hour = hour % 12 or 12
    return f"{display_hour}:{minute:02d} {suffix}"


def _replace_dmy_datetime(match: re.Match[str]) -> str:
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))

    if not (
        1 <= month <= 12
        and 1 <= day <= 31
        and 0 <= hour <= 23
        and 0 <= minute <= 59
    ):
        return match.group(0)

    return (
        f"{_MONTHS_EN[month]} {day}, {year}, "
        f"{_format_12_hour(hour, minute)}"
    )


def _replace_ymd_datetime(match: re.Match[str]) -> str:
    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    hour = int(match.group(4))
    minute = int(match.group(5))

    if not (
        1 <= month <= 12
        and 1 <= day <= 31
        and 0 <= hour <= 23
        and 0 <= minute <= 59
    ):
        return match.group(0)

    return (
        f"{_MONTHS_EN[month]} {day}, {year}, "
        f"{_format_12_hour(hour, minute)}"
    )


def _replace_dmy_date(match: re.Match[str]) -> str:
    day = int(match.group(1))
    month = int(match.group(2))
    year = int(match.group(3))

    if not (1 <= month <= 12 and 1 <= day <= 31):
        return match.group(0)

    return f"{_MONTHS_EN[month]} {day}, {year}"


_DMY_DATETIME_RE = re.compile(
    r"(?<![\d/])"
    r"(\d{1,2})/(\d{1,2})/(\d{4})"
    r"\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)"
    r"(?:\:[0-5]\d)?"
    r"(?!\d)"
)

_YMD_DATETIME_RE = re.compile(
    r"(?<![\d-])"
    r"(\d{4})-(\d{1,2})-(\d{1,2})"
    r"\s+"
    r"([01]?\d|2[0-3]):([0-5]\d)"
    r"(?:\:[0-5]\d)?"
    r"(?!\d)"
)

_DMY_DATE_RE = re.compile(
    r"(?<![\d/])"
    r"(\d{1,2})/(\d{1,2})/(\d{4})"
    r"(?![\d/])"
)

_SCRIPT_STYLE_RE = re.compile(
    r"(<script\b.*?</script>|<style\b.*?</style>)",
    re.IGNORECASE | re.DOTALL,
)


def translate_visible_html_datetimes(html: str) -> str:
    """
    Convert visible server-rendered dates/times to an English display:
    16/08/2026 16:30 -> Aug 16, 2026, 4:30 PM.

    Script/style blocks are deliberately left unchanged.
    """
    parts = _SCRIPT_STYLE_RE.split(html)

    for index, part in enumerate(parts):
        lowered = part.lstrip().lower()
        if lowered.startswith("<script") or lowered.startswith("<style"):
            continue

        part = _DMY_DATETIME_RE.sub(_replace_dmy_datetime, part)
        part = _YMD_DATETIME_RE.sub(_replace_ymd_datetime, part)
        part = _DMY_DATE_RE.sub(_replace_dmy_date, part)
        parts[index] = part

    return "".join(parts)

def translate_residual_text(value: str) -> str:
    """Translate known residual French UI strings into English."""
    text = value

    # V14C225_DOT_JOBLIB_MESSAGE
    from django.utils.translation import get_language as _v14c225_get_language

    if str(_v14c225_get_language() or '').lower().startswith('en'):
        text = re.sub(
            r"Fichier\s+\.joblib\s+introuvable\.?",
            "Missing .joblib file.",
            text,
            flags=re.IGNORECASE,
        )

    # V14C220_LOGIN_TOAST_FIX
    # Normalize the complete login toast before generic rules.
    text = re.sub(
        r"(?:Connexion réussie|Login successful)\.\s*"
        r"Bon retour,\s*([A-Za-z0-9@._+\-]+?)\."
        r"(?=\s|<|$)",
        lambda match: (
            "Login successful. Welcome back, "
            + match.group(1)
            + "."
        ),
        text,
        flags=re.IGNORECASE,
    )

    for pattern, replacement in _TEXT_RULES:
        text = pattern.sub(replacement, text)

    return text


def _translate_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return translate_residual_text(value)
    if isinstance(value, list):
        return [_translate_json_value(item) for item in value]
    if isinstance(value, dict):
        return {
            key: _translate_json_value(item)
            for key, item in value.items()
        }
    return value


class EnglishResidualTranslationMiddleware:
    """
    Last-mile translation for legacy UI strings.

    LocaleMiddleware must run before this middleware on requests.
    Only English responses are changed.
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

        if content_type.startswith("text/html"):
            charset = getattr(response, "charset", None) or "utf-8"

            try:
                original = response.content.decode(charset)
            except (UnicodeDecodeError, LookupError):
                original = response.content.decode(
                    "utf-8",
                    errors="replace",
                )
                charset = "utf-8"

            translated = translate_visible_html_datetimes(
                translate_residual_text(original)
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

        # Notification feed is populated asynchronously after the HTML load.
        # Translate only that JSON surface, not the REST API in general.
        if (
            "application/json" in content_type
            and "notification" in request.path.lower()
        ):
            try:
                payload = json.loads(
                    response.content.decode("utf-8")
                )
            except (UnicodeDecodeError, json.JSONDecodeError):
                return response

            translated_payload = _translate_json_value(payload)
            encoded = json.dumps(
                translated_payload,
                ensure_ascii=False,
                separators=(",", ":"),
            ).encode("utf-8")

            response.content = encoded
            if response.has_header("ETag"):
                del response["ETag"]
            if response.has_header("Content-Length"):
                response["Content-Length"] = str(
                    len(encoded)
                )

        return response
