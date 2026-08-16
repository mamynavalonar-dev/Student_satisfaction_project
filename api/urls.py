from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import (
    BatchPredictAPIView,
    FeedbackListAPIView,
    ModelListAPIView,
    PredictAPIView,
)

app_name = "api"

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("predict/", PredictAPIView.as_view(), name="predict"),
    path("predict/batch/", BatchPredictAPIView.as_view(), name="predict_batch"),
    path("models/", ModelListAPIView.as_view(), name="models"),
    path("feedbacks/", FeedbackListAPIView.as_view(), name="feedbacks"),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        SpectacularSwaggerView.as_view(url_name="api:schema"),
        name="swagger-ui",
    ),
]
