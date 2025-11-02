# 📘 Especificação Completa - `/api/v1/cliente/login/`

## **Endpoint**
```
POST /api/v1/cliente/login/
```

## **Headers**
```
Content-Type: application/json
Authorization: Bearer <oauth_token>  // Token OAuth do canal
```

## **Request Body**
```json
{
  "cpf": "12345678901",
  "senha": "senha123",
  "canal_id": 1,
  "firebase_token": "opcional",
  "ip_address": "opcional"
}
```

---

## 📤 Respostas Possíveis

### 1️⃣ **Sucesso - Login Válido**
```json
{
  "sucesso": true,
  "codigo": "success",
  "mensagem": "Credenciais válidas. Use auth_token para verificar 2FA.",
  "data": {
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expires_at": "2025-10-28T18:20:00"
  }
}
```
**Status HTTP:** 200  
**Ação:** Usar `auth_token` para verificar necessidade de 2FA

---

### 2️⃣ **Erro - Credenciais Inválidas (1-4 tentativas)**
```json
{
  "sucesso": false,
  "codigo": "invalid_credentials",
  "mensagem": "CPF ou senha incorretos",
  "tentativas": {
    "restantes": 3,
    "limite": 5,
    "janela_minutos": 15
  }
}
```
**Status HTTP:** 200  
**Notificação WhatsApp:** A partir da 3ª tentativa → `alerta_seguranca_tentativa_falha`

---

### 3️⃣ **Erro - Conta Bloqueada por Tentativas (5ª tentativa)**
```json
{
  "sucesso": false,
  "codigo": "account_locked",
  "mensagem": "Muitas tentativas incorretas. Conta temporariamente bloqueada.",
  "bloqueio": {
    "ativo": true,
    "motivo": "limite_15min_atingido",
    "bloqueado_ate": "2025-10-28T18:20:00",
    "retry_after_seconds": 900
  }
}
```
**Status HTTP:** 200  
**Motivos possíveis:**
- `limite_15min_atingido` - 5 tentativas em 15 minutos (bloqueio: 15 min)
- `limite_1h_atingido` - 10 tentativas em 1 hora (bloqueio: 1 hora)
- `limite_24h_atingido` - 15 tentativas em 24 horas (bloqueio: 24 horas)

**Notificação WhatsApp:** `alerta_seguranca_bloqueio_conta`

---

### 4️⃣ **Erro - Já Bloqueado (tentativa durante bloqueio)**
```json
{
  "sucesso": false,
  "codigo": "account_locked",
  "mensagem": "Conta bloqueada por 15 minutos devido a múltiplas tentativas incorretas.",
  "bloqueio": {
    "ativo": true,
    "motivo": "limite_15min_atingido",
    "bloqueado_ate": "2025-10-28T18:15:30",
    "retry_after_seconds": 780
  }
}
```
**Status HTTP:** 200  
**Nota:** `retry_after_seconds` diminui a cada tentativa

---

### 5️⃣ **Erro - Rate Limit por CPF**
```json
{
  "sucesso": false,
  "codigo": "rate_limit_cpf",
  "mensagem": "Muitas tentativas. Conta temporariamente bloqueada.",
  "bloqueio": {
    "ativo": true,
    "motivo": "rate_limit_cpf",
    "bloqueado_ate": null,
    "retry_after_seconds": 3600
  }
}
```
**Status HTTP:** 200  
**Quando:** Excede limite do rate limiter por CPF  
**Notificação WhatsApp:** `alerta_seguranca_bloqueio_conta`

---

### 6️⃣ **Erro - Rate Limit por IP**
```json
{
  "sucesso": false,
  "codigo": "rate_limit_ip",
  "mensagem": "Muitas tentativas deste endereço IP.",
  "bloqueio": {
    "ativo": true,
    "motivo": "rate_limit_ip",
    "bloqueado_ate": null,
    "retry_after_seconds": 3600
  }
}
```
**Status HTTP:** 200  
**Quando:** Excede limite do rate limiter por IP

---

### 7️⃣ **Erro - Cadastro Incompleto**
```json
{
  "sucesso": false,
  "codigo": "incomplete_registration",
  "mensagem": "Complete seu cadastro no app antes de fazer login"
}
```
**Status HTTP:** 200  
**Quando:** Cliente existe mas `cadastro_completo=False`

---

### 8️⃣ **Erro - Interno do Servidor**
```json
{
  "sucesso": false,
  "codigo": "internal_error",
  "mensagem": "Erro interno do servidor"
}
```
**Status HTTP:** 200  
**Quando:** Exception não tratada

---

## 🔑 Códigos de Resposta

| Código | Descrição | HTTP Status |
|--------|-----------|-------------|
| `success` | Login bem-sucedido | 200 |
| `invalid_credentials` | CPF ou senha incorretos | 200 |
| `account_locked` | Bloqueio por excesso de tentativas | 200 |
| `rate_limit_cpf` | Bloqueio por rate limit no CPF | 200 |
| `rate_limit_ip` | Bloqueio por rate limit no IP | 200 |
| `incomplete_registration` | Cadastro não finalizado | 200 |
| `internal_error` | Erro interno do servidor | 200 |

---

## 📱 Notificações WhatsApp

| Evento | Template | Quando |
|--------|----------|--------|
| 3+ tentativas falhas | `alerta_seguranca_tentativa_falha` | A partir da 3ª tentativa |
| Bloqueio por tentativas | `alerta_seguranca_bloqueio_conta` | 5ª tentativa (bloqueio) |
| Bloqueio por rate limit | `alerta_seguranca_bloqueio_conta` | Rate limit CPF excedido |

---

## 📐 Estrutura de Campos

### **Todos os Retornos**
```typescript
{
  sucesso: boolean,        // true/false
  codigo: string,          // Código específico do resultado
  mensagem: string         // Mensagem descritiva
}
```

### **Apenas Sucesso**
```typescript
{
  data: {
    auth_token: string,    // JWT temporário (5 minutos)
    expires_at: string     // ISO 8601 timestamp
  }
}
```

### **Apenas Bloqueios**
```typescript
{
  bloqueio: {
    ativo: true,                    // Sempre true quando bloqueado
    motivo: string,                 // Tipo de bloqueio
    bloqueado_ate: string | null,   // ISO timestamp ou null (rate limits)
    retry_after_seconds: number     // Segundos até desbloquear
  }
}
```

### **Apenas Credenciais Inválidas**
```typescript
{
  tentativas: {
    restantes: number,      // Tentativas restantes antes do bloqueio
    limite: number,         // Limite de tentativas (5)
    janela_minutos: number  // Janela de tempo (15 minutos)
  }
}
```

---

## 🔐 Regras de Bloqueio

| Limite | Janela | Bloqueio | Motivo |
|--------|--------|----------|--------|
| 5 tentativas | 15 minutos | 15 minutos | `limite_15min_atingido` |
| 10 tentativas | 1 hora | 1 hora | `limite_1h_atingido` |
| 15 tentativas | 24 horas | 24 horas | `limite_24h_atingido` |
| Rate limit | Por CPF | 1 hora | `rate_limit_cpf` |
| Rate limit | Por IP | 1 hora | `rate_limit_ip` |

---

## 💡 Notas de Implementação

1. **Todas as respostas retornam HTTP 200** (mesmo erros)
2. **Campo `bloqueado_ate`:**
   - Com data: bloqueios por tentativas
   - `null`: rate limits (usam apenas `retry_after_seconds`)
3. **Mensagens genéricas:** CPF inválido retorna mesma mensagem que senha incorreta (segurança)
4. **WhatsApp fail-safe:** Erro no envio não bloqueia o fluxo principal
5. **Contadores Redis:** Limpos automaticamente ao login bem-sucedido

---

## 🧪 Exemplo de Teste (curl)

```bash
# Configuração
export API_URL="https://apidj.wallclub.com.br"
export CPF="12345678901"
export SENHA="senha123"
export CANAL_ID="1"

# Teste 1-5: Tentativas falhas até bloqueio
for i in {1..5}; do
  echo "=== Tentativa $i ==="
  curl -X POST "${API_URL}/api/v1/cliente/login/" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <oauth_token>" \
    -d '{
      "cpf": "'"${CPF}"'",
      "senha": "senhaerrada",
      "canal_id": '"${CANAL_ID}"'
    }' | jq .
  sleep 2
done

# Limpar bloqueio (Redis)
docker exec wallclub-redis redis-cli DEL "login_blocked:${CPF}"
docker exec wallclub-redis redis-cli DEL "login_attempts_15min:${CPF}"
docker exec wallclub-redis redis-cli DEL "login_attempts_1h:${CPF}"
docker exec wallclub-redis redis-cli DEL "login_attempts_24h:${CPF}"
```

---

## 📊 Resumo de Alterações (28/10/2025)

### Padronização Implementada:
1. ✅ Todos os erros têm código específico
2. ✅ Campo `bloqueio` consistente em todos os bloqueios
3. ✅ Campo `bloqueado_ate` sempre presente (null para rate limits)
4. ✅ Códigos específicos: `rate_limit_cpf` e `rate_limit_ip`
5. ✅ Estrutura `data` para sucesso
6. ✅ Estrutura `tentativas` para credenciais inválidas

### Notificações WhatsApp:
1. ✅ `alerta_seguranca_tentativa_falha` - 3+ tentativas
2. ✅ `alerta_seguranca_bloqueio_conta` - Bloqueio por tentativas ou rate limit

### Arquivos Modificados:
- `apps/cliente/services.py` - Método `ClienteAuthService.login()`
