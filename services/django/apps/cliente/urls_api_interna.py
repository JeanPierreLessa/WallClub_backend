"""
URLs de API Interna para comunicação entre containers
"""
from django.urls import path
from . import views_api_interna

urlpatterns = [
    path('consultar_por_cpf/', views_api_interna.consultar_por_cpf, name='cliente_consultar_por_cpf'),
    path('cadastrar/', views_api_interna.cadastrar, name='cliente_cadastrar'),
    path('obter_cliente_id/', views_api_interna.obter_cliente_id, name='cliente_obter_id'),
    path('atualizar_celular/', views_api_interna.atualizar_celular, name='cliente_atualizar_celular'),
    path('obter_dados_cliente/', views_api_interna.obter_dados_cliente, name='cliente_obter_dados'),
    path('verificar_cadastro/', views_api_interna.verificar_cadastro, name='cliente_verificar_cadastro'),
]
