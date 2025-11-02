"""
Configuração do app OAuth para Django
"""
from django.apps import AppConfig


class OAuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallclub_core.oauth'
    verbose_name = 'OAuth 2.0'
