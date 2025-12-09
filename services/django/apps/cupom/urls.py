"""
URLs para APIs REST de cupons
"""
from django.urls import path
from .api_views import cupons_ativos, validar_cupom, validar_cupom_checkout, verificar_cupons_disponiveis

app_name = 'cupom'

urlpatterns = [
    path('ativos/', cupons_ativos, name='cupons_ativos'),
    path('validar/', validar_cupom_checkout, name='cupom_validar_checkout'),  # Checkout (sem auth)
    path('validar-pos/', validar_cupom, name='cupom_validar'),  # POS (com OAuth)
    path('verificar_disponiveis/', verificar_cupons_disponiveis, name='verificar_disponiveis'),
]
