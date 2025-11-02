"""
Middleware de segurança para APIs
Rate limiting, validação de requisições e logging
"""
import json
import time
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class RateLimiter:
    """Gerenciador de rate limiting usando Redis"""

    @classmethod
    def _get_rate_limits_config(cls):
        """Obtém configurações de rate limit de settings.py"""
        return getattr(settings, 'API_RATE_LIMITS', {
            # APIs de autenticação (mais restritivas)
            '/api/oauth/token/': {'requests': 10, 'window': 60},
            '/api/v1/cliente/login/': {'requests': 5, 'window': 60},

            # APIs de transação (moderadas)
            '/api/v1/transacao/': {'requests': 30, 'window': 60},
            '/api/v1/cliente/extrato/': {'requests': 20, 'window': 60},
            '/api/v1/cliente/comprovante/': {'requests': 20, 'window': 60},

            # POSP2 (crítico - mais permissivo)
            '/posp2/v1/checkout/': {'requests': 100, 'window': 60},
            '/posp2/v1/consulta/': {'requests': 50, 'window': 60},

            # Default para outros endpoints
            'default': {'requests': 60, 'window': 60},
        })

    @classmethod
    def get_limit_config(cls, path):
        """Retorna configuração de limite para um path"""
        rate_limits = cls._get_rate_limits_config()

        # Busca exata
        if path in rate_limits:
            return rate_limits[path]

        # Busca por prefixo (ex: /api/v1/cliente/*)
        for pattern, config in rate_limits.items():
            if pattern != 'default' and path.startswith(pattern):
                return config

        # Fallback para default
        return rate_limits.get('default', {'requests': 60, 'window': 60})

    @classmethod
    def check_rate_limit(cls, request):
        """
        Verifica se requisição excede rate limit

        Returns:
            tuple: (allowed: bool, retry_after: int)
        """
        try:
            # Identificar cliente (IP ou token)
            identifier = cls._get_client_identifier(request)
            path = request.path

            # Obter configuração de limite
            limit_config = cls.get_limit_config(path)
            max_requests = limit_config['requests']
            window_seconds = limit_config['window']

            # Chave no cache
            cache_key = f"rate_limit:{identifier}:{path}"
            ttl_key = f"{cache_key}:ttl"

            # Obter contador atual
            current_count = cache.get(cache_key, 0)

            if current_count >= max_requests:
                # Limite excedido - calcular tempo restante
                window_end = cache.get(ttl_key, 0)
                retry_after = max(1, int(window_end - time.time()))

                registrar_log('comum.middleware',
                             f"Rate limit excedido - IP: {identifier}, Path: {path}, Count: {current_count}/{max_requests}",
                             nivel='WARNING')
                return False, retry_after

            # Incrementar contador
            if current_count == 0:
                # Primeiro request na janela - criar contador e timestamp de expiração
                window_end = time.time() + window_seconds
                cache.set(cache_key, 1, timeout=window_seconds)
                cache.set(ttl_key, window_end, timeout=window_seconds)
            else:
                # Incrementar contador existente
                cache.incr(cache_key)

            return True, 0

        except Exception as e:
            registrar_log('comum.middleware', f"Erro no rate limiter: {str(e)}", nivel='ERROR')
            # Em caso de erro, permitir requisição (fail-open)
            return True, 0

    @staticmethod
    def _get_client_identifier(request):
        """Extrai identificador único do cliente (IP ou token)"""
        # Tentar obter do token JWT primeiro
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1][:20]  # Primeiros 20 chars do token
            return f"token_{token}"

        # Fallback para IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', 'unknown')

        return f"ip_{ip}"


class APISecurityMiddleware:
    """
    Middleware de segurança para APIs
    - Rate limiting
    - Validação de requisições
    - Logging de segurança
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Pular para endpoints não-API
        if not self._is_api_endpoint(request.path):
            return self.get_response(request)

        # APIs internas: sem rate limiting
        if request.path.startswith('/api/internal/'):
            return self._handle_internal_api(request)

        # APIs externas: rate limiting completo
        # 1. Rate Limiting
        allowed, retry_after = RateLimiter.check_rate_limit(request)
        if not allowed:
            return JsonResponse({
                'erro': 'Limite de requisições excedido',
                'mensagem': f'Tente novamente em {retry_after} segundos',
                'retry_after': retry_after
            }, status=429)

        # 2. Validação básica de requisição
        validation_error = self._validate_request(request)
        if validation_error:
            registrar_log('comum.middleware',
                         f"Requisição inválida - {validation_error} - Path: {request.path}",
                         nivel='WARNING')
            return JsonResponse({
                'erro': 'Requisição inválida',
                'mensagem': validation_error
            }, status=400)

        # 3. Log de acesso (apenas em desenvolvimento)
        if settings.DEBUG:
            self._log_request(request)

        # Processar requisição
        response = self.get_response(request)

        # 4. Headers de segurança
        response = self._add_security_headers(response)

        return response

    def _is_api_endpoint(self, path):
        """Verifica se é endpoint de API"""
        api_prefixes = ['/api/', '/posp2/']
        return any(path.startswith(prefix) for prefix in api_prefixes)

    def _handle_internal_api(self, request):
        """
        Handler para APIs internas (comunicação entre containers)
        Sem rate limiting, apenas validação básica e logging
        """
        # Validação básica de requisição
        validation_error = self._validate_request(request)
        if validation_error:
            registrar_log('comum.middleware',
                         f"Internal API - Requisição inválida: {validation_error} - Path: {request.path}",
                         nivel='WARNING')
            return JsonResponse({
                'erro': 'Requisição inválida',
                'mensagem': validation_error
            }, status=400)

        # Log de chamadas internas (produção também)
        registrar_log('comum.middleware',
                     f"Internal API - {request.method} {request.path} - "
                     f"Origin: {request.META.get('REMOTE_ADDR', 'unknown')}",
                     nivel='INFO')

        # Processar requisição
        response = self.get_response(request)

        # Headers de segurança
        response = self._add_security_headers(response)

        return response

    def _validate_request(self, request):
        """Validação básica de requisição"""
        # Validar Content-Type para POST/PUT
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.META.get('CONTENT_TYPE', '')

            # Aceitar apenas JSON ou form-data
            if not (content_type.startswith('application/json') or
                    content_type.startswith('application/x-www-form-urlencoded') or
                    content_type.startswith('multipart/form-data')):
                return f"Content-Type não suportado: {content_type}"

        # Validar tamanho do body (máximo 10MB)
        if hasattr(request, 'body'):
            try:
                body_size = len(request.body)
                max_size = 10 * 1024 * 1024  # 10MB
                if body_size > max_size:
                    return f"Payload muito grande: {body_size} bytes (max: {max_size})"
            except:
                pass

        return None

    def _log_request(self, request):
        """Log de requisição (apenas em DEBUG)"""
        registrar_log('comum.middleware',
                     f"API Request - Method: {request.method}, Path: {request.path}, "
                     f"IP: {request.META.get('REMOTE_ADDR', 'unknown')}",
                     nivel='INFO')

    def _add_security_headers(self, response):
        """Adiciona headers de segurança à resposta"""
        # Prevenir clickjacking
        response['X-Frame-Options'] = 'DENY'

        # Prevenir MIME sniffing
        response['X-Content-Type-Options'] = 'nosniff'

        # XSS Protection
        response['X-XSS-Protection'] = '1; mode=block'

        # Strict Transport Security (HSTS) - apenas em produção
        if not settings.DEBUG:
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'

        return response

    def process_exception(self, request, exception):
        """Tratamento de exceções"""
        registrar_log('comum.middleware',
                     f"Exception em API - Path: {request.path}, Error: {str(exception)}",
                     nivel='ERROR')
        return None
