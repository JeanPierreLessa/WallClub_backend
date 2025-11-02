# FASE 6 - SEPARAÇÃO EM MÚLTIPLOS CONTAINERS

**Data:** 31/10/2025 - 01/11/2025  
**Branch:** `multiplos_containers`  
**Status:** ✅ FASE 6A + 6B CONCLUÍDAS  
**Última Atualização:** 01/11/2025 23:32  
**Documento:** Consolidado FASE_6 + FASE_6B

---

## 📊 ÍNDICE

1. [Resumo Executivo](#resumo-executivo)
2. [Análise de Estrutura - 82+46+87 arquivos](#análise-de-estrutura)
3. [Análise de Dependências - Imports detalhados](#análise-de-dependências)
4. [Fase 6A - Limpeza do CORE](#fase-6a---limpeza-do-core)
5. [Bug Fix - device_fingerprint](#bug-fix---device_fingerprint)
6. [Fase 6B - Resolver Dependências Cruzadas](#fase-6b---resolver-dependências-cruzadas)
7. [Validação e Testes Completos](#validação-e-testes)
8. [Próximas Fases 6C/6D](#próximas-fases)
9. [Distribuição por Container](#distribuição-por-container)
10. [Cronograma](#cronograma)

---

## 📊 RESUMO EXECUTIVO

### Objetivo:
Separar monolito Django em 4 containers independentes + 1 package compartilhado

### Containers:
1. **APP1 - wallclub-portais** (8001): Portais admin/lojista/vendas
2. **APP2 - wallclub-pos** (8002): POS e processamento
3. **APP3 - wallclub-apis** (8003): APIs mobile e checkout
4. **APP4 - wallclub-riskengine** (8004): Antifraude ✅ JÁ EXISTE
5. **CORE - wallclub-core**: Package compartilhado

### Status:
- ✅ **Fase 6A:** CORE limpo (0 imports problemáticos)
- ✅ **Bug fix:** device_fingerprint não sobrescreve mais
- ✅ **Fase 6B:** Dependências cruzadas resolvidas (26 APIs + 17 lazy imports)
- ⏳ **Próximo:** Fase 6C - Extrair CORE

---

## 🏗️ ANÁLISE DE ESTRUTURA

### APP1 - PORTAIS (82 arquivos)
- `portais/admin/` (35 arquivos)
- `portais/lojista/` (18 arquivos)
- `portais/vendas/` (12 arquivos)
- `portais/corporativo/` (5 arquivos)
- `portais/controle_acesso/` (8 arquivos)
- `sistema_bancario/` (10 arquivos)

### APP2 - POS (46 arquivos)
- `posp2/` (18 arquivos)
- `pinbank/` (15 arquivos)
- `parametros_wallclub/` (13 arquivos)

### APP3 - APIS (87 arquivos)
- `apps/cliente/` (28 arquivos)
- `apps/transacoes/` (8 arquivos)
- `apps/conta_digital/` (10 arquivos)
- `apps/ofertas/` (6 arquivos)
- `checkout/` (31 arquivos)

### CORE (49 arquivos)
- `comum/decorators/` (3)
- `comum/oauth/` (4) - ✅ jwt_utils.py NOVO
- `comum/seguranca/` (8) - ✅ REFATORADO
- `comum/integracoes/` (12) - ✅ REFATORADO
- `comum/middleware/` (3)
- `comum/services/` (6)
- `comum/utilitarios/` (5)

**Status CORE:**
- ✅ 0 imports diretos de apps
- ✅ 2 imports lazy (dentro de funções - OK)
- ✅ Pronto para extração

---

## 🔗 ANÁLISE DE DEPENDÊNCIAS

| De → Para | Imports | % | Severidade | Status |
|-----------|---------|---|------------|--------|
| CORE → Apps | 0 | 0% | ✅ OK | Resolvido |
| APP1 → APP3 | 48 | 58.5% | 🔴 CRÍTICO | Pendente |
| APP1 → APP2 | 27 | 32.9% | 🟡 Alto | Pendente |
| APP2 → APP3 | 20 | 43.5% | 🟠 Médio | Pendente |
| APP3 → APP2 | 8 | 9.2% | 🟠 Médio | Pendente |
| Apps → CORE | 281 | ✅ | OK | Esperado |

### 🔴 APP1 → APP3 (CRÍTICO - 48 imports)
**Arquivos problemáticos:**
- `portais/admin/views_clientes.py` → `apps.cliente.models`
- `portais/lojista/views.py` → `checkout.models`
- `portais/vendas/views.py` → `checkout.link_pagamento_web.services`

**Estratégias:**
1. Models compartilhados → SQL direto
2. Leitura → Endpoints REST internos
3. Write → API REST

### 🟡 APP1 → APP2 (ALTO - 27 imports)
**Estratégias:**
1. Calculadoras → Mover para CORE
2. Parâmetros → Avaliar CORE (config global)
3. Transações → SQL direto

### 🟠 APP2 ↔ APP3 (MÉDIO - 28 imports total)
**Estratégias:**
1. Model Cliente → Mover para CORE (entidade central)
2. Gateway Pinbank → Service no CORE
3. Queries → SQL direto temporário

---

## ✅ FASE 6A - LIMPEZA DO CORE

### Arquivos Alterados:

#### 1. `comum/oauth/jwt_utils.py` ✅ CRIADO
Funções JWT genéricas sem dependência de apps:
- `validate_jwt_token()` - Validação genérica
- `validate_cliente_jwt_token()` - Wrapper retrocompatível
- `decode_jwt_token()` - Debug
- `extract_token_from_header()` - Extração

#### 2. `comum/seguranca/services_device.py` ✅ REFATORADO
Removido código que buscava Cliente:
- Métodos de notificação esvaziados
- Caller deve notificar manualmente
- CORE não conhece Cliente

#### 3. `comum/integracoes/notificacao_seguranca_service.py` ✅ REFATORADO
Métodos não buscam mais Cliente. Nova assinatura:
```python
NotificacaoSegurancaService.notificar_troca_senha(
    cliente_id=123,
    canal_id=1,
    celular='11987654321',  # Obrigatório
    nome='João'             # Opcional
)
```

### Callers Atualizados (6 arquivos):
- ✅ `apps/cliente/views_senha.py`
- ✅ `apps/cliente/views.py` (celular e email)
- ✅ `apps/cliente/services_reset_senha.py`
- ✅ `apps/cliente/services.py` (3 chamadas)
- ✅ `apps/cliente/services_2fa_login.py`

---

## 🐛 BUG FIX - DEVICE_FINGERPRINT

### Problema:
Backend sobrescrevia fingerprint do app com string vazia:
```python
device_fingerprint = request.data.get('device_fingerprint', '')  # ❌
```

Resultado:
- Recalculava fingerprint a cada login
- Criava dispositivos duplicados
- Atingia limite de 2 dispositivos

### Correção:
```python
# apps/cliente/views_2fa_login.py
device_fingerprint = request.data.get('device_fingerprint')  # ✅ Sem default

# comum/seguranca/services_device.py
if not fingerprint or fingerprint.strip() == '':  # ✅ Valida vazio
    registrar_log('...não fornecido, calculando...')
    fingerprint = cls.calcular_fingerprint(dados_dispositivo)
else:
    registrar_log(f'...fornecido pelo app: {fingerprint[:8]}...')
```

### Status:
- ✅ Commit `4e2fc56` em release/3.1.0
- ✅ Merged em multiplos_containers

---

## ✅ FASE 6B - RESOLVER DEPENDÊNCIAS CRUZADAS

**Duração:** 3 semanas (Semanas 28-30)  
**Status:** ✅ CONCLUÍDA  
**Data Conclusão:** 01/11/2025 23:28

### Objetivo:
Resolver 103 imports cruzados para permitir separação física dos containers

### Estratégias Aplicadas:

| Estratégia | Uso | Endpoints/Arquivos |
|------------|-----|--------------------|
| 🌐 APIs REST | 70% | 26 endpoints |
| 📊 SQL Direto | 25% | 2 classes |
| 🔄 Lazy Imports | 5% | 17 arquivos |

---

### Semana 28: APIs Internas - Conta Digital + Checkout ✅

**APIs Conta Digital (5 endpoints):**
```
POST /api/internal/conta-digital/consultar-saldo/
POST /api/internal/conta-digital/autorizar-uso/
POST /api/internal/conta-digital/debitar-saldo/
POST /api/internal/conta-digital/estornar-saldo/
POST /api/internal/conta-digital/calcular-maximo/
```

**APIs Checkout Recorrências (8 endpoints):**
```
GET  /api/internal/checkout/recorrencias/
POST /api/internal/checkout/recorrencias/criar/
GET  /api/internal/checkout/recorrencias/{id}/
POST /api/internal/checkout/recorrencias/{id}/pausar/
POST /api/internal/checkout/recorrencias/{id}/reativar/
POST /api/internal/checkout/recorrencias/{id}/cobrar/
PUT  /api/internal/checkout/recorrencias/{id}/atualizar/
DEL  /api/internal/checkout/recorrencias/{id}/deletar/
```

**Entregas:**
- ✅ Middleware ajustado (sem rate limiting para APIs internas)
- ✅ posp2 independente de apps/conta_digital
- ✅ Tasks Celery movidas para checkout/
- ✅ OAuth 2.0 Client Credentials com scope `internal`

**Commits:**
- `c6f98d5` - INICIO DA FASE 6B
- `7416f3a` - feat(conta-digital): APIs internas
- `b9fae11` - refactor(posp2): usar APIs internas
- `62ca51e` - refactor(checkout): mover tasks
- `05c0b39` - feat(checkout): APIs internas recorrências

---

### Semana 29: Ofertas + SQL Direto ✅

**APIs Ofertas (6 endpoints):**
```
POST /api/internal/ofertas/listar/
POST /api/internal/ofertas/criar/
POST /api/internal/ofertas/obter/
POST /api/internal/ofertas/atualizar/
POST /api/internal/ofertas/grupos/listar/
POST /api/internal/ofertas/grupos/criar/
```

**SQL Direto - comum/database/queries.py:**

**TransacoesQueries (7 métodos):**
- `listar_transacoes_periodo()`
- `buscar_transacao_por_nsu()`
- `calcular_totais_periodo()`
- `listar_ultimas_transacoes()`
- `buscar_transacoes_cliente()`
- `exportar_transacoes_excel()`
- `buscar_estatisticas_loja()`

**TerminaisQueries (2 métodos):**
- `listar_terminais_loja()`
- `buscar_terminal_por_serial()`

**Arquivos Refatorados (7):**
- `portais/admin/views.py`
- `portais/admin/views_transacoes.py`
- `portais/admin/views_rpr.py`
- `portais/admin/services_rpr.py`
- `portais/lojista/views.py`
- `portais/lojista/views_cancelamentos.py`
- `portais/lojista/services_recebimentos.py`

**Entregas:**
- ✅ Portais independente de pinbank
- ✅ Portais independente de apps/ofertas
- ✅ SQL direto para queries read-only complexas

**Commit:**
- `286e0f5` - feat(fase6b): APIs ofertas + SQL direto

---

### Semana 30: Lazy Imports + Parâmetros + Validação ✅

**Lazy Imports (17 arquivos):**

**Padrão Implementado:**
```python
# ANTES (import direto - ERRADO)
from posp2.models import Terminal
from checkout.models import CheckoutCliente

def minha_funcao():
    terminal = Terminal.objects.get(id=1)

# DEPOIS (lazy import - CORRETO)
from django.apps import apps

def minha_funcao():
    Terminal = apps.get_model('posp2', 'Terminal')
    terminal = Terminal.objects.get(id=1)
```

**Arquivos Corrigidos:**
1. `portais/admin/` - 6 arquivos
2. `portais/lojista/` - 4 arquivos
3. `portais/vendas/` - 4 arquivos (Cliente, CheckoutCliente, CheckoutTransaction)
4. `posp2/` - 2 arquivos (Cliente, ClienteAuthService)
5. `checkout/` - 1 arquivo

**APIs Parâmetros (7 endpoints):**
```
POST /api/internal/parametros/configuracoes/loja/
POST /api/internal/parametros/configuracoes/contar/
POST /api/internal/parametros/configuracoes/ultima/
POST /api/internal/parametros/loja/modalidades/
POST /api/internal/parametros/planos/
GET  /api/internal/parametros/importacoes/
GET  /api/internal/parametros/importacoes/{id}/
```

**Fix Crítico RPR:**
- **Problema:** Valores zerados (transações vêm como `dict` mas código usava `getattr()`)
- **Solução:** `transacao.get(campo, '')` em 3 ocorrências
- **Arquivo:** `portais/admin/views_rpr.py`
- **Status:** ✅ Validado em produção

**Decisões Arquiteturais:**
- ✅ **Cliente:** Manter em `apps/cliente` com lazy imports
- ✅ **ParametrosWall:** REST API (7 endpoints)

**Commits:**
- `ee0e369` - Lazy imports (14 arquivos)
- `d2e0d36` - Restaurar OfertaService
- `b83fd91` - Corrigir labels apps
- Fix RPR dict access

---

### 🎉 FASE 6B - RESUMO EXECUTIVO

**Entregas Completas:**

**1. APIs REST Internas (26 endpoints):**
- ✅ 5 endpoints Conta Digital
- ✅ 8 endpoints Checkout Recorrências
- ✅ 6 endpoints Ofertas
- ✅ 7 endpoints Parâmetros

**2. Lazy Imports (17 arquivos):**
- ✅ `portais/admin/` - 6 arquivos
- ✅ `portais/lojista/` - 4 arquivos
- ✅ `portais/vendas/` - 4 arquivos
- ✅ `posp2/` - 2 arquivos
- ✅ `checkout/` - 1 arquivo

**3. SQL Direto (2 classes):**
- ✅ `TransacoesQueries` - 7 métodos
- ✅ `TerminaisQueries` - 2 métodos

**4. Correções Críticas:**
- ✅ Middleware APIs internas (sem rate limiting)
- ✅ Tasks Celery movidas para checkout/
- ✅ RPR corrigido (dict vs getattr)
- ✅ Imports cruzados removidos

**Validação Final:**
```bash
✓ SUCESSO: Containers desacoplados!
```

**Arquitetura Resultante:**
- 🟢 APP1 (Portais) → APP2 (POS): 0 imports diretos
- 🟢 APP1 (Portais) → APP3 (APIs): 0 imports diretos
- 🟢 APP2 (POS) → APP3 (APIs): 0 imports diretos
- 🟢 Comunicação: HTTP/REST via APIs internas
- 🟢 Código pronto para separação física

---

## ✅ VALIDAÇÃO E TESTES

### 1. Validar CORE (1 min)
```bash
bash scripts/validar_core_limpo.sh
# Esperado: CORE limpo, 0 imports diretos
```

### 2. Testar device_fingerprint (5 min)
```bash
# Ver logs
docker exec wallclub-prod tail -f /var/log/wallclub/app.log | grep "Device fingerprint"

# Fazer login 3x no app
# Esperado:
# ✅ "fornecido pelo app: c57ef4da..."
# ✅ Não cria dispositivo novo
# ✅ Não pede 2FA toda vez

# Verificar base
SELECT COUNT(*) FROM otp_dispositivo_confiavel 
WHERE user_id = 1 AND ativo = 1;
# Esperado: Não aumenta
```

### 3. Testar Notificações (5-10 min)
- Trocar senha → Push + WhatsApp
- Alterar celular → WhatsApp para número ANTIGO
- Alterar email → Notificação enviada
- 3+ tentativas falhas → Alerta
- 5 tentativas → Bloqueio + notificação
- Login novo dispositivo → WhatsApp

### 4. Verificar Logs
```bash
docker exec wallclub-prod tail -f /var/log/wallclub/app.log | grep -i "notificacao\|erro"
```

---

## 🎯 PRÓXIMAS FASES

### Fase 6C: Extrair CORE (1 semana) - 📅 PRÓXIMA
1. Criar package wallclub-core
2. Setup.py + requirements
3. Publicar localmente
4. Instalar em containers
5. Atualizar imports

### Fase 6D: Separar Containers (3-4 semanas)
1. APP2 (POS) - Mais isolado
2. APP3 (APIs)
3. APP1 (Portais) - Mais complexo
4. Nginx Gateway

---

## 📋 DISTRIBUIÇÃO POR CONTAINER

### APP1 - wallclub-portais (8001)
- portais/admin/, lojista/, vendas/, corporativo/
- portais/controle_acesso/
- sistema_bancario/
- Deploy: Frequente
- Auth: Sessão Django
- Celery: Recorrências

### APP2 - wallclub-pos (8002)
- posp2/, pinbank/, parametros_wallclub/
- Deploy: Raro (crítico)
- Auth: OAuth 2.0
- Celery: Cargas

### APP3 - wallclub-apis (8003)
- apps/cliente/, transacoes/, conta_digital/, ofertas/
- checkout/
- Deploy: Médio
- Auth: JWT custom

### APP4 - wallclub-riskengine (8004) ✅
- antifraude/
- Status: JÁ EXISTE

### CORE - wallclub-core (package)
- comum/* (49 arquivos)
- Status: Pronto para extração

---

## ⏱️ CRONOGRAMA

| Fase | Semanas | Status |
|------|---------|--------|
| 6A - CORE | 27 | ✅ Concluída |
| Bug fix | 27 | ✅ Concluída |
| 6B - Dependências | 28-30 | ✅ Concluída |
| 6C - Extrair CORE | 31 | 📅 Próxima |
| 6D - Containers | 32-36 | 📅 Planejada |

**Total:** 10 semanas  
**Concluído:** 6 semanas (60%)  
**Restante:** 4-5 semanas

---

## 📊 MÉTRICAS

### Antes:
- Containers: 2 (web + riskengine)
- Deploy: Tudo junto
- Acoplamento: Alto (103 imports cruzados)
- Bug: device_fingerprint duplicado

### Agora (Fase 6A + 6B concluídas):
- CORE: Limpo (0 imports de apps)
- Dependências: Resolvidas (26 APIs + 17 lazy imports + 2 SQL classes)
- Acoplamento: 0 imports diretos entre containers
- Bug device_fingerprint: ✅ Corrigido
- Validação: ✅ Script passou
- Código: Pronto para separação física

### Depois (Fase 6C + 6D):
- Containers: 5 (portais + pos + apis + riskengine + core)
- Deploy: Independente
- Comunicação: APIs REST internas

---

## 📝 COMMITS

### release/3.1.0:
- `4e2fc56` - fix: device_fingerprint sobrescrito

### multiplos_containers - Fase 6A:
- `b366851` - feat(fase6a): CORE limpo
- `89d01ff` - Merge release/3.1.0
- `84df3b2` - docs: arquivos fase 6
- `c38605e` - docs: remover individuais

### multiplos_containers - Fase 6B:
- `c6f98d5` - INICIO DA FASE 6B
- `7416f3a` - feat(conta-digital): APIs internas
- `b9fae11` - refactor(posp2): usar APIs internas
- `62ca51e` - refactor(checkout): mover tasks
- `05c0b39` - feat(checkout): APIs internas recorrências
- `286e0f5` - feat(fase6b): APIs ofertas + SQL direto
- `ee0e369` - Lazy imports (14 arquivos)
- `d2e0d36` - Restaurar OfertaService
- `b83fd91` - Corrigir labels apps
- Fix RPR dict access (3 ocorrências)
- feat(parametros): APIs internas (7 endpoints)

---

**Documento:** 01/11/2025 23:32  
**Responsável:** Jean Lessa  
**Versão:** Consolidada FASE_6 + FASE_6B
