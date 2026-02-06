"""
URLs para webhooks Own Financial
"""

from django.urls import path
from adquirente_own import views_webhook

urlpatterns = [
    # Webhooks Own Financial
    path('webhook/own/transacao/', views_webhook.webhook_transacao, name='own_webhook_transacao'),
    path('webhook/own/liquidacao/', views_webhook.webhook_liquidacao, name='own_webhook_liquidacao'),
    path('webhook/own/credenciamento/', views_webhook.webhook_credenciamento, name='own_webhook_credenciamento'),
]
