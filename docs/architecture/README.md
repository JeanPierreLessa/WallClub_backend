# VISÃO INTEGRADA - WALLCLUB ECOSYSTEM

**Versão:** 4.0  
**Data:** 05/11/2025  
**Objetivo:** Documentação completa Fases 1-6 (Segurança + Antifraude + Services + 2FA + Portais + 4 Containers)

**Resultado:** 4 containers independentes, 10 containers totais, 26 APIs internas, Sistema Multi-Portal, 9 regras antifraude, Flower monitoring

---

## 📚 ÍNDICE DE DOCUMENTOS

### 📖 Leitura Obrigatória (Ordem Recomendada)

1. **[ARQUITETURA_GERAL.md](1.%20ARQUITETURA_GERAL.md)** (~950 linhas)
   - ✅ 10 containers orquestrados (4 Django + Redis + 2 Celery + Beat + Nginx + Flower)
   - ✅ Fases 1-6 concluídas (Segurança + Antifraude + Services + 2FA + Portais + Containers)
   - ✅ 4 containers Django independentes em produção (portais, pos, apis, riskengine)
   - ✅ Nginx Gateway com 14 subdomínios (incluindo flower.wallclub.com.br)
   - ✅ Flower: Monitoramento Celery em tempo real (credenciais via AWS Secrets)
   - ✅ Sistema Antifraude completo (score 0-100, 9 regras)
   - ✅ JWT Customizado (18 cenários testados)
   - ✅ Sistema Multi-Portal (3 tabelas, controle hierárquico)
   - ✅ Estrutura de diretórios anotada
   - ✅ Deploy e configuração produção
   - **Tempo leitura:** 30 min

2. **[DIRETRIZES_UNIFICADAS.md](2.%20DIRETRIZES_UNIFICADAS.md)** (~950 linhas)
   - Regras fundamentais de comportamento
   - ✅ Containers desacoplados (26 APIs REST + SQL + Lazy imports)
   - ✅ Banco de dados (collation utf8mb4_unicode_ci, AWS Secrets)
   - ✅ Timezone e datas (USE_TZ=False, datetime.now())
   - ✅ Valores monetários (Decimal, formato brasileiro)
   - ✅ APIs REST (POST obrigatório, formato padrão)
   - ✅ JWT Customizado (18 cenários, validação obrigatória contra tabela)
   - ✅ Login Simplificado Fintech (modelo Nubank/PicPay)
   - ✅ Bypass 2FA para testes Apple/Google
   - ✅ Sistema Antifraude (9 regras, MaxMind, 3DS)
   - ✅ Sistema Segurança Multi-Portal (6 detectores Celery)
   - ✅ Notificações (WhatsApp, SMS, Push Firebase/APN)
   - ✅ Arquitetura Docker (10 containers: +Flower monitoring)
   - Boas práticas de código
   - **Tempo leitura:** 30 min

3. **[INTEGRACOES.md](3.%20INTEGRACOES.md)** (~1550 linhas)
   - **APIs Internas (26 endpoints - Fase 6B):**
     - ✅ Conta Digital (5 endpoints: consultar-saldo, autorizar-uso, debitar, estornar, calcular-maximo)
     - ✅ Checkout Recorrências (8 endpoints: CRUD + pausar/reativar/cobrar)
     - ✅ Ofertas (6 endpoints: CRUD + grupos/segmentação)
     - ✅ Parâmetros (7 endpoints: configs + modalidades + planos + importações)
   - **Integrações Externas:**
     - ✅ Pinbank (gateway pagamentos, cargas automáticas, captura recorrências)
     - ✅ MaxMind minFraud (score 0-100, cache 1h, hit rate >90%)
     - ✅ Risk Engine - Autenticação Cliente (score 0-50, 9 flags)
     - ✅ WhatsApp Business (templates AUTHENTICATION/UTILITY)
     - ✅ SMS (encoding URLs correto)
     - ✅ Firebase Cloud Messaging (Android push)
     - ✅ Apple Push Notifications (iOS push, fallback sandbox)
     - ✅ AWS Secrets Manager (credenciais seguras, migração completa)
   - ✅ Celery Tasks (recorrências diárias, detectores segurança)
   - Troubleshooting completo
   - **Tempo leitura:** 45 min

---

## PARA QUEM É ESTA DOCUMENTAÇÃO?

### Novo Desenvolvedor (Onboarding)
### 👨‍💻 Novo Desenvolvedor (Onboarding)
**Objetivo:** Entender sistema em <1 hora

**Roteiro:**
1. Ler `ARQUITETURA_GERAL.md` (entender containers e fluxos)
2. Ler `DIRETRIZES_UNIFICADAS.md` (regras de código)
3. Ler `INTEGRACOES.md` seção relevante ao trabalho
4. Consultar documentos específicos conforme necessidade

**Resultado esperado:** Pronto para contribuir no primeiro dia

---

### 🔧 Desenvolvedor Experiente
**Objetivo:** Referência rápida

**Uso:**
- `DIRETRIZES_UNIFICADAS.md` → Consulta padrões
- `INTEGRACOES.md` → Ver código de integrações específicas
- `ARQUITETURA_GERAL.md` → Entender fluxo end-to-end

---

### 🏗️ Arquiteto/Tech Lead
**Objetivo:** Visão holística + decisões técnicas

**Foco:**
- `ARQUITETURA_GERAL.md` → Roadmap Fase 6
- Avaliar separação de containers
- Propor melhorias de integração

---

### 🐛 Troubleshooting
**Objetivo:** Resolver bugs rapidamente

**Checklist:**
1. Identificar container com problema (Django 8003 ou Risk Engine 8004)
2. `INTEGRACOES.md` → Ver fluxo da integração
3. `DIRETRIZES_UNIFICADAS.md` → Verificar padrões (fail-open, timeouts, cache)
4. Logs do container específico

---

## 🚀 QUICK START

### Subir Ambiente Completo
```bash
cd /var/www/wallclub_django
docker-compose down
docker-compose up -d --build

# Verificar status
docker-compose ps

# Logs
docker-compose logs -f web           # Django Principal
docker-compose logs -f riskengine    # Risk Engine
docker-compose logs -f celery-worker # Detectores
```

### Health Checks
```bash
# Django Principal
curl http://localhost:8003/api/health/

# Risk Engine
curl http://localhost:8004/api/antifraude/health/ \
  -H "Authorization: Bearer <token>"

# Redis
docker exec wallclub-redis redis-cli ping
```

### Obter Token OAuth
```bash
curl -X POST http://localhost:8004/oauth/token/ \
  -d "grant_type=client_credentials" \
  -d "client_id=wallclub_django_internal" \
  -d "client_secret=<secret>"
```

---

## 📊 STATUS DO SISTEMA

### Containers Operacionais
| Container | Porta | Status | Versão |
|-----------|-------|--------|--------|
| Django Principal | 8003 | ✅ Operacional | release300 |
| Risk Engine | 8004 | ✅ Operacional | 1.0 |
| Redis | 6379 | ✅ Operacional | 7-alpine |
| Celery Worker | - | ✅ Operacional | 1.0 |
| Celery Beat | - | ✅ Operacional | 1.0 |

### Integrações
| Integração | Status | Desde |
|------------|--------|-------|
| POSP2 → Risk Engine | ✅ Ativo | 16/10/2025 |
| Checkout → Risk Engine | ✅ Ativo | 22/10/2025 |
| Middleware → Risk Engine | ✅ Ativo | 18/10/2025 |
| Portal Admin → Risk Engine | ✅ Ativo | 18/10/2025 |
| Risk Engine → MaxMind | ✅ Ativo | 16/10/2025 |
| 3D Secure 2.0 | ⏳ Pendente | - |

### Funcionalidades
| Feature | Status | Testado |
|---------|--------|---------|
| Sistema JWT Customizado | ✅ Completo | 18 cenários (28/10) |
| 2FA WhatsApp + Devices | ✅ Completo | 5 endpoints |
| Bypass 2FA Testes Apple/Google | ✅ Completo | Release 3.1.0 (31/10) |
| Antifraude 5 Regras | ✅ Completo | Produção |
| 6 Detectores Automáticos | ✅ Completo | Celery 5min |
| Portal Atividades Suspeitas | ✅ Completo | Admin |
| Sistema Bloqueios | ✅ Completo | IP + CPF |
| Checkout 2FA | ✅ Completo | Rate limiting |
| POSP2 Interceptação | ✅ Completo | Linha 333 |

---

## 🔗 LINKS RÁPIDOS

### Documentação Técnica Original
- [Django - DIRETRIZES.md](../1.%20DIRETRIZES.md)
- [Django - README.md](../2.%20README.md)
- [Risk Engine - DIRETRIZES.md](../../../wallclub-riskengine/docs/DIRETRIZES.md)
- [Risk Engine - engine_antifraude.md](../../../wallclub-riskengine/docs/engine_antifraude.md)
- [Risk Engine - README.md](../../../wallclub-riskengine/docs/README.md)
- [Testes Autenticação](../TESTE_CURL_USUARIO.md)
- [Sistema Atividades Suspeitas](../seguranca/SISTEMA_ATIVIDADES_SUSPEITAS.md)

### Planejamento
- [Roteiro Mestre Sequencial](../plano_estruturado/ROTEIRO_MESTRE_SEQUENCIAL.md)
- [Fase 5 - Checkout](../plano_estruturado/ROTEIRO_FASE_5.md)
- [Fases 1-4 Concluídas](../plano_estruturado/ROTEIRO_CONCLUIDO_FASE_1_A_4.md)

---

## 🎓 CONCEITOS-CHAVE

### Fail-Open Principle
Sistema NUNCA bloqueia por falha técnica. Todas integrações externas implementam fallback seguro.

### OAuth 2.0 entre Containers
Autenticação obrigatória para todas chamadas entre Django ↔ Risk Engine.

### JWT Customizado
Sistema independente do Django User/Session com validação obrigatória contra tabela de auditoria.

### Collation Padronizada
100% das tabelas em `utf8mb4_unicode_ci` para evitar "Illegal mix of collations".

### Score de Risco
- 0-59: APROVADO (automático)
- 60-79: REVISÃO (analista)
- 80-100: REPROVADO (automático)

### Rate Limiting
- Login: 5/15min, 10/1h, 20/24h
- Checkout 2FA: 3/tel, 5/cpf, 10/ip
- Limite progressivo valores

---

## 📈 MÉTRICAS DE PERFORMANCE

| Operação | Meta | P95 | Status |
|----------|------|-----|--------|
| Análise de risco | <200ms | <500ms | ✅ |
| Consulta MaxMind | <300ms | <600ms | ✅ |
| Cache hit Redis | <10ms | <20ms | ✅ |
| Login + JWT | <500ms | <1s | ✅ |

---

## 🔮 ROADMAP

### Fase 5 - Checkout + Recorrências
**Status:** ✅ Concluída  
**Data:** Out/2025

### Fase 6 - Separação em Múltiplos Containers
**Status:** 🔄 Em progresso (60% concluído)  
**Período:** Semanas 27-34

**6A - CORE Limpo:** ✅ Concluída (30/10/2025)
- 0 imports de apps no módulo comum/
- Pronto para extração como package

**6B - Dependências Cruzadas:** ✅ Concluída (01/11/2025)
- 26 APIs REST internas (OAuth 2.0)
- 17 arquivos com lazy imports
- 2 classes SQL direto (9 métodos)
- Fix crítico RPR (dict vs getattr)
- Validação: 0 imports diretos entre containers

**6C - Extrair CORE:** ⏳ Próxima (Semana 31)
- Criar package wallclub-core
- Setup.py + requirements
- Publicar localmente

**6D - Separação Física:** 📋 Planejada (Semanas 32-36)
- 5 containers independentes
- Deploy por container
- Nginx Gateway

**Arquitetura Alvo:**
```
1. wallclub-portais (8001)     - Admin/Lojista/Vendas
2. wallclub-pos (8002)          - POSP2 + Pinbank
3. wallclub-apis (8003)         - Mobile + Checkout
4. wallclub-riskengine (8004)   - Antifraude (✅ existe)
5. wallclub-core (package)      - Compartilhado
```

**Benefícios:**
- Deploy independente
- Escalabilidade por app
- Isolamento de falhas
- Comunicação via APIs REST

---

## 🆘 SUPORTE E CONTATOS

### Ambiente de Desenvolvimento
- **Servidor:** `apidj.wallclub.com.br`
- **Diretório Django:** `/var/www/wallclub_django`
- **Diretório Risk Engine:** `/var/www/wallclub_django_risk_engine`

### Logs Importantes
```bash
# Auditoria login (lido por detector automático)
/app/logs/auditoria.login.log

# Django geral
docker-compose logs -f web

# Risk Engine
docker-compose logs -f riskengine

# Celery tasks
docker-compose logs -f celery-worker
```

### AWS Secrets Manager
- **Secret:** `wall/prod/db`
- **Contém:** Credenciais MySQL, OAuth clients, MaxMind

---

## 📝 CONVENÇÕES DESTE DOCUMENTO

### Emojis Usados
- ✅ Funcionalidade completa e testada
- ⏳ Em desenvolvimento ou pendente
- 🔄 Em andamento
- 📋 Planejado
- ❌ Não implementado/Erro
- 🚨 Atenção/Crítico

### Formatação de Código
```python
# Código Python inline
```

```bash
# Comandos shell
```

```json
// JSON examples
```

---

## 📅 HISTÓRICO DE ATUALIZAÇÕES

| Data | Versão | Mudanças |
|------|--------|----------|
| 29/10/2025 | 1.0 | Criação da documentação integrada (3 docs principais) |
| 30/10/2025 | 2.0 | Consolidação semântica completa (Django 1117 + Risk Engine 839 + DIRETRIZES 4303 linhas → 3 docs organizados) |
| 30/10/2025 | 2.1 | Permissões granulares Portal Vendas (checkout vs recorrência) + Correção filtros |
| 31/10/2025 | 2.2 | Bypass 2FA para testes Apple/Google (campo bypass_2fa, login sem OTP para revisores) |
| 01/11/2025 | 3.0 | **Fase 6A+6B:** Containers desacoplados, 26 APIs internas, lazy imports, CORE limpo |

---

## 🤝 CONTRIBUINDO

### Atualizar Documentação
1. Editar arquivo `.md` correspondente
2. Manter formatação consistente
3. Atualizar data no cabeçalho
4. Incrementar versão se necessário

### Regras de Ouro
- ✅ Falar em português
- ✅ Ser técnico e direto
- ✅ Incluir exemplos de código
- ✅ Documentar decisões técnicas
- ❌ Não inventar informações
- ❌ Não criar código não solicitado

---

**Mantido por:** Jean Lessa + Claude AI  
**Última atualização:** 01/11/2025  
**Versão:** 3.0

---

## 📊 ESTATÍSTICAS DA CONSOLIDAÇÃO

**Documentos Originais:**
- Django README.md: 1.117 linhas
- Risk Engine README.md: 839 linhas
- Django DIRETRIZES.md: 3.428 linhas
- Risk Engine DIRETRIZES.md: 875 linhas
- **Total:** 6.259 linhas

**Documentos Consolidados:**
- ARQUITETURA_GERAL.md: ~800 linhas
- DIRETRIZES_UNIFICADAS.md: ~700 linhas
- INTEGRACOES.md: ~800 linhas
- **Total:** ~2.300 linhas organizadas

**Benefícios:**
- ✅ Eliminação de duplicações
- ✅ Organização semântica por tema
- ✅ Navegação facilitada (índices)
- ✅ Referências cruzadas aos documentos originais
- ✅ 100% da informação técnica preservada
