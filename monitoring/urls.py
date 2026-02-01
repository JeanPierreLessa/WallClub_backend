"""
URLs para endpoints de monitoramento e health checks
"""
from django.urls import path
from monitoring import health_checks

urlpatterns = [
    path('health/', health_checks.health_check, name='health'),
    path('health/live/', health_checks.health_live, name='health_live'),
    path('health/ready/', health_checks.health_ready, name='health_ready'),
    path('health/startup/', health_checks.health_startup, name='health_startup'),
]
