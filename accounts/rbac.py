from __future__ import annotations

from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from predictor.models import ModelTraining, StudentFeedback


ROLE_SUPER_ADMIN = "Super Administrateur"
ROLE_ADMIN = "Administrateur"
ROLE_ML_MANAGER = "Responsable ML"
ROLE_ANALYST = "Analyste"
ROLE_USER = "Utilisateur"

MANAGED_ROLES = (
    ROLE_ADMIN,
    ROLE_ML_MANAGER,
    ROLE_ANALYST,
    ROLE_USER,
)

ROLE_CHOICES = (
    (ROLE_ADMIN, "Administrateur"),
    (ROLE_ML_MANAGER, "Responsable ML"),
    (ROLE_ANALYST, "Analyste"),
    (ROLE_USER, "Utilisateur"),
)

ROLE_PRIORITY = (
    ROLE_ADMIN,
    ROLE_ML_MANAGER,
    ROLE_ANALYST,
    ROLE_USER,
)

CAP_PREDICT = "predict"
CAP_BATCH = "batch_predict"
CAP_STATISTICS = "statistics"
CAP_DATA = "data"
CAP_EXPORT = "export_data"
CAP_TRAIN = "train_model"
CAP_MODELS = "manage_models"
CAP_USERS = "manage_users"
CAP_ROLES = "assign_roles"

CAPABILITY_PERMISSIONS = {
    CAP_PREDICT: "predictor.use_prediction",
    CAP_BATCH: "predictor.use_batch_prediction",
    CAP_STATISTICS: "predictor.view_prediction_statistics",
    CAP_DATA: "predictor.view_feedback_data",
    CAP_EXPORT: "predictor.export_feedback_data",
    CAP_TRAIN: "predictor.train_mlp_model",
    CAP_MODELS: "predictor.manage_mlp_models",
    CAP_USERS: "auth.manage_application_users",
    CAP_ROLES: "auth.assign_application_roles",
}

ROLE_CAPABILITIES = {
    ROLE_USER: {
        CAP_PREDICT,
    },
    ROLE_ANALYST: {
        CAP_PREDICT,
        CAP_BATCH,
        CAP_STATISTICS,
        CAP_DATA,
        CAP_EXPORT,
    },
    ROLE_ML_MANAGER: {
        CAP_PREDICT,
        CAP_BATCH,
        CAP_STATISTICS,
        CAP_DATA,
        CAP_EXPORT,
        CAP_TRAIN,
        CAP_MODELS,
    },
    ROLE_ADMIN: set(CAPABILITY_PERMISSIONS),
}

ROLE_BADGE_CLASSES = {
    ROLE_SUPER_ADMIN: "bg-danger",
    ROLE_ADMIN: "bg-primary",
    ROLE_ML_MANAGER: "bg-info text-dark",
    ROLE_ANALYST: "bg-success",
    ROLE_USER: "bg-secondary",
}


@dataclass(frozen=True)
class PermissionSpec:
    model: type
    codename: str
    name: str


CUSTOM_PERMISSION_SPECS = (
    PermissionSpec(
        StudentFeedback,
        "use_prediction",
        "Peut utiliser la prédiction individuelle",
    ),
    PermissionSpec(
        StudentFeedback,
        "use_batch_prediction",
        "Peut utiliser la prédiction par lot",
    ),
    PermissionSpec(
        StudentFeedback,
        "view_prediction_statistics",
        "Peut consulter les statistiques de prédiction",
    ),
    PermissionSpec(
        StudentFeedback,
        "view_feedback_data",
        "Peut consulter et gérer les données de prédiction",
    ),
    PermissionSpec(
        StudentFeedback,
        "export_feedback_data",
        "Peut exporter les données de prédiction",
    ),
    PermissionSpec(
        ModelTraining,
        "train_mlp_model",
        "Peut entraîner un modèle MLP",
    ),
    PermissionSpec(
        ModelTraining,
        "manage_mlp_models",
        "Peut comparer et activer les modèles MLP",
    ),
    PermissionSpec(
        get_user_model(),
        "manage_application_users",
        "Peut gérer les utilisateurs de l'application",
    ),
    PermissionSpec(
        get_user_model(),
        "assign_application_roles",
        "Peut attribuer les rôles de l'application",
    ),
)


def _permission_key(permission):
    return f"{permission.content_type.app_label}.{permission.codename}"


@transaction.atomic
def ensure_roles_and_permissions():
    permissions = {}

    for spec in CUSTOM_PERMISSION_SPECS:
        content_type = ContentType.objects.get_for_model(spec.model)
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=spec.codename,
            defaults={"name": spec.name},
        )
        if permission.name != spec.name:
            permission.name = spec.name
            permission.save(update_fields=["name"])
        permissions[_permission_key(permission)] = permission

    groups = {}
    for role in MANAGED_ROLES:
        groups[role], _ = Group.objects.get_or_create(name=role)

    for role, capabilities in ROLE_CAPABILITIES.items():
        expected = [
            permissions[CAPABILITY_PERMISSIONS[capability]]
            for capability in capabilities
        ]

        if role == ROLE_ADMIN:
            for model in (StudentFeedback, ModelTraining):
                content_type = ContentType.objects.get_for_model(model)
                expected.extend(
                    Permission.objects.filter(
                        content_type=content_type,
                        codename__in=(
                            f"view_{model._meta.model_name}",
                            f"add_{model._meta.model_name}",
                            f"change_{model._meta.model_name}",
                            f"delete_{model._meta.model_name}",
                        ),
                    )
                )

        groups[role].permissions.set(expected)

    return groups


def managed_role_names():
    return set(MANAGED_ROLES)


def get_user_role(user):
    if not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return ROLE_SUPER_ADMIN

    group_names = set(
        user.groups.filter(name__in=MANAGED_ROLES)
        .values_list("name", flat=True)
    )
    for role in ROLE_PRIORITY:
        if role in group_names:
            return role

    if user.is_staff:
        return ROLE_ADMIN
    return ROLE_USER


def has_explicit_managed_role(user):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=MANAGED_ROLES).exists()


def role_badge_class(role):
    return ROLE_BADGE_CLASSES.get(role, "bg-secondary")


def clear_permission_cache(user):
    for attr in (
        "_perm_cache",
        "_user_perm_cache",
        "_group_perm_cache",
    ):
        if hasattr(user, attr):
            delattr(user, attr)


@transaction.atomic
def assign_role(user, role):
    if user.is_superuser:
        return ROLE_SUPER_ADMIN

    if role not in MANAGED_ROLES:
        raise ValueError("Rôle non reconnu.")

    groups = ensure_roles_and_permissions()

    user.groups.remove(
        *Group.objects.filter(name__in=MANAGED_ROLES)
    )
    user.groups.add(groups[role])

    should_be_staff = role == ROLE_ADMIN
    if user.is_staff != should_be_staff:
        user.is_staff = should_be_staff
        user.save(update_fields=["is_staff"])

    clear_permission_cache(user)
    return role


def user_can(user, capability):
    if not getattr(user, "is_authenticated", False):
        return False
    if user.is_superuser:
        return True

    permission = CAPABILITY_PERMISSIONS.get(capability)
    if permission is None:
        return False

    clear_permission_cache(user)
    return user.has_perm(permission)


def can_manage_target(actor, target):
    if not actor.is_authenticated:
        return False
    if target.is_superuser:
        return False
    if actor.pk == target.pk:
        return False
    return user_can(actor, CAP_USERS)


def bootstrap_existing_users():
    User = get_user_model()
    ensure_roles_and_permissions()

    for user in User.objects.all():
        if user.is_superuser:
            continue

        if user.groups.filter(name__in=MANAGED_ROLES).exists():
            continue

        assign_role(
            user,
            ROLE_ADMIN if user.is_staff else ROLE_USER,
        )
