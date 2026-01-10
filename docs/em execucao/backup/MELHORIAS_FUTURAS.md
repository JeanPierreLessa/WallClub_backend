# MELHORIAS FUTURAS - WALLCLUB BACKEND

**Versão:** 2.0  
**Data:** 20/12/2025  
**Status:** Roadmap Atualizado - Removido itens já implementados

---

## 📋 ÍNDICE

1. [Segurança e Compliance](#segurança-e-compliance)
2. [Notificações e Alertas](#notificações-e-alertas)
3. [Sistema de Recorrência](#sistema-de-recorrência)
4. [Monitoramento e Observabilidade](#monitoramento-e-observabilidade)
5. [Testes e Qualidade](#testes-e-qualidade)
6. [Otimizações de Performance](#otimizações-de-performance)

---

## 🔐 SEGURANÇA E COMPLIANCE

### 1. 2FA Login App Móvel

**Prioridade:** ALTA  
**Tempo Estimado:** 8 horas

**Contexto:** Checkout Web já tem 2FA completo. Falta implementar no app mobile.

**Implementações:**
- [ ] Gerar OTP no login (além de senha)
- [ ] Enviar OTP via SMS/WhatsApp
- [ ] Validar OTP antes permitir acesso
- [ ] Marcar dispositivo como confiável (30 dias)
- [ ] Bypass 2FA para dispositivos confiáveis
- [ ] Limite de 1 dispositivo ativo por cliente

**Gatilhos Obrigatórios:**
- Login de novo dispositivo
- Primeira transação do dia
- Transação > R$ 100,00
- Alteração de celular/email/senha
- Transferências (qualquer valor)
- Dispositivo confiável expirado (>30 dias)

**Arquivos:**
- `apps/cliente/services_2fa_login.py`
- `apps/cliente/views_2fa.py`
- Atualização app mobile

---

### 2. Revalidação de Celular (90 dias)

**Prioridade:** ALTA  
**Tempo Estimado:** 4 horas

**Objetivo:** Forçar revalidação de celular a cada 90 dias

**Implementações:**
- [ ] `verificar_validade_celular()` - Verificar última validação
- [ ] `solicitar_revalidacao_celular()` - Enviar OTP
- [ ] `validar_celular()` - Confirmar OTP e atualizar data
- [ ] `bloquear_por_celular_expirado()` - Bloquear transações se >90 dias

**Model:**
- [ ] Campo `celular_validado_em` (DateTimeField, nullable)
- [ ] Campo `celular_revalidacao_solicitada` (BooleanField)

**Regras:**
- Celular válido por 90 dias
- Bloquear transações até revalidar
- Lembrete 7 dias antes
- Primeira validação: no cadastro

**Job Celery:**
- [ ] Verificar celulares próximos de expirar (diário)
- [ ] Enviar lembretes 7 dias antes
- [ ] Bloquear transações automático após expirar

**Arquivos:**
- `apps/cliente/services_revalidacao_celular.py`
- `scripts/producao/adicionar_campos_revalidacao_celular.sql`

---

### 3. Validação CPF com Bureau no Cadastro

**Prioridade:** MÉDIA  
**Tempo Estimado:** 4 horas

**Contexto:** Atualmente só validação local de dígitos verificadores.

**Implementações:**
- [ ] Integrar com Bureau (Serasa/Boa Vista)
- [ ] Validar CPF ativo no cadastro (app + checkout)
- [ ] Match de nome informado com nome do CPF (80% similaridade)
- [ ] Bloquear cadastro se CPF irregular
- [ ] Logs detalhados de validações

**Cache:**
- Redis: `bureau:cpf:{cpf}` válido por 24h
- Retry automático: 2 tentativas com 3s intervalo
- Fallback: se Bureau offline, permitir + flag revisar

**Custo Estimado:** R$ 300-600/mês

---

## 📢 NOTIFICAÇÕES E ALERTAS

### 1. Sistema de Notificações de Segurança

**Prioridade:** ALTA  
**Tempo Estimado:** 5 horas

**Objetivo:** Notificar clientes sobre eventos de segurança

**Service:** `comum/integracoes/notificacao_seguranca_service.py`

**Métodos:**
- [ ] `enviar_alerta_seguranca()` - Método unificado
- [ ] `notificar_login_novo_dispositivo()`
- [ ] `notificar_troca_senha()`
- [ ] `notificar_alteracao_dados()`
- [ ] `notificar_transacao_alto_valor()`
- [ ] `notificar_tentativas_falhas()`
- [ ] `notificar_bloqueio_conta()`
- [ ] `notificar_dispositivo_removido()`

**Canais:**
1. Push Notification (prioritário)
2. SMS (backup - alertas críticos)
3. Email (backup - documentação)

**Integrações:**
- [ ] Login app mobile: notificar se novo dispositivo
- [ ] Troca de senha: notificar sempre
- [ ] Alteração celular/email: notificar sempre
- [ ] Transação >R$100: notificar após aprovação
- [ ] 3 tentativas login falhas: notificar titular
- [ ] Conta bloqueada: notificar imediatamente

**Tabela:**
- `notificacoes_seguranca`
- Campos: cliente_id, tipo, canal, enviado_em, status, detalhes
- Retention: 90 dias

---

### 2. Notificações Recorrência

**Prioridade:** MÉDIA  
**Tempo Estimado:** 3 horas

**Implementações:**
- [ ] Email vendedor quando recorrência entra em HOLD
- [ ] SMS cliente antes da cobrança
- [ ] Email confirmação de cobrança para cliente
- [ ] Push notification cobrança processada

---

## 🔄 SISTEMA DE RECORRÊNCIA

### 1. Dashboard de Métricas

**Prioridade:** MÉDIA  
**Tempo Estimado:** 6 horas

**Métricas:**
- [ ] Taxa de sucesso/falha de cobranças
- [ ] MRR (Monthly Recurring Revenue)
- [ ] Churn rate
- [ ] Top motivos de recusa
- [ ] Gráficos de tendência

---

### 2. Webhook para Sistema Externo

**Prioridade:** BAIXA  
**Tempo Estimado:** 4 horas

**Implementações:**
- [ ] Enviar evento quando cobrança processada
- [ ] Payload JSON com dados da transação
- [ ] Retry automático em falha
- [ ] Logs de webhooks enviados

---

### 3. Atualização de Cartão pelo Cliente

**Prioridade:** MÉDIA  
**Tempo Estimado:** 5 horas

**Implementações:**
- [ ] Link para cliente atualizar cartão tokenizado
- [ ] Integração com gateway de pagamento
- [ ] Email automático quando cartão próximo de expirar
- [ ] Validação 2FA na atualização

---

## 📊 MONITORAMENTO E OBSERVABILIDADE

### 1. ELK Stack

**Prioridade:** ALTA  
**Tempo Estimado:** 16 horas

**Implementações:**
- [ ] Elasticsearch para logs
- [ ] Logstash para pipeline
- [ ] Kibana para visualização
- [ ] Dashboards customizados
- [ ] Alertas automáticos

---

### 2. Prometheus + Grafana

**Prioridade:** ALTA  
**Tempo Estimado:** 12 horas

**Contexto:** Atualmente só temos Flower para Celery.

**Implementações:**
- [ ] Prometheus para métricas
- [ ] Grafana para dashboards
- [ ] Alertmanager para alertas
- [ ] Integração Slack/Email
- [ ] Métricas de negócio (MRR, conversão, churn)

---

## 🧪 TESTES E QUALIDADE

### 1. Testes Unitários

**Prioridade:** ALTA  
**Tempo Estimado:** 40 horas

**Contexto:** Cobertura atual muito baixa.

**Cobertura Mínima:**
- [ ] Services críticos (80%): TransacoesService, CashbackService, Antifraude
- [ ] Models principais
- [ ] Serializers de APIs
- [ ] Utils e decorators

---

### 2. Testes de Carga

**Prioridade:** MÉDIA  
**Tempo Estimado:** 8 horas

**Implementações:**
- [ ] Locust ou JMeter
- [ ] Simular 1000 usuários simultâneos
- [ ] Identificar gargalos
- [ ] Otimizar queries lentas

---

## ⚡ OTIMIZAÇÕES DE PERFORMANCE

### 1. Cache Agressivo

**Prioridade:** MÉDIA  
**Tempo Estimado:** 6 horas

**Contexto:** Redis usado apenas para Celery e sessões.

**Implementações:**
- [ ] Cache de hierarquia organizacional (1 hora TTL)
- [ ] Cache de parâmetros financeiros (30 min TTL)
- [ ] Cache de ofertas ativas (15 min TTL)
- [ ] Cache de saldo conta digital (5 min TTL)
- [ ] Invalidação inteligente

---

### 2. Índices de Banco de Dados

**Prioridade:** ALTA  
**Tempo Estimado:** 4 horas

**Contexto:** Nunca foi feita análise de performance de queries.

**Análise:**
- [ ] Ativar slow query log MySQL
- [ ] Identificar queries >1s
- [ ] Criar índices compostos
- [ ] Analisar EXPLAIN de queries críticas
- [ ] Otimizar JOINs pesados

---


---

## 🎯 PRIORIZAÇÃO RECOMENDADA

### Curto Prazo (1-2 meses) - 33 horas
1. **Índices de Banco de Dados** (4h) - ROI imediato
2. **2FA Login App Móvel** (8h) - Segurança crítica
3. **Revalidação de Celular** (4h) - Compliance
4. **Sistema de Notificações** (5h) - UX e segurança
5. **Dashboard Métricas Recorrência** (6h) - Visibilidade negócio
6. **Cache Agressivo** (6h) - Performance

### Médio Prazo (3-6 meses) - 56 horas
1. **Prometheus + Grafana** (12h) - Observabilidade
2. **Testes Unitários** (40h) - Qualidade
3. **Validação CPF Bureau** (4h) - Redução fraude

### Longo Prazo (6+ meses) - 16 horas
1. **Testes de Carga** (8h)
2. **Atualização Cartão Cliente** (5h)
3. **Notificações Recorrência** (3h)

---

## 📝 OBSERVAÇÕES

**Estimativas de Tempo:**
- Baseadas em desenvolvedor experiente
- Incluem testes básicos
- Não incluem code review e ajustes

**Dependências:**
- 2FA App Móvel: requer atualização app mobile
- Validação CPF Bureau: contratação serviço externo
- Prometheus/Grafana: infraestrutura adicional

**Custos Adicionais:**
- Bureau de crédito: R$ 300-600/mês
- Prometheus/Grafana: Infraestrutura adicional (~R$ 200/mês)

**Total Estimado:** 105 horas (~3 semanas)

---

**Responsável:** Jean Lessa  
**Última Atualização:** 20/12/2025  
**Próxima Revisão:** Trimestral
