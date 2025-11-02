"""
URLs para APIs Internas de Ofertas
Comunicação entre containers
"""
from django.urls import path
from . import views_internal_api

app_name = 'ofertas_internal'

urlpatterns = [
    # Ofertas (4 endpoints)
    path('listar/', views_internal_api.listar_ofertas, name='listar_ofertas'),
    path('criar/', views_internal_api.criar_oferta, name='criar_oferta'),
    path('obter/', views_internal_api.obter_oferta, name='obter_oferta'),
    path('atualizar/', views_internal_api.atualizar_oferta, name='atualizar_oferta'),
    
    # Grupos de Segmentação (2 endpoints)
    path('grupos/listar/', views_internal_api.listar_grupos, name='listar_grupos'),
    path('grupos/criar/', views_internal_api.criar_grupo, name='criar_grupo'),
]
