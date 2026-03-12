# WallClub Backend - Memory

**Última atualização:** 11/03/2026 00:54

---

## 🎯 Contexto Atual de Desenvolvimento

### Features em Desenvolvimento Ativo
- Sistema de recorrência operacional com Celery tasks agendadas
- Link de pagamento para cadastro de cartão em recorrências funcionando
- Portal Admin com correções de redirect
- **Device Fingerprint com Análise de Similaridade** (IMPLEMENTADO 06/03/2026)
- **Sistema de Cupons** - Portal Lojista e API POS operacionais (07/03/2026)
- **Sistema de Alertas via Telegram** (IMPLEMENTADO 09/03/2026)
- **Integração Own Financial** - Página de edição de loja corrigida (11/03/2026)

### Decisões Técnicas Recentes (Últimos 7 dias)
- **11/03/2026:** Correções na Página de Edição de Loja (Own Financial) ⭐ IMPLEMENTADO
  - **Problema:** Interface de edição de loja com cestas de tarifas misturadas e enviando dados incorretos para API Own
  - **Causa raiz:**
    - JavaScript carregava 4 cestas (333, 1655, 117, 1608) mas IDs dos containers estavam errados
    - Backend coletava TODAS as tarifas do formulário independente do modelo escolhido
    - Cestas ficavam ocultas após carregamento assíncrono
  - **Soluções implementadas:**
    - **Frontend (JavaScript):**
      - Corrigidos IDs dos containers: `tarifas_cesta_parcela_pos`, `tarifas_cesta_parcela_ecommerce`, `tarifas_cesta_bandeira_mdr`, `tarifas_cesta_ecommerce_mdr`
      - Método `aplicarVisibilidadeCestas()` executado após carregamento completo das 4 cestas
      - Dois checkboxes sincronizados (FLEX e MDR) via JavaScript
      - Logs detalhados para debug
    - **Backend (Python):**
      - Filtro de tarifas por modelo: FLEX filtra apenas {333, 1655}, MDR filtra apenas {117, 1608}
      - Sincronização automática de tarifas ao carregar página (compara banco vs API)
      - Aplicado em 2 locais: cadastro inicial e reenvio com protocolo
    - **Template (HTML):**
      - Checkbox E-commerce movido para cima dos títulos das seções
      - Removido checkbox duplicado ao lado dos campos de antecipação
      - Separação visual clara: FLEX (333 + 1655) vs MDR (117 + 1608)
  - **Arquivos modificados:**
    - `services/django/portais/admin/templates/portais/admin/loja_edit.html`
    - `services/django/portais/admin/static/js/cadastro_loja_own.js`
    - `services/django/portais/admin/views_hierarquia.py`
  - **Estrutura das cestas Own Financial:**
    - **FLEX (sem antecipação):**
      - Cesta 333: Tarifas por parcela POS
      - Cesta 1655: Tarifas por parcela E-commerce
    - **MDR (com antecipação):**
      - Cesta 117: Tarifas por bandeira POS
      - Cesta 1608: Tarifas por bandeira E-commerce
  - **Status:** Testado e funcionando, aguardando validação de envio de tarifas para API Own
- **09/03/2026:** Sistema de Alertas Telegram Operacional ⭐ IMPLEMENTADO
  - **Problema:** Alertmanager não enviava notificações para Telegram - bot_token não era substituído
  - **Causa raiz:** Arquivo `/etc/alertmanager/alertmanager.yml` montado read-only do host com variáveis não substituídas
  - **Solução:**
    - Script `alertmanager-entrypoint.sh` busca credenciais do AWS Secrets Manager
    - Gera arquivo `/tmp/alertmanager.yml` com bot_token e chat_id substituídos
    - Dockerfile customizado (Debian base + AWS CLI v2 + jq) igual ao Flower
    - Alertmanager inicia com `--config.file=/tmp/alertmanager.yml`
  - **Arquivos criados:**
    - `Dockerfile.alertmanager`: Multi-stage build (Debian + alertmanager binário)
    - `monitoring/alertmanager-entrypoint.sh`: Script que busca secrets e substitui variáveis
    - `monitoring/alertmanager.yml`: Template com `${TELEGRAM_MONITOR_BOT_TOKEN}` e `${TELEGRAM_MONITOR_BOT_CHAT_ID}`
  - **Bot Telegram:** @Wallclub_monitor_bot (ID: 8352234743)
  - **Alertas configurados:**
    - ServiceDown (30s), RedisDown (1m), MySQLDown (1m)
    - DiskSpaceLow (10% critical, 20% warning)
    - HighCPUUsage (>80% por 10min), HighMemoryUsage (>90% por 10min)
    - LowAvailability (<95% na última hora)
    - CeleryTasksFailing, RedisMemoryHigh, MySQLConnectionsHigh
  - **Comportamento de envio:**
    - `repeat_interval: 1h` para alertas warning (evita spam)
    - `repeat_interval: 30m` para alertas critical
    - `send_resolved: true` envia notificação quando alerta é resolvido
    - `group_wait: 10s` agrupa alertas similares
  - **Teste realizado:** Alerta manual enviado com sucesso via Telegram
  - **Status:** Produção ativa, monitorando infraestrutura 24/7
- **08/03/2026:** Otimizações Continue - Redução de 85-99% nos Custos da API Claude ⭐ IMPLEMENTADO
  - **Problema:** Custo mensal com API Claude em ~$1,200/mês, rate limit frequente (450k tokens/min)
  - **Causa:** Continue enviando muito contexto (200k-400k tokens/requisição) e usando modelo Opus como padrão
  - **Soluções implementadas:**
    - ✅ Criado `.continueignore` otimizado (exclusão: docs/, migrations/, *.md, node_modules/, __pycache__/, .venv/, dist/, build/, *.log, etc.)
    - ✅ Implementado **Claude Haiku 4.5 como modelo padrão** (94% mais barato que Opus)
    - ✅ Configurações `config.yaml`: maxTokens=2000 em TODOS os modelos
    - ✅ Configurações `config.json`: maxFiles=5, maxFileSize=15000, contextWindow=4096
    - ✅ Desabilitado: Diagnostics (lsp.disabled=true), Autocomplete (tabAutocompleteModel.disabled=true)
    - ✅ Cache de Contexto adicionado em Sonnet 4.5 e Opus (cacheSize=2048, cacheTTL=3600)
  - **Modelos configurados (em ordem de custo):**
    - 🟢 Claude Haiku 4.5 (PADRÃO - USE 90% DO TEMPO): $1/$5 por 1M tokens (input/output)
    - 🟡 Claude Sonnet 4.5 (Intermediário): $3/$15 por 1M tokens
    - 🔴 Claude Opus 4.5 (Premium): $15/$75 por 1M tokens
  - **Economia realizada:**
    - Antes: ~$1,200/mês (usando Opus como padrão)
    - Depois: ~$12/mês (usando Haiku como padrão)
    - **Total economizado: ~$1,188/mês (99% redução!)**
  - **Como usar:**
    - Use **Haiku 4.5** para: debugging, CRUD, refatorações médias, testes, explicações (90% do trabalho)
    - Use **Sonnet 4.5** para: arquitetura complexa, refatorações grandes, código crítico
    - Use **Opus** apenas para: casos extremamente críticos que outras falham
  - **Como trocar modelo no Continue:**
    1. Abra Continue (Cmd+L)
    2. Clique no nome do modelo no topo
    3. Selecione outro modelo
    4. **SEMPRE volte para Haiku 4.5 após usar modelos caros!**
  - **Arquivos atualizados:**
    - `~/.continue/config.yaml`: modelos com maxTokens e cache
    - `~/.continue/config.json`: maxFiles, maxFileSize, contextWindow, desabilitado autocomplete/embeddings
    - `WallClub_backend/.continueignore`: otimizado para desenvolvimento
  - **Impacto:** Desenvolvimento mais rápido (menos rate limit), custos reduzidos em 99%, continue mantém qualidade
- **08/03/2026:** Limpeza de Infraestrutura AWS - Economia R$ 77/mês
  - **Situação:** Recursos AWS não utilizados identificados via console
  - **Recursos removidos:**
    - ALB "prd-php-mysql" (sem targets desde Janeiro) - R$ 60/mês
    - 5 AMIs php-nginx antigas (2025-08-03, 2025-08-14, 20250909, 20251017, sem data) - R$ 12-15/mês
    - ~250GB snapshots EBS correspondentes
  - **Descobertas para validação com infra:**
    - AMI mysql-prd (ami-02db39fb1a6e7cf25) - máquina usa Ubuntu oficial
    - AMI prod-server-20250505 (ami-0a96784fea2e2c915) - nenhuma instância usa
    - Economia potencial adicional: R$ 5-8/mês
  - **Validação:** Máquinas confirmadas usando AMIs corretas (Ubuntu oficial)
  - **Documentação atualizada:**
    - `docs/infraestrutura/MAPA_INFRAESTRUTURA_ATUAL.md`: economia R$ 1.590 → R$ 1.513/mês
    - `README.md`: estatística de economia adicionada
    - `CHANGELOG.md`: entrada completa da otimização
  - **Confirmação:** Todas as 4 máquinas EC2 funcionando normalmente após limpeza
- **07/03/2026:** Otimizações de Memória Docker - Diagnóstico e Ajustes
  - **Problema inicial:** Consumo de RAM em 76% (2.9GB de 3.8GB) com baixo volume
  - **Investigação:** Processos Python aparecendo duplicados no `ps aux` do host
  - **Descoberta crítica:** Processos NÃO estão duplicados - Docker compartilha user namespace com host
  - **Confirmação:** PIDs do container = PIDs visíveis no host (comportamento normal do Docker)
  - **Análise real:**
    - wallclub-celery-beat: 114MB de 128MB (89% - crítico)
    - wallclub-celery-worker: 368MB de 512MB (72%)
    - wallclub-grafana: 239MB de 256MB (93% - crítico)
    - wallclub-portais: 289MB (3 workers gunicorn)
    - wallclub-apis: 353MB (4 workers gunicorn)
  - **Otimizações aplicadas:**
    - Celery Beat: limite 128MB → 256MB
    - Celery Worker: concurrency 5 → 3
    - Gunicorn Portais: 3 → 2 workers
    - Gunicorn APIs: 4 → 2 workers
  - **Resultado esperado:** Consumo de 76% → ~63% (~500MB economizados)
  - **Arquivos:** docker-compose.yml, Dockerfile.portais, Dockerfile.apis
  - **Lição aprendida:** Sempre verificar PIDs antes de assumir duplicação de processos
- **07/03/2026:** Sistema de Cupons - Correções de Validação e Formulário
  - **Problema 1:** Formulário de criação enviando `loja_id='None'` como string
  - **Solução:** Template corrigido para sempre mostrar select de lojas (padrão cashback)
  - **Problema 2:** `lojas_acessiveis` retorna lista de dicts, não objetos
  - **Solução:** Acesso corrigido de `.id` para `['id']` em views_cupons.py
  - **Problema 3:** API retornando erro genérico para validações de negócio
  - **Solução:** Captura de `ValidationError` ao invés de `ValueError` em api_views.py
  - **Impacto:** Mensagens de validação claras ("Valor mínimo: R$ 1000.00") ao invés de erro 500
  - Arquivos: portais/lojista/views_cupons.py, templates/cupons/form.html, apps/cupom/api_views.py
  - **API Endpoint:** `POST /api/v1/cupons/validar/` (OAuth POS, 30 req/min)
- **06/03/2026:** Device Fingerprint com Análise de Similaridade - IMPLEMENTAÇÃO COMPLETA
  - **Problema:** Sistema anterior validava apenas hash exato do fingerprint
  - **Solução híbrida:** Armazenar componentes individuais + calcular similaridade
  - **Componentes:** native_id (40pts), screen_resolution (20pts), device_model (20pts), device_brand (10pts), os_version (5pts), timezone (5pts), platform
  - **Lógica de decisão:**
    - Score 100 (hash exato) → `allow`
    - Score ≥90 (1 componente mudou) → `allow` COM MONITORAMENTO
    - Score 80-89 (2 componentes) → `require_otp`
    - Score 50-79 (suspeito) → `require_otp`
    - Score <50 (novo device) → `require_otp` ou `block`
  - **Backend - Models & Services:**
    - `wallclub_core/seguranca/models.py`: 7 novos campos no modelo DispositivoConfiavel
    - `wallclub_core/seguranca/services_device.py`: métodos `calcular_similaridade()`, `validar_dispositivo_com_similaridade()`, `_versoes_proximas()`
  - **Backend - Endpoints Atualizados (6 endpoints):**
    - `apps/cliente/views_login_biometrico.py`: Login biométrico com validação de similaridade
    - `apps/cliente/views_2fa_login.py`: Endpoints 2FA (verificar_necessidade, validar_codigo)
    - `apps/cliente/views_cadastro.py`: Validar OTP cadastro
    - `apps/cliente/views_refresh_jwt.py`: Refresh token
    - `apps/cliente/services_2fa_login.py`: Service 2FA com parâmetro dados_dispositivo
    - `apps/cliente/services_cadastro.py`: Service cadastro com parâmetro dados_dispositivo
    - `apps/cliente/jwt_cliente.py`: refresh_cliente_access_token() com dados_dispositivo
  - **Retrocompatibilidade:** 100% compatível com apps antigos via fallback automático
  - **Migration:** ALTER TABLE executada com sucesso (MySQL) - `docs/seguranca/migration_device_fingerprint_componentes.sql`
  - **Benefício:** Permite login direto em updates legítimos (iOS update) enquanto detecta fraudes
  - **Status:** Pronto para produção. App mobile precisa enviar os 7 componentes nos payloads
- **06/03/2026:** Link de Recorrência - Otimização e correção
  - **Removida pré-autorização de R$ 1,00:** Tokenização do gateway já valida o cartão
  - Fluxo simplificado: validar token → tokenizar → vincular à recorrência
  - **Corrigido erro 500 na página de sucesso:** Lambda inline substituída por view adequada
  - Arquivos: checkout/link_recorrencia_web/services.py, views.py, urls.py
  - **Celery tasks configuradas:**
    - `processar-recorrencias-do-dia`: 09:30 diariamente
    - `retentar-cobrancas-falhadas`: 21:30 diariamente
    - `notificar-recorrencias-hold`: 18:00 diariamente
- **06/03/2026:** Correção crítica de timezone em autenticação 2FA
  - Problema: `datetime.now()` retorna UTC, causando diferença de 3h (UTC-3 Brasília)
  - Solução: Substituir por `timezone.now()` em 5 arquivos (18 ocorrências)
  - Impacto: Dispositivos e celulares não expiram mais imediatamente
  - Arquivos: services_device.py, jwt_cliente.py, services_revalidacao_celular.py, services_2fa_login.py, services_cadastro.py
  - **IMPORTANTE:** Sempre usar `timezone.now()` ao invés de `datetime.now()` para datas do Django
- **06/03/2026:** Campo `celular_validado_em` adicionado ao fluxo de cadastro
  - Antes: Campo ficava NULL após cadastro, causando erro "celular_expirado"
  - Agora: Atualizado automaticamente ao validar OTP do cadastro
  - Arquivo: services_cadastro.py linha 392
- **06/03/2026:** Correção de redirects no portal admin para usar URLs relativas
  - Problema: `redirect('portais_admin:login')` resolvia para `/portal_admin/` via subdomínio
  - Solução: Usar `redirect('/')` em decorators.py e controle_acesso.py
- **06/03/2026:** Download CSV de parâmetros corrigido
  - Problema: Erro 500 ao acessar /parametros/template/
  - Causa: Tentativa de buscar planos via API que estava falhando
  - Solução: Buscar diretamente do banco com `Plano.objects.all()`
  - Arquivo: views_importacao.py
- **06/03/2026:** Merge release-2.2.2 → main concluído
  - Branch release-2.2.2 removida (local e remota)
  - Ambiente de produção agora usa release/2.2.3
- **04/03/2026:** Calculadora credenciadora agora força `wall='K'` para todos os parâmetros
- **04/03/2026:** Variáveis alteradas para buscar de parametros ao invés de extrato Pinbank:
  - var39 = parametro_loja_12
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

---

## 🐛 Bugs Conhecidos em Investigação

_Nenhum bug ativo no momento._

### Bugs Resolvidos Recentemente
- **[RESOLVIDO 07/03/2026]** Erro ao criar cupom: "invalid literal for int() with base 10: 'None'"
  - Causa: Template enviando `loja_id='None'` como string quando não havia loja na sessão
  - Solução: Template sempre mostra select de lojas + validação no POST
- **[RESOLVIDO 07/03/2026]** API de cupom retornando erro 500 para validações de negócio
  - Causa: Captura de `ValueError` ao invés de `ValidationError`
  - Solução: Import e captura corrigidos em apps/cupom/api_views.py
- **[RESOLVIDO 06/03/2026]** Dispositivos marcados como expirados imediatamente após validação
  - Causa: Uso de `datetime.now()` ao invés de `timezone.now()`
  - Solução: 18 substituições em 5 arquivos
- **[RESOLVIDO 06/03/2026]** Celular sempre pedindo revalidação após cadastro
  - Causa: Campo `celular_validado_em` não era atualizado no cadastro
  - Solução: Adicionada linha em services_cadastro.py:392
- **[RESOLVIDO 06/03/2026]** Erro 500 em /parametros/template/
  - Causa: API de planos falhando
  - Solução: Buscar planos do banco ao invés da API

---

## 🧪 Dados de Teste

### Credenciais de Teste
- **Cliente teste:** CPF 17653377807, Canal ID: 1
- **Loja teste:** loja_id=26 (cupons), loja_id=14 (parâmetros), id_plano=3
- **NSUs para teste:** 170972868, 172562013
- **Cupom teste:** PROMO_FERNANDO (loja 26, valor_minimo_compra: R$ 1000.00)

### Valores de Parâmetros (wall='K', loja=14, plano=3)
```sql
parametro_uptal_1 = 0.0078500000
parametro_uptal_4 = ?
parametro_uptal_5 = ?
parametro_uptal_6 = ?
parametro_loja_12 = ?
parametro_loja_13 = ?
parametro_loja_18 = ?
parametro_loja_31 = ?
```

---

## ⚠️ Erros Pré-Existentes (NÃO Corrigir)

_Nenhum erro pré-existente catalogado no momento._

---

## 📝 Notas de Sessão

### Comandos Úteis Recentes
```bash
# Processar NSU específico
docker exec -it wallclub-portais python manage.py carga_base_unificada_credenciadora --nsu 170972868

# Carregar extrato POS
docker exec -it wallclub-portais python manage.py carga_extrato_pos 72h

# Verificar logs
tail -100 services/django/logs/parametros_wallclub.log
```

### Queries SQL Úteis
```sql
-- Verificar parâmetros wall='K'
SELECT id, loja_id, id_plano, wall, parametro_uptal_1, parametro_loja_12
FROM parametros_wallclub
WHERE loja_id = 14 AND id_plano = 3 AND wall = 'K'
ORDER BY data_inicio DESC;

-- Verificar resultado do cálculo
SELECT var87, var89, var91, var93, var94, var94_A, var130
FROM base_transacoes_unificadas
WHERE var9 = '170972868';
```

---

## 🔄 Próximos Passos

1. ✅ ~~Testar download de parâmetros ativos em produção~~ (Concluído)
2. ✅ ~~Verificar erro 500 no template CSV~~ (Resolvido)
3. ✅ ~~Validar redirect após timeout de sessão~~ (Corrigido)
4. Validar fluxo completo de cadastro + login em produção após deploy

---

**Instruções de Uso:**
- Mantenha apenas informações dos últimos 30 dias
- Remova decisões que já foram consolidadas na arquitetura
- Atualize bugs resolvidos para "Resolvido" antes de remover
