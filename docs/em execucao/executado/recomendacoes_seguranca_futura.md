# RECOMENDAÇÕES DE SEGURANÇA - IMPLEMENTAÇÃO FUTURA

**Criado em:** 04/10/2025  
**Status:** Pendente de implementação

---

## 1. RATE LIMITING - VALIDAÇÃO DE SENHA

### Problema Identificado
Endpoint `validar_senha_e_saldo` permite tentativas ilimitadas de validação de senha por qualquer POS com token OAuth válido.

### Recomendações

#### a) Rate Limiting por CPF
```python
# Máximo 3 tentativas por CPF a cada 5 minutos
# Bloquear CPF temporariamente após 5 tentativas consecutivas falhas
# Implementar usando Django Cache (Redis)
```

#### b) Rate Limiting por Terminal
```python
# Máximo 10 validações por minuto por terminal
# Alertar admin se terminal exceder limite
```

#### c) Rate Limiting por IP
```python
# Máximo 20 validações por minuto por IP
# Bloquear IP após padrão suspeito
```

### Implementação Sugerida
- **Tecnologia:** Django Cache com Redis (já disponível no projeto)
- **Persistência:** Tabela separada para auditoria
- **Expiração:** Automática via TTL do cache

---

## 2. AUDITORIA DE TENTATIVAS

### Tabela de Auditoria
```sql
CREATE TABLE auditoria_validacao_senha (
    id SERIAL PRIMARY KEY,
    cpf VARCHAR(11),
    terminal VARCHAR(50),
    ip_address VARCHAR(45),
    canal_id INT,
    sucesso BOOLEAN,
    mensagem_erro VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_cpf_created (cpf, created_at),
    INDEX idx_terminal_created (terminal, created_at)
);
```

### Logs Necessários
- Todas tentativas de validação (sucesso/falha)
- CPF (parcialmente mascarado nos logs: XXX.XXX.XXX-07)
- Terminal, IP, canal, timestamp
- Resultado da validação

---

## 3. ALERTAS E NOTIFICAÇÕES

### Alertas para Cliente
- Push notification após 3 tentativas de senha incorreta
- Mensagem: "Detectamos tentativas de acesso à sua conta"

### Alertas para Admin
- Email/SMS após padrão suspeito:
  - Mais de 10 CPFs diferentes em 1 minuto (mesmo terminal)
  - Mais de 20 tentativas falhas em 5 minutos (mesmo IP)
  - Terminal novo fazendo muitas validações

---

## 4. SEGURANÇA ADICIONAL

### Opções de Implementação Futura

#### a) Token Temporário (OTP)
- Cliente gera token de 6 dígitos no app
- Válido por 60 segundos
- POS valida: CPF + Senha + Token

#### b) Últimos 4 Dígitos do Cartão
- Adicionar validação extra: últimos 4 dígitos
- CPF + Senha + Cartão (XXXX)

#### c) Biometria no POS
- Se POS suportar, validar biometria
- Reduz dependência de senha

#### d) IP Whitelist por Terminal
- Terminal só pode fazer chamadas de IPs conhecidos
- Detectar mudanças suspeitas de localização

---

## 5. MONITORAMENTO

### Métricas a Acompanhar
- Taxa de sucesso/falha de validações
- Tentativas por CPF/Terminal/IP
- Tempo médio de resposta
- Picos anormais de requisições

### Dashboards
- Grafana: visualização em tempo real
- Alertas automáticos para anomalias

---

## 6. PROTEÇÃO CONTRA TOKEN COMPROMETIDO

### Rotação de Tokens OAuth
- Renovar tokens POSP2 periodicamente (ex: 7 dias)
- Invalidar tokens antigos
- Notificar terminais para renovar

### Assinatura de Requisições
- HMAC-SHA256 com secret compartilhado
- Prevenir replay attacks
- Timestamp em cada requisição (max 30s de diferença)

---

## 7. PRIORIZAÇÃO

### Alta Prioridade (Implementar Primeiro)
1. ✅ Rate limiting por CPF (cache)
2. ✅ Auditoria de tentativas (tabela)
3. ✅ Alerta para cliente após tentativas falhas

### Média Prioridade
4. Rate limiting por terminal/IP
5. Dashboard de monitoramento
6. Alertas para admin

### Baixa Prioridade (Long Term)
7. Token temporário (OTP)
8. Últimos 4 dígitos do cartão
9. Rotação de tokens OAuth
10. Assinatura de requisições

---

## 8. REFATORAÇÃO E MODULARIZAÇÃO (IMPLEMENTADO)

### ✅ Concluído em 10/10/2025

**Objetivo:** Separar responsabilidades e melhorar manutenibilidade do código POSP2

#### Estrutura Anterior
```
posp2/services.py (2440 linhas)
├── POSP2Service
├── SaldoService
├── TRDataService
└── TransactionSyncService
```

#### Estrutura Após Refatoração
```
posp2/
├── services.py (1106 linhas) - POSP2Service
├── services_saldo.py - SaldoService
├── services_transacao.py - TRDataService
└── services_sync.py - TransactionSyncService
```

#### Benefícios
- ✅ Redução de 46% no tamanho do arquivo principal
- ✅ Separação clara de responsabilidades
- ✅ Código mais testável e modular
- ✅ Zero duplicação de código
- ✅ Facilita manutenção e evolução

---

## 9. GERENCIAMENTO DE CARTÕES TOKENIZADOS

### Gap Identificado (30/10/2025)
**Problema:** Nenhuma interface permite exclusão/invalidação manual de cartões tokenizados.

#### Situação Atual
- Código existe: `CartaoTokenizadoService.invalidar_cartao()`
- Código existe: `CartaoTokenizadoService.excluir_cartao()`
- **MAS:** Nenhuma tela/endpoint permite acesso a essas funções

#### Implementações Necessárias

**a) Portal de Vendas - Gerenciar Cartões do Cliente**
```
Tela: /portal_vendas/cliente/{id}/cartoes/
- Listar cartões ativos do cliente
- Botão "Invalidar" (marca valido=False)
- Botão "Excluir" (chama Pinbank + marca inválido)
- Log de ação (auditoria)
```

**b) Invalidação Automática por Falhas**
```python
# Após 5 tentativas consecutivas falhas:
if tentativas_falhas >= 5:
    cartao.valido = False
    cartao.motivo_invalidacao = 'Múltiplas falhas'
    cartao.save()
    
    # Marcar recorrências como HOLD
    RecorrenciaAgendada.objects.filter(
        cartao_tokenizado=cartao,
        status='ativo'
    ).update(status='hold')
```

**c) Notificação ao Vendedor**
- Email/notificação quando cartão é invalidado automaticamente
- Lista recorrências afetadas
- Sugestão de ação (solicitar novo cartão)

#### Campos Adicionais Recomendados
```sql
ALTER TABLE checkout_cartao_tokenizado 
ADD COLUMN tentativas_falhas_consecutivas INT DEFAULT 0,
ADD COLUMN ultima_falha_em DATETIME NULL,
ADD COLUMN motivo_invalidacao VARCHAR(255) NULL,
ADD COLUMN invalidado_por INT NULL COMMENT 'ID do usuário que invalidou',
ADD COLUMN invalidado_em DATETIME NULL;
```

### Prioridade
- **Alta:** Invalidação automática após 5 falhas (segurança)
- **Média:** Interface de gerenciamento (usabilidade)
- **Média:** Notificações automáticas (operação)

---

## NOTAS

- Implementar incrementalmente para não impactar operação
- Testar em staging antes de produção
- Documentar cada implementação
- Revisar logs semanalmente nos primeiros meses
