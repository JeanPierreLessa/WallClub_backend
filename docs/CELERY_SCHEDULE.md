# Celery Beat - Tasks Agendadas

Documento atualizado em: 2026-01-05

## Tasks Agendadas Automaticamente

### 💳 Cargas Pinbank

#### 1. `carga-extrato-pos`
- **Task:** `pinbank.carga_extrato_pos`
- **Agendamento:** 5x ao dia (05:13, 09:13, 13:13, 18:13, 22:13)
- **Parâmetros:** `periodo='72h'`
- **Expira em:** 1 hora
- **O que faz:** Busca transações da API Pinbank das últimas 72 horas

#### 2. `carga-extrato-pos-60dias`
- **Task:** `pinbank.carga_extrato_pos`
- **Agendamento:** Diariamente às 02:00
- **Parâmetros:** `periodo='60dias'`
- **Expira em:** 2 horas
- **O que faz:** Busca transações da API Pinbank dos últimos 60 dias (carga completa para reconciliação)

#### 3. `cargas-completas-pinbank`
- **Task:** `pinbank.cargas_completas`
- **Agendamento:** De hora em hora, minuto :05, das 5h às 23h
- **Expira em:** 1 hora
- **O que faz:** Executa o script `executar_cargas_completas.py` que roda sequencialmente:
  1. `carga_extrato_pos` (80min)
  2. `carga_base_gestao` (--limite=10000)
  3. `carga_credenciadora`
  4. `ajustes_manuais_base`

### 💰 Conta Digital

#### 4. `expirar-autorizacoes-saldo`
- **Task:** `apps.conta_digital.expirar_autorizacoes_saldo`
- **Agendamento:** Diariamente às 01:00
- **Expira em:** 1 hora
- **O que faz:** Expira autorizações de uso de saldo vencidas

### 🎁 Cashback

#### 5. `liberar-cashback-retido`
- **Task:** `cashback.liberar_cashback_retido`
- **Agendamento:** Diariamente às 02:00
- **Expira em:** 1 hora
- **O que faz:** Libera cashback que completou período de retenção (move de bloqueado para disponível)

#### 6. `expirar-cashback-vencido`
- **Task:** `cashback.expirar_cashback_vencido`
- **Agendamento:** Diariamente às 03:00
- **Expira em:** 1 hora
- **O que faz:** Expira cashback vencido (remove de disponível)

#### 7. `resetar-gasto-mensal-lojas`
- **Task:** `cashback.resetar_gasto_mensal_lojas`
- **Agendamento:** Mensalmente no dia 1 às 04:00
- **Expira em:** 1 hora
- **O que faz:** Reseta `gasto_mes_atual` das regras de cashback de loja que possuem orçamento mensal

### 🎁 Ofertas

#### 8. `processar-ofertas-agendadas`
- **Task:** `apps.ofertas.processar_ofertas_agendadas`
- **Agendamento:** A cada 5 minutos
- **Expira em:** 5 minutos
- **O que faz:** Processa ofertas com disparo automático agendado
  - Busca ofertas com `data_agendamento_disparo <= agora`, `disparada=False`, `ativo=True`
  - Dispara push notification automaticamente
  - Marca oferta como `disparada=True`
  - Cria registros em `oferta_disparos` e `oferta_envios`

---

## Tasks Definidas mas NÃO Agendadas

### Recorrências (Desabilitadas)
- `portais.vendas.tasks_recorrencia.processar_recorrencias_do_dia`
- `portais.vendas.tasks_recorrencia.retentar_cobrancas_falhadas`
- `portais.vendas.tasks_recorrencia.notificar_recorrencias_hold`
- `portais.vendas.tasks_recorrencia.limpar_recorrencias_antigas`

**Status:** Tasks definidas mas não agendadas. Sistema de recorrências ainda não está em produção.

---

## Configuração

**Arquivo:** `services/django/wallclub/celery.py`

**Timezone:** `America/Sao_Paulo`

**Beat Schedule Filename:** `celerybeat-schedule`

**Beat Max Loop Interval:** 1800 segundos (30 minutos)

---

## Resumo

- **Total de tasks agendadas:** 8
- **Total de tasks definidas:** 11+
- **Broker:** Redis
- **Containers:**
  - `wallclub-celery-worker` - Executa as tasks
  - `wallclub-celery-beat` - Agendador
  - `wallclub-flower` - Interface web de monitoramento
