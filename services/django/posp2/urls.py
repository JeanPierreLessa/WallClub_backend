"""
URLs para o app POSP2
Endpoints consolidados usando views.py
"""

from django.urls import path
from . import views

app_name = 'posp2'

urlpatterns = [
    # APIs POSP2
    path('valida_versao_terminal/', views.validar_versao_terminal, name='valida_versao_terminal'),
    path('simula_parcelas/', views.simular_parcelas, name='simula_parcelas'),
    path('calcula_desconto_parcela/', views.calcular_desconto_parcela, name='calcula_desconto_parcela'),
    path('valida_cpf/', views.valida_cpf, name='valida_cpf'),
    path('logo_pos/', views.obter_logo_pos, name='logo_pos'),
    path('listar_operadores/', views.listar_operadores_pos, name='listar_operadores'),
    path('atualiza_celular_envia_msg_app/', views.atualiza_celular_envia_msg_app, name='atualiza_celular_envia_msg_app'),
    path('transaction_sync_service/', views.TransactionSyncView.as_view(), name='transaction_sync_service'),
    path('trdata/', views.processar_dados_transacao, name='trdata'),
    
    # Uso de Saldo no POS
    path('consultar_saldo/', views.consultar_saldo, name='consultar_saldo'),
    path('solicitar_autorizacao_saldo/', views.solicitar_autorizacao_saldo, name='solicitar_autorizacao_saldo'),
    path('verificar_autorizacao/', views.verificar_autorizacao, name='verificar_autorizacao'),
    path('debitar_saldo_transacao/', views.debitar_saldo_transacao, name='debitar_saldo_transacao'),
    path('finalizar_transacao_saldo/', views.finalizar_transacao_saldo, name='finalizar_transacao_saldo'),
    path('estornar_saldo_transacao/', views.estornar_saldo_transacao, name='estornar_saldo_transacao'),
]
