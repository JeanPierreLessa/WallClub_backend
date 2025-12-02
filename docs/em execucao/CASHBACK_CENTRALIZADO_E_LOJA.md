# SISTEMA DE CASHBACK CENTRALIZADO - ESPECIFICAÇÃO TÉCNICA

**Versão:** 1.0
**Data:** 23/11/2025
**Status:** Especificação para implementação

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Arquitetura](#arquitetura)
3. [Modelos de Dados](#modelos-de-dados)
4. [Regras de Negócio](#regras-de-negócio)
5. [Fluxos de Aplicação](#fluxos-de-aplicação)
6. [Implementação por Etapas](#implementação-por-etapas)

---

## 🎯 VISÃO GERAL

### Objetivo

Centralizar toda lógica de cashback (Wall + Loja) em um único app, eliminando duplicação de código e unificando regras de retenção, expiração e liberação.

### Tipos de Cashback

| Tipo | Origem | Custo | Ativação |
|------|--------|-------|----------|
| **Cashback Wall** | Parâmetros Wall (tipo 'C') | Wall | Automática (parametrização) |
| **Cashback Loja** | Regras criadas pela loja | Loja | Automática (condições) |

### Estado Atual vs Proposta

**Hoje:**
- Cashback Wall: calculado em `parametros_wallclub`, creditado via `ContaDigitalService`
- Retenção/expiração: `TipoMovimentacao` + `CashbackRetencao` em `conta_digital`
- Cashback Loja: não existe

**Proposta:**
- App `apps/cashback/` centralizado
- Lógica comum de retenção/expiração/liberação
- Histórico unificado
- Conta Digital apenas armazena saldos

---

## 🏗️ ARQUITETURA

### Estrutura do App

```
apps/cashback/
├── __init__.py
├── apps.py
├── models.py           # RegraCashback, CashbackUso, CashbackRetencao
├── services.py         # CashbackService (lógica comum)
├── admin.py            # Admin para regras
├── tasks.py            # Celery tasks (liberação automática)
└── migrations/
```

### Responsabilidades

**apps/cashback/**
- Definir regras de cashback (Wall + Loja)
- Calcular valor do cashback
- Aplicar retenção/expiração
- Creditar na conta digital
- Liberar cashback retido (job automático)
- Histórico unificado

**apps/conta_digital/**
- Armazenar saldos (cashback_disponivel, cashback_bloqueado)
- Movimentações financeiras
- Continua com `TipoMovimentacao` (tipos de crédito)

**parametros_wallclub/**
- Continua calculando desconto Wall (wall='S')
- Continua calculando cashback Wall (wall='C')
- Delega crédito para `CashbackService`

---

## 🗄️ MODELOS DE DADOS

### Model Base (Abstrato)

```python
class RegraCashback(models.Model):
    """
    Classe base abstrata para regras de cashback.
    Compartilhada entre Wall e Loja.
    """
    
    # Identificação
    nome = models.CharField(max_length=100)
    descricao = models.TextField()
    ativo = models.BooleanField(default=True)
    prioridade = models.IntegerField(default=0)
    
    # Tipo de desconto
    tipo_desconto = models.CharField(
        max_length=20,
        choices=[('FIXO', 'Fixo (R$)'), ('PERCENTUAL', 'Percentual (%)')]
    )
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Condições
    valor_minimo_compra = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    valor_maximo_cashback = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Teto de cashback por transação'
    )
    
    # Retenção e Expiração
    periodo_retencao_dias = models.IntegerField(
        default=0,
        help_text='Dias de carência antes de liberar (0 = libera imediatamente)'
    )
    periodo_expiracao_dias = models.IntegerField(
        default=0,
        help_text='Dias até expirar após liberação (0 = não expira)'
    )
    
    # Vigência
    vigencia_inicio = models.DateTimeField()
    vigencia_fim = models.DateTimeField()
    
    # Auditoria
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
    
    def calcular_cashback(self, valor_base):
        """Calcula valor do cashback"""
        if self.tipo_desconto == 'FIXO':
            cashback = self.valor_desconto
        else:  # PERCENTUAL
            cashback = valor_base * (self.valor_desconto / Decimal('100'))
        
        # Aplicar teto se configurado
        if self.valor_maximo_cashback:
            cashback = min(cashback, self.valor_maximo_cashback)
        
        return min(cashback, valor_base)
```

### Cashback Wall

```python
class RegraCashbackWall(RegraCashback):
    """
    Regras de cashback da Wall (via parametrização).
    Vinculado a parametros_wallclub (wall='C').
    """
    
    parametro_wall_id = models.BigIntegerField(
        help_text='ID do ParametrosWall (wall=C)'
    )
    
    class Meta:
        db_table = 'cashback_regra_wall'
        verbose_name = 'Regra Cashback Wall'
        verbose_name_plural = 'Regras Cashback Wall'
```

### Cashback Loja

```python
class RegraCashbackLoja(RegraCashback):
    """
    Regras de cashback criadas pela loja.
    Aplicação automática baseada em condições.
    """
    
    loja_id = models.BigIntegerField()
    
    # Filtros opcionais
    formas_pagamento = models.JSONField(
        null=True, blank=True,
        help_text='Lista de formas aceitas: ["PIX", "DEBITO", "CREDITO"]'
    )
    dias_semana = models.JSONField(
        null=True, blank=True,
        help_text='Dias da semana: [0,1,2,3,4,5,6] (0=domingo)'
    )
    horario_inicio = models.TimeField(null=True, blank=True)
    horario_fim = models.TimeField(null=True, blank=True)
    
    # Limites de uso
    limite_uso_cliente_dia = models.IntegerField(
        null=True, blank=True,
        help_text='Máximo de vezes que um cliente pode usar por dia'
    )
    limite_uso_cliente_mes = models.IntegerField(
        null=True, blank=True,
        help_text='Máximo de vezes que um cliente pode usar por mês'
    )
    orcamento_mensal = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text='Orçamento total da loja para cashback no mês'
    )
    gasto_mes_atual = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        help_text='Total gasto no mês atual'
    )
    
    class Meta:
        db_table = 'cashback_regra_loja'
        verbose_name = 'Regra Cashback Loja'
        verbose_name_plural = 'Regras Cashback Loja'
        indexes = [
            models.Index(fields=['loja_id', 'ativo']),
            models.Index(fields=['vigencia_inicio', 'vigencia_fim']),
        ]
```

### Histórico de Uso

```python
class CashbackUso(models.Model):
    """
    Histórico unificado de cashback aplicado (Wall + Loja).
    """
    
    TIPO_ORIGEM_CHOICES = [
        ('WALL', 'Cashback Wall'),
        ('LOJA', 'Cashback Loja'),
    ]
    
    # Origem
    tipo_origem = models.CharField(max_length=10, choices=TIPO_ORIGEM_CHOICES)
    regra_wall_id = models.BigIntegerField(null=True, blank=True)
    regra_loja_id = models.BigIntegerField(null=True, blank=True)
    
    # Transação
    cliente_id = models.BigIntegerField(db_index=True)
    loja_id = models.BigIntegerField(db_index=True)
    canal_id = models.IntegerField()
    transacao_tipo = models.CharField(
        max_length=20,
        choices=[('POS', 'Terminal POS'), ('CHECKOUT', 'Checkout Web')]
    )
    transacao_id = models.BigIntegerField()
    
    # Valores
    valor_transacao = models.DecimalField(max_digits=10, decimal_places=2)
    valor_cashback = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Status
    status = models.CharField(
        max_length=20,
        choices=[
            ('RETIDO', 'Retido (em carência)'),
            ('LIBERADO', 'Liberado'),
            ('EXPIRADO', 'Expirado'),
            ('ESTORNADO', 'Estornado'),
        ],
        default='RETIDO'
    )
    
    # Datas
    aplicado_em = models.DateTimeField(auto_now_add=True, db_index=True)
    liberado_em = models.DateTimeField(null=True, blank=True)
    expira_em = models.DateTimeField(null=True, blank=True)
    
    # Referência na conta digital
    movimentacao_id = models.BigIntegerField(
        null=True, blank=True,
        help_text='ID da MovimentacaoContaDigital'
    )
    
    class Meta:
        db_table = 'cashback_uso'
        verbose_name = 'Uso de Cashback'
        verbose_name_plural = 'Usos de Cashback'
        indexes = [
            models.Index(fields=['cliente_id', 'aplicado_em']),
            models.Index(fields=['tipo_origem', 'status']),
            models.Index(fields=['transacao_tipo', 'transacao_id']),
            models.Index(fields=['status', 'liberado_em']),
            models.Index(fields=['status', 'expira_em']),
        ]
        ordering = ['-aplicado_em']
```

---

## 📐 REGRAS DE NEGÓCIO

### RN01 - Tipos de Cashback

| Tipo | Quem Paga | Como Ativa | Exemplo |
|------|-----------|------------|---------|
| Wall | Wall | Parametrização (wall='C') | 3% em todas as compras |
| Loja | Loja | Regra com condições | 5% às terças-feiras |

### RN02 - Ordem de Aplicação

```
1. Valor Original
2. Desconto Pinbank/Own
3. Desconto Wall (wall='S')
4. Cupom (se houver)
= Valor Final

5. Cashback Wall (sobre valor final)
6. Cashback Loja (sobre valor final)
```

### RN03 - Retenção (Período de Carência)

- Cashback vai para `cashback_bloqueado`
- Após `periodo_retencao_dias` → move para `cashback_disponivel`
- Job Celery roda diariamente para liberar

### RN04 - Expiração

- Após liberação, conta `periodo_expiracao_dias`
- Se expirar → remove de `cashback_disponivel`
- Status muda para `EXPIRADO`

### RN05 - Múltiplas Regras

**Cashback Loja:**
- Aplica apenas **1 regra** (maior prioridade ou maior valor)
- Não acumula com outras regras de loja

**Cashback Wall + Loja:**
- Podem acumular (são independentes)

### RN06 - Estorno

- Se transação estornada → marca cashback como `ESTORNADO`
- Se ainda retido → remove de `cashback_bloqueado`
- Se já liberado → debita de `cashback_disponivel`

---

## 🔄 FLUXOS DE APLICAÇÃO

### Fluxo 1: Cashback Wall (POS)

```python
# 1. Calculadora calcula cashback (wall='C')
valor_cashback_wall = calculadora.calcular_desconto(
    valor_original=valor_final,
    wall='C',
    ...
)

# 2. Delega para CashbackService
if valor_cashback_wall > 0:
    CashbackService.aplicar_cashback_wall(
        parametro_wall_id=config.id,
        cliente_id=cliente_id,
        loja_id=loja_id,
        transacao_tipo='POS',
        transacao_id=transaction_data.id,
        valor_transacao=valor_final,
        valor_cashback=valor_cashback_wall
    )
```

### Fluxo 2: Cashback Loja (automático)

```python
# Após cupom, verifica regras de cashback loja
CashbackService.aplicar_cashback_loja_automatico(
    loja_id=loja_id,
    cliente_id=cliente_id,
    canal_id=canal_id,
    valor_transacao=valor_final,
    forma_pagamento='PIX',
    transacao_tipo='POS',
    transacao_id=transaction_data.id
)
```

### Fluxo 3: Liberação Automática (Celery)

```python
# Task roda diariamente
@shared_task
def liberar_cashback_retido():
    """
    Libera cashback que completou período de retenção.
    """
    agora = datetime.now()
    
    # Buscar cashback retido pronto para liberar
    cashbacks = CashbackUso.objects.filter(
        status='RETIDO',
        liberado_em__lte=agora
    )
    
    for cashback in cashbacks:
        CashbackService.liberar_cashback(cashback.id)
```

### Fluxo 4: Expiração Automática (Celery)

```python
@shared_task
def expirar_cashback_vencido():
    """
    Expira cashback que passou do prazo.
    """
    agora = datetime.now()
    
    cashbacks = CashbackUso.objects.filter(
        status='LIBERADO',
        expira_em__lte=agora
    )
    
    for cashback in cashbacks:
        CashbackService.expirar_cashback(cashback.id)
```

---

## 🔧 CASHBACK SERVICE

```python
class CashbackService:
    """Service centralizado para toda lógica de cashback"""
    
    @staticmethod
    def aplicar_cashback_wall(parametro_wall_id, cliente_id, loja_id, canal_id,
                              transacao_tipo, transacao_id, valor_transacao, 
                              valor_cashback):
        """
        Aplica cashback Wall após transação.
        """
        # Buscar regra Wall (ou criar se não existir)
        regra = RegraCashbackWall.objects.filter(
            parametro_wall_id=parametro_wall_id
        ).first()
        
        if not regra:
            # Criar regra baseada no ParametrosWall
            regra = CashbackService._criar_regra_wall(parametro_wall_id)
        
        # Calcular datas
        data_liberacao = datetime.now() + timedelta(days=regra.periodo_retencao_dias)
        data_expiracao = None
        if regra.periodo_expiracao_dias > 0:
            data_expiracao = data_liberacao + timedelta(days=regra.periodo_expiracao_dias)
        
        # Creditar na conta digital
        movimentacao = ContaDigitalService.creditar(
            cliente_id=cliente_id,
            canal_id=canal_id,
            valor=valor_cashback,
            descricao=f"Cashback Wall - {regra.nome}",
            tipo_codigo='CASHBACK_WALL',
            referencia_externa=f'WALL:{parametro_wall_id}',
            sistema_origem='CASHBACK'
        )
        
        # Registrar histórico
        CashbackUso.objects.create(
            tipo_origem='WALL',
            regra_wall_id=regra.id,
            cliente_id=cliente_id,
            loja_id=loja_id,
            canal_id=canal_id,
            transacao_tipo=transacao_tipo,
            transacao_id=transacao_id,
            valor_transacao=valor_transacao,
            valor_cashback=valor_cashback,
            status='RETIDO' if regra.periodo_retencao_dias > 0 else 'LIBERADO',
            liberado_em=data_liberacao,
            expira_em=data_expiracao,
            movimentacao_id=movimentacao.id
        )
    
    @staticmethod
    def aplicar_cashback_loja_automatico(loja_id, cliente_id, canal_id,
                                         valor_transacao, forma_pagamento,
                                         transacao_tipo, transacao_id):
        """
        Verifica e aplica regras de cashback da loja automaticamente.
        """
        from datetime import datetime
        
        agora = datetime.now()
        dia_semana = agora.weekday()
        horario = agora.time()
        
        # Buscar regras ativas
        regras = RegraCashbackLoja.objects.filter(
            loja_id=loja_id,
            ativo=True,
            vigencia_inicio__lte=agora,
            vigencia_fim__gte=agora
        ).order_by('-prioridade', '-valor_desconto')
        
        for regra in regras:
            # Validar condições
            if not CashbackService._valida_condicoes_loja(
                regra, valor_transacao, forma_pagamento, dia_semana, horario
            ):
                continue
            
            # Validar limites
            if not CashbackService._valida_limites_loja(regra, cliente_id):
                continue
            
            # Calcular cashback
            valor_cashback = regra.calcular_cashback(valor_transacao)
            
            # Aplicar
            CashbackService._aplicar_cashback_loja(
                regra, cliente_id, canal_id, transacao_tipo,
                transacao_id, valor_transacao, valor_cashback
            )
            
            break  # Aplica apenas 1 regra
    
    @staticmethod
    def liberar_cashback(cashback_uso_id):
        """
        Libera cashback retido (move de bloqueado para disponível).
        """
        cashback = CashbackUso.objects.get(id=cashback_uso_id)
        
        if cashback.status != 'RETIDO':
            return
        
        # Atualizar conta digital
        conta = ContaDigital.objects.get(
            cliente_id=cashback.cliente_id,
            canal_id=cashback.canal_id
        )
        
        conta.cashback_bloqueado -= cashback.valor_cashback
        conta.cashback_disponivel += cashback.valor_cashback
        conta.save()
        
        # Atualizar status
        cashback.status = 'LIBERADO'
        cashback.save()
    
    @staticmethod
    def expirar_cashback(cashback_uso_id):
        """
        Expira cashback vencido (remove de disponível).
        """
        cashback = CashbackUso.objects.get(id=cashback_uso_id)
        
        if cashback.status != 'LIBERADO':
            return
        
        # Debitar da conta digital
        ContaDigitalService.debitar(
            cliente_id=cashback.cliente_id,
            canal_id=cashback.canal_id,
            valor=cashback.valor_cashback,
            descricao=f"Expiração de cashback",
            tipo_codigo='CASHBACK_EXPIRACAO'
        )
        
        # Atualizar status
        cashback.status = 'EXPIRADO'
        cashback.save()
    
    @staticmethod
    def estornar_cashback(transacao_tipo, transacao_id):
        """
        Estorna cashback de uma transação estornada.
        """
        cashbacks = CashbackUso.objects.filter(
            transacao_tipo=transacao_tipo,
            transacao_id=transacao_id,
            status__in=['RETIDO', 'LIBERADO']
        )
        
        for cashback in cashbacks:
            if cashback.status == 'RETIDO':
                # Remove de bloqueado
                conta = ContaDigital.objects.get(
                    cliente_id=cashback.cliente_id,
                    canal_id=cashback.canal_id
                )
                conta.cashback_bloqueado -= cashback.valor_cashback
                conta.save()
            
            elif cashback.status == 'LIBERADO':
                # Debita de disponível
                ContaDigitalService.debitar(
                    cliente_id=cashback.cliente_id,
                    canal_id=cashback.canal_id,
                    valor=cashback.valor_cashback,
                    descricao=f"Estorno de cashback",
                    tipo_codigo='CASHBACK_ESTORNO'
                )
            
            cashback.status = 'ESTORNADO'
            cashback.save()
```

---

## 🏗️ IMPLEMENTAÇÃO POR ETAPAS

### ✅ Etapa 1: Estrutura Base - CONCLUÍDA (25/11/2025)
- ✅ Criar app `apps/cashback/`
- ✅ Models: `RegraCashbackLoja`, `CashbackUso` (RegraCashback abstrato)
- ✅ **IMPORTANTE:** Cashback Wall usa DIRETAMENTE `parametros_wallclub` (wall='C') - SEM tabela intermediária
- ✅ Migrations SQL executadas (2 tabelas criadas)
- ✅ Admin básico configurado
- ✅ App adicionado ao `INSTALLED_APPS`

**Arquivos criados:**
- `apps/cashback/__init__.py`
- `apps/cashback/apps.py`
- `apps/cashback/models.py` (310 linhas)
- `apps/cashback/services.py` (420 linhas)
- `apps/cashback/admin.py` (90 linhas)
- `apps/cashback/tasks.py` (140 linhas)
- `apps/cashback/migrations_sql.sql`

**Tabelas criadas:**
- `cashback_regra_loja` - Regras de cashback criadas pela loja
- `cashback_uso` - Histórico unificado (Wall + Loja)

### ✅ Etapa 2: CashbackService - CONCLUÍDA (25/11/2025)
- ✅ `aplicar_cashback_wall()` - Recebe valor calculado, credita + registra
- ✅ `aplicar_cashback_loja_automatico()` - Verifica regras e aplica
- ✅ `liberar_cashback()` - Move de bloqueado para disponível
- ✅ `expirar_cashback()` - Remove cashback vencido
- ✅ `estornar_cashback()` - Estorna em caso de cancelamento
- ✅ Métodos privados de validação (condições e limites)

### ✅ Etapa 3: Jobs Celery - CONCLUÍDA (25/11/2025)
- ✅ `liberar_cashback_retido()` - Roda diariamente
- ✅ `expirar_cashback_vencido()` - Roda diariamente
- ✅ `resetar_gasto_mensal_lojas()` - Roda dia 1 de cada mês
- ⏳ Configurar schedule no Celery Beat (pendente)

### ⏳ Etapa 4: Migrar Cashback Wall - PENDENTE
- Modificar fluxo POS para usar `CashbackService.aplicar_cashback_wall()`
- Modificar fluxo Checkout para usar `CashbackService.aplicar_cashback_wall()`
- Validar que continua funcionando
- Testes de regressão

### ✅ Etapa 5: Cashback Loja (Portal Lojista) - CONCLUÍDA (26/11/2025)
- ✅ CRUD de regras no portal lojista (6 views)
- ✅ Templates HTML (lista, form, detalhe, relatório)
- ✅ URLs configuradas
- ✅ Deploy em produção e correções de configuração
- ✅ Pulldown de seleção de loja adicionado ao formulário
- ✅ Remoção de campos `periodo_retencao_dias` e `periodo_expiracao_dias` (agora são globais)
- ⏳ CRUD de regras no portal admin (pendente)
- ⏳ Aplicação automática no fluxo POS/Checkout (pendente)

**Arquivos criados:**
- `portais/lojista/views_cashback.py` (380 linhas)
- `portais/lojista/templates/portais/lojista/cashback/lista.html`
- `portais/lojista/templates/portais/lojista/cashback/form.html`
- `portais/lojista/templates/portais/lojista/cashback/detalhe.html`
- `portais/lojista/templates/portais/lojista/cashback/relatorio.html`

**Funcionalidades:**
- Lista com filtros (busca, status, vigência) e paginação
- Criar/Editar regra (formulário completo com todos os campos)
- Detalhes + estatísticas de uso
- Ativar/Desativar regra
- Relatório de uso com filtros avançados

**Correções de Deploy:**
- Uso de `apps.get_model()` para evitar import circular
- Configuração de `app_label = 'cashback'` nos models
- Adição de `CashbackConfig` em `portais.py` INSTALLED_APPS
- Refatoração de settings para evitar duplicação (herança de INSTALLED_APPS)
- Correção de `INTERNAL_API_BASE_URL` para apontar para container correto

### ✅ Etapa 6: APIs REST - CONCLUÍDA (26/11/2025)
- ✅ API `POST /api/v1/cashback/simular/` - Simula cashback Loja
- ✅ API `POST /api/v1/cashback/aplicar/` - Aplica cashback Wall ou Loja
- ✅ Métodos `simular_cashback_loja()` e `aplicar_cashback_loja()` no CashbackService
- ✅ Configurações globais de cashback em `settings/base.py`
- ✅ URLs configuradas em `wallclub/urls.py`

**Arquivos criados:**
- `apps/cashback/api_views.py` (200 linhas)
- `apps/cashback/urls.py`

**Configurações Globais:**
- `CASHBACK_PERIODO_RETENCAO_DIAS` = 30 (padrão, via env)
- `CASHBACK_PERIODO_EXPIRACAO_DIAS` = 90 (padrão, via env)

**Endpoints:**
1. **POST /api/v1/cashback/simular/** - Simula cashback Loja antes da transação
   - Body: `loja_id`, `cliente_id`, `valor_transacao`, `forma_pagamento`
   - Retorna: regra aplicável e valor do cashback
   
2. **POST /api/v1/cashback/aplicar/** - Aplica cashback após transação aprovada
   - Body: `tipo` (WALL/LOJA), `cliente_id`, `loja_id`, `transacao_id`, `valor_cashback`
   - Retorna: `cashback_uso_id`, `status`, `data_liberacao`, `data_expiracao`

### ✅ Etapa 7: Integração POSP2 V2 - CONCLUÍDA (01/12/2025)
- ✅ Endpoint V2 `POST /api/v1/posp2/simula_parcelas_v2/` com cashback loja integrado
- ✅ Service `POSP2ServiceV2` com simulação unificada (Wall + Loja)
- ✅ Estrutura padronizada de resposta com `cashback_wall`, `cashback_loja` e `cashback_total`
- ✅ Validação de formas de pagamento (campo vazio = todas as formas)
- ✅ Correção de bugs em validação de JSONField (MySQL)

**Arquivos criados:**
- `posp2/services_v2.py` (270 linhas)
- `posp2/views.py` - Endpoint `simular_parcelas_v2`
- `posp2/urls.py` - Rota `/simula_parcelas_v2/`

**Estrutura de Resposta V2:**
```json
{
  "sucesso": true,
  "dados": {
    "parcelas": {
      "PIX": {
        "valor_original": "100.00",
        "valor_total": "84.67",
        "desconto_wall": "15.33",
        "cashback_wall": {"valor": "0.00", "percentual": "0.00"},
        "cashback_loja": {"aplicavel": true, "valor": "5.00", "regra_nome": "..."},
        "cashback_total": "5.00"
      }
    }
  }
}
```

**Correções Técnicas:**
- Validação robusta de `formas_pagamento` e `dias_semana` (lista vazia = aceita todos)
- Tratamento de JSONField do MySQL (tipo `json` vs `jsonb`)
- Logs de debug para troubleshooting

### ⏳ Etapa 7: Estorno - PENDENTE
- Integrar `CashbackService.estornar_cashback()` nos fluxos de estorno
- Testes de edge cases

### ⏳ Etapa 7: Testes e Homologação - PENDENTE
- Testes integração
- Homologação
- Deploy produção

---

## 📊 ESTIMATIVA TOTAL

**Tempo:** 11-17 dias úteis (2 a 3,5 semanas)
**Complexidade:** Alta (migração + nova funcionalidade)
**Risco:** Médio-Alto (impacta cashback existente)

---

## 🚨 PONTOS DE ATENÇÃO

1. **Migração de dados** - Cashback Wall existente precisa ser mapeado
2. **Retrocompatibilidade** - Não quebrar cashback atual durante migração
3. **Performance** - Jobs de liberação/expiração devem ser otimizados
4. **Contabilização** - Separar custo Wall vs Loja nos relatórios
5. **Testes** - Validar retenção, liberação e expiração funcionam corretamente
