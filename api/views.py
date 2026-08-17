from __future__ import annotations

import json
import logging

import pandas as pd
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from accounts.api_permissions import (
    CanUseBatchPrediction,
    CanViewFeedbackData,
    CanViewModelManagement,
)

from predictor.models import ModelTraining, StudentFeedback
from predictor.neural_network_model import (
    FEATURE_COLUMNS,
    inspect_model_artifact,
    load_current_model,
    predict_satisfaction,
    predict_satisfaction_batch,
)

from .serializers import (
    BatchPredictionInputSerializer,
    BatchPredictionResponseSerializer,
    ModelInfoSerializer,
    PredictionInputSerializer,
    PredictionResponseSerializer,
    StudentFeedbackSerializer,
)

logger = logging.getLogger(__name__)


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Le modèle de prédiction n'est pas disponible."
    default_code = "model_unavailable"


def _active_training():
    return (
        ModelTraining.objects
        .filter(is_active=True)
        .order_by("-training_date")
        .first()
    )


def _model_reference(training, model_data):
    metrics = model_data.get("metrics") if isinstance(model_data, dict) else {}
    accuracy = None
    if training is not None:
        accuracy = round(float(training.accuracy) * 100.0, 2)
    elif isinstance(metrics, dict) and metrics.get("accuracy") is not None:
        accuracy = round(float(metrics["accuracy"]) * 100.0, 2)

    schema_version = None
    if isinstance(model_data, dict):
        schema_version = model_data.get("schema_version")

    return {
        "id": training.pk if training else None,
        "training_date": training.training_date if training else None,
        "accuracy": accuracy,
        "schema_version": schema_version,
    }


def _single_result_payload(result):
    prediction = int(result["prediction"])
    return {
        "prediction": prediction,
        "prediction_label": result.get(
            "satisfaction_text",
            "Satisfait" if prediction == 1 else "Non satisfait",
        ),
        "probability_satisfied": round(float(result["probability_satisfied"]), 2),
        "probability_unsatisfied": round(float(result["probability_unsatisfied"]), 2),
        "confidence": round(float(result.get("prediction_probability", 0.0)), 2),
    }


class PredictAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "prediction"

    @extend_schema(
        request=PredictionInputSerializer,
        responses={200: PredictionResponseSerializer},
        description=(
            "Prédit la satisfaction pour un cours avec le modèle MLP actif. "
            "La requête n'est pas enregistrée dans StudentFeedback."
        ),
    )
    def post(self, request):
        serializer = PredictionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        model_data = load_current_model()
        if model_data is None:
            raise ServiceUnavailable("Aucun modèle actif compatible n'est disponible.")

        try:
            prediction = predict_satisfaction(
                model_data,
                serializer.validated_data,
            )
        except ValueError as exc:
            raise ValidationError({"input": str(exc)}) from exc
        except Exception as exc:
            logger.exception("Erreur API de prédiction individuelle")
            raise APIException(
                "Une erreur interne est survenue pendant la prédiction."
            ) from exc

        return Response(
            {
                "result": _single_result_payload(prediction),
                "model": _model_reference(_active_training(), model_data),
            },
            status=status.HTTP_200_OK,
        )


class BatchPredictAPIView(APIView):
    permission_classes = [IsAuthenticated, CanUseBatchPrediction]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "batch_prediction"

    @extend_schema(
        request=BatchPredictionInputSerializer,
        responses={200: BatchPredictionResponseSerializer},
        description=(
            "Prédit plusieurs lignes en une seule opération vectorisée. "
            "Les lignes ne sont pas enregistrées dans StudentFeedback."
        ),
    )
    def post(self, request):
        serializer = BatchPredictionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        model_data = load_current_model()
        if model_data is None:
            raise ServiceUnavailable("Aucun modèle actif compatible n'est disponible.")

        frame = pd.DataFrame(
            serializer.validated_data["rows"],
            columns=FEATURE_COLUMNS,
        )

        try:
            result_df = predict_satisfaction_batch(model_data, frame)
        except ValueError as exc:
            raise ValidationError({"rows": str(exc)}) from exc
        except Exception as exc:
            logger.exception("Erreur API de prédiction par lot")
            raise APIException(
                "Une erreur interne est survenue pendant la prédiction par lot."
            ) from exc

        total = int(len(result_df))
        satisfied = int((result_df["predicted_satisfaction"] == 1).sum())
        unsatisfied = total - satisfied

        raw_rows = json.loads(
            result_df.to_json(orient="records", force_ascii=False)
        )
        results = [
            {
                "prediction": int(row["predicted_satisfaction"]),
                "prediction_label": row["prediction_label"],
                "probability_satisfied": float(row["probability_satisfied"]),
                "probability_unsatisfied": float(row["probability_unsatisfied"]),
                "confidence": float(row["confidence"]),
            }
            for row in raw_rows
        ]

        return Response(
            {
                "summary": {
                    "total": total,
                    "satisfied": satisfied,
                    "unsatisfied": unsatisfied,
                    "satisfaction_rate": (
                        round(satisfied / total * 100.0, 2) if total else 0.0
                    ),
                    "average_confidence": (
                        round(float(result_df["confidence"].mean()), 2)
                        if total else 0.0
                    ),
                    "average_probability_satisfied": (
                        round(float(result_df["probability_satisfied"].mean()), 2)
                        if total else 0.0
                    ),
                },
                "results": results,
                "model": _model_reference(_active_training(), model_data),
            },
            status=status.HTTP_200_OK,
        )


class ModelListAPIView(APIView):
    permission_classes = [IsAuthenticated, CanViewModelManagement]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "api_readonly"

    @extend_schema(
        responses={200: ModelInfoSerializer(many=True)},
        description="Liste les modèles enregistrés. Réservé aux utilisateurs staff.",
    )
    def get(self, request):
        rows = []
        trainings = ModelTraining.objects.all().order_by("-training_date")[:50]

        for training in trainings:
            info = inspect_model_artifact(training.model_file)
            if not info.get("available"):
                artifact_status = "missing"
            elif not info.get("compatible"):
                artifact_status = "incompatible"
            else:
                artifact_status = "available"

            rows.append(
                {
                    "id": training.pk,
                    "training_date": training.training_date,
                    "accuracy": round(float(training.accuracy) * 100.0, 2),
                    "dataset_size": training.dataset_size,
                    "notes": training.notes,
                    "is_active": training.is_active,
                    "artifact_status": artifact_status,
                    "artifact_format": info.get("format_label") or "—",
                    "artifact_reason": info.get("reason") or "",
                    "can_activate": (
                        artifact_status == "available"
                        and not training.is_active
                    ),
                    "metrics": info.get("metrics") or {},
                }
            )

        return Response(
            ModelInfoSerializer(rows, many=True).data,
            status=status.HTTP_200_OK,
        )


class FeedbackListAPIView(generics.ListAPIView):
    serializer_class = StudentFeedbackSerializer
    permission_classes = [IsAuthenticated, CanViewFeedbackData]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "api_readonly"

    def get_queryset(self):
        return StudentFeedback.objects.all().order_by("-created_at")
