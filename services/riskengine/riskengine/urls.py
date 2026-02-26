"""
URLs do WallClub Risk Engine
"""
from django.contrib import admin
from django.urls import path, include
from monitoring_metrics import metrics_view

urlpatterns = [
    # Métricas Prometheus
    path('metrics', metrics_view, name='prometheus-metrics'),

    # Admin e APIs
    path('admin/', admin.site.urls),
    path('api/antifraude/', include('antifraude.urls')),
]
