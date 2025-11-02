"""
Configurações do projeto WallClub Django.
Por padrão, carrega as configurações de desenvolvimento.
Para usar as configurações de produção, defina a variável de ambiente:
DJANGO_SETTINGS_MODULE=wallclub.settings.production
"""

from .development import *  # noqa
