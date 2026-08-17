from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin

from .rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_EXPORT,
    CAP_MODELS,
    CAP_STATISTICS,
    CAP_TRAIN,
    has_explicit_managed_role,
    user_can,
)


URL_CAPABILITIES = {
    "batch_predict": CAP_BATCH,
    "batch_predict_download": CAP_BATCH,
    "statistics": CAP_STATISTICS,
    "data_management": CAP_DATA,
    "feedback_detail": CAP_DATA,
    "feedback_update": CAP_DATA,
    "feedback_delete": CAP_DATA,
    "export_data": CAP_EXPORT,
    "train_model": CAP_TRAIN,
    "activate_model": CAP_MODELS,
    "deactivate_model": CAP_MODELS,
}


class RbacAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        match = request.resolver_match
        if match is None:
            return None

        if match.namespace in {"api", "accounts", "admin"}:
            return None

        capability = URL_CAPABILITIES.get(match.url_name)
        if capability is None:
            return None

        # Compatibilité avec les anciens tests et éventuels comptes techniques
        # créés directement par du code historique : seuls les comptes auxquels
        # le RBAC a été explicitement appliqué sont filtrés par ce middleware.
        # V15A1_FAIL_CLOSED: no implicit access for an
        # authenticated account without a managed application role.

        if user_can(request.user, capability):
            return None

        return render(
            request,
            "accounts/forbidden.html",
            {
                "required_capability": capability,
            },
            status=403,
        )
