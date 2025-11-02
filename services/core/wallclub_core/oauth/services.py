"""
Serviços OAuth 2.0 para WallClub.
Lógica de negócio centralizada para OAuth.
"""
import secrets
import uuid
from datetime import datetime, timedelta
from wallclub_core.utilitarios.log_control import registrar_log


class OAuthService:
    """Serviço para gerenciamento OAuth 2.0"""

    @staticmethod
    def generate_access_token():
        """Gera access token seguro"""
        return f"wc_at_{secrets.token_urlsafe(32)}"

    @staticmethod
    def generate_refresh_token():
        """Gera refresh token seguro"""
        return f"wc_rt_{secrets.token_urlsafe(32)}"

    @staticmethod
    def validate_brand_access(brand, canal_id):
        """
        Valida se a marca OAuth tem permissão para acessar o canal

        Args:
            brand (str): Marca do cliente OAuth (wallclub, aclub, dotz)
            canal_id (int): ID do canal solicitado

        Returns:
            bool: True se permitido, False caso contrário
        """
        brand_canal_mapping = {
            'wallclub': [1],  # Canal WallClub
            'aclub': [6],     # Canal AClub
            'dotz': [7],      # Canal Dotz (exemplo)
        }

        allowed_canals = brand_canal_mapping.get(brand.lower(), [])
        return canal_id in allowed_canals

    @staticmethod
    def is_context_allowed(client_id, context):
        """
        Verifica se o client_id é permitido para o contexto (apps, posp2, checkout)

        Args:
            client_id (str): ID do cliente OAuth
            context (str): Contexto de uso (apps, posp2, checkout)

        Returns:
            bool: True se permitido, False caso contrário
        """
        context_patterns = {
            'apps': ['mobile', '_app_'],
            'posp2': ['pos', '_terminal_'],
            'checkout': ['checkout', '_web_']
        }

        patterns = context_patterns.get(context, [])
        return any(pattern in client_id.lower() for pattern in patterns)

    @staticmethod
    def is_server_based_client(client_id):
        """
        Identifica se cliente é server-to-server (não precisa device fingerprint)

        Clientes server-based:
        - POS/Terminal (máquinas fixas)
        - Internos (wallclub_django_internal, risk engine)
        - Admin tools

        Args:
            client_id (str): ID do cliente OAuth

        Returns:
            bool: True se é cliente server-based
        """
        server_patterns = [
            'pos',           # Terminal POS
            '_terminal_',    # Terminais em geral
            '_internal',     # Sistemas internos
            'riskengine',    # Risk Engine
            'wallclub_django', # Django interno
            '_admin',        # Ferramentas admin
            '_server_'       # Qualquer servidor
        ]

        client_id_lower = client_id.lower()
        return any(pattern in client_id_lower for pattern in server_patterns)

    @staticmethod
    def create_oauth_token(client, expires_in_hours=24, device_fingerprint=None):
        """
        Cria novo token OAuth para um cliente

        Args:
            client: Instância de OAuthClient
            expires_in_hours (int): Horas até expiração
            device_fingerprint (str): Fingerprint do dispositivo (opcional)

        Returns:
            OAuthToken: Token criado
        """
        from .models import OAuthToken

        access_token = OAuthService.generate_access_token()
        refresh_token = OAuthService.generate_refresh_token()

        return OAuthToken.objects.create(
            client=client,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=datetime.now() + timedelta(hours=expires_in_hours),
            device_fingerprint=device_fingerprint
        )

    @staticmethod
    def validate_oauth_token(access_token):
        """
        Valida token OAuth

        Args:
            access_token (str): Token a ser validado

        Returns:
            OAuthToken|None: Token válido ou None se inválido
        """
        from .models import OAuthToken

        try:
            token = OAuthToken.objects.select_related('client').get(
                access_token=access_token,
                is_active=True
            )

            if token.is_expired():
                registrar_log("comum.oauth", f"Token expirado: {access_token[:12]}...", nivel='WARNING')
                return None

            # Registrar uso
            token.record_usage()

            registrar_log("comum.oauth", f"Token válido: {token.client.name}", nivel='DEBUG')
            return token

        except OAuthToken.DoesNotExist:
            registrar_log("comum.oauth", f"Token não encontrado: {access_token[:12]}...", nivel='WARNING')
            return None

    @staticmethod
    def refresh_token(refresh_token_value):
        """
        Renova access_token usando refresh_token

        Args:
            refresh_token_value (str): Refresh token

        Returns:
            dict: {'success': bool, 'access_token': str, 'error': str}
        """
        from .models import OAuthToken

        try:
            token = OAuthToken.objects.select_related('client').get(
                refresh_token=refresh_token_value,
                is_active=True
            )

            # Gerar novo access_token
            new_access_token = token.refresh_access_token()

            registrar_log("comum.oauth", f"Token renovado: {token.client.name}", nivel='INFO')

            return {
                'success': True,
                'access_token': new_access_token,
                'expires_in': 86400
            }

        except OAuthToken.DoesNotExist:
            registrar_log("comum.oauth", "Refresh token inválido", nivel='ERROR')
            return {
                'success': False,
                'error': 'invalid_grant',
                'error_description': 'Refresh token inválido'
            }

    @staticmethod
    def revoke_token(access_token):
        """
        Revoga token OAuth (marca como inativo)

        Args:
            access_token (str): Access token a ser revogado

        Returns:
            bool: True se revogado, False se não encontrado
        """
        from .models import OAuthToken

        try:
            token = OAuthToken.objects.get(
                access_token=access_token,
                is_active=True
            )

            token.is_active = False
            token.save(update_fields=['is_active'])

            registrar_log("comum.oauth", f"Token revogado: {token.client.name}", nivel='INFO')
            return True

        except OAuthToken.DoesNotExist:
            registrar_log("comum.oauth", "Token não encontrado", nivel='ERROR')
            return False

    @staticmethod
    def extract_device_fingerprint(request):
        """
        Extrai device fingerprint da requisição

        Args:
            request: Django/DRF request object

        Returns:
            str: Hash MD5 do fingerprint do dispositivo
        """
        import hashlib

        # Coleta dados do dispositivo
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')

        # Monta string única do dispositivo
        fingerprint_data = f"{user_agent}|{accept_language}|{accept_encoding}"

        # Gera hash MD5
        fingerprint_hash = hashlib.md5(fingerprint_data.encode()).hexdigest()

        return fingerprint_hash

    @staticmethod
    def validate_device_fingerprint(token, request):
        """
        Valida se o device fingerprint da requisição corresponde ao token

        Args:
            token: OAuthToken instance
            request: Django/DRF request object

        Returns:
            bool: True se válido ou não configurado, False se inválido
        """
        if not token.device_fingerprint:
            # Token sem fingerprint configurado - permite
            return True

        current_fingerprint = OAuthService.extract_device_fingerprint(request)

        if token.device_fingerprint != current_fingerprint:
            registrar_log(
                "comum.oauth",
                f"Device fingerprint inválido para {token.client.name}",
                nivel='ERROR'
            )
            return False

        return True

    @staticmethod
    def cleanup_expired_tokens(days_old=7):
        """
        Remove tokens expirados antigos

        Args:
            days_old (int): Dias de antiguidade para remoção

        Returns:
            int: Número de tokens removidos
        """
        from .models import OAuthToken

        cutoff_date = datetime.now() - timedelta(days=days_old)

        expired_tokens = OAuthToken.objects.filter(
            expires_at__lt=cutoff_date
        )

        count = expired_tokens.count()
        expired_tokens.delete()

        registrar_log("comum.oauth", f"Removidos {count} tokens expirados", nivel='INFO')
        return count
