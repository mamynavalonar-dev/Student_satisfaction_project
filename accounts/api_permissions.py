from rest_framework.permissions import BasePermission

from .rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_MODELS,
    user_can,
)


class CanUseBatchPrediction(BasePermission):
    message = "Votre rôle ne permet pas la prédiction par lot."

    def has_permission(self, request, view):
        return user_can(request.user, CAP_BATCH)


class CanViewModelManagement(BasePermission):
    message = "Votre rôle ne permet pas de consulter la gestion des modèles."

    def has_permission(self, request, view):
        return user_can(request.user, CAP_MODELS)


class CanViewFeedbackData(BasePermission):
    message = "Votre rôle ne permet pas de consulter les données de prédiction."

    def has_permission(self, request, view):
        return user_can(request.user, CAP_DATA)
