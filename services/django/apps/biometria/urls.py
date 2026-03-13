"""
URLs para o módulo de biometria (Veriff)
"""
from django.urls import path
from . import views

app_name = 'biometria'

urlpatterns = [
    path('criar_sessao/', views.criar_sessao_veriff, name='veriff_criar_sessao'),
    path('webhook/', views.webhook_veriff, name='veriff_webhook'),
    path('status/<str:session_id>/', views.status_veriff, name='veriff_status'),
]
