# PROMPT: Implementar Integração Veriff no Backend WallClub

## CONTEXTO

Você está trabalhando no backend WallClub, um projeto Django 4.2 + Django REST Framework.
O app mobile (React Native) já tem o Veriff SDK Android integrado e funcionando.
Agora precisa implementar os endpoints no backend para criar sessões, receber webhooks e consultar status.

## STACK DO BACKEND

- Django 4.2.23 + DRF 3.16.1
- MySQL 5.7+
- Redis (cache + Celery)
- JWT customizado em `apps/cliente/jwt_cliente.py`
- Decorators: `@require_oauth_apps` (área deslogada), `@require_jwt_only` (área logada)
- Padrão: Views (orquestração) + Services (lógica) + Serializers (validação)
- Variáveis sensíveis via `.env` (dev) ou AWS Secrets Manager (prod)
- Respostas sempre com campo `sucesso` (português), não `success`

## ESTRUTURA EXISTENTE RELEVANTE

```
services/django/
├── wallclub/
│   ├── settings/base.py          # Config central, INSTALLED_APPS
│   ├── urls_apis.py              # Registro de URLs dos apps
├── apps/
│   ├── cliente/
│   │   ├── models.py             # Model Cliente (cpf, canal_id, nome, etc.)
│   │   ├── jwt_cliente.py        # Autenticação JWT customizada
│   │   ├── urls.py               # Endpoints existentes
│   │   ├── views.py              # Padrão de view
│   │   └── services.py           # Padrão de service
```

## O QUE IMPLEMENTAR

### 1. Model: VeriffSession

Criar em `apps/cliente/models_veriff.py`:

```python
class VeriffSession(models.Model):
    id = models.BigAutoField(primary_key=True)
    cliente = models.ForeignKey('Cliente', on_delete=models.CASCADE, related_name='veriff_sessions')
    canal_id = models.IntegerField()
    session_id = models.CharField(max_length=100, unique=True, db_index=True)  # ID da sessão Veriff
    session_url = models.URLField(max_length=500)  # URL para o SDK abrir
    status = models.CharField(max_length=30, default='created')
    # Status possíveis: created, submitted, approved, declined, resubmission_requested, expired, abandoned
    decision_time = models.DateTimeField(null=True, blank=True)  # Quando Veriff decidiu
    veriff_reason = models.TextField(null=True, blank=True)  # Motivo da decisão
    vendor_data = models.CharField(max_length=255, null=True, blank=True)  # Dados extras enviados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'veriff_session'
        ordering = ['-created_at']
```

**Migration:** Gerar com `python manage.py makemigrations cliente`

### 2. Serializers

Criar em `apps/cliente/serializers_veriff.py`:

```python
class CriarSessaoVeriffSerializer(serializers.Serializer):
    # Não precisa de campos - usa dados do JWT (cliente autenticado)
    pass

class VeriffWebhookSerializer(serializers.Serializer):
    id = serializers.CharField()
    feature = serializers.CharField(required=False)
    code = serializers.IntegerField(required=False)
    action = serializers.CharField()
    vendorData = serializers.CharField(required=False, allow_blank=True)
    verification = serializers.DictField()  # Contém id, status, person, document, etc.

class VeriffStatusSerializer(serializers.Serializer):
    session_id = serializers.CharField(max_length=100)
```

### 3. Service

Criar em `apps/cliente/services_veriff.py`:

```python
import requests
import hmac
import hashlib
import json
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('veriff')

class VeriffService:

    VERIFF_API_URL = 'https://stationapi.veriff.com/v1/sessions'

    @staticmethod
    def criar_sessao(cliente):
        """
        Cria sessão no Veriff para o cliente.
        Chama API Veriff com a API key do backend.
        Salva no banco e retorna sessionUrl + sessionId.
        """
        api_key = settings.VERIFF_API_KEY

        # Separar primeiro nome e sobrenome
        partes_nome = cliente.nome.split(' ', 1) if cliente.nome else ['Cliente', 'WallClub']
        first_name = partes_nome[0]
        last_name = partes_nome[1] if len(partes_nome) > 1 else ''

        payload = {
            'verification': {
                'callback': settings.VERIFF_WEBHOOK_URL,
                'person': {
                    'firstName': first_name,
                    'lastName': last_name,
                },
                'vendorData': str(cliente.id),
            }
        }

        response = requests.post(
            VeriffService.VERIFF_API_URL,
            headers={
                'X-AUTH-CLIENT': api_key,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=15,
        )

        data = response.json()

        if data.get('status') != 'success' or not data.get('verification', {}).get('url'):
            logger.error(f'[VERIFF] Erro ao criar sessão: {data}')
            raise Exception(data.get('message', 'Erro ao criar sessão Veriff'))

        verification = data['verification']

        # Salvar no banco
        from apps.cliente.models_veriff import VeriffSession
        sessao = VeriffSession.objects.create(
            cliente=cliente,
            canal_id=cliente.canal_id,
            session_id=verification['id'],
            session_url=verification['url'],
            status='created',
            vendor_data=str(cliente.id),
        )

        logger.info(f'[VERIFF] Sessão criada para cliente {cliente.id}: {verification["id"]}')

        return {
            'sessionUrl': verification['url'],
            'sessionId': verification['id'],
        }

    @staticmethod
    def processar_webhook(payload):
        """
        Processa webhook recebido do Veriff.
        Atualiza status da sessão no banco.
        """
        verification = payload.get('verification', {})
        session_id = verification.get('id')
        status = verification.get('status')
        reason = verification.get('reason')

        if not session_id:
            logger.error('[VERIFF] Webhook sem session_id')
            return False

        from apps.cliente.models_veriff import VeriffSession
        try:
            sessao = VeriffSession.objects.get(session_id=session_id)
        except VeriffSession.DoesNotExist:
            logger.error(f'[VERIFF] Sessão não encontrada: {session_id}')
            return False

        sessao.status = status
        sessao.veriff_reason = reason
        sessao.decision_time = timezone.now()
        sessao.save()

        logger.info(f'[VERIFF] Webhook processado - sessão {session_id}: {status}')

        # Se aprovado, marcar cliente como verificado
        if status == 'approved':
            cliente = sessao.cliente
            # TODO: Adicionar campo identidade_verificada ao model Cliente
            # cliente.identidade_verificada = True
            # cliente.identidade_verificada_em = timezone.now()
            # cliente.save(update_fields=['identidade_verificada', 'identidade_verificada_em'])
            logger.info(f'[VERIFF] Cliente {cliente.id} APROVADO na verificação')

        return True

    @staticmethod
    def validar_hmac(payload_bytes, signature):
        """
        Valida assinatura HMAC-SHA256 do webhook Veriff.
        Retorna True se válida.
        """
        shared_secret = settings.VERIFF_SHARED_SECRET
        expected = hmac.new(
            shared_secret.encode('utf-8'),
            payload_bytes,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected.lower(), signature.lower())

    @staticmethod
    def consultar_status(session_id, cliente_id):
        """
        Consulta status de uma sessão Veriff no banco local.
        """
        from apps.cliente.models_veriff import VeriffSession
        try:
            sessao = VeriffSession.objects.get(
                session_id=session_id,
                cliente_id=cliente_id,
            )
        except VeriffSession.DoesNotExist:
            return None

        MENSAGENS = {
            'created': 'Verificação ainda não iniciada',
            'submitted': 'Verificação em processamento',
            'approved': 'Identidade verificada com sucesso',
            'declined': 'Verificação não aprovada',
            'resubmission_requested': 'É necessário refazer a verificação',
            'expired': 'Sessão expirada, inicie novamente',
            'abandoned': 'Verificação abandonada',
        }

        return {
            'status': sessao.status,
            'mensagem': MENSAGENS.get(sessao.status, 'Status desconhecido'),
        }
```

### 4. Views

Criar em `apps/cliente/views_veriff.py`:

```python
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

# Importar decorators do projeto
# @require_jwt_only para endpoints autenticados
# @require_oauth_apps se for área deslogada


@api_view(['POST'])
@require_jwt_only  # Usuário logado com JWT
def criar_sessao_veriff(request):
    """
    POST /api/v1/cliente/veriff/criar-sessao/
    Cria sessão Veriff para o cliente autenticado.
    """
    try:
        from apps.cliente.models import Cliente
        cliente = Cliente.objects.get(id=request.user.cliente_id)

        resultado = VeriffService.criar_sessao(cliente)

        return Response({
            'sucesso': True,
            'dados': resultado,
        }, status=200)

    except Cliente.DoesNotExist:
        return Response({
            'sucesso': False,
            'erro': 'cliente_nao_encontrado',
            'mensagem': 'Cliente não encontrado',
        }, status=404)

    except Exception as e:
        return Response({
            'sucesso': False,
            'erro': 'erro_criar_sessao',
            'mensagem': str(e),
        }, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])  # Webhook público (valida via HMAC)
def webhook_veriff(request):
    """
    POST /api/v1/cliente/veriff/webhook/
    Recebe decisão do Veriff via webhook.
    Valida assinatura HMAC antes de processar.
    """
    # Validar assinatura HMAC
    signature = request.headers.get('X-HMAC-SIGNATURE', '')
    if not signature:
        return Response({'erro': 'assinatura_ausente'}, status=401)

    if not VeriffService.validar_hmac(request.body, signature):
        return Response({'erro': 'assinatura_invalida'}, status=401)

    # Processar webhook
    sucesso = VeriffService.processar_webhook(request.data)

    if sucesso:
        return Response({'sucesso': True}, status=200)
    else:
        return Response({'sucesso': False}, status=400)


@api_view(['GET'])
@require_jwt_only  # Usuário logado com JWT
def status_veriff(request, session_id):
    """
    GET /api/v1/cliente/veriff/status/{session_id}/
    Consulta status da verificação.
    """
    resultado = VeriffService.consultar_status(session_id, request.user.cliente_id)

    if resultado is None:
        return Response({
            'sucesso': False,
            'erro': 'sessao_nao_encontrada',
            'mensagem': 'Sessão não encontrada',
        }, status=404)

    return Response({
        'sucesso': True,
        'dados': resultado,
    }, status=200)
```

### 5. URLs

Adicionar em `apps/cliente/urls.py`:

```python
# Veriff - Verificação de identidade
path('veriff/criar-sessao/', views_veriff.criar_sessao_veriff, name='veriff_criar_sessao'),
path('veriff/webhook/', views_veriff.webhook_veriff, name='veriff_webhook'),
path('veriff/status/<str:session_id>/', views_veriff.status_veriff, name='veriff_status'),
```

Os endpoints ficam em:
- `POST /api/v1/cliente/veriff/criar-sessao/` (JWT)
- `POST /api/v1/cliente/veriff/webhook/` (público, HMAC)
- `GET /api/v1/cliente/veriff/status/{session_id}/` (JWT)

### 6. Settings

Adicionar ao `.env`:

```bash
# Veriff - Verificação de identidade
VERIFF_API_KEY=5c1d2390-0409-4a13-9c1b-67d0577881ef
VERIFF_SHARED_SECRET=<pegar_no_dashboard_veriff>
VERIFF_WEBHOOK_URL=https://seu-dominio.com/api/v1/cliente/veriff/webhook/
```

Adicionar ao `wallclub/settings/base.py`:

```python
# Veriff
VERIFF_API_KEY = config_manager.get('VERIFF_API_KEY', '')
VERIFF_SHARED_SECRET = config_manager.get('VERIFF_SHARED_SECRET', '')
VERIFF_WEBHOOK_URL = config_manager.get('VERIFF_WEBHOOK_URL', '')
```

### 7. Dependência

Adicionar ao `requirements.txt` (se `requests` não estiver):

```
requests>=2.31.0
```

## CONTRATO COM O APP MOBILE

O app mobile (React Native) já está programado para chamar estes endpoints exatamente assim:

### Criar Sessão (app chama ao abrir tela de biometria)

```
POST /api/v1/cliente/veriff/criar-sessao/
Headers:
  Authorization: Bearer <jwt_token>
  Content-Type: application/json

Response esperada:
{
  "sucesso": true,
  "dados": {
    "sessionUrl": "https://magic.veriff.me/v/...",
    "sessionId": "abc123-def456-..."
  }
}
```

### Consultar Status (app chama após SDK retornar DONE)

```
GET /api/v1/cliente/veriff/status/{sessionId}/
Headers:
  Authorization: Bearer <jwt_token>

Response esperada:
{
  "sucesso": true,
  "dados": {
    "status": "approved",
    "mensagem": "Identidade verificada com sucesso"
  }
}
```

### Webhook (Veriff chama o backend diretamente)

```
POST /api/v1/cliente/veriff/webhook/
Headers:
  X-HMAC-SIGNATURE: <hmac_sha256>
  Content-Type: application/json

Body (enviado pelo Veriff):
{
  "id": "event_id",
  "feature": "selfid",
  "code": 9001,
  "action": "decision",
  "vendorData": "123",
  "verification": {
    "id": "session_id_aqui",
    "status": "approved",
    "person": {
      "firstName": "João",
      "lastName": "Silva"
    },
    "document": {
      "number": "...",
      "type": "ID_CARD",
      "country": "BR"
    }
  }
}
```

## CHECKLIST DE IMPLEMENTAÇÃO

1. [ ] Criar `apps/cliente/models_veriff.py` com model `VeriffSession`
2. [ ] Gerar migration: `python manage.py makemigrations cliente`
3. [ ] Aplicar migration: `python manage.py migrate`
4. [ ] Criar `apps/cliente/serializers_veriff.py`
5. [ ] Criar `apps/cliente/services_veriff.py` com `VeriffService`
6. [ ] Criar `apps/cliente/views_veriff.py` com 3 endpoints
7. [ ] Registrar URLs em `apps/cliente/urls.py`
8. [ ] Adicionar variáveis no `.env` e `settings/base.py`
9. [ ] Configurar webhook URL no Dashboard Veriff
10. [ ] Copiar Shared Secret do Dashboard para `.env`
11. [ ] Testar criar sessão via app
12. [ ] Testar webhook com sessão real (Live integration)
13. [ ] Testar consulta de status após decisão

## CONFIGURAÇÃO NO DASHBOARD VERIFF

1. Acessar https://office.veriff.com
2. Settings > Integrations > Webhook URL: `https://seu-dominio.com/api/v1/cliente/veriff/webhook/`
3. Settings > API Keys > copiar Shared Secret para validação HMAC
4. Ativar "Live integration" para processar verificações reais

## NOTAS IMPORTANTES

- **Padrão de resposta**: Sempre usar `sucesso` (português), nunca `success`
- **Padrão de erro**: Campo `erro` tem prioridade sobre `mensagem`
- **Logs**: Prefixo `[VERIFF]` em todos os logs
- **JWT**: Usar `@require_jwt_only` nos endpoints autenticados
- **Webhook**: Usar `@permission_classes([AllowAny])` + validação HMAC manual
- **Lazy imports**: Usar `from apps.cliente.models_veriff import VeriffSession` dentro das funções do service (padrão do projeto para evitar imports circulares)
- **Rate limiting**: Considerar adicionar em `API_RATE_LIMITS` no `settings/base.py`
