# CENÁRIO DE EVOLUÇÃO ARQUITETURAL - WALLCLUB FINTECH

**Data da Análise:** 09/01/2026
**Arquiteto Responsável:** Análise Técnica Sênior
**Versão do Sistema:** 6.1 (Fase 7 - 95% concluída)
**Validade:** 12 meses (revisão trimestral)

---

## 📋 SUMÁRIO EXECUTIVO

Sistema fintech Django em produção desde outubro/2025, processando transações financeiras com 9 containers orquestrados.

**Arquitetura atual:** Boa separação de responsabilidades mas com acoplamento ao banco de dados que limita evolução para microserviços verdadeiros.

**Kubernetes:** ✅ Viável com refatorações incrementais (6-9 meses)
**Microserviços:** ⚠️ Requerem redesenho significativo da camada de dados (18-36 meses)

### Pontuação Geral: 7.5/10

| Aspecto | Pontuação | Status |
|---------|-----------|--------|
| Segurança | 7/10 | Boa base, gaps críticos identificados |
| Reuso e Modularização | 8/10 | Excelente package core, calculadoras centralizadas |
| Consistência do Desenho | 7/10 | Padrões bem definidos, exceções não documentadas |
| Preparação Kubernetes | 8/10 | Arquitetura favorável, ajustes incrementais |
| Preparação Microserviços | 5/10 | Bloqueadores críticos no banco de dados |

---

## 📑 ÍNDICE

1. [Análise de Segurança](#1-análise-de-segurança)
2. [Reuso e Modularização](#2-reuso-e-modularização)
3. [Consistência do Desenho](#3-consistência-do-desenho)
4. [Roadmap Kubernetes](#4-roadmap-kubernetes)
5. [Roadmap Microserviços](#5-roadmap-microserviços)
6. [Métricas de Sucesso](#6-métricas-de-sucesso)
7. [Recomendações Prioritárias](#7-recomendações-prioritárias)

---

## 1. ANÁLISE DE SEGURANÇA

### 1.1 Pontos Fortes ✅

- **JWT customizado** com validação obrigatória contra BD
- **OAuth 2.0** com contextos separados (admin, pos, internal)
- **Rate limiting progressivo:** 5/15min → 10/1h → 20/24h
- **AWS Secrets Manager** centralizado (zero credenciais hardcoded)
- **Antifraude <200ms** com 9 regras configuráveis
- **MaxMind minFraud** com cache 1h (hit rate >90%)

### 1.2 Vulnerabilidades Críticas 🚨

#### ✅ IMPLEMENTADO - Rate Limiting em Endpoints POS (16/01/2026)

**Status:** ✅ Implementado com defesa em profundidade (dupla camada)

**Arquitetura Implementada:**
- **Camada 1 (Middleware):** Rate limiting por IP em todos endpoints `/api/*`
- **Camada 2 (Decorator POS):** Rate limiting adicional por `terminal_id`

**Justificativa da dupla camada:**
- POS: Múltiplos terminais compartilham mesmo token OAuth
- Terminal comprometido não pode afetar outros terminais da mesma loja
- Outras APIs (Mobile, Checkout) não precisam dessa camada adicional

**Endpoints protegidos:**
- `/api/v1/posp2/valida_cpf/` - 50 req/min por terminal
- `/api/v1/posp2/solicitar_autorizacao_saldo/` - 30 req/min por terminal (critical)
- `/api/v1/posp2/verificar_autorizacao/` - 50 req/min por terminal
- `/api/v1/posp2/trdata/` e `/trdata_own/` - 30 req/min por terminal (critical)
- `/api/v1/cupons/validar/` - 30 req/min por terminal (critical)

**Implementação:**
1. ✅ Configuração em `settings.API_RATE_LIMITS`
2. ✅ Decorator `@require_pos_rate_limit()` criado
3. ✅ Auditoria de atividades suspeitas
4. ✅ Alertas automáticos após 10 atividades suspeitas/dia
5. ✅ Bloqueio temporário automático

---

#### 🚨 CRÍTICO - Webhooks Own Financial (Pendente)

**Problema:** Webhooks da Own Financial (`/webhook/*`) não possuem validação de origem.

**Risco:** Alto - Dados falsos podem ser inseridos no sistema
**Prioridade:** 🔴 ALTA
**Esforço:** 4-8 horas (após resposta da Own)

**Ação Necessária:**
1. Solicitar à Own Financial: Lista de IPs de origem dos webhooks
2. Implementar IP whitelist ou validação de assinatura

**Referência:** `/docs/PENDENCIAS_SEGURANCA.md`

---

#### ✅ IMPLEMENTADO - Gerenciamento de Cartões Tokenizados (16/01/2026)

**Status:** ✅ Implementado completo (backend + frontend)

**Implementação:**
1. ✅ APIs REST criadas (`/api/v1/checkout/cartoes/`)
   - GET `/{cpf}/` - Listar cartões do cliente
   - POST `/{cartao_id}/invalidar/` - Invalidar cartão
   - POST `/{cartao_id}/reativar/` - Reativar cartão
2. ✅ Service `CartaoTokenizadoService.invalidar_cartao()` melhorado
   - Aceita motivo e usuario_id
   - Registra timestamp e auditoria completa
3. ✅ Interface Portal Vendas implementada
   - Página `/portal_vendas/cliente/{id}/cartoes/`
   - Modal de confirmação com seleção de motivo
   - Histórico de invalidações visível
4. ✅ Model já possuía todos os campos necessários
   - `tentativas_falhas_consecutivas`
   - `motivo_invalidacao`
   - `invalidado_por`, `invalidado_em`

**Funcionalidades:**
- Listar todos os cartões (ativos e invalidados)
- Invalidar cartão com motivo obrigatório
- Visualizar histórico de invalidações
- Auditoria completa de ações

---

#### MÉDIO - 2FA Incompleto

**Situação:**
- ✅ Checkout Web: 2FA completo
- ❌ App Mobile: Sem 2FA no login
- ❌ Revalidação celular: Não implementada (90 dias)

**Prioridade:** 🟡 MÉDIA
**Esforço:** 12 horas (8h 2FA + 4h revalidação)

**Gatilhos 2FA Obrigatórios:**
- Login de novo dispositivo
- Transação > R$ 100,00
- Alteração de dados sensíveis
- Dispositivo confiável expirado (>30 dias)

---

### 1.3 Resumo de Segurança

**Pontuação:** 8/10 (atualizada em 16/01/2026)

**Implementações Concluídas (16/01/2026):**
1. ✅ Rate limiting endpoints POS (4h) - Completo
2. ✅ Gerenciamento cartões tokenizados (12h) - Completo
3. 🔴 Webhooks Own Financial - Pendente (aguardando Own)

**Pendências:**
1. 🟡 2FA app móvel (8h) - Adiado
2. 🔴 Validação webhooks Own (4-8h) - Aguardando informações da Own

**Total Implementado:** 16 horas de 24 horas (67%)
**Total Pendente:** 8-16 horas

---

## 2. REUSO E MODULARIZAÇÃO

### 2.1 Pontos Fortes ✅

#### Package `wallclub_core` (52 arquivos)
- Zero duplicação entre containers
- Instalação via pip: `wallclub_core @ file:///../core`
- Estrutura: database, integracoes, middleware, oauth, seguranca, services

#### 26 APIs REST Internas
- Cliente: 6 endpoints
- Conta Digital: 5 endpoints
- Checkout: 8 endpoints
- Ofertas: 6 endpoints
- Parâmetros: 7 endpoints

#### 22 Services Criados
- Eliminação de 25 queries diretas em views
- Exemplo: `posp2/services.py` (2440 linhas) → 4 arquivos (redução 46%)

### 2.2 Oportunidades de Melhoria 🔄

#### Calculadoras Centralizadas (Ponto Único de Falha)

**Problema:**
```python
# CalculadoraBaseUnificada: 1178 linhas
# - Lógica crítica em um único ponto
# - Difícil distribuir em microserviços
# - Deploy requer rebuild de todos containers
```

**Recomendação:** Extrair para serviço dedicado com API REST
**Esforço:** 40 horas
**Benefícios:** Escalabilidade independente, deploy isolado

---

#### Lazy Imports (17 arquivos)

**Problema:**
```python
# apps.get_model() funciona em monolito
# Quebra em microserviços verdadeiros
```

**Recomendação:** Substituir por APIs REST
**Esforço:** 16 horas

---

#### Sistema de Notificações

**Problema:** Lógica espalhada sem orquestrador unificado

**Recomendação:** `NotificationOrchestrator` com retry/fallback
**Esforço:** 12 horas
**Benefícios:** Candidato a microserviço (baixo acoplamento)

---

### 2.3 Resumo de Reuso

**Pontuação:** 8/10

**Prioridades:**
1. 🟠 Extrair Calculadoras (40h)
2. 🟡 NotificationOrchestrator (12h)
3. 🟡 Substituir lazy imports (16h)

**Total Esforço:** 68 horas (~2 semanas)

---

## 3. CONSISTÊNCIA DO DESENHO

### 3.1 Padrões Bem Definidos ✅

**Comunicação Inter-Containers:**
- 70% APIs REST (padrão)
- 25% SQL direto read-only (performance)
- 5% Lazy imports (entidades compartilhadas)

**Formato API:** `{"sucesso": bool, "mensagem": str, "dados": {...}}`
**Regra:** SEMPRE POST (nunca GET/PUT/DELETE)

### 3.2 Inconsistências Identificadas ⚠️

#### Timezone Híbrido
- Padrão: `datetime.now()`
- Exceção: `timezone.now()` em CashbackService (não documentado)

**Recomendação:** Documentar exceções explicitamente
**Esforço:** 1 hora

---

#### Duplicação de Models de Transação
- TransactionData (Pinbank) - antiga
- TransactionDataOwn (Own) - nova
- transactiondata_pos - unificada (em migração)

**Recomendação:** Finalizar migração e deprecar tabelas antigas
**Esforço:** 24 horas

---

### 3.3 Resumo de Consistência

**Pontuação:** 7/10

**Prioridades:**
1. 🟡 Finalizar migração transactiondata_pos (24h)
2. 🟢 Documentar exceção timezone (1h)

**Total Esforço:** 25 horas

---

## 4. ROADMAP KUBERNETES

### 4.1 Análise de Viabilidade

**Status:** ✅ **VIÁVEL COM REFATORAÇÕES INCREMENTAIS**

Arquitetura atual com 9 containers Docker Compose é excelente ponto de partida.

**Benefícios Esperados:**
- Escalabilidade horizontal automática (HPA)
- Alta disponibilidade (multi-AZ)
- Rolling updates sem downtime
- Self-healing (restart automático)
- Service discovery nativo

---

### 4.2 Roadmap Detalhado (6-9 meses)

#### FASE 1: Preparação (2 meses - 60 horas)

**1.1 Stateless vs Stateful**
- ✅ Stateless: portais, pos, apis, riskengine (podem escalar)
- ⚠️ Stateful: redis (StatefulSet ou ElastiCache)
- ⚠️ Singleton: celery-beat (leader election)

**1.2 Health Checks (8 horas)**
```python
/health/live/    # Liveness probe
/health/ready/   # Readiness probe
/health/startup/ # Startup probe
```

**1.3 Configuração Externalizada (16 horas)**
- ConfigMaps para variáveis não-sensíveis
- External Secrets Operator para AWS Secrets Manager

**1.4 Migrar Arquivos para S3 (12 horas)**
- Django Storages + boto3
- CloudFront (CDN opcional)
- Custo: ~R$ 50-100/mês

---

#### FASE 2: Migração Básica (2 meses - 48 horas)

**2.1 Deployments (24 horas)**
- Criar manifests para todos containers
- Anti-affinity (não colocar 2 pods no mesmo node)
- Resources requests/limits

**2.2 Services (8 horas)**
- Service discovery nativo
- Atualizar URLs: `http://wallclub-apis-service`

**2.3 Ingress Controller (16 horas)**
- Substituir Nginx gateway
- Cert-manager para SSL automático
- 14 subdomínios configurados

---

#### FASE 3: Otimização (2-3 meses - 52 horas)

**3.1 Redis Cluster (16 horas)**
- StatefulSet com 6 nós (3 masters + 3 replicas)
- Alternativa: AWS ElastiCache (~R$ 200-400/mês)

**3.2 HPA (8 horas)**
- Escalar baseado em CPU/Memória
- APIs: min 4, max 15 réplicas

**3.3 MySQL RDS Multi-AZ (24 horas)**
- Alta disponibilidade automática
- Backups automáticos
- Custo: ~R$ 2.500/mês

**3.4 Celery Beat Leader Election (4 horas)**
- Garantir singleton (evitar duplicação de tasks)

---

### 4.3 Estimativa Total

| Fase | Duração | Esforço | Risco |
|------|---------|---------|-------|
| Preparação | 2 meses | 60h | Baixo |
| Migração Básica | 2 meses | 48h | Médio |
| Otimização | 2-3 meses | 52h | Médio |
| **TOTAL** | **6-7 meses** | **160h** | - |

**Custo Adicional Mensal:** ~R$ 2.800 (S3 + ElastiCache + RDS)

### 4.4 Pontuação: 8/10

**Justificativa:** Arquitetura bem preparada. Principais desafios são operacionais, não arquiteturais.

---

## 5. ROADMAP MICROSERVIÇOS

### 5.1 Análise de Viabilidade

**Status:** ⚠️ **VIÁVEL MAS REQUER REDESENHO SIGNIFICATIVO**

Arquitetura atual é **monolito modular bem estruturado**, não microserviços verdadeiros.

### 5.2 Bloqueadores Críticos

**1. Banco de Dados Compartilhado**
```
MySQL Único (200+ tabelas)
❌ Todos containers têm acesso total
❌ Transações ACID cross-container
❌ Schema coupling
```

**2. Transações Distribuídas**
```python
# Atualmente: 1 transação ACID
with transaction.atomic():
    MovimentacaoConta.objects.create(...)  # APIs
    TransactionData.objects.create(...)     # POS

# Em microserviços: Requer Saga Pattern
```

**3. Lazy Imports (17 arquivos)**
```python
Terminal = apps.get_model('posp2', 'Terminal')
# Quebra em microserviços
```

**4. Calculadoras Centralizadas**
```python
# 1178 linhas de lógica crítica
# Ponto único de falha
```

---

### 5.3 Candidatos a Extração (Ordem de Prioridade)

#### NÍVEL 1: Baixo Acoplamento (3-6 meses cada)

**1. Sistema de Notificações** ⭐ RECOMENDADO
- Zero dependência de BD transacional
- Comunicação via eventos (Kafka/SQS)
- Escalabilidade independente
- **Esforço:** 3 meses | **Risco:** Baixo

**2. Sistema Antifraude** (já 80% isolado)
- BD próprio (tabelas antifraude)
- APIs REST já implementadas
- **Esforço:** 2 meses | **Risco:** Baixo

**3. Sistema de Ofertas**
- 5 tabelas isoladas
- Push notifications (delegar para Notificações)
- **Esforço:** 4 meses | **Risco:** Médio

---

#### NÍVEL 2: Acoplamento Moderado (6-12 meses cada)

**4. Autenticação/2FA**
- Usado por TODOS os containers
- Latência crítica (<50ms)
- **Esforço:** 9 meses | **Risco:** Alto

**5. Sistema de Cashback**
- Transações distribuídas (débito + crédito)
- Consistência eventual vs ACID
- **Esforço:** 8 meses | **Risco:** Alto

---

#### NÍVEL 3: Alto Acoplamento (12+ meses)

**6. Parâmetros Financeiros**
- 3.840 configurações
- Usado por TODOS os containers
- **Esforço:** 12+ meses | **Risco:** Muito Alto

---

### 5.4 Estratégia de Dados

**Opção 1: Database per Service** (Recomendado)
```
Notificações Service → PostgreSQL (3 tabelas)
Antifraude Service → PostgreSQL (8 tabelas)
Ofertas Service → PostgreSQL (5 tabelas)
Core Monolith → MySQL (180+ tabelas)
```

**Opção 2: Shared Database** (Transição)
```
MySQL Único com schemas isolados
- Schema notificacoes
- Schema antifraude
- Schema ofertas
- Schema core
```

---

### 5.5 Padrões Arquiteturais

**Event-Driven (Recomendado)**
- Kafka ou AWS SQS/SNS
- Consistência eventual
- Desacoplamento temporal

**Saga Pattern**
```python
# Transação distribuída
1. Débito conta (APIs) → Sucesso
2. Insert transação (POS) → Falha
3. Compensação: Estorno débito (APIs)
```

**CQRS**
- Command: escrita otimizada
- Query: leitura otimizada (cache, denormalização)

---

### 5.6 Estimativa Total

| Nível | Serviços | Duração | Esforço | Risco |
|-------|----------|---------|---------|-------|
| Nível 1 | 3 serviços | 9 meses | 720h | Baixo-Médio |
| Nível 2 | 2 serviços | 17 meses | 1360h | Alto |
| Nível 3 | 1 serviço | 12+ meses | 960h | Muito Alto |
| **TOTAL** | **6 serviços** | **38 meses** | **3040h** | - |

**Recomendação:** Começar com Nível 1 (Notificações) como prova de conceito.

### 5.7 Pontuação: 5/10

**Justificativa:** Bloqueadores críticos no banco de dados. Viável mas requer redesenho significativo.

---

## 6. MÉTRICAS DE SUCESSO

### 6.1 Kubernetes

**Performance:**
- Latência P95 < 200ms (mantida)
- Disponibilidade > 99.9% (SLA)
- MTTR < 5min (self-healing)

**Escalabilidade:**
- HPA funcional (escala em <2min)
- Suporta 3x carga atual sem degradação

**Operacional:**
- Deploy frequency: 2x/semana (vs 1x/mês atual)
- Lead time: <30min (vs 2h atual)
- Zero downtime em 100% dos deploys

---

### 6.2 Microserviços

**Desacoplamento:**
- Zero queries SQL cross-service
- Comunicação 100% via APIs/Eventos
- Deploy independente (sem rebuild de outros serviços)

**Resiliência:**
- Falha de 1 serviço não afeta outros
- Circuit breaker ativo
- Retry com backoff exponencial

**Performance:**
- Latência mantida (<200ms P95)
- Throughput aumentado em 50%

---

## 7. RECOMENDAÇÕES PRIORITÁRIAS

### 7.1 Curto Prazo (1-3 meses)

**Segurança - CRÍTICO**
1. 🔴 Rate limiting validação senha (8h)
2. 🟠 Gerenciamento cartões tokenizados (12h)
3. 🟡 2FA app móvel (12h)

**Arquitetura**
4. 🟠 Extrair Calculadoras para serviço (40h)
5. 🟡 Finalizar migração transactiondata_pos (24h)

**Total:** 96 horas (~2 semanas)

---

### 7.2 Médio Prazo (3-9 meses)

**Kubernetes - Fases 1-3**
1. Preparação (60h)
2. Migração Básica (48h)
3. Otimização (52h)

**Arquitetura**
4. NotificationOrchestrator (12h)
5. Sistema Auditoria unificado (20h)

**Total:** 192 horas (~5 semanas) + custo mensal R$ 2.800

---

### 7.3 Longo Prazo (9-36 meses)

**Microserviços - Nível 1**
1. Notificações Service (3 meses)
2. Antifraude Service (2 meses)
3. Ofertas Service (4 meses)

**Total:** 9 meses (~720 horas)

---

## 8. ASPECTOS OPERACIONAIS CRÍTICOS

### 8.1 Integrações e Middleware

#### Situação Atual

**Middleware Implementado:**
```python
# wallclub_core/middleware/
├── security_middleware.py      # Segurança HTTP
├── security_validation.py      # Validações (Risk Engine)
├── session_timeout.py          # Timeout de sessão
└── subdomain_router.py         # Roteamento por domínio
```

**Análise:**
- ✅ **SubdomainRouterMiddleware:** Funcional, roteia 14 subdomínios corretamente
- ✅ **SecurityValidationMiddleware:** Integra com Risk Engine (fail-open)
- ⚠️ **Sem middleware de logging unificado** para rastreabilidade
- ⚠️ **Sem middleware de correlação de requisições** (correlation-id)
- ⚠️ **Sem middleware de rate limiting global** (apenas por endpoint)

#### Problemas Identificados

**1. Rastreabilidade Cross-Container**
```python
# Problema: Impossível rastrear requisição entre containers
# Requisição: Cliente → APIs → POS → APIs
# Logs separados sem correlação
```

**2. Integrações Externas Sem Circuit Breaker**
```python
# Pinbank, Own, MaxMind, WhatsApp, SMS
# ❌ Sem proteção contra falhas em cascata
# ❌ Sem retry inteligente
# ❌ Sem fallback automático
```

**3. Timeout Inconsistente**
```python
# APIs internas: 5s, 10s, 30s (configurável)
# APIs externas: 3s, 60s, >60s (inconsistente)
# ❌ Sem timeout global padrão
```

#### Recomendações

**1. Correlation ID Middleware (8 horas)**
```python
# wallclub_core/middleware/correlation_middleware.py
import uuid
from django.utils.deprecation import MiddlewareMixin

class CorrelationIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Pegar do header ou gerar novo
        correlation_id = request.META.get('HTTP_X_CORRELATION_ID') or str(uuid.uuid4())
        request.correlation_id = correlation_id

        # Adicionar a todos os logs
        import logging
        logger = logging.getLogger()
        logger.addFilter(lambda record: setattr(record, 'correlation_id', correlation_id) or True)

        return None

    def process_response(self, request, response):
        # Retornar no header
        if hasattr(request, 'correlation_id'):
            response['X-Correlation-ID'] = request.correlation_id
        return response
```

**Benefícios:**
- ✅ Rastreabilidade completa cross-container
- ✅ Troubleshooting facilitado
- ✅ Logs correlacionados

---

**2. Circuit Breaker Pattern (16 horas)**
```python
# wallclub_core/integracoes/circuit_breaker.py
from datetime import datetime, timedelta
from django.core.cache import cache

class CircuitBreaker:
    def __init__(self, service_name, failure_threshold=5, timeout=60):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.cache_key = f'circuit_breaker:{service_name}'

    def call(self, func, *args, **kwargs):
        # Verificar estado do circuit
        state = cache.get(self.cache_key, {'state': 'CLOSED', 'failures': 0})

        if state['state'] == 'OPEN':
            # Circuit aberto, verificar timeout
            if datetime.now() < state['open_until']:
                raise CircuitBreakerOpenError(f'{self.service_name} circuit is OPEN')
            else:
                # Tentar half-open
                state['state'] = 'HALF_OPEN'

        try:
            result = func(*args, **kwargs)

            # Sucesso, fechar circuit
            if state['state'] == 'HALF_OPEN':
                state = {'state': 'CLOSED', 'failures': 0}
                cache.set(self.cache_key, state, 3600)

            return result

        except Exception as e:
            # Falha, incrementar contador
            state['failures'] += 1

            if state['failures'] >= self.failure_threshold:
                # Abrir circuit
                state['state'] = 'OPEN'
                state['open_until'] = datetime.now() + timedelta(seconds=self.timeout)

                # Alertar
                self._send_alert(f'{self.service_name} circuit OPENED')

            cache.set(self.cache_key, state, 3600)
            raise

# Uso:
pinbank_circuit = CircuitBreaker('pinbank', failure_threshold=5, timeout=60)
result = pinbank_circuit.call(PinbankService.efetuar_transacao, dados)
```

**Aplicar em:**
- Pinbank (transações, cargas)
- Own Financial (transações, webhooks)
- MaxMind minFraud
- WhatsApp Business API
- SMS Gateway
- AWS SES

---

**3. Request Logging Middleware (4 horas)**
```python
# wallclub_core/middleware/request_logging_middleware.py
import time
import logging

logger = logging.getLogger('requests')

class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Início
        start_time = time.time()

        # Log request
        logger.info(
            f"Request started",
            extra={
                'correlation_id': getattr(request, 'correlation_id', None),
                'method': request.method,
                'path': request.path,
                'ip': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT'),
            }
        )

        # Processar
        response = self.get_response(request)

        # Log response
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                'correlation_id': getattr(request, 'correlation_id', None),
                'status_code': response.status_code,
                'duration_ms': round(duration * 1000, 2),
            }
        )

        return response
```

---

**Resumo Integrações:**
- **Pontuação Atual:** 6/10
- **Esforço Total:** 28 horas
- **Prioridade:** 🟠 Alta

---

### 8.2 Monitoramento de Interfaces e Integrações

#### Situação Atual

**Monitoramento Existente:**
- ✅ Flower (Celery tasks) - flower.wallclub.com.br
- ⚠️ Logs em arquivos (sem agregação)
- ❌ Sem métricas de APIs internas
- ❌ Sem métricas de integrações externas
- ❌ Sem alertas automáticos
- ❌ Sem dashboards de negócio

#### Gaps Críticos

**1. APIs Internas (26 endpoints)**
```python
# Sem visibilidade:
# - Latência por endpoint
# - Taxa de erro
# - Throughput
# - Dependências entre containers
```

**2. Integrações Externas**
```python
# Pinbank, Own, MaxMind, WhatsApp, SMS
# - Sem SLA tracking
# - Sem alertas de degradação
# - Sem métricas de custo (APIs pagas)
```

**3. Transações Financeiras**
```python
# Sem monitoramento:
# - Taxa de aprovação/reprovação
# - Valor médio por gateway
# - Latência end-to-end
# - Falhas por etapa
```

#### Recomendações

**FASE 1: Prometheus + Grafana (40 horas)**

**1.1 Instrumentação Django (16 horas)**
```python
# requirements.txt
django-prometheus==2.3.1
prometheus-client==0.19.0

# settings.py
INSTALLED_APPS = [
    'django_prometheus',
    ...
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Métricas customizadas
from prometheus_client import Counter, Histogram, Gauge

# APIs Internas
api_interna_requests = Counter(
    'wallclub_api_interna_requests_total',
    'Total de requisições APIs internas',
    ['container_origem', 'container_destino', 'endpoint', 'status']
)

api_interna_latency = Histogram(
    'wallclub_api_interna_latency_seconds',
    'Latência APIs internas',
    ['container_origem', 'container_destino', 'endpoint']
)

# Integrações Externas
integracao_externa_requests = Counter(
    'wallclub_integracao_externa_requests_total',
    'Total de requisições integrações externas',
    ['servico', 'operacao', 'status']
)

integracao_externa_latency = Histogram(
    'wallclub_integracao_externa_latency_seconds',
    'Latência integrações externas',
    ['servico', 'operacao']
)

# Transações Financeiras
transacoes_total = Counter(
    'wallclub_transacoes_total',
    'Total de transações',
    ['gateway', 'tipo', 'status']
)

transacoes_valor = Histogram(
    'wallclub_transacoes_valor_reais',
    'Valor das transações em reais',
    ['gateway', 'tipo']
)

# Circuit Breaker
circuit_breaker_state = Gauge(
    'wallclub_circuit_breaker_state',
    'Estado do circuit breaker (0=CLOSED, 1=HALF_OPEN, 2=OPEN)',
    ['servico']
)
```

**1.2 Prometheus Server (8 horas)**
```yaml
# k8s/prometheus/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        args:
        - '--config.file=/etc/prometheus/prometheus.yml'
        - '--storage.tsdb.retention.time=30d'
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config
          mountPath: /etc/prometheus
        - name: data
          mountPath: /prometheus
      volumes:
      - name: config
        configMap:
          name: prometheus-config
      - name: data
        persistentVolumeClaim:
          claimName: prometheus-data

---
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
- job_name: 'wallclub-portais'
  static_configs:
  - targets: ['wallclub-portais-service:80']
  metrics_path: '/metrics'

- job_name: 'wallclub-pos'
  static_configs:
  - targets: ['wallclub-pos-service:80']

- job_name: 'wallclub-apis'
  static_configs:
  - targets: ['wallclub-apis-service:80']

- job_name: 'wallclub-riskengine'
  static_configs:
  - targets: ['wallclub-riskengine-service:80']
```

**1.3 Grafana Dashboards (16 horas)**

**Dashboard 1: APIs Internas**
- Latência P50/P95/P99 por endpoint
- Taxa de erro por container
- Throughput (req/s)
- Mapa de dependências

**Dashboard 2: Integrações Externas**
- SLA tracking (disponibilidade %)
- Latência por serviço
- Taxa de erro
- Circuit breaker status
- Custo estimado (APIs pagas)

**Dashboard 3: Transações Financeiras**
- Taxa de aprovação (%)
- Valor transacionado (R$/hora)
- Latência end-to-end
- Falhas por gateway
- Top motivos de recusa

**Dashboard 4: Infraestrutura**
- CPU/Memória por container
- Pods ativos/reiniciando
- Redis hit rate
- MySQL connections/slow queries

---

**FASE 2: ELK Stack (48 horas)**

**2.1 Elasticsearch (16 horas)**
```yaml
# Logs centralizados
# - Todos containers enviam logs
# - Retenção: 30 dias
# - Índices por dia
```

**2.2 Logstash (16 horas)**
```ruby
# Pipeline de processamento
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse JSON logs
  json {
    source => "message"
  }

  # Adicionar geolocalização (IP)
  geoip {
    source => "ip_address"
  }

  # Enriquecer com dados
  if [correlation_id] {
    # Buscar outros logs da mesma requisição
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "wallclub-logs-%{+YYYY.MM.dd}"
  }
}
```

**2.3 Kibana (16 horas)**
- Dashboards de logs
- Alertas customizados
- Pesquisa por correlation_id
- Análise de erros

---

**FASE 3: Alertas (24 horas)**

**3.1 Alertmanager (Prometheus)**
```yaml
# Alertas críticos
groups:
- name: wallclub_alerts
  rules:
  # API Interna com alta latência
  - alert: APIInternaLatenciaAlta
    expr: histogram_quantile(0.95, wallclub_api_interna_latency_seconds) > 0.5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "API interna com latência P95 > 500ms"

  # Integração externa falhando
  - alert: IntegracaoExternaFalhando
    expr: rate(wallclub_integracao_externa_requests_total{status="error"}[5m]) > 0.1
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Integração {{ $labels.servico }} com taxa de erro > 10%"

  # Circuit breaker aberto
  - alert: CircuitBreakerAberto
    expr: wallclub_circuit_breaker_state == 2
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Circuit breaker {{ $labels.servico }} ABERTO"

  # Taxa de aprovação baixa
  - alert: TaxaAprovacaoBaixa
    expr: rate(wallclub_transacoes_total{status="aprovado"}[10m]) / rate(wallclub_transacoes_total[10m]) < 0.7
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Taxa de aprovação < 70%"
```

**3.2 Canais de Notificação**
- Slack: alertas em tempo real
- Email: resumo diário + alertas críticos
- PagerDuty: on-call (opcional)

---

**Resumo Monitoramento:**
- **Pontuação Atual:** 3/10
- **Esforço Total:** 112 horas (~3 semanas)
- **Custo Adicional:** ~R$ 500/mês (Elasticsearch, Prometheus storage)
- **Prioridade:** 🔴 CRÍTICA

---

### 8.3 Testes Automatizados

#### Situação Atual

**Cobertura Atual:** ~5% (estimado)
- ❌ Sem testes unitários sistemáticos
- ❌ Sem testes de integração
- ❌ Sem testes end-to-end
- ❌ Sem testes de carga
- ✅ Testes manuais via curl (18 cenários JWT)

#### Gaps Críticos

**1. Lógica Financeira Sem Testes**
```python
# Calculadoras (1178 linhas)
# ❌ Zero testes automatizados
# Risco: Bug pode causar prejuízo financeiro
```

**2. APIs Sem Contrato**
```python
# 26 APIs internas
# ❌ Sem testes de contrato
# Risco: Breaking changes não detectados
```

**3. Integrações Sem Mock**
```python
# Pinbank, Own, MaxMind
# ❌ Testes dependem de ambiente externo
# Risco: Testes instáveis, custo de APIs
```

#### Recomendações

**FASE 1: Testes Unitários (80 horas)**

**1.1 Services Críticos (40 horas)**
```python
# tests/services/test_calculadora_base.py
import pytest
from decimal import Decimal
from parametros_wallclub.services import CalculadoraBaseUnificada

class TestCalculadoraBaseUnificada:
    @pytest.fixture
    def calculadora(self):
        return CalculadoraBaseUnificada()

    @pytest.fixture
    def dados_transacao(self):
        return {
            'valor': Decimal('100.00'),
            'parcelas': 1,
            'modalidade': 'DEBITO',
            # ... outros campos
        }

    @pytest.fixture
    def info_loja(self):
        return {
            'id': 1,
            'loja': 'Loja Teste',
            # ... outros campos
        }

    def test_calcular_valores_primarios_debito(self, calculadora, dados_transacao, info_loja):
        """Testa cálculo de débito à vista"""
        resultado = calculadora.calcular_valores_primarios(
            dados_linha=dados_transacao,
            tabela='transactiondata_pos',
            info_loja=info_loja,
            info_canal={'canal': 1}
        )

        # Assertions
        assert resultado[0] == Decimal('100.00')  # Valor bruto
        assert resultado[14] >= 0  # Desconto Wall
        assert resultado[19] > 0  # Valor líquido loja

    def test_calcular_valores_primarios_credito_parcelado(self, calculadora, dados_transacao, info_loja):
        """Testa cálculo de crédito parcelado"""
        dados_transacao['modalidade'] = 'CREDITO'
        dados_transacao['parcelas'] = 3

        resultado = calculadora.calcular_valores_primarios(
            dados_linha=dados_transacao,
            tabela='transactiondata_pos',
            info_loja=info_loja,
            info_canal={'canal': 1}
        )

        # Assertions
        assert resultado[20] == Decimal('33.33')  # Valor parcela (arredondado)
        assert resultado[14] >= 0  # Desconto Wall

    @pytest.mark.parametrize("modalidade,parcelas,esperado_tipo", [
        ('DEBITO', 1, 'DEBITO'),
        ('CREDITO', 1, 'CREDITO_AVISTA'),
        ('CREDITO', 3, 'CREDITO_PARCELADO'),
        ('PIX', 1, 'PIX'),
    ])
    def test_identificar_tipo_transacao(self, calculadora, modalidade, parcelas, esperado_tipo):
        """Testa identificação correta do tipo de transação"""
        tipo = calculadora._identificar_tipo_transacao(modalidade, parcelas)
        assert tipo == esperado_tipo
```

**Outros services a testar:**
- `CashbackService` (crédito, liberação, expiração)
- `ContaDigitalService` (débito, estorno, saldo)
- `TRDataService` (parser Pinbank)
- `TRDataOwnService` (parser Own)
- `AntifraaudeService` (cálculo de score)

---

**1.2 Models e Serializers (20 horas)**
```python
# tests/models/test_cliente.py
def test_cliente_cpf_valido():
    cliente = Cliente(cpf='12345678900')
    assert cliente.cpf_valido()

def test_cliente_cpf_invalido():
    cliente = Cliente(cpf='12345678901')
    assert not cliente.cpf_valido()

# tests/serializers/test_cliente_serializer.py
def test_serializer_valida_cpf():
    data = {'cpf': '12345678900', 'nome': 'Teste'}
    serializer = ClienteSerializer(data=data)
    assert serializer.is_valid()

def test_serializer_rejeita_cpf_invalido():
    data = {'cpf': '00000000000', 'nome': 'Teste'}
    serializer = ClienteSerializer(data=data)
    assert not serializer.is_valid()
```

---

**1.3 Utils e Validators (20 horas)**
```python
# tests/utils/test_formatacao.py
def test_formatar_cpf():
    assert formatar_cpf('12345678900') == '123.456.789-00'

def test_formatar_valor_monetario():
    assert formatar_valor_monetario(Decimal('1234.56')) == 'R$ 1.234,56'

# tests/validators/test_validador_cpf.py
def test_validador_cpf_valido():
    assert ValidadorCPF.validar('12345678900') == True

def test_validador_cpf_invalido():
    assert ValidadorCPF.validar('11111111111') == False
```

---

**FASE 2: Testes de Integração (60 horas)**

**2.1 APIs Internas (30 horas)**
```python
# tests/integration/test_api_interna_cliente.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestAPIInternaCliente:
    @pytest.fixture
    def api_client(self):
        client = APIClient()
        # Autenticar com OAuth
        token = obter_token_oauth('wallclub_pos', 'secret')
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    def test_consultar_por_cpf_sucesso(self, api_client):
        """Testa consulta de cliente por CPF"""
        response = api_client.post(
            '/api/internal/cliente/consultar_por_cpf/',
            {'cpf': '12345678900', 'canal_id': 1},
            format='json'
        )

        assert response.status_code == 200
        assert response.json()['sucesso'] == True
        assert 'saldo_disponivel' in response.json()['dados']

    def test_consultar_por_cpf_nao_encontrado(self, api_client):
        """Testa consulta de cliente inexistente"""
        response = api_client.post(
            '/api/internal/cliente/consultar_por_cpf/',
            {'cpf': '99999999999', 'canal_id': 1},
            format='json'
        )

        assert response.status_code == 200
        assert response.json()['sucesso'] == False

    def test_consultar_sem_autenticacao(self):
        """Testa que endpoint requer autenticação"""
        client = APIClient()  # Sem token
        response = client.post(
            '/api/internal/cliente/consultar_por_cpf/',
            {'cpf': '12345678900', 'canal_id': 1},
            format='json'
        )

        assert response.status_code == 401
```

---

**2.2 Integrações Externas com Mock (30 horas)**
```python
# tests/integration/test_pinbank_service.py
import pytest
from unittest.mock import patch, Mock
from pinbank.services import PinbankService

class TestPinbankService:
    @patch('pinbank.services.requests.post')
    def test_efetuar_transacao_sucesso(self, mock_post):
        """Testa transação Pinbank com mock"""
        # Mock da resposta Pinbank
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'status': 'aprovado',
            'nsu': '123456',
            'autorizacao': '789012'
        }
        mock_post.return_value = mock_response

        # Executar
        resultado = PinbankService.efetuar_transacao(
            valor=Decimal('100.00'),
            parcelas=1,
            cartao='4111111111111111'
        )

        # Assertions
        assert resultado['status'] == 'aprovado'
        assert resultado['nsu'] == '123456'
        mock_post.assert_called_once()

    @patch('pinbank.services.requests.post')
    def test_efetuar_transacao_timeout(self, mock_post):
        """Testa tratamento de timeout"""
        mock_post.side_effect = requests.Timeout()

        with pytest.raises(PinbankTimeoutError):
            PinbankService.efetuar_transacao(
                valor=Decimal('100.00'),
                parcelas=1,
                cartao='4111111111111111'
            )
```

---

**FASE 3: Testes End-to-End (40 horas)**

**3.1 Fluxos Críticos (40 horas)**
```python
# tests/e2e/test_fluxo_transacional.py
import pytest
from selenium import webdriver

@pytest.mark.e2e
class TestFluxoTransacional:
    @pytest.fixture
    def browser(self):
        driver = webdriver.Chrome()
        yield driver
        driver.quit()

    def test_fluxo_completo_checkout(self, browser):
        """Testa fluxo completo de checkout"""
        # 1. Acessar link de pagamento
        browser.get('https://checkout.wallclub.com.br/link/abc123')

        # 2. Preencher dados do cartão
        browser.find_element_by_id('numero_cartao').send_keys('4111111111111111')
        browser.find_element_by_id('cvv').send_keys('123')
        browser.find_element_by_id('validade').send_keys('12/25')

        # 3. Validar OTP (2FA)
        browser.find_element_by_id('celular').send_keys('11999999999')
        browser.find_element_by_id('btn_enviar_otp').click()

        # Mock OTP (ambiente de teste)
        otp = obter_otp_teste('11999999999')
        browser.find_element_by_id('otp').send_keys(otp)

        # 4. Confirmar pagamento
        browser.find_element_by_id('btn_confirmar').click()

        # 5. Aguardar processamento
        WebDriverWait(browser, 10).until(
            EC.presence_of_element_located((By.ID, 'status_transacao'))
        )

        # 6. Verificar sucesso
        status = browser.find_element_by_id('status_transacao').text
        assert 'aprovado' in status.lower()
```

**Outros fluxos a testar:**
- Login app móvel + 2FA
- Autorização uso saldo (POS)
- Recorrência (cobrança automática)
- Cashback (crédito + liberação)

---

**FASE 4: Testes de Carga (24 horas)**

**4.1 Locust (24 horas)**
```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class WallClubUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """Autenticar usuário"""
        response = self.client.post('/api/oauth/token/', {
            'grant_type': 'client_credentials',
            'client_id': 'test_client',
            'client_secret': 'test_secret'
        })
        self.token = response.json()['access_token']

    @task(3)
    def consultar_saldo(self):
        """Simula consulta de saldo (operação comum)"""
        self.client.post(
            '/api/internal/conta_digital/consultar-saldo/',
            json={'cliente_id': 123},
            headers={'Authorization': f'Bearer {self.token}'}
        )

    @task(1)
    def efetuar_transacao(self):
        """Simula transação (operação crítica)"""
        self.client.post(
            '/api/v1/posp2/trdata_own/',
            json={
                'valor': 100.00,
                'parcelas': 1,
                'modalidade': 'DEBITO',
                # ... outros campos
            },
            headers={'Authorization': f'Bearer {self.token}'}
        )

# Executar:
# locust -f locustfile.py --host=https://wcapi.wallclub.com.br --users=1000 --spawn-rate=50
```

**Cenários de Carga:**
1. **Normal:** 100 usuários simultâneos (baseline)
2. **Pico:** 1000 usuários simultâneos (Black Friday)
3. **Stress:** 5000 usuários (encontrar limite)

**Métricas:**
- Latência P50/P95/P99
- Taxa de erro
- Throughput (req/s)
- Identificar gargalos

---

**FASE 5: CI/CD Integration (16 horas)**

**5.1 GitHub Actions (16 horas)**
```yaml
# .github/workflows/tests.yml
name: Tests

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov pytest-django

    - name: Run unit tests
      run: |
        pytest tests/unit/ --cov=. --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml

  integration-tests:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test
          MYSQL_DATABASE: wallclub_test
      redis:
        image: redis:7-alpine

    steps:
    - uses: actions/checkout@v3

    - name: Run integration tests
      run: |
        pytest tests/integration/

  quality-gate:
    needs: [unit-tests, integration-tests]
    runs-on: ubuntu-latest
    steps:
    - name: Check coverage
      run: |
        # Falhar se cobertura < 70%
        if [ $COVERAGE -lt 70 ]; then
          echo "Coverage too low: $COVERAGE%"
          exit 1
        fi
```

---

**Resumo Testes:**
- **Pontuação Atual:** 1/10
- **Esforço Total:** 220 horas (~6 semanas)
- **Cobertura Alvo:** 70% (unitários) + 50% (integração)
- **Prioridade:** 🔴 CRÍTICA

---

### 8.4 Esteira CI/CD

#### Situação Atual

**Deploy Atual:**
```bash
# Manual via SSH
ssh ubuntu@servidor
cd /var/www/WallClub_backend
git pull origin main
docker-compose down
docker-compose up -d --build
```

**Problemas:**
- ❌ Deploy manual (erro humano)
- ❌ Sem rollback automático
- ❌ Sem validação pré-deploy
- ❌ Downtime durante deploy
- ❌ Sem ambientes staging/QA

#### Recomendações

**FASE 1: Pipeline Básico (40 horas)**

**1.1 GitHub Actions - Build & Test (16 horas)**
```yaml
# .github/workflows/ci.yml
name: CI Pipeline

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  build-and-test:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2

    - name: Build images
      run: |
        docker-compose -f docker-compose.yml build

    - name: Run tests
      run: |
        docker-compose -f docker-compose.test.yml up --abort-on-container-exit

    - name: Security scan
      uses: aquasecurity/trivy-action@master
      with:
        scan-type: 'image'
        image-ref: 'wallclub-apis:latest'
        severity: 'CRITICAL,HIGH'

    - name: Lint code
      run: |
        docker run --rm wallclub-apis:latest flake8 .
        docker run --rm wallclub-apis:latest black --check .
```

---

**1.2 GitHub Actions - Deploy (24 horas)**
```yaml
# .github/workflows/cd.yml
name: CD Pipeline

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  deploy-staging:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: staging

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v2
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: us-east-1

    - name: Login to ECR
      run: |
        aws ecr get-login-password --region us-east-1 | \
        docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

    - name: Build and push images
      run: |
        docker-compose -f docker-compose.yml build
        docker tag wallclub-apis:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/wallclub-apis:${{ github.sha }}
        docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/wallclub-apis:${{ github.sha }}

    - name: Deploy to staging
      run: |
        # Atualizar deployment Kubernetes
        kubectl set image deployment/wallclub-apis \
          apis=123456789.dkr.ecr.us-east-1.amazonaws.com/wallclub-apis:${{ github.sha }} \
          -n staging

        # Aguardar rollout
        kubectl rollout status deployment/wallclub-apis -n staging

    - name: Run smoke tests
      run: |
        curl -f https://staging.wcapi.wallclub.com.br/health/ready/ || exit 1

    - name: Notify Slack
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: 'Deploy to staging: ${{ job.status }}'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}

  deploy-production:
    if: startsWith(github.ref, 'refs/tags/v')
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production

    steps:
    # ... similar ao staging

    - name: Deploy to production
      run: |
        # Blue-Green deployment
        kubectl apply -f k8s/production/blue-green.yaml

        # Aguardar health checks
        sleep 30

        # Switch traffic
        kubectl patch service wallclub-apis-service \
          -p '{"spec":{"selector":{"version":"green"}}}' \
          -n production

    - name: Rollback on failure
      if: failure()
      run: |
        kubectl patch service wallclub-apis-service \
          -p '{"spec":{"selector":{"version":"blue"}}}' \
          -n production
```

---

**FASE 2: Ambientes Isolados (32 horas)**

**2.1 Staging Environment (16 horas)**
```yaml
# k8s/staging/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: staging
  labels:
    environment: staging

---
# Recursos reduzidos (50% de produção)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wallclub-apis
  namespace: staging
spec:
  replicas: 2  # vs 4 em produção
  template:
    spec:
      containers:
      - name: apis
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

**Características:**
- Banco de dados separado (staging)
- Integrações em sandbox (Pinbank QA, Own QA)
- Dados sintéticos (não produção)
- Deploy automático (branch main)

---

**2.2 QA Environment (16 horas)**
```yaml
# k8s/qa/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: qa
  labels:
    environment: qa

# Deploy manual (para testes específicos)
# Dados de teste controlados
# Integrações mockadas
```

---

**FASE 3: Estratégias de Deploy (24 horas)**

**3.1 Blue-Green Deployment (12 horas)**
```yaml
# k8s/production/blue-green.yaml
# Deployment Blue (versão atual)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wallclub-apis-blue
  namespace: production
spec:
  replicas: 4
  selector:
    matchLabels:
      app: wallclub-apis
      version: blue
  template:
    metadata:
      labels:
        app: wallclub-apis
        version: blue
    spec:
      containers:
      - name: apis
        image: wallclub-apis:v1.0.0

---
# Deployment Green (nova versão)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: wallclub-apis-green
  namespace: production
spec:
  replicas: 4
  selector:
    matchLabels:
      app: wallclub-apis
      version: green
  template:
    metadata:
      labels:
        app: wallclub-apis
        version: green
    spec:
      containers:
      - name: apis
        image: wallclub-apis:v1.1.0

---
# Service (switch entre blue/green)
apiVersion: v1
kind: Service
metadata:
  name: wallclub-apis-service
  namespace: production
spec:
  selector:
    app: wallclub-apis
    version: blue  # Mudar para 'green' após validação
  ports:
  - port: 80
    targetPort: 8007
```

**Processo:**
1. Deploy green (nova versão)
2. Validar health checks
3. Smoke tests
4. Switch service (blue → green)
5. Manter blue por 1h (rollback rápido)
6. Remover blue

---

**3.2 Canary Deployment (12 horas)**
```yaml
# Istio VirtualService
apiVersion: networking.istio.io/v1beta1
kind: VirtualService
metadata:
  name: wallclub-apis
  namespace: production
spec:
  hosts:
  - wallclub-apis-service
  http:
  - match:
    - headers:
        x-canary:
          exact: "true"
    route:
    - destination:
        host: wallclub-apis-service
        subset: v2
  - route:
    - destination:
        host: wallclub-apis-service
        subset: v1
      weight: 90
    - destination:
        host: wallclub-apis-service
        subset: v2
      weight: 10  # 10% do tráfego para nova versão
```

**Processo:**
1. Deploy v2 (nova versão)
2. Rotear 10% do tráfego
3. Monitorar métricas (30min)
4. Se OK: 50% → 100%
5. Se falha: rollback para 0%

---

**FASE 4: Monitoramento de Deploy (16 horas)**

**4.1 Métricas de Deploy**
```python
# Prometheus metrics
deployment_duration_seconds = Histogram(
    'wallclub_deployment_duration_seconds',
    'Duração do deploy',
    ['environment', 'service']
)

deployment_status = Counter(
    'wallclub_deployment_status_total',
    'Status dos deploys',
    ['environment', 'service', 'status']  # success, failure, rollback
)

deployment_frequency = Counter(
    'wallclub_deployment_frequency_total',
    'Frequência de deploys',
    ['environment', 'service']
)
```

**4.2 Dashboards**
- Lead time (commit → produção)
- Deploy frequency (deploys/dia)
- Change failure rate (%)
- MTTR (Mean Time To Recovery)

---

**Resumo CI/CD:**
- **Pontuação Atual:** 2/10
- **Esforço Total:** 112 horas (~3 semanas)
- **Custo Adicional:** ~R$ 800/mês (ambientes staging/QA)
- **Prioridade:** 🟠 ALTA

---

### 8.5 Resumo de Aspectos Operacionais

| Aspecto | Pontuação Atual | Esforço | Prioridade |
|---------|-----------------|---------|------------|
| Integrações/Middleware | 6/10 | 28h | 🟠 Alta |
| Monitoramento | 3/10 | 112h | 🔴 Crítica |
| Testes Automatizados | 1/10 | 220h | 🔴 Crítica |
| CI/CD | 2/10 | 112h | 🟠 Alta |
| **TOTAL** | **3/10** | **472h** | - |

**Esforço Total:** 472 horas (~12 semanas / 3 meses)
**Custo Adicional Mensal:** ~R$ 1.300 (monitoramento + ambientes)

**Recomendação:** Implementar em paralelo com migração Kubernetes (Fase 2-3).

---

## 9. CONCLUSÃO

### Pontos Fortes
✅ Arquitetura modular bem estruturada
✅ Package `wallclub_core` exemplar
✅ 26 APIs REST internas funcionais
✅ Pronta para Kubernetes (6-9 meses)

### Pontos de Atenção
⚠️ Gaps críticos de segurança (rate limiting, 2FA)
⚠️ Calculadoras centralizadas (ponto único de falha)
⚠️ Acoplamento ao banco de dados (limita microserviços)
⚠️ Transações distribuídas (requer Saga Pattern)

### Recomendação Final

**Curto Prazo:** Focar em segurança (32h) e extrair calculadoras (40h)

**Médio Prazo:** Migrar para Kubernetes (160h + R$ 2.800/mês)
- Benefícios imediatos: escalabilidade, disponibilidade, deploy frequency

**Longo Prazo:** Avaliar microserviços após Kubernetes estável
- Começar com Notificações (baixo risco, alto aprendizado)
- Evitar Parâmetros Financeiros (alto risco, baixo benefício)

---

## 10. ITENS PENDENTES (Adicionados em 15/01/2026)

### 10.1 Ativar Middlewares de Observabilidade

**Status:** Arquivos criados, não ativados
**Prioridade:** 🟡 MÉDIA
**Esforço:** 4 horas

**Middlewares disponíveis:**
- `correlation_middleware.py` - Rastreia requisições entre containers via `X-Correlation-ID`
- `request_logging_middleware.py` - Logging estruturado de requisições HTTP

**Benefícios:**
- Debugging facilitado de problemas entre containers
- Monitoramento de performance por endpoint
- Auditoria de requisições

**Para ativar:** Adicionar ao `MIDDLEWARE` em `settings.py` de cada container:
```python
MIDDLEWARE = [
    'wallclub_core.middleware.correlation_middleware.CorrelationIdMiddleware',
    'wallclub_core.middleware.request_logging_middleware.RequestLoggingMiddleware',
    # ... outros middlewares
]
```

**Quando ativar:** Quando houver necessidade de debugging avançado ou monitoramento de performance.

---

### 10.2 Incluir Risk Engine na Análise Arquitetural

**Status:** Não analisado neste documento
**Prioridade:** 🟠 ALTA
**Esforço:** 8 horas

**Risk Engine atual:**
- Container separado: `wallclub-riskengine` (porta 8008)
- 9 regras antifraude ativas
- Integração com MaxMind minFraud
- OAuth 2.0 entre containers
- Análise <200ms

**Pontos a analisar:**
1. **Segurança:** Validação de tokens OAuth, rate limiting
2. **Escalabilidade:** Comportamento sob carga alta
3. **Resiliência:** Circuit breaker, fallback quando indisponível
4. **Monitoramento:** Métricas de decisões (aprovado/reprovado/revisão)
5. **Evolução:** Machine learning, regras dinâmicas

**Documentação existente:**
- `services/riskengine/docs/engine_antifraude.md`
- `services/riskengine/docs/integracao_autenticacao_fraude.md`

**Tabelas relacionadas:**
- `antifraude_regra` (9 regras)
- `antifraude_decisao`
- `antifraude_transacao_risco`
- `antifraude_whitelist`
- `antifraude_blacklist`
- `antifraude_configuracao`

---

**Responsável:** Jean Lessa
**Próxima Revisão:** Abril/2026
**Aprovação:** Pendente

