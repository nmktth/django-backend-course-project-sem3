from django.views.generic import TemplateView
from django.http import JsonResponse
from django.db import connections
from django.db.utils import OperationalError


class IndexView(TemplateView):
    template_name = "index.html"


def health_check(request):  # pylint: disable=unused-argument
    """
    Проверка работоспособности приложения и соединения с БД.
    Используется для мониторинга и проверки деплоя.
    """
    db_conn = True
    try:
        connections['default'].cursor()
    except OperationalError:
        db_conn = False

    if db_conn:
        return JsonResponse({"status": "ok", "database": "connected"}, status=200)

    return JsonResponse({"status": "error", "database": "disconnected"}, status=503)
