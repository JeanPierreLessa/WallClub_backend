# Proposta: API de Autenticação OAuth2 para Aplicativo Externo

## 1. Contexto

Criar uma API de autenticação OAuth2 exposta para internet que permita a um desenvolvedor externo integrar seu aplicativo com o backend WallClub de forma segura.

## 2. Arquitetura Recomendada

### 2.1 Diagrama de Arquitetura

```
┌─────────────────────────┐
│  Aplicativo Externo     │
│  (Cliente OAuth2)       │
└───────────┬─────────────┘
            │
            │ HTTPS + OAuth2
            ▼
┌─────────────────────────────────────────┐
│  Camada de Proteção                     │
│  - CloudFlare (DDoS, WAF)               │
│  - Nginx (Reverse Proxy, Rate Limit)    │
└───────────┬─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  Django OAuth2 Server                   │
│  - django-oauth-toolkit                 │
│  - Token Management                     │
│  - Scope Control                        │
│  - Client Credentials                   │
└───────────┬─────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────┐
│  WallClub Backend APIs                  │
│  - Recursos protegidos por token        │
│  - Validação de scopes                  │
│  - Rate limiting por client             │
└─────────────────────────────────────────┘
```

## 3. Solução Técnica: Django OAuth Toolkit

### 3.1 Dependências

```python
# requirements.txt
django-oauth-toolkit==2.3.0
djangorestframework==3.14.0
django-cors-headers==4.3.0
djangorestframework-simplejwt==5.3.0  # Opcional, para JWT
```

### 3.2 Fluxo OAuth2 Recomendado

**Client Credentials Flow** (Server-to-Server)

```
1. App Externo → POST /oauth/token/
   Headers: Authorization: Basic base64(client_id:client_secret)
   Body: grant_type=client_credentials&scope=read:profile write:transaction

2. OAuth Server → Response
   {
     "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
     "token_type": "Bearer",
     "expires_in": 3600,
     "scope": "read:profile write:transaction"
   }

3. App Externo → GET /api/v1/user/profile/
   Headers: Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc...

4. API → Valida token e retorna dados
```

## 4. Configuração Django

### 4.1 Settings

```python
# settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # OAuth2 e API
    'oauth2_provider',
    'rest_framework',
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # ... outros middlewares
]

# Configuração OAuth2
OAUTH2_PROVIDER = {
    # Expiração de tokens
    'ACCESS_TOKEN_EXPIRE_SECONDS': 3600,  # 1 hora
    'REFRESH_TOKEN_EXPIRE_SECONDS': 2592000,  # 30 dias

    # Rotação de refresh tokens
    'ROTATE_REFRESH_TOKEN': True,

    # Scopes disponíveis
    'SCOPES': {
        'read:profile': 'Ler dados do perfil do usuário',
        'read:balance': 'Consultar saldo e extratos',
        'write:transaction': 'Criar transações',
        'read:transaction': 'Consultar transações',
        'read:cashback': 'Consultar cashback',
        'write:cashback': 'Resgatar cashback',
    },

    # Backend OAuth2
    'OAUTH2_BACKEND_CLASS': 'oauth2_provider.oauth2_backends.JSONOAuthLibCore',

    # Permitir apenas HTTPS em produção
    'ALLOWED_SCHEMES': ['https'] if not DEBUG else ['http', 'https'],
}

# Configuração REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.SessionAuthentication',  # Para admin
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
        'rest_framework.throttling.ScopedRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/minute',
        'user': '1000/minute',
        'oauth_client': '500/minute',
    },
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
}

# CORS (ajustar conforme necessário)
CORS_ALLOWED_ORIGINS = [
    "https://app-externo.com",
]

CORS_ALLOW_METHODS = [
    'GET',
    'POST',
    'PUT',
    'PATCH',
    'DELETE',
    'OPTIONS',
]
```

### 4.2 URLs

```python
# urls.py

from django.urls import path, include

urlpatterns = [
    # OAuth2 endpoints
    path('oauth/', include('oauth2_provider.urls', namespace='oauth2_provider')),

    # API endpoints
    path('api/v1/', include('api.urls')),
]
```

### 4.3 Exemplo de View Protegida

```python
# api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope

class UserProfileView(APIView):
    permission_classes = [IsAuthenticated, TokenHasReadWriteScope]
    required_scopes = ['read:profile']

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'cpf': user.cpf,
        })

class TransactionCreateView(APIView):
    permission_classes = [IsAuthenticated, TokenHasReadWriteScope]
    required_scopes = ['write:transaction']
    throttle_scope = 'oauth_client'

    def post(self, request):
        # Lógica de criação de transação
        return Response({'status': 'created'})
```

## 5. Segurança

### 5.1 Camadas de Proteção

#### Nível 1: CloudFlare
- **DDoS Protection**: Proteção contra ataques distribuídos
- **WAF**: Web Application Firewall
- **Rate Limiting**: Limite global de requests
- **SSL/TLS**: Certificado gerenciado

#### Nível 2: Nginx
```nginx
# nginx.conf

upstream django_oauth {
    server 127.0.0.1:8000;
}

# Rate limiting zones
limit_req_zone $binary_remote_addr zone=oauth_limit:10m rate=100r/m;
limit_req_zone $http_authorization zone=client_limit:10m rate=500r/m;

server {
    listen 443 ssl http2;
    server_name api.wallclub.com;

    ssl_certificate /etc/ssl/certs/wallclub.crt;
    ssl_certificate_key /etc/ssl/private/wallclub.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    # Headers de segurança
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    location /oauth/ {
        limit_req zone=oauth_limit burst=20 nodelay;
        proxy_pass http://django_oauth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /api/ {
        limit_req zone=client_limit burst=50 nodelay;
        proxy_pass http://django_oauth;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Nível 3: Django
- **Token Validation**: Validação de tokens em cada request
- **Scope Checking**: Verificação de permissões granulares
- **Rate Limiting**: Throttling por client_id
- **Audit Logging**: Log de todas as operações

### 5.2 Configurações de Segurança

```python
# settings.py - Segurança adicional

# HTTPS obrigatório em produção
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Headers de segurança
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'

# Allowed hosts
ALLOWED_HOSTS = ['api.wallclub.com']
```

## 6. Gestão de Clientes OAuth2

### 6.1 Criar Cliente via Django Admin

```python
# Via Django shell ou admin
from oauth2_provider.models import Application

app = Application.objects.create(
    name="App Externo - Parceiro XYZ",
    client_type=Application.CLIENT_CONFIDENTIAL,
    authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
    user=None,  # Client credentials não precisa de user
)

print(f"Client ID: {app.client_id}")
print(f"Client Secret: {app.client_secret}")
```

### 6.2 Modelo de Dados Estendido (Opcional)

```python
# models.py

from django.db import models
from oauth2_provider.models import Application

class OAuthClient(models.Model):
    """Extensão do modelo Application para dados adicionais"""
    application = models.OneToOneField(Application, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    ip_whitelist = models.TextField(blank=True, help_text="IPs permitidos, um por linha")
    is_active = models.BooleanField(default=True)
    max_requests_per_minute = models.IntegerField(default=500)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} - {self.application.name}"
```

## 7. Monitoramento e Logs

### 7.1 Métricas Importantes

```python
# middleware.py - Middleware de métricas

import time
from django.utils.deprecation import MiddlewareMixin
from prometheus_client import Counter, Histogram

oauth_requests = Counter(
    'oauth_requests_total',
    'Total OAuth requests',
    ['client_id', 'endpoint', 'status']
)

oauth_latency = Histogram(
    'oauth_request_duration_seconds',
    'OAuth request latency',
    ['client_id', 'endpoint']
)

class OAuthMetricsMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, 'auth') and request.auth:
            client_id = request.auth.application.client_id
            endpoint = request.path
            duration = time.time() - request._start_time

            oauth_requests.labels(
                client_id=client_id,
                endpoint=endpoint,
                status=response.status_code
            ).inc()

            oauth_latency.labels(
                client_id=client_id,
                endpoint=endpoint
            ).observe(duration)

        return response
```

### 7.2 Logging

```python
# settings.py

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'oauth_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/wallclub/oauth.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'sentry': {
            'level': 'ERROR',
            'class': 'sentry_sdk.integrations.logging.EventHandler',
        },
    },
    'loggers': {
        'oauth2_provider': {
            'handlers': ['oauth_file', 'sentry'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
```

## 8. Documentação para Desenvolvedor Externo

### 8.1 Swagger/OpenAPI

```python
# settings.py

INSTALLED_APPS += [
    'drf_spectacular',
]

REST_FRAMEWORK['DEFAULT_SCHEMA_CLASS'] = 'drf_spectacular.openapi.AutoSchema'

SPECTACULAR_SETTINGS = {
    'TITLE': 'WallClub API',
    'DESCRIPTION': 'API OAuth2 para integração com WallClub',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    'SECURITY': [{'oauth2': []}],
}

# urls.py
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
```

### 8.2 Guia de Quick Start

Criar arquivo `docs/API_QUICKSTART.md`:

```markdown
# Quick Start - WallClub OAuth2 API

## 1. Obter Credenciais
Contate o time WallClub para receber:
- Client ID
- Client Secret

## 2. Obter Access Token

```bash
curl -X POST https://api.wallclub.com/oauth/token/ \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -u "CLIENT_ID:CLIENT_SECRET" \
  -d "grant_type=client_credentials&scope=read:profile read:balance"
```

## 3. Usar Token nas Requisições

```bash
curl -X GET https://api.wallclub.com/api/v1/user/profile/ \
  -H "Authorization: Bearer ACCESS_TOKEN"
```
```

## 9. Testes

### 9.1 Testes Unitários

```python
# tests/test_oauth.py

from django.test import TestCase
from oauth2_provider.models import Application, AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()

class OAuthTestCase(TestCase):
    def setUp(self):
        self.app = Application.objects.create(
            name="Test App",
            client_type=Application.CLIENT_CONFIDENTIAL,
            authorization_grant_type=Application.GRANT_CLIENT_CREDENTIALS,
        )

    def test_token_generation(self):
        response = self.client.post('/oauth/token/', {
            'grant_type': 'client_credentials',
            'client_id': self.app.client_id,
            'client_secret': self.app.client_secret,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn('access_token', response.json())

    def test_protected_endpoint(self):
        token = AccessToken.objects.create(
            application=self.app,
            token='test-token',
            scope='read:profile',
        )

        response = self.client.get('/api/v1/user/profile/',
            HTTP_AUTHORIZATION=f'Bearer {token.token}')
        self.assertEqual(response.status_code, 200)
```

## 10. Alternativas Avaliadas

### 10.1 Keycloak
**Prós:**
- Identity Provider completo
- Suporte a múltiplos protocolos
- Admin UI robusta
- Open source

**Contras:**
- Complexidade de setup
- Requer infraestrutura adicional (Java)
- Curva de aprendizado

### 10.2 Auth0 / Okta
**Prós:**
- Solução gerenciada
- Fácil integração
- Suporte empresarial

**Contras:**
- Custo por MAU
- Vendor lock-in
- Menos controle

### 10.3 AWS API Gateway + Cognito
**Prós:**
- Integração nativa AWS
- Escalabilidade automática
- Pay-per-use

**Contras:**
- Vendor lock-in AWS
- Custo pode crescer
- Menos flexibilidade

## 11. Roadmap de Implementação

### Fase 1 - Setup Básico (1 semana)
- [ ] Instalar django-oauth-toolkit
- [ ] Configurar settings
- [ ] Criar endpoints OAuth2
- [ ] Testes básicos

### Fase 2 - Segurança (1 semana)
- [ ] Configurar HTTPS
- [ ] Implementar rate limiting
- [ ] Configurar CORS
- [ ] Audit logging

### Fase 3 - APIs Protegidas (2 semanas)
- [ ] Criar endpoints de API
- [ ] Implementar scopes
- [ ] Validação de tokens
- [ ] Testes de integração

### Fase 4 - Monitoramento (1 semana)
- [ ] Configurar Prometheus
- [ ] Dashboards Grafana
- [ ] Alertas Sentry
- [ ] Logs centralizados

### Fase 5 - Documentação (1 semana)
- [ ] Swagger/OpenAPI
- [ ] Guia de Quick Start
- [ ] Postman Collection
- [ ] Exemplos de código

## 12. Custos Estimados

### Infraestrutura
- **CloudFlare Pro**: ~$20/mês
- **Servidor adicional** (se necessário): ~$50-100/mês
- **Monitoramento** (Sentry, etc.): ~$30/mês

### Desenvolvimento
- **Setup inicial**: ~40 horas
- **Manutenção mensal**: ~8 horas

**Total estimado**: $100-150/mês + desenvolvimento inicial

## 13. Próximos Passos

1. **Validar requisitos** com desenvolvedor externo
2. **Definir scopes** necessários
3. **Aprovar arquitetura** com time técnico
4. **Iniciar implementação** seguindo roadmap
5. **Testes em ambiente** de staging
6. **Deploy em produção** com monitoramento

---

**Documento criado em**: 2025
**Responsável**: Time Backend WallClub
**Status**: Proposta para avaliação
