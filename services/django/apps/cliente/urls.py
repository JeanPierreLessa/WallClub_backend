"""
URLs para o módulo de cliente
"""
from django.urls import path
from . import (
    views, views_saldo, views_2fa_login, views_senha,
    views_dispositivos, views_revalidacao, views_refresh_jwt,
    views_cadastro, views_reset_senha, views_autenticacao_analise
)

app_name = 'cliente'

urlpatterns = [
    # Autenticação
    path('login/', views.cliente_login, name='cliente_login'),  # API Key + CPF + SENHA → auth_token
    path('refresh/', views_refresh_jwt.refresh_jwt_token, name='refresh_jwt'),  # API Key + Refresh Token

    # Cadastro Completo no App
    path('cadastro/', views.cliente_cadastro, name='cliente_cadastro'),  # LEGADO
    path('cadastro/iniciar/', views_cadastro.iniciar_cadastro, name='cadastro_iniciar'),  # Verifica CPF
    path('cadastro/finalizar/', views_cadastro.finalizar_cadastro, name='cadastro_finalizar'),  # Salva + envia OTP
    path('cadastro/validar_otp/', views_cadastro.validar_otp_cadastro, name='cadastro_validar_otp'),  # Valida OTP

    # Reset de Senha via OTP
    path('senha/reset/solicitar/', views_reset_senha.solicitar_reset_senha, name='senha_reset_solicitar'),  # Envia OTP
    path('senha/reset/validar/', views_reset_senha.validar_reset_senha, name='senha_reset_validar'),  # Valida OTP + nova senha

    # Perfil
    path('perfil/', views.perfil_cliente, name='perfil_cliente'),  # API Key + JWT Token

    # Atualizações
    path('atualiza_celular/', views.atualiza_celular, name='atualiza_celular'),  # API Key + JWT Token
    path('atualiza_email/', views.atualiza_email, name='atualiza_email'),  # API Key + JWT Token
    path('grava_firebase_token/', views.grava_firebase_token, name='grava_firebase_token'),
    
    # Exclusão de conta
    path('excluir/', views.excluir_conta, name='excluir_conta'),  # API Key + JWT Token

    # Notificações
    path('notificacoes/', views.notificacoes, name='notificacoes'),  # API Key + JWT Token
    path('notificacoes_ler/', views.notificacoes_ler, name='notificacoes_ler'),  # API Key + JWT Token

    # Uso de Saldo no POS (Cliente aprova/nega/verifica)
    path('aprovar_uso_saldo/', views_saldo.aprovar_uso_saldo, name='aprovar_uso_saldo'),
    path('negar_uso_saldo/', views_saldo.negar_uso_saldo, name='negar_uso_saldo'),
    path('verificar_autorizacao/', views_saldo.verificar_autorizacao, name='verificar_autorizacao'),

    # 2FA no Login do App Móvel - Fase 4 (inclui detecção de celular expirado)
    path('2fa/verificar_necessidade/', views_2fa_login.verificar_necessidade_2fa, name='2fa_verificar_necessidade'),
    path('2fa/solicitar_codigo/', views_2fa_login.solicitar_codigo_2fa_login, name='2fa_solicitar_codigo'),
    path('2fa/validar_codigo/', views_2fa_login.validar_codigo_2fa_login, name='2fa_validar_codigo'),
    path('2fa/verificar_primeira_transacao/', views_2fa_login.verificar_primeira_transacao, name='2fa_primeira_transacao'),
    path('2fa/registrar_transacao/', views_2fa_login.registrar_transacao_completa, name='2fa_registrar_transacao'),

    # Revalidação de Celular (90 dias) - Atualiza celular_validado_em
    path('celular/status/', views_revalidacao.verificar_status_celular, name='celular_status'),
    path('celular/solicitar_codigo/', views_revalidacao.solicitar_codigo_revalidacao, name='celular_solicitar_codigo'),
    path('celular/validar_codigo/', views_revalidacao.validar_codigo_revalidacao, name='celular_validar_codigo'),

    # Gestão de Senha - App Móvel
    path('senha/solicitar_troca/', views_senha.solicitar_troca_senha, name='senha_solicitar_troca'),
    path('senha/trocar/', views_senha.trocar_senha, name='senha_trocar'),

    # Gestão de Dispositivos - App Móvel
    path('dispositivos/meus/', views_dispositivos.meus_dispositivos, name='dispositivos_meus'),
    path('dispositivos/revogar/', views_dispositivos.revogar_meu_dispositivo, name='dispositivos_revogar'),

    # API v1 - Análise de Autenticação (usado pelo riskengine)
    path('api/v1/autenticacao/analise/<str:cpf>/', 
         views_autenticacao_analise.ClienteAutenticacaoAnaliseView.as_view(), 
         name='autenticacao_analise'),

]
