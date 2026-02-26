"""
Sistema de Health Checks para Monitoramento
Verifica status de dependências críticas (MySQL, Redis, Celery)
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import logging
import time
from datetime import datetime

logger = logging.getLogger(__name__)


def check_database():
    """Verifica conexão com MySQL"""
    try:
        start = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        latency = (time.time() - start) * 1000
        return {'status': 'healthy', 'latency_ms': round(latency, 2)}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}


def check_redis():
    """Verifica conexão com Redis"""
    try:
        start = time.time()
        cache.set('health_check', 'ok', 10)
        result = cache.get('health_check')
        latency = (time.time() - start) * 1000

        if result == 'ok':
            return {'status': 'healthy', 'latency_ms': round(latency, 2)}
        else:
            return {'status': 'unhealthy', 'error': 'Cache read/write failed'}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}


def check_celery():
    """Verifica status das filas Celery"""
    try:
        from celery import current_app

        inspect = current_app.control.inspect(timeout=2.0)
        stats = inspect.stats()
        active = inspect.active()

        if stats is None:
            return {'status': 'unhealthy', 'error': 'No workers available'}

        worker_count = len(stats)
        active_tasks = sum(len(tasks) for tasks in (active or {}).values())

        return {
            'status': 'healthy',
            'workers': worker_count,
            'active_tasks': active_tasks
        }
    except Exception as e:
        logger.error(f"Celery health check failed: {e}")
        return {'status': 'unhealthy', 'error': str(e)}


@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Endpoint básico de health check
    GET /health/
    """
    return JsonResponse({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'wallclub'
    })


@csrf_exempt
@require_http_methods(["GET"])
def health_live(request):
    """
    Liveness probe - verifica se o container está vivo
    GET /health/live/
    """
    return JsonResponse({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    })


@csrf_exempt
@require_http_methods(["GET"])
def health_ready(request):
    """
    Readiness probe - verifica se o container está pronto para receber tráfego
    GET /health/ready/
    """
    checks = {
        'database': check_database(),
        'redis': check_redis(),
    }

    all_healthy = all(check['status'] == 'healthy' for check in checks.values())

    status_code = 200 if all_healthy else 503

    return JsonResponse({
        'status': 'ready' if all_healthy else 'not_ready',
        'timestamp': datetime.now().isoformat(),
        'checks': checks
    }, status=status_code)


@csrf_exempt
@require_http_methods(["GET"])
def health_startup(request):
    """
    Startup probe - verifica se o container terminou de inicializar
    GET /health/startup/
    """
    checks = {
        'database': check_database(),
        'redis': check_redis(),
        'celery': check_celery(),
    }

    all_healthy = all(check['status'] == 'healthy' for check in checks.values())

    status_code = 200 if all_healthy else 503

    return JsonResponse({
        'status': 'started' if all_healthy else 'starting',
        'timestamp': datetime.now().isoformat(),
        'checks': checks
    }, status=status_code)
