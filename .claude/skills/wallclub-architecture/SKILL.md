---
name: wallclub-architecture
description: Arquitetura completa do sistema WallClub - containers, integrações, fluxos de dados, diagramas. Use quando precisar entender a estrutura do sistema, dependências entre módulos, ou planejar mudanças arquiteturais.
---

# WallClub - Arquitetura Completa

Este documento contém a arquitetura detalhada do sistema WallClub. Consulte quando precisar entender:
- Estrutura de containers e serviços
- Integrações entre módulos
- Fluxos de dados e processamento
- Decisões arquiteturais

**Fonte:** `/docs/ARQUITETURA.md` (3938 linhas)

Para consultar o conteúdo completo, leia o arquivo original:
```bash
cat /Users/jeanlessa/wall_projects/WallClub_backend/docs/ARQUITETURA.md
```

## Principais Seções

### 1. Containers e Serviços
- 4 containers principais: APIs, Portais, POS, RiskEngine
- 9 containers totais com Celery workers
- Stack: Django 5.1 + DRF + PostgreSQL + Redis + Celery

### 2. Integrações Externas
- **Pinbank:** Extrato POS, Base Gestão, Credenciadora
- **Own Financial:** Transações, Liquidações (Webhooks + Double-check)
- **MaxMind:** Antifraude e geolocalização
- **Firebase/APN:** Push notifications

### 3. APIs Internas (32 endpoints)
- Cliente APIs (cadastro, autenticação, dispositivos)
- Conta Digital APIs (saldo, movimentações, PIX)
- Checkout APIs (link pagamento, recorrências)
- Ofertas APIs (CRUD, disparo push)
- Parâmetros APIs (configurações financeiras)

### 4. Fluxos de Processamento
- Cargas automáticas (Pinbank + Own)
- Cálculo de cashback (regras configuráveis)
- Processamento de transações (POS + Checkout)
- Análise de risco (RiskEngine)

### 5. Estrutura de Diretórios
```
services/
├── core/              # Shared utilities
├── django/
│   ├── apps/          # Módulos de negócio
│   ├── pinbank/       # Integração Pinbank
│   ├── adquirente_own/  # Integração Own
│   ├── parametros_wallclub/  # Cálculos financeiros
│   ├── portais/       # Portais Web
│   └── gestao_financeira/  # Lançamentos manuais
└── riskengine/        # Motor antifraude
```

## Quando Usar Esta Skill

✅ **Use quando:**
- Planejar mudanças que impactem múltiplos módulos
- Entender dependências entre serviços
- Verificar integrações com sistemas externos
- Analisar fluxos de dados complexos
- Tomar decisões arquiteturais

❌ **Não use para:**
- Padrões de código (use @wallclub-standards)
- Implementação de features simples
- Debugging de código específico
