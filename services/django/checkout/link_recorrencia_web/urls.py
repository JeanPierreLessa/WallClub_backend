"""
URLs para checkout de recorrência.
"""
from django.urls import path
from checkout.link_recorrencia_web import views

app_name = 'recorrencia'

urlpatterns = [
    # GET: Formulário de cadastro de cartão
    path('', views.checkout_recorrencia_view, name='checkout'),

    # POST: Enviar OTP para telefone
    path('enviar-otp/', views.enviar_otp_view, name='enviar_otp'),

    # POST: Processar tokenização do cartão
    path('processar/', views.processar_cadastro_cartao_view, name='processar'),

    # Página de sucesso (redirect após cadastro)
    path('sucesso/', views.sucesso_view, name='sucesso'),
]
