"""
URLs para APIs REST de cupons
"""
from django.urls import path
from .api_views import cupons_ativos, CupomValidarAPIView

app_name = 'cupom'

urlpatterns = [
    path('ativos/', cupons_ativos, name='cupons_ativos'),
    path('validar/', CupomValidarAPIView.as_view(), name='cupom_validar'),
]
