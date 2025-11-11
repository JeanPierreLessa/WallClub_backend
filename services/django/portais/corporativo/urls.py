from django.urls import path
from . import views

app_name = 'portais_corporativo'

urlpatterns = [
    # Páginas públicas (sem login)
    path('', views.home_view, name='home'),
    path('para_voce_cliente/', views.para_voce_cliente_view, name='para_voce_cliente'),
    path('para_voce_comerciante/', views.para_voce_comerciante_view, name='para_voce_comerciante'),
    path('sobre/', views.sobre_view, name='sobre'),
    path('contato/', views.contato_view, name='contato'),
    path('download_app_wall/', views.download_app_view, name='download_app'),
    path('politica_privacidade/', views.politica_privacidade_view, name='politica_privacidade'),
    path('termos_uso/', views.termos_uso_view, name='termos_uso'),
    path('termo_servico_adesao/', views.termo_servico_adesao_view, name='termo_servico_adesao'),
    
    # API pública
    path('api/informacoes/', views.api_informacoes, name='api_informacoes'),
]
