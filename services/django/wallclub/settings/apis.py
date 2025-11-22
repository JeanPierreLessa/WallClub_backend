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
        'wccheckout.wallclub.com.br',
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
    'wallclub_core.estr_organizacional.apps.EstrOrganizacionalConfig',  # Necessário para model Loja (usado por checkout)
    
    # Apps do container APIs
    'apps.cliente',
    'apps.transacoes',
    'apps.conta_digital',
    'apps.ofertas',
    'checkout',
    'checkout.link_pagamento_web',
    'checkout.link_recorrencia_web',
    'parametros_wallclub',  # Necessário para CalculadoraDesconto (usado por checkout)
    'portais.controle_acesso',  # Necessário para PortalUsuario (usado por gestao_financeira)
    'gestao_financeira',  # Necessário para BaseTransacoesGestao (usado por cargas)
    'pinbank',
    'pinbank.cargas_pinbank',
    'adquirente_own',
    'adquirente_own.cargas_own',
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

# Templates - Sobrescrever context_processors do base.py
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Removidos context_processors de portais (não estão no INSTALLED_APPS)
            ],
        },
    },
]
