"""
Middleware de Correlation ID para rastreamento de requisições entre containers.

Gera ou propaga um ID único para cada requisição, permitindo rastrear
o fluxo completo de uma transação através de múltiplos serviços.

Uso:
- Adicionar 'wallclub_core.middleware.correlation_middleware.CorrelationIdMiddleware'
  ao MIDDLEWARE do Django settings.py
- O header X-Correlation-ID será propagado automaticamente
"""
import uuid
from django.conf import settings


CORRELATION_ID_HEADER = 'HTTP_X_CORRELATION_ID'
CORRELATION_ID_RESPONSE_HEADER = 'X-Correlation-ID'


class CorrelationIdMiddleware:
    """
    Middleware que gerencia Correlation IDs para rastreamento distribuído.

    - Se a requisição já possui X-Correlation-ID, propaga o mesmo
    - Se não possui, gera um novo UUID
    - Adiciona o ID ao response header
    - Disponibiliza via request.correlation_id
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        correlation_id = request.META.get(CORRELATION_ID_HEADER)

        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        request.correlation_id = correlation_id

        response = self.get_response(request)

        response[CORRELATION_ID_RESPONSE_HEADER] = correlation_id

        return response


def get_correlation_id():
    """
    Obtém o correlation_id do contexto atual.
    Útil para logging em código que não tem acesso direto ao request.

    Retorna None se não houver correlation_id no contexto.
    """
    import threading
    return getattr(threading.current_thread(), 'correlation_id', None)


def set_correlation_id(correlation_id):
    """
    Define o correlation_id no contexto atual.
    Usado internamente pelo middleware.
    """
    import threading
    threading.current_thread().correlation_id = correlation_id
