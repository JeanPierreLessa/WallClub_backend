"""
URLs para webhooks Own Financial
"""

from django.urls import path
from adquirente_own import views_webhook

urlpatterns = [
    # Webhooks Own Financial
    path('webhook/transacao/', views_webhook.webhook_transacao, name='own_webhook_transacao'),
    path('webhook/liquidacao/', views_webhook.webhook_liquidacao, name='own_webhook_liquidacao'),
    path('webhook/cadastro/', views_webhook.webhook_cadastro, name='own_webhook_cadastro'),
]
