"""
URLs do sistema de checkout.
"""
from django.urls import path, include
from . import views

app_name = 'checkout'

urlpatterns = [
    # API para geração de token
    path('gerar_token/', views.GerarTokenView.as_view(), name='gerar_token'),
    
    # Página de checkout (HTML)
    path('', views.CheckoutPageView.as_view(), name='checkout_page'),
    
    # API para processar dados do formulário (LEGACY - sem 2FA)
    path('processar/', views.ProcessarCheckoutView.as_view(), name='processar'),
    
    # API para simular parcelas usando CalculadoraDesconto
    path('simular_parcelas/', views.SimularParcelasView.as_view(), name='simular_parcelas'),
    
    # API para status da transação
    path('status/<str:token>/', views.StatusCheckoutView.as_view(), name='status'),
    
    # Página do simulador DermaDream
    path('simula_dermadream/', views.SimuladorDermaDreamView.as_view(), name='simula_dermadream'),
    
    # =====================================================
    # APIs 2FA (Fase 4 - Semana 21)
    # =====================================================
    path('2fa/', include('checkout.link_pagamento_web.urls_2fa')),
]
