"""
URLs centralizadas de todos os apps.
"""
from django.urls import path, include
from . import views

app_name = 'apps'

urlpatterns = [
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Versão mínima dos apps mobile
    path('versao_minima/', views.versao_minima, name='versao_minima'),
    
    # Feature flags por versão
    path('feature_flag/', views.feature_flag, name='feature_flag'),
    
    # Apps centralizados
    path('auth/', include('apps.cliente.urls')),
    path('transacoes/', include('apps.transacoes.urls')),
    # path('carteira/', include('apps.carteira.urls')),  # Removido - usando conta_digital
    path('conta_digital/', include('apps.conta_digital.urls')),
]
