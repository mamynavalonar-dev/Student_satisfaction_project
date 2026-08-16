# predictor/utils_explain.py
from __future__ import annotations

import logging
import math
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.inspection import permutation_importance

from .neural_network_model import (
    ALLOWED_LEVELS,
    ALLOWED_TYPES,
    BASE_DIR,
    FEATURE_COLUMNS,
    NUMERIC_COLUMNS,
    _normalize_type,
    _validate_prediction_input,
)

logger = logging.getLogger(__name__)

FEATURE_LABELS = {
    "qualite_enseignement": "Qualité de l'enseignement",
    "charge_travail": "Charge de travail",
    "interactivite": "Interactivité",
    "type_cours": "Type de cours",
    "niveau_etudiant": "Niveau étudiant",
}

_GLOBAL_IMPORTANCE_CACHE = {}


def _pipeline_from_model_data(model_data):
    if not isinstance(model_data, dict):
        return None
    pipeline = model_data.get("pipeline")
    if pipeline is None or not hasattr(pipeline, "predict_proba"):
        return None
    return pipeline


def _normalise_feature_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        raise ValueError("Le jeu de référence d'explication est vide.")

    missing = [column for column in FEATURE_COLUMNS if column not in frame.columns]
    if missing:
        raise ValueError(
            "Colonnes manquantes dans le jeu de référence : " + ", ".join(missing)
        )

    data = frame[FEATURE_COLUMNS].copy()

    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"Valeurs invalides dans '{column}'.")
        if not ((values >= 1) & (values <= 7)).all():
            raise ValueError(f"'{column}' doit rester compris entre 1 et 7.")
        data[column] = values.astype(int)

    data["type_cours"] = data["type_cours"].map(_normalize_type)
    invalid_types = sorted(set(data["type_cours"]) - ALLOWED_TYPES)
    if invalid_types:
        raise ValueError(
            "Types de cours invalides dans le jeu de référence : "
            + ", ".join(invalid_types)
        )

    data["niveau_etudiant"] = (
        data["niveau_etudiant"].astype(str).str.strip().str.upper()
    )
    invalid_levels = sorted(set(data["niveau_etudiant"]) - ALLOWED_LEVELS)
    if invalid_levels:
        raise ValueError(
            "Niveaux invalides dans le jeu de référence : "
            + ", ".join(invalid_levels)
        )

    return data


def _artifact_reference(model_data):
    reference = model_data.get("explanation_reference") if isinstance(model_data, dict) else None
    if not isinstance(reference, dict):
        return None

    features = reference.get("features")
    target = reference.get("target")
    if not isinstance(features, list) or not isinstance(target, list):
        return None
    if not features or len(features) != len(target):
        return None

    frame = _normalise_feature_frame(pd.DataFrame(features))
    y = pd.Series(target, dtype="int64")
    if not set(y.unique()).issubset({0, 1}):
        return None
    return frame, y, "jeu de test enregistré avec le modèle"


def _artifact_background(model_data):
    background = model_data.get("explanation_background") if isinstance(model_data, dict) else None
    if not isinstance(background, list) or not background:
        return None
    try:
        return _normalise_feature_frame(pd.DataFrame(background))
    except Exception:
        logger.exception("Background d'explication invalide dans l'artefact")
        return None


def _candidate_reference_paths() -> list[Path]:
    data_dir = BASE_DIR / "data"
    if not data_dir.is_dir():
        return []
    return sorted(
        data_dir.glob("satisfaction_etudiants_synthetiques_v8_*.csv"),
        key=lambda path: (path.stat().st_mtime_ns, path.name),
        reverse=True,
    )


@lru_cache(maxsize=4)
def _read_reference_csv(path_string: str, mtime_ns: int):
    del mtime_ns
    path = Path(path_string)
    frame = pd.read_csv(path, encoding="utf-8-sig")
    if "satisfaction" not in frame.columns:
        raise ValueError("Le CSV de référence ne contient pas la cible satisfaction.")

    features = _normalise_feature_frame(frame)
    target = pd.to_numeric(frame["satisfaction"], errors="coerce")
    if target.isna().any() or not set(target.astype(int).unique()).issubset({0, 1}):
        raise ValueError("La cible du CSV de référence doit contenir uniquement 0 et 1.")

    return features, target.astype(int)


def _fallback_reference():
    for path in _candidate_reference_paths():
        try:
            features, target = _read_reference_csv(
                str(path.resolve()),
                path.stat().st_mtime_ns,
            )
            return features.copy(), target.copy(), f"{path.name} (référence locale)"
        except Exception:
            logger.exception("Impossible d'utiliser le CSV de référence %s", path)
    return None


def _background_for_local_explanation(model_data, max_rows: int = 32):
    background = _artifact_background(model_data)
    source = "échantillon d'entraînement enregistré avec le modèle"

    if background is None:
        fallback = _fallback_reference()
        if fallback is None:
            return None, None
        background, _target, source = fallback

    if len(background) > max_rows:
        background = background.sample(n=max_rows, random_state=42).reset_index(drop=True)
    else:
        background = background.reset_index(drop=True)

    return background, source


def _positive_probability(pipeline, frame: pd.DataFrame) -> np.ndarray:
    probabilities = np.asarray(pipeline.predict_proba(frame), dtype=float)
    if probabilities.ndim != 2:
        raise ValueError("Le modèle n'a pas retourné une matrice de probabilités.")

    classes = getattr(pipeline, "classes_", None)
    if classes is None and hasattr(pipeline, "named_steps"):
        classifier = pipeline.named_steps.get("classifier")
        classes = getattr(classifier, "classes_", None)

    if classes is None:
        raise ValueError("Les classes du modèle sont indisponibles.")

    class_values = [int(value) for value in classes]
    if 1 not in class_values:
        raise ValueError("La classe 1 (satisfait) est absente du modèle.")

    return probabilities[:, class_values.index(1)]


def _display_value(feature: str, value) -> str:
    if feature in NUMERIC_COLUMNS:
        return f"{int(value)}/7"
    if feature == "type_cours":
        return str(value).capitalize()
    return str(value)


def get_local_explanation(model_data, input_data, max_background_rows: int = 32):
    # Valeurs de Shapley exactes des 5 variables sur P(satisfait).
    pipeline = _pipeline_from_model_data(model_data)
    if pipeline is None:
        return {
            "available": False,
            "reason": "L'explication détaillée nécessite un modèle récent au format pipeline.",
        }

    input_frame = _validate_prediction_input(input_data)
    input_row = input_frame.iloc[0]

    background, source = _background_for_local_explanation(
        model_data,
        max_rows=max_background_rows,
    )
    if background is None or background.empty:
        return {
            "available": False,
            "reason": "Aucun jeu de référence n'est disponible pour calculer l'explication.",
        }

    feature_count = len(FEATURE_COLUMNS)
    coalition_values = {}

    for size in range(feature_count + 1):
        for subset_tuple in combinations(FEATURE_COLUMNS, size):
            subset = frozenset(subset_tuple)
            evaluation = background.copy()
            for feature in subset:
                evaluation[feature] = input_row[feature]
            coalition_values[subset] = float(
                _positive_probability(pipeline, evaluation).mean()
            )

    factorial_m = math.factorial(feature_count)
    contributions = {}
    all_features = frozenset(FEATURE_COLUMNS)

    for feature in FEATURE_COLUMNS:
        other_features = [name for name in FEATURE_COLUMNS if name != feature]
        shap_value = 0.0

        for size in range(feature_count):
            weight = (
                math.factorial(size)
                * math.factorial(feature_count - size - 1)
                / factorial_m
            )
            for subset_tuple in combinations(other_features, size):
                subset = frozenset(subset_tuple)
                with_feature = subset | {feature}
                shap_value += weight * (
                    coalition_values[with_feature] - coalition_values[subset]
                )

        contributions[feature] = float(shap_value * 100.0)

    baseline_probability = float(coalition_values[frozenset()] * 100.0)
    predicted_probability = float(coalition_values[all_features] * 100.0)
    contribution_sum = float(sum(contributions.values()))
    delta = predicted_probability - baseline_probability
    additivity_error = abs(delta - contribution_sum)

    max_abs = max((abs(value) for value in contributions.values()), default=0.0)
    scale = max_abs if max_abs > 1e-12 else 1.0

    items = []
    for feature in FEATURE_COLUMNS:
        contribution = contributions[feature]
        bar_width = min(48.0, abs(contribution) / scale * 48.0)
        direction = "positive" if contribution >= 0 else "negative"
        bar_left = 50.0 if contribution >= 0 else 50.0 - bar_width
        items.append(
            {
                "feature": feature,
                "label": FEATURE_LABELS[feature],
                "value": _display_value(feature, input_row[feature]),
                "contribution": round(contribution, 3),
                "magnitude": abs(contribution),
                "direction": direction,
                "bar_left": round(bar_left, 2),
                "bar_width": round(bar_width, 2),
            }
        )

    items.sort(key=lambda item: item["magnitude"], reverse=True)

    return {
        "available": True,
        "items": items,
        "baseline_probability": round(baseline_probability, 3),
        "predicted_probability": round(predicted_probability, 3),
        "delta": round(delta, 3),
        "additivity_error": round(additivity_error, 8),
        "reference_source": source,
        "method": "Valeurs de Shapley exactes sur la probabilité d'être satisfait",
    }


def _importance_cache_key(model_data, source: str):
    if not isinstance(model_data, dict):
        return None
    training_date = model_data.get("training_date")
    if training_date is None:
        return None
    return f"{training_date!s}|{source}"


def get_global_importance(model_data, max_rows: int = 250, n_repeats: int = 8):
    # Importance globale par permutation sur les cinq variables métier.
    pipeline = _pipeline_from_model_data(model_data)
    if pipeline is None:
        return {
            "available": False,
            "reason": "L'importance du modèle nécessite un modèle récent au format pipeline.",
        }

    reference = _artifact_reference(model_data) or _fallback_reference()
    if reference is None:
        return {
            "available": False,
            "reason": "Aucun jeu de référence étiqueté n'est disponible.",
        }

    X, y, source = reference
    if len(X) > max_rows:
        rng = np.random.default_rng(42)
        selected = np.sort(rng.choice(len(X), size=max_rows, replace=False))
        X = X.iloc[selected].reset_index(drop=True)
        y = y.iloc[selected].reset_index(drop=True)

    cache_key = _importance_cache_key(model_data, source)
    if cache_key and cache_key in _GLOBAL_IMPORTANCE_CACHE:
        return _GLOBAL_IMPORTANCE_CACHE[cache_key]

    result = permutation_importance(
        pipeline,
        X,
        y,
        scoring="f1",
        n_repeats=n_repeats,
        random_state=42,
        n_jobs=1,
    )

    means = [float(value) for value in result.importances_mean]
    stds = [float(value) for value in result.importances_std]
    max_positive = max([max(0.0, value) for value in means] + [0.0])

    items = []
    for feature, mean, std in zip(FEATURE_COLUMNS, means, stds):
        width = (max(0.0, mean) / max_positive * 100.0) if max_positive else 0.0
        items.append(
            {
                "feature": feature,
                "label": FEATURE_LABELS[feature],
                "importance": round(mean, 4),
                "importance_points": round(mean * 100.0, 2),
                "std": round(std, 4),
                "std_points": round(std * 100.0, 2),
                "width": round(max(0.0, min(100.0, width)), 1),
            }
        )

    items.sort(key=lambda item: item["importance"], reverse=True)
    payload = {
        "available": True,
        "items": items,
        "reference_source": source,
        "sample_size": int(len(X)),
        "n_repeats": int(n_repeats),
        "metric": "F1-score",
        "method": "Importance par permutation",
    }

    if cache_key:
        if len(_GLOBAL_IMPORTANCE_CACHE) >= 8:
            _GLOBAL_IMPORTANCE_CACHE.pop(next(iter(_GLOBAL_IMPORTANCE_CACHE)))
        _GLOBAL_IMPORTANCE_CACHE[cache_key] = payload

    return payload
