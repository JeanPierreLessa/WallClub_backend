"""
Configurações base do projeto WallClub Django.
Contém configurações comuns a todos os ambientes.
Usa ConfigManager para gerenciar configurações híbridas (.env local / AWS Secrets produção).
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Application definition
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
    
    # Local apps
    'wallclub_core',
    'wallclub_core.oauth',
    'parametros_wallclub',
    'apps.cliente',
    'apps.transacoes',
    'apps.conta_digital',
    'apps.ofertas',
    'checkout',
    'checkout.link_pagamento_web',
    'checkout.link_recorrencia_web',
    'pinbank',
    'pinbank.cargas_pinbank',
    'posp2',
    'portais.admin',
    'portais.lojista',
    'portais.corporativo',
    'portais.controle_acesso',
    'portais.vendas',
    'sistema_bancario',
]

# Configurações de upload para formulários com muitos campos
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000  # Padrão é 1000, aumentado para suportar formulários de parâmetros com múltiplas configurações

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'portais.controle_acesso.middleware.PortalSessionMiddleware',  # Substituir SessionMiddleware padrão
    'corsheaders.middleware.CorsMiddleware',
    'wallclub_core.middleware.security_middleware.APISecurityMiddleware',  # Rate limiting e validação de APIs
    'wallclub_core.middleware.security_validation.SecurityValidationMiddleware',  # Validação de login com Risk Engine (Semana 23)
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'portais.controle_acesso.middleware.PortalAuthMiddleware',
    'wallclub_core.middleware.session_timeout.PortalSessionTimeoutMiddleware',
    'wallclub_core.middleware.session_timeout.PortalSessionSecurityMiddleware',
    # Middleware para marca do canal no portal lojista
    'portais.lojista.middleware.MarcaCanalMiddleware',
]

ROOT_URLCONF = 'wallclub.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'portais.lojista.context_processors.canal_context',
                'portais.controle_acesso.context_processors.usuario_canal_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'wallclub.wsgi.application'

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 10,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = False

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Diretórios onde o Django procura arquivos estáticos
STATICFILES_DIRS = [
    # BASE_DIR / 'staticfiles_custom',  # Removido - arquivos movidos para apps específicos
]

# Finders para arquivos estáticos
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# Media files
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
}

# CORS settings
CORS_ALLOW_CREDENTIALS = True

# Configurações híbridas usando ConfigManager
# Local: usa .env | Produção: usa AWS Secrets Manager + Parameter Store

# Django Secret Key
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-temp-key-for-testing-12345')

# SimpleJWT settings (após SECRET_KEY)
from datetime import timedelta

# SimpleJWT removido - usando JWT customizado

# Hosts permitidos
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Modo Debug
DEBUG = os.getenv('DEBUG', 'True').lower() in ['true', '1', 'yes']

# Configurações de Sessão dos Portais
SESSION_COOKIE_NAME = 'django_portal_adm_id'  # Nome customizado do cookie de sessão
SESSION_COOKIE_AGE = int(os.getenv('PORTAL_SESSION_TIMEOUT_MINUTES', 30)) * 60  # Converter minutos para segundos
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # Sessão expira ao fechar navegador
SESSION_SAVE_EVERY_REQUEST = True  # Renovar sessão a cada request (importante para timeout)
SESSION_COOKIE_SECURE = not DEBUG  # HTTPS apenas em produção
SESSION_COOKIE_HTTPONLY = True  # Prevenir acesso via JavaScript
SESSION_COOKIE_SAMESITE = 'Lax'  # Proteção CSRF

# URLs de autenticação
LOGIN_URL = '/portal_admin/'
LOGIN_REDIRECT_URL = '/portal_admin/'
LOGOUT_REDIRECT_URL = '/portal_admin/'

# Configuração de Cache
try:
    from .connection_pooling import CACHE_CONFIG, CACHE_FALLBACK
    # Tentar usar Redis primeiro, fallback para local se falhar
    try:
        import redis
        redis.Redis(host='wallclub-redis', port=6379, db=1).ping()  # Usa hostname ao invés de IP
        CACHES = CACHE_CONFIG
    except:
        CACHES = CACHE_FALLBACK
except ImportError:
    # Fallback básico se módulo não existir
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'wallclub-cache',
        }
    }

# Configuração de Rate Limiting para APIs
API_RATE_LIMITS = {
    # APIs de autenticação (mais restritivas)
    '/api/oauth/token/': {'requests': 10, 'window': 60},  # 10 req/min
    '/api/v1/cliente/login/': {'requests': 6, 'window': 60},  # 6 req/min (permite 5 falhas + 1 sucesso)
    
    # APIs de transação (moderadas)
    '/api/v1/transacao/': {'requests': 30, 'window': 60},  # 30 req/min
    '/api/v1/cliente/extrato/': {'requests': 20, 'window': 60},  # 20 req/min
    '/api/v1/cliente/comprovante/': {'requests': 20, 'window': 60},  # 20 req/min
    
    # POSP2 (crítico - mais permissivo)
    '/posp2/v1/checkout/': {'requests': 100, 'window': 60},  # 100 req/min
    '/posp2/v1/consulta/': {'requests': 50, 'window': 60},  # 50 req/min
    
    # Default para outros endpoints
    'default': {'requests': 60, 'window': 60},  # 60 req/min
}

# =====================================================
# Configurações de 2FA (Fase 4)
# =====================================================

# Habilitar 2FA por módulo (feature flags)
ENABLE_2FA_CHECKOUT = os.environ.get('ENABLE_2FA_CHECKOUT', 'False') == 'True'
ENABLE_2FA_APP = os.environ.get('ENABLE_2FA_APP', 'False') == 'True'
ENABLE_2FA_VENDAS = os.environ.get('ENABLE_2FA_VENDAS', 'False') == 'True'
ENABLE_2FA_RECORRENCIA = os.environ.get('ENABLE_2FA_RECORRENCIA', 'False') == 'True'

# Configurações de OTP
OTP_TAMANHO_CODIGO = 6
OTP_VALIDADE_MINUTOS = 5
OTP_MAX_TENTATIVAS = 3
OTP_MAX_CODIGOS_POR_HORA = 5
OTP_DURACAO_BLOQUEIO_MINUTOS = 60

# Limites de dispositivos confiáveis por tipo de usuário
DISPOSITIVO_LIMITE_CLIENTE = 3
DISPOSITIVO_LIMITE_VENDEDOR = 2
DISPOSITIVO_LIMITE_ADMIN = 10  # Sem limite prático
DISPOSITIVO_CONFIAVEL_DIAS = 30  # Dispositivo confiável por 30 dias

# Valores mínimos para revalidação 2FA em transações
VALOR_MINIMO_2FA_CHECKOUT = float(os.environ.get('VALOR_MINIMO_2FA_CHECKOUT', '500.00'))  # R$ 500
VALOR_MINIMO_2FA_VENDAS = float(os.environ.get('VALOR_MINIMO_2FA_VENDAS', '1000.00'))  # R$ 1.000
VALOR_MINIMO_2FA_RECORRENCIA = float(os.environ.get('VALOR_MINIMO_2FA_RECORRENCIA', '5000.00'))  # R$ 5.000

# Template WhatsApp para OTP (deve existir no WhatsApp Business)
WHATSAPP_TEMPLATE_OTP = 'codigo_otp_2fa'

# Configuração do banco de dados baseada no ambiente
def get_database_config():
    """
    Retorna configuração do banco usando ConfigManager.
    ConfigManager gerencia automaticamente desenvolvimento (.env) vs produção (AWS Secrets).
    """
    from wallclub_core.utilitarios.config_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_database_config()

DATABASES = {
    'default': get_database_config()
}

# Configuração do Pinbank usando ConfigManager
def get_pinbank_config():
    """
    Retorna configuração do Pinbank usando ConfigManager.
    ConfigManager gerencia automaticamente desenvolvimento (.env) vs produção (AWS Secrets).
    """
    from wallclub_core.utilitarios.config_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_pinbank_config()

# Carregar configurações do Pinbank
pinbank_config = get_pinbank_config()
PINBANK_URL = pinbank_config.get('url')
PINBANK_WALL_USERNAME = pinbank_config.get('username')
PINBANK_WALL_PASSWD = pinbank_config.get('password')
PINBANK_TIMEOUT = 30  # Timeout padrão

# Risk Engine - Antifraude (Fase 2 - Semana 14) - DEPRECADO, usar RISK_ENGINE_* abaixo

# Configurações de email adicionais
EMAIL_CHARSET = 'UTF-8'
EMAIL_SMTP_DEBUG = 0

# Configuração de Email - AWS SES
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('MAILSERVER_URL','email-smtp.us-east-1.amazonaws.com')
EMAIL_PORT = 587
EMAIL_USE_SSL = False
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('MAILSERVER_USERNAME', 'AKIAXWHDLWAXPATSXOK6')
EMAIL_HOST_PASSWORD = os.environ.get('MAILSERVER_PASSWD', 'BIlwP21H2UKtnQWSngltPT6jdpV3+D7MunK/RcxRD3S5')
DEFAULT_FROM_EMAIL = 'noreply@wallclub.com.br'
BASE_URL = 'https://apidj.wallclub.com.br'

# Configuração de Logging
import os
import sys

# Garantir que o diretório de logs existe
LOG_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Configuração base de logging (comum para todos os ambientes)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'debug.log'),
            'formatter': 'verbose',
            'mode': 'a',
            'encoding': 'utf-8',
        },
        'error_file': {
            'class': 'logging.FileHandler',
            'filename': os.path.join(LOG_DIR, 'error.log'),
            'formatter': 'verbose',
            'mode': 'a',
            'encoding': 'utf-8',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'django.request': {
            'handlers': ['console', 'file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': False,
        },
        'wallclub.security': {
            'handlers': ['console', 'file', 'error_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'wallclub.admin.seguranca': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Configurações de Integração com Risk Engine (Semana 23)
# URL e configurações gerais vêm do .env
RISK_ENGINE_URL = os.environ.get('RISK_ENGINE_URL', 'http://wallclub-riskengine:8004')
ANTIFRAUDE_ENABLED = os.environ.get('ANTIFRAUDE_ENABLED', 'False') == 'True'
ANTIFRAUDE_TIMEOUT = int(os.environ.get('ANTIFRAUDE_TIMEOUT', '5'))

# Credenciais OAuth vêm do AWS Secrets Manager (sensíveis)
# 3 pares de credenciais separadas por contexto
def get_riskengine_credentials():
    """Obtém credenciais OAuth do Risk Engine do AWS Secrets Manager"""
    from wallclub_core.utilitarios.config_manager import get_config_manager
    config_manager = get_config_manager()
    return config_manager.get_riskengine_credentials()

riskengine_creds = get_riskengine_credentials()

# Portal Admin (wallclub-django)
RISK_ENGINE_ADMIN_CLIENT_ID = riskengine_creds.get('admin_client_id', 'wallclub-django')
RISK_ENGINE_ADMIN_CLIENT_SECRET = riskengine_creds.get('admin_client_secret', '')

# POSP2 + Checkout (wallclub-pos-checkout)
RISK_ENGINE_POS_CLIENT_ID = riskengine_creds.get('pos_client_id', 'wallclub-pos-checkout')
RISK_ENGINE_POS_CLIENT_SECRET = riskengine_creds.get('pos_client_secret', '')

# Interno (wallclub_django_internal)
RISK_ENGINE_INTERNAL_CLIENT_ID = riskengine_creds.get('internal_client_id', 'wallclub_django_internal')
RISK_ENGINE_INTERNAL_CLIENT_SECRET = riskengine_creds.get('internal_client_secret', '')

# Configurações de Notificações de Segurança (Fase 4 - Semana 23)
SECURITY_NOTIFICATIONS_ENABLED = os.environ.get('SECURITY_NOTIFICATIONS_ENABLED', 'True') == 'True'
SECURITY_NOTIFICATIONS_PUSH = os.environ.get('SECURITY_NOTIFICATIONS_PUSH', 'True') == 'True'
SECURITY_NOTIFICATIONS_WHATSAPP = os.environ.get('SECURITY_NOTIFICATIONS_WHATSAPP', 'True') == 'True'
SECURITY_NOTIFICATIONS_EMAIL = os.environ.get('SECURITY_NOTIFICATIONS_EMAIL', 'True') == 'True'

# =====================================================
# Configurações do Celery (Fase 5 - Recorrências)
# =====================================================

# Broker: Redis
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://wallclub-redis:6379/0')
CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://wallclub-redis:6379/0')

# Serialização
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Timezone (mesmo do Django)
CELERY_TIMEZONE = 'America/Sao_Paulo'
CELERY_ENABLE_UTC = False

# Configurações de Tasks
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 300  # 5 minutos
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutos (aviso)

# Logs
CELERY_WORKER_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'
CELERY_WORKER_TASK_LOG_FORMAT = '[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s'

# Beat Schedule (definido em wallclub/celery.py)
