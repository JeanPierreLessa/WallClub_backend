"""
Settings para Container APIs (Mobile + Checkout)
"""
from .base import *
import os

# Debug mode (ativar para desenvolvimento local)
DEBUG = os.getenv('DEBUG', 'False').lower() in ['true', '1', 'yes']

# ALLOWED_HOSTS - priorizar .env, depois fallback baseado em DEBUG
allowed_hosts_env = os.getenv('ALLOWED_HOSTS', '').strip()
if allowed_hosts_env:
    ALLOWED_HOSTS = [host.strip() for host in allowed_hosts_env.split(',') if host.strip()]
elif DEBUG:
    ALLOWED_HOSTS = ['*']
else:
    ALLOWED_HOSTS = [
        'api.wallclub.com.br',
        'checkout.wallclub.com.br',
        'wcapi.wallclub.com.br',
    ]

# Apps específicos do container APIs
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
    
    # Apps do container APIs
    'apps.cliente',
    'apps.transacoes',
    'apps.conta_digital',
    'apps.ofertas',
    'checkout',
    'checkout.link_pagamento_web',
    'checkout.link_recorrencia_web',
]

# URLs específicas
ROOT_URLCONF = 'wallclub.urls_apis'

# Middleware para APIs (sem middlewares de portais)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'wallclub_core.middleware.security_middleware.APISecurityMiddleware',
    'wallclub_core.middleware.security_validation.SecurityValidationMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
