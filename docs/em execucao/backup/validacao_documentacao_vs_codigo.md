# VALIDAÇÃO DOCUMENTAÇÃO VS CÓDIGO REAL

**Data:** 09/01/2026  
**Objetivo:** Garantir que documentação reflete a realidade do código em produção  
**Frequência Recomendada:** Mensal ou após mudanças significativas

---

## 📋 ESTRATÉGIA DE VALIDAÇÃO

### Abordagem em 3 Camadas

1. **Validação Automatizada (70%)** - Scripts que verificam código
2. **Validação Semi-Automatizada (20%)** - Queries SQL + análise
3. **Validação Manual (10%)** - Revisão humana de pontos críticos

---

## 1. VALIDAÇÃO AUTOMATIZADA

### 1.1 Script: Validar Containers e Portas

```bash
#!/bin/bash
# scripts/validacao/validar_containers.sh

echo "=== VALIDAÇÃO: Containers e Portas ==="
echo ""

# Documentado: 9 containers
echo "📄 Documentação afirma: 9 containers"
echo "🔍 Realidade:"
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep wallclub

CONTAINER_COUNT=$(docker ps | grep wallclub | wc -l)
echo ""
echo "Total containers ativos: $CONTAINER_COUNT"

if [ $CONTAINER_COUNT -eq 9 ]; then
    echo "✅ VALIDADO: 9 containers conforme documentação"
else
    echo "❌ DIVERGÊNCIA: Esperado 9, encontrado $CONTAINER_COUNT"
fi

echo ""
echo "=== Portas Documentadas vs Reais ==="
echo "Portais: 8005 (doc) vs $(docker port wallclub-portais 2>/dev/null | grep 8005 || echo 'ERRO')"
echo "POS: 8006 (doc) vs $(docker port wallclub-pos 2>/dev/null | grep 8006 || echo 'ERRO')"
echo "APIs: 8007 (doc) vs $(docker port wallclub-apis 2>/dev/null | grep 8007 || echo 'ERRO')"
echo "RiskEngine: 8008 (doc) vs $(docker port wallclub-riskengine 2>/dev/null | grep 8008 || echo 'ERRO')"
echo "Redis: 6379 (doc) vs $(docker port wallclub-redis 2>/dev/null | grep 6379 || echo 'ERRO')"
```

---

### 1.2 Script: Validar APIs Internas

```python
#!/usr/bin/env python3
# scripts/validacao/validar_apis_internas.py

import os
import re
from pathlib import Path

# Documentado: 26 APIs REST internas
APIS_DOCUMENTADAS = {
    'cliente': 6,
    'conta_digital': 5,
    'checkout': 8,
    'ofertas': 6,
    'parametros': 7,
}

def encontrar_endpoints_api_interna(base_path):
    """Busca por @api_view(['POST']) em arquivos api_interna_*.py"""
    endpoints = {}
    
    for root, dirs, files in os.walk(base_path):
        for file in files:
            if 'api_interna' in file and file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Contar @api_view(['POST'])
                    count = len(re.findall(r"@api_view\(\['POST'\]\)", content))
                    
                    if count > 0:
                        modulo = os.path.basename(os.path.dirname(filepath))
                        endpoints[modulo] = endpoints.get(modulo, 0) + count
    
    return endpoints

def validar_apis():
    print("=== VALIDAÇÃO: APIs REST Internas ===\n")
    
    base_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/django'
    endpoints_reais = encontrar_endpoints_api_interna(base_path)
    
    print("📄 Documentação:")
    total_doc = sum(APIS_DOCUMENTADAS.values())
    for modulo, count in APIS_DOCUMENTADAS.items():
        print(f"  - {modulo}: {count} endpoints")
    print(f"  TOTAL: {total_doc} endpoints\n")
    
    print("🔍 Código Real:")
    total_real = sum(endpoints_reais.values())
    for modulo, count in endpoints_reais.items():
        print(f"  - {modulo}: {count} endpoints")
    print(f"  TOTAL: {total_real} endpoints\n")
    
    # Comparar
    print("=== Resultado ===")
    if total_doc == total_real:
        print(f"✅ VALIDADO: {total_doc} endpoints conforme documentação")
    else:
        print(f"❌ DIVERGÊNCIA: Doc={total_doc}, Real={total_real}")
        
        # Detalhar divergências
        for modulo in set(list(APIS_DOCUMENTADAS.keys()) + list(endpoints_reais.keys())):
            doc = APIS_DOCUMENTADAS.get(modulo, 0)
            real = endpoints_reais.get(modulo, 0)
            if doc != real:
                print(f"  ⚠️  {modulo}: Doc={doc}, Real={real}")

if __name__ == '__main__':
    validar_apis()
```

---

### 1.3 Script: Validar Middleware

```python
#!/usr/bin/env python3
# scripts/validacao/validar_middleware.py

import os
import importlib.util

# Documentado em DIRETRIZES.md e cenario_evolucao_arquitetura_JAN2026.md
MIDDLEWARE_DOCUMENTADO = [
    'security_middleware.py',
    'security_validation.py',
    'session_timeout.py',
    'subdomain_router.py',
]

MIDDLEWARE_RECOMENDADO = [
    'correlation_middleware.py',  # Ainda não implementado
    'request_logging_middleware.py',  # Ainda não implementado
]

def validar_middleware():
    print("=== VALIDAÇÃO: Middleware ===\n")
    
    middleware_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/core/wallclub_core/middleware'
    
    if not os.path.exists(middleware_path):
        print(f"❌ ERRO: Diretório não encontrado: {middleware_path}")
        return
    
    arquivos_reais = [f for f in os.listdir(middleware_path) if f.endswith('.py') and f != '__init__.py']
    
    print("📄 Middleware Documentado (Implementado):")
    for mw in MIDDLEWARE_DOCUMENTADO:
        existe = mw in arquivos_reais
        status = "✅" if existe else "❌"
        print(f"  {status} {mw}")
    
    print("\n📄 Middleware Recomendado (Não Implementado):")
    for mw in MIDDLEWARE_RECOMENDADO:
        existe = mw in arquivos_reais
        status = "✅ Implementado" if existe else "⏳ Pendente"
        print(f"  {status}: {mw}")
    
    print("\n🔍 Middleware Real (não documentado):")
    nao_documentados = set(arquivos_reais) - set(MIDDLEWARE_DOCUMENTADO) - set(MIDDLEWARE_RECOMENDADO)
    if nao_documentados:
        for mw in nao_documentados:
            print(f"  ⚠️  {mw} (não está na documentação)")
    else:
        print("  (nenhum)")

if __name__ == '__main__':
    validar_middleware()
```

---

### 1.4 Script: Validar Estrutura wallclub_core

```python
#!/usr/bin/env python3
# scripts/validacao/validar_wallclub_core.py

import os

# Documentado em README.md e ARQUITETURA.md
ESTRUTURA_DOCUMENTADA = {
    'database': ['queries.py'],
    'decorators': ['api_decorators.py'],
    'estr_organizacional': ['__init__.py', 'apps.py', 'canal.py'],
    'integracoes': ['apn_service.py', 'bureau_service.py', 'email_service.py', 
                    'firebase_service.py', 'sms_service.py', 'whatsapp_service.py',
                    'config_manager.py', 'notification_service.py'],
    'middleware': ['security_middleware.py', 'security_validation.py', 
                   'session_timeout.py', 'subdomain_router.py'],
    'oauth': ['decorators.py', 'jwt_utils.py', 'models.py', 'services.py'],
    'seguranca': ['services_2fa.py', 'services_device.py', 'rate_limiter_2fa.py', 
                  'validador_cpf.py'],
    'services': ['auditoria_service.py'],
    'templatetags': ['formatacao_tags.py'],
    'utilitarios': ['config_manager.py', 'export_utils.py', 'formatacao.py', 
                    'log_control.py'],
}

def validar_wallclub_core():
    print("=== VALIDAÇÃO: Estrutura wallclub_core ===\n")
    
    core_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/core/wallclub_core'
    
    if not os.path.exists(core_path):
        print(f"❌ ERRO: Diretório não encontrado: {core_path}")
        return
    
    divergencias = []
    
    for diretorio, arquivos_doc in ESTRUTURA_DOCUMENTADA.items():
        dir_path = os.path.join(core_path, diretorio)
        
        print(f"📁 {diretorio}/")
        
        if not os.path.exists(dir_path):
            print(f"  ❌ Diretório não existe")
            divergencias.append(f"Diretório ausente: {diretorio}")
            continue
        
        arquivos_reais = [f for f in os.listdir(dir_path) if f.endswith('.py')]
        
        # Verificar arquivos documentados
        for arquivo in arquivos_doc:
            existe = arquivo in arquivos_reais
            status = "✅" if existe else "❌"
            print(f"  {status} {arquivo}")
            if not existe:
                divergencias.append(f"Arquivo ausente: {diretorio}/{arquivo}")
        
        # Arquivos não documentados
        nao_documentados = set(arquivos_reais) - set(arquivos_doc) - {'__init__.py', '__pycache__'}
        if nao_documentados:
            for arquivo in nao_documentados:
                print(f"  ⚠️  {arquivo} (não documentado)")
    
    print("\n=== Resultado ===")
    if not divergencias:
        print("✅ VALIDADO: Estrutura conforme documentação")
    else:
        print(f"❌ DIVERGÊNCIAS ENCONTRADAS: {len(divergencias)}")
        for div in divergencias:
            print(f"  - {div}")

if __name__ == '__main__':
    validar_wallclub_core()
```

---

### 1.5 Script Master: Executar Todas Validações

```bash
#!/bin/bash
# scripts/validacao/validar_tudo.sh

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  VALIDAÇÃO COMPLETA: DOCUMENTAÇÃO VS CÓDIGO REAL          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Containers
bash scripts/validacao/validar_containers.sh
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 2. APIs Internas
python3 scripts/validacao/validar_apis_internas.py
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 3. Middleware
python3 scripts/validacao/validar_middleware.py
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 4. wallclub_core
python3 scripts/validacao/validar_wallclub_core.py
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 5. Variáveis de Ambiente
bash scripts/validacao/validar_env_vars.sh
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  VALIDAÇÃO CONCLUÍDA                                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
```

---

## 2. VALIDAÇÃO SEMI-AUTOMATIZADA

### 2.1 Queries SQL: Validar Tabelas Documentadas

```sql
-- scripts/validacao/validar_tabelas.sql

-- Documentado: Sistema de Ofertas (5 tabelas)
SELECT 'ofertas' AS tabela, 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS existe
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'ofertas'
UNION ALL
SELECT 'ofertas_grupos_segmentacao', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'ofertas_grupos_segmentacao'
UNION ALL
SELECT 'ofertas_grupos_clientes', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'ofertas_grupos_clientes'
UNION ALL
SELECT 'oferta_disparos', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'oferta_disparos'
UNION ALL
SELECT 'oferta_envios', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'oferta_envios';

-- Documentado: Sistema de Cashback (3 tabelas)
SELECT 'cashback_regra_loja' AS tabela, 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS existe
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'cashback_regra_loja'
UNION ALL
SELECT 'cashback_uso', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'cashback_uso'
UNION ALL
SELECT 'movimentacao_conta_digital', 
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'movimentacao_conta_digital';

-- Documentado: Tabela unificada transactiondata_pos
SELECT 'transactiondata_pos' AS tabela,
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS existe,
       (SELECT COUNT(*) FROM transactiondata_pos) AS total_registros
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'transactiondata_pos';

-- Verificar campo 'gateway' (PINBANK/OWN)
SELECT 'Campo gateway existe?' AS validacao,
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS resultado
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub' 
  AND TABLE_NAME = 'transactiondata_pos'
  AND COLUMN_NAME = 'gateway';
```

---

### 2.2 Queries SQL: Validar Parâmetros Financeiros

```sql
-- scripts/validacao/validar_parametros.sql

-- Documentado: 3.840 configurações ativas
SELECT '3.840 configurações ativas' AS documentado,
       COUNT(*) AS real,
       CASE 
           WHEN COUNT(*) = 3840 THEN '✅ VALIDADO'
           ELSE CONCAT('❌ DIVERGÊNCIA: ', COUNT(*))
       END AS status
FROM parametros_loja
WHERE ativo = TRUE;

-- Documentado: 133 planos
SELECT '133 planos' AS documentado,
       COUNT(DISTINCT id_plano) AS real,
       CASE 
           WHEN COUNT(DISTINCT id_plano) = 133 THEN '✅ VALIDADO'
           ELSE CONCAT('❌ DIVERGÊNCIA: ', COUNT(DISTINCT id_plano))
       END AS status
FROM parametros_loja
WHERE ativo = TRUE;

-- Verificar modalidades documentadas
SELECT 'Modalidades' AS tipo,
       GROUP_CONCAT(DISTINCT modalidade ORDER BY modalidade) AS valores
FROM parametros_loja
WHERE ativo = TRUE;
```

---

### 2.3 Script: Validar Variáveis de Ambiente

```bash
#!/bin/bash
# scripts/validacao/validar_env_vars.sh

echo "=== VALIDAÇÃO: Variáveis de Ambiente ==="
echo ""

# Documentado em README.md e ARQUITETURA.md
VARS_OBRIGATORIAS=(
    "BASE_URL"
    "CHECKOUT_BASE_URL"
    "PORTAL_LOJISTA_URL"
    "PORTAL_VENDAS_URL"
    "MEDIA_BASE_URL"
    "MERCHANT_URL"
    "DEBUG"
    "ALLOWED_HOSTS"
)

echo "📄 Variáveis Documentadas como Obrigatórias:"
echo ""

# Verificar no container
for var in "${VARS_OBRIGATORIAS[@]}"; do
    valor=$(docker exec wallclub-apis printenv $var 2>/dev/null)
    if [ -n "$valor" ]; then
        echo "✅ $var = $valor"
    else
        echo "❌ $var = (não definida)"
    fi
done

echo ""
echo "=== Verificar MERCHANT_URL (Obrigatória para Own Financial) ==="
MERCHANT_URL=$(docker exec wallclub-pos printenv MERCHANT_URL 2>/dev/null)
if [ -n "$MERCHANT_URL" ]; then
    echo "✅ MERCHANT_URL definida: $MERCHANT_URL"
else
    echo "❌ MERCHANT_URL não definida (CRÍTICO para Own Financial)"
fi
```

---

## 3. VALIDAÇÃO MANUAL (CHECKLIST)

### 3.1 Arquitetura de Containers

```markdown
## Checklist: Containers e Comunicação

- [ ] 9 containers rodando (portais, pos, apis, riskengine, redis, celery-worker, celery-beat, nginx, flower)
- [ ] Portas corretas (8005, 8006, 8007, 8008, 6379, 5555)
- [ ] Comunicação inter-containers funcional (testar API interna)
- [ ] OAuth 2.0 entre containers (verificar tokens)
- [ ] Nginx roteando 14 subdomínios corretamente
- [ ] Flower acessível (flower.wallclub.com.br)

**Como testar comunicação:**
```bash
# Container POS chamando API interna (Container APIs)
docker exec wallclub-pos curl -X POST http://wallclub-apis:8007/api/internal/cliente/consultar_por_cpf/ \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"cpf": "12345678900", "canal_id": 1}'
```
```

---

### 3.2 Segurança

```markdown
## Checklist: Segurança

- [ ] JWT validado contra BD (não apenas decodificação)
- [ ] Rate limiting progressivo ativo (5/15min → 10/1h → 20/24h)
- [ ] AWS Secrets Manager funcionando (sem credenciais hardcoded)
- [ ] Antifraude <200ms (verificar logs)
- [ ] MaxMind cache ativo (hit rate >90%)
- [ ] 2FA Checkout Web funcional
- [ ] Circuit breaker implementado? (❌ Pendente conforme doc)

**Como testar JWT:**
```bash
# Tentar usar token revogado (deve falhar)
curl -X POST https://wcapi.wallclub.com.br/api/v1/conta_digital/consultar-saldo/ \
  -H "Authorization: Bearer TOKEN_REVOGADO" \
  -d '{"cliente_id": 123}'
# Esperado: 401 Unauthorized
```
```

---

### 3.3 Integrações Externas

```markdown
## Checklist: Integrações

- [ ] Pinbank: transações funcionando
- [ ] Own Financial: OAuth 2.0 com cache 4min
- [ ] MaxMind: score retornando (0-100)
- [ ] WhatsApp Business: templates dinâmicos enviando
- [ ] SMS Gateway: mensagens sendo entregues
- [ ] AWS SES: emails transacionais funcionando
- [ ] Firebase/APN: push notifications enviando

**Como testar:**
```bash
# Verificar logs de integração
docker logs wallclub-pos --tail 100 | grep -i "pinbank\|own"
docker logs wallclub-riskengine --tail 100 | grep -i "maxmind"
docker logs wallclub-apis --tail 100 | grep -i "whatsapp\|sms\|firebase"
```
```

---

### 3.4 Dados e Tabelas

```markdown
## Checklist: Banco de Dados

- [ ] Collation utf8mb4_unicode_ci em todas tabelas
- [ ] Tabela transactiondata_pos unificada (Pinbank + Own)
- [ ] Campo 'gateway' (PINBANK/OWN) populado
- [ ] Sistema Ofertas: 5 tabelas criadas
- [ ] Sistema Cashback: 3 tabelas criadas
- [ ] Parâmetros: 3.840 configurações ativas
- [ ] Terminais: campos inicio/fim como DATETIME (não Unix timestamp)

**Como validar:**
```sql
-- Executar scripts/validacao/validar_tabelas.sql
-- Executar scripts/validacao/validar_parametros.sql
```
```

---

### 3.5 Monitoramento

```markdown
## Checklist: Observabilidade

- [ ] Flower acessível (flower.wallclub.com.br)
- [ ] Logs estruturados (JSON)
- [ ] Prometheus implementado? (❌ Pendente)
- [ ] Grafana implementado? (❌ Pendente)
- [ ] ELK Stack implementado? (❌ Pendente)
- [ ] Alertas configurados? (❌ Pendente)

**Status Atual (conforme doc):**
- ✅ Flower (Celery tasks)
- ❌ Métricas de APIs internas (Pendente)
- ❌ Métricas de integrações externas (Pendente)
- ❌ Dashboards de negócio (Pendente)
```

---

### 3.6 Testes

```markdown
## Checklist: Testes Automatizados

- [ ] Testes unitários existem? (❌ ~5% cobertura)
- [ ] Testes de integração existem? (❌ Não)
- [ ] Testes E2E existem? (❌ Não)
- [ ] Testes de carga existem? (❌ Não)
- [ ] CI/CD pipeline configurado? (❌ Deploy manual)

**Status Atual (conforme doc):**
- Cobertura: ~5% (estimado)
- Apenas testes manuais via curl (18 cenários JWT)
```

---

## 4. RELATÓRIO DE VALIDAÇÃO

### Template de Relatório

```markdown
# RELATÓRIO DE VALIDAÇÃO - [DATA]

## Resumo Executivo

- **Validações Automatizadas:** X/Y passaram
- **Validações Semi-Automatizadas:** X/Y passaram
- **Validações Manuais:** X/Y passaram
- **Taxa de Conformidade:** XX%

## Divergências Críticas 🔴

1. [Descrição da divergência]
   - **Documentado:** [O que está na doc]
   - **Real:** [O que está no código]
   - **Impacto:** [Alto/Médio/Baixo]
   - **Ação:** [O que fazer]

## Divergências Médias 🟡

...

## Divergências Baixas 🟢

...

## Itens Não Implementados (Conforme Esperado)

- Circuit Breaker (Recomendado em cenario_evolucao_arquitetura_JAN2026.md)
- Correlation ID Middleware (Recomendado)
- Prometheus + Grafana (Planejado)
- Testes Automatizados (Planejado)
- CI/CD Pipeline (Planejado)

## Recomendações

1. [Ação prioritária 1]
2. [Ação prioritária 2]
3. [Ação prioritária 3]

## Próxima Validação

**Data:** [Data + 30 dias]
**Responsável:** [Nome]
```

---

## 5. AUTOMAÇÃO COMPLETA

### GitHub Action: Validação Semanal

```yaml
# .github/workflows/validacao-documentacao.yml
name: Validação Documentação vs Código

on:
  schedule:
    - cron: '0 9 * * 1'  # Toda segunda-feira às 9h
  workflow_dispatch:  # Permitir execução manual

jobs:
  validar:
    runs-on: ubuntu-latest
    
    steps:
    - name: Checkout code
      uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Executar validações
      run: |
        chmod +x scripts/validacao/*.sh
        bash scripts/validacao/validar_tudo.sh > relatorio_validacao.txt
    
    - name: Upload relatório
      uses: actions/upload-artifact@v3
      with:
        name: relatorio-validacao
        path: relatorio_validacao.txt
    
    - name: Notificar Slack
      if: failure()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: '⚠️ Divergências encontradas na validação documentação vs código'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## 6. FREQUÊNCIA RECOMENDADA

| Tipo de Validação | Frequência | Responsável |
|-------------------|------------|-------------|
| Automatizada (scripts) | Semanal | CI/CD |
| Semi-Automatizada (SQL) | Mensal | Arquiteto |
| Manual (checklist) | Trimestral | Tech Lead |
| Completa (todas) | Após mudanças grandes | Equipe |

---

## 7. MANUTENÇÃO DA DOCUMENTAÇÃO

### Regras de Ouro

1. **Atualizar documentação ANTES do código** (TDD de docs)
2. **Pull Request deve incluir atualização de docs**
3. **Validação automatizada no CI/CD** (bloquear merge se divergir)
4. **Revisão trimestral completa** (agendar no calendário)

### Processo de Atualização

```
1. Mudança planejada
   ↓
2. Atualizar DIRETRIZES.md / ARQUITETURA.md
   ↓
3. Implementar código
   ↓
4. Executar validação automatizada
   ↓
5. Corrigir divergências
   ↓
6. Commit + PR
```

---

## 8. FERRAMENTAS ADICIONAIS

### 8.1 Docstring Coverage (Python)

```bash
# Verificar cobertura de docstrings
pip install interrogate
interrogate -v services/django/

# Esperado: >70% de cobertura
```

### 8.2 API Documentation (Swagger/OpenAPI)

```python
# Gerar documentação automática das APIs
# requirements.txt
drf-yasg==1.21.7

# urls.py
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
   openapi.Info(
      title="WallClub API",
      default_version='v1',
   ),
   public=False,
)

urlpatterns = [
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0)),
]
```

### 8.3 Architecture Decision Records (ADR)

```markdown
# docs/adr/001-usar-django-orm.md

# 1. Usar Django ORM para Acesso ao Banco

**Status:** Aceito
**Data:** 2025-10-01
**Decisores:** Jean Lessa, Equipe

## Contexto

Precisamos decidir como acessar o banco de dados MySQL.

## Decisão

Usar Django ORM com exceções para SQL direto em queries complexas.

## Consequências

**Positivas:**
- Migrations automáticas
- Proteção contra SQL injection
- Código mais legível

**Negativas:**
- Performance em queries complexas
- Curva de aprendizado

## Alternativas Consideradas

1. SQL direto (rejeitado - manutenção difícil)
2. SQLAlchemy (rejeitado - complexidade adicional)
```

---

## CONCLUSÃO

**Esforço Estimado para Setup Inicial:**
- Criar scripts: 16 horas
- Primeira validação completa: 8 horas
- Documentar divergências: 4 horas
- **TOTAL:** 28 horas (~1 semana)

**Esforço Recorrente:**
- Validação semanal automatizada: 0 horas (CI/CD)
- Validação mensal semi-automatizada: 2 horas
- Validação trimestral manual: 4 horas

**ROI:**
- Reduz drift entre documentação e código
- Facilita onboarding de novos desenvolvedores
- Aumenta confiança na documentação
- Detecta problemas antes de virarem bugs

---

**Responsável:** Jean Lessa  
**Próxima Revisão:** Fevereiro/2026  
**Status:** Proposta (aguardando aprovação)
