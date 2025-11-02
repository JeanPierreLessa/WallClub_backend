from django.apps import AppConfig


class PortalAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portais.admin'
    label = 'portais_admin'  # Label único para evitar conflito
    verbose_name = 'Portal Administrativo'
