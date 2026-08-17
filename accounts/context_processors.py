from .rbac import (
    CAP_BATCH,
    CAP_DATA,
    CAP_EXPORT,
    CAP_MODELS,
    CAP_ROLES,
    CAP_STATISTICS,
    CAP_TRAIN,
    CAP_USERS,
    get_user_role,
    role_badge_class,
    user_can,
)


def rbac_context(request):
    user = request.user
    if not getattr(user, "is_authenticated", False):
        return {
            "current_role_label": None,
            "current_role_badge_class": "bg-secondary",
            "can_batch_predict": False,
            "can_view_statistics": False,
            "can_view_data": False,
            "can_export_data": False,
            "can_train_models": False,
            "can_manage_models": False,
            "can_manage_users": False,
            "can_assign_roles": False,
            "rbac_nav_count": 0,
        }

    role = get_user_role(user)
    can_data = user_can(user, CAP_DATA)
    can_stats = user_can(user, CAP_STATISTICS)
    can_train = user_can(user, CAP_TRAIN)

    nav_count = 2
    if can_data:
        nav_count += 1
    if can_stats:
        nav_count += 1
    if can_train:
        nav_count += 1

    return {
        "current_role_label": role,
        "current_role_badge_class": role_badge_class(role),
        "can_batch_predict": user_can(user, CAP_BATCH),
        "can_view_statistics": can_stats,
        "can_view_data": can_data,
        "can_export_data": user_can(user, CAP_EXPORT),
        "can_train_models": can_train,
        "can_manage_models": user_can(user, CAP_MODELS),
        "can_manage_users": user_can(user, CAP_USERS),
        "can_assign_roles": user_can(user, CAP_ROLES),
        "rbac_nav_count": nav_count,
    }
