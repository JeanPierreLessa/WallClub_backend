# Documentação WallClub Backend

Documentação completa e consolidada do ecossistema WallClub.

## 📚 Estrutura da Documentação

```
docs/
├── architecture/              # Arquitetura e Visão Integrada do Sistema
│   ├── README.md             # Índice e navegação (Visão Integrada)
│   ├── 1. ARQUITETURA_GERAL.md
│   ├── 2. DIRETRIZES_UNIFICADAS.md
│   └── 3. INTEGRACOES.md
├── development/               # Diretrizes de Desenvolvimento
│   ├── django-diretrizes.md
│   └── riskengine-diretrizes.md
├── services/                  # Documentação Detalhada por Serviço
│   ├── django-readme.md
│   └── riskengine-readme.md
├── setup/                     # Configuração de Ambiente
│   └── local.md
└── deployment/                # Procedimentos de Deploy
    └── producao.md
```

## 🚀 Começando

### Primeiro Acesso

1. **[Setup Local](setup/local.md)** - Configure seu ambiente de desenvolvimento
2. **[Arquitetura Geral](architecture/1.%20ARQUITETURA_GERAL.md)** - Entenda a arquitetura completa do sistema
3. **[Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md)** - Aprenda os padrões e regras de código

### Desenvolvimento Diário

- **[Integrações](architecture/3.%20INTEGRACOES.md)** - APIs internas e externas (26 endpoints)
- **[Diretrizes Django](development/django-diretrizes.md)** - Padrões específicos do Django
- **[Diretrizes Risk Engine](development/riskengine-diretrizes.md)** - Padrões do motor antifraude

### Operações

- **[Deploy Produção](deployment/producao.md)** - Procedimentos de deploy
- **[README Django](services/django-readme.md)** - Documentação completa (1117 linhas)
- **[README Risk Engine](services/riskengine-readme.md)** - Documentação completa (839 linhas)

## 📖 Guias por Perfil

### 👨‍💻 Novo Desenvolvedor (Onboarding)

**Objetivo:** Entender o sistema em <1 hora

**Roteiro:**
1. [Arquitetura Geral](architecture/1.%20ARQUITETURA_GERAL.md) - Entender containers e fluxos (25 min)
2. [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md) - Regras de código (30 min)
3. [Integrações](architecture/3.%20INTEGRACOES.md) - Seção relevante ao trabalho (10 min)
4. [Setup Local](setup/local.md) - Configurar ambiente

**Resultado:** Pronto para contribuir no primeiro dia

---

### 🔧 Desenvolvedor Experiente

**Uso como Referência:**
- [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md) → Consultar padrões
- [Integrações](architecture/3.%20INTEGRACOES.md) → Ver código de integrações específicas
- [Arquitetura Geral](architecture/1.%20ARQUITETURA_GERAL.md) → Fluxo end-to-end

---

### 🏗️ Arquiteto/Tech Lead

**Foco em Decisões Técnicas:**
- [Arquitetura Geral](architecture/1.%20ARQUITETURA_GERAL.md) → Roadmap Fase 6
- [Visão Integrada](architecture/README.md) → Status completo do sistema
- Avaliar separação de containers (Fase 6D)

---

### 🐛 Troubleshooting

**Checklist:**
1. Identificar container com problema (Django 8003 ou Risk Engine 8004)
2. [Integrações](architecture/3.%20INTEGRACOES.md) → Ver fluxo da integração
3. [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md) → Verificar padrões (fail-open, timeouts, cache)
4. Logs: `docker-compose logs -f web` ou `docker-compose logs -f riskengine`

## 📋 Documentos por Categoria

### Arquitetura

| Documento | Conteúdo | Linhas | Tempo |
|-----------|----------|--------|-------|
| [ARQUITETURA_GERAL.md](architecture/1.%20ARQUITETURA_GERAL.md) | Containers, status migração, funcionalidades, estrutura | ~900 | 25 min |
| [DIRETRIZES_UNIFICADAS.md](architecture/2.%20DIRETRIZES_UNIFICADAS.md) | Regras fundamentais, padrões, boas práticas | ~850 | 30 min |
| [INTEGRACOES.md](architecture/3.%20INTEGRACOES.md) | 26 APIs internas, serviços externos, troubleshooting | ~950 | 35 min |

### Desenvolvimento

| Documento | Conteúdo | Foco |
|-----------|----------|------|
| [django-diretrizes.md](development/django-diretrizes.md) | Padrões Django específicos | Backend principal |
| [riskengine-diretrizes.md](development/riskengine-diretrizes.md) | Padrões antifraude | Scoring, regras |

### Serviços

| Documento | Conteúdo | Detalhamento |
|-----------|----------|--------------|
| [django-readme.md](services/django-readme.md) | Documentação completa Django | 1117 linhas |
| [riskengine-readme.md](services/riskengine-readme.md) | Documentação completa Risk Engine | 839 linhas |

### Setup e Deploy

| Documento | Conteúdo | Uso |
|-----------|----------|-----|
| [local.md](setup/local.md) | Setup desenvolvimento local | Docker, ENV vars, AWS |
| [producao.md](deployment/producao.md) | Deploy produção | AWS, Secrets Manager |

## 🎯 Tópicos Rápidos

### Autenticação
- JWT Customizado: [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md#autenticação)
- OAuth 2.0: [Integrações](architecture/3.%20INTEGRACOES.md#oauth)
- 2FA WhatsApp: [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md#segurança)

### Banco de Dados
- Collation: [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md#banco-de-dados)
- Configuração: [Setup Local](setup/local.md)
- AWS Secrets: [Integrações](architecture/3.%20INTEGRACOES.md#aws-secrets-manager)

### APIs
- 26 APIs Internas: [Integrações](architecture/3.%20INTEGRACOES.md#apis-internas)
- Padrões REST: [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md#apis-rest)
- Endpoints: [README Django](services/django-readme.md)

### Antifraude
- 5 Regras: [Diretrizes Unificadas](architecture/2.%20DIRETRIZES_UNIFICADAS.md#antifraude)
- MaxMind: [Integrações](architecture/3.%20INTEGRACOES.md#maxmind)
- Scoring: [README Risk Engine](services/riskengine-readme.md)

### Notificações
- WhatsApp: [Integrações](architecture/3.%20INTEGRACOES.md#whatsapp)
- SMS: [Integrações](architecture/3.%20INTEGRACOES.md#sms)
- Firebase/APN: [Integrações](architecture/3.%20INTEGRACOES.md#push-notifications)

## 🔍 Busca por Palavra-Chave

Use `grep` ou busca do editor para encontrar:

```bash
# Buscar por termo em toda documentação
grep -r "termo_busca" docs/

# Buscar em arquivos específicos
grep "JWT" docs/architecture/*.md
```

**Termos Comuns:**
- `OAuth`, `JWT`, `2FA` → Autenticação
- `MaxMind`, `score`, `risco` → Antifraude
- `WhatsApp`, `SMS`, `Firebase` → Notificações
- `collation`, `utf8mb4` → Banco de dados
- `container`, `docker`, `deploy` → Infraestrutura

## 📊 Estatísticas

**Documentação Original:**
- Django README: 1.117 linhas
- Risk Engine README: 839 linhas
- Django DIRETRIZES: 3.428 linhas
- Risk Engine DIRETRIZES: 875 linhas
- **Total:** 6.259 linhas

**Documentação Consolidada:**
- ARQUITETURA_GERAL: ~800 linhas
- DIRETRIZES_UNIFICADAS: ~700 linhas
- INTEGRACOES: ~800 linhas
- **Total:** ~2.300 linhas organizadas semanticamente

**Benefícios:**
- ✅ Eliminação de duplicações
- ✅ Organização semântica por tema
- ✅ Navegação facilitada (índices)
- ✅ Referências cruzadas
- ✅ 100% da informação técnica preservada

## 🔄 Atualizações

**Última consolidação:** 02/11/2025  
**Versão:** 3.0

Para atualizar a documentação:
1. Editar arquivo `.md` correspondente
2. Manter formatação consistente
3. Atualizar data no cabeçalho
4. Incrementar versão se necessário

---

**Mantido por:** Equipe WallClub  
**Dúvidas:** Consulte a [Visão Integrada](architecture/README.md)
