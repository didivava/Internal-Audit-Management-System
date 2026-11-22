import logging

from django.conf import settings
from django.db import DatabaseError, connection
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@require_GET
def home(request):
    if not settings.DEBUG:
        return HttpResponse(
            "The audit workspace is not ready for production use.",
            status=503,
            content_type="text/plain",
        )
    return render(request, "index.html")


@require_GET
def live(request):
    return JsonResponse({"status": "ok"})


@require_GET
def ready(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        logger.exception("Readiness check failed because the database is unavailable.")
        return JsonResponse({"status": "not_ready"}, status=503)
    return JsonResponse({"status": "ready", "database": "ok"})
