"""
Decorators para autenticação OAuth do checkout.
Sistema migrado para OAuth 2.0 - API Keys removidas.
"""
from functools import wraps
from wallclub_core.oauth.decorators import require_oauth_checkout
from wallclub_core.utilitarios.log_control import registrar_log


def require_oauth_checkout_api_key(view_func):
    """
    Decorator que exige OAuth válida para checkout.
    """
    return require_oauth_checkout()(view_func)


def log_checkout_access(view_func):
    """
    Decorator para registrar tentativas de acesso ao checkout.
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        registrar_log("checkout.link_pagamento_web", f"Acesso à página de checkout - IP: {request.META.get('REMOTE_ADDR')}")
        return view_func(request, *args, **kwargs)
    
    return wrapper


# require_oauth_checkout importado de comum.oauth.decorators
