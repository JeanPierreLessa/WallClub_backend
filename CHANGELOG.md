# Changelog - WallClub Backend

Todas as mudanças notáveis do projeto serão documentadas neste arquivo.

---

## [1.0.0] - 2025-11-01

### Monorepo Inicial
- Criação do monorepo unificado WallClub_backend
- Extração do wallclub_core como package compartilhado
- Migração de 113 arquivos (108 Django + 5 Risk Engine)
- Padrão: `from comum.*` → `from wallclub_core.*`

---

## Atualizações Recentes

### [2026-03-06] - Device Fingerprint com Análise de Similaridade
- **Problema:** Sistema validava apenas hash exato do fingerprint, causando fricção em updates legítimos (iOS, reinstalação)
- **Solução Híbrida:**
  - Armazenar 7 componentes individuais do fingerprint no banco
  - Algoritmo de similaridade com pesos (native_id: 40pts, screen_resolution: 20pts, device_model: 20pts, device_brand: 10pts, os_version: 5pts, timezone: 5pts)
  - Lógica de decisão inteligente baseada em score 0-100
- **Lógica de Decisão:**
  - Score 100 (hash exato) → `allow` (login direto)
  - Score ≥90 (1 componente mudou) → `allow` COM MONITORAMENTO (provável update iOS)
  - Score 80-89 (2 componentes) → `require_otp` (suspeito)
  - Score 50-79 → `require_otp` (comportamento suspeito)
  - Score <50 → `require_otp` ou `block` (novo dispositivo ou limite atingido)
- **Arquivos Modificados:**
  - `wallclub_core/seguranca/models.py`: Campos native_id, screen_resolution, device_model, os_version, device_brand, timezone, platform
  - `wallclub_core/seguranca/services_device.py`: Métodos calcular_similaridade(), validar_dispositivo_com_similaridade(), _versoes_proximas()
- **Migration MySQL:**
  - ALTER TABLE otp_dispositivo_confiavel ADD COLUMN (7 campos)
  - Índices: idx_dispositivo_native_id_ativo, idx_dispositivo_user_native
- **Benefícios:**
  - Reduz fricção: permite login direto em updates legítimos do iOS
  - Aumenta segurança: detecta mudanças suspeitas (IDFV reset, clonagem)
  - Monitoramento: logs de WARNING para análise posterior
- **Documentação:** `docs/seguranca/IMPLEMENTACAO_DEVICE_FINGERPRINT_BACKEND.md`
- **Commits:** [pending]

### [2026-03-06] - Link de Recorrência - Otimização e Correção
- **Remoção de pré-autorização de R$ 1,00:**
  - Processo de validação de cartão com transação de R$ 1,00 removido
  - Tokenização via gateway (Pinbank/OWN) já valida o cartão automaticamente
  - Fluxo simplificado: validar token → tokenizar cartão → vincular à recorrência
  - Arquivo: `checkout/link_recorrencia_web/services.py`
- **Correção erro 500 na página de sucesso:**
  - Lambda inline na URL causava Server Error 500
  - Criada view adequada `sucesso_view()`
  - Arquivos: `checkout/link_recorrencia_web/views.py`, `urls.py`
- **Impacto:** Cadastro de cartão mais rápido e sem transações desnecessárias

### [2026-03-06] - Correção Crítica de Timezone em Autenticação 2FA
- **Problema:** Dispositivos e celulares marcados como expirados imediatamente após validação
- **Causa:** Uso de `datetime.now()` (UTC) ao invés de `timezone.now()` (timezone-aware)
- **Arquivos corrigidos:**
  - `wallclub_core/seguranca/services_device.py` (10 ocorrências)
  - `apps/cliente/jwt_cliente.py` (1 ocorrência)
  - `apps/cliente/services_revalidacao_celular.py` (2 ocorrências - Python + SQL)
  - `apps/cliente/services_2fa_login.py` (1 ocorrência)
  - `apps/cliente/services_cadastro.py` (4 ocorrências + adicionado `celular_validado_em`)
- **Impacto:**
  - Campo `confiavel_ate` agora define corretamente data + 30 dias
  - Campo `celular_validado_em` atualizado no cadastro e login
  - SQL `NOW()` substituído por parâmetro com `timezone.now()`
- **Commits:** a57cce9, 8f28199

### [2026-03-06] - Parâmetros e Correções Portal Admin
- **Novos parâmetros adicionados ao download CSV:**
  - parametro_loja_31, parametro_loja_32, parametro_loja_33
  - parametro_uptal_7
- **Correção redirect sessão expirada:**
  - Redirects alterados de `redirect('portais_admin:login')` para `redirect('/')`
  - Corrige erro ao acessar via subdomínio admin.wallclub.com.br
  - Arquivos: decorators.py, controle_acesso.py
- **Merge release-2.2.2 → main:**
  - Branch release-2.2.2 removida (local e remota)
  - Documentação de deploy atualizada para release/2.2.3

### [2026-03-04] - Calculadora Credenciadora
- **Alterações nas variáveis de cálculo:**
  - var39 = parametro_loja_12 (antes: ValorTaxaMes do extrato)
  - var40 = parametro_loja_13
  - var41 = var40 * var26
  - var42 = var26 - var37 - var41 - parametro_loja_31
  - var43 = parametro_loja_18
  - var44 = var19
  - var87 = parametro_uptal_1
  - var89 = parametro_uptal_1
  - var91 = parametro_uptal_4
  - var93[0] = parametro_uptal_5
  - var94[0] = var93[0] * var26
  - var94[A] = parametro_uptal_6
  - var130 = 'Credenciadora'
- **Forçar wall='K'** em toda calculadora credenciadora
- **Novos parâmetros:** parametro_loja_31, parametro_loja_32, parametro_loja_33, parametro_uptal_7

### [2026-02-23] - Login Biométrico App Mobile
- **Endpoint:** `POST /api/v1/cliente/login_biometrico/` ✅ funcional
- **Autenticação:** CPF + device_fingerprint + canal_id
- **Validação:** DeviceManagementService.validar_dispositivo() (30 dias)
- **Retorno:** JWT token + refresh_token + dados do cliente
- **Campo:** Cliente.is_active (não 'ativo')

### [2026-02-06] - Own Financial E-commerce e Webhooks
- **Limitação Crítica:** API `/buscaTransacoesGerais` NÃO retorna e-commerce
- **Webhook Obrigatório:** Único meio de obter identificadorTransacao
- **Endpoint:** `https://wcapi.wallclub.com.br/webhook/own/transacao/` ✅
- **Novos campos em checkout_transactions:**
  - card_bin, card_last4, payment_brand_response
  - result_code, tx_transaction_id
- **Renomeações:** pinbank_response → gateway_response

### [2026-02-03] - Portal Admin RPR - Refinamento de Métricas
- Coluna "Custo ajuste nos Repasses" reposicionada
- Nova coluna "Resultado Operacional Ajustado"
- Box "Custo Direto Total": sinal invertido
- Box "Resultado Financeiro": totalizador recalculado
- Percentual de comissão dinâmico (tabela canal_comissao)

### [2026-01-31] - Arquitetura de URLs Refatorada
- Redução de 8 para 3 arquivos de URLs (62% redução)
- Função helper `get_portal_urlpatterns()`
- Middleware simplificado
- Rotas globais centralizadas

### [2026-01-31] - Sistema de Monitoramento Completo
- Prometheus + Alertmanager + Exporters
- 14 alertas configurados
- Notificações via Telegram e Email
- Métricas customizadas em todos os containers

### [2026-01-29] - GatewayRouter Portal de Vendas
- CheckoutService refatorado para usar GatewayRouter
- Seleção dinâmica Pinbank/Own por loja
- Suporte completo: tokenização, pagamento, estorno, exclusão

### [2026-01-24] - Conta Digital - Débito de Cashback Corrigido
- Método `debitar()` verifica `tipo_movimentacao.afeta_cashback`
- Débito de cashback usa `cashback_disponivel`
- Método `estornar_movimentacao()` também corrigido
- Fluxo POS com cashback funcionando 100%

### [2025-12-24] - Abstração Calculadoras Base
- Parâmetros obrigatórios (info_loja, info_canal, dados_linha)
- Sem busca interna de parâmetros
- Abstração completa (Base, Gestão, Credenciadora, Checkout)

### [2025-12-23] - Migração Pinbank para transactiondata_pos
- Endpoint `/trdata/` grava em tabela unificada
- Campo `gateway` (PINBANK/OWN)
- Campos de rastreamento de regras aplicadas

### [2025-12-20] - Migração Terminais DATETIME
- Campos `inicio`/`fim` convertidos de Unix timestamp para DATETIME

### [2025-12-08] - Transactiondata_pos Unificada
- Tabela unificada Pinbank + Own
- Endpoints: `/trdata_pinbank/` e `/trdata_own/`
- Service: TRDataPosService (parser por gateway)

### [2025-12-08] - Sistema Cashback Centralizado
- Corrigido erro `ParametrosWall.plano`
- Import `timezone` corrigido
- Tipo movimentação: CASHBACK_CREDITO unificado
- Integração completa com Conta Digital

### [2025-12-08] - Conta Digital - Movimentações Informativas REMOVIDAS
- Apenas movimentações que afetam saldo/cashback
- Histórico consultado de transactiondata_pos
- Tipos removidos: COMPRA_CARTAO, COMPRA_PIX, COMPRA_DEBITO

### [2025-12-08] - Portal Lojista - Vendas por Operador
- Relatório agrupado por operador POS
- Métricas: qtde vendas, valor total, ticket médio
- URL: `/vendas/operador/`

### [2025-12-01] - Sistema de Ofertas
- 5 tabelas criadas
- Portal Lojista: CRUD completo, disparo de push
- Segmentação: todos do canal ou grupo customizado
- Push notifications via Firebase/APN

### [2025-11-22] - Segurança e Domínios
- 11 arquivos ajustados
- CORS manual removido
- URLs hardcoded substituídas por variáveis
- HTTPS obrigatório em produção

### [2025-11-20] - Integração Own Financial
- OAuth 2.0 com token cache
- APIs de consulta: transações, liquidações
- Cargas automáticas
- Webhooks tempo real

### [2025-11-14] - Upload de Pagamentos via CSV
- Validação em 2 fases
- Tabela editável com validação em tempo real
- Processamento automático de valores decimais
- Salvamento em lote com transação atômica

### [2025-11-10] - Gestão Admin
- Filtro por tipo de transação (Wallet/Credenciadora)
- Campo `tipo_operacao` como primeira coluna
- Checkbox "Incluir transações Credenciadora"

### [2025-11-07] - Portal Admin e Infraestrutura
- Portal Admin sem prefixo `/portal_admin/`
- SubdomainRouterMiddleware ativo
- Sistema de logs unificado
- Email Service centralizado com AWS SES

### [2025-11-05] - Fase 6D - 4 Containers Independentes ✅
- Deploy independente por container
- Escalabilidade horizontal
- Isolamento de falhas
- 26 APIs REST internas
- Zero downtime em deploys seletivos

### [2025-11-01] - Fase 6C - Monorepo + wallclub_core
- Package wallclub_core criado
- 52 arquivos Python migrados
- 113 arquivos com imports atualizados
- Código compartilhado centralizado

### [2025-10-23] - Sistema Segurança Multi-Portal
- Integração RiskEngine com todos os portais
- Análise de risco em tempo real

### [2025-10-22] - Checkout Web + RiskEngine
- Integração completa
- Análise antifraude em checkout

### [2025-10-16] - WallClub Django + Risk Engine Operacionais
- Sistema fintech migrado PHP→Django
- Sistema antifraude em tempo real
- 18 cenários JWT testados

---

## Estatísticas do Projeto

- **Containers:** 9 (4 Django + Redis + 2 Celery + Beat + Nginx)
- **APIs Internas:** 26 endpoints REST
- **Regras Antifraude:** 9 (5 básicas + 4 autenticação)
- **Parâmetros Financeiros:** 3.840 configurações
- **Cenários JWT Testados:** 18
- **Services Criados:** 22
- **Queries SQL Eliminadas:** 25
- **Arquivos Migrados (Fase 6C):** 113

---

**Formato:** [YYYY-MM-DD] - Título
**Tipos:** feat, fix, refactor, docs, chore, test
