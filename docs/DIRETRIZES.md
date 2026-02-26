# DIRETRIZES UNIFICADAS - WALLCLUB ECOSYSTEM

**Versão:** 5.8
**Data:** 23/02/2026
**Fontes:** Fases 1-7 (100%) + Django DIRETRIZES.md + Risk Engine DIRETRIZES.md
**Mudanças:**
- **Login Biométrico - App Mobile (23/02/2026)**
  - **Endpoint:** `POST /api/v1/cliente/login_biometrico/` ✅ funcional
  - **Autenticação:** CPF + device_fingerprint + canal_id
  - **Validação:** `DeviceManagementService.validar_dispositivo()` verifica dispositivo confiável (30 dias)
  - **Retorno:** JWT token + refresh_token + dados do cliente
  - **Segurança:** Requer OAuth token (`@require_oauth_apps`)
  - **Modelo Cliente:** Campo `is_active` (não `ativo`)
  - **Arquivo:** `apps/cliente/views_login_biometrico.py`
- **Own Financial - E-commerce e Webhooks (06/02/2026)**
  - **Limitação Crítica:** API `/buscaTransacoesGerais` NÃO retorna transações e-commerce (apenas POS físico)
  - **Identificadores:** `merchantTransactionId` e `id` (OPPWA) não funcionam como `identificadorTransacao` para consultas
  - **Webhook Obrigatório:** Único meio de obter `identificadorTransacao` para transações e-commerce
  - **Endpoint Testado:** `https://wcapi.wallclub.com.br/webhook/own/transacao/` ✅ funcional
  - **Campos Novos em `checkout_transactions`:**
    - `card_bin` VARCHAR(6) - Primeiros 6 dígitos do cartão
    - `card_last4` VARCHAR(4) - Últimos 4 dígitos do cartão
    - `payment_brand_response` VARCHAR(50) - Bandeira retornada pela OWN
    - `result_code` VARCHAR(20) - Código de resultado da transação
    - `tx_transaction_id` VARCHAR(100) - identificadorTransacao (vem do webhook)
  - **Renomeações:** `pinbank_response` → `gateway_response`, `erro_pinbank` → `erro_gateway`
  - **Pendente:** Configuração do webhook de e-commerce com a OWN
- **Portal Admin - RPR - Refinamento Completo de Métricas (03/02/2026)**
  - Coluna "Custo ajuste nos Repasses" reposicionada (antes de var98) e renomeada
  - Nova coluna "Resultado Operacional Ajustado" = Resultado Operacional + Custo ajuste nos Repasses
  - Box "Custo Direto Total": sinal invertido, "Custos POS/Equip" removido
  - Box "Resultado Financeiro": totalizador recalculado (Receita Financeira - Custo Direto)
  - Nova linha "Resultado após Custos de POS's" no box Resultado Financeiro
  - Percentual de comissão dinâmico (tabela canal_comissao) sincronizado entre tela e exports
- **Own Financial - Rotinas de Carga e Ambiente (05/02/2026)**
  - **Ambiente Centralizado:** `CredenciaisOwnService.obter_environment()` usado em todos os 7 services
  - **API `/buscaTransacoesGerais`:** Retorna APENAS transações POS (não retorna e-commerce)
  - **Rotinas de Carga:**
    - `carga_transacoes_own` - Busca transações POS via API (suporte a `--nsu`, `--data-inicial`, `--data-final`)
    - `carga_liquidacoes_own` - Busca liquidações via API `/consultaLiquidacoes`
    - `carga_base_unificada_checkout_own` - Processa checkout OWN para `base_transacoes_unificadas`
      - **JOIN:** `ownExtratoTransacoes.identificadorTransacao = checkout_transactions.tx_transaction_id`
      - **Filtro:** `ownExtratoTransacoes.lido = 0` (marca como `lido=1` após processar)
      - **Campos mapeados:** `mdr`, `statusTransacao`, `statusPagamento`, `dataPagamentoPrevista`
      - **TxTransactionId:** Salvo em `checkout_transactions.tx_transaction_id` no momento da venda (campo `resultDetails.TxTransactionId` da resposta OWN)
  - **Webhooks:** Endpoints implementados (`/webhook/transacao/`, `/webhook/liquidacao/`) - pendente configuração com suporte OWN
  - **Campo `gateway_ativo`:** Obrigatório na tabela `loja` para seleção correta do gateway ('PINBANK' ou 'OWN')
- **Own Financial - Payload Otimizado (03/02/2026)**
  - Campos estruturados de cliente e endereço implementados
  - CheckoutCliente e CheckoutToken: `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado`, `cep`, `data_nascimento`, `email`
  - Portal de Vendas: Formulários de cadastro/edição com campos estruturados
  - Payload Own: `merchant.taxId` (CNPJ), `merchant.id` (razão social), `merchant.postcode` (CEP)
  - Payload Own: `customer.identificationDocType: TAXSTATEMENT`, `customer.birthDate`, `customer.email`
  - Campos removidos (rejeitados pela API): `customer.browserUserAgent`, `billing.street`, `shipping.street`
  - Transação aprovada com payload completo (NSU: 8ac7a4a19c22cdec019c2357e13915e2)
  - Documentação oficial: https://docs.payments-own.financial/reference/parameters
- **Arquitetura de URLs Refatorada (31/01/2026)**
  - Redução de 8 para 3 arquivos de URLs (62% redução)
  - Função helper `get_portal_urlpatterns()` para geração dinâmica
  - Middleware simplificado usando função helper (zero duplicação)
  - Subdomínios mantidos funcionando (admin.wallclub.com.br, vendas.wallclub.com.br)
  - Rotas globais centralizadas (/metrics, /health/, /admin/)
- **Sistema de Monitoramento Completo (31/01/2026)**
  - Prometheus + Alertmanager + Exporters (Redis, Node)
  - 14 alertas configurados (críticos e warnings)
  - Notificações via Telegram e Email funcionando
  - Métricas customizadas em todos os containers Django
- **GatewayRouter - Portal de Vendas com Own Financial completo (29/01/2026)**
  - `CheckoutService` refatorado para usar `GatewayRouter` ao invés de hardcoded Pinbank
  - Seleção dinâmica de gateway (Pinbank/Own) por loja via campo `gateway_ativo`
  - Suporte completo: tokenização, pagamento com token, pagamento direto, estorno e exclusão
- Conta Digital - Métodos `debitar()` e `estornar_movimentacao()` corrigidos para verificar `afeta_cashback` (24/01/2026)
- Sistema Backsync POS - Novo endpoint `transactiondata_pos_backsync` para sincronização offline (23/01/2026)
- Depreciações Planejadas - Endpoints `/transaction_sync_service/` e `/trdata/` marcados para substituição (23/01/2026)
- Abstração Calculadoras Base - Parâmetros obrigatórios, sem busca interna (24/12/2025)
- Migração Pinbank para `transactiondata_pos` - Endpoint `/trdata/` agora grava em tabela unificada (23/12/2025)
- Migração Terminais DATETIME - Campos `inicio`/`fim` convertidos de Unix timestamp para DATETIME (20/12/2025)

---

## 📋 ÍNDICE

1. [Regras Fundamentais](#regras-fundamentais)
2. [Containers Desacoplados](#containers-desacoplados) ⭐ NOVO
3. [Banco de Dados](#banco-de-dados)
4. [Timezone e Datas](#timezone-e-datas)
5. [Valores Monetários](#valores-monetários)
6. [APIs REST](#apis-rest)
7. [Autenticação e Segurança](#autenticação-e-segurança)
8. [Sistema Antifraude](#sistema-antifraude)
9. [Notificações](#notificações)
10. [Arquitetura Docker](#arquitetura-docker)
11. [Boas Práticas de Código](#boas-práticas-de-código)

**Documentos Completos:**
- [Django DIRETRIZES (3428 linhas)](../1.%20DIRETRIZES.md)
- [Risk Engine DIRETRIZES (875 linhas)](../../wallclub-riskengine/docs/DIRETRIZES.md)

---

## 🔴 REGRAS FUNDAMENTAIS

### Comunicação e Validação

**SEMPRE:**
- ✅ Falar em português
- ✅ Ser técnico e direto (sem floreios)
- ✅ Responder SOMENTE com base no código visível
- ✅ Fazer perguntas breves para esclarecer
- ✅ **Para perguntas simples e diretas:** dar APENAS a resposta mais prática (sem listar múltiplas opções)
- ✅ **Para perguntas complexas:** listar opções com prós/contras quando necessário
- ✅ Respeitar formato solicitado (JSON, markdown, etc)

**NUNCA:**
- ❌ Inventar códigos, variáveis, métodos ou APIs
- ❌ Criar código não solicitado explicitamente
- ❌ Completar funções sem pedido direto
- ❌ Usar dados hardcoded (só quando explícito)
- ❌ Assumir o que o usuário quer
- ❌ **🚨 CRÍTICO: EXPOR CREDENCIAIS EM CÓDIGO, ARQUIVOS DE CONFIGURAÇÃO OU DOCUMENTOS**
- ❌ **🚨 CRÍTICO: USAR FALLBACK COM CREDENCIAIS REAIS** (ex: `os.environ.get('TOKEN', 'credencial_real')`)
- ❌ **🚨 CRÍTICO: COMMITAR TOKENS, SENHAS, API KEYS EM REPOSITÓRIO GIT**
- ❌ **CRIAR DOCUMENTOS (README, guias, tutoriais) SEM SOLICITAÇÃO EXPLÍCITA**
- ❌ Propor soluções que exijam ações do usuário sem perguntar primeiro
- ❌ Mudar abordagem quando falhar sem consultar o usuário

### Controle de Escopo Absoluto

**Antes de responder:**
> "Essa resposta foi solicitada exatamente?"

**Sempre perguntar antes de:**
- Propor soluções que exijam ações do usuário
- Mudar abordagem quando algo falhar
- Implementar requisitos não validados

---

## 🐳 CONTAINERS DESACOPLADOS

**Status:** Fase 6 completa (6A+6B+6C+6D) - 4 containers em produção (05/11/2025)

### Regra de Ouro: Zero Imports Diretos

**PROIBIDO:**
```python
# ❌ ERRADO - Import direto entre containers
from posp2.models import Terminal
from checkout.models import CheckoutCliente
from apps.ofertas.services import OfertaService
```

**OBRIGATÓRIO:**
```python
# ✅ CORRETO - Lazy import
from django.apps import apps

def minha_funcao():
    Terminal = apps.get_model('posp2', 'Terminal')
    terminal = Terminal.objects.get(id=1)
```

### 3 Estratégias de Comunicação (Fase 6B)

**1. APIs REST Internas (70% dos casos) - 40 endpoints**

```python
# Exemplo: Consultar cliente (POS → APIs)
from wallclub_core.integracoes.api_interna_service import APIInternaService

response = APIInternaService.chamar_api_interna(
    metodo='POST',
    endpoint='/api/internal/cliente/consultar_por_cpf/',
    payload={'cpf': '12345678900', 'canal_id': 1},
    contexto='apis',
    oauth_token=request.oauth_token.access_token
)

if response.get('sucesso'):
    data = response.json()
    saldo = data['saldo_disponivel']
```

**40 Endpoints Disponíveis:**
- **Cliente (API Interna):** 6 endpoints (consultar_por_cpf, cadastrar, obter_cliente_id, atualizar_celular, obter_dados_cliente, verificar_cadastro) ⭐ NOVO
- **Conta Digital:** 5 endpoints (consultar-saldo, autorizar-uso, debitar-saldo, estornar-saldo, calcular-maximo)
- **Checkout:** 16 endpoints
  - Recorrências: 8 endpoints (listar, criar, obter, pausar, reativar, cobrar, atualizar, deletar)
  - Clientes: 4 endpoints (listar, criar, obter, atualizar)
  - Tokens/Links: 4 endpoints (listar, criar, obter, validar)
- **Ofertas:** 6 endpoints (listar, criar, obter, atualizar, grupos/listar, grupos/criar)
- **Parâmetros:** 7 endpoints (configuracoes/loja, configuracoes/contar, configuracoes/ultima, loja/modalidades, planos, importacoes, importacoes/{id})

**Características:**
- ❌ Sem autenticação OAuth (isolamento de rede Docker)
- Sem rate limiting entre containers
- Timeout: 5s consulta, 10s escrita, 30s padrão
- Service helper: `wallclub_core.integracoes.api_interna_service.APIInternaService`
- Mapeamento automático de containers: `apis`, `pos`, `portais`, `riskengine`

**2. SQL Direto (25% - read-only)**

```python
# Exemplo: Buscar transações
from comum.database.queries import TransacoesQueries

transacoes = TransacoesQueries.listar_transacoes_periodo(
    loja_id=1,
    data_inicio='2025-11-01',
    data_fim='2025-11-30'
)
```

**Classes Disponíveis:**
- `TransacoesQueries` - 7 métodos
- `TerminaisQueries` - 2 métodos

**Regras:**
- ✅ Apenas leitura (SELECT)
- ✅ Queries complexas com performance crítica
- ❌ Nunca INSERT/UPDATE/DELETE
- ❌ Nunca acessar models Django de outro container

**3. Lazy Imports (5% - entidades compartilhadas)**

```python
# Usar apenas quando ABSOLUTAMENTE necessário
from django.apps import apps

def processar_cliente(cliente_id):
    Cliente = apps.get_model('cliente', 'Cliente')
    cliente = Cliente.objects.get(id=cliente_id)
    # ...
```

**Labels Corretos:**
- ✅ `'cliente'` (NÃO 'apps.cliente')
- ✅ `'ofertas'` (NÃO 'apps.ofertas')
- ✅ `'checkout'`
- ✅ `'pinbank'`
- ✅ `'posp2'`
- ✅ `'link_pagamento_web'` (NÃO 'checkout.link_pagamento_web')

### Validação Automática

```bash
# Rodar antes de commit
bash scripts/validar_dependencias.sh

# Esperado:
# ✓ SUCESSO: Containers desacoplados!
# Próximo: Fase 6C - Extrair CORE
```

### Type Hints com Lazy Imports

```python
from typing import Any  # Não usar tipo específico

def processar(terminal: Any) -> dict:  # ✅ CORRETO
    Terminal = apps.get_model('posp2', 'Terminal')
    # ...

# ❌ ERRADO - import direto para type hint
from posp2.models import Terminal
def processar(terminal: Terminal) -> dict:
    pass
```

### CORE Limpo

**Regra:** `comum/*` NUNCA importa de `apps/*`, `posp2/*`, `checkout/*`, `portais/*`

```python
# comum/services/exemplo.py

# ❌ ERRADO
from apps.cliente.models import Cliente

# ✅ CORRETO - CORE não conhece apps
# Caller deve passar dados necessários
def enviar_notificacao(cliente_id: int, celular: str, nome: str):
    # CORE só envia, não busca Cliente
    pass
```

**Validação CORE:**
```bash
bash scripts/validar_core_limpo.sh
# Esperado: CORE limpo, 0 imports diretos
```

---

## 💾 BANCO DE DADOS

### Collation Obrigatória (MySQL)

**Padrão:** `utf8mb4_unicode_ci` (compatível MySQL 5.7 e 8.0)

**Template CREATE TABLE:**
```sql
CREATE TABLE nome_tabela (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    campo_texto VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    campo_numero DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Converter Existente:**
```sql
-- Altera TUDO: estrutura + dados + colunas
ALTER TABLE nome_tabela
  CONVERT TO CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

**Verificar Inconsistências:**
```sql
-- Tabelas com collation diferente
SELECT TABLE_NAME, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_COLLATION != 'utf8mb4_unicode_ci';

-- Colunas com collation diferente
SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub'
  AND COLLATION_NAME IS NOT NULL
  AND COLLATION_NAME != 'utf8mb4_unicode_ci';
```

**Regra de Ouro:**
- ❌ NUNCA usar `COLLATE` em queries SQL
- ✅ Padronizar collation no schema
- Se precisar COLLATE na query = schema está errado

### Configurações Django

**OBRIGATÓRIO:**
- ❌ NÃO usar migrations Django
- ✅ SEMPRE criar tabelas via SQL direto
- ✅ Credenciais sempre via AWS Secrets Manager (sem fallback)

---

## 📅 TIMEZONE E DATAS

### Configuração Obrigatória

**Django settings:**
```python
USE_TZ = False
TIME_ZONE = 'America/Sao_Paulo'
```

**Container Docker:**
```dockerfile
ENV TZ=America/Sao_Paulo
```

### Uso Correto

**SEMPRE usar:**
```python
from datetime import datetime

# ✅ CORRETO
agora = datetime.now()
data_futura = datetime.now() + timedelta(days=30)
```

**EXCEÇÃO - Django timezone para campos específicos:**
```python
from django.utils import timezone

# ✅ PERMITIDO apenas em contextos específicos (ex: CashbackService)
# Quando o campo do model exige timezone-aware
agora = timezone.now()
```

**NUNCA usar em models com USE_TZ=False:**
```python
# ❌ ERRADO - Gera erro com MySQL
data_aware = timezone.make_aware(datetime.now())
```

**Motivo:** MySQL backend do Django não suporta timezone-aware datetimes quando USE_TZ=False, exceto em casos específicos onde o Django gerencia internamente

**Campos DATETIME (20/12/2025):**
- ✅ Tabela `terminais`: campos `inicio`/`fim` migrados de INT (Unix timestamp) para DATETIME
- ✅ Model `Terminal`: propriedades `ativo`, `inicio_date`, `fim_date` para compatibilidade
- ✅ Queries SQL: removido `UNIX_TIMESTAMP()`, comparação direta com `NOW()`
- ✅ Template filters: suportam DATETIME e Unix timestamp automaticamente

**Arquivos Corrigidos (26/10/2025):**
- posp2/models.py
- parametros_wallclub/models.py
- apps/cliente/models.py
- apps/conta_digital/models.py
- checkout/link_pagamento_web/models.py

---

## 💰 VALORES MONETÁRIOS

### Formatação e Armazenamento

**Frontend:**
- Aceitar entrada brasileira: `2.030,22` (vírgula decimal)
- Converter vírgula→ponto antes de enviar backend

**Backend:**
```python
# ✅ SEMPRE usar Decimal
from decimal import Decimal

valor = Decimal('110.50')  # Ponto decimal
percentual = Decimal('0.02')  # 2%

# ❌ NUNCA usar float
valor = 110.50  # Imprecisão
```

**Banco de Dados:**
```sql
valor_transacao DECIMAL(10,2)  -- SEMPRE com ponto
percentual_desconto DECIMAL(5,4)  -- Ex: 0.0199 = 1.99%
```

**Exibição:**
- Monetário: `R$ 2.030,22` (ponto=milhares, vírgula=decimal)
- Percentual: `0,2 → 20,00%` (multiplicar por 100)

**Campos HTML:**
```html
<!-- ✅ CORRETO: Evita flechinhas -->
<input type="text" name="valor" placeholder="110,50">

<!-- ❌ ERRADO: Flechinhas confundem usuário -->
<input type="number" name="valor">
```

### Validação

```python
def validar_valor_monetario(valor_str):
    """Aceita vírgula e ponto no input"""
    valor_str = valor_str.replace('.', '').replace(',', '.')
    return Decimal(valor_str)
```

---

## CONTA DIGITAL

### Estrutura de Saldos

**Campos Separados:**
```python
# Model ContaDigital
saldo_atual          # Dinheiro disponível
saldo_bloqueado      # Dinheiro bloqueado temporariamente
cashback_disponivel  # Cashback disponível para uso
cashback_bloqueado   # Cashback em retenção
```

**Regra de Ouro:** Saldo monetário e cashback são **SEMPRE** separados.

### Tipos de Movimentação

**Campo `afeta_cashback` em `TipoMovimentacao`:**
- `afeta_cashback=0` → Afeta `saldo_atual` e `saldo_bloqueado`
- `afeta_cashback=1` → Afeta `cashback_disponivel` e `cashback_bloqueado`

**Tipos Principais:**
```sql
-- Saldo monetário (afeta_cashback=0)
CREDITO, CREDITO_MANUAL, DEBITO, DEBITO_COMPRA, SAQUE

-- Cashback (afeta_cashback=1)
CASHBACK_CREDITO, CASHBACK_DEBITO

-- Bloqueios (afeta_cashback=0)
BLOQUEIO, DESBLOQUEIO
```

### Métodos do ContaDigitalService

**SEMPRE verificar `tipo_movimentacao.afeta_cashback`:**

```python
# CORRETO - Método creditar()
if tipo_movimentacao.afeta_cashback:
    if periodo_retencao_dias > 0:
        conta.cashback_bloqueado += valor
    else:
        conta.cashback_disponivel += valor
else:
    conta.saldo_atual += valor

# CORRETO - Método debitar()
if tipo_movimentacao.afeta_cashback:
    if conta.cashback_disponivel < valor:
        raise ValidationError("Cashback insuficiente")
    conta.cashback_disponivel -= valor
else:
    if not conta.tem_saldo_suficiente(valor):
        raise ValidationError("Saldo insuficiente")
    conta.saldo_atual -= valor

# CORRETO - Método estornar_movimentacao()
if movimentacao_original.tipo_movimentacao.afeta_cashback:
    # Estornar em cashback_disponivel
    conta.cashback_disponivel += valor
else:
    # Estornar em saldo_atual
    conta.saldo_atual += valor
```

**NUNCA misturar saldo e cashback:**
```python
# ERRADO - Sempre debita de saldo_atual
conta.saldo_atual -= valor  # Ignora se é cashback

# ERRADO - Sempre valida saldo_atual
if conta.saldo_atual < valor:  # Ignora cashback_disponivel
    raise ValidationError("Saldo insuficiente")
```

### Uso em Transações POS

**Débito de Cashback:**
```python
# CORRETO - Usar tipo CASHBACK_DEBITO
ContaDigitalService.debitar(
    cliente_id=cliente_id,
    canal_id=canal_id,
    valor=valor_cashback,
    descricao='Uso de cashback - Terminal PB59237K70569',
    tipo_codigo='CASHBACK_DEBITO',  # afeta_cashback=1
    referencia_externa=nsu,
    sistema_origem='POSP2'
)

# ERRADO - Usar tipo DEBITO para cashback
ContaDigitalService.debitar(
    tipo_codigo='DEBITO',  # afeta_cashback=0 - vai debitar saldo_atual!
    ...
)
```

**Validação de Saldo:**
```python
# CORRETO - Validar cashback disponível
if conta.cashback_disponivel < valor:
    raise ValidationError("Cashback insuficiente")

# ERRADO - Validar saldo monetário para cashback
if conta.saldo_atual < valor:  # Cliente tem R$ 0,00 mas R$ 27,29 em cashback
    raise ValidationError("Saldo insuficiente")
```

### Métodos Específicos

**Para Cashback:**
- `usar_cashback()` - Debita de `cashback_disponivel` (tipo `CASHBACK_DEBITO`)
- `creditar_cashback_transacao_pos()` - Credita em `cashback_disponivel` ou `cashback_bloqueado`
- `estornar_cashback_transacao_pos()` - Debita de `cashback_disponivel`
- `liberar_cashback_retido()` - Move de `cashback_bloqueado` para `cashback_disponivel`

**Para Saldo Monetário:**
- `bloquear_saldo()` - Move de `saldo_atual` para `saldo_bloqueado`
- `desbloquear_saldo()` - Move de `saldo_bloqueado` para `saldo_atual`

**Genéricos (verificam `afeta_cashback`):**
- `creditar()` - Credita em `saldo_atual` ou `cashback_disponivel`
- `debitar()` - Debita de `saldo_atual` ou `cashback_disponivel`
- `estornar_movimentacao()` - Estorna em `saldo_atual` ou `cashback_disponivel`

---

## APIS REST

### Método HTTP Obrigatório

**SEMPRE usar POST:**
```python
# ...
# ✅ CORRETO
@api_view(['POST'])
def minha_api(request):
    dados = request.data  # Body JSON
    cpf = dados.get('cpf')
```

**NUNCA usar GET/PUT/DELETE:**
- ❌ GET: expõe dados sensíveis na URL
- ❌ PUT/DELETE: complexidade desnecessária
- ✅ POST: parâmetros no body, simplifica POS/apps

**Motivos:**
- Simplifica integração terminais POS
- Evita problemas cache/logs de URL
- Dados sensíveis nunca expostos

### Formato de Resposta Padrão

**SEMPRE usar:**
```json
{
  "sucesso": true,
  "mensagem": "Operação realizada com sucesso",
  "dados": {...}
}
```

**NUNCA usar:**
```json
{
  "success": true,  // ❌ Inglês
  "error": "...",   // ❌ Inglês
  "data": {...}     // ❌ Inglês
}
```

### URLs de Arquivos

**SEMPRE salvar URLs completas:**
```python
# ✅ CORRETO
url_completa = f"https://apidj.wallclub.com.br/media/ofertas/{filename}"
oferta.imagem_url = url_completa

# ❌ ERRADO - Apps móveis precisam de URL absoluta
oferta.imagem_url = f"/media/ofertas/{filename}"
```

---

## 🔐 AUTENTICAÇÃO E SEGURANÇA

### 🚨 REGRA CRÍTICA: Gestão de Credenciais

**PROIBIDO ABSOLUTAMENTE:**
```python
# ❌ NUNCA expor credenciais em código
EMAIL_HOST_USER = 'AKIAXWHDLWAXPATSXOK6'
API_KEY = 'abc123...'
DB_PASSWORD = 'senha123'
```

**OBRIGATÓRIO:**
```python
# ✅ SEMPRE usar variáveis de ambiente ou AWS Secrets Manager
EMAIL_HOST_USER = os.environ.get('MAILSERVER_USERNAME')
API_KEY = secrets.get('API_KEY')
DB_PASSWORD = secrets.get('DB_PASSWORD')
MERCHANT_URL = os.environ.get('MERCHANT_URL')  # Obrigatória para Own Financial
```

### 🚨 REGRA CRÍTICA: Dados Sensíveis de Cartão (PCI-DSS)

**PROIBIDO ABSOLUTAMENTE:**
```python
# ❌ NUNCA trafegar número completo de cartão
payload = {
    'numero_cartao': numero_cartao,  # VIOLAÇÃO PCI-DSS
    'telefone': telefone
}

# ❌ NUNCA armazenar número completo
cartao.numero = '4111111111111111'  # VIOLAÇÃO PCI-DSS

# ❌ NUNCA enviar número completo para frontend
response = {
    'numero_cartao': cartao.numero  # VIOLAÇÃO PCI-DSS
}
```

**OBRIGATÓRIO:**
```python
# ✅ SEMPRE usar apenas últimos 4 dígitos
ultimos_4 = numero_cartao[-4:]
payload = {
    'ultimos_4_digitos': ultimos_4,
    'telefone': telefone
}

# ✅ SEMPRE armazenar apenas mascarado
cartao.cartao_mascarado = f"****{numero_cartao[-4:]}"

# ✅ SEMPRE tokenizar via gateway (Pinbank/Own)
token_id = gateway.tokenizar(numero_cartao)
cartao.id_token = token_id  # Salvar apenas token
```

**Regras PCI-DSS:**
1. ❌ **NUNCA** armazenar número completo do cartão
2. ❌ **NUNCA** armazenar CVV/CVC
3. ❌ **NUNCA** trafegar dados completos entre frontend/backend
4. ✅ **SEMPRE** tokenizar via gateway certificado
5. ✅ **SEMPRE** usar apenas últimos 4 dígitos para exibição
6. ✅ **SEMPRE** mascarar: `****1234` ou `4444########1234`

**Locais onde dados completos NUNCA devem aparecer:**
- ❌ Requests HTTP (query params ou body)
- ❌ Responses HTTP (JSON)
- ❌ Banco de dados (exceto gateway certificado)
- ❌ Logs de aplicação
- ❌ Cache (Redis/Memcached)
- ❌ Mensagens (WhatsApp/SMS/Email)

### GatewayRouter - Multi-Gateway de Pagamentos ⭐

**Status:** Implementado (29/01/2026)

**Regra de Ouro:** ❌ **NUNCA** instanciar `TransacoesPinbankService` ou `TransacoesOwnService` diretamente. ✅ **SEMPRE** usar `GatewayRouter`.

**Uso Correto:**
```python
from checkout.services_gateway_router import GatewayRouter

# Obter gateway ativo da loja
gateway = GatewayRouter.obter_gateway_loja(loja_id)  # 'PINBANK' ou 'OWN'

# Obter service correto
service = GatewayRouter.obter_service_transacao(loja_id)

# Processar conforme gateway
if gateway == GatewayRouter.GATEWAY_OWN:
    # Own Financial
    resultado = service.create_payment_with_registration(
        registration_id=token,
        amount=valor,
        parcelas=parcelas,
        loja_id=loja_id
    )
else:
    # Pinbank
    resultado = service.efetuar_transacao_cartao_tokenizado(payload)
```

**Uso INCORRETO:**
```python
# ❌ NUNCA fazer isso
from pinbank.services_transacoes_pagamento import TransacoesPinbankService
pinbank_service = TransacoesPinbankService(loja_id=loja_id)
```

**Ativação por Loja:**
```sql
-- Ativar Own Financial
UPDATE loja SET gateway_ativo = 'OWN' WHERE id = 15;

-- Ativar Pinbank (padrão)
UPDATE loja SET gateway_ativo = 'PINBANK' WHERE id = 15;
```

**Credenciais Own Financial:**
- Tabela: `loja_own`
- Campos: `entity_id`, `access_token`
- URLs: QA (`eu-test.oppwa.com`) e PROD (`eu-prod.oppwa.com`)

**Métodos Suportados:**
- Pagamento direto (cartão digitado)
- Tokenização (salvar cartão)
- Pagamento com token (MIT)
- Estorno
- Exclusão de token

**Arquivo:** `checkout/services_gateway_router.py`

**Variáveis Obrigatórias no `.env`:**
```bash
# Desenvolvimento (services/django/.env)
MERCHANT_URL=https://wallclub.com.br  # URL estabelecimento (payload Own)
CHECKOUT_BASE_URL=http://localhost:8007
BASE_URL=http://localhost:8005
```

**Variáveis Obrigatórias no `settings/base.py`:**
```python
# wallclub/settings/base.py
MERCHANT_URL = os.environ.get('MERCHANT_URL')  # Adicionar junto com outras URLs
```

**🚨 REGRA CRÍTICA: Credenciais NUNCA devem aparecer em:**
- ❌ Código Python (.py)
- ❌ Arquivos de configuração commitados (YAML, JSON, .conf)
- ❌ Documentação (.md)
- ❌ Scripts (.sh, .sql)
- ❌ Logs de aplicação
- ❌ **FALLBACK de variáveis de ambiente** (ex: `os.environ.get('TOKEN', 'valor_real')`)

**❌ PROIBIDO - Exemplos de código INSEGURO:**
```python
# NUNCA FAZER ISSO:
EMAIL_HOST_USER = os.environ.get('MAILSERVER_USERNAME', 'AKIAXWHDLWAXPATSXOK6')
bot_token = os.environ.get('TELEGRAM_TOKEN', '8352234743:AAELmuFIBsNeZ639dlUVOAozkUivpnKAj7w')
```

**✅ CORRETO - Usar ConfigManager ou variável obrigatória:**
```python
# Opção 1: ConfigManager (recomendado)
from wallclub_core.utilitarios.config_manager import get_config_manager
email_config = get_config_manager().get_email_config()
EMAIL_HOST_USER = email_config.get('user')  # Sem fallback

# Opção 2: Variável obrigatória (falha se não existir)
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']  # Sem fallback, levanta KeyError

# Opção 3: Validação explícita
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN não configurado")
```

**Usar:** AWS Secrets Manager (`wall/prod/db`, `wall/prod/oauth/*`, `wall/prod/integrations`)

---

### Sistema JWT Customizado ⭐ (Fase 1 + 4)

**Status:** 18 cenários testados (28/10/2025)
**Correção Crítica:** 26/10/2025 - Validação obrigatória contra tabela em produção**

**Tokens:**
- Access: 30 dias (JWT customizado)
- Refresh: 60 dias (reutilizável)

{{ ... }}
**Tabelas:**
- `cliente_jwt_tokens` - Auditoria completa
- `otp_autenticacao` - Códigos OTP (5min)
- `otp_dispositivo_confiavel` - Devices (30 dias)
- `cliente_autenticacao` - Tentativas login
- `cliente_bloqueios` - Histórico bloqueios
- `cliente_senhas_historico` - Histórico senhas

### Validação Obrigatória Tokens (26/10/2025)

**CRÍTICO - Falha de Segurança Corrigida:**

❌ **ERRADO:** Apenas decodificar JWT
```python
payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
return (ClienteUser(payload), token)
```

✅ **CORRETO:** Validar contra tabela
```python
payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])

# CRÍTICO: Validar contra tabela de auditoria
jti = payload.get('jti')
if jti:
    jwt_record = ClienteJWTToken.validate_token(token, jti)
    if not jwt_record:
        raise AuthenticationFailed('Token inválido ou revogado')
    jwt_record.record_usage()  # Registrar uso
else:
    raise AuthenticationFailed('Token inválido')

return (ClienteUser(payload), token)
```

### 5 Regras de Ouro - Tokens JWT

1. ✅ **SEMPRE validar JWT contra tabela** - nunca confiar apenas na decodificação
2. ✅ **SEMPRE revogar tokens anteriores** ao gerar novo
3. ✅ **SEMPRE incluir JTI** no payload (rejeitar sem JTI)
4. ✅ **SEMPRE registrar uso** (last_used, ip_address)
5. ✅ **NUNCA permitir múltiplos tokens ativos** para mesmo cliente

### Rate Limiting

**Progressivo:**
- 1ª tentativa: sem bloqueio
- 5 falhas/15min: bloqueio 1h
- 10 falhas/1h: bloqueio 24h
- 20 falhas/24h: bloqueio permanente (manual)

**Redis:**
```python
# Chaves
f"login_attempts:{cpf}:15min"
f"login_attempts:{cpf}:1h"
f"login_attempts:{cpf}:24h"

# TTLs
900s, 3600s, 86400s
```

### Login Simplificado Fintech (Fase 4 - 25/10/2025)

**Filosofia:** Senha sempre via SMS, revalidação recorrente (modelo Nubank/PicPay)

**Fluxo:**
```
Cadastro → Senha SMS (4 dígitos) → JWT 30 dias → Biometria
                                          ↓
                                   (Após 30 dias)
                                          ↓
                                   2FA → Novo JWT 30 dias
```

**Princípios:**
- ✅ NÃO existe "senha definitiva"
- ✅ JWT válido 30 dias (era 1 dia)
- ✅ Celular revalidado 30 dias (era 90)
- ✅ Biometria desde dia 1
- ✅ 2FA apenas quando necessário

**Inspiração:** Nubank, PicPay, Inter, C6 Bank

### OAuth 2.0

**Grant Type:** `client_credentials`
**Expiration:** 3600s (1h)
**Header:** `Authorization: Bearer <token>`

**Contextos Separados:**
- Admin: `RISK_ENGINE_ADMIN_CLIENT_ID/SECRET`
- POS: `RISK_ENGINE_POS_CLIENT_ID/SECRET`
- Internal: `RISK_ENGINE_INTERNAL_CLIENT_ID/SECRET`

---

## 🛡️ SISTEMA ANTIFRAUDE (Fase 2)

**Status:** Operacional desde 16/10/2025
**Integrações:** POSP2 + Checkout Web + Portal Admin

### Arquitetura Risk Engine

**Container:** wallclub-riskengine:8008
**Latência:** <200ms média
**Fail-open:** Erro não bloqueia transações

**Score de Risco:**
```
MaxMind (0-100) + Regras (+pontos) = Score Final

Decisão:
0-59: APROVADO ✅
60-79: REVISAR ⚠️
80-100: REPROVADO 🚫
```

### 9 Regras Antifraude (5 básicas + 4 autenticação)

**Regras Básicas:**
| # | Nome | Pontos | Lógica |
|---|------|--------|--------|
| 1 | Velocidade Alta | +80 | >3 tx em 10min |
| 2 | Valor Suspeito | +70 | >média × 3 |
| 3 | Dispositivo Novo | +50 | Fingerprint novo |
| 4 | Horário Incomum | +40 | 00h-05h |
| 5 | IP Suspeito | +90 | >5 CPFs no IP/24h |

**Regras Autenticação (Fase 2 - 30/10/2025):**
| # | Nome | Pontos | Lógica |
|---|------|--------|--------|
| 6 | Dispositivo Novo - Alto Valor | +70 | Device <7 dias + valor >R$500 |
| 7 | IP Novo + Histórico Bloqueios | +80 | IP <3 dias + 2+ bloqueios/30d |
| 8 | Múltiplas Tentativas Falhas | +60 | 5+ falhas/24h + taxa ≥30% |
| 9 | Cliente com Bloqueio Recente | +90 | Bloqueio <7 dias |

**Cálculo:** `score += peso × 10`

**Exceção:** Regra com `acao=REPROVAR` → REPROVADO (ignora score)

### Integrações

**POSP2:**
- Arquivo: `posp2/services_antifraude.py` (374 linhas)
- Intercepta linha ~333 (antes Pinbank)

**Checkout Web:**
- Arquivo: `checkout/services_antifraude.py` (268 linhas)
- Intercepta linhas 117-183 (antes Pinbank)
- 7 campos novos: score_risco, decisao_antifraude, motivo_bloqueio, etc
- 2 status novos: BLOQUEADA_ANTIFRAUDE, PENDENTE_REVISAO

**Decisões:**
- APROVADO: processa normalmente
- REPROVADO: bloqueia (não processa Pinbank)
- REVISAR: processa + marca para análise manual

### MaxMind minFraud

**Cache:** Redis 1h
**Fallback:** Score neutro 50
**Timeout:** 3s
**Custo:** R$ 50-75/mês

**Chave Redis:** `maxmind:{cpf}:{valor}:{ip}`

**Princípio:** Sistema NUNCA bloqueia por falha técnica

### Sistema Segurança Multi-Portal (Fase 2 - 23/10/2025)

**6 Detectores Automáticos (Celery 5min):**
1. Login Múltiplo (Sev 4) - 3+ IPs/10min
2. Tentativas Falhas (Sev 5) - 5+ reprovações/5min
3. IP Novo (Sev 3) - IP nunca visto
4. Horário Suspeito (Sev 2) - 02:00-05:00
5. Velocidade (Sev 4) - 10+ tx/5min
6. Localização Anômala - MaxMind GeoIP

**Middleware:**
- Valida IP/CPF antes login
- Fail-open (erro não bloqueia)
- Arquivo: `comum/middleware/security_validation.py`

**Bloqueio Automático:**
- Severidade 5 → bloqueio imediato
- Task: `bloquear_automatico_critico()` (10min)

---

## 📬 NOTIFICAÇÕES

### WhatsApp Business (29/10/2025)

**Templates Dinâmicos:**
- `2fa_login_app` (AUTHENTICATION)
- `senha_acesso` (AUTHENTICATION)
- `baixar_app` (UTILITY)

**Categorias:**
- AUTHENTICATION: sempre entrega
- UTILITY: funcional
- MARKETING: requer opt-in

**Ordem Parâmetros SMS:**
```
/TELEFONE/MENSAGEM/SHORTCODE/ASSUNTO
```

**URL Encoding:**
```python
# ✅ CORRETO: Preserva URLs
mensagem_encoded = quote(mensagem, safe=':/')
# Resultado: https://tinyurl.com/abc

# ❌ ERRADO: Codifica tudo
mensagem_encoded = quote(mensagem, safe='')
# Resultado: https:%2F%2Ftinyurl.com%2Fabc
```

### Push Notifications

**NUNCA hardcodar:**
```python
# ❌ ERRADO
payload["aps"]["category"] = "AUTORIZACAO_SALDO"

# ✅ CORRETO: Dinâmico do template
payload["aps"]["category"] = tipo_push  # Do banco
```

**Firebase (Android):**
```json
{
  "notification": {...},
  "data": {
    "tipo": "oferta",
    "oferta_id": "123"
  }
}
```

**APN (iOS):**
- Bundle ID: dinâmico da tabela canal
- Fallback: produção → sandbox automático
- Token: UUID completo (não truncar)

---

## 🐳 ARQUITETURA DOCKER

### 9 Containers Orquestrados (Fase 6D - 05/11/2025)

| Container | CPU | RAM | Porta | Workers | Módulos |
|-----------|-----|-----|-------|---------|---------|
| Portais | 1.0 | 1GB | 8005 | 3 | Admin/Vendas/Lojista |
| POS | 0.5 | 512MB | 8006 | 2 | Terminal POS |
| APIs | 1.0 | 1GB | 8007 | 4 | Mobile/Checkout |
| Risk Engine | 0.5 | 512MB | 8008 | 3 | Antifraude |
| Redis | 0.25 | 256MB | 6379 | - | Cache/Broker |
| Celery Worker | 0.5 | 512MB | - | 4 | Tasks |
| Celery Beat | 0.25 | 128MB | - | - | Scheduler |

### Deploy

**Completo:**
```bash
cd /var/www/wallclub_django
docker-compose down
docker-compose up -d --build
```

**Seletivo (mantém Redis):**
```bash
docker-compose up -d --build --no-deps web riskengine celery-worker celery-beat
```

**Logs:**
```bash
docker-compose logs -f web
docker-compose logs -f riskengine
docker-compose logs -f celery-worker
```

### Benefícios

- ✅ Isolamento responsabilidades
- ✅ Escalabilidade independente
- ✅ Resiliência (falha isolada)
- ✅ Deploy atômico ou seletivo
- ✅ Zero downtime cache

---

## 💻 BOAS PRÁTICAS DE CÓDIGO

### Gestão de Variáveis (24/10/2025)

**Regra de Ouro:** Resolver variáveis UMA ÚNICA VEZ

❌ **ERRADO:** Buscar múltiplas vezes
```python
id_loja = cursor.fetchone()[0]
# ... código ...
id_loja = cursor.fetchone()[0]  # SOBRESCREVE!
```

✅ **CORRETO:** Resolver no início
```python
id_loja = dados_terminal['loja_id']  # Linha 145

# Usar em todos cálculos
valor = calculadora.calcular(
    id_loja=id_loja  # Variável já resolvida
)
```

### Calculadoras Base (24/12/2025)

**Abstração Completa:**

**2 Calculadoras:**
- `CalculadoraBaseUnificada`: Wallet (Checkout + POS Pinbank/Own)
- `CalculadoraBaseCredenciadora`: TEF (Credenciadora)

**Regra de Ouro:** Calculadoras NÃO buscam dados

```python
# ❌ ERRADO - Buscar dados internamente
class Calculadora:
    def calcular(self, nsu):
        loja = Loja.objects.get(...)  # PROIBIDO
        canal = Canal.objects.get(...)  # PROIBIDO

# ✅ CORRETO - Receber tudo via parâmetros
class CalculadoraBaseUnificada:
    def calcular_valores_primarios(
        self,
        dados_linha: Dict[str, Any],
        tabela: str,
        info_loja: Dict[str, Any],  # OBRIGATÓRIO
        info_canal: Dict[str, Any]  # OBRIGATÓRIO
    ):
        # Usa apenas dados recebidos
        valores[6] = info_loja['id']
        valores[4] = info_canal['canal']
```

**Campos Adicionados:**
- `origem_transacao`: LINK_PAGAMENTO, RECORRENCIA, TEF, POS
- `tipo_operacao`: Wallet, Credenciadora

**Cargas Migradas:**
1. Checkout (LINK_PAGAMENTO, RECORRENCIA)
2. Credenciadora (TEF)
3. POS Pinbank (POS)
4. POS Own (POS)

**Deprecados:**
- `CalculadoraBaseGestao` → renomeado para `.bkp`
- `calculadora_tef.py` → renomeado para `.bkp`

### Cargas Pinbank (25/10/2025)

**Lições Aprendidas:**

1. **Processar lote residual:**
```python
# Sempre após loop principal
if lote_atual:
    with transaction.atomic():
        processar_lote(lote_atual)
```

2. **Evitar queries em loops:**
```python
# ✅ Montar info_loja localmente
linha['info_loja'] = {
    'id': linha.get('clienteId'),
    'loja': linha.get('razao_social')
}
```

3. **Não sobrescrever variáveis:**
```python
# valores[45] já foi calculado acima
# NÃO sobrescrever
```

4. **Preservar dados históricos:**
```python
# Data de pagamento é imutável
registro_existente = Model.objects.filter(nsu=nsu).first()
if registro_existente and registro_existente.data_pagamento:
    valores[45] = registro_existente.data_pagamento
```

### Sistema de Logs (28/10/2025)

**Níveis:**
- DEBUG: validações OK, fluxo normal
- INFO: operações concluídas
- WARNING: validações negadas, anomalias
- ERROR: exceções críticas

**Categoria:**
```python
import logging
logger = logging.getLogger('comum.modulo')
logger = logging.getLogger('apps.modulo')
```

**Boas Práticas:**
```python
# ✅ Sempre especificar nível
logger.debug(f"Token validado: {jti[:8]}...")
logger.info(f"Cliente {cliente_id} autenticado")
logger.warning(f"Rate limit: {cpf}")
logger.error(f"Erro crítico: {str(e)}")

# ✅ Mensagens descritivas
logger.info("✅ Senha trocada com sucesso")
logger.warning("⚠️ Dispositivo não confiável")
logger.error("❌ Falha ao processar pagamento")
```

### Nomenclatura

**Python:**
- Variáveis/funções: `snake_case`
- Classes: `PascalCase`
- Constantes: `UPPER_SNAKE_CASE`

**Arquivos:**
- Python: `snake_case.py`
- Templates: `snake_case.html`
- SQL: `snake_case.sql`

**Banco:**
- Tabelas: `snake_case` ou legado
- Colunas: `snake_case` ou camelCase (legado)

---

## 📚 REFERÊNCIAS RÁPIDAS

### Comandos Docker

**Desenvolvimento:**
```bash
# Subir ambiente dev (sem nginx, celery, flower)
cd /Users/jeanlessa/wall_projects/WallClub_backend
docker exec wallclub-redis redis-cli FLUSHALL
docker-compose -f docker-compose.yml -f docker-compose.dev.yml down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Status containers
docker ps

# Logs tempo real
docker logs wallclub-portais --tail 50 -f
docker logs wallclub-apis --tail 50 -f

# Restart container
docker-compose -f docker-compose.yml -f docker-compose.dev.yml restart wallclub-apis
```

**Produção:**
```bash
# Status containers
docker-compose ps

# Logs tempo real
docker-compose logs -f wallclub-portais

# Restart container
docker-compose restart wallclub-portais

# Entrar no container
docker exec -it wallclub-portais bash

# Redis CLI
docker exec -it wallclub-redis redis-cli
```

### Queries Úteis

```sql
-- Verificar collation
SELECT TABLE_NAME, TABLE_COLLATION
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'wallclub';

-- Tokens ativos
SELECT COUNT(*) FROM cliente_jwt_tokens
WHERE is_active = TRUE;

-- Bloqueios ativos
SELECT COUNT(*) FROM bloqueios_seguranca
WHERE ativo = TRUE;

-- Transações últimas 24h
SELECT COUNT(*) FROM baseTransacoesGestao
WHERE created_at >= NOW() - INTERVAL 24 HOUR;
```

### Health Checks

```bash
# APIs Mobile
curl http://localhost:8007/api/v1/health/

# Risk Engine
curl http://localhost:8008/api/antifraude/health/

# Redis
docker exec wallclub-redis redis-cli ping
```

---

## ⚠️ ATENÇÕES CRÍTICAS

### Segurança

1. ✅ Tokens JWT validados contra BD (26/10)
2. ✅ Rate limiting progressivo ativo
3. ✅ Fail-open em sistemas externos
4. ✅ Logs sem dados sensíveis completos
5. ✅ Credenciais via AWS Secrets

### Performance

1. ✅ Cache Redis (1h MaxMind)
2. ✅ Streaming cargas (100 registros/lote)
3. ✅ Queries otimizadas (sem N+1)
4. ✅ Decimal para monetários (não float)
5. ✅ Collation padronizada (sem conversões)

### Operacional

1. ✅ Deploy seletivo (mantém Redis)
2. ✅ Logs separados por container
3. ✅ Celery tasks monitoradas
4. ✅ Antifraude com latência <200ms
5. ✅ Backup volumes persistentes

---

**Última atualização:** 02/12/2025
**Próxima revisão:** Testes completos Cashback Loja
**Manutenção:** Jean Lessa + Claude AI

---

## 🎁 SISTEMA DE OFERTAS

**Status:** Implementado (01/12/2025)

### Estrutura de Tabelas

**ofertas:**
- `id`, `canal_id`, `loja_id`, `grupo_economico_id`
- `titulo`, `texto_push`, `descricao`, `imagem_url`
- `vigencia_inicio`, `vigencia_fim`, `ativo`
- `tipo_segmentacao` (todos_canal, grupo_customizado)
- `grupo_id` (referência a grupos de clientes)
- `usuario_criador_id`, `created_at`, `updated_at`

**ofertas_grupos_segmentacao:**
- `id`, `canal_id`, `nome`, `descricao`
- `criterio_tipo` (manual, regra_automatica)
- `criterio_json`, `ativo`

**ofertas_grupos_clientes:**
- `id`, `grupo_id`, `cliente_id`, `adicionado_em`

**oferta_disparos:**
- `id`, `oferta_id`, `data_disparo`, `usuario_disparador_id`
- `status` (processando, concluido, erro)
- `total_clientes`, `total_enviados`, `total_falhas`

**oferta_envios:**
- `id`, `oferta_disparo_id`, `cliente_id`
- `enviado`, `data_envio`, `erro`

### Regras de Negócio

**Escopo da Oferta:**
```python
# Loja específica
loja_id = 123
grupo_economico_id = NULL

# Todas as lojas do grupo econômico
loja_id = NULL
grupo_economico_id = 456
```

**Segmentação de Clientes:**
```python
# Todos os clientes do canal
tipo_segmentacao = 'todos_canal'
grupo_id = NULL

# Grupo customizado
tipo_segmentacao = 'grupo_customizado'
grupo_id = 789
```

**Permissões:**
- **Portal Lojista:** Sempre cria com `loja_id` ou `grupo_economico_id`
- **Portal Admin:** Pode criar com `loja_id=NULL` e `grupo_economico_id=NULL` (todas as lojas do canal)

**Disparo de Push:**
```python
# Service busca clientes elegíveis baseado em:
# 1. tipo_segmentacao (todos_canal ou grupo_customizado)
# 2. Clientes ativos com firebase_token
# 3. Registra disparo e envios individuais
```

### Portal Lojista

**Menu:** `/ofertas/` (visível no sidebar)

**Funcionalidades:**
- Listar ofertas (próprias + globais do admin)
- Criar oferta (com escopo loja ou grupo econômico)
- Editar oferta (apenas próprias)
- Disparar push (apenas próprias)
- Histórico de disparos

**Filtros:**
```python
# Lista ofertas da loja OU ofertas globais (admin)
ofertas = Oferta.objects.filter(
    canal_id=canal_id,
    Q(loja_id=loja_id) | Q(loja_id__isnull=True)
)
```

### APIs Internas

**Ofertas Service:**
- `criar_oferta()` - Criar nova oferta
- `listar_ofertas_vigentes(cliente_id)` - Ofertas para cliente
- `disparar_push(oferta_id)` - Enviar push notification
- `buscar_clientes_elegiveis()` - Clientes para disparo

**Status:** ⚠️ Em testes (aguardando validação em produção)

---

## 💰 SISTEMA DE CASHBACK CENTRALIZADO

**Status:** Implementado (02/12/2025)

### Estrutura de Tabelas

**cashback_regra_loja:**
- `id`, `loja_id`, `nome`, `descricao`, `ativo`, `prioridade`
- `tipo_concessao` (FIXO, PERCENTUAL), `valor_concessao`
- `valor_minimo_compra`, `valor_maximo_cashback`
- `formas_pagamento` (JSON: PIX, DEBITO, CREDITO), `dias_semana` (JSON: 0-6)
- `horario_inicio`, `horario_fim`
- `limite_uso_cliente_dia`, `limite_uso_cliente_mes`
- `orcamento_mensal`, `gasto_mes_atual`
- `vigencia_inicio`, `vigencia_fim`

**cashback_uso:**
- `id`, `tipo_origem` (WALL, LOJA)
- `parametro_wall_id`, `regra_loja_id`
- `cliente_id`, `loja_id`, `canal_id`
- `transacao_tipo` (POS, CHECKOUT), `transacao_id`
- `valor_transacao`, `valor_cashback`
- `status` (RETIDO, LIBERADO, EXPIRADO, ESTORNADO)
- `aplicado_em`, `liberado_em`, `expira_em`
- `movimentacao_id` (referência conta digital)

**transactiondata_own (campos renomeados):**
- `desconto_wall` - Desconto Wall aplicado (wall=S)
- `cashback_debitado` - Cashback usado para pagar
- `cashback_creditado_wall` - Cashback Wall concedido
- `cashback_creditado_loja` - Cashback Loja concedido (NOVO)
- `autorizacao_uso_saldo_id` - ID autorização uso saldo
- `saldo_debitado` - Saldo conta digital usado

### Regras de Negócio

**Cashback Wall:**
- Concedido pela plataforma WallClub
- Baseado em parâmetros globais (wall='C')
- Custo absorvido pela WallClub

**Cashback Loja:**
- Concedido pela loja (regras customizadas)
- Lojista define: valor, condições, limites
- Custo absorvido pela loja
- Prioridade: maior número = maior prioridade

**Retenção e Expiração (Global):**
```python
# settings/base.py
CASHBACK_PERIODO_RETENCAO_DIAS = 30  # Dias retido antes de liberar
CASHBACK_PERIODO_EXPIRACAO_DIAS = 90  # Dias após liberação para expirar
```

**Fluxo de Estados:**
1. `RETIDO` - Creditado mas bloqueado (30 dias)
2. `LIBERADO` - Disponível para uso (90 dias)
3. `EXPIRADO` - Não usado no prazo
4. `ESTORNADO` - Transação estornada

### APIs REST

**Simulação V2 (POSP2):**
```bash
POST /api/v1/posp2/simula_parcelas_v2/
{
  "valor": 100.00,
  "terminal": "PB59237K70569",
  "wall": "s",
  "cliente_id": 123
}

# Resposta inclui:
{
  "cashback_wall": {"valor": "0.00", "percentual": "0.00"},
  "cashback_loja": {
    "aplicavel": true,
    "valor": "5.00",
    "regra_id": 2,
    "regra_nome": "Cashback 5% PIX"
  },
  "cashback_total": "5.00"
}
```

**Aplicação de Cashback:**
```python
# Após transação aprovada (trdata_own)
CashbackService.aplicar_cashback_wall(
    parametro_wall_id=1,
    cliente_id=123,
    loja_id=456,
    canal_id=1,
    transacao_tipo='POS',
    transacao_id=789,
    valor_transacao=Decimal('100.00'),
    valor_cashback=Decimal('5.00')
)

CashbackService.aplicar_cashback_loja(
    regra_loja_id=2,
    cliente_id=123,
    loja_id=456,
    canal_id=1,
    transacao_tipo='POS',
    transacao_id=789,
    valor_transacao=Decimal('100.00'),
    valor_cashback=Decimal('5.00')
)
```

### Portal Lojista

**Menu:** `/cashback/` (CRUD completo)

**Funcionalidades:**
- Listar regras (filtros: busca, status, vigência)
- Criar/Editar regra (formulário completo)
- Ativar/Desativar regra
- Detalhes + estatísticas de uso
- Relatório de uso com filtros avançados

**Validações:**
- Lojista só gerencia regras da própria loja
- Orçamento mensal controlado automaticamente
- Limites de uso por cliente validados

### Jobs Celery

**Diários:**
- `liberar_cashback_retido()` - Libera cashback após período de retenção
- `expirar_cashback_vencido()` - Expira cashback não usado

**Mensais:**
- `resetar_gasto_mensal_lojas()` - Zera `gasto_mes_atual` dia 1

### Contabilização

**Separação de Custos:**
- Cashback Wall: custo WallClub (`tipo_origem='WALL'`)
- Cashback Loja: custo Loja (`tipo_origem='LOJA'`)
- Relatórios separados por tipo de origem

**Status:** ✅ Em produção (simulação V2 funcionando)

---

## 📊 CONTA DIGITAL - COMPRAS INFORMATIVAS

**Status:** Implementado (08/12/2025)

### Tipo de Movimentação COMPRA_CARTAO

**Características:**
- Registro informativo (não afeta saldo)
- Exibe histórico completo de compras no extrato
- Armazena dados da transação em JSON

**Tabela:** `conta_digital_tipo_movimentacao`
```sql
codigo: 'COMPRA_CARTAO'
nome: 'Compra com Cartão'
descricao: 'Registro informativo de compra (não afeta saldo)'
debita_saldo: FALSE
permite_estorno: FALSE
visivel_extrato: TRUE
categoria: 'DEBITO'
afeta_cashback: FALSE
```

### Método ContaDigitalService.registrar_compra_informativa()

**Parâmetros:**
```python
def registrar_compra_informativa(
    cliente_id: int,
    canal_id: int,
    valor: Decimal,
    descricao: str,
    referencia_externa: str = None,  # NSU da transação
    sistema_origem: str = 'POSP2',   # POSP2, CHECKOUT
    dados_adicionais: dict = None    # JSON com detalhes
):
```

**Dados Adicionais (JSON):**
```json
{
  "forma_pagamento": "PIX|DEBITO|CREDITO",
  "parcelas": 1,
  "bandeira": "MASTERCARD",
  "estabelecimento": "Nome da Loja",
  "valor_original": 100.00,
  "desconto_aplicado": 10.00,
  "cupom_desconto": 5.00,
  "cashback_concedido": 2.50
}
```

### Integração nos Fluxos

**POS Own (Implementado):**
```python
# services/django/posp2/services_transacao_own.py
# Após salvar transação e aplicar cashback/cupom
ContaDigitalService.registrar_compra_informativa(
    cliente_id=cliente_id,
    canal_id=canal_id,
    valor=valor_final_pago,
    descricao=f"Compra - {loja_nome}",
    referencia_externa=nsu,
    sistema_origem='POSP2',
    dados_adicionais={...}
)
```

**POS Pinbank (Pendente):**
- Integrar em `services_transacao.py`

**Checkout Web (Pendente):**
- Integrar em fluxo de pagamento aprovado

### Visualização no Extrato

**Movimentações exibidas:**
1. Compra informativa (COMPRA_CARTAO)
2. Débito de saldo (se usado)
3. Débito de cashback (se usado)
4. Crédito de cashback (se concedido)

**Exemplo de extrato:**
```
08/12/2025 14:30 - Compra - Loja ABC        R$ 95,00
08/12/2025 14:30 - Cashback concedido       R$ 2,50
```

**Status:** ✅ POS Own implementado | ⏳ POS Pinbank e Checkout pendentes

---

## 📈 PORTAL LOJISTA - VENDAS POR OPERADOR

**Status:** Implementado (08/12/2025)

### Funcionalidade

**Localização:** `/vendas/` → Botão "Pesquisar venda por operador"

**Página:** `/vendas/operador/`

**Filtros:**
- Data inicial/final (obrigatórios)
- Loja (se múltiplas lojas)
- NSU (opcional)

### Query Agrupada

```sql
SELECT
    x.nome AS nome_operador,
    SUM(x.var11) AS valor_total,
    COUNT(1) AS qtde_vendas
FROM (
    SELECT DISTINCT
        b.var9, b.var6, b.var11,
        t.operador_pos,
        teops.nome
    FROM baseTransacoesGestao b
    INNER JOIN transactiondata t ON b.var9 = t.nsuPinbank
    LEFT JOIN terminais_operadores_pos tepos ON t.operador_pos = tepos.id
    LEFT JOIN terminais_operadores teops ON tepos.operador = teops.operador
    WHERE {filtros}
        AND t.operador_pos IS NOT NULL
) x
GROUP BY x.nome
ORDER BY valor_total DESC
```

### Relatório Exibido

**Cards de Totais:**
- Total de operadores
- Total de vendas
- Valor total

**Tabela:**
- Nome do operador
- Quantidade de vendas
- Valor total (R$)
- Ticket médio (calculado)

**Totalizador:** Linha final com soma geral

**Arquivos:**
- Template: `portais/lojista/templates/portais/lojista/vendas_operador.html`
- View: `portais/lojista/views_vendas_operador.py`
- URL: `vendas/operador/`

**Status:** ✅ Implementado e funcional

