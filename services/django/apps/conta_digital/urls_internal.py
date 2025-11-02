"""
URLs para APIs Internas de Conta Digital
Comunicação entre containers
"""
from django.urls import path
from . import views_internal_api

app_name = 'conta_digital_internal'

urlpatterns = [
    path('consultar_saldo/', views_internal_api.consultar_saldo, name='consultar_saldo'),
    path('autorizar_uso/', views_internal_api.autorizar_uso, name='autorizar_uso'),
    path('debitar_saldo/', views_internal_api.debitar_saldo, name='debitar_saldo'),
    path('estornar_saldo/', views_internal_api.estornar_saldo, name='estornar_saldo'),
    path('calcular_maximo/', views_internal_api.calcular_maximo, name='calcular_maximo'),
]
