"""
URLs para API de gerenciamento de cartões tokenizados
"""
from django.urls import path
from . import api_cartoes

urlpatterns = [
    # Listar cartões de um cliente
    path('cartoes/<str:cpf>/', api_cartoes.listar_cartoes_cliente, name='listar_cartoes_cliente'),

    # Invalidar cartão
    path('cartoes/<int:cartao_id>/invalidar/', api_cartoes.invalidar_cartao, name='invalidar_cartao'),

    # Reativar cartão
    path('cartoes/<int:cartao_id>/reativar/', api_cartoes.reativar_cartao, name='reativar_cartao'),
]
