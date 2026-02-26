"""
View customizada para endpoint /metrics no formato Prometheus
"""
from django.http import HttpResponse
from django.db import connection
import time


def metrics_view(request):
    """
    Endpoint /metrics que expõe métricas básicas no formato Prometheus.

    Métricas expostas:
    - up: Indica que o serviço está funcionando (sempre 1)
    - django_http_requests_total: Total de requisições HTTP
    - django_db_connection_status: Status da conexão com banco de dados
    """

    # Verificar conexão com banco de dados
    db_status = 1
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        db_status = 0

    # Timestamp atual
    timestamp = int(time.time() * 1000)

    # Métricas no formato Prometheus
    metrics = [
        '# HELP up Service is up and running',
        '# TYPE up gauge',
        'up 1',
        '',
        '# HELP django_db_connection_status Database connection status (1=connected, 0=disconnected)',
        '# TYPE django_db_connection_status gauge',
        f'django_db_connection_status {db_status}',
        '',
        '# HELP django_info Django application information',
        '# TYPE django_info gauge',
        'django_info{version="4.2.23"} 1',
        '',
    ]

    return HttpResponse('\n'.join(metrics), content_type='text/plain; version=0.0.4; charset=utf-8')
