from django.urls import path
from . import views, views_usuarios, views_terminais, views_parametros, views_hierarquia, views_pagamentos, views_transacoes, views_importacao, views_rpr, views_ofertas, views_grupos_segmentacao, views_antifraude, views_dispositivos, views_seguranca, views_perfil, views_celery

app_name = 'portais_admin'

urlpatterns = [
    # Autenticação
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Dashboard
    path('home/', views.dashboard, name='dashboard'),
    
    # Perfil e Troca de Senha
    path('perfil/', views_perfil.perfil_view, name='perfil'),
    path('perfil/trocar-senha/', views_perfil.AdminTrocarSenhaView.as_view(), name='trocar_senha'),
    path('perfil/confirmar-troca-senha/', views_perfil.AdminConfirmarTrocaSenhaView.as_view(), name='confirmar_troca_senha'),
    
    # Usuários (REFATORADO - usando views_usuarios.py)
    path('usuarios/', views_usuarios.usuarios_list, name='usuarios_list'),
    path('usuarios/novo/', views_usuarios.usuario_form, name='usuario_novo'),
    path('usuarios/<int:pk>/editar/', views_usuarios.usuario_form, name='usuario_editar'),
    path('usuarios/<int:pk>/deletar/', views_usuarios.usuario_delete, name='usuario_deletar'),
    path('usuarios/<int:pk>/portais/', views.usuario_portais_ajax, name='usuario_portais_ajax'),  # Mantido views.py
    
    # Ofertas
    path('ofertas/', views_ofertas.ofertas_list, name='ofertas_list'),
    path('ofertas/criar/', views_ofertas.ofertas_create, name='ofertas_create'),
    path('ofertas/<int:oferta_id>/editar/', views_ofertas.ofertas_edit, name='ofertas_edit'),
    path('ofertas/<int:oferta_id>/disparar/', views_ofertas.ofertas_disparar, name='ofertas_disparar'),
    path('ofertas/<int:oferta_id>/historico/', views_ofertas.ofertas_historico, name='ofertas_historico'),
    
    # Grupos de Segmentação
    path('grupos-segmentacao/', views_grupos_segmentacao.grupos_list, name='grupos_list'),
    path('grupos-segmentacao/criar/', views_grupos_segmentacao.grupos_create, name='grupos_create'),
    path('grupos-segmentacao/<int:grupo_id>/editar/', views_grupos_segmentacao.grupos_edit, name='grupos_edit'),
    path('grupos-segmentacao/<int:grupo_id>/clientes/', views_grupos_segmentacao.grupos_clientes, name='grupos_clientes'),
    path('grupos-segmentacao/<int:grupo_id>/adicionar-cliente/', views_grupos_segmentacao.grupos_adicionar_cliente, name='grupos_adicionar_cliente'),
    path('grupos-segmentacao/<int:grupo_id>/remover-cliente/<int:cliente_id>/', views_grupos_segmentacao.grupos_remover_cliente, name='grupos_remover_cliente'),
    
    # Autenticação de usuários (REFATORADO - usando views_usuarios.py)
    path('primeiro_acesso/<str:token>/', views_usuarios.primeiro_acesso, name='primeiro_acesso'),
    path('reset-senha/<str:token>/', views.reset_senha_view, name='reset_senha'),  # Mantido views.py
    
    # Parâmetros
    path('parametros/', views_parametros.parametros_list, name='parametros_list'),
    path('parametros/<int:loja_id>/download-csv/', views_parametros.parametros_download_csv, name='parametros_download_csv'),
    path('parametros/ajax/plano/<int:plano_id>/', views_parametros.parametros_ajax_plano_info, name='parametros_ajax_plano_info'),
    path('parametros/importar/', views_importacao.importacao_parametros, name='importacao_parametros'),
    path('parametros/processar-csv/', views_importacao.processar_importacao_csv, name='processar_importacao_csv'),
    path('parametros/template/', views_importacao.download_template_csv, name='parametros_template'),
    
    # Pagamentos
    path('pagamentos/', views_pagamentos.pagamentos_list, name='pagamentos_list'),
    path('pagamentos/novo/', views_pagamentos.pagamentos_create, name='pagamentos_create'),
    path('pagamentos/<int:pagamento_id>/editar/', views_pagamentos.pagamentos_edit, name='pagamentos_edit'),
    path('pagamentos/<int:pagamento_id>/excluir/', views_pagamentos.pagamentos_delete, name='pagamentos_delete'),
    path('pagamentos/ajax/check-nsu/', views_pagamentos.pagamentos_ajax_check_nsu, name='pagamentos_ajax_check_nsu'),
    path('pagamentos/bulk-create/', views_pagamentos.pagamentos_bulk_create, name='pagamentos_bulk_create'),
    path('pagamentos/upload-csv/', views_pagamentos.pagamentos_upload_csv, name='pagamentos_upload_csv'),
    
    # Relatórios
    path('rpr/', views_rpr.relatorio_producao_receita, name='relatorio_producao_receita'),
    path('rpr/tabela/', views_rpr.tabela_rpr_ajax, name='tabela_rpr_ajax'),
    path('rpr/export/excel/', views_rpr.exportar_rpr_excel, name='exportar_rpr_excel'),
    path('rpr/export/csv/', views_rpr.exportar_rpr_csv, name='exportar_rpr_csv'),
    
    # Gestão Financeira
    path('base_transacoes_gestao/', views_transacoes.base_transacoes_gestao, name='base_transacoes_gestao'),
    path('base_transacoes_gestao/export/excel/', views_transacoes.exportar_transacoes_excel, name='exportar_transacoes_excel'),
    path('base_transacoes_gestao/export/csv/', views_transacoes.exportar_transacoes_csv, name='exportar_transacoes_csv'),
    
    # Hierarquia Organizacional
    path('hierarquia/', views_hierarquia.hierarquia_geral, name='hierarquia_geral'),
    path('hierarquia/canal/<int:canal_id>/', views_hierarquia.canal_detail, name='canal_detail'),
    path('hierarquia/canal/<int:canal_id>/comissao/', views_hierarquia.canal_edit_comissao, name='canal_edit_comissao'),
    path('hierarquia/regional/<int:regional_id>/', views_hierarquia.regional_detail, name='regional_detail'),
    path('hierarquia/vendedor/<int:vendedor_id>/', views_hierarquia.vendedor_detail, name='vendedor_detail'),
    path('hierarquia/grupo/<int:grupo_id>/', views_hierarquia.grupo_detail, name='grupo_detail'),
    path('hierarquia/loja/<int:loja_id>/', views_hierarquia.loja_detail, name='loja_detail'),
    
    # Criação de estruturas hierárquicas
    path('hierarquia/canal/novo/', views_hierarquia.canal_create, name='canal_create'),
    path('hierarquia/regional/novo/', views_hierarquia.regional_create, name='regional_create'),
    path('hierarquia/vendedor/novo/', views_hierarquia.vendedor_create, name='vendedor_create'),
    path('hierarquia/grupo/novo/', views_hierarquia.grupo_create, name='grupo_create'),
    path('hierarquia/loja/novo/', views_hierarquia.loja_create, name='loja_create'),
    path('hierarquia/loja/<int:loja_id>/editar/', views_hierarquia.loja_edit, name='loja_edit'),
    
    # Terminais (REFATORADO - usando views_terminais.py)
    path('terminais/', views_terminais.terminais_list, name='terminais_list'),
    path('terminais/novo/', views_terminais.terminal_novo, name='terminal_novo'),
    path('terminais/<int:pk>/deletar/', views_terminais.terminal_delete, name='terminal_delete'),
    
    # Lançamentos Manuais
    path('lancamentos-manuais/', views_pagamentos.lancamentos_manuais_list, name='lancamentos_manuais_list'),
    path('lancamentos-manuais/novo/', views_pagamentos.lancamento_manual_form, name='lancamento_manual_form'),
    path('lancamentos-manuais/criar/', views_pagamentos.lancamento_manual_create, name='lancamento_manual_create'),
    path('lancamentos-manuais/<int:lancamento_id>/atualizar/', views_pagamentos.lancamento_manual_update, name='lancamento_manual_update'),
    path('lancamentos-manuais/<int:lancamento_id>/cancelar/', views_pagamentos.lancamento_manual_cancel, name='lancamento_manual_cancel'),
    path('lancamentos-manuais/<int:lancamento_id>/processar/', views_pagamentos.lancamento_manual_process, name='lancamento_manual_process'),
    path('lancamentos-manuais/<int:lancamento_id>/', views_pagamentos.lancamento_manual_detail, name='lancamento_manual_detail'),
    
    # AJAX endpoints para referências dinâmicas
    path('ajax_lojas/', views.ajax_lojas, name='ajax_lojas'),
    path('ajax_grupos_economicos/', views.ajax_grupos_economicos, name='ajax_grupos_economicos'),
    path('ajax_canais/', views.ajax_canais, name='ajax_canais'),
    path('ajax_regionais/', views.ajax_regionais, name='ajax_regionais'),
    path('ajax_vendedores/', views.ajax_vendedores, name='ajax_vendedores'),
    
    # Antifraude
    path('antifraude/', views_antifraude.antifraude_dashboard, name='antifraude_dashboard'),
    path('antifraude/pendentes/', views_antifraude.antifraude_pendentes, name='antifraude_pendentes'),
    path('antifraude/historico/', views_antifraude.antifraude_historico, name='antifraude_historico'),
    path('antifraude/aprovar/', views_antifraude.antifraude_aprovar, name='antifraude_aprovar'),
    path('antifraude/reprovar/', views_antifraude.antifraude_reprovar, name='antifraude_reprovar'),
    
    # Dispositivos Confiáveis
    path('dispositivos/', views_dispositivos.listar_dispositivos, name='dispositivos_list'),
    path('dispositivos/dashboard/', views_dispositivos.dashboard_dispositivos, name='dispositivos_dashboard'),
    path('dispositivos/usuario/', views_dispositivos.buscar_dispositivos_usuario, name='dispositivos_usuario'),
    path('dispositivos/revogar/', views_dispositivos.revogar_dispositivo, name='dispositivos_revogar'),
    path('dispositivos/revogar-todos/', views_dispositivos.revogar_todos_dispositivos_usuario, name='dispositivos_revogar_todos'),
    
    # Segurança - Atividades Suspeitas e Bloqueios (Semana 23)
    path('seguranca/atividades/', views_seguranca.atividades_suspeitas, name='atividades_suspeitas'),
    path('seguranca/atividades/<int:atividade_id>/investigar/', views_seguranca.investigar_atividade, name='investigar_atividade'),
    path('seguranca/bloqueios/', views_seguranca.bloqueios_seguranca, name='bloqueios_seguranca'),
    path('seguranca/bloqueios/criar/', views_seguranca.criar_bloqueio, name='criar_bloqueio'),
    
    # Monitoramento Celery
    path('celery/', views_celery.celery_dashboard, name='celery_dashboard'),
    path('celery/history/', views_celery.celery_task_history, name='celery_task_history'),
    path('celery/task/<str:task_id>/', views_celery.celery_task_detail, name='celery_task_detail'),
]
