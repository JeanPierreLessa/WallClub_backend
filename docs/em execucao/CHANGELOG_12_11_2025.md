# Changelog - 12/11/2025

## Melhorias de Segurança e Autenticação

### 1. Captura de IP Real do Cliente ✅

**Problema:** Sistema capturava IP interno do Load Balancer (10.0.0.x) em vez do IP real do cliente.

**Solução:**
- Configurado Nginx para confiar no header `X-Forwarded-For` do ALB
- Adicionado no `nginx.conf`:
  ```nginx
  set_real_ip_from 10.0.0.0/16;
  real_ip_header X-Forwarded-For;
  real_ip_recursive on;
  ```

**Arquivos alterados:**
- `nginx.conf`
- `apps/cliente/jwt_cliente.py` - Usa `get_client_ip()` em vez de `REMOTE_ADDR`
- `apps/cliente/views_senha.py` - Usa `get_client_ip()`
- `apps/cliente/views_2fa_login.py` - Usa `get_client_ip()`

**Impacto:**
- ✅ Rate limiting funciona por IP real do cliente
- ✅ Auditoria de dispositivos com IP correto
- ✅ Sistema antifraude com dados precisos
- ✅ Logs mostram IP real da internet

---

### 2. Limite de Dispositivos Aumentado ✅

**Mudança:** Limite de dispositivos por cliente aumentado de 2 para 5.

**Arquivo alterado:**
- `apps/cliente/services_2fa_login.py` (linhas 510, 535, 541)

**Motivo:** Permitir que clientes usem mais dispositivos sem precisar revogar constantemente.

---

### 3. POS Não Cria Mais Senha Inútil ✅

**Problema:** 
- POS cadastrava cliente com senha temporária de 4 dígitos
- Senha era enviada via WhatsApp/SMS
- Cliente nunca usava essa senha (fazia cadastro completo no app)
- Senha ficava "perdida" no banco

**Solução:**
- Removida geração e envio de senha no cadastro via POS
- Cliente criado com hash dummy: `make_password(None)`
- Cliente deve fazer cadastro completo no app para definir senha real

**Arquivo alterado:**
- `apps/cliente/services.py` - Método `ClienteAuthService.cadastrar()`

**Comportamento:**
- POS cadastra cliente apenas para liberar uso de saldo/cashback
- Hash dummy no banco (nunca vai funcionar para login)
- Cliente faz cadastro no app → define senha real → consegue fazer login

---

### 4. Registro de Dispositivo no Cadastro ✅

**Problema:**
- Cliente fazia cadastro → validava OTP → cadastro completo ✅
- Cliente fazia login → dispositivo não existia → **pedia OTP novamente** ❌

**Solução:**
- Endpoint `validar_otp_cadastro` agora registra dispositivo como confiável
- Cliente valida OTP do cadastro → dispositivo registrado automaticamente
- Próximo login → dispositivo já existe → **sem OTP duplicado** ✅

**Arquivos alterados:**
- `apps/cliente/views_cadastro.py` - Captura `device_fingerprint`, IP e user agent
- `apps/cliente/services_cadastro.py` - Registra dispositivo após validar OTP

**Payload esperado do app:**
```json
POST /api/v1/cliente/cadastro/validar_otp/
{
  "cpf": "12345678900",
  "codigo": "123456",
  "canal_id": 1,
  "device_fingerprint": "6aa0e9bd51366b1c2e6d50b7e86beb9f"  // ← Adicionar no app
}
```

**Status:** Backend pronto, aguardando atualização do app.

---

## Logs de Debug Adicionados

Para facilitar troubleshooting, foram adicionados logs detalhados:

```python
# Verifica se device_fingerprint foi recebido
🔍 DEBUG validar_otp_cadastro: device_fingerprint=SIM/NÃO, ip=..., user_agent=...

# Sucesso ao registrar
✅ Dispositivo registrado no cadastro: cliente=123, device=6aa0e9bd...

# Erro ao registrar (com traceback completo)
⚠️ Erro ao registrar dispositivo no cadastro: ...

# App não enviou device_fingerprint
⚠️ device_fingerprint NÃO foi enviado pelo app no validar_otp_cadastro
```

---

## Deploy

```bash
cd /var/www/WallClub_backend
git pull origin main
docker-compose build --no-cache wallclub-apis wallclub-portais wallclub-pos nginx
docker-compose down
docker-compose up -d
```

---

## Pendências

- [ ] App mobile: Adicionar `device_fingerprint` no payload de `POST /api/v1/cliente/cadastro/validar_otp/`

---

**Data:** 12/11/2025  
**Responsável:** Jean Lessa + Claude AI
