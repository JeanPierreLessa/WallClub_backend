# Celery Beat - Tasks Agendadas

Documento atualizado em: 2025-11-21

## Tasks Agendadas Automaticamente

### 💳 Cargas Pinbank

#### 1. `carga-extrato-pos`
- **Task:** `pinbank.carga_extrato_pos`
- **Agendamento:** 5x ao dia (05:13, 09:13, 13:13, 18:13, 22:13)
- **Parâmetros:** `periodo='72h'`
- **Expira em:** 1 hora
- **O que faz:** Busca transações da API Pinbank das últimas 72 horas

#### 2. `cargas-completas-pinbank`
- **Task:** `pinbank.cargas_completas`
- **Agendamento:** De hora em hora, minuto :05, das 5h às 23h
- **Expira em:** 1 hora
- **O que faz:** Executa o script `executar_cargas_completas.py` que roda sequencialmente:
  1. `carga_extrato_pos` (80min)
  2. `carga_base_gestao` (--limite=10000)
  3. `carga_credenciadora`
  4. `ajustes_manuais_base`

#### 3. `migrar-financeiro-pagamentos`
- **Task:** `pinbank.migrar_financeiro_pagamentos`
- **Agendamento:** De hora em hora, minuto :15 (24h)
- **Parâmetros:** `limite=1000`
- **Expira em:** 1 hora
- **O que faz:** Migra dados de `wclub.financeiro` para `wallclub.pagamentos_efetuados`

### 💰 Conta Digital

#### 4. `expirar-autorizacoes-saldo`
- **Task:** `apps.conta_digital.expirar_autorizacoes_saldo`
- **Agendamento:** Diariamente às 01:00
- **Expira em:** 1 hora
- **O que faz:** Expira autorizações de uso de saldo vencidas

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

- **Total de tasks agendadas:** 4
- **Total de tasks definidas:** 10+
- **Broker:** Redis
- **Containers:**
  - `wallclub-celery-worker` - Executa as tasks
  - `wallclub-celery-beat` - Agendador
  - `wallclub-flower` - Interface web de monitoramento
