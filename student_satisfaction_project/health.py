from __future__ import annotations

from django.db import DatabaseError, connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET


def _database_ready() -> bool:
    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return False
    return True


@require_GET
def health_check(request):
    ready = _database_ready()
    response = JsonResponse(
        {"status": "ok" if ready else "unavailable"},
        status=200 if ready else 503,
    )
    response["Cache-Control"] = "no-store"
    return response
