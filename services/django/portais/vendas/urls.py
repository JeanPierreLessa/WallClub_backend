"""
URLs do Portal de Vendas (Checkout)
"""
from django.urls import path
from . import views
from . import views_recorrencia

app_name = 'vendas'

urlpatterns = [
    # Autenticação
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Gestão de Clientes
    path('cliente/novo/', views.cliente_form, name='cliente_novo'),
    path('cliente/busca/', views.cliente_busca, name='cliente_busca'),
    path('cliente/<int:cliente_id>/editar/', views.cliente_editar, name='cliente_editar'),
    path('cliente/<int:cliente_id>/inativar/', views.cliente_inativar, name='cliente_inativar'),
    path('cliente/<int:cliente_id>/reativar/', views.cliente_reativar, name='cliente_reativar'),
    
    
    # Checkout Direto
    path('checkout/', views.checkout_view, name='checkout'),
    path('checkout/processar/', views.checkout_processar, name='checkout_processar'),
    path('checkout/resultado/<int:transacao_id>/', views.checkout_resultado, name='checkout_resultado'),
    
    # Buscar Pedidos
    path('pedidos/buscar/', views.buscar_pedido, name='buscar_pedido'),
    
    # AJAX
    path('ajax/buscar-cliente/', views.ajax_buscar_cliente, name='ajax_buscar_cliente'),
    path('ajax/calcular-parcelas/', views.ajax_calcular_parcelas, name='ajax_calcular_parcelas'),
    path('ajax/simular-parcelas/', views.ajax_simular_parcelas, name='ajax_simular_parcelas'),
    path('ajax/pesquisar-cpf/', views.ajax_pesquisar_cpf, name='ajax_pesquisar_cpf'),
    
    # Recorrencia (Fase 5 - Unificacao)
    path('recorrencia/agendar/', views_recorrencia.recorrencia_agendar, name='recorrencia_agendar'),
    path('recorrencia/lista/', views_recorrencia.recorrencia_listar, name='recorrencia_listar'),
    path('recorrencia/<int:recorrencia_id>/pausar/', views_recorrencia.recorrencia_pausar, name='recorrencia_pausar'),
    path('recorrencia/<int:recorrencia_id>/cancelar/', views_recorrencia.recorrencia_cancelar, name='recorrencia_cancelar'),
    path('recorrencia/<int:recorrencia_id>/reativar/', views_recorrencia.recorrencia_reativar, name='recorrencia_reativar'),
    path('recorrencia/<int:recorrencia_id>/detalhe/', views_recorrencia.recorrencia_detalhe, name='recorrencia_detalhe'),
    path('recorrencia/nao-cobrados/', views_recorrencia.recorrencia_relatorio_nao_cobrados, name='recorrencia_nao_cobrados'),
]
