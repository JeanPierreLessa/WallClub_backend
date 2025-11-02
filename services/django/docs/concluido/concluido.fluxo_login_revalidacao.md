# Fluxos de Login, 2FA e Revalidação - Exemplos de Chamadas

## 🔒 CORREÇÃO CRÍTICA DE SEGURANÇA JWT (26/10/2025)

**FALHA GRAVE IDENTIFICADA E CORRIGIDA:**

### Problema
- ❌ Tokens JWT revogados (`is_active=0`) continuavam funcionando
- ❌ Sistema apenas decodificava JWT sem validar contra tabela de auditoria
- ❌ Novo login não revogava tokens anteriores
- ❌ Cliente podia ter múltiplos tokens ativos simultaneamente

### Correções Aplicadas

**1. `ClienteJWTAuthentication.authenticate()` (apps/cliente/jwt_cliente.py):**
```python
# AGORA VALIDA OBRIGATORIAMENTE contra cliente_jwt_tokens
jti = payload.get('jti')
if jti:
    jwt_record = ClienteJWTToken.validate_token(token, jti)
    if not jwt_record:  # Verifica is_active=True e revoked_at=NULL
        raise exceptions.AuthenticationFailed('Token inválido ou revogado')
    jwt_record.record_usage()  # Registra last_used
```

**2. `generate_cliente_jwt_token()` (apps/cliente/jwt_cliente.py):**
```python
# REVOGA AUTOMATICAMENTE tokens anteriores antes de criar novo
ClienteJWTToken.objects.filter(
    cliente=cliente,
    is_active=True
).update(
    is_active=False,
    revoked_at=datetime.utcnow()
)
```

### Validado em Produção ✅
- Token com `is_active=0` → Rejeitado com **401 Unauthorized**
- Token expirado → Rejeitado com **401 Unauthorized**
- Novo login → Tokens antigos revogados automaticamente
- Dispositivo confiável → Gera JWT novo sem pedir SMS

### Sistema Gera 2 Tokens por Login (Correto ✅)
- **Access Token** (30 dias): Usado nas requisições diárias
- **Refresh Token** (60 dias): Para renovação futura
- Padrão **OAuth 2.0** - comportamento esperado

### Renovação Automática (Dispositivo Confiável)
- Dispositivo confiável válido (< 30 dias) → `/2fa/verificar_necessidade/` gera JWT novo **sem SMS**
- App usa biometria para desbloquear `auth_token` do secure storage
- Sistema verifica device e retorna JWT automaticamente

**Documentação:** Ver Diretriz 9.1 em `docs/1. DIRETRIZES.md`

---

## ⚠️ OUTRAS ATUALIZAÇÕES CRÍTICAS (26/10/2025)

**Correções Implementadas:**

1. **Rate Limiter** - `cache.ttl()` removido (método não existe no `LocMemCache`)
2. **Feature Flag** - `cliente_id` extraído do JWT automaticamente (não do body)
3. **Device Management** - Criar NOVO registro ao reativar dispositivo (preserva histórico auditoria)
4. **Constraint UNIQUE** - Composta: `(user_id, device_fingerprint, ativo)` permite histórico
5. **Limites de Dispositivos:**
   - **Cliente:** Até **2 dispositivos ATIVOS** (validade 30 dias)
   - **Vendedor/Lojista:** 2 dispositivos
   - **Admin:** Sem limite
6. **Revalidação de Celular (90 dias):**
   - ✅ Endpoints agora usam `auth_token` (OAuth) em vez de JWT
   - ✅ Sistema 2FA detecta celular expirado automaticamente
   - ✅ Template WhatsApp unificado (`2fa_login_app`)
   - ✅ Validação antes do login completo (sem JWT)

**Arquivos Corrigidos:**
- `comum/seguranca/rate_limiter_2fa.py`
- `apps/views.py` (endpoint `/api/v1/feature_flag/`)
- `comum/seguranca/services_device.py`
- `apps/cliente/views_revalidacao.py` - Alterado para `@require_oauth_apps`
- `apps/cliente/services_revalidacao_celular.py` - Removido parâmetro `contexto`
- `apps/cliente/services_2fa_login.py` - Validação de celular expirado integrada
- `apps/cliente/jwt_cliente.py` - **Validação obrigatória contra tabela + auto-revogação**
- SQL: `ALTER TABLE otp_dispositivo_confiavel DROP INDEX device_fingerprint, ADD UNIQUE KEY unique_user_device_ativo (user_id, device_fingerprint, ativo)`

---

## 🎯 Modelo Simplificado - Fintech Moderno

**Princípios:**
- ✅ Toda senha é via SMS/WhatsApp (não existe "senha definitiva")
- ✅ JWT válido por **30 dias** (era 1 dia)
- ✅ Biometria desde primeiro acesso
- ✅ Revalidação celular a cada **90 dias** (confirma que número pertence ao usuário)
- ✅ 2FA apenas quando necessário (novo device ou token expirado)

**Inspiração:** Nubank, PicPay, Inter, C6 Bank

---

### Obter OAuth Token
```bash
curl -X POST https://apidj.wallclub.com.br/api/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "wallclub_mobile_rls_310",
    "client_secret": "wallclub_mobile_XXXGYsz7CThOUgPXWhsgNsC9mnkXNJz_ncH1nwmSerChQLY1uC0DX1ewDsJ8Dr3wMyJ",
    "grant_type": "client_credentials"
  }'
```

---

## 1️⃣ FLUXO: LOGIN SEGURO (AUTH_TOKEN → 2FA → JWT FINAL)

**Arquitetura:** Login → auth_token (5min) → 2FA verifica device → JWT final (30 dias)
**Segurança:** cliente_id NUNCA exposto - sempre encriptado no auth_token

### 1.1. Passo 1: Validar CPF → Recebe auth_token temporário (SEM SENHA)

```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/login/ \
  -H "Authorization: Bearer wc_at_zvw4n-nbjZ24x8ZlK4boesKVSzKqGgLBpUfGlzd6dwE" \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "13444714718",
    "canal_id": 1
  }'
```

⚠️ **SEM SENHA** - 2FA é obrigatório para segurança

**Resposta (200) - Auth token temporário (5min):**
```json
{
  "sucesso": true,
  "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRlX2lkIjoxMDcsImNwZiI6IjEzNDQ0NzE0NzE4IiwiY2FuYWxfaWQiOjEsImlhdCI6MTcyOTg3MDAwMCwiZXhwIjoxNzI5ODcwMzAwLCJqdGkiOiJhYmMxMjMiLCJ0b2tlbl90eXBlIjoiYXV0aF9wZW5kaW5nIn0...",
  "expires_at": "2025-10-25T15:18:00Z",
  "mensagem": "Credenciais válidas. Use auth_token para verificar 2FA."
}
```
✅ **auth_token válido por 5 minutos**
✅ **cliente_id encriptado no token (nunca exposto)**
✅ **Sem senha - 2FA obrigatório**
⚠️ **JWT final SÓ após validação 2FA**

---

### 1.2. Passo 2: Verificar necessidade de 2FA (PONTO DE EMISSÃO DO JWT)

```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/verificar_necessidade/ \
  -H "Authorization: Bearer wc_at_zvw4n-nbjZ24x8ZlK4boesKVSzKqGgLBpUfGlzd6dwE" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRlX2lkIjoxMTAsImNwZiI6IjEzNDQ0NzE0NzE4IiwiY2FuYWxfaWQiOjEsImlhdCI6MTc2MTQxNjc5MywiZXhwIjoxNzYxNDE3MDkzLCJqdGkiOiJjZGViYTM0Zi1mMGE3LTRlY2UtODk1MC0wYTMzYTkxNDViN2QiLCJ0b2tlbl90eXBlIjoiYXV0aF9wZW5kaW5nIn0.tRojLbdNG7PO3bs6Id6ZrUWvDjzp8Zes28kYqzCbX-Y",
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2",
    "contexto": "login"
  }'
```

**Resposta A - NÃO precisa 2FA (device válido) - JWT GERADO:**
```json
{
  "necessario": false,
  "motivo": "dispositivo_confiavel_valido",
  "dispositivo_confiavel": true,
  "mensagem": "Dispositivo confiável válido",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-11-24T13:00:00Z"
}
```
✅ **JWT gerado no ponto seguro (após validação de device)**
✅ **Device renovado automaticamente (30 dias)**
✅ **Biometria funciona**

**Resposta B - PRECISA 2FA (device novo/expirado):**
```json
{
  "necessario": true,
  "motivo": "novo_dispositivo",
  "dispositivo_confiavel": false,
  "mensagem": "Primeiro acesso neste dispositivo - validação necessária"
}
```
⚠️ **App deve solicitar 2FA** - Ver seção 2

**Resposta C - PRECISA REVALIDAR CELULAR (>90 dias):**
```json
{
  "necessario": true,
  "motivo": "celular_expirado",
  "dispositivo_confiavel": true,
  "mensagem": "Seu celular precisa ser revalidado para continuar usando o app",
  "dias_expirado": 5
}
```
⚠️ **App deve solicitar revalidação de celular** - Ver seção 4

**Resposta erro (400):**
```json
{
  "sucesso": false,
  "erro": "CPF não encontrado"
}
```

---

## 2️⃣ FLUXO: LOGIN COM 2FA (DEVICE NOVO/EXPIRADO)

**Cenário:** Cliente tem device novo ou device expirou (> 30 dias) - precisa validar 2FA

### 2.1. Solicitar código 2FA via WhatsApp

```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/solicitar_codigo/ \
  -H "Authorization: Bearer wc_at_kYklJKI5U6xkeviw4G7F6t2s4WUdwKKXcYmG7Vt9_LA" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2"
  }'
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via WhatsApp"
}
```

---

### 2.2. Validar código 2FA (PONTO DE EMISSÃO DO JWT)

```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/validar_codigo/ \
  -H "Authorization: Bearer wc_at_kYklJKI5U6xkeviw4G7F6t2s4WUdwKKXcYmG7Vt9_LA" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "codigo": "123456",
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2",
    "marcar_confiavel": true
  }'
```

**Resposta (200) - JWT GERADO:**
```json
{
  "sucesso": true,
  "mensagem": "2FA validado com sucesso",
  "dispositivo_registrado": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-11-24T13:00:00Z"
}
```
✅ **JWT gerado após validação 2FA**
✅ **Device registrado por 30 dias**
✅ **Biometria funciona**

**Resposta (400) - Código inválido:**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado"
}
```

**Resposta - Device confiável (200):**
```json
{
  "sucesso": true,
  "necessario": false,
  "motivo": "Dispositivo já cadastrado e confiável",
  "dispositivo_confiavel": true
}
```

**Resposta - Precisa 2FA (200):**
```json
{
  "sucesso": true,
  "necessario": true,
  "motivo": "Novo dispositivo detectado",
  "dispositivo_confiavel": false
}
```

**Resposta - Limite atingido (200):**
```json
{
  "sucesso": true,
  "necessario": true,
  "motivo": "Limite de dispositivos atingido",
  "dispositivo_confiavel": false,
  "limite_atingido": true,
  "device_atual": {
    "nome_dispositivo": "iPhone 13",
    "ultimo_acesso": "2025-10-20T15:30:00Z"
  }
}
```

---

### 1.3. Solicitar código 2FA
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/solicitar_codigo/ \
  -H "Authorization: Bearer wc_at_XGIXuMwr2ImlKE8AF8IrvUszsqHpYi6WKPPrLRRwOCE" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 12345,
    "canal_id": 1,
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2",
    "ip_address": "177.104.56.78"
  }'
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via WhatsApp para o número (21) 9****-****"
}
```

**Resposta erro (400):**
```json
{
  "sucesso": false,
  "mensagem": "Erro ao enviar código. Aguarde 60 segundos antes de solicitar novamente."
}
```

---

### 1.4. Validar código 2FA (registra device)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/validar_codigo/ \
  -H "Authorization: Bearer wc_at_XGIXuMwr2ImlKE8AF8IrvUszsqHpYi6WKPPrLRRwOCE" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 12345,
    "codigo": "123456",
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2",
    "marcar_confiavel": true,
    "ip_address": "177.104.56.78",
    "user_agent": "App Wall/1.0 (iOS 16.0)"
  }'
```

**Resposta - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código validado com sucesso",
  "dispositivo_registrado": true
}
```

**Resposta - Código inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 2
}
```

---

## 3️⃣ FLUXO: GERENCIAR DISPOSITIVOS (CLIENTE LOGADO)

### 3.1. Listar meus dispositivos
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/dispositivos/meus/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "total": 1,
  "dispositivos": [
    {
      "id": 789,
      "nome_dispositivo": "iPhone 13",
      "fingerprint": "a5b3c8d9e1f2a3b4...",
      "ip_registro": "177.104.56.78",
      "ultimo_acesso": "25/10/2025 06:15",
      "ativo": true,
      "confiavel": true,
      "expirado": false,
      "dias_restantes": 28,
      "criado_em": "27/09/2025 14:30",
      "revogado_em": null,
      "revogado_por": null
    }
  ]
}
```

---

### 3.2. Revogar dispositivo específico
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/dispositivos/revogar/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2"
  }'
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "mensagem": "Dispositivo removido com sucesso"
}
```

---

## 4️⃣ FLUXO: REVALIDAÇÃO DE CELULAR (90 DIAS)

**IMPORTANTE:** Endpoints de revalidação usam `auth_token` (OAuth), NÃO JWT.
Permite validar celular ANTES do login completo.

### 4.1. Verificar status do celular
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/celular/status/ \
  -H "Authorization: Bearer wc_at_XXX" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Resposta - Celular válido (200):**
```json
{
  "sucesso": true,
  "valido": true,
  "dias_restantes": 45,
  "precisa_revalidar": false,
  "ultima_validacao": "2025-09-10T14:30:00Z"
}
```

**Resposta - Precisa revalidar (200):**
```json
{
  "sucesso": true,
  "valido": false,
  "dias_restantes": -5,
  "precisa_revalidar": true,
  "ultima_validacao": "2025-07-20T10:15:00Z",
  "dias_expirados": 5
}
```

---

### 4.2. Solicitar código de revalidação
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/celular/solicitar_codigo/ \
  -H "Authorization: Bearer wc_at_XXX" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via WhatsApp para (21) 9****-7890"
}
```

---

### 4.3. Validar código de revalidação
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/celular/validar_codigo/ \
  -H "Authorization: Bearer wc_at_XXX" \
  -H "Content-Type: application/json" \
  -d '{
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "codigo": "123456"
  }'
```

**Resposta - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Celular revalidado com sucesso",
  "proxima_validacao": "2026-01-23T06:15:00Z"
}
```

**Resposta - Código inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 2
}
```

---

### 4.4. Verificar bloqueio de transação (antes de usar saldo)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/celular/verificar_bloqueio/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

**Resposta - Liberado (200):**
```json
{
  "sucesso": true,
  "bloqueado": false,
  "pode_transacionar": true
}
```

**Resposta - Bloqueado (200):**
```json
{
  "sucesso": true,
  "bloqueado": true,
  "pode_transacionar": false,
  "motivo": "Celular não validado há mais de 30 dias",
  "dias_expirados": 5,
  "mensagem": "Valide seu celular para continuar usando o saldo"
}
```

---

## 5️⃣ FLUXO: TOKEN EXPIRADO (APÓS 30 DIAS)

**Cenário:** JWT expirou após 30 dias. Cliente precisa revalidar.

---

### 5.1. Tentar acessar com token expirado
```bash
curl -X GET https://apidj.wallclub.com.br/api/v1/cliente/perfil/ \
  -H "Authorization: Bearer <token_expirado>"
```

**Resposta (401):**
```json
{
  "sucesso": false,
  "mensagem": "Token expirado",
  "codigo": "token_expired"
}
```

---

### 5.2. Solicitar código 2FA para revalidar
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/solicitar_codigo/ \
  -H "Authorization: Bearer wc_at_l4JMThMvZy1EoQJK-7whYkf2BK8JEnF2EsSvQ7lAua8" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 110,
    "canal_id": 1
  }'
```

**Resposta (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via WhatsApp"
}
```

---

### 5.3. Validar 2FA → Recebe novo JWT 30 dias
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/2fa/validar_codigo/ \
  -H "Authorization: Bearer wc_at_l4JMThMvZy1EoQJK-7whYkf2BK8JEnF2EsSvQ7lAua8" \
  -H "Content-Type: application/json" \
  -d '{
    "cliente_id": 110,
    "codigo": "123456",
    "device_fingerprint": "a5b3c8d9e1f2a3b4c5d6e7f8a9b0c1d2",
    "marcar_confiavel": true,
    "user_agent": "App Wall/1.0 (iOS 16.0)"
  }'
```

**Resposta - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código validado com sucesso",
  "dispositivo_registrado": true
}
```

**Resposta - Código inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 2
}
```

---

## 📋 RESUMO DOS ENDPOINTS

| Endpoint | Método | Auth | Descrição |
|----------|--------|------|-----------|
| `/cliente/login/` | POST | OAuth API Key | Login apenas com CPF (sem senha) |
| `/cliente/2fa/verificar_necessidade/` | POST | OAuth API Key | Verifica se precisa 2FA |
| `/cliente/2fa/solicitar_codigo/` | POST | OAuth API Key | Envia código 2FA |
| `/cliente/2fa/validar_codigo/` | POST | OAuth API Key | Valida 2FA + Registra device |
| `/cliente/dispositivos/meus/` | POST | JWT Token | Lista devices do cliente |
| `/cliente/dispositivos/revogar/` | POST | JWT Token | Remove device específico |
| `/cliente/celular/status/` | POST | OAuth + auth_token | Status de validade celular |
| `/cliente/celular/solicitar_codigo/` | POST | OAuth + auth_token | Código revalidação |
| `/cliente/celular/validar_codigo/` | POST | OAuth + auth_token | Revalida celular |
| `/cliente/celular/verificar_bloqueio/` | POST | JWT | Verifica bloqueio transação |

---

## 🔑 Headers Obrigatórios

### OAuth API Key (endpoints públicos)
```
Authorization: Bearer wc_at_XGIXuMwr2ImlKE8AF8IrvUszsqHpYi6WKPPrLRRwOCE
```

### JWT Token (cliente logado)
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

---

## 📄 MUDANÇAS DO NOVO MODELO

### O que mudou?

| Aspecto | Antes | Agora |
|---------|-------|-------|
| **JWT expiração** | 1 dia | 30 dias |
| **Refresh token** | 7 dias | 60 dias |
| **Celular validade** | 90 dias | 90 dias (mantido) |
| **Senha** | Temporária → Definitiva | Sempre via SMS |
| **Onboarding** | 4 passos | 2 passos |
| **Biometria** | Após criar senha | Desde dia 1 |

### Fluxo simplificado

```
CADASTRO
  ↓
Senha SMS (4 dígitos)
  ↓
LOGIN → JWT 30 dias
  ↓
Biometria funciona
  ↓
(Após 30 dias)
  ↓
2FA → Novo JWT 30 dias
```

### Endpoints removidos
- ❌ `/cliente/senha/criar_definitiva/` (não usado)
- ❌ `/cliente/senha/trocar/` (senha sempre via SMS)

### Por que essa mudança?

1. **UX melhor**: Zero fricção no onboarding
2. **Mais seguro**: Revalidação 3x mais frequente (30 vs 90 dias)
3. **Padrão mercado**: Nubank, PicPay, Inter fazem assim
4. **Realidade**: Usuário sempre podia resetar via SMS mesmo

---
