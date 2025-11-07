# MELHORIAS FUTURAS - WALLCLUB BACKEND

**Versão:** 1.0  
**Data:** 07/11/2025  
**Status:** Roadmap de Melhorias Pendentes  

---

## 📋 ÍNDICE

1. [Segurança Avançada](#segurança-avançada)
2. [Notificações e Alertas](#notificações-e-alertas)
3. [Validações e Compliance](#validações-e-compliance)
4. [Sistema de Recorrência](#sistema-de-recorrência)
5. [Portal Corporativo](#portal-corporativo)
6. [Monitoramento e Observabilidade](#monitoramento-e-observabilidade)
7. [Testes e Qualidade](#testes-e-qualidade)
8. [Otimizações de Performance](#otimizações-de-performance)
9. [Refatorações Menores](#refatorações-menores)

---

## 🔐 SEGURANÇA AVANÇADA

### 1. 2FA Login App Móvel

**Prioridade:** ALTA  
**Tempo Estimado:** 8 horas

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
- `scripts/producao/fase4/adicionar_campos_revalidacao_celular.sql`

---

### 3. Validação CPF com Bureau no Cadastro

**Prioridade:** MÉDIA  
**Tempo Estimado:** 4 horas

**Objetivo:** Validar CPF na Receita Federal via Bureau

**Implementações:**
- [ ] Integrar com `comum/integracoes/bureau_service.py`
- [ ] Validar CPF ativo no cadastro (app + checkout)
- [ ] Match de nome informado com nome do CPF
- [ ] Bloquear cadastro se CPF irregular
- [ ] Logs detalhados de validações

**Validações:**
- ✅ Dígitos verificadores (validação local)
- ✅ CPF ativo na Receita Federal (Bureau)
- ✅ Match de nome (tolerância: 80% similaridade)
- ✅ CPF não está em blacklist interna
- ✅ Status "REGULAR" no Bureau

**Cache:**
- Redis: `bureau:cpf:{cpf}` válido por 24h
- Retry automático: 2 tentativas com 3s intervalo
- Fallback: se Bureau offline, permitir + flag revisar

**Configurações:**
```python
BUREAU_VALIDATION_ENABLED = True
BUREAU_VALIDATION_REQUIRED = True
BUREAU_CACHE_TIMEOUT = 86400  # 24 horas
BUREAU_NAME_MATCH_THRESHOLD = 0.80
```

---

### 4. Senha Transacional Separada

**Prioridade:** BAIXA  
**Tempo Estimado:** 6 horas

**Objetivo:** Senha de 4-6 dígitos apenas para transações

**Benefícios:**
- Mais rápido que 2FA via SMS
- Não depende de operadora
- Funciona offline

**Implementações:**
- [ ] Campo `senha_transacional_hash` em Cliente
- [ ] Endpoint criar/alterar senha transacional
- [ ] Validação em transações >R$ 50
- [ ] Bloqueio após 3 tentativas erradas
- [ ] Reset via 2FA

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

## ✅ VALIDAÇÕES E COMPLIANCE

### 1. Auditoria Automática via Django Signals

**Prioridade:** MÉDIA  
**Tempo Estimado:** 4 horas

**Objetivo:** Rastrear mudanças em recorrências

**Implementações:**
- [ ] Criar signals para `checkout_recorrencias_historico`
- [ ] Rastrear: criação, pausar, reativar, cancelar, atualizar valor
- [ ] Registrar usuário que fez a ação
- [ ] Timestamp automático

---

### 2. Testes End-to-End Completos

**Prioridade:** ALTA  
**Tempo Estimado:** 8 horas

**Fluxos a Testar:**
- [ ] Checkout Web (cartão novo + OTP)
- [ ] App Móvel (login + 2FA + dispositivo confiável)
- [ ] Login portal com IP bloqueado
- [ ] Login portal com CPF bloqueado
- [ ] Detector automático criando alertas
- [ ] Rate limiting funcionando
- [ ] Validação CPF com Bureau
- [ ] Notificações de segurança (todos tipos)
- [ ] Revalidação celular após 90 dias
- [ ] Limite de 1 dispositivo por conta

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

### 4. Periodicidades Adicionais

**Prioridade:** BAIXA  
**Tempo Estimado:** 3 horas

**Implementações:**
- [ ] Quinzenal
- [ ] Bimestral
- [ ] Trimestral
- [ ] Semestral

---

### 5. Regras de Desconto/Acréscimo

**Prioridade:** BAIXA  
**Tempo Estimado:** 4 horas

**Implementações:**
- [ ] Descontos para pagamento antecipado
- [ ] Multa por atraso
- [ ] Juros configuráveis
- [ ] Promoções temporárias

---

### 6. Exportação de Relatórios

**Prioridade:** BAIXA  
**Tempo Estimado:** 3 horas

**Implementações:**
- [ ] Excel/CSV de recorrências
- [ ] PDF de comprovantes
- [ ] Relatório consolidado mensal
- [ ] Envio automático por email

---

## 🌐 PORTAL CORPORATIVO

### 1. Implementar Envio de Email no Formulário

**Prioridade:** MÉDIA  
**Tempo Estimado:** 2 horas

**Implementações:**
- [ ] Salvar lead no banco de dados
- [ ] Enviar email para atendimento
- [ ] Email de confirmação para cliente
- [ ] Integração com CRM (opcional)

---

### 2. Google Analytics

**Prioridade:** MÉDIA  
**Tempo Estimado:** 2 horas

**Implementações:**
- [ ] Tracking de páginas
- [ ] Eventos de conversão (formulário enviado, app download)
- [ ] Funil de conversão cliente/lojista
- [ ] Relatórios mensais

---

### 3. Dashboard de Leads no Portal Admin

**Prioridade:** BAIXA  
**Tempo Estimado:** 4 horas

**Implementações:**
- [ ] Lista de leads recebidos
- [ ] Filtros por tipo (consumidor/lojista)
- [ ] Status de atendimento
- [ ] Exportação CSV

---

### 4. Sitemap.xml

**Prioridade:** BAIXA  
**Tempo Estimado:** 1 hora

**Implementações:**
- [ ] Gerar sitemap.xml
- [ ] Submeter ao Google Search Console
- [ ] Atualização automática

---

### 5. Blog/Conteúdo SEO

**Prioridade:** BAIXA  
**Tempo Estimado:** 8+ horas

**Implementações:**
- [ ] Sistema de blog
- [ ] Artigos sobre benefícios
- [ ] Casos de sucesso
- [ ] FAQ expandido

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

**Implementações:**
- [ ] Prometheus para métricas
- [ ] Grafana para dashboards
- [ ] Alertmanager para alertas
- [ ] Integração Slack/Email
- [ ] Métricas de negócio (MRR, conversão, etc)

---

### 3. Métricas de Recorrência

**Prioridade:** MÉDIA  
**Tempo Estimado:** 4 horas

**Monitorar:**
- Taxa de sucesso de cobranças (alerta se <80%)
- Recorrências em HOLD (alerta se >10% do total)
- Tempo de processamento tasks (alerta se >5 min)
- Falhas de task (alerta qualquer exception)

---

## 🧪 TESTES E QUALIDADE

### 1. Testes Unitários

**Prioridade:** ALTA  
**Tempo Estimado:** 40 horas

**Cobertura:**
- [ ] Testes de services (cobertura 80%)
- [ ] Testes de models
- [ ] Testes de serializers
- [ ] Testes de utils
- [ ] Testes de decorators

---

### 2. Testes de Integração

**Prioridade:** ALTA  
**Tempo Estimado:** 32 horas

**Cobertura:**
- [ ] Testes de fluxos completos
- [ ] Testes de APIs
- [ ] Testes de autenticação
- [ ] Testes de permissões
- [ ] Testes de comunicação entre containers

---

### 3. Testes de Carga

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

**Implementações:**
- [ ] Cache de hierarquia organizacional (1 hora)
- [ ] Cache de parâmetros (30 min)
- [ ] Cache de ofertas ativas (15 min)
- [ ] Cache de saldo conta digital (5 min)
- [ ] Invalidação inteligente

---

### 2. Índices de Banco de Dados

**Prioridade:** ALTA  
**Tempo Estimado:** 4 horas

**Análise:**
- [ ] Identificar queries lentas (slow query log)
- [ ] Criar índices compostos
- [ ] Otimizar JOINs
- [ ] Analisar EXPLAIN de queries críticas

---

### 3. Paginação Otimizada

**Prioridade:** MÉDIA  
**Tempo Estimado:** 3 horas

**Implementações:**
- [ ] Cursor-based pagination em listas grandes
- [ ] Lazy loading em templates
- [ ] Infinite scroll onde apropriado

---

## 🔧 REFATORAÇÕES MENORES

### 1. Limpeza de Recuperações de Sessão

**Prioridade:** BAIXA  
**Tempo Estimado:** 4 horas

**Arquivos:**
- [ ] `apps/oauth/views.py` - 1 ocorrência
- [ ] `portais/admin/views.py` - 2 ocorrências
- [ ] `portais/lojista/views.py` - 13 ocorrências

**Solução:**
- Criar métodos auxiliares:
  - `OAuthService.validar_cliente_por_credenciais()`
  - `UsuarioService.obter_usuario_sessao(user_id)`
  - `UsuarioService.validar_token_senha(token)`

---

### 2. Centralização de Templates de Email

**Prioridade:** BAIXA  
**Status:** ✅ PARCIALMENTE CONCLUÍDO

**Pendências:**
- [ ] Remover templates antigos após validação em produção
- [ ] Criar template para notificações de transação
- [ ] Criar template para alertas de segurança
- [ ] Criar template para relatórios periódicos

---

### 3. Ajuste de URLs dos Portais

**Prioridade:** BAIXA  
**Tempo Estimado:** 3 horas

**Situação Atual:**
- `admin.wallclub.local/portal_admin/`
- `vendas.wallclub.local/portal_vendas/`
- `lojista.wallclub.local/portal_lojista/`

**Desejado:**
- `admin.wallclub.local/`
- `vendas.wallclub.local/`
- `lojista.wallclub.local/`

**Solução:**
- Criar middleware para detectar subdomínio e ajustar URL_PREFIX

---

## 🎯 PRIORIZAÇÃO RECOMENDADA

### Curto Prazo (1-2 meses)
1. ✅ 2FA Login App Móvel
2. ✅ Revalidação de Celular (90 dias)
3. ✅ Sistema de Notificações de Segurança
4. ✅ Testes End-to-End Completos
5. ✅ Monitoramento (ELK Stack ou Prometheus)

### Médio Prazo (3-6 meses)
1. ✅ Validação CPF com Bureau
2. ✅ Dashboard Métricas Recorrência
3. ✅ Testes Unitários (cobertura 80%)
4. ✅ Cache Agressivo
5. ✅ Índices de Banco de Dados

### Longo Prazo (6+ meses)
1. ✅ Senha Transacional Separada
2. ✅ Webhook Sistema Externo
3. ✅ Portal Corporativo (melhorias)
4. ✅ Testes de Carga
5. ✅ Refatorações Menores

---

## 📝 OBSERVAÇÕES

**Estimativas de Tempo:**
- Baseadas em desenvolvedor experiente
- Incluem testes básicos
- Não incluem code review e ajustes

**Dependências:**
- Algumas melhorias dependem de equipe mobile
- Outras dependem de aprovação de negócio
- Algumas requerem contratação de serviços externos

**Custos Adicionais:**
- Bureau de crédito: R$ 300-600/mês
- ELK Stack: Infraestrutura adicional
- Prometheus/Grafana: Infraestrutura adicional

---

**Responsável:** Jean Lessa  
**Data:** 07/11/2025  
**Próxima Revisão:** Trimestral
