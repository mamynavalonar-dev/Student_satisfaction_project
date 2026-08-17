# predictor/views.py
from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pandas as pd
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Avg, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from accounts.rbac import ROLE_USER, assign_role
from .forms import (
    LoginForm,
    PredictionForm,
    RegistrationForm,
    StudentFeedbackEditForm,
    TrainingForm,
)
from .models import ModelTraining, Notification, StudentFeedback
from .notifications import notify_user
from .utils_explain import get_global_importance, get_local_explanation
from .neural_network_model import (
    inspect_model_artifact,
    load_current_model,
    load_model_artifact,
    predict_satisfaction,
    predict_satisfaction_batch,
    train_model,
    validate_prediction_dataframe,
    validate_training_dataframe,
)
from django.utils.translation import gettext as _

# V14C225_TRAINING_CHART_DATETIME
def _format_training_chart_datetime(value, language_code):
    """Display-only date formatting for the Training history chart."""
    from django.utils import timezone

    current = value

    try:
        if timezone.is_aware(current):
            current = timezone.localtime(current)
    except (TypeError, ValueError):
        pass

    language = str(language_code or "").lower()

    if language.startswith("en"):
        hour = current.hour
        suffix = "AM" if hour < 12 else "PM"
        display_hour = hour % 12 or 12

        return (
            f"{current.strftime('%b')} "
            f"{current.day}, {current.year}, "
            f"{display_hour}:{current.minute:02d} {suffix}"
        )

    return current.strftime("%Y-%m-%d %H:%M")


logger = logging.getLogger(__name__)

BATCH_MAX_FILE_SIZE = 5 * 1024 * 1024
BATCH_EXPORT_MAX_AGE_SECONDS = 24 * 60 * 60
BATCH_SESSION_KEY = "batch_prediction_result"


def login_register_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    next_url = request.POST.get("next") or request.GET.get("next") or ""
    active_panel = "register" if request.GET.get("mode") == "register" else "login"

    login_form = LoginForm(request=request, prefix="login")
    register_form = RegistrationForm(prefix="register")

    if request.method == "POST":
        form_type = request.POST.get("form_type")

        if form_type == "login":
            active_panel = "login"
            login_form = LoginForm(request=request, data=request.POST, prefix="login")
            if login_form.is_valid():
                user = login_form.get_user()
                login(request, user)
                notify_user(
                    user,
                    "Connexion réussie",
                    f"Bienvenue {user.username}. Votre session est active.",
                    level="success",
                    event_type="auth",
                    target_url=reverse("home"),
                )
                messages.success(request, f"Connexion réussie. Bon retour, {user.username}.")
                if next_url and url_has_allowed_host_and_scheme(
                    url=next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect("home")

        elif form_type == "register":
            active_panel = "register"
            register_form = RegistrationForm(request.POST, prefix="register")
            if register_form.is_valid():
                user = register_form.save()
                assign_role(user, ROLE_USER)
                login(request, user)

                notify_user(
                    user,
                    "Compte créé",
                    f"Bienvenue {user.username}. Votre compte a été créé avec succès.",
                    level="success",
                    event_type="auth",
                    target_url=reverse("home"),
                )
                messages.success(request, f"Inscription réussie ! Bienvenue, {user.username}.")
                return redirect("home")

        else:
            messages.error(request, "Formulaire d'authentification invalide.")

    return render(
        request,
        "predictor/login_register.html",
        {
            "login_form": login_form,
            "register_form": register_form,
            "active_panel": active_panel,
            "next_url": next_url,
        },
    )


@login_required(login_url="login_register")
@require_POST
def logout_view(request):
    logout(request)
    messages.info(request, "Vous avez été déconnecté avec succès.")
    return redirect("login_register")


@login_required(login_url="login_register")
def notifications_feed(request):
    queryset = Notification.objects.filter(user=request.user)
    notifications = list(queryset.order_by("-created_at")[:25])

    payload = [
        {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "level": notification.level,
            "event_type": notification.event_type,
            "target_url": notification.target_url,
            "is_read": notification.is_read,
            "created_at": timezone.localtime(notification.created_at).isoformat(),
            "mark_read_url": reverse("notification_mark_read", args=[notification.id]),
        }
        for notification in notifications
    ]

    response = JsonResponse(
        {
            "notifications": payload,
            "unread_count": queryset.filter(is_read=False).count(),
        }
    )
    response["Cache-Control"] = "no-store, max-age=0"
    return response


@login_required(login_url="login_register")
@require_POST
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
    return JsonResponse({"ok": True, "id": notification.id})


@login_required(login_url="login_register")
@require_POST
def notifications_mark_all_read(request):
    updated = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return JsonResponse({"ok": True, "updated": updated})

def _metric_percent(value):
    """Normalise une métrique stockée en ratio (0..1) ou déjà en pourcentage."""
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if 0 <= numeric <= 1.000001:
        numeric *= 100
    return round(numeric, 2)


def _active_model_summary(model_data=None):
    """Construit un résumé sûr du modèle actif, compatible avec les anciens joblib."""
    if model_data is None:
        model_data = load_current_model()

    training = ModelTraining.objects.filter(is_active=True).order_by("-training_date").first()
    if model_data is None and training is None:
        return None

    metrics = {}
    if isinstance(model_data, dict):
        raw_metrics = model_data.get("metrics")
        if isinstance(raw_metrics, dict):
            metrics = raw_metrics

    accuracy_source = metrics.get("accuracy")
    if accuracy_source is None and isinstance(model_data, dict):
        accuracy_source = model_data.get("accuracy")
    if accuracy_source is None and training is not None:
        accuracy_source = training.accuracy

    return {
        "accuracy": _metric_percent(accuracy_source),
        "precision": _metric_percent(metrics.get("precision")),
        "recall": _metric_percent(metrics.get("recall")),
        "f1": _metric_percent(metrics.get("f1")),
        "dataset_size": metrics.get("dataset_size") or (training.dataset_size if training else None),
        "train_size": metrics.get("train_size"),
        "test_size": metrics.get("test_size"),
        "duplicates_removed": metrics.get("duplicates_removed"),
        "training_date": training.training_date if training else None,
        "has_detailed_metrics": any(
            metrics.get(key) is not None for key in ("precision", "recall", "f1")
        ),
    }


def _average_prediction_confidence(feedbacks):
    # probability_satisfied = P(satisfait).
    # Pour une prédiction négative, la confiance de la classe prédite
    # vaut donc 100 - probability_satisfied.
    values = []

    for feedback in feedbacks.only(
        "predicted_satisfaction",
        "probability_satisfied",
    ):
        probability_satisfied = feedback.probability_satisfied

        if probability_satisfied is None:
            continue

        probability_satisfied = float(probability_satisfied)

        confidence = (
            probability_satisfied
            if feedback.predicted_satisfaction
            else 100.0 - probability_satisfied
        )

        confidence = max(0.0, min(100.0, confidence))
        values.append(confidence)

    if not values:
        return None

    return sum(values) / len(values)


@login_required(login_url="login_register")
def home(request):
    feedbacks = StudentFeedback.objects.all()
    total_feedbacks = feedbacks.count()
    satisfied_count = feedbacks.filter(predicted_satisfaction=True).count()
    unsatisfied_count = total_feedbacks - satisfied_count
    satisfaction_rate = (satisfied_count / total_feedbacks * 100) if total_feedbacks else 0
    average_confidence = _average_prediction_confidence(feedbacks)

    model_data = load_current_model()
    active_model = _active_model_summary(model_data)

    context = {
        "total_feedbacks": total_feedbacks,
        "satisfied_count": satisfied_count,
        "unsatisfied_count": unsatisfied_count,
        "satisfaction_rate": satisfaction_rate,
        "average_confidence": average_confidence,
        "model_loaded": model_data is not None,
        "active_model": active_model,
    }
    return render(request, "predictor/home.html", context)


@login_required(login_url="login_register")
def predict(request):
    if request.method == "POST":
        form = PredictionForm(request.POST)
        if form.is_valid():
            try:
                input_data = {
                    "qualite_enseignement": int(form.cleaned_data["qualite_enseignement"]),
                    "charge_travail": int(form.cleaned_data["charge_travail"]),
                    "interactivite": int(form.cleaned_data["interactivite"]),
                    "type_cours": form.cleaned_data["type_cours"],
                    "niveau_etudiant": form.cleaned_data["niveau_etudiant"],
                }

                model_data = load_current_model()
                if model_data is None:
                    messages.error(request, "Aucun modèle n'est chargé. Entraînez d'abord un modèle.")
                else:
                    prediction_result = predict_satisfaction(model_data, input_data)

                    prediction_explanation = None
                    try:
                        prediction_explanation = get_local_explanation(
                            model_data,
                            input_data,
                        )
                    except Exception:
                        logger.exception(
                            "Impossible de calculer l'explication locale de la prédiction"
                        )

                    feedback = StudentFeedback.objects.create(
                        qualite_enseignement=input_data["qualite_enseignement"],
                        charge_travail=input_data["charge_travail"],
                        interactivite=input_data["interactivite"],
                        type_cours=input_data["type_cours"],
                        niveau_etudiant=input_data["niveau_etudiant"],
                        predicted_satisfaction=bool(prediction_result["prediction"]),
                        probability_satisfied=prediction_result["probability_satisfied"],
                    )

                    notify_user(
                        request.user,
                        "Nouvelle prédiction",
                        f"Avis #{feedback.id} : {prediction_result['satisfaction_text']} "
                        f"({prediction_result['prediction_probability']:.1f}% de confiance).",
                        level="success" if prediction_result["prediction"] else "info",
                        event_type="prediction",
                        target_url=f"{reverse('data_management')}?q={feedback.id}",
                    )

                    return render(
                        request,
                        "predictor/predict.html",
                        {
                            # Garder le formulaire POST lié : les valeurs affichées
                            # à gauche restent exactement celles utilisées par le modèle.
                            "form": form,
                            "prediction_result": prediction_result,
                            "input_data": input_data,
                            "prediction_explanation": prediction_explanation,
                        },
                    )
            except Exception:
                logger.exception("Erreur inattendue pendant la prédiction")
                messages.error(
                    request,
                    "La prédiction n'a pas pu être effectuée. Vérifiez le modèle actif et réessayez.",
                )
    else:
        form = PredictionForm()

    return render(request, "predictor/predict.html", {"form": form})



def _batch_export_directory() -> Path:
    directory = Path(settings.MEDIA_ROOT) / "batch_exports"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _batch_export_path(user_id: int, token: str) -> Path:
    return _batch_export_directory() / f"batch_user_{user_id}_{token}.csv"


def _cleanup_stale_batch_exports():
    directory = Path(settings.MEDIA_ROOT) / "batch_exports"
    if not directory.is_dir():
        return

    cutoff = time.time() - BATCH_EXPORT_MAX_AGE_SECONDS
    for path in directory.glob("batch_user_*.csv"):
        try:
            if path.stat().st_mtime < cutoff:
                path.unlink()
        except OSError:
            logger.warning("Impossible de nettoyer l'export batch temporaire : %s", path)


def _remove_previous_batch_export(request):
    previous = request.session.get(BATCH_SESSION_KEY)
    if not isinstance(previous, dict):
        return

    token = str(previous.get("download_token") or "")
    if not token:
        return

    path = _batch_export_path(request.user.pk, token)
    try:
        path.unlink(missing_ok=True)
    except OSError:
        logger.warning("Impossible de supprimer l'ancien export batch : %s", path)


def _batch_summary(result_df: pd.DataFrame) -> dict:
    total = int(len(result_df))
    satisfied = int((result_df["predicted_satisfaction"] == 1).sum())
    unsatisfied = total - satisfied
    return {
        "total": total,
        "satisfied": satisfied,
        "unsatisfied": unsatisfied,
        "satisfaction_rate": (satisfied / total * 100.0) if total else 0.0,
        "average_confidence": float(result_df["confidence"].mean()) if total else 0.0,
        "average_probability_satisfied": (
            float(result_df["probability_satisfied"].mean()) if total else 0.0
        ),
    }


@login_required(login_url="login_register")
def batch_predict(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")

        if csv_file is None:
            messages.error(request, "Sélectionnez un fichier CSV à traiter.")
            return redirect("batch_predict")

        if not csv_file.name.lower().endswith(".csv"):
            messages.error(request, "Le fichier doit être au format CSV (.csv).")
            return redirect("batch_predict")

        if csv_file.size > BATCH_MAX_FILE_SIZE:
            messages.error(request, "Le fichier dépasse la taille maximale autorisée de 5 Mo.")
            return redirect("batch_predict")

        model_data = load_current_model()
        if model_data is None:
            messages.error(
                request,
                "Aucun modèle actif n'est disponible. Entraînez d'abord un modèle.",
            )
            return redirect("batch_predict")

        try:
            source_df = pd.read_csv(csv_file, encoding="utf-8-sig")
            validated_df = validate_prediction_dataframe(source_df)
            result_df = predict_satisfaction_batch(model_data, validated_df)

            _cleanup_stale_batch_exports()
            _remove_previous_batch_export(request)

            token = str(uuid4())
            export_path = _batch_export_path(request.user.pk, token)
            result_df.to_csv(export_path, index=False, encoding="utf-8-sig")

            preview = json.loads(
                result_df.head(10).to_json(orient="records", force_ascii=False)
            )
            summary = _batch_summary(result_df)
            download_filename = f"predictions_lot_{timezone.now():%Y%m%d_%H%M%S}.csv"

            request.session[BATCH_SESSION_KEY] = {
                "source_filename": Path(csv_file.name).name,
                "download_token": token,
                "download_filename": download_filename,
                "summary": summary,
                "preview": preview,
            }
            request.session.modified = True

            notify_user(
                request.user,
                "Prédiction par lot terminée",
                f"{summary['total']} lignes traitées : {summary['satisfied']} satisfaites et "
                f"{summary['unsatisfied']} non satisfaites.",
                level="success",
                event_type="prediction",
                target_url=reverse("batch_predict"),
            )

            messages.success(
                request,
                f"Prédiction par lot terminée : {summary['total']} lignes traitées.",
            )
            return redirect("batch_predict")

        except (ValueError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
            messages.error(request, f"CSV de prédiction invalide : {exc}")
            return redirect("batch_predict")
        except RuntimeError:
            logger.exception("Erreur interne pendant la prédiction par lot")
            messages.error(
                request,
                "Une erreur interne est survenue pendant la prédiction par lot. Consultez le journal serveur.",
            )
            return redirect("batch_predict")
        except Exception:
            logger.exception("Erreur inattendue pendant la prédiction par lot")
            messages.error(
                request,
                "La prédiction par lot n'a pas pu être effectuée. Vérifiez le fichier et réessayez.",
            )
            return redirect("batch_predict")

    return render(
        request,
        "predictor/batch_predict.html",
        {"batch_result": request.session.get(BATCH_SESSION_KEY)},
    )


@login_required(login_url="login_register")
def batch_predict_download(request, token):
    batch_result = request.session.get(BATCH_SESSION_KEY)
    token_text = str(token)

    if not isinstance(batch_result, dict) or str(batch_result.get("download_token")) != token_text:
        messages.error(request, "Cet export de prédiction par lot n'est pas disponible pour cette session.")
        return redirect("batch_predict")

    export_path = _batch_export_path(request.user.pk, token_text)
    if not export_path.is_file():
        messages.error(request, "Le fichier de résultat a expiré. Relancez la prédiction par lot.")
        return redirect("batch_predict")

    try:
        payload = export_path.read_bytes()
    except OSError:
        logger.exception("Impossible de lire l'export batch %s", export_path)
        messages.error(request, "Le fichier de résultat ne peut pas être téléchargé actuellement.")
        return redirect("batch_predict")

    response = HttpResponse(payload, content_type="text/csv; charset=utf-8")
    filename = batch_result.get("download_filename") or "predictions_lot.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "no-store"
    return response


def _artifact_metric_percent(metrics, key):
    value = (metrics or {}).get(key)
    if value is None:
        return None
    try:
        return round(float(value) * 100.0, 2)
    except (TypeError, ValueError):
        return None


def _model_management_rows(trainings):
    rows = []
    for training in trainings:
        info = inspect_model_artifact(training.model_file)
        metrics = info.get("metrics") or {}
        selection = info.get("model_selection") or {}
        selected_layers = selection.get("selected_hidden_layer_sizes")
        if isinstance(selected_layers, (list, tuple)):
            selected_layers_display = "(" + ", ".join(str(int(value)) for value in selected_layers) + ")"
        else:
            selected_layers_display = None
        rows.append(
            {
                "training": training,
                "available": bool(info.get("available")),
                "compatible": bool(info.get("compatible")),
                "can_activate": bool(info.get("available"))
                and bool(info.get("compatible"))
                and not training.is_active,
                "format_label": info.get("format_label") or "—",
                "reason": info.get("reason") or "",
                "file_name": info.get("file_name") or "—",
                "file_size_mb": info.get("file_size_mb"),
                "precision_percent": _artifact_metric_percent(metrics, "precision"),
                "recall_percent": _artifact_metric_percent(metrics, "recall"),
                "f1_percent": _artifact_metric_percent(metrics, "f1"),
                "train_size": metrics.get("train_size"),
                "test_size": metrics.get("test_size"),
                "cv_f1_percent": _artifact_metric_percent(metrics, "cv_f1_mean"),
                "cv_f1_std_percent": _artifact_metric_percent(metrics, "cv_f1_std"),
                "cv_folds": metrics.get("cv_folds"),
                "candidate_count": metrics.get("candidate_count"),
                "selected_layers_display": selected_layers_display,
                "selected_alpha": selection.get("selected_alpha"),
            }
        )
    return rows



def _active_training_configuration(model_data):
    if not isinstance(model_data, dict):
        return None

    pipeline = model_data.get("pipeline")
    if pipeline is None:
        return {
            "format_label": "Ancien format",
            "layers_display": "—",
            "alpha": None,
            "tuned": False,
            "cv_folds": None,
            "candidate_count": None,
            "cv_f1_percent": None,
            "cv_f1_std_percent": None,
        }

    classifier = pipeline.named_steps.get("classifier")
    if classifier is None:
        return None

    layers = getattr(classifier, "hidden_layer_sizes", ())
    if isinstance(layers, int):
        layers = (layers,)
    layers_display = "(" + ", ".join(str(int(value)) for value in layers) + ")"

    selection = model_data.get("model_selection") or {}
    return {
        "format_label": (
            f"Pipeline v{model_data.get('schema_version')}"
            if model_data.get("schema_version") is not None
            else "Pipeline"
        ),
        "layers_display": layers_display,
        "alpha": float(getattr(classifier, "alpha", 0.0)),
        "tuned": bool(selection),
        "cv_folds": selection.get("cv_splits"),
        "candidate_count": selection.get("candidate_count"),
        "cv_f1_percent": (
            round(float(selection["f1_mean"]) * 100.0, 2)
            if selection.get("f1_mean") is not None
            else None
        ),
        "cv_f1_std_percent": (
            round(float(selection["f1_std"]) * 100.0, 2)
            if selection.get("f1_std") is not None
            else None
        ),
    }

@login_required(login_url="login_register")
def train_model_view(request):
    trainings = ModelTraining.objects.all().order_by("-training_date")[:25]

    # Le tableau reste du plus récent au plus ancien.
    # Le graphique, lui, doit représenter le temps de gauche à droite.
    history_trainings = list(reversed(list(trainings)))

    training_history = {
        "dates": [
            _format_training_chart_datetime(training.training_date, request.LANGUAGE_CODE)
            for training in history_trainings
        ],
        "accuracies": [
            float(training.accuracy * 100)
            for training in history_trainings
        ],
    }

    model_rows = _model_management_rows(trainings)
    active_model_row = next(
        (row for row in model_rows if row["training"].is_active),
        None,
    )
    active_model_warning = None
    if active_model_row and not (
        active_model_row["available"] and active_model_row["compatible"]
    ):
        active_model_warning = (
            "Un entraînement est marqué actif dans la base, mais son fichier modèle "
            "est indisponible ou incompatible. Activez un modèle disponible ou "
            "réentraînez le MLP."
        )

    active_model_data = load_current_model()
    active_training_config = _active_training_configuration(active_model_data)

    if request.method == "POST":
        form = TrainingForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                csv_file = form.cleaned_data["csv_file"]
                if not csv_file.name.lower().endswith(".csv"):
                    raise ValueError("Le fichier doit être au format CSV.")

                df = pd.read_csv(csv_file, encoding="utf-8-sig")
                validated_df = validate_training_dataframe(df)
                accuracy, model_path, metrics = train_model(validated_df)

                with transaction.atomic():
                    ModelTraining.objects.filter(is_active=True).update(is_active=False)
                    training = ModelTraining.objects.create(
                        accuracy=accuracy,
                        dataset_size=metrics["dataset_size"],
                        model_file=model_path,
                        notes=form.cleaned_data["notes"],
                        is_active=True,
                    )

                notify_user(
                    request.user,
                    "Modèle MLP entraîné",
                    f"Entraînement #{training.id} terminé : Accuracy test {accuracy:.2%}, "
                    f"F1 test {metrics['f1']:.2%}, F1 CV {metrics['cv_f1_mean']:.2%} "
                    f"± {metrics['cv_f1_std']:.2%}, {metrics['dataset_size']} échantillons.",
                    level="success",
                    event_type="training",
                    target_url=reverse("train_model"),
                )

                duplicate_info = ""
                if metrics["duplicates_removed"]:
                    duplicate_info = f" | Doublons retirés : {metrics['duplicates_removed']}"

                messages.success(
                    request,
                    "Modèle entraîné avec succès ! "
                    f"Accuracy test : {accuracy:.2%} | F1 test : {metrics['f1']:.2%} | "
                    f"F1 CV : {metrics['cv_f1_mean']:.2%} ± {metrics['cv_f1_std']:.2%} | "
                    f"Couches : {tuple(metrics['selected_hidden_layer_sizes'])} | "
                    f"alpha={metrics['selected_alpha']}"
                    f"{duplicate_info}",
                )
                return redirect("train_model")

            except (ValueError, UnicodeDecodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
                messages.error(request, f"Données d'entraînement invalides : {exc}")
            except Exception:
                logger.exception("Erreur inattendue pendant l'entraînement du modèle")
                messages.error(
                    request,
                    "Une erreur inattendue est survenue pendant l'entraînement. Consultez le journal serveur.",
                )
    else:
        form = TrainingForm()

    context = {
        "form": form,
        "trainings": trainings,
        "model_loaded": active_model_data is not None,
        "active_training_config": active_training_config,
        "training_history": json.dumps(training_history, ensure_ascii=False),
        "model_rows": model_rows,
        "active_model_warning": active_model_warning,
    }
    return render(request, "predictor/train.html", context)


def _breakdown_for_choices(feedbacks, field_name, choices):
    result = {}
    for value, label in choices:
        group = feedbacks.filter(**{field_name: value})
        total = group.count()
        satisfied = group.filter(predicted_satisfaction=True).count()
        result[value] = {
            "label": label,
            "total": total,
            "satisfied": satisfied,
            "unsatisfied": total - satisfied,
            "rate": (satisfied / total * 100) if total else 0,
        }
    return result


def _score_breakdown(feedbacks, field_name):
    rows = []
    for score in range(1, 8):
        group = feedbacks.filter(**{field_name: score})
        total = group.count()
        satisfied = group.filter(predicted_satisfaction=True).count()
        rows.append(
            {
                "score": score,
                "total": total,
                "satisfied": satisfied,
                "rate": (satisfied / total * 100) if total else 0,
            }
        )
    return rows


def _rate_spread(rows):
    rates = [row["rate"] for row in rows if row["total"] > 0]
    if len(rates) < 2:
        return 0.0
    return max(rates) - min(rates)



@login_required(login_url="login_register")
@require_POST
def activate_model(request, pk):
    training = get_object_or_404(ModelTraining, pk=pk)

    try:
        _model_data, resolved_path = load_model_artifact(training.model_file)
    except FileNotFoundError:
        messages.error(
            request,
            f"Le modèle #{training.id} ne peut pas être activé : son fichier .joblib est introuvable.",
        )
        return redirect("train_model")
    except ValueError as exc:
        messages.error(
            request,
            f"Le modèle #{training.id} ne peut pas être activé : {exc}",
        )
        return redirect("train_model")
    except Exception:
        logger.exception("Erreur inattendue pendant la vérification du modèle #%s", training.id)
        messages.error(request, f"Le modèle #{training.id} n'a pas pu être vérifié.")
        return redirect("train_model")

    with transaction.atomic():
        locked_training = ModelTraining.objects.select_for_update().get(pk=pk)
        ModelTraining.objects.select_for_update().filter(
            is_active=True
        ).exclude(pk=pk).update(is_active=False)

        if not locked_training.is_active:
            locked_training.is_active = True
            locked_training.save(update_fields=["is_active"])

    notify_user(
        request.user,
        "Modèle MLP activé",
        f"Entraînement #{training.id} activé : {Path(resolved_path).name}.",
        level="success",
        event_type="training",
        target_url=reverse("train_model"),
    )
    messages.success(request, f"Le modèle #{training.id} est maintenant actif.")
    return redirect("train_model")


@login_required(login_url="login_register")
@require_POST
def deactivate_model(request, pk):
    training = get_object_or_404(ModelTraining, pk=pk)

    with transaction.atomic():
        locked_training = ModelTraining.objects.select_for_update().get(pk=pk)
        was_active = bool(locked_training.is_active)
        if was_active:
            locked_training.is_active = False
            locked_training.save(update_fields=["is_active"])

    if was_active:
        notify_user(
            request.user,
            "Modèle MLP désactivé",
            f"Entraînement #{training.id} désactivé. Les prédictions nécessitent désormais l'activation d'un autre modèle.",
            level="warning",
            event_type="training",
            target_url=reverse("train_model"),
        )
        messages.warning(request, f"Le modèle #{training.id} a été désactivé.")
    else:
        messages.info(request, f"Le modèle #{training.id} était déjà inactif.")

    return redirect("train_model")

@login_required(login_url="login_register")
def statistics(request):
    feedbacks = StudentFeedback.objects.all()
    total = feedbacks.count()
    satisfied = feedbacks.filter(predicted_satisfaction=True).count()
    unsatisfied = total - satisfied
    satisfaction_rate = (satisfied / total * 100) if total else 0
    average_probability = feedbacks.aggregate(value=Avg("probability_satisfied"))["value"]

    stats = {
        "total": total,
        "satisfied": satisfied,
        "unsatisfied": unsatisfied,
        "satisfaction_rate": satisfaction_rate,
        "average_probability": float(average_probability) if average_probability is not None else None,
    }

    type_stats = _breakdown_for_choices(
        feedbacks,
        "type_cours",
        StudentFeedback.TYPE_COURS_CHOICES,
    )
    niveau_stats = _breakdown_for_choices(
        feedbacks,
        "niveau_etudiant",
        StudentFeedback.NIVEAU_CHOICES,
    )

    quality_rows = _score_breakdown(feedbacks, "qualite_enseignement")
    workload_rows = _score_breakdown(feedbacks, "charge_travail")
    interactivity_rows = _score_breakdown(feedbacks, "interactivite")

    type_rows = list(type_stats.values())
    level_rows = list(niveau_stats.values())

    association_factors = [
        {
            "key": "quality",
            "label": "Qualité de l'enseignement",
            "spread": _rate_spread(quality_rows),
        },
        {
            "key": "interactivity",
            "label": "Interactivité",
            "spread": _rate_spread(interactivity_rows),
        },
        {
            "key": "workload",
            "label": "Charge de travail",
            "spread": _rate_spread(workload_rows),
        },
        {
            "key": "course_type",
            "label": "Type de cours",
            "spread": _rate_spread(type_rows),
        },
        {
            "key": "level",
            "label": "Niveau étudiant",
            "spread": _rate_spread(level_rows),
        },
    ]
    association_factors.sort(key=lambda item: item["spread"], reverse=True)
    for factor in association_factors:
        factor["spread"] = round(float(factor["spread"]), 1)
        factor["spread_width"] = max(0, min(100, int(round(factor["spread"]))))

    charts_data = {
        "satisfaction": {
            "labels": ["Satisfaits prédits", "Non satisfaits prédits"],
            "data": [satisfied, unsatisfied],
        },
        "course_types": {
            "labels": [row["label"] for row in type_rows],
            "rates": [round(row["rate"], 2) for row in type_rows],
            "totals": [row["total"] for row in type_rows],
        },
        "levels": {
            "labels": [row["label"] for row in level_rows],
            "rates": [round(row["rate"], 2) for row in level_rows],
            "totals": [row["total"] for row in level_rows],
        },
        "scores": {
            "labels": [str(score) for score in range(1, 8)],
            "quality": [round(row["rate"], 2) for row in quality_rows],
            "workload": [round(row["rate"], 2) for row in workload_rows],
            "interactivity": [round(row["rate"], 2) for row in interactivity_rows],
            "quality_totals": [row["total"] for row in quality_rows],
            "workload_totals": [row["total"] for row in workload_rows],
            "interactivity_totals": [row["total"] for row in interactivity_rows],
        },
    }

    model_data = load_current_model()

    model_importance = None
    if model_data is not None:
        try:
            model_importance = get_global_importance(model_data)
        except Exception:
            logger.exception("Impossible de calculer l'importance globale du modèle")

    return render(
        request,
        "predictor/statistics.html",
        {
            "stats": stats,
            "type_stats": type_stats,
            "niveau_stats": niveau_stats,
            "association_factors": association_factors,
            "charts_data": charts_data,
            "active_model": _active_model_summary(model_data),
            "model_loaded": model_data is not None,
            "model_importance": model_importance,
        },
    )


def _feedback_queryset_from_request(request):
    """Applique les filtres GET sur l'ensemble de la base avant pagination."""
    queryset = StudentFeedback.objects.all()

    status = (request.GET.get("status") or "all").strip().lower()
    if status not in {"all", "satisfied", "unsatisfied", "recent"}:
        status = "all"

    if status == "satisfied":
        queryset = queryset.filter(predicted_satisfaction=True)
    elif status == "unsatisfied":
        queryset = queryset.filter(predicted_satisfaction=False)
    elif status == "recent":
        queryset = queryset.filter(created_at__gte=timezone.now() - timedelta(days=7))

    type_cours = (request.GET.get("type_cours") or "").strip().lower()
    allowed_types = {choice[0] for choice in StudentFeedback.TYPE_COURS_CHOICES}
    if type_cours not in allowed_types:
        type_cours = ""
    if type_cours:
        queryset = queryset.filter(type_cours=type_cours)

    niveau = (request.GET.get("niveau") or "").strip().upper()
    allowed_levels = {choice[0] for choice in StudentFeedback.NIVEAU_CHOICES}
    if niveau not in allowed_levels:
        niveau = ""
    if niveau:
        queryset = queryset.filter(niveau_etudiant=niveau)

    qualite_min_raw = (request.GET.get("qualite_min") or "").strip()
    qualite_min = None
    if qualite_min_raw:
        try:
            candidate = int(qualite_min_raw)
            if 1 <= candidate <= 7:
                qualite_min = candidate
                queryset = queryset.filter(qualite_enseignement__gte=candidate)
        except ValueError:
            pass

    search = (request.GET.get("q") or "").strip()
    if search:
        query = (
            Q(type_cours__icontains=search)
            | Q(niveau_etudiant__icontains=search)
        )
        normalized_id = search.lstrip("#").strip()
        if normalized_id.isdigit():
            query |= Q(pk=int(normalized_id))
        queryset = queryset.filter(query)

    filters = {
        "status": status,
        "type_cours": type_cours,
        "niveau": niveau,
        "qualite_min": "" if qualite_min is None else str(qualite_min),
        "q": search,
    }
    return queryset.order_by("-created_at"), filters


def _query_string_without_page(request):
    params = request.GET.copy()
    params.pop("page", None)
    return params.urlencode()


def _safe_next_url(request):
    candidate = (request.POST.get("next") or "").strip()
    if not candidate:
        return None
    if url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return None


def _redirect_after_data_change(request):
    target = _safe_next_url(request)
    if target:
        return redirect(target)
    return redirect("data_management")


@login_required(login_url="login_register")
def data_management(request):
    all_feedbacks = StudentFeedback.objects.all()
    total_count = all_feedbacks.count()
    satisfied_count = all_feedbacks.filter(predicted_satisfaction=True).count()
    unsatisfied_count = all_feedbacks.filter(predicted_satisfaction=False).count()
    satisfaction_rate = (satisfied_count / total_count * 100) if total_count else 0

    filtered_feedbacks, filters = _feedback_queryset_from_request(request)
    result_count = filtered_feedbacks.count()

    paginator = Paginator(filtered_feedbacks, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Pourcentages calculés en Python : 7/7 doit occuper 100 % de la barre.
    for feedback in page_obj.object_list:
        feedback.qualite_percent = round(max(0, min(7, feedback.qualite_enseignement)) / 7 * 100)
        feedback.interactivite_percent = round(max(0, min(7, feedback.interactivite)) / 7 * 100)

    return render(
        request,
        "predictor/data.html",
        {
            "feedbacks": page_obj,
            "total_count": total_count,
            "satisfied_count": satisfied_count,
            "unsatisfied_count": unsatisfied_count,
            "satisfaction_rate": satisfaction_rate,
            "result_count": result_count,
            "filters": filters,
            "query_string": _query_string_without_page(request),
            "return_url": request.get_full_path(),
        },
    )


@login_required(login_url="login_register")
def feedback_detail(request, pk):
    feedback = get_object_or_404(StudentFeedback, pk=pk)

    if feedback.predicted_satisfaction is True:
        prediction_label = "Satisfait"
    elif feedback.predicted_satisfaction is False:
        prediction_label = "Non satisfait"
    else:
        prediction_label = "Indisponible"

    return JsonResponse(
        {
            "id": feedback.id,
            "qualite_enseignement": feedback.qualite_enseignement,
            "charge_travail": feedback.charge_travail,
            "interactivite": feedback.interactivite,
            "type_cours": feedback.type_cours,
            "niveau_etudiant": feedback.niveau_etudiant,
            "predicted_satisfaction": feedback.predicted_satisfaction,
            "prediction_label": prediction_label,
            "probability_satisfied": feedback.probability_satisfied,
            "created_at": timezone.localtime(feedback.created_at).strftime("%d/%m/%Y %H:%M"),
            "updated_at": timezone.localtime(feedback.updated_at).strftime("%d/%m/%Y %H:%M"),
        }
    )


@login_required(login_url="login_register")
@require_POST
def feedback_update(request, pk):
    feedback = get_object_or_404(StudentFeedback, pk=pk)
    form = StudentFeedbackEditForm(request.POST, instance=feedback)

    if not form.is_valid():
        first_error = next(iter(form.errors.values()), None)
        detail = first_error[0] if first_error else "Données invalides."
        messages.error(request, f"Modification impossible : {detail}")
        return _redirect_after_data_change(request)

    model_data = load_current_model()
    if model_data is None:
        messages.error(
            request,
            "Modification impossible : aucun modèle actif n'est disponible pour recalculer la prédiction.",
        )
        return _redirect_after_data_change(request)

    try:
        input_data = {
            "qualite_enseignement": form.cleaned_data["qualite_enseignement"],
            "charge_travail": form.cleaned_data["charge_travail"],
            "interactivite": form.cleaned_data["interactivite"],
            "type_cours": form.cleaned_data["type_cours"],
            "niveau_etudiant": form.cleaned_data["niveau_etudiant"],
        }
        prediction_result = predict_satisfaction(model_data, input_data)

        with transaction.atomic():
            updated_feedback = form.save(commit=False)
            updated_feedback.predicted_satisfaction = bool(prediction_result["prediction"])
            updated_feedback.probability_satisfied = prediction_result["probability_satisfied"]
            updated_feedback.save()

        messages.success(
            request,
            f"Avis #{feedback.id} modifié. La prédiction a été recalculée automatiquement.",
        )
        notify_user(
            request.user,
            "Avis modifié",
            f"L'avis #{feedback.id} a été modifié et sa prédiction recalculée.",
            level="success",
            event_type="data",
            target_url=f"{reverse('data_management')}?q={feedback.id}",
        )

    except Exception:
        logger.exception("Erreur inattendue pendant la modification de l'avis %s", feedback.id)
        messages.error(
            request,
            "La modification n'a pas pu être enregistrée. Vérifiez le modèle actif et réessayez.",
        )

    return _redirect_after_data_change(request)


@login_required(login_url="login_register")
@require_POST
def feedback_delete(request, pk):
    feedback = get_object_or_404(StudentFeedback, pk=pk)
    feedback_id = feedback.id
    feedback.delete()

    notify_user(
        request.user,
        "Avis supprimé",
        f"L'avis #{feedback_id} a été supprimé de la base.",
        level="warning",
        event_type="data",
        target_url=reverse("data_management"),
    )
    messages.success(request, f"Avis #{feedback_id} supprimé.")
    return _redirect_after_data_change(request)


@login_required(login_url="login_register")
def export_data(request):
    try:
        feedbacks, _ = _feedback_queryset_from_request(request)

        data = [
            {
                "id": feedback.id,
                "qualite_enseignement": feedback.qualite_enseignement,
                "charge_travail": feedback.charge_travail,
                "interactivite": feedback.interactivite,
                "type_cours": feedback.type_cours,
                "niveau_etudiant": feedback.niveau_etudiant,
                "predicted_satisfaction": feedback.predicted_satisfaction,
                "probability_satisfied": feedback.probability_satisfied,
                "created_at": timezone.localtime(feedback.created_at).isoformat(),
            }
            for feedback in feedbacks
        ]

        df = pd.DataFrame(data)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="avis_etudiants_export.csv"'
        df.to_csv(response, index=False, encoding="utf-8-sig")
        notify_user(
            request.user,
            "Export CSV généré",
            f"Export terminé : {len(data)} ligne(s) incluse(s).",
            level="success",
            event_type="export",
            target_url=reverse("data_management"),
        )
        return response
    except Exception:
        logger.exception("Erreur inattendue pendant l'export CSV")
        messages.error(request, "L'export CSV n'a pas pu être généré.")
        return redirect("data_management")
