from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.rbac import (
    ROLE_SUPER_ADMIN,
    bootstrap_existing_users,
    ensure_roles_and_permissions,
)


class Command(BaseCommand):
    help = "Initialise les rôles RBAC et attribue un rôle aux comptes existants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--promote-superuser",
            dest="promote_superuser",
            help=(
                "Nom d'utilisateur à promouvoir explicitement en Super "
                "Administrateur. Aucun mot de passe n'est modifié."
            ),
        )

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_roles_and_permissions()

        username = (options.get("promote_superuser") or "").strip()
        if username:
            User = get_user_model()
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"Compte {username!r} introuvable : aucune promotion effectuée."
                    )
                )
            else:
                changed = []
                if not user.is_staff:
                    user.is_staff = True
                    changed.append("is_staff")
                if not user.is_superuser:
                    user.is_superuser = True
                    changed.append("is_superuser")
                if changed:
                    user.save(update_fields=changed)
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{username} : rôle {ROLE_SUPER_ADMIN} confirmé."
                    )
                )

        bootstrap_existing_users()

        self.stdout.write(
            self.style.SUCCESS(
                "Rôles RBAC initialisés : Administrateur, Responsable ML, "
                "Analyste, Utilisateur."
            )
        )
