"""
URLs para APIs REST de cupons
"""
from django.urls import path
from .api_views import cupons_ativos, validar_cupom

app_name = 'cupom'

urlpatterns = [
    path('ativos/', cupons_ativos, name='cupons_ativos'),
    path('validar/', validar_cupom, name='cupom_validar'),
]
