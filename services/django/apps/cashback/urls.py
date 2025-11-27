"""
URLs para APIs de cashback
"""
from django.urls import path
from . import api_views

app_name = 'cashback'

urlpatterns = [
    path('simular/', api_views.simular_cashback, name='simular'),
    path('aplicar/', api_views.aplicar_cashback, name='aplicar'),
]
