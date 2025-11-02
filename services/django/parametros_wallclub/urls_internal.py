"""
URLs para APIs Internas de Parâmetros WallClub
Comunicação entre containers
"""
from django.urls import path
from . import views_internal_api

app_name = 'parametros_internal'

urlpatterns = [
    # Configurações
    path('configuracoes/loja/', views_internal_api.buscar_configuracoes_loja, name='buscar_configuracoes_loja'),
    path('configuracoes/contar/', views_internal_api.contar_configuracoes_loja, name='contar_configuracoes_loja'),
    path('configuracoes/ultima/', views_internal_api.obter_ultima_configuracao, name='obter_ultima_configuracao'),
    
    # Loja/Modalidades
    path('loja/modalidades/', views_internal_api.verificar_modalidades_loja, name='verificar_modalidades_loja'),
    
    # Planos
    path('planos/', views_internal_api.listar_planos, name='listar_planos'),
    
    # Importações
    path('importacoes/', views_internal_api.listar_importacoes, name='listar_importacoes'),
    path('importacoes/<int:importacao_id>/', views_internal_api.obter_importacao, name='obter_importacao'),
]
