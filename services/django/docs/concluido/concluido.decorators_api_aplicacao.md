# Aplicação de Decorators API - Tratamento Padronizado de Erros

**Data Criação:** 2025-10-11  
**Última Revisão:** 2025-10-17  
**Status:** ✅ FASES 1 E 3 CONCLUÍDAS - POSP2 (13 endpoints) + Portais (5 endpoints)  
**Arquivo Base:** `comum/decorators/api_decorators.py`

---

## Decorators Disponíveis

### 1. `@handle_api_errors`
- **Função:** Tratamento automático de exceções
- **Captura:** JSONDecodeError (400) + Exception genérica (500)
- **Log:** Automático com `registrar_log(nivel='ERROR')`

### 2. `@validate_required_params(*params)`
- **Função:** Validação de parâmetros obrigatórios no body
- **Retorna:** 400 se parâmetros faltando
- **Mensagem:** Lista parâmetros obrigatórios e faltantes

---

## ⚠️ Regra Fundamental

**USAR APENAS EM:**
- ✅ Views Django puras (não DRF)
- ✅ Endpoints que retornam `JsonResponse`
- ✅ Views decoradas com `@csrf_exempt` ou `@require_http_methods`

**NÃO USAR EM:**
- ❌ Views DRF (`@api_view`)
- ❌ Views que retornam `Response` (DRF)
- ❌ Endpoints com serializers DRF

---

## Endpoints que DEVEM usar os Decorators

### 🔹 POSP2 (`posp2/views.py`)

**Views Django Puras:**
```python
@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf', 'senha', 'terminal')
def validar_senha_e_saldo(request):
    # ...

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('auth_token', 'terminal', 'valor')
def solicitar_autorizacao_saldo(request):
    # ...

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('autorizacao_id', 'terminal')
def verificar_autorizacao(request):
    # ...

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('terminal', 'valor', 'bandeira', 'wall')
def simula_parcelas(request):
    # ...

@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
def trdata(request):
    # Validação customizada (muitos params opcionais)
    # ...
```

**Total:** 5-6 endpoints

---

### 🔹 Portais AJAX (`portais/admin/views.py`, `portais/vendas/views.py`)

**Endpoints AJAX Administrativos:**
```python
@ajax_admin_required
def ajax_lojas(request):
    # Retorna JsonResponse com lista de lojas filtradas por canal
    # ...

@ajax_admin_required  
def ajax_grupos_economicos(request):
    # Retorna JsonResponse com grupos econômicos filtrados
    # ...

@ajax_admin_required
def ajax_canais(request):
    # Retorna JsonResponse com canais do usuário
    # ...

@ajax_admin_required
def ajax_regionais(request):
    # Retorna JsonResponse com regionais
    # ...

@ajax_admin_required
def ajax_vendedores(request):
    # Retorna JsonResponse com vendedores
    # ...
```

**Portal de Vendas:**
```python
@requer_checkout_vendedor
def buscar_cliente_ajax(request):
    # Busca cliente por documento e retorna JsonResponse
    # ...

@requer_checkout_vendedor
def calcular_parcelas_ajax(request):
    # Calcula parcelas e retorna JsonResponse
    # ...

@requer_checkout_vendedor
def simular_parcelas_ajax(request):
    # Simula parcelas com CalculadoraDesconto
    # ...
```

**Portal Corporativo:**
```python
def contato_submit(request):
    # Formulário de contato, retorna JsonResponse
    # ...

def dados_graficos(request):
    # Dados para gráficos dashboard
    # ...
```

**Total:** ~10 endpoints AJAX

**Observação:** Estes endpoints já têm autenticação customizada (`@ajax_admin_required`, `@requer_checkout_vendedor`). 
Prioridade **BAIXA** para decorators - focar em middleware genérico.

---

### 🔹 Portais Web (Possíveis Candidatos)

**Portal Lojista (`portais/lojista/views.py`):**
- Endpoints AJAX para filtros
- Exportações de relatórios
- **Status:** Verificar se retornam `JsonResponse` ou templates

**Portal Admin (`portais/admin/views.py`):**
- Endpoints AJAX similares
- **Status:** Verificar implementação

---

## Endpoints que NÃO devem usar (DRF)

### ❌ Apps Cliente (`apps/cliente/views.py`)
```python
# DRF - Não usar decorators
@api_view(['POST'])
@require_oauth_apps
def cliente_login(request):
    return Response({...})  # DRF Response
```

### ❌ Apps Ofertas (`apps/ofertas/views.py`)
```python
# DRF - Não usar decorators
@api_view(['POST'])
@require_oauth_apps
def lista_ofertas(request):
    return Response({...})  # DRF Response
```

### ❌ Apps Transações (`apps/transacoes/views.py`)
```python
# DRF - Não usar decorators
@api_view(['POST'])
@require_oauth_apps
def saldo(request):
    return Response({...})  # DRF Response
```

**Motivo:** Views DRF já têm tratamento próprio com `Response` objects

---

## Plano de Implementação

### Fase 1: POSP2 (Prioridade Alta) ✅ CONCLUÍDA
- [x] `validar_senha_e_saldo` - decorators aplicados
- [x] `solicitar_autorizacao_saldo` - decorators aplicados
- [x] `verificar_autorizacao` - decorators aplicados
- [x] `simula_parcelas` - decorators aplicados
- [x] `trdata` - `@handle_api_errors` aplicado
- [x] **Total: 13 endpoints POSP2 refatorados**
- [x] **~90 linhas de código repetido removidas**

**Data de conclusão:** 16/10/2025  
**Arquivo:** `posp2/views.py`  
**Documentação:** `ROTEIRO_MESTRE_SEQUENCIAL.md` - Fase 1, Semanas 5-6

### Fase 2: Checkout Link Pagamento ❌ NÃO APLICÁVEL
- ❌ Views usam **DRF** (`APIView`, `Response`)
- ❌ Decorators são para Django puro, não DRF
- ✅ DRF já tem tratamento próprio de erros

**Conclusão:** Checkout está correto como está (DRF patterns)

### Fase 3: Portais AJAX ✅ CONCLUÍDA
- [x] `ajax_lojas` - decorator aplicado
- [x] `ajax_grupos_economicos` - decorator aplicado
- [x] `ajax_canais` - decorator aplicado
- [x] `ajax_regionais` - decorator aplicado
- [x] `ajax_vendedores` - decorator aplicado
- [x] **Total: 5 endpoints AJAX refatorados**
- [x] **~40 linhas de código repetido removidas**

**Data de conclusão:** 17/10/2025  
**Arquivo:** `portais/admin/views.py`  
**Benefícios:** Tratamento de erros padronizado, logs automáticos, código mais limpo

---

## Padrão de Implementação

### Antes (sem decorators):
```python
@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
def validar_senha_e_saldo(request):
    try:
        data = json.loads(request.body)
        
        # Validação manual
        if not data.get('cpf'):
            return JsonResponse({'sucesso': False, 'mensagem': 'CPF obrigatório'}, status=400)
        
        # Lógica...
        
    except json.JSONDecodeError:
        return JsonResponse({'sucesso': False, 'mensagem': 'JSON inválido'}, status=400)
    except Exception as e:
        registrar_log('posp2', f'Erro: {str(e)}', nivel='ERROR')
        return JsonResponse({'sucesso': False, 'mensagem': 'Erro interno'}, status=500)
```

### Depois (com decorators):
```python
@csrf_exempt
@require_http_methods(["POST"])
@require_oauth_posp2
@handle_api_errors
@validate_required_params('cpf', 'senha', 'terminal')
def validar_senha_e_saldo(request):
    data = json.loads(request.body)  # Seguro: decorator já validou JSON
    
    # cpf, senha, terminal já foram validados
    # Lógica direta sem try/except manual
    
    return JsonResponse({'sucesso': True, 'dados': resultado})
```

---

## Benefícios

### 🎯 Código Limpo
- Elimina try/except repetitivo
- Reduz duplicação de código
- Foco na lógica de negócio

### 🔒 Segurança
- Validação consistente de parâmetros
- Tratamento uniforme de erros
- Logs automáticos de exceções

### 📊 Padronização
- Mensagens de erro consistentes
- Status codes corretos (400, 500)
- Formato de resposta uniforme

---

## Observações Importantes

### 1. Ordem dos Decorators
```python
@csrf_exempt              # 1º - Django
@require_http_methods     # 2º - Django
@require_oauth_posp2      # 3º - OAuth
@handle_api_errors        # 4º - Tratamento erros
@validate_required_params # 5º - Validação params
def minha_view(request):
    pass
```

### 2. Views com Validação Complexa
Para endpoints com muitos parâmetros opcionais (ex: `trdata`), usar apenas `@handle_api_errors` e manter validações customizadas.

### 3. Compatibilidade DRF
**NUNCA** misturar:
- `@api_view` + `@handle_api_errors` = ❌
- `Response` + `JsonResponse` = ❌

---

## Resumo Executivo

| Módulo | Endpoints | Usar Decorators | Usar Middleware | Status | Prioridade |
|--------|-----------|-----------------|-----------------|--------|------------|
| POSP2 | 14-15 | ✅ Sim | ✅ Sim | 🔴 Pendente | P1 - ALTA |
| Portais AJAX | ~10 | ❌ Não* | ✅ Sim | 🟡 Análise | P2 - MÉDIA |
| Apps (DRF) | ~15 | ❌ Não | ✅ Sim | N/A | P3 - BAIXA |
| Checkout Link (DRF) | 4 | ❌ Não | ✅ Sim | N/A | P3 - BAIXA |

*Já possuem autenticação customizada, não precisam de decorators adicionais.

**Estratégia Recomendada:**
1. **Fase 1:** Criar `APISecurityMiddleware` genérico (rate limiting, logging, validação)
2. **Fase 2:** Aplicar decorators em POSP2 (tratamento de erros padronizado)
3. **Fase 3:** Monitorar e ajustar middleware conforme necessidade

**Total Estimado:** 14-15 endpoints POSP2 para refatorar com decorators  
**Tempo Estimado:** 3-4 dias (middleware + decorators + testes)  
**Impacto:** MÉDIO - Melhora código, não quebra funcionalidade

---

## 🛡️ Plano de Implementação: API Security Middleware

### Objetivo
Criar middleware Django para proteção, monitoramento e padronização de todas as APIs públicas (POSP2, Apps, Checkout).

### Funcionalidades do Middleware

#### 1. **Rate Limiting** (Prioridade ALTA)
- Controle de requisições por IP
- Diferentes limites por tipo de endpoint:
  - POSP2: 100 req/min por terminal
  - Apps: 50 req/min por usuário
  - Checkout: 10 req/min por IP
- Cache em memória (Django cache)
- Resposta HTTP 429 (Too Many Requests)

#### 2. **Request Validation** (Prioridade MÉDIA)
- Validação de Content-Type (application/json)
- Validação de tamanho máximo do body (10MB)
- Bloqueio de IPs em blacklist
- Headers obrigatórios para APIs específicas

#### 3. **Logging Padronizado** (Prioridade ALTA)
- Log de todas requisições a APIs públicas
- Informações registradas:
  - IP do cliente
  - Endpoint acessado
  - Método HTTP
  - Status da resposta
  - Tempo de processamento
  - User-Agent
- Integração com `comum/utilitarios/log_control.py`

#### 4. **Security Headers** (Prioridade BAIXA)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block

### Estrutura de Arquivos

```
comum/
├── middleware/
│   ├── __init__.py
│   ├── api_security.py          # Middleware principal
│   ├── rate_limiter.py          # Lógica de rate limiting
│   └── request_validator.py     # Validações de request
└── utils/
    └── ip_utils.py              # Utilitários de IP (blacklist, etc)
```

### Implementação em Fases

#### **FASE 1: Estrutura Base (1 dia)**
- [ ] Criar `comum/middleware/api_security.py`
- [ ] Implementar logging básico de requisições
- [ ] Adicionar middleware em `settings.py`
- [ ] Testar em ambiente local
- [ ] Validar que não quebra nada

#### **FASE 2: Rate Limiting (1 dia)**
- [ ] Criar `comum/middleware/rate_limiter.py`
- [ ] Implementar cache de contadores por IP
- [ ] Configurar limites diferentes por path pattern
- [ ] Testar limites com múltiplas requisições
- [ ] Adicionar whitelist de IPs (servidores internos)

#### **FASE 3: Request Validation (0.5 dia)**
- [ ] Criar `comum/middleware/request_validator.py`
- [ ] Validar Content-Type para POSTs
- [ ] Validar tamanho do body
- [ ] Implementar blacklist de IPs
- [ ] Testar validações

#### **FASE 4: Integração com Decorators POSP2 (1 dia)**
- [ ] Aplicar decorators em endpoints POSP2
- [ ] Garantir compatibilidade middleware + decorators
- [ ] Testes de integração
- [ ] Monitorar logs em produção

#### **FASE 5: Deploy e Monitoramento (0.5 dia)**
- [ ] Deploy em produção
- [ ] Configurar alertas para rate limit atingido
- [ ] Monitorar performance
- [ ] Ajustar limites conforme necessário

### Configuração em Settings

```python
# wallclub/settings/base.py

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'comum.middleware.api_security.APISecurityMiddleware',  # ← Adicionar aqui
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Configurações do middleware
API_SECURITY = {
    'RATE_LIMITS': {
        '/api/v1/posp2/': 100,      # 100 req/min
        '/api/v1/cliente/': 50,      # 50 req/min
        '/api/v1/checkout/': 10,     # 10 req/min
    },
    'MAX_BODY_SIZE': 10 * 1024 * 1024,  # 10MB
    'WHITELIST_IPS': [
        '127.0.0.1',
        '192.168.0.0/16',  # Rede interna
    ],
    'BLACKLIST_IPS': [],
    'ENABLE_LOGGING': True,
    'LOG_FILE': 'api_security.log',
}
```

### Exemplo de Código

```python
# comum/middleware/api_security.py

import time
import json
from django.http import JsonResponse
from django.conf import settings
from comum.utilitarios.log_control import registrar_log
from .rate_limiter import RateLimiter
from .request_validator import RequestValidator


class APISecurityMiddleware:
    """
    Middleware para segurança e monitoramento de APIs públicas.
    Aplica rate limiting, validação e logging.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.rate_limiter = RateLimiter()
        self.validator = RequestValidator()
        self.config = getattr(settings, 'API_SECURITY', {})
    
    def __call__(self, request):
        # Aplicar apenas em APIs públicas
        if not self._is_api_endpoint(request.path):
            return self.get_response(request)
        
        start_time = time.time()
        client_ip = self._get_client_ip(request)
        
        # 1. Validação de request
        validation_error = self.validator.validate(request, client_ip)
        if validation_error:
            self._log_request(request, client_ip, 400, time.time() - start_time)
            return JsonResponse(validation_error, status=400)
        
        # 2. Rate limiting
        if not self.rate_limiter.allow_request(request.path, client_ip):
            self._log_request(request, client_ip, 429, time.time() - start_time)
            return JsonResponse({
                'sucesso': False,
                'mensagem': 'Muitas requisições. Tente novamente em alguns minutos.'
            }, status=429)
        
        # 3. Processar request
        response = self.get_response(request)
        
        # 4. Log de request/response
        duration = time.time() - start_time
        self._log_request(request, client_ip, response.status_code, duration)
        
        # 5. Adicionar security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        
        return response
    
    def _is_api_endpoint(self, path):
        """Verifica se é endpoint de API pública"""
        api_prefixes = ['/api/v1/posp2/', '/api/v1/cliente/', '/api/v1/checkout/']
        return any(path.startswith(prefix) for prefix in api_prefixes)
    
    def _get_client_ip(self, request):
        """Obtém IP real do cliente (considerando proxies)"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
    
    def _log_request(self, request, client_ip, status_code, duration):
        """Registra log da requisição"""
        if not self.config.get('ENABLE_LOGGING', True):
            return
        
        log_data = {
            'ip': client_ip,
            'method': request.method,
            'path': request.path,
            'status': status_code,
            'duration': f"{duration:.3f}s",
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:100]
        }
        
        registrar_log(
            'api_security',
            f"API Request: {log_data}",
            nivel='INFO' if status_code < 400 else 'WARNING'
        )
```

### Testes

```python
# tests/test_api_security_middleware.py

import pytest
from django.test import RequestFactory, override_settings
from comum.middleware.api_security import APISecurityMiddleware


class TestAPISecurityMiddleware:
    
    def test_rate_limiting(self):
        """Testa se rate limiting funciona"""
        factory = RequestFactory()
        middleware = APISecurityMiddleware(lambda r: None)
        
        # Fazer múltiplas requisições
        for i in range(101):
            request = factory.post('/api/v1/posp2/trdata')
            response = middleware(request)
            
            if i < 100:
                assert response.status_code != 429
            else:
                assert response.status_code == 429
    
    def test_request_validation(self):
        """Testa validação de requests"""
        factory = RequestFactory()
        middleware = APISecurityMiddleware(lambda r: None)
        
        # Request sem Content-Type
        request = factory.post('/api/v1/posp2/trdata', data='{}')
        response = middleware(request)
        assert response.status_code == 400
    
    def test_blacklist_ip(self):
        """Testa bloqueio de IPs na blacklist"""
        factory = RequestFactory()
        middleware = APISecurityMiddleware(lambda r: None)
        
        request = factory.post('/api/v1/posp2/trdata', REMOTE_ADDR='1.2.3.4')
        # Adicionar IP na blacklist
        middleware.validator.blacklist.add('1.2.3.4')
        
        response = middleware(request)
        assert response.status_code == 403
```

### Monitoramento

```bash
# Comandos para monitorar logs

# Ver requisições com rate limit atingido
docker exec wallclub-prod tail -f /app/logs/api_security.log | grep "429"

# Ver IPs mais ativos
docker exec wallclub-prod tail -1000 /app/logs/api_security.log | grep -oP 'ip: \K[^,]+' | sort | uniq -c | sort -rn | head -10

# Ver endpoints mais lentos
docker exec wallclub-prod tail -1000 /app/logs/api_security.log | grep -oP 'duration: \K[^s]+' | awk '{if($1>1.0)print}' | wc -l
```

---

## 📋 AÇÕES NECESSÁRIAS

### ✅ Checklist de Implementação

#### FASE 1: POSP2 (Prioridade ALTA - 1-2 dias)
- [ ] **Arquivo:** `posp2/views.py`
- [ ] Adicionar `@handle_api_errors` + `@validate_required_params` em `validar_senha_e_saldo`
- [ ] Adicionar decorators em `solicitar_autorizacao_saldo`
- [ ] Adicionar decorators em `verificar_autorizacao`
- [ ] Adicionar decorators em `simula_parcelas`
- [ ] Adicionar apenas `@handle_api_errors` em `trdata` (validação customizada)
- [ ] Remover blocos try/except manuais
- [ ] Remover validações manuais de parâmetros
- [ ] Testar todos endpoints POSP2
- [ ] Validar logs de erro

**Riscos:** BAIXO - Endpoints externos já estáveis  
**Impacto:** Redução de ~50 linhas de código repetitivo

#### FASE 2: Checkout Link Pagamento (Prioridade MÉDIA - 1 dia)
- [ ] **Arquivo:** `checkout/link_pagamento_web/views.py`
- [ ] Identificar views Django puras (não DRF)
- [ ] Adicionar decorators em views de geração de token
- [ ] Adicionar decorators em simulação de parcelas
- [ ] Adicionar decorators em processamento (se não DRF)
- [ ] Testar fluxo completo de checkout
- [ ] Validar tratamento de erros

**Riscos:** MÉDIO - Fluxo crítico de pagamento  
**Impacto:** Padronização de erros em checkout

#### FASE 3: Análise Portais AJAX (Prioridade BAIXA - 0.5 dia)
- [ ] Listar todos endpoints AJAX em `portais/lojista/views.py`
- [ ] Listar todos endpoints AJAX em `portais/admin/views.py`
- [ ] Verificar quais retornam `JsonResponse`
- [ ] Verificar quais são Django puro vs DRF
- [ ] Criar lista de candidatos
- [ ] Decidir aplicação caso a caso

**Riscos:** BAIXO - Análise apenas  
**Impacto:** Identificação de oportunidades

---

## 🎯 Critérios de Sucesso

### Código Refatorado Deve:
1. ✅ Não ter blocos try/except para JSONDecodeError
2. ✅ Não ter validações manuais de parâmetros obrigatórios
3. ✅ Ter logs automáticos de erros
4. ✅ Retornar status codes consistentes (400, 500)
5. ✅ Passar em todos testes existentes

### Testes Necessários:
1. ✅ Enviar JSON inválido → deve retornar 400
2. ✅ Omitir parâmetro obrigatório → deve retornar 400 com lista
3. ✅ Forçar exception → deve retornar 500 e logar
4. ✅ Request válido → deve funcionar normalmente

---

## 📊 Métricas de Progresso

**Status Final (2025-10-17):**
- ✅ POSP2: 13/13 endpoints refatorados (100%)
- ❌ Checkout: Não aplicável (usa DRF)
- ✅ Portais: 5/5 endpoints refatorados (100%)
- ✅ Middleware: APISecurityMiddleware implementado (100%)

**Resultado:**
- ✅ **18 endpoints refatorados:** POSP2 + Portais AJAX
- ✅ **~130 linhas removidas:** Código significativamente mais limpo
- ✅ **Tratamento padronizado:** Erros consistentes em toda aplicação
- ✅ **Logs automáticos:** Rastreamento completo de exceções
- ✅ **Middleware global:** Protege todas APIs
- ✅ **Rate limiting ativo:** 100 req/min por IP

**Conclusão:**
- Fases 1 e 3 completas com sucesso
- Fase 2 não aplicável (DRF)
- Sistema robusto e padronizado

---

## ⚠️ Observações Importantes

### NÃO Aplicar Decorators Em:
1. **Views DRF** com `@api_view` - já têm tratamento próprio
2. **Views com serializers DRF** - usar validação do serializer
3. **Views que retornam templates** - não são APIs
4. **Views com validação complexa** - manter customizada, usar só `@handle_api_errors`

### Cuidados Especiais:
1. **OAuth decorators** devem vir ANTES dos novos decorators
2. **CSRF exempt** deve ser sempre primeiro
3. **Testar em ambiente local** antes de deploy
4. **Validar logs** após implementação
5. **Documentar mudanças** em changelog

---

**Documento atualizado em:** 2025-10-17  
**Status:** ✅ CONCLUÍDO - Fase 1 implementada na Fase 1 do projeto (Semanas 5-6)  
**Referência:** `ROTEIRO_MESTRE_SEQUENCIAL.md` + `RESUMO_FASE_1_A_3.md`
