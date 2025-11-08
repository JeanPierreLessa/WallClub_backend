"""
Settings para Celery Worker Unificado
Tem acesso a TODOS os apps para executar qualquer task
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
    ALLOWED_HOSTS = ['*']  # Worker não recebe requests HTTP

# INSTALLED_APPS - TODOS os apps para descobrir todas as tasks
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
    'wallclub_core.estr_organizacional',  # Necessário para model Loja
    
    # TODOS os apps do projeto (para descobrir todas as tasks)
    'apps.cliente',
    'apps.conta_digital',
    'apps.ofertas',
    'apps.transacoes',
    'checkout',
    'checkout.link_pagamento_web',
    'checkout.link_recorrencia_web',
    'pinbank',
    'pinbank.cargas_pinbank',
    'parametros_wallclub',
    'posp2',
    'portais.admin',
    'portais.lojista',
    'portais.corporativo',
    'portais.controle_acesso',
    'portais.vendas',
    'sistema_bancario',
]

# URLs não são necessárias para worker (não recebe HTTP)
ROOT_URLCONF = 'wallclub.urls'

# Middleware mínimo (worker não processa requests HTTP)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
