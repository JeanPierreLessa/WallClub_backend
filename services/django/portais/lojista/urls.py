from django.urls import path
from . import views
from .views_vendas import LojistaVendasView, LojistaVendasExportView
from .views_recebimentos import (
    LojistaRecebimentosView, 
    LojistaRecebimentosExportView, 
    LojistaRecebimentosDetalhesView,
    LojistaRecebimentosDetalhesTransacoesExportView,
    LojistaRecebimentosDetalhesLancamentosExportView
)
from .views_cancelamentos import LojistaCancelamentosView, LojistaCancelamentosExportView
from .views_conciliacao import LojistaConciliacaoView, LojistaConciliacaoExportView
from .views_terminais import LojistaTerminaisView
from .views_ofertas import (
    OfertasListView,
    OfertasCreateView,
    OfertasEditView,
    OfertasDispararView,
    OfertasHistoricoView
)
# from .views_relatorios import ()

app_name = 'lojista'

urlpatterns = [
    # Autenticação
    path('', views.LojistaLoginView.as_view(), name='login'),
    path('logout/', views.LojistaLogoutView.as_view(), name='logout'),
    path('primeiro_acesso/<str:token>/', views.LojistaPrimeiroAcessoView.as_view(), name='primeiro_acesso'),
    
    # Dashboard e Home
    path('home/', views.LojistaHomeView.as_view(), name='home'),
    
    # Vendas
    path('vendas/', LojistaVendasView.as_view(), name='vendas'),
    path('vendas/ajax/', LojistaVendasView.as_view(), name='vendas_ajax'),
    path('vendas/export/', LojistaVendasExportView.as_view(), name='vendas_export'),
    
    # Cancelamentos
    path('cancelamentos/', LojistaCancelamentosView.as_view(), name='cancelamentos'),
    path('cancelamentos/export/', LojistaCancelamentosExportView.as_view(), name='cancelamentos_export'),
    
    # Recebimentos
    path('recebimentos/', LojistaRecebimentosView.as_view(), name='recebimentos'),
    path('recebimentos/detalhes/', LojistaRecebimentosDetalhesView.as_view(), name='recebimentos_detalhes'),
    path('recebimentos/export/', LojistaRecebimentosExportView.as_view(), name='recebimentos_export'),
    path('recebimentos/detalhes/transacoes/export/', LojistaRecebimentosDetalhesTransacoesExportView.as_view(), name='recebimentos_detalhes_transacoes_export'),
    path('recebimentos/detalhes/lancamentos/export/', LojistaRecebimentosDetalhesLancamentosExportView.as_view(), name='recebimentos_detalhes_lancamentos_export'),
    
    # Relatórios
    path('conciliacao/', LojistaConciliacaoView.as_view(), name='conciliacao'),
    path('conciliacao/export/', LojistaConciliacaoExportView.as_view(), name='conciliacao_export'),
    
    # Configurações
    path('terminais/', LojistaTerminaisView.as_view(), name='terminais'),
    path('perfil/', views.LojistaPerfilView.as_view(), name='perfil'),
    path('aceite/', views.LojistaAceiteView.as_view(), name='aceite'),
    path('processar_aceite/', views.LojistaProcessarAceiteView.as_view(), name='processar_aceite'),
    path('trocar_senha/', views.LojistaTrocarSenhaView.as_view(), name='trocar_senha'),
    path('confirmar_troca_senha/', views.LojistaConfirmarTrocaSenhaView.as_view(), name='confirmar_troca_senha'),
    path('validar_usuario/', views.LojistaValidarUsuarioView.as_view(), name='validar_usuario'),
    
    # Ofertas
    path('ofertas/', OfertasListView.as_view(), name='ofertas_list'),
    path('ofertas/criar/', OfertasCreateView.as_view(), name='ofertas_create'),
    path('ofertas/<int:oferta_id>/editar/', OfertasEditView.as_view(), name='ofertas_edit'),
    path('ofertas/<int:oferta_id>/disparar/', OfertasDispararView.as_view(), name='ofertas_disparar'),
    path('ofertas/<int:oferta_id>/historico/', OfertasHistoricoView.as_view(), name='ofertas_historico'),
]
