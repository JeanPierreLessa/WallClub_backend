"""
URLs para as APIs da conta digital.
"""
from django.urls import path
from . import views
# views_system desabilitado - migrado para OAuth 2.0

app_name = 'conta_digital'

urlpatterns = [
    # Endpoints principais (requerem JWT de cliente)
    path('saldo/', views.saldo, name='saldo'),
    path('creditar/', views.creditar, name='creditar'),
    path('debitar/', views.debitar, name='debitar'),
    path('extrato/', views.extrato, name='extrato'),
    
    # Controles de saldo
    path('bloquear_saldo/', views.bloquear_saldo, name='bloquear_saldo'),
    path('desbloquear_saldo/', views.desbloquear_saldo, name='desbloquear_saldo'),
    
    # Operações especiais
    path('estornar/', views.estornar, name='estornar'),
    
    # Endpoints de sistema DESABILITADOS - API Keys removidas
    # Para uso interno, chamar ContaDigitalService diretamente
    # path('system/creditar/', views_system.system_creditar, name='system_creditar'),
    # path('system/debitar/', views_system.system_debitar, name='system_debitar'),
    # path('system/bloquear-saldo/', views_system.system_bloquear_saldo, name='system_bloquear_saldo'),
    # path('system/desbloquear-saldo/', views_system.system_desbloquear_saldo, name='system_desbloquear_saldo'),
]
