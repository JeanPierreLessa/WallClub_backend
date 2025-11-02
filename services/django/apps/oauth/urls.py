"""
URLs para endpoints OAuth 2.0
"""
from django.urls import path
from . import views

urlpatterns = [
    path('token/', views.token_request, name='oauth_token'),
    path('refresh/', views.token_refresh, name='oauth_refresh'),
    path('revoke/', views.token_revoke, name='oauth_revoke'),
]
