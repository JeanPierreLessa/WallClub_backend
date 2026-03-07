# WallClub Backend - Memory

**Última atualização:** 06/03/2026 19:16

---

## 🎯 Contexto Atual de Desenvolvimento

### Features em Desenvolvimento Ativo
- Sistema de recorrência operacional com Celery tasks agendadas
- Link de pagamento para cadastro de cartão em recorrências funcionando
- Portal Admin com correções de redirect
- **Device Fingerprint com Análise de Similaridade** (IMPLEMENTADO 06/03/2026)

### Decisões Técnicas Recentes (Últimos 7 dias)
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
- **Loja teste:** loja_id=14, id_plano=3
- **NSUs para teste:** 170972868, 172562013

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
