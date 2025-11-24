# SISTEMA DE CUPOM DE DESCONTO - ESPECIFICAÇÃO TÉCNICA

**Versão:** 1.0
**Data:** 23/11/2025
**Status:** Especificação para implementação

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Regras de Negócio](#regras-de-negócio)
3. [Estrutura de Dados](#estrutura-de-dados)
4. [Fluxos de Integração](#fluxos-de-integração)
5. [Validações](#validações)
6. [Impacto em Sistemas Existentes](#impacto-em-sistemas-existentes)
7. [Contabilização](#contabilização)
8. [Implementação por Etapas](#implementação-por-etapas)

---

## 🎯 VISÃO GERAL

### Objetivo

Implementar sistema de cupons de desconto que permite lojas oferecerem descontos fixos ou percentuais aos clientes, aplicável tanto em transações POS quanto Checkout Web.

### Características Principais

- ✅ Funciona em **POSP2** (Terminal POS) e **Checkout Web**
- ✅ Suporta 2 tipos: **Genérico** (múltiplos usos) e **Individual** (1 uso por CPF)
- ✅ Desconto **fixo** (R$ 10,00) ou **percentual** (15%)
- ✅ Aplicado **após todos os cálculos** (Pinbank + Wall + Cashback)
- ✅ Custo do desconto **sempre arcado pela loja**
- ✅ Antifraude analisa **valor com desconto aplicado**
- ✅ Cupom usado **não retorna** em caso de estorno (prevenção fraude)

---

## 📐 REGRAS DE NEGÓCIO

### RN01 - Tipos de Cupom

| Tipo | Descrição | Limite Uso |
|------|-----------|------------|
| **GENERICO** | Qualquer cliente pode usar | Limite global (ex: 100 usos totais) |
| **INDIVIDUAL** | Vinculado a CPF específico | 1 uso por CPF |

### RN02 - Tipos de Desconto

| Tipo | Exemplo | Cálculo |
|------|---------|---------|
| **FIXO** | R$ 10,00 | Subtrai valor fixo |
| **PERCENTUAL** | 15% | `valor_transacao * (percentual / 100)` |

### RN03 - Ordem de Aplicação de Descontos

```
1. Valor Original da Transação
2. Desconto Pinbank/Own (calculadora)
3. Desconto Wall (calculadora)
4. Cashback (se aplicável)
5. ➡️ CUPOM (aplicado por último)
   = Valor Final
```

### RN04 - Validações Obrigatórias

1. ✅ Cupom existe e está ativo
2. ✅ Cupom está dentro da validade
3. ✅ Cupom pertence à loja da transação
4. ✅ **Valor da transação atende valor mínimo** (campo obrigatório)
5. ✅ Cupom ainda tem usos disponíveis (limite global)
6. ✅ Cliente não usou (se tipo INDIVIDUAL)
7. ✅ Código do cupom é válido (case-insensitive)

### RN05 - Comportamento em Estorno

**IMPORTANTE:** Cupom usado **NÃO retorna** em caso de estorno.

**Motivo:** Prevenção de fraude (cliente compra, usa cupom, estorna, reutiliza).

**Exceção:** Estorno por erro operacional pode ser tratado manualmente no portal admin.

### RN06 - Antifraude

- Antifraude analisa **valor final COM desconto do cupom**
- Futuro: Detectar padrões de fraude com cupons (ex: múltiplos CPFs usando mesmo cupom genérico)

---

## 🗄️ ESTRUTURA DE DADOS

### Tabela: `cupom`

```sql
CREATE TABLE cupom (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(50) NOT NULL UNIQUE COLLATE utf8mb4_unicode_ci,
    loja_id BIGINT NOT NULL,
    tipo_cupom ENUM('GENERICO', 'INDIVIDUAL') NOT NULL DEFAULT 'GENERICO',
    tipo_desconto ENUM('FIXO', 'PERCENTUAL') NOT NULL,
    valor_desconto DECIMAL(10,2) NOT NULL COMMENT 'Valor fixo em R$ ou percentual (ex: 15.00 = 15%)',
    valor_minimo_compra DECIMAL(10,2) DEFAULT NULL COMMENT 'Valor mínimo da transação para usar o cupom',
    limite_uso_total INT DEFAULT NULL COMMENT 'Limite de usos totais (NULL = ilimitado)',
    limite_uso_por_cpf INT DEFAULT 1 COMMENT 'Quantas vezes o mesmo CPF pode usar',
    quantidade_usada INT DEFAULT 0 COMMENT 'Contador de usos',
    cliente_id BIGINT DEFAULT NULL COMMENT 'Se tipo INDIVIDUAL, CPF vinculado',
    data_inicio DATETIME NOT NULL,
    data_fim DATETIME NOT NULL,
    ativo TINYINT(1) DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_codigo (codigo),
    INDEX idx_loja_ativo (loja_id, ativo),
    INDEX idx_cliente (cliente_id),
    FOREIGN KEY (loja_id) REFERENCES loja(id),
    FOREIGN KEY (cliente_id) REFERENCES cliente(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Tabela: `cupom_uso`

```sql
CREATE TABLE cupom_uso (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    cupom_id BIGINT NOT NULL,
    cliente_id BIGINT NOT NULL,
    loja_id BIGINT NOT NULL,
    transacao_tipo ENUM('POS', 'CHECKOUT') NOT NULL,
    transacao_id BIGINT NOT NULL COMMENT 'ID da TransactionData ou CheckoutTransaction',
    nsu VARCHAR(50) DEFAULT NULL COMMENT 'NSU da transação (se disponível)',
    valor_transacao_original DECIMAL(10,2) NOT NULL,
    valor_desconto_aplicado DECIMAL(10,2) NOT NULL,
    valor_transacao_final DECIMAL(10,2) NOT NULL,
    estornado TINYINT(1) DEFAULT 0,
    usado_em DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45) DEFAULT NULL,

    INDEX idx_cupom (cupom_id),
    INDEX idx_cliente (cliente_id),
    INDEX idx_transacao (transacao_tipo, transacao_id),
    INDEX idx_usado_em (usado_em),
    FOREIGN KEY (cupom_id) REFERENCES cupom(id),
    FOREIGN KEY (cliente_id) REFERENCES cliente(id),
    FOREIGN KEY (loja_id) REFERENCES loja(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Alterações em Tabelas Existentes

```sql
-- TransactionData (POSP2 - Pinbank)
ALTER TABLE transactiondata
ADD COLUMN cupom_id BIGINT DEFAULT NULL COMMENT 'ID do cupom usado',
ADD COLUMN cupom_valor_desconto DECIMAL(10,2) DEFAULT NULL COMMENT 'Valor do desconto do cupom',
ADD INDEX idx_cupom_id (cupom_id);

-- TransactionDataOwn (POSP2 - Own)
ALTER TABLE transactiondata_own
ADD COLUMN cupom_id BIGINT DEFAULT NULL COMMENT 'ID do cupom usado',
ADD COLUMN cupom_valor_desconto DECIMAL(10,2) DEFAULT NULL COMMENT 'Valor do desconto do cupom',
ADD INDEX idx_cupom_id (cupom_id);

-- CheckoutTransaction (Checkout Web)
ALTER TABLE checkoutTransaction
ADD COLUMN cupom_id BIGINT DEFAULT NULL COMMENT 'ID do cupom usado',
ADD COLUMN cupom_valor_desconto DECIMAL(10,2) DEFAULT NULL COMMENT 'Valor do desconto do cupom',
ADD INDEX idx_cupom_id (cupom_id);

-- BaseTransacoesGestao (Contabilização)
ALTER TABLE baseTransacoesGestao
ADD COLUMN cupom_id BIGINT DEFAULT NULL COMMENT 'ID do cupom usado',
ADD COLUMN cupom_valor_desconto DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Desconto do cupom (custo da loja)',
ADD INDEX idx_cupom_id (cupom_id);
```

**Nota:** Apenas `cupom_id` (FK) é armazenado. O código do cupom pode ser obtido via JOIN quando necessário.

---

## 🔄 FLUXOS DE INTEGRAÇÃO

### Fluxo 1: POSP2 (Terminal POS)

```
1. Terminal envia transação com cupom_codigo (opcional)
2. TRDataService.processar_transacao() - Valida dados básicos
3. CupomService.validar_e_aplicar() - Valida cupom, calcula desconto
4. CalculadoraDesconto.calcular() - Aplica cupom por último
5. RiskEngineService.analisar() - Analisa com valor final (COM desconto)
6. Pinbank/Own - Processa pagamento com valor final
7. CupomService.registrar_uso() - Incrementa contador, insere histórico
8. BaseGestaoService - Contabiliza cupom_valor_desconto (custo loja)
```

### Fluxo 2: Checkout Web

```
1. Cliente informa cupom no formulário
2. API /validar_cupom/ (AJAX) - Valida em tempo real, retorna desconto
3. LinkPagamentoTransactionService.processar() - Valida OTP + aplica cupom
4. RiskEngineService.analisar() - Analisa com valor final
5. Pinbank - Processa pagamento
6. CupomService.registrar_uso() - Registra uso
```

### Fluxo 3: Estorno

```
1. Estorno solicitado
2. Pinbank/Own - Processa estorno do valor final (COM desconto)
3. CupomService.registrar_estorno() - Marca estornado=1 em cupom_uso
   ❌ NÃO decrementa quantidade_usada
   ❌ NÃO permite reutilização (prevenção fraude)
4. BaseGestaoService - Ajusta contabilização
```

---

## ✅ VALIDAÇÕES

```python
# 1. Cupom existe e ativo
cupom = Cupom.objects.filter(codigo__iexact=codigo, ativo=True).first()
if not cupom:
    raise ValidationError("Cupom inválido ou inativo")

# 2. Validade
agora = datetime.now()
if not (cupom.data_inicio <= agora <= cupom.data_fim):
    raise ValidationError("Cupom fora do período de validade")

# 3. Loja correta
if cupom.loja_id != transacao_loja_id:
    raise ValidationError("Cupom não pertence a esta loja")

# 4. Valor mínimo
if cupom.valor_minimo_compra and valor < cupom.valor_minimo_compra:
    raise ValidationError(f"Valor mínimo: R$ {cupom.valor_minimo_compra}")

# 5. Limite global
if cupom.limite_uso_total and cupom.quantidade_usada >= cupom.limite_uso_total:
    raise ValidationError("Cupom esgotado")

# 6. Limite por CPF
if cupom.tipo_cupom == 'INDIVIDUAL':
    usos = CupomUso.objects.filter(cupom_id=cupom.id, cliente_id=cliente_id).count()
    if usos >= cupom.limite_uso_por_cpf:
        raise ValidationError("Você já usou este cupom")

# 7. Cliente vinculado
if cupom.tipo_cupom == 'INDIVIDUAL' and cupom.cliente_id:
    if cupom.cliente_id != cliente_id:
        raise ValidationError("Este cupom não é válido para você")
```

---

## 🔧 IMPACTO EM SISTEMAS EXISTENTES

### 1. TRDataService (posp2/services_transacao.py)

```python
def processar_transacao(self, dados):
    # 1. Calculadora faz o trabalho dela (SEM cupom)
    resultado_calculadora = calculadora.calcular(
        valor_transacao=valor_transacao,
        modalidade=modalidade,
        plano_id=plano_id,
        loja_id=loja_id
    )
    valor_liquido = resultado_calculadora['valor_liquido']

    # 2. Aplicar cupom DEPOIS (se informado)
    cupom_codigo = dados.get('cupom_codigo')
    cupom_obj = None
    desconto_cupom = Decimal('0.00')
    valor_final = valor_liquido

    if cupom_codigo:
        cupom_service = CupomService()
        cupom_obj = cupom_service.validar_cupom(
            codigo=cupom_codigo,
            loja_id=loja_id,
            cliente_id=cliente_id,
            valor_transacao=valor_liquido  # Valida sobre valor já com descontos
        )

        # Calcula desconto do cupom
        desconto_cupom = cupom_service.calcular_desconto(cupom_obj, valor_liquido)
        valor_final = valor_liquido - desconto_cupom

    # 3. Enviar para antifraude e gateway com valor_final
    # ... resto do código ...

    # 4. Salvar transação
    transaction_data = TransactionData(
        ...,
        cupom_id=cupom_obj.id if cupom_obj else None,
        cupom_valor_desconto=desconto_cupom
    )
    transaction_data.save()

    # 5. Registrar uso do cupom
    if cupom_obj:
        cupom_service.registrar_uso(
            cupom=cupom_obj,
            cliente_id=cliente_id,
            transacao_tipo='POS',
            transacao_id=transaction_data.id,
            valor_original=valor_liquido,
            valor_desconto=desconto_cupom,
            valor_final=valor_final
        )
```

### 2. LinkPagamentoTransactionService (checkout/services.py)

```python
def processar_pagamento(self, checkout_transaction, dados):
    # 1. Calculadora faz o trabalho dela (SEM cupom)
    resultado_calculadora = calculadora.calcular(...)
    valor_liquido = resultado_calculadora['valor_liquido']

    # 2. Aplicar cupom DEPOIS (se informado)
    cupom_codigo = dados.get('cupom_codigo')
    desconto_cupom = Decimal('0.00')
    valor_final = valor_liquido

    if cupom_codigo:
        cupom_service = CupomService()
        cupom_obj = cupom_service.validar_cupom(...)
        desconto_cupom = cupom_service.calcular_desconto(cupom_obj, valor_liquido)
        valor_final = valor_liquido - desconto_cupom

    # 3. Antifraude + Gateway com valor_final
    # 4. Salvar e registrar uso
```

### 3. CalculadoraBaseGestao (pinbank/cargas_pinbank/services.py)

```python
# Adicionar campo cupom_valor_desconto ao processar cargas
valores[XX] = transaction_data.cupom_valor_desconto or Decimal('0.00')
```

---

## 💰 CONTABILIZAÇÃO

### Impacto no Repasse

```
Valor Original:      R$ 100,00
- Desconto Pinbank:  R$ 2,00
- Desconto Wall:     R$ 1,00
- Cupom (loja):      R$ 10,00  ← CUSTO DA LOJA
= Valor Final:       R$ 87,00

Repasse Loja: R$ 87,00 - Taxas - Cupom = R$ 72,00
```

### Relatórios Impactados

1. **RPR** - Adicionar coluna "Cupom Desconto"
2. **Gestão Admin** - Filtro por cupom, total descontos
3. **Portal Lojista** - Dashboard cupons, performance

---

## 🏗️ IMPLEMENTAÇÃO POR ETAPAS

### ✅ Etapa 1: Estrutura Base - CONCLUÍDA
- ✅ Criar app `apps/cupom/`
- ✅ Models: `Cupom`, `CupomUso`
- ✅ `CupomService` com validações (7 validações obrigatórias)
- ✅ Admin Django básico
- ✅ Campo `valor_minimo_compra` tornado obrigatório (default 0)

**Arquivos criados:**
- `apps/cupom/models.py` (268 linhas)
- `apps/cupom/services.py` (234 linhas)
- `apps/cupom/admin.py` (145 linhas)
- `apps/cupom/apps.py`

### ✅ Etapa 2: Integração Own (POSP2) - CONCLUÍDA
- ✅ Campos adicionados em `TransactionDataOwn` (cupom_id, cupom_valor_desconto)
- ✅ Modificar `TRDataOwnService.processar_transacao()`
- ✅ Validação e aplicação de cupom (opcional)
- ✅ Registro de uso do cupom
- ✅ Retrocompatibilidade garantida (terminal sem cupom funciona normal)

**SQL executado:**
```sql
ALTER TABLE transactiondata_own
ADD COLUMN cupom_id BIGINT DEFAULT NULL,
ADD COLUMN cupom_valor_desconto DECIMAL(10,2) DEFAULT NULL,
ADD INDEX idx_cupom_id (cupom_id);
```

**Arquivos modificados:**
- `posp2/models.py` - TransactionDataOwn
- `posp2/services_transacao_own.py` - Integração completa

### ✅ Etapa 3: Portal Lojista (CRUD) - CONCLUÍDA
- ✅ Views completas (6 views)
- ✅ URLs configuradas
- ✅ Templates HTML (4 templates)
- ✅ Validações e logs de auditoria

**Funcionalidades:**
- Lista com filtros (busca, status, vigência) e paginação
- Criar/Editar cupom (formulário completo)
- Detalhes + estatísticas de uso
- Ativar/Desativar cupom
- Relatório de uso com ranking

**Arquivos criados:**
- `portais/lojista/views_cupons.py` (280 linhas)
- `portais/lojista/templates/portais/lojista/cupons/lista.html`
- `portais/lojista/templates/portais/lojista/cupons/form.html`
- `portais/lojista/templates/portais/lojista/cupons/detalhe.html`
- `portais/lojista/templates/portais/lojista/cupons/relatorio.html`

**Arquivos modificados:**
- `portais/lojista/urls.py` - 6 URLs adicionadas

### ✅ Etapa 4: APIs REST - CONCLUÍDA
**APIs implementadas:**
1. `GET /api/v1/cupons/ativos/` - Lista cupons ativos disponíveis para o cliente (App Mobile)
2. `POST /api/v1/cupons/validar/` - Valida cupom e retorna desconto (POS + Checkout Web)

**Autenticação:**
- API de listagem: `ClienteJWTAuthentication` (JWT do cliente mobile) - extrai `cliente_id` automaticamente do token
- API de validação: Aceita qualquer autenticação configurada (OAuth Token do POS ou JWT)
- Ambas usam `permission_classes = [IsAuthenticated]`

**IMPORTANTE:** A validação do cupom no POS e Checkout usa **exatamente a mesma API** `/api/v1/cupons/validar/` para garantir consistência.

**Payload da API de validação:**
```json
{
  "codigo": "PROMO10",
  "loja_id": 26,
  "cliente_id": 123,
  "valor_transacao": 100.00
}
```

**Response sucesso:**
```json
{
  "valido": true,
  "cupom_id": 1,
  "valor_desconto": 10.00,
  "valor_final": 90.00,
  "mensagem": "Cupom aplicado com sucesso"
}
```

**Response erro:**
```json
{
  "valido": false,
  "cupom_id": null,
  "valor_desconto": null,
  "valor_final": null,
  "mensagem": "Cupom inválido ou expirado"
}
```

**Arquivos criados:**
- `apps/cupom/serializers.py` - Serializers REST
- `apps/cupom/api_views.py` - Views das APIs (2 endpoints)
- `apps/cupom/urls.py` - Rotas das APIs

**Arquivos modificados:**
- `wallclub/urls_apis.py` - Adicionado rota `/api/v1/cupons/`
- `wallclub/urls_pos.py` - Adicionado rota `/api/v1/cupons/`

### ⏳ Etapa 5: Integração Checkout Web - PENDENTE
- Alterar `CheckoutTransaction`
- Modificar `LinkPagamentoTransactionService` para usar API
- Campo cupom no formulário

### ⏳ Etapa 5: Integração Pinbank (POSP2) - PENDENTE
- Alterar `TransactionData`
- Modificar `TRDataService`
- Mesmo fluxo da Own

### ⏳ Etapa 6: Contabilização - PENDENTE (aguardando definição de regras)
- Alterar `BaseTransacoesGestao`
- Modificar `CalculadoraBaseGestao`
- Atualizar cargas Pinbank/Own

### ⏳ Etapa 7: Estorno - PENDENTE
- Implementar `CupomService.registrar_estorno()`
- Integrar com fluxos de estorno existentes
- Testes edge cases

### ⏳ Etapa 8: Testes e Homologação - PENDENTE
- Testes unitários
- Testes integração
- Deploy produção

---

## 📊 ESTIMATIVA TOTAL

**Tempo:** 12-18 dias úteis (2,5 a 3,5 semanas)
**Complexidade:** Média-Alta
**Risco:** Médio (impacta fluxo crítico)

---

## 🚨 PONTOS DE ATENÇÃO

1. **Performance** - Cache Redis para cupons ativos (TTL 5min)
2. **Segurança** - Cupom não retorna em estorno, logs de auditoria
3. **Contabilização** - Cupom é custo da loja, impacta repasse
4. **Antifraude** - Fase 2: detectar padrões de fraude com cupons
5. **UX** - Preview desconto em tempo real, mensagens claras

---

## 🔄 EVOLUÇÕES FUTURAS

- Cupons promocionais (primeira compra, aniversário)
- Regras avançadas (produtos específicos, horários)
- Antifraude específico para cupons
- Gamificação (cupons por pontos)
