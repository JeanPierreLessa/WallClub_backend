"""
URLs para ofertas
"""
from django.urls import path
from . import views

app_name = 'ofertas'

urlpatterns = [
    path('lista_ofertas/', views.lista_ofertas, name='lista_ofertas'),
    path('detalhes_oferta/', views.detalhes_oferta, name='detalhes_oferta'),
]
