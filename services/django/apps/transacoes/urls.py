"""
URLs para o módulo de transações
"""
from django.urls import path
from . import views

app_name = 'transacoes'

urlpatterns = [
    # Endpoint de saldo
    path('saldo/', views.saldo, name='transacoes_saldo'),
    
    # Endpoint de extrato - MIGRADO DO PHP
    path('extrato/', views.extrato, name='transacoes_extrato'),
    
    # Endpoint de comprovante - FUNCIONANDO!
    path('comprovante/', views.comprovante, name='transacoes_comprovante'),
]
