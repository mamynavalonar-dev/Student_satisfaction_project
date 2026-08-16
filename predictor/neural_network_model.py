# predictor/neural_network_model.py
from __future__ import annotations

import logging
import os
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from .models import ModelTraining

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "model_artifacts"

FEATURE_COLUMNS = [
    "qualite_enseignement",
    "charge_travail",
    "interactivite",
    "type_cours",
    "niveau_etudiant",
]
REQUIRED_COLUMNS = FEATURE_COLUMNS + ["satisfaction"]
NUMERIC_COLUMNS = ["qualite_enseignement", "charge_travail", "interactivite"]
CATEGORICAL_COLUMNS = ["type_cours", "niveau_etudiant"]
ALLOWED_TYPES = {"présentiel", "distanciel", "hybride"}
ALLOWED_LEVELS = {"L1", "L2", "L3", "M1", "M2"}


def _ascii_key(value: object) -> str:
    text = str(value).strip().lower()
    return "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _normalize_type(value: object) -> str:
    key = _ascii_key(value)
    mapping = {
        "presentiel": "présentiel",
        "distanciel": "distanciel",
        "hybride": "hybride",
    }
    return mapping.get(key, str(value).strip().lower())


def _normalize_satisfaction(series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")

    if numeric.notna().all():
        return numeric

    mapping = {
        "1": 1,
        "0": 0,
        "satisfait": 1,
        "satisfaite": 1,
        "oui": 1,
        "true": 1,
        "non satisfait": 0,
        "non satisfaite": 0,
        "insatisfait": 0,
        "insatisfaite": 0,
        "non": 0,
        "false": 0,
    }
    return series.astype(str).str.strip().str.lower().map(mapping)


def validate_training_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Valide et normalise un CSV d'entraînement avant tout apprentissage."""
    if df is None or df.empty:
        raise ValueError("Le fichier CSV est vide.")

    data = df.copy()
    data.columns = [str(column).strip() for column in data.columns]

    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    extra = [column for column in data.columns if column not in REQUIRED_COLUMNS]

    if missing:
        raise ValueError(f"Colonnes manquantes : {', '.join(missing)}")
    if extra:
        raise ValueError(
            "Colonnes supplémentaires non autorisées : " + ", ".join(extra)
        )

    data = data[REQUIRED_COLUMNS].copy()

    for column in NUMERIC_COLUMNS:
        values = pd.to_numeric(data[column], errors="coerce")
        if values.isna().any():
            raise ValueError(f"La colonne '{column}' contient des valeurs non numériques ou vides.")
        if not np.isfinite(values.to_numpy(dtype=float)).all():
            raise ValueError(f"La colonne '{column}' contient une valeur infinie.")
        if not ((values >= 1) & (values <= 7)).all():
            raise ValueError(f"La colonne '{column}' doit contenir uniquement des valeurs de 1 à 7.")
        if not np.equal(values, np.floor(values)).all():
            raise ValueError(f"La colonne '{column}' doit contenir uniquement des entiers.")
        data[column] = values.astype(int)

    data["type_cours"] = data["type_cours"].map(_normalize_type)
    invalid_types = sorted(set(data["type_cours"]) - ALLOWED_TYPES)
    if invalid_types:
        raise ValueError(
            "Valeurs invalides dans 'type_cours' : " + ", ".join(invalid_types)
        )

    data["niveau_etudiant"] = data["niveau_etudiant"].astype(str).str.strip().str.upper()
    invalid_levels = sorted(set(data["niveau_etudiant"]) - ALLOWED_LEVELS)
    if invalid_levels:
        raise ValueError(
            "Valeurs invalides dans 'niveau_etudiant' : " + ", ".join(invalid_levels)
        )

    satisfaction = _normalize_satisfaction(data["satisfaction"])
    if satisfaction.isna().any():
        raise ValueError("La colonne 'satisfaction' doit contenir uniquement 0 ou 1.")
    if not set(satisfaction.astype(int).unique()).issubset({0, 1}):
        raise ValueError("La colonne 'satisfaction' doit contenir uniquement 0 ou 1.")
    data["satisfaction"] = satisfaction.astype(int)

    classes = set(data["satisfaction"].unique())
    if classes != {0, 1}:
        raise ValueError("Le CSV doit contenir les deux classes : 0 (insatisfait) et 1 (satisfait).")

    duplicate_count = int(data.duplicated().sum())
    if duplicate_count:
        data = data.drop_duplicates().reset_index(drop=True)

    if len(data) < 20:
        raise ValueError("Le CSV doit contenir au moins 20 lignes distinctes pour entraîner le modèle.")

    class_counts = data["satisfaction"].value_counts()
    if int(class_counts.min()) < 5:
        raise ValueError("Chaque classe doit contenir au moins 5 observations distinctes.")

    data.attrs["duplicates_removed"] = duplicate_count
    return data


def preprocess_data(df: pd.DataFrame):
    """Compatibilité : retourne les variables brutes validées et la cible."""
    data = validate_training_dataframe(df)
    return data[FEATURE_COLUMNS].copy(), data["satisfaction"].copy()


def _make_one_hot_encoder():
    # Compatibilité scikit-learn avant/après 1.2.
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def _build_pipeline() -> Pipeline:
    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", StandardScaler(), NUMERIC_COLUMNS),
            ("categorical", _make_one_hot_encoder(), CATEGORICAL_COLUMNS),
        ],
        remainder="drop",
    )

    classifier = MLPClassifier(
        hidden_layer_sizes=(128, 64, 32),
        activation="relu",
        solver="adam",
        alpha=0.001,
        max_iter=1000,
        random_state=42,
        early_stopping=True,
        validation_fraction=0.1,
    )

    return Pipeline([
        ("preprocessor", preprocessor),
        ("classifier", classifier),
    ])


def train_model(df: pd.DataFrame):
    """Entraîne le MLP sans fuite train/test et sauvegarde un artefact portable."""
    # Les erreurs de validation du CSV restent des ValueError afin que la vue
    # puisse les présenter comme des données invalides.
    data = validate_training_dataframe(df)
    duplicates_removed = int(data.attrs.get("duplicates_removed", 0))

    try:
        X = data[FEATURE_COLUMNS].copy()
        y = data["satisfaction"].copy()

        X_train, X_test, y_train, y_test = train_test_split(
            X,
            y,
            test_size=0.2,
            random_state=42,
            stratify=y,
        )

        pipeline = _build_pipeline()
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)

        accuracy = float(accuracy_score(y_test, y_pred))
        precision = float(precision_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        matrix = confusion_matrix(y_test, y_pred, labels=[0, 1]).tolist()

        metrics = {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "confusion_matrix": matrix,
            "dataset_size": int(len(data)),
            "train_size": int(len(X_train)),
            "test_size": int(len(X_test)),
            "duplicates_removed": duplicates_removed,
        }

        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        model_filename = f"student_satisfaction_model_{timestamp}_{uuid4().hex[:8]}.joblib"
        model_path = MODEL_DIR / model_filename
        temp_path = model_path.with_suffix(".tmp")

        model_data = {
            "schema_version": 2,
            "pipeline": pipeline,
            "metrics": metrics,
            "accuracy": accuracy,
            "training_date": datetime.now(),
            "feature_names": FEATURE_COLUMNS,
            "target_name": "satisfaction",
            "explanation_background": X_train.sample(
                n=min(40, len(X_train)),
                random_state=42,
            ).to_dict(orient="records"),
            "explanation_reference": {
                "features": X_test.to_dict(orient="records"),
                "target": [int(value) for value in y_test.tolist()],
            },
        }

        joblib.dump(model_data, temp_path, compress=3)
        os.replace(temp_path, model_path)

        relative_model_path = model_path.relative_to(BASE_DIR).as_posix()
        return accuracy, relative_model_path, metrics

    except Exception as exc:
        logger.exception("Échec interne de l'entraînement du modèle")
        raise RuntimeError(
            "Une erreur interne est survenue pendant l'entraînement du modèle."
        ) from exc

def _resolve_model_path(stored_path: str) -> Path | None:
    path = Path(stored_path)
    candidates = []

    if path.is_absolute():
        candidates.append(path)
        # Permet de déplacer le projet tout en conservant les anciens enregistrements DB.
        candidates.extend([
            BASE_DIR / path.name,
            MODEL_DIR / path.name,
        ])
    else:
        candidates.extend([
            BASE_DIR / path,
            MODEL_DIR / path.name,
            BASE_DIR / path.name,
        ])

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_current_model():
    """Charge le modèle actif ; journalise les erreurs au lieu de les masquer."""
    try:
        active_training = ModelTraining.objects.filter(is_active=True).latest("training_date")
    except ModelTraining.DoesNotExist:
        return None

    try:
        model_path = _resolve_model_path(active_training.model_file)
        if model_path is None:
            logger.error("Fichier du modèle actif introuvable : %s", active_training.model_file)
            return None
        return joblib.load(model_path)
    except Exception:
        logger.exception("Impossible de charger le modèle actif")
        return None


def _validate_prediction_input(input_data: dict) -> pd.DataFrame:
    missing = [column for column in FEATURE_COLUMNS if column not in input_data]
    if missing:
        raise ValueError("Données de prédiction incomplètes : " + ", ".join(missing))

    row = dict(input_data)
    for column in NUMERIC_COLUMNS:
        try:
            value = int(row[column])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"'{column}' doit être un entier de 1 à 7.") from exc
        if not 1 <= value <= 7:
            raise ValueError(f"'{column}' doit être compris entre 1 et 7.")
        row[column] = value

    row["type_cours"] = _normalize_type(row["type_cours"])
    if row["type_cours"] not in ALLOWED_TYPES:
        raise ValueError("Type de cours inconnu.")

    row["niveau_etudiant"] = str(row["niveau_etudiant"]).strip().upper()
    if row["niveau_etudiant"] not in ALLOWED_LEVELS:
        raise ValueError("Niveau étudiant inconnu.")

    return pd.DataFrame([row], columns=FEATURE_COLUMNS)


def _format_prediction(prediction: int, probabilities: dict[int, float]):
    probability_satisfied = float(probabilities.get(1, 0.0))
    probability_unsatisfied = float(probabilities.get(0, 0.0))
    prediction_probability = (
        probability_satisfied if prediction == 1 else probability_unsatisfied
    )

    return {
        "prediction": int(prediction),
        "probability_satisfied": probability_satisfied * 100,
        "probability_unsatisfied": probability_unsatisfied * 100,
        "satisfaction_text": "Satisfait" if prediction == 1 else "Non satisfait",
        "prediction_probability": prediction_probability * 100,
    }


def predict_satisfaction(model_data, input_data):
    """Prédit la satisfaction, avec compatibilité des anciens artefacts joblib."""
    try:
        input_df = _validate_prediction_input(input_data)

        if "pipeline" in model_data:
            pipeline = model_data["pipeline"]
            prediction = int(pipeline.predict(input_df)[0])
            probability_values = pipeline.predict_proba(input_df)[0]
            classes = pipeline.named_steps["classifier"].classes_
            probabilities = {
                int(class_value): float(probability)
                for class_value, probability in zip(classes, probability_values)
            }
            return _format_prediction(prediction, probabilities)

        # Compatibilité avec les modèles historiques déjà enregistrés.
        model = model_data["model"]
        scaler = model_data["scaler"]
        label_encoders = model_data["label_encoders"]
        legacy_df = input_df.copy()

        for column, encoder in label_encoders.items():
            value = legacy_df[column].iloc[0]
            if value not in set(encoder.classes_):
                raise ValueError(
                    f"La valeur '{value}' n'existait pas dans les données utilisées par cet ancien modèle. "
                    "Réentraînez le modèle avec un CSV à jour."
                )
            legacy_df[column] = encoder.transform([value])

        if "feature_names" in model_data:
            legacy_df = legacy_df[model_data["feature_names"]]

        scaled = scaler.transform(legacy_df)
        prediction = int(model.predict(scaled)[0])
        probability_values = model.predict_proba(scaled)[0]
        probabilities = {
            int(class_value): float(probability)
            for class_value, probability in zip(model.classes_, probability_values)
        }
        return _format_prediction(prediction, probabilities)

    except Exception as exc:
        logger.exception("Échec de la prédiction")
        raise ValueError(f"Erreur lors de la prédiction : {exc}") from exc
