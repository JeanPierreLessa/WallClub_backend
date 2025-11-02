"""
URLs para 2FA no Checkout Web
"""
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from .views_2fa import (
    SolicitarOTPCheckoutView,
    ValidarOTPCheckoutView,
    ConsultarLimiteProgressivoView
)

urlpatterns = [
    # 2FA Checkout - csrf_exempt aplicado nas URLs
    path('solicitar-otp/', csrf_exempt(SolicitarOTPCheckoutView.as_view()), name='checkout_solicitar_otp'),
    path('validar-otp/', csrf_exempt(ValidarOTPCheckoutView.as_view()), name='checkout_validar_otp'),
    path('limite-progressivo/', csrf_exempt(ConsultarLimiteProgressivoView.as_view()), name='checkout_limite_progressivo'),
]
