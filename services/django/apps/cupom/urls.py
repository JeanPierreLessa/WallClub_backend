"""
URLs para APIs REST de cupons
"""
from django.urls import path
from .api_views import CuponsAtivosAPIView, CupomValidarAPIView

app_name = 'cupom'

urlpatterns = [
    path('ativos/', CuponsAtivosAPIView.as_view(), name='cupons_ativos'),
    path('validar/', CupomValidarAPIView.as_view(), name='cupom_validar'),
]
