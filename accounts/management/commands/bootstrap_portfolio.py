from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.rbac import ROLE_USER, assign_role, ensure_roles_and_permissions
from predictor.models import ModelTraining
from predictor.neural_network_model import load_model_artifact


class Command(BaseCommand):
    help = (
        "Prépare le modèle ML packagé et le compte public de démonstration "
        "pour un déploiement portfolio."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        if not getattr(settings, "PORTFOLIO_DEMO_ENABLED", False):
            raise CommandError(
                "PORTFOLIO_DEMO_ENABLED doit être activé pour créer le compte public."
            )

        username = str(settings.PORTFOLIO_DEMO_USERNAME or "").strip()
        email = str(settings.PORTFOLIO_DEMO_EMAIL or "").strip()
        password = str(settings.PORTFOLIO_DEMO_PASSWORD or "")
        model_path = str(settings.PORTFOLIO_MODEL_PATH or "").strip()

        if not username:
            raise CommandError("PORTFOLIO_DEMO_USERNAME est obligatoire.")
        if not password:
            raise CommandError("PORTFOLIO_DEMO_PASSWORD est obligatoire.")
        if len(password) < 12:
            raise CommandError(
                "PORTFOLIO_DEMO_PASSWORD doit contenir au moins 12 caractères."
            )
        if not model_path:
            raise CommandError("PORTFOLIO_MODEL_PATH est obligatoire.")

        try:
            model_data, resolved_path = load_model_artifact(model_path)
        except (FileNotFoundError, ValueError) as exc:
            raise CommandError(
                f"Le modèle portfolio n'est pas exploitable : {exc}"
            ) from exc

        schema_version = (
            model_data.get("schema_version")
            if isinstance(model_data, dict)
            else None
        )
        if schema_version != 3:
            raise CommandError(
                "Le modèle portfolio doit être un artefact Pipeline v3 compatible."
            )

        metrics = model_data.get("metrics") or {}
        try:
            accuracy = float(
                metrics.get("accuracy", model_data.get("accuracy"))
            )
            dataset_size = int(metrics.get("dataset_size"))
        except (TypeError, ValueError) as exc:
            raise CommandError(
                "Le modèle packagé ne contient pas les métriques de production attendues."
            ) from exc

        if not 0.0 <= accuracy <= 1.0 or dataset_size <= 0:
            raise CommandError(
                "Les métriques du modèle packagé sont incohérentes."
            )

        ensure_roles_and_permissions()

        User = get_user_model()
        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            user = User(username=username)

        user.username = username
        user.email = email
        user.first_name = "Portfolio"
        user.last_name = "Demo"
        user.is_active = True
        user.is_staff = False
        user.is_superuser = False

        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise CommandError(
                "PORTFOLIO_DEMO_PASSWORD ne respecte pas les validateurs Django : "
                + "; ".join(exc.messages)
            ) from exc

        user.set_password(password)
        user.save()
        user.user_permissions.clear()
        assign_role(user, ROLE_USER)

        training = (
            ModelTraining.objects
            .filter(model_file=model_path)
            .order_by("-training_date")
            .first()
        )

        if training is None:
            training = ModelTraining.objects.create(
                accuracy=accuracy,
                dataset_size=dataset_size,
                model_file=model_path,
                notes="Production portfolio bootstrap",
                is_active=False,
            )
        else:
            training.accuracy = accuracy
            training.dataset_size = dataset_size
            training.notes = "Production portfolio bootstrap"
            training.save(
                update_fields=[
                    "accuracy",
                    "dataset_size",
                    "notes",
                ]
            )

        ModelTraining.objects.exclude(pk=training.pk).filter(
            is_active=True
        ).update(is_active=False)

        if not training.is_active:
            training.is_active = True
            training.save(update_fields=["is_active"])

        self.stdout.write(
            self.style.SUCCESS(
                "Portfolio prêt : "
                f"compte {username!r} (rôle Utilisateur) + "
                f"modèle actif #{training.pk} ({resolved_path.name})."
            )
        )
