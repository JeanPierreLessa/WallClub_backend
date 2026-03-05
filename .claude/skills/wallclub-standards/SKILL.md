---
name: wallclub-standards
description: Padrões técnicos detalhados do WallClub - regras de código, banco de dados, APIs, segurança, timezone, valores monetários. Use quando precisar consultar padrões específicos de implementação ou validar conformidade técnica.
---

# WallClub - Padrões Técnicos Detalhados

Este documento contém os padrões técnicos completos do sistema WallClub. Consulte quando precisar:
- Regras específicas de implementação
- Padrões de código e nomenclatura
- Configurações de banco de dados
- Regras de timezone e valores monetários
- Padrões de APIs e segurança

**Fonte:** `/docs/DIRETRIZES.md` (1790 linhas)

Para consultar o conteúdo completo, leia o arquivo original:
```bash
cat /Users/jeanlessa/wall_projects/WallClub_backend/docs/DIRETRIZES.md
```

## Principais Seções

### 1. Regras Fundamentais
- Containers desacoplados (4 independentes)
- Comunicação via APIs REST internas
- OAuth 2.0 inter-containers
- Sem imports diretos entre containers

### 2. Banco de Dados
- PostgreSQL 16 (migrado de MySQL)
- Timezone: UTC (NEVER use timezone-naive datetimes)
- Transações: `@transaction.atomic` obrigatório
- Migrations: sempre revisar antes de aplicar

### 3. Timezone e Datas
```python
# ✅ CORRETO
from django.utils import timezone
now = timezone.now()  # timezone-aware

# ❌ ERRADO
from datetime import datetime
now = datetime.now()  # timezone-naive
```

### 4. Valores Monetários
```python
# ✅ CORRETO
from decimal import Decimal
valor = Decimal('10.50')

# ❌ ERRADO
valor = 10.50  # float tem imprecisão
```

### 5. APIs REST
- DRF 3.16.1
- Versionamento: `/api/v1/`
- Paginação: 50 itens padrão
- Serializers: sempre validar dados
- Responses: sempre incluir status HTTP correto

### 6. Autenticação e Segurança
- JWT customizado (18 cenários testados)
- OAuth 2.0 para terminais POS
- Decorators obrigatórios:
  - `@require_oauth_apps` (mobile)
  - `@require_oauth_web` (portal lojista)
  - `@require_oauth_admin` (portal admin)
  - `@require_api_key` (integrações)

### 7. Sistema Antifraude (RiskEngine)
- Score 0-100
- 5 regras configuráveis
- MaxMind minFraud
- 3D Secure 2.0
- 6 detectores automáticos

### 8. Notificações
- Firebase (Android)
- APN (iOS)
- Sistema de ofertas com push

### 9. Arquitetura Docker
- 4 containers principais
- 9 containers totais (com Celery)
- Nginx como reverse proxy
- Redis para cache e OAuth

### 10. Boas Práticas de Código
- PEP 8 compliance
- Type hints obrigatórios
- Docstrings em funções públicas
- Testes unitários para lógica crítica
- Logs estruturados

## Regras Críticas Específicas

### Login Biométrico
```python
# Endpoint: POST /api/v1/cliente/login_biometrico/
# Autenticação: CPF + device_fingerprint + canal_id
# Validação: DeviceManagementService.validar_dispositivo()
# Campo: Cliente.is_active (não 'ativo')
```

### Own Financial
- API `/buscaTransacoesGerais` NÃO retorna e-commerce
- Webhook obrigatório para transações e-commerce
- Campo `gateway_ativo` na tabela `loja` ('PINBANK' ou 'OWN')
- Payload estruturado com dados completos do cliente

### GatewayRouter
- Seleção dinâmica Pinbank/Own por loja
- Suporte: tokenização, pagamento, estorno, exclusão
- CheckoutService usa GatewayRouter (não hardcoded)

### Calculadoras Base
- Parâmetros obrigatórios (info_loja, info_canal, dados_linha)
- Sem busca interna de parâmetros
- Abstração completa (Base, Gestão, Credenciadora, Checkout)

## Quando Usar Esta Skill

✅ **Use quando:**
- Implementar novas features
- Validar conformidade com padrões
- Resolver dúvidas sobre regras específicas
- Revisar código antes de commit
- Configurar integrações externas

❌ **Não use para:**
- Entender arquitetura geral (use @wallclub-architecture)
- Debugging de problemas específicos
- Consultas rápidas (use CLAUDE.md)
