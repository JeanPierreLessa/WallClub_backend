"""
Configuração do app comum.
"""
from django.apps import AppConfig


class ComumConfig(AppConfig):
    """Configuração do app comum"""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'wallclub_core'
    verbose_name = 'WallClub Core'
