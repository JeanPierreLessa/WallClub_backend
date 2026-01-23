"""
URLs para webhooks Own Financial
"""

from django.urls import path
from adquirente_own import views_webhook

urlpatterns = [
    # Webhooks Own Financial (formato padrão)
    path('webhook/transacao/', views_webhook.webhook_transacao, name='own_webhook_transacao'),
    path('webhook/liquidacao/', views_webhook.webhook_liquidacao, name='own_webhook_liquidacao'),
    path('webhook/cadastro/', views_webhook.webhook_cadastro, name='own_webhook_cadastro'),
    path('webhook/credenciamento/', views_webhook.webhook_credenciamento, name='own_webhook_credenciamento'),

    # Webhooks Own Financial (formato alternativo que a Own está enviando)
    path('webhook/own/transacao/', views_webhook.webhook_transacao, name='own_webhook_transacao_alt'),
    path('webhook/own/liquidacao/', views_webhook.webhook_liquidacao, name='own_webhook_liquidacao_alt'),
    path('webhook/own/cadastro/', views_webhook.webhook_cadastro, name='own_webhook_cadastro_alt'),
    path('webhook/own/credenciamento/', views_webhook.webhook_credenciamento, name='own_webhook_credenciamento_alt'),
]
