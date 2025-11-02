"""
Configurações de desenvolvimento do projeto WallClub Django.
"""

import os
from .base import *  # noqa

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-kwrso*hh_w)cei4h!#$f4=i9y&q6f(ysg(#(9s^(sp=2rptuuv')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True').lower() == 'true'

# Parse ALLOWED_HOSTS from environment
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1,192.168.0.251').split(',')

# CORS settings for development - configurável via .env
cors_origins = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000')
CORS_ALLOWED_ORIGINS = [origin.strip() for origin in cors_origins.split(',') if origin.strip()]

# Email backend: Comentado para usar AWS SES (configurado em base.py)
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'  # Descomente para testar sem enviar emails reais

# Customizações de logging para desenvolvimento
# A configuração base está em base.py, aqui apenas ajustamos o que é específico
LOGGING['handlers']['file']['level'] = 'DEBUG'  # Logs detalhados em arquivo
LOGGING['handlers']['console']['level'] = 'DEBUG'  # Logs detalhados no console
