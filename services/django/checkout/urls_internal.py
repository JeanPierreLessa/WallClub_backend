"""
URLs para APIs Internas de Checkout
Comunicação entre containers
"""
from django.urls import path
from . import views_internal_api

app_name = 'checkout_internal'

urlpatterns = [
    # Recorrências (8 endpoints)
    path('recorrencias/', views_internal_api.listar_recorrencias, name='listar_recorrencias'),
    path('recorrencias/criar/', views_internal_api.criar_recorrencia, name='criar_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/', views_internal_api.obter_recorrencia, name='obter_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/pausar/', views_internal_api.pausar_recorrencia, name='pausar_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/reativar/', views_internal_api.reativar_recorrencia, name='reativar_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/cobrar/', views_internal_api.cobrar_recorrencia, name='cobrar_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/atualizar/', views_internal_api.atualizar_recorrencia, name='atualizar_recorrencia'),
    path('recorrencias/<int:recorrencia_id>/deletar/', views_internal_api.deletar_recorrencia, name='deletar_recorrencia'),
    
    # Clientes (4 endpoints - TODOS POST)
    path('clientes/listar/', views_internal_api.listar_clientes, name='listar_clientes'),
    path('clientes/criar/', views_internal_api.criar_cliente, name='criar_cliente'),
    path('clientes/obter/', views_internal_api.obter_cliente, name='obter_cliente'),
    path('clientes/atualizar/', views_internal_api.atualizar_cliente, name='atualizar_cliente'),
    
    # Links/Tokens (4 endpoints - TODOS POST)
    path('tokens/listar/', views_internal_api.listar_tokens, name='listar_tokens'),
    path('tokens/criar/', views_internal_api.criar_token, name='criar_token'),
    path('tokens/validar/', views_internal_api.validar_token, name='validar_token'),
    path('tokens/obter/', views_internal_api.obter_token, name='obter_token'),
]
