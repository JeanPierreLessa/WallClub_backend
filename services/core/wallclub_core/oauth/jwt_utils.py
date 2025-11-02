"""
Utilitários genéricos para validação JWT.
Permite validação sem dependência de apps específicos.
"""
from typing import Dict, Any, Optional
from wallclub_core.utilitarios.log_control import registrar_log


def validate_jwt_token(token: str, cliente_model=None) -> Dict[str, Any]:
    """
    Valida token JWT genérico.
    
    Args:
        token: Token JWT a ser validado
        cliente_model: Model Cliente (opcional, para validação específica)
        
    Returns:
        dict: {'valido': bool, 'payload': dict, 'mensagem': str}
    """
    try:
        import jwt
        from django.conf import settings
        from datetime import datetime
        
        # Decodificar sem validar primeiro (para debug)
        try:
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
        except jwt.ExpiredSignatureError:
            return {
                'valido': False,
                'payload': None,
                'mensagem': 'Token expirado'
            }
        except jwt.InvalidTokenError as e:
            return {
                'valido': False,
                'payload': None,
                'mensagem': f'Token inválido: {str(e)}'
            }
        
        # Validar jti se model fornecido
        jti = payload.get('jti')
        if jti and cliente_model:
            # Import lazy para evitar dependência circular
            from apps.cliente.models import ClienteJWTToken
            jwt_record = ClienteJWTToken.validate_token(token, jti)
            
            if jwt_record:
                return {
                    'valido': True,
                    'payload': payload,
                    'jwt_record': jwt_record,
                    'mensagem': 'Token válido'
                }
            else:
                return {
                    'valido': False,
                    'payload': payload,
                    'mensagem': 'Token revogado ou expirado'
                }
        
        # Token válido (sem validação de jti)
        return {
            'valido': True,
            'payload': payload,
            'mensagem': 'Token válido'
        }
        
    except Exception as e:
        registrar_log('comum.oauth',
            f"Erro ao validar JWT: {str(e)}", nivel='ERROR')
        return {
            'valido': False,
            'payload': None,
            'mensagem': f'Erro interno: {str(e)}'
        }


def validate_cliente_jwt_token(token: str) -> Dict[str, Any]:
    """
    Wrapper para validação de JWT de cliente.
    Mantém retrocompatibilidade.
    """
    from apps.cliente.models import Cliente
    return validate_jwt_token(token, cliente_model=Cliente)


def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica token JWT sem validar assinatura (apenas para debug/análise).
    
    Args:
        token: Token JWT
        
    Returns:
        dict: Payload decodificado ou None se inválido
    """
    try:
        import jwt
        payload = jwt.decode(
            token,
            options={"verify_signature": False}
        )
        return payload
    except Exception:
        return None


def extract_token_from_header(auth_header: str) -> Optional[str]:
    """
    Extrai token JWT do header Authorization.
    
    Args:
        auth_header: Header 'Authorization: Bearer <token>'
        
    Returns:
        str: Token extraído ou None
    """
    if not auth_header:
        return None
    
    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != 'bearer':
        return None
    
    return parts[1]
