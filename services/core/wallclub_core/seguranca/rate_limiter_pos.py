"""
Rate Limiter específico para endpoints POS
Implementa rate limiting por terminal_id além do IP
"""
from functools import wraps
from django.http import JsonResponse
from django.core.cache import cache
from wallclub_core.utilitarios.log_control import registrar_log
import time


class POSRateLimiter:
    """
    Rate limiter específico para POS
    Controla requisições por terminal_id e IP
    """

    # Configurações de rate limit por terminal
    TERMINAL_LIMITS = {
        'default': {
            'requests_per_minute': 50,
            'requests_per_hour': 500,
        },
        'critical': {  # Endpoints críticos (autorização, transação)
            'requests_per_minute': 30,
            'requests_per_hour': 300,
        }
    }

    @classmethod
    def check_terminal_rate_limit(cls, terminal_id, endpoint_type='default'):
        """
        Verifica rate limit por terminal

        Args:
            terminal_id: ID do terminal POS
            endpoint_type: 'default' ou 'critical'

        Returns:
            tuple: (allowed: bool, retry_after: int, message: str)
        """
        if not terminal_id:
            return True, 0, None

        try:
            limits = cls.TERMINAL_LIMITS.get(endpoint_type, cls.TERMINAL_LIMITS['default'])

            # Verificar limite por minuto
            minute_key = f"pos_rate_limit:terminal:{terminal_id}:minute"
            minute_count = cache.get(minute_key, 0)

            if minute_count >= limits['requests_per_minute']:
                retry_after = cache.ttl(minute_key) or 60
                message = f"Terminal {terminal_id} excedeu limite de {limits['requests_per_minute']} requisições/minuto"

                registrar_log('seguranca.rate_limit',
                             f"Rate limit TERMINAL excedido - Terminal: {terminal_id}, "
                             f"Count: {minute_count}/{limits['requests_per_minute']}/min",
                             nivel='WARNING')

                return False, retry_after, message

            # Verificar limite por hora
            hour_key = f"pos_rate_limit:terminal:{terminal_id}:hour"
            hour_count = cache.get(hour_key, 0)

            if hour_count >= limits['requests_per_hour']:
                retry_after = cache.ttl(hour_key) or 3600
                message = f"Terminal {terminal_id} excedeu limite de {limits['requests_per_hour']} requisições/hora"

                registrar_log('seguranca.rate_limit',
                             f"Rate limit TERMINAL excedido - Terminal: {terminal_id}, "
                             f"Count: {hour_count}/{limits['requests_per_hour']}/hora",
                             nivel='WARNING')

                return False, retry_after, message

            # Incrementar contadores
            if minute_count == 0:
                cache.set(minute_key, 1, timeout=60)
            else:
                cache.incr(minute_key)

            if hour_count == 0:
                cache.set(hour_key, 1, timeout=3600)
            else:
                cache.incr(hour_key)

            return True, 0, None

        except Exception as e:
            registrar_log('seguranca.rate_limit',
                         f"Erro no rate limiter POS: {str(e)}",
                         nivel='ERROR')
            # Fail-open em caso de erro
            return True, 0, None

    @classmethod
    def log_suspicious_activity(cls, terminal_id, ip, endpoint, reason):
        """
        Registra atividade suspeita para análise
        """
        try:
            # Log detalhado
            registrar_log('seguranca.suspicious',
                         f"ATIVIDADE SUSPEITA - Terminal: {terminal_id}, IP: {ip}, "
                         f"Endpoint: {endpoint}, Motivo: {reason}",
                         nivel='WARNING')

            # Contador de atividades suspeitas
            suspicious_key = f"pos_suspicious:terminal:{terminal_id}:daily"
            count = cache.get(suspicious_key, 0)
            cache.set(suspicious_key, count + 1, timeout=86400)  # 24h

            # Alerta se muitas atividades suspeitas
            if count + 1 >= 10:
                registrar_log('seguranca.alert',
                             f"ALERTA: Terminal {terminal_id} com {count + 1} atividades suspeitas hoje",
                             nivel='ERROR')

        except Exception as e:
            registrar_log('seguranca.rate_limit',
                         f"Erro ao registrar atividade suspeita: {str(e)}",
                         nivel='ERROR')


def require_pos_rate_limit(endpoint_type='default'):
    """
    Decorator para aplicar rate limiting em endpoints POS

    Args:
        endpoint_type: 'default' ou 'critical'

    Usage:
        @require_pos_rate_limit('critical')
        def solicitar_autorizacao_saldo(request):
            ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            # Extrair terminal_id do request
            terminal_id = None

            # Tentar obter do body (POST/PUT)
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    if hasattr(request, 'data'):
                        terminal_id = request.data.get('terminal_id') or request.data.get('terminalId')
                    elif request.POST:
                        terminal_id = request.POST.get('terminal_id') or request.POST.get('terminalId')
                except:
                    pass

            # Tentar obter do query params (GET)
            if not terminal_id:
                terminal_id = request.GET.get('terminal_id') or request.GET.get('terminalId')

            # Tentar obter do header
            if not terminal_id:
                terminal_id = request.META.get('HTTP_X_TERMINAL_ID')

            # Verificar rate limit
            if terminal_id:
                allowed, retry_after, message = POSRateLimiter.check_terminal_rate_limit(
                    terminal_id,
                    endpoint_type
                )

                if not allowed:
                    # Registrar atividade suspeita
                    ip = request.META.get('REMOTE_ADDR', 'unknown')
                    POSRateLimiter.log_suspicious_activity(
                        terminal_id,
                        ip,
                        request.path,
                        f"Rate limit excedido ({endpoint_type})"
                    )

                    return JsonResponse({
                        'sucesso': False,
                        'erro': 'Limite de requisições excedido',
                        'mensagem': message,
                        'retry_after': retry_after
                    }, status=429)

            # Processar requisição normalmente
            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
