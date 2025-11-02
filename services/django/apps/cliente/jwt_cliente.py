"""
Autenticação JWT customizada EXCLUSIVA para apps de cliente (mobile/API)
Completamente independente do sistema de portais administrativos
"""
import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from datetime import datetime
from wallclub_core.utilitarios.log_control import registrar_log


class ClienteJWTAuthentication(authentication.BaseAuthentication):
    """
    Autenticação JWT customizada EXCLUSIVA para clientes mobile/API
    Não usa User do Django, apenas dados do Cliente
    """
    
    def authenticate(self, request):
        """
        Autentica requisição usando JWT customizado de cliente
        
        Returns:
            tuple: (user_obj, token) ou None se não autenticado
        """
        registrar_log('apps.cliente', "🔐 ClienteJWTAuthentication: Iniciando autenticação", nivel='DEBUG')
        
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        registrar_log('apps.cliente', f"🔐 Auth header: {auth_header}", nivel='DEBUG')
        
        if not auth_header or not auth_header.startswith('Bearer '):
            registrar_log('apps.cliente', "🔐 Sem token Bearer, retornando None", nivel='DEBUG')
            return None
            
        try:
            token = auth_header.split(' ')[1]
            registrar_log('apps.cliente', f"🔐 Token extraído: {token[:50]}...", nivel='DEBUG')
            
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            registrar_log('apps.cliente', f"🔐 Payload decodificado: {payload}", nivel='DEBUG')
            
            # Verificar se é access token
            if payload.get('token_type') != 'access':
                registrar_log('apps.cliente', f"🔐 Token type inválido: {payload.get('token_type')}", nivel='ERROR')
                raise exceptions.AuthenticationFailed('Token inválido')
            
            # Verificar expiração
            exp = payload.get('exp')
            if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
                registrar_log('apps.cliente', "🔐 Token expirado", nivel='ERROR')
                raise exceptions.AuthenticationFailed('Token expirado')
            
            # CRÍTICO: Validar contra tabela de auditoria
            jti = payload.get('jti')
            if jti:
                from .models import ClienteJWTToken
                jwt_record = ClienteJWTToken.validate_token(token, jti)
                
                if not jwt_record:
                    registrar_log('apps.cliente', f"🔐 Token revogado ou não encontrado na tabela (jti={jti})", nivel='ERROR')
                    raise exceptions.AuthenticationFailed('Token inválido ou revogado')
                
                # Registrar uso do token
                jwt_record.record_usage()
                registrar_log('apps.cliente', f"🔐 Token validado com sucesso (jti={jti})", nivel='DEBUG')
            else:
                # Token sem JTI - rejeitar por segurança
                registrar_log('apps.cliente', "🔐 Token sem JTI - rejeitado por segurança", nivel='ERROR')
                raise exceptions.AuthenticationFailed('Token inválido')
            
            # Criar objeto user-like com dados do cliente
            user_obj = ClienteUser(payload)
            registrar_log('apps.cliente', f"🔐 ClienteUser criado: {user_obj}", nivel='DEBUG')
            
            return (user_obj, token)
            
        except jwt.ExpiredSignatureError:
            registrar_log('apps.cliente', "🔐 JWT ExpiredSignatureError", nivel='ERROR')
            raise exceptions.AuthenticationFailed('Token expirado')
        except jwt.InvalidTokenError as e:
            registrar_log('apps.cliente', f"🔐 JWT InvalidTokenError: {str(e)}", nivel='ERROR')
            raise exceptions.AuthenticationFailed('Token inválido')
        except Exception as e:
            registrar_log('apps.cliente', f"🔐 Erro na autenticação JWT cliente: {str(e)}", nivel='ERROR')
            raise exceptions.AuthenticationFailed('Erro na autenticação')


class ClienteUser:
    """
    Objeto user-like para representar cliente autenticado
    EXCLUSIVO para apps de cliente - não confundir com User do Django
    """
    
    def __init__(self, payload):
        self.cliente_id = payload.get('cliente_id')
        self.cpf = payload.get('cpf')
        self.nome = payload.get('nome')
        self.canal_id = payload.get('canal_id')
        self.is_active = payload.get('is_active', True)
        self.is_authenticated = True
        self.is_anonymous = False
    
    @property
    def id(self):
        """Compatibilidade com código que usa request.user.id"""
        return self.cliente_id
    
    @property
    def pk(self):
        """Compatibilidade com Django"""
        return self.cliente_id
    
    def __str__(self):
        return f"Cliente {self.nome} ({self.cpf})"


# Importar validação do CORE para evitar dependência circular
from wallclub_core.oauth.jwt_utils import validate_cliente_jwt_token


def refresh_cliente_access_token(refresh_token):
    """
    Gera novo access token usando refresh token de cliente
    
    Args:
        refresh_token (str): Refresh token
        
    Returns:
        dict: Novo access token ou None se inválido
    """
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=['HS256'])
        
        # Verificar se é refresh token
        if payload.get('token_type') != 'refresh':
            return None
        
        # Verificar expiração
        exp = payload.get('exp')
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            return None
        
        # Validar token contra tabela de auditoria
        jti = payload.get('jti')
        if jti:
            from apps.cliente.models import ClienteJWTToken
            jwt_record = ClienteJWTToken.validate_token(refresh_token, jti)
            
            if not jwt_record:
                registrar_log('apps.cliente', 
                    f"Refresh token revogado ou não encontrado na tabela (jti={jti})", 
                    nivel='WARNING')
                return None
        
        # Buscar dados do cliente
        from apps.cliente.models import Cliente
        try:
            cliente = Cliente.objects.get(id=payload['cliente_id'])
            
            # Gerar novo access token (sem request pois é refresh)
            jwt_data = generate_cliente_jwt_token(cliente, request=None, is_refresh=True)
            
            if not jwt_data or not jwt_data.get('token'):
                registrar_log('apps.cliente', 
                    f"Erro ao gerar novo token no refresh para cliente={payload['cliente_id']}", 
                    nivel='ERROR')
                return None
            
            return {
                'token': jwt_data['token'],
                'expires_at': jwt_data['expires_at'].isoformat() if hasattr(jwt_data['expires_at'], 'isoformat') else jwt_data['expires_at']
            }
            
        except Cliente.DoesNotExist:
            return None
            
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def generate_auth_pending_token(cliente_id, cpf, canal_id):
    """
    Gera token temporário "auth_pending" válido por 2 minutos.
    Usado entre login e validação 2FA para evitar expor cliente_id.
    
    Args:
        cliente_id: ID do cliente
        cpf: CPF do cliente
        canal_id: ID do canal
        
    Returns:
        dict: {auth_token: str, expires_at: datetime}
    """
    try:
        import uuid
        from datetime import datetime, timedelta
        import time
        
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (2 * 60)  # 2 minutos
        
        payload = {
            'cliente_id': cliente_id,
            'cpf': cpf,
            'canal_id': canal_id,
            'iat': now_timestamp,
            'exp': exp_timestamp,
            'jti': str(uuid.uuid4()),
            'token_type': 'auth_pending'  # Token temporário
        }
        
        auth_token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')
        expires_at = datetime.utcfromtimestamp(exp_timestamp)
        
        registrar_log('apps.cliente', 
            f"Auth pending token gerado: cliente={cliente_id}, expira em 5min",
            nivel='INFO')
        
        return {
            'auth_token': auth_token,
            'expires_at': expires_at
        }
        
    except Exception as e:
        registrar_log('apps.cliente', 
            f"Erro ao gerar auth_pending token: {str(e)}", nivel='ERROR')
        return None


def validate_auth_pending_token(token):
    """
    Valida auth_pending token e extrai dados do cliente.
    
    Args:
        token: Auth pending token
        
    Returns:
        dict: Payload do token ou None se inválido
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        
        # Verificar tipo
        if payload.get('token_type') != 'auth_pending':
            registrar_log('apps.cliente', 
                f"Token type inválido: {payload.get('token_type')}", nivel='ERROR')
            return None
        
        # Verificar expiração
        exp = payload.get('exp')
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            registrar_log('apps.cliente', "Auth pending token expirado", nivel='ERROR')
            return None
        
        return payload
        
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        registrar_log('apps.cliente', 
            f"Erro ao validar auth_pending token: {str(e)}", nivel='ERROR')
        return None


def generate_cliente_jwt_token(cliente, request=None, is_refresh=False):
    """
    Gera token JWT customizado para o cliente com auditoria
    
    Args:
        cliente: Instância do modelo Cliente
        request: Request HTTP para metadados (opcional)
        is_refresh: Se True, gera apenas access token sem revogar tokens anteriores
        
    Returns:
        dict: Token JWT e dados de expiração
    """
    try:
        import uuid
        from datetime import datetime, timedelta
        import time
        
        # Usar timestamp atual diretamente (mais preciso)
        now_timestamp = int(time.time())
        exp_timestamp = now_timestamp + (1 * 24 * 60 * 60)  # 1 dia (segurança)
        refresh_exp_timestamp = now_timestamp + (30 * 24 * 60 * 60)  # 30 dias
        
        # Gerar JTIs únicos
        access_jti = str(uuid.uuid4())
        refresh_jti = str(uuid.uuid4())
        
        # Payload do access token
        access_payload = {
            'cliente_id': cliente.id,
            'cpf': cliente.cpf,
            'nome': cliente.nome,
            'canal_id': cliente.canal_id,
            'is_active': cliente.is_active,
            'iat': now_timestamp,
            'exp': exp_timestamp,
            'jti': access_jti,
            'token_type': 'access',
            'oauth_validated': True  # Indica que foi gerado via OAuth
        }
        
        # Payload do refresh token
        refresh_payload = {
            'cliente_id': cliente.id,
            'iat': now_timestamp,
            'exp': refresh_exp_timestamp,
            'jti': refresh_jti,
            'token_type': 'refresh'
        }
        
        # Gerar tokens usando PyJWT
        access_token = jwt.encode(access_payload, settings.SECRET_KEY, algorithm='HS256')
        refresh_token = jwt.encode(refresh_payload, settings.SECRET_KEY, algorithm='HS256')
        
        # Salvar tokens no banco para auditoria
        from .models import ClienteJWTToken
        
        expires_at = datetime.utcfromtimestamp(exp_timestamp)
        refresh_expires_at = datetime.utcfromtimestamp(refresh_exp_timestamp)
        
        # Extrair metadados do request
        ip_address = None
        user_agent = None
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # CRÍTICO: Revogar apenas access tokens anteriores (preservar refresh tokens)
        from .models import ClienteJWTToken
        
        if not is_refresh:
            # Login normal: revogar TODOS os tokens ativos
            tokens_revogados = ClienteJWTToken.objects.filter(
                cliente=cliente,
                is_active=True
            ).update(
                is_active=False,
                revoked_at=datetime.utcnow()
            )
            
            if tokens_revogados > 0:
                registrar_log('apps.cliente', 
                    f"🔒 {tokens_revogados} token(s) anterior(es) revogado(s) para cliente_id={cliente.id}")
        else:
            # Refresh: revogar apenas access tokens anteriores, manter refresh tokens
            tokens_revogados = ClienteJWTToken.objects.filter(
                cliente=cliente,
                is_active=True,
                token_type='access'
            ).update(
                is_active=False,
                revoked_at=datetime.utcnow()
            )
            
            if tokens_revogados > 0:
                registrar_log('apps.cliente', 
                    f"🔄 {tokens_revogados} access token(s) anterior(es) revogado(s) (refresh) para cliente_id={cliente.id}")
        
        # Criar registros de auditoria
        ClienteJWTToken.create_from_token(
            cliente=cliente,
            token=access_token,
            jti=access_jti,
            expires_at=expires_at,
            token_type='access',
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Só criar novo refresh token se não for refresh (evitar duplicação)
        if not is_refresh:
            ClienteJWTToken.create_from_token(
                cliente=cliente,
                token=refresh_token,
                jti=refresh_jti,
                expires_at=refresh_expires_at,
                token_type='refresh',
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        return {
            'token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at
        }
        
    except Exception as e:
        registrar_log('apps.cliente', f"Erro ao gerar JWT token cliente: {str(e)}", nivel='ERROR')
        return {
            'token': '',
            'refresh_token': '',
            'expires_at': datetime.utcnow()
        }
