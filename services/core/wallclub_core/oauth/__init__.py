"""
Sistema OAuth 2.0 para WallClub.
Centraliza autenticação OAuth para múltiplos contextos (apps, posp2, checkout).

Para usar os componentes OAuth, importe diretamente:
- from wallclub_core.oauth.models import OAuthClient, OAuthToken
- from wallclub_core.oauth.services import OAuthService
- from wallclub_core.oauth.decorators import require_oauth_token, require_oauth_apps
"""
