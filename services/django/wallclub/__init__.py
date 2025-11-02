import pymysql

# Configurar PyMySQL como backend MySQL padrão
pymysql.install_as_MySQLdb()

# Celery app - Carregar ao iniciar Django
from .celery import app as celery_app

__all__ = ('celery_app',)