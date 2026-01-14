"""
URLs para APIs de cadastro de estabelecimentos na Own Financial
"""

from django.urls import path
from adquirente_own.views_cadastro import (
    ConsultarCnaeView,
    ConsultarCestasView,
    ConsultarTarifasCestaView,
    CadastrarEstabelecimentoView,
    StatusCredenciamentoView
)

urlpatterns = [
    # Consultas auxiliares
    path('cnae/', ConsultarCnaeView.as_view(), name='own-consultar-cnae'),
    path('cestas/', ConsultarCestasView.as_view(), name='own-consultar-cestas'),
    path('cestas/<int:cesta_id>/tarifas/', ConsultarTarifasCestaView.as_view(), name='own-consultar-tarifas-cesta'),

    # Cadastro
    path('cadastrar-estabelecimento/', CadastrarEstabelecimentoView.as_view(), name='own-cadastrar-estabelecimento'),

    # Status
    path('status-credenciamento/<int:loja_id>/', StatusCredenciamentoView.as_view(), name='own-status-credenciamento'),
]
