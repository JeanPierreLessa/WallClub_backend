# ROTEIRO DE TESTES - CONTA DIGITAL

**Data:** 05/10/2025  
**Objetivo:** Validar funcionalidades completas da Conta Digital incluindo saldo, movimentações, autorização de uso e cashback.

---

## 📊 STATUS DOS TESTES

### 🔧 ENDPOINTS POS (OAuth)

| # | Funcionalidade | Status | Observações |
|---|---|---|---|
| 3 | Validar Senha + Consultar Saldo | ✅ TESTADO | Funcionando conforme esperado |
| 4 | Solicitar Autorização (Push) | 🔄 EM TESTE | Testando integração Android |
| 5 | Verificar Status (Polling) | ✅ TESTADO | |
| 6 | Debitar Saldo | ❌ NÃO TESTADO | |
| 7 | Finalizar Transação | ❌ NÃO TESTADO | |
| 8 | Estornar Transação | ❌ NÃO TESTADO | |

### 📱 ENDPOINTS APPS (JWT)

| # | Funcionalidade | Status | Observações |
|---|---|---|---|
| 9 | Aprovar Uso de Saldo | ✅ TESTADO | |
| 10 | Negar Uso de Saldo | ❌ NÃO TESTADO | |
| 11 | Listar Notificações | ✅ TESTADO | |

### 🏦 CONTA DIGITAL (SQL + API)

| # | Funcionalidade | Status | Observações |
|---|---|---|---|
| 1 | Consultar Saldo (API) | ✅ TESTADO | |
| 2 | Consultar Saldo (SQL) | ✅ TESTADO | |
| 3 | Consultar Extrato (API) | ✅ TESTADO | |
| 4 | Listar Movimentações (SQL) | ✅ TESTADO | |
| 5 | Verificar Tipos de Movimentação | ❌ NÃO TESTADO | |
| 6 | Verificar Autorização Criada | ❌ NÃO TESTADO | |
| 7 | Autorização por Status | ❌ NÃO TESTADO | |
| 8 | Verificar Autorização Específica | ❌ NÃO TESTADO | |
| 9 | Saldo Bloqueado Atual | ❌ NÃO TESTADO | |
| 10 | Histórico de Bloqueios | ❌ NÃO TESTADO | |
| 11 | Histórico de Estornos | ❌ NÃO TESTADO | |
| 12 | Total de Cashback Recebido | ❌ NÃO TESTADO | |
| 13 | Histórico de Cashback | ❌ NÃO TESTADO | |
| 14 | Cashback por Período | ❌ NÃO TESTADO | |
| 15 | Verificar Conta Digital Ativa | ❌ NÃO TESTADO | |
| 16 | Conferir Saldo Calculado vs Armazenado | ❌ NÃO TESTADO | |
| 17 | Movimentações sem Saldo Após | ❌ NÃO TESTADO | |
| 18 | Notificações de Autorização | ❌ NÃO TESTADO | |
| 19 | Notificações de Transação | ❌ NÃO TESTADO | |
| 20 | Fluxo: Criar Conta Digital | ❌ NÃO TESTADO | |
| 21 | Fluxo: Creditar Cashback Manual | ❌ NÃO TESTADO | |
| 22 | Fluxo: Bloquear → Debitar → Finalizar | ❌ NÃO TESTADO | |
| 23 | Fluxo: Bloquear → Negar → Estornar | ❌ NÃO TESTADO | |
| 24 | Fluxo: Bloquear → Expirar (Timeout) | ❌ NÃO TESTADO | |
| 25 | Senha Inválida | ❌ NÃO TESTADO | |
| 26 | Saldo Insuficiente | ❌ NÃO TESTADO | |
| 27 | Bloquear > Saldo Disponível | ❌ NÃO TESTADO | |
| 28 | Aprovar Autorização Expirada | ❌ NÃO TESTADO | |
| 29 | Estornar Transação Finalizada | ❌ NÃO TESTADO | |
| 30 | Cliente sem Conta Digital | ❌ NÃO TESTADO | |

**Legenda:**
- ✅ TESTADO - Funcionando conforme esperado
- ⚠️ TESTADO COM RESSALVAS - Funciona mas precisa ajustes
- ❌ NÃO TESTADO - Ainda não validado
- 🚫 FALHOU - Teste executado mas falhou

---

## 🔑 PRÉ-REQUISITOS

**1. Token OAuth POSP2:**
```bash
curl -X POST https://apidj.wallclub.com.br/api/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "posp2",
    "client_secret": "posp2_N93cAK62qbBq332ElQ4ZZjn26dNhF13Dmn_Lb2ATSftbYFH9bAhsqwPj4gWBw06o",
    "grant_type": "client_credentials"
  }'
# Salvar: access_token
```

**2. Token OAuth Apps:**
```bash
curl -X POST https://apidj.wallclub.com.br/api/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "wallclub_mobile",
    "client_secret": "wallclub_oauth_secret_v1_secure_key_wallclub",
    "grant_type": "client_credentials"
  }'
# Salvar: access_token_apps
```

**3. Login Cliente (JWT):**
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/login/ \
  -H "Authorization: Bearer  {access_token_apps}" \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "17653377807",
    "senha": "4640",
    "canal_id": 1
  }'
# Salvar: jwt_token
```

---

## 🔧 CURLS DE TESTE - ENDPOINTS POS (OAuth)

### 3. Validar Senha + Consultar Saldo
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/posp2/validar_senha_e_saldo/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wc_at_lNC1Oe7xZoK1MuNFARMmvA6vYxBvodZhP0Bg7FdOs9w" \
  -d '{
    "cpf": "17653377807",
    "senha": "2985",
    "terminal": "PB59237K70569"
  }'
# Resposta esperada: 
# {
#   "valido": true, 
#   "cliente_id": 1,
#   "saldo_disponivel": 100.50,
#   "cashback_disponivel": 25.00,
#   "saldo_total": 125.50,
#   "auth_token": "a1b2c3d4e5f6..."  ← TOKEN VÁLIDO POR 15 MINUTOS
# }
```

### 4. Solicitar Autorização (Push) 🔒
**IMPORTANTE:** Requer `auth_token` obtido no passo 3 (válido por 15 minutos)

```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/posp2/solicitar_autorizacao_saldo/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wc_at_Fa1ZqnhcyPxavlN-b4bTYIGHWIKfrrhfJz8Ypa21qNA" \
  -d '{
    "auth_token": "bf38ebb6a4c646d9a23ac13004dfa5b2",
    "valor_usar": 1.00,
    "terminal": "PB59237K70569"
  }'
# O auth_token:
# - Valida que a senha foi verificada recentemente (15 minutos)
# - Garante que o terminal é o mesmo da validação
# - Verifica que o valor não excede o saldo disponível
# - Expira automaticamente após 15 minutos
# - Pode ser reutilizado para múltiplas transações durante sua validade
# Resposta esperada: {"sucesso": true, "autorizacao_id": "UUID", "status": "PENDENTE", "mensagem": "Autorização criada - aguardando aprovação do cliente", "expira_em": 30}
```

### 5. Verificar Status (Polling)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/posp2/verificar_autorizacao/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer wc_at_Is7AWOINXPxEMZD94M-xqv6Mr9ltuS-3fwEHNlByyHU" \
  -d '{
    "autorizacao_id": "9a3db4e2-a88e-4d81-b70f-b316fb2578ad"
  }'
# Resposta esperada:
# {
#   "sucesso": true,
#   "status": "APROVADO",  // ou PENDENTE, NEGADO, EXPIRADO
#   "valor_bloqueado": 1.00,
#   "pode_processar": true  // true se status=APROVADO e não expirado
# }
# Status possíveis: PENDENTE, APROVADO, NEGADO, EXPIRADO, CONCLUIDA, ESTORNADA
```

### 6. Debitar Saldo (Backend)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/posp2/debitar_saldo_transacao/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -d '{
    "autorizacao_id": "cd818e98-93f8-4793-95c0-971e1a9b3f7b",
    "nsu_transacao": "123456789"
  }'
# Resposta esperada:
# {"sucesso": true, "mensagem": "Saldo debitado com sucesso", "valor_debitado": 1.00}
```

### 7. Finalizar Transação
```bash
# Endpoint para finalizar transação
# (Implementar conforme necessário)
```

### 8. Estornar Transação
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/estornar/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "movimentacao_id": 123,
    "motivo": "Estorno via POS"
  }'
```

---

## 📱 CURLS DE TESTE - ENDPOINTS APPS (JWT)

### 9. Aprovar Uso de Saldo
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/aprovar_uso_saldo/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRlX2lkIjoxLCJjcGYiOiIxNzY1MzM3NzgwNyIsIm5vbWUiOiJKRUFOIFBJRVJSRSBMRVNTQSBFIFNBTlRPUyBGRVJSRUlSQSIsImNhbmFsX2lkIjoxLCJpc19hY3RpdmUiOnRydWUsImlhdCI6MTc1OTcwMTQ0NSwiZXhwIjoxNzU5Nzg3ODQ1LCJqdGkiOiIzOTg5MGJjMS0xMzMzLTRiYzQtODQxMS0xZmY2ZWE5ZjE4ODQiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwib2F1dGhfdmFsaWRhdGVkIjp0cnVlfQ.HM5DuL4tBN0Mu72IVifhpskS7y2GkFsAfF1JycvDZJA" \
  -H "Content-Type: application/json" \
  -d '{
    "autorizacao_id": "d8a44ddf-7c66-4732-a1e3-e37eafb20e2f"
  }'
# Resposta esperada:
# {
#   "success": true,
#   "data": {
#     "mensagem": "Autorização aprovada com sucesso",
#     "valor_bloqueado": 50.00,
#     "expira_em": 120
#   }
# }
```

### 10. Negar Uso de Saldo
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/negar_uso_saldo/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRlX2lkIjoxLCJjcGYiOiIxNzY1MzM3NzgwNyIsIm5vbWUiOiJKRUFOIFBJRVJSRSBMRVNTQSBFIFNBTlRPUyBGRVJSRUlSQSIsImNhbmFsX2lkIjoxLCJpc19hY3RpdmUiOnRydWUsImlhdCI6MTc1OTY5NjkwOSwiZXhwIjoxNzU5NzgzMzA5LCJqdGkiOiI2NTFiMjZhOS1lMmZhLTQ1MzQtYjlkZC1iZTJiZTlkMmFkZTciLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwib2F1dGhfdmFsaWRhdGVkIjp0cnVlfQ.terHudx4FN7TpVJNHRXJh8gr6Fhz1RT-bnab_xudMM0" \
  -H "Content-Type: application/json" \
  -d '{
    "autorizacao_id": "6c67727e-aac1-43fc-9a52-ac835b883594"
  }'
# Resposta esperada:
# {
#   "success": true,
#   "data": {
#     "mensagem": "Autorização negada"
#   }
# }
```

### 11. Listar Notificações
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/cliente/notificacoes/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{}'
```

---

## 🏦 CURLS DE TESTE - CONTA DIGITAL (API)

### 1. Consultar Saldo (API)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/saldo/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjbGllbnRlX2lkIjoxLCJjcGYiOiIxNzY1MzM3NzgwNyIsIm5vbWUiOiJKRUFOIFBJRVJSRSBMRVNTQSBFIFNBTlRPUyBGRVJSRUlSQSIsImNhbmFsX2lkIjoxLCJpc19hY3RpdmUiOnRydWUsImlhdCI6MTc1OTcwOTcwNywiZXhwIjoxNzU5Nzk2MTA3LCJqdGkiOiIwNDJhMGFiZC0zOGE1LTRlYzgtYTJkNi03NjM3YzFmNzM3MGIiLCJ0b2tlbl90eXBlIjoiYWNjZXNzIiwib2F1dGhfdmFsaWRhdGVkIjp0cnVlfQ.JEu60okZX_RXGtbis0QB8983OTjC_GEp1m6eGXJPwJo" \
  -H "Content-Type: application/json" \
  -d '{}'
# Esperado: {"saldo_disponivel": XXX.XX, "saldo_bloqueado": YYY.YY}
```

### 3. Consultar Extrato (API)
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/extrato/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2025-09-01",
    "data_fim": "2025-10-05",
    "limite": 50
  }'
# Verificar: Lista de movimentações com tipo, valor, data, descrição
```

### 20. Fluxo: Criar Conta Digital
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/criar/ \
  -H "Authorization: Bearer {access_token_apps}" \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "17653377807",
    "canal_id": 1
  }'
# Verificar no banco: conta criada com saldo_atual = 0
```

### 21. Fluxo: Creditar Cashback Manual
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/creditar/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "valor": 100.00,
    "descricao": "Cashback teste manual",
    "tipo_operacao": "CASHBACK",
    "referencia_externa": "CASH123",
    "sistema_origem": "TESTE"
  }'
```

### Bloquear Saldo
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/bloquear-saldo/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "valor": 25.00,
    "motivo": "Teste de bloqueio"
  }'
```

### Desbloquear Saldo
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/desbloquear-saldo/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{
    "valor": 25.00,
    "motivo": "Teste de desbloqueio"
  }'
```

---

## ✅ CHECKLIST DE TESTES

### 📊 CONSULTAS DE SALDO

- [ ] **1. Consultar Saldo via API**
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/saldo/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{}'
# Esperado: {"saldo_disponivel": XXX.XX, "saldo_bloqueado": YYY.YY}
```

- [ ] **2. Consultar Saldo via SQL**
```sql
SELECT 
    cliente_id,
    SUM(CASE WHEN tipo_movimentacao IN ('CREDITO', 'ESTORNO') THEN valor ELSE -valor END) as saldo_total
FROM conta_digital_movimentacao 
WHERE cliente_id = 1
GROUP BY cliente_id;
```

### 📝 MOVIMENTAÇÕES

- [ ] **3. Consultar Extrato via API**
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/extrato/ \
  -H "Authorization: Bearer {jwt_token}" \
  -H "Content-Type: application/json" \
  -d '{"limite":20}'
# Verificar: Lista de movimentações com tipo, valor, data, descrição
```

- [ ] **4. Listar Movimentações via SQL**
```sql
SELECT 
    id,
    cliente_id,
    tipo_movimentacao,
    valor,
    descricao,
    data_hora,
    saldo_apos_movimentacao
FROM conta_digital_movimentacao 
WHERE cliente_id = 1
ORDER BY data_hora DESC 
LIMIT 20;
```

- [ ] **5. Verificar Tipos de Movimentação**
```sql
SELECT 
    tipo_movimentacao,
    COUNT(*) as quantidade,
    SUM(valor) as total
FROM conta_digital_movimentacao 
WHERE cliente_id = 1
GROUP BY tipo_movimentacao;
# Esperado: CREDITO, DEBITO, BLOQUEIO, ESTORNO, CASHBACK
```

### 🔒 AUTORIZAÇÕES DE USO DE SALDO

- [ ] **6. Verificar Autorização Criada**
```sql
SELECT * FROM conta_digital_autorizacao_uso_saldo 
WHERE cliente_id = 1
ORDER BY criado_em DESC 
LIMIT 5;
# Verificar: id, status, valor, terminal, criado_em, expira_em
```

- [ ] **7. Autorização por Status**
```sql
SELECT 
    status,
    COUNT(*) as quantidade,
    SUM(valor) as total_valor
FROM conta_digital_autorizacao_uso_saldo 
WHERE cliente_id = 1
GROUP BY status;
# Status possíveis: PENDENTE, APROVADO, NEGADO, EXPIRADO
```

- [ ] **8. Verificar Autorização Específica**
```sql
SELECT 
    id,
    cliente_id,
    valor,
    status,
    terminal,
    nsu_transacao,
    criado_em,
    aprovado_em,
    expira_em
FROM conta_digital_autorizacao_uso_saldo 
WHERE id = '{autorizacao_id}';
```

### 💰 BLOQUEIOS E ESTORNOS

- [ ] **9. Saldo Bloqueado Atual**
```sql
SELECT 
    cliente_id,
    SUM(CASE WHEN tipo_movimentacao = 'BLOQUEIO' THEN ABS(valor) ELSE 0 END) as saldo_bloqueado
FROM conta_digital_movimentacao 
WHERE cliente_id = 1
GROUP BY cliente_id;
```

- [ ] **10. Histórico de Bloqueios**
```sql
SELECT * FROM conta_digital_movimentacao 
WHERE cliente_id = 1 
AND tipo_movimentacao = 'BLOQUEIO'
ORDER BY data_hora DESC 
LIMIT 10;
# Verificar: descricao contém autorizacao_id
```

- [ ] **11. Histórico de Estornos**
```sql
SELECT * FROM conta_digital_movimentacao 
WHERE cliente_id = 1 
AND tipo_movimentacao = 'ESTORNO'
ORDER BY data_hora DESC 
LIMIT 10;
```

### 💸 CASHBACK

- [ ] **12. Total de Cashback Recebido**
```sql
SELECT 
    cliente_id,
    COUNT(*) as quantidade_cashbacks,
    SUM(valor) as total_cashback
FROM conta_digital_movimentacao 
WHERE cliente_id = 1
AND tipo_movimentacao = 'CASHBACK'
GROUP BY cliente_id;
```

- [ ] **13. Histórico de Cashback**
```sql
SELECT 
    id,
    valor,
    descricao,
    data_hora,
    saldo_apos_movimentacao
FROM conta_digital_movimentacao 
WHERE cliente_id = 1 
AND tipo_movimentacao = 'CASHBACK'
ORDER BY data_hora DESC 
LIMIT 10;
# Verificar: descricao contém % de cashback e NSU
```

- [ ] **14. Cashback por Período**
```sql
SELECT 
    DATE(data_hora) as data,
    COUNT(*) as quantidade,
    SUM(valor) as total_cashback
FROM conta_digital_movimentacao 
WHERE cliente_id = 1 
AND tipo_movimentacao = 'CASHBACK'
AND data_hora >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY DATE(data_hora)
ORDER BY data DESC;
```

### 🏦 VALIDAÇÕES DE INTEGRIDADE

- [ ] **15. Verificar Conta Digital Ativa**
```sql
SELECT 
    id,
    cliente_id,
    saldo_atual,
    ativa,
    criada_em,
    atualizada_em
FROM conta_digital 
WHERE cliente_id = 1;
# Verificar: ativa = true
```

- [ ] **16. Conferir Saldo Calculado vs Armazenado**
```sql
SELECT 
    cd.cliente_id,
    cd.saldo_atual as saldo_armazenado,
    COALESCE(SUM(
        CASE 
            WHEN m.tipo_movimentacao IN ('CREDITO', 'ESTORNO', 'CASHBACK') THEN m.valor
            ELSE -m.valor 
        END
    ), 0) as saldo_calculado
FROM conta_digital cd
LEFT JOIN conta_digital_movimentacao m ON cd.cliente_id = m.cliente_id
WHERE cd.cliente_id = 1
GROUP BY cd.cliente_id, cd.saldo_atual;
# Verificar: saldo_armazenado = saldo_calculado
```

- [ ] **17. Movimentações sem Saldo Após**
```sql
SELECT * FROM conta_digital_movimentacao 
WHERE cliente_id = 1 
AND saldo_apos_movimentacao IS NULL
ORDER BY data_hora DESC;
# Esperado: Nenhum registro (todos devem ter saldo_apos_movimentacao)
```

### 📱 NOTIFICAÇÕES DE CONTA DIGITAL

- [ ] **18. Notificações de Autorização**
```sql
SELECT * FROM notificacoes 
WHERE cpf = '17653377807' 
AND tipo = 'autorizacao_saldo'
ORDER BY data_envio DESC 
LIMIT 10;
# Verificar: titulo, mensagem, dados_adicionais (estabelecimento, valor, autorizacao_id)
```

- [ ] **19. Notificações de Transação**
```sql
SELECT * FROM notificacoes 
WHERE cpf = '17653377807' 
AND tipo = 'transacao'
ORDER BY data_envio DESC 
LIMIT 10;
# Verificar: dados_adicionais contém valor_cashback se wall='S'
```

### 🔄 FLUXOS COMPLETOS

- [ ] **20. Fluxo: Criar Conta Digital**
```bash
curl -X POST https://apidj.wallclub.com.br/api/v1/conta_digital/criar/ \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"cpf":"17653377807","canal_id":1}'
# Verificar no banco: conta criada com saldo_atual = 0
```

- [ ] **21. Fluxo: Creditar Cashback Manual**
```sql
INSERT INTO conta_digital_movimentacao 
(cliente_id, tipo_movimentacao, valor, descricao, data_hora, saldo_apos_movimentacao)
VALUES 
(1, 'CASHBACK', 10.00, 'Cashback teste manual', NOW(), 
 (SELECT saldo_atual + 10.00 FROM conta_digital WHERE cliente_id = 1));

UPDATE conta_digital SET saldo_atual = saldo_atual + 10.00 WHERE cliente_id = 1;
# Verificar: Saldo aumentou, movimentação registrada
```

- [ ] **22. Fluxo: Bloquear → Debitar → Finalizar**
```
1. Solicitar autorização (bloqueia saldo) ✅
2. Aprovar autorização ✅
3. Debitar saldo (transforma bloqueio em débito) ✅
4. Finalizar transação (confirma) ✅
5. Verificar: Bloqueio removido, débito aplicado
```

- [ ] **23. Fluxo: Bloquear → Negar → Estornar**
```
1. Solicitar autorização (bloqueia saldo) ✅
2. Negar autorização ✅
3. Verificar: Bloqueio estornado automaticamente
4. Saldo volta ao valor original ✅
```

- [ ] **24. Fluxo: Bloquear → Expirar (Timeout)**
```
1. Solicitar autorização (bloqueia saldo) ✅
2. Esperar 5 minutos (sem aprovar/negar) ✅
3. Verificar: Status = EXPIRADO
4. Bloqueio estornado automaticamente ✅
```

### 🚨 TESTES DE ERRO

- [ ] **25. Criar Conta Duplicada**
- [ ] **26. Debitar com Saldo Insuficiente**
- [ ] **27. Bloquear Valor Maior que Saldo Disponível**
- [ ] **28. Aprovar Autorização Expirada**
- [ ] **29. Estornar Transação Já Finalizada**
- [ ] **30. Cliente sem Conta Digital Ativa**

---

## 📋 QUERIES ÚTEIS PARA DEBUG

**Resetar Saldo de Teste:**
```sql
-- CUIDADO: Apenas em desenvolvimento/homologação
UPDATE conta_digital SET saldo_atual = 1000.00 WHERE cliente_id = 1;
```

**Limpar Autorizações Antigas:**
```sql
DELETE FROM conta_digital_autorizacao_uso_saldo 
WHERE criado_em < DATE_SUB(NOW(), INTERVAL 1 DAY);
```

**Ver Últimas 10 Ações do Cliente:**
```sql
SELECT 
    'movimentacao' as tipo,
    m.tipo_movimentacao as acao,
    m.valor,
    m.descricao,
    m.data_hora
FROM conta_digital_movimentacao m
WHERE m.cliente_id = 1
UNION ALL
SELECT 
    'autorizacao' as tipo,
    a.status as acao,
    a.valor,
    CONCAT('Terminal: ', a.terminal) as descricao,
    a.criado_em as data_hora
FROM conta_digital_autorizacao_uso_saldo a
WHERE a.cliente_id = 1
ORDER BY data_hora DESC
LIMIT 10;
```
