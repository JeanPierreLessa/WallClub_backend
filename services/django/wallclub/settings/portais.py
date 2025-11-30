"""
Settings para Container PORTAIS (Admin + Vendas + Lojista)
"""
from .base import *
import os

# Debug mode (ativar para desenvolvimento local)
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS - usar variável de ambiente do base.py

# URL base para APIs internas (container wallclub-apis)
INTERNAL_API_BASE_URL = 'http://wallclub-apis:8007'

# Apps específicos do container de portais (herda do base e adiciona apenas os específicos)
INSTALLED_APPS = INSTALLED_APPS + [
    'portais.admin',
    'portais.lojista',
    'portais.corporativo',
    'portais.controle_acesso',
    'portais.vendas',
    'gestao_financeira',
]

# URLs específicas
ROOT_URLCONF = 'wallclub.urls_portais'

# CSRF Trusted Origins - usar variável de ambiente do base.py
# Desenvolvimento: adicionar domínios .local
if DEBUG:
    CSRF_TRUSTED_ORIGINS.extend([
        'http://admin.wallclub.local',
        'http://vendas.wallclub.local',
        'http://lojista.wallclub.local',
    ])

# Session Cookie Secure (apenas HTTPS em produção)
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# Static files - Whitenoise
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'  # Comentado temporariamente

# Middleware - usar do base.py

# Whitenoise - Servir arquivos estáticos sem Nginx
WHITENOISE_USE_FINDERS = True
WHITENOISE_AUTOREFRESH = DEBUG
WHITENOISE_MAX_AGE = 31536000 if not DEBUG else 0  # 1 ano em produção
