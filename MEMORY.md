# WallClub Backend - Memory

**Última atualização:** 08/03/2026 19:45

---

## 🎯 Contexto Atual de Desenvolvimento

### Features em Desenvolvimento Ativo
- Sistema de recorrência operacional com Celery tasks agendadas
- Link de pagamento para cadastro de cartão em recorrências funcionando
- Portal Admin com correções de redirect
- **Device Fingerprint com Análise de Similaridade** (IMPLEMENTADO 06/03/2026)
- **Sistema de Cupons** - Portal Lojista e API POS operacionais (07/03/2026)

### Decisões Técnicas Recentes (Últimos 7 dias)
- **08/03/2026:** Otimizações Continue - Rate Limit Prevention
  - **Problema:** Rate limit de 450k tokens/minuto sendo atingido com frequência
  - **Causa:** Continue enviando muitos arquivos como contexto (200k-400k tokens/requisição)
  - **Soluções aplicadas:**
    - Criado `.continueignore` otimizado (docs/, logs/, docker-compose.yml, *.md, etc.)
    - Documentação completa: `docs/desenvolvimento/OTIMIZACOES_CONTINUE_RATE_LIMIT.md`
    - Configurações recomendadas: maxFiles=5, maxTokens=2000, disable auto-context
  - **Resultado esperado:** Redução de 80-90% no consumo (30k-50k tokens/requisição)
  - **Impacto:** Desenvolvimento mais fluido, menos interrupções por rate limit
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
