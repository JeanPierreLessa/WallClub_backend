"""
URLs para APIs de cadastro de estabelecimentos na Own Financial
"""

from django.urls import path
from adquirente_own import views_cadastro

urlpatterns = [
    # Consultas auxiliares
    path('cnae/', views_cadastro.consultar_cnae, name='own-consultar-cnae'),
    path('cestas/', views_cadastro.consultar_cestas, name='own-consultar-cestas'),
    path('cestas/<int:cesta_id>/tarifas/', views_cadastro.consultar_tarifas_cesta, name='own-consultar-tarifas-cesta'),
]
