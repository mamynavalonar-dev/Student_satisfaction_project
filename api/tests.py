from __future__ import annotations

from unittest.mock import patch

import pandas as pd
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from predictor.models import ModelTraining, StudentFeedback


class RestApiTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.password = "ApiProjet2026!Solide"
        self.user = User.objects.create_user(
            username="api-user",
            email="api-user@example.com",
            password=self.password,
        )
        self.staff = User.objects.create_user(
            username="api-staff",
            email="api-staff@example.com",
            password=self.password,
            is_staff=True,
        )
        self.training = ModelTraining.objects.create(
            accuracy=0.7075,
            dataset_size=2000,
            model_file="model_artifacts/api-test.joblib",
            notes="API test",
            is_active=True,
        )

    @staticmethod
    def _valid_input():
        return {
            "qualite_enseignement": 7,
            "charge_travail": 4,
            "interactivite": 7,
            "type_cours": "présentiel",
            "niveau_etudiant": "M1",
        }

    def test_prediction_requires_authentication(self):
        response = self.client.post(
            reverse("api:predict"),
            self._valid_input(),
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_jwt_token_and_refresh_endpoints_work(self):
        token_response = self.client.post(
            reverse("api:token_obtain_pair"),
            {"username": self.user.username, "password": self.password},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)
        self.assertIn("refresh", token_response.data)

        refresh_response = self.client.post(
            reverse("api:token_refresh"),
            {"refresh": token_response.data["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)

    def test_authenticated_prediction_reuses_ml_engine(self):
        self.client.force_authenticate(user=self.user)
        result = {
            "prediction": 1,
            "probability_satisfied": 87.2,
            "probability_unsatisfied": 12.8,
            "satisfaction_text": "Satisfait",
            "prediction_probability": 87.2,
        }

        with (
            patch("api.views.load_current_model", return_value={"schema_version": 3}),
            patch("api.views.predict_satisfaction", return_value=result) as predict_mock,
        ):
            response = self.client.post(
                reverse("api:predict"),
                self._valid_input(),
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["result"]["prediction"], 1)
        self.assertEqual(response.data["result"]["probability_satisfied"], 87.2)
        self.assertEqual(response.data["model"]["id"], self.training.id)
        predict_mock.assert_called_once()

    def test_prediction_validation_rejects_out_of_range_score(self):
        self.client.force_authenticate(user=self.user)
        payload = self._valid_input()
        payload["qualite_enseignement"] = 8

        response = self.client.post(
            reverse("api:predict"),
            payload,
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_prediction_returns_503_without_active_model(self):
        self.client.force_authenticate(user=self.user)
        with patch("api.views.load_current_model", return_value=None):
            response = self.client.post(
                reverse("api:predict"),
                self._valid_input(),
                format="json",
            )
        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_batch_prediction_returns_summary_and_results(self):
        self.client.force_authenticate(user=self.user)
        predicted = pd.DataFrame(
            [
                {
                    "qualite_enseignement": 7,
                    "charge_travail": 4,
                    "interactivite": 7,
                    "type_cours": "présentiel",
                    "niveau_etudiant": "M1",
                    "predicted_satisfaction": 1,
                    "prediction_label": "Satisfait",
                    "probability_satisfied": 87.2,
                    "probability_unsatisfied": 12.8,
                    "confidence": 87.2,
                },
                {
                    "qualite_enseignement": 1,
                    "charge_travail": 7,
                    "interactivite": 1,
                    "type_cours": "distanciel",
                    "niveau_etudiant": "M2",
                    "predicted_satisfaction": 0,
                    "prediction_label": "Non satisfait",
                    "probability_satisfied": 1.7,
                    "probability_unsatisfied": 98.3,
                    "confidence": 98.3,
                },
            ]
        )

        with (
            patch("api.views.load_current_model", return_value={"schema_version": 3}),
            patch("api.views.predict_satisfaction_batch", return_value=predicted),
        ):
            response = self.client.post(
                reverse("api:predict_batch"),
                {
                    "rows": [
                        self._valid_input(),
                        {
                            "qualite_enseignement": 1,
                            "charge_travail": 7,
                            "interactivite": 1,
                            "type_cours": "distanciel",
                            "niveau_etudiant": "M2",
                        },
                    ]
                },
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["summary"]["total"], 2)
        self.assertEqual(response.data["summary"]["satisfied"], 1)
        self.assertEqual(response.data["summary"]["unsatisfied"], 1)
        self.assertEqual(len(response.data["results"]), 2)

    def test_models_endpoint_is_staff_only(self):
        self.client.force_authenticate(user=self.user)
        forbidden = self.client.get(reverse("api:models"))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        artifact_info = {
            "available": True,
            "compatible": True,
            "format_label": "Pipeline v3",
            "reason": "",
            "metrics": {"f1": 0.6628},
        }
        with patch("api.views.inspect_model_artifact", return_value=artifact_info):
            allowed = self.client.get(reverse("api:models"))

        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed.data[0]["id"], self.training.id)
        self.assertEqual(allowed.data[0]["artifact_status"], "available")

    def test_feedbacks_endpoint_is_staff_only_and_paginated(self):
        StudentFeedback.objects.create(
            qualite_enseignement=7,
            charge_travail=4,
            interactivite=7,
            type_cours="présentiel",
            niveau_etudiant="M1",
            predicted_satisfaction=True,
            probability_satisfied=87.2,
        )

        self.client.force_authenticate(user=self.user)
        forbidden = self.client.get(reverse("api:feedbacks"))
        self.assertEqual(forbidden.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.staff)
        allowed = self.client.get(reverse("api:feedbacks"))
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.assertEqual(allowed.data["count"], 1)
        self.assertEqual(allowed.data["results"][0]["prediction_label"], "Satisfait")

    def test_openapi_schema_and_swagger_are_public(self):
        self.client.force_authenticate(user=None)
        schema = self.client.get(reverse("api:schema"))
        docs = self.client.get(reverse("api:swagger-ui"))

        self.assertEqual(schema.status_code, status.HTTP_200_OK)
        self.assertEqual(docs.status_code, status.HTTP_200_OK)
