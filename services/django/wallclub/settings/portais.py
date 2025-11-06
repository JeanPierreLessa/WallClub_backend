"""
Settings para Container PORTAIS (Admin + Vendas + Lojista)
"""
from .base import *
import os

# Debug mode (ativar para desenvolvimento local)
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS - priorizar .env, depois fallback baseado em DEBUG
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '').strip()
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [
        'admin.wallclub.com.br',
        'vendas.wallclub.com.br',
        'lojista.wallclub.com.br',
        'wcadmin.wallclub.com.br',
        'wclojista.wallclub.com.br',
        'wcvendas.wallclub.com.br',
    ]

# URL base para APIs internas (mesmo container)
INTERNAL_API_BASE_URL = 'http://127.0.0.1:8000'

# Apps específicos do container de portais
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'corsheaders',
    
    # Core
    'wallclub_core',
    'wallclub_core.oauth',
    
    # Apps do container portais
    'portais.admin',
    'portais.lojista',
    'portais.corporativo',
    'portais.controle_acesso',
    'portais.vendas',
    'sistema_bancario',
    
    # Dependências (portais usa checkout, ofertas, parametros)
    'checkout',
    'checkout.link_pagamento_web',
    'checkout.link_recorrencia_web',
    'apps.cliente',
    'apps.ofertas',
    'parametros_wallclub',
]

# URLs específicas
ROOT_URLCONF = 'wallclub.urls_portais'

# Middleware específico (manter middlewares de portais)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'wallclub.middleware.subdomain_router.SubdomainRouterMiddleware',  # Roteamento por subdomínio
    'portais.controle_acesso.middleware.PortalSessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'portais.controle_acesso.middleware.PortalAuthMiddleware',
    'wallclub_core.middleware.session_timeout.PortalSessionTimeoutMiddleware',
    'wallclub_core.middleware.session_timeout.PortalSessionSecurityMiddleware',
    'portais.lojista.middleware.MarcaCanalMiddleware',
]
