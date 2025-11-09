"""
Settings para Container POS (Terminal POS)
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
        'wcapi.wallclub.com.br',
    ]

# Apps específicos do container POS
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
    
    # Apps do container POS
    'posp2',
    'apps.cliente',  # Necessário para models de Cliente (usado por conta_digital)
    'apps.conta_digital',  # Necessário para verificar status de autorizações
    'pinbank',
    'pinbank.cargas_pinbank',
    'parametros_wallclub',
]

# URLs específicas
ROOT_URLCONF = 'wallclub.urls_pos'

# Middleware mínimo (sem middlewares de portais)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'wallclub_core.middleware.security_middleware.APISecurityMiddleware',
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
