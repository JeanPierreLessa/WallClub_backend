# PENDÊNCIAS DE SEGURANÇA

**Última Atualização:** 16/01/2026

---

## 🚨 CRÍTICO - Webhooks Own Financial

### Problema
Webhooks da Own Financial (`/webhook/*`) não possuem validação de origem, permitindo que qualquer IP envie dados falsos.

### Endpoints Afetados
- `/webhook/transacao/` - Notificações de vendas confirmadas/estornadas
- `/webhook/liquidacao/` - Notificações de pagamentos realizados
- `/webhook/cadastro/` - Notificações de deferimento/indeferimento
- `/webhook/credenciamento/` - Notificações de credenciamento

### Risco
- **Alto:** Dados falsos podem ser inseridos no sistema
- Possível manipulação de saldos e transações
- Sem autenticação ou validação de assinatura

### Solução Recomendada

**Opção 1: IP Whitelist (Preferencial)**
```python
# Validar IP de origem contra lista da Own
ALLOWED_OWN_IPS = [
    '200.xxx.xxx.xxx',  # IP 1 da Own (solicitar)
    '200.xxx.xxx.xxx',  # IP 2 da Own (solicitar)
]

@csrf_exempt
@require_http_methods(["POST"])
def webhook_transacao(request):
    # Validar IP
    client_ip = get_client_ip(request)
    if client_ip not in ALLOWED_OWN_IPS:
        registrar_log('own.webhook', f'IP não autorizado: {client_ip}', nivel='ERROR')
        return JsonResponse({'erro': 'Não autorizado'}, status=403)

    # Processar webhook...
```

**Opção 2: Validação de Assinatura**
```python
# Se Own fornecer assinatura HMAC ou JWT
def validar_assinatura_own(request):
    signature = request.headers.get('X-Own-Signature')
    payload = request.body
    expected = hmac.new(OWN_SECRET_KEY, payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature, expected)
```

### Ação Necessária
1. ✅ Documentado em PENDENCIAS_SEGURANCA.md
2. ⏳ Solicitar à Own Financial:
   - Lista de IPs de origem dos webhooks
   - OU método de assinatura/autenticação de webhooks
3. ⏳ Implementar validação após resposta da Own

### Prioridade
🔴 **ALTA** - Implementar assim que Own fornecer informações

### Esforço Estimado
- **4 horas** (IP whitelist)
- **8 horas** (validação de assinatura, se disponível)

---

## 📋 Histórico de Implementações

### ✅ Concluído - Rate Limiting POS (16/01/2026)

**Implementado:**
- Rate limiting por IP via middleware (todos endpoints `/api/*`)
- Rate limiting adicional por `terminal_id` em endpoints POS críticos
- Auditoria de atividades suspeitas
- Alertas automáticos

**Arquitetura:**
- **Camada 1 (Middleware):** Proteção por IP contra DDoS
- **Camada 2 (Decorator POS):** Proteção por terminal contra abuso de terminal específico

**Justificativa da dupla camada:**
- POS: Múltiplos terminais compartilham mesmo token OAuth
- Terminal comprometido não pode afetar outros terminais da mesma loja
- Outras APIs (Mobile, Checkout) não precisam dessa camada adicional

**Endpoints protegidos:**
- `/api/v1/posp2/trdata/` - 30 req/min por terminal
- `/api/v1/posp2/trdata_own/` - 30 req/min por terminal
- `/api/v1/posp2/solicitar_autorizacao_saldo/` - 30 req/min por terminal
- `/api/v1/posp2/verificar_autorizacao/` - 50 req/min por terminal
- `/api/v1/posp2/valida_cpf/` - 50 req/min por terminal
- `/api/v1/cupons/validar/` - 30 req/min por terminal

---

## 📝 Notas

- Webhooks não utilizam rate limiting tradicional pois são notificações assíncronas da Own
- Validação de origem (IP ou assinatura) é mais apropriada para webhooks
- Rate limiting POS é defesa em profundidade (múltiplas camadas de proteção)
