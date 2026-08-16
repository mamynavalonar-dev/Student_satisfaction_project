from __future__ import annotations

import pandas as pd
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from predictor.models import StudentFeedback
from predictor.neural_network_model import (
    FEATURE_COLUMNS,
    MAX_BATCH_ROWS,
    validate_prediction_dataframe,
)


class PredictionInputSerializer(serializers.Serializer):
    qualite_enseignement = serializers.IntegerField(min_value=1, max_value=7)
    charge_travail = serializers.IntegerField(min_value=1, max_value=7)
    interactivite = serializers.IntegerField(min_value=1, max_value=7)
    type_cours = serializers.CharField(max_length=20)
    niveau_etudiant = serializers.CharField(max_length=10)

    def validate(self, attrs):
        try:
            validated = validate_prediction_dataframe(
                pd.DataFrame([attrs]),
                max_rows=1,
            )
        except ValueError as exc:
            raise serializers.ValidationError({"input": str(exc)}) from exc
        return validated.iloc[0].to_dict()


class BatchPredictionInputSerializer(serializers.Serializer):
    rows = PredictionInputSerializer(many=True)

    def validate_rows(self, value):
        if not value:
            raise serializers.ValidationError("Ajoutez au moins une ligne à prédire.")
        if len(value) > MAX_BATCH_ROWS:
            raise serializers.ValidationError(
                f"La limite est de {MAX_BATCH_ROWS} lignes par requête."
            )
        return value


class ModelReferenceSerializer(serializers.Serializer):
    id = serializers.IntegerField(allow_null=True)
    training_date = serializers.DateTimeField(allow_null=True)
    accuracy = serializers.FloatField(allow_null=True)
    schema_version = serializers.IntegerField(allow_null=True)


class PredictionResultSerializer(serializers.Serializer):
    prediction = serializers.IntegerField()
    prediction_label = serializers.CharField()
    probability_satisfied = serializers.FloatField()
    probability_unsatisfied = serializers.FloatField()
    confidence = serializers.FloatField()


class PredictionResponseSerializer(serializers.Serializer):
    result = PredictionResultSerializer()
    model = ModelReferenceSerializer()


class BatchSummarySerializer(serializers.Serializer):
    total = serializers.IntegerField()
    satisfied = serializers.IntegerField()
    unsatisfied = serializers.IntegerField()
    satisfaction_rate = serializers.FloatField()
    average_confidence = serializers.FloatField()
    average_probability_satisfied = serializers.FloatField()


class BatchPredictionResponseSerializer(serializers.Serializer):
    summary = BatchSummarySerializer()
    results = PredictionResultSerializer(many=True)
    model = ModelReferenceSerializer()


class ModelInfoSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    training_date = serializers.DateTimeField()
    accuracy = serializers.FloatField()
    dataset_size = serializers.IntegerField()
    notes = serializers.CharField()
    is_active = serializers.BooleanField()
    artifact_status = serializers.CharField()
    artifact_format = serializers.CharField()
    artifact_reason = serializers.CharField(allow_blank=True)
    can_activate = serializers.BooleanField()
    metrics = serializers.DictField()


class StudentFeedbackSerializer(serializers.ModelSerializer):
    prediction_label = serializers.SerializerMethodField()

    class Meta:
        model = StudentFeedback
        fields = [
            "id",
            "qualite_enseignement",
            "charge_travail",
            "interactivite",
            "type_cours",
            "niveau_etudiant",
            "predicted_satisfaction",
            "prediction_label",
            "probability_satisfied",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    @extend_schema_field(serializers.CharField(allow_null=True))
    def get_prediction_label(self, obj) -> str | None:
        if obj.predicted_satisfaction is None:
            return None
        return "Satisfait" if obj.predicted_satisfaction else "Non satisfait"
