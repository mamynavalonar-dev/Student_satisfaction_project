from __future__ import annotations

import logging

from django.db import DatabaseError

from .models import Notification

logger = logging.getLogger(__name__)


def notify_user(user, title, message, *, level="info", event_type="system", target_url=""):
    """Crée une notification sans jamais casser l'action métier principale."""
    if not getattr(user, "is_authenticated", False):
        return None

    try:
        return Notification.objects.create(
            user=user,
            title=str(title)[:120],
            message=str(message)[:500],
            level=level if level in {"info", "success", "warning", "error"} else "info",
            event_type=event_type if event_type in {"auth", "prediction", "training", "data", "export", "system"} else "system",
            target_url=str(target_url or "")[:255],
        )
    except DatabaseError:
        logger.exception("Impossible d'enregistrer la notification %s", title)
        return None
