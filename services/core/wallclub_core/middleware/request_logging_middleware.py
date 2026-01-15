"""
Middleware de logging estruturado para requisições HTTP.

Registra informações detalhadas sobre cada requisição e resposta,
incluindo tempo de processamento, status, e dados relevantes para debugging.

Uso:
- Adicionar 'wallclub_core.middleware.request_logging_middleware.RequestLoggingMiddleware'
  ao MIDDLEWARE do Django settings.py
"""
import time
import json
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class RequestLoggingMiddleware:
    """
    Middleware que registra logs estruturados de requisições HTTP.

    Registra:
    - Método HTTP e path
    - Tempo de processamento
    - Status code da resposta
    - Correlation ID (se disponível)
    - IP do cliente
    - User agent
    """

    PATHS_IGNORADOS = [
        '/health/',
        '/favicon.ico',
        '/static/',
        '/media/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response
        self.enabled = getattr(settings, 'REQUEST_LOGGING_ENABLED', True)
        self.log_body = getattr(settings, 'REQUEST_LOGGING_BODY', False)

    def __call__(self, request):
        if not self.enabled or self._should_ignore(request.path):
            return self.get_response(request)

        start_time = time.time()

        response = self.get_response(request)

        duration_ms = (time.time() - start_time) * 1000

        self._log_request(request, response, duration_ms)

        return response

    def _should_ignore(self, path):
        """Verifica se o path deve ser ignorado no logging"""
        for ignored in self.PATHS_IGNORADOS:
            if path.startswith(ignored):
                return True
        return False

    def _log_request(self, request, response, duration_ms):
        """Registra log da requisição"""
        correlation_id = getattr(request, 'correlation_id', '-')

        ip = self._get_client_ip(request)

        log_data = {
            'method': request.method,
            'path': request.path,
            'status': response.status_code,
            'duration_ms': round(duration_ms, 2),
            'ip': ip,
            'correlation_id': correlation_id,
        }

        if request.user and request.user.is_authenticated:
            log_data['user_id'] = request.user.id

        status = response.status_code
        if status >= 500:
            nivel = 'error'
        elif status >= 400:
            nivel = 'warning'
        else:
            nivel = 'info'

        log_msg = f"{request.method} {request.path} {status} {round(duration_ms, 2)}ms"

        if correlation_id != '-':
            log_msg = f"[{correlation_id[:8]}] {log_msg}"

        registrar_log('http.request', log_msg, nivel=nivel)

    def _get_client_ip(self, request):
        """Obtém IP real do cliente considerando proxies"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '-')
