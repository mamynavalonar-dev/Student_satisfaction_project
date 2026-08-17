from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .rbac import ensure_roles_and_permissions


@receiver(post_migrate)
def create_rbac_roles_after_migrate(sender, **kwargs):
    if sender.label == "accounts":
        ensure_roles_and_permissions()
