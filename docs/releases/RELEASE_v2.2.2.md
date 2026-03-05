# Release Notes - WallClub Backend v2.2.2

**Data de Release:** 04/03/2026
**Versão:** 2.2.2
**Status:** Stable
**Branch:** release-2.2.2

---

## 📋 Visão Geral

A versão 2.2.2 traz melhorias incrementais focadas em refinamento de funcionalidades existentes, com ênfase em:
- Padronização de exportações (Excel, CSV, PDF) em Conciliação e Recebimentos
- Melhorias na gestão de credenciais Pinbank
- Refinamentos no checkout e cadastro de clientes
- Ajustes em métricas de monitoramento
- Atualização de versões mínimas dos apps mobile

**Total de Commits:** 23
**Módulos Impactados:** 8
**Arquivos Modificados:** 31

---

## 🚀 Melhorias e Refinamentos

### 1. Portal Lojista - Conciliação ⭐

#### Padronização de Nomes de Colunas
- Nomes de colunas em exportações (Excel/CSV/PDF) agora idênticos aos da tela web
- Exemplos: "Dt Crédito", "Vl.Bruto(R$)", "Tx.Adm.(R$)", "Cód.Estab."
- Melhora experiência do usuário e facilita análise de dados

#### Correção de Formatação de Percentuais
- **Excel/PDF:** Percentuais exibidos corretamente (ex: 2,38% ao invés de 238%)
- **CSV:** Percentuais em formato decimal com 4 casas (ex: 0,0238)
- Remoção de multiplicação duplicada por 100 em queries de exportação

#### Filtros de Data de Pagamento
- Novos filtros: "Data Inicial Pagamento" e "Data Final Pagamento"
- Permite filtrar transações por data de crédito/pagamento separadamente
- Melhora precisão em conciliações financeiras

#### Ajuste de Precisão de Taxas
- Taxas percentuais agora com 4 casas decimais (DECIMAL(10,4))
- Maior precisão em cálculos financeiros

---

### 2. Portal Lojista - Recebimentos

#### Nova View: Recebimentos por Loja
- View intermediária agrupando recebimentos por estabelecimento
- Separação clara de valores brutos, líquidos e taxas
- Contador de registros por loja
- Template dedicado: `recebimentos_por_loja.html`

#### Padronização de Serviços
- Refatoração de `services_recebimentos.py`
- Código mais limpo e manutenível
- Tratamento consistente de valores None

---

### 3. Gestão de Credenciais Pinbank

#### Migração para Modelo LojaPinbank
- Remoção de campos de credenciais do modelo `Loja`
- Credenciais agora gerenciadas exclusivamente via `LojaPinbank`
- Melhor separação de responsabilidades
- Facilita rotação de credenciais por loja

#### Impacto
- `services_transacoes_pagamento.py` atualizado
- Queries otimizadas para buscar credenciais do modelo correto

---

### 4. Checkout e Cadastro de Clientes

#### Desmembramento de Endereço
- Campo único `endereco` removido de `CheckoutCliente`
- Endereço agora construído a partir de campos separados (logradouro, número, bairro, etc.)
- Maior flexibilidade para validações e integrações

#### Campo Data de Nascimento
- Adicionado `data_nascimento` em resposta de busca de cliente
- Campo readonly em formulários de edição
- Correção de nome de campo: `dt_nascimento` → `data_nascimento`

#### Login Biométrico
- Filtro por `canal_id` adicionado em busca de cliente
- Melhora segurança e isolamento de dados por canal

---

### 5. Monitoramento e Métricas

#### Endpoint /metrics
- Novo endpoint `/metrics` para coleta Prometheus
- Remoção de prefixo `/health/` de rotas de monitoramento
- Padronização de nomenclatura

#### Dashboard Grafana
- Atualização de jobs para nova estrutura de endpoints
- Métricas `django-prometheus` documentadas
- Correção de target do Alertmanager

---

### 6. Exportações - Melhorias Gerais

#### Tratamento de Valores None
- Padronização em todas as funções de exportação (Excel, CSV, PDF)
- Valores None exibidos como células vazias ao invés de "0" ou "None"
- Código mais limpo em `export_utils.py`

#### Ajustes de Layout PDF
- Redução de tamanho de fonte para melhor aproveitamento de espaço
- Largura de colunas otimizada
- Remoção de rodapé redundante de lojas

---

### 7. Apps Mobile

#### Atualização de Versões Mínimas
- Android: versão mínima atualizada para **3.1.9**
- iOS: versão mínima atualizada para **3.1.9**
- Garante compatibilidade com novas funcionalidades backend

---

## 🔧 Correções Técnicas

### Queries SQL
- Remoção de multiplicação duplicada por 100 em campos percentuais de exportação
- Queries de tela web e exportação agora com formatações distintas e corretas

### URLs
- Padronização de rotas em `urls_apis.py`, `urls_portais.py`, `urls_pos.py`
- Melhor organização de endpoints

### Documentação
- `ARQUITETURA.md` atualizado com novas estruturas
- `DIRETRIZES.md` refinado
- `producao.md` com comandos de deployment atualizados

---

## 📦 Arquivos Modificados

### Core
- `services/core/wallclub_core/estr_organizacional/loja.py`
- `services/core/wallclub_core/utilitarios/export_utils.py`

### Django Apps
- `services/django/apps/cliente/views_login_biometrico.py`
- `services/django/apps/views.py`
- `services/django/checkout/models.py`
- `services/django/checkout/services.py`

### Portal Lojista
- `services/django/portais/lojista/services_recebimentos.py`
- `services/django/portais/lojista/views_conciliacao.py`
- `services/django/portais/lojista/views_recebimentos.py`
- `services/django/portais/lojista/views_cancelamentos.py`
- `services/django/portais/lojista/views_vendas.py`
- `services/django/portais/lojista/templates/portais/lojista/conciliacao.html`
- `services/django/portais/lojista/templates/portais/lojista/recebimentos_por_loja.html`

### Portal Vendas
- `services/django/portais/vendas/services.py`
- `services/django/portais/vendas/views.py`
- `services/django/portais/vendas/templates/vendas/checkout_resultado.html`
- `services/django/portais/vendas/templates/vendas/cliente_editar.html`
- `services/django/portais/vendas/templates/vendas/cliente_form.html`

### Pinbank
- `services/django/pinbank/services_transacoes_pagamento.py`

### Monitoramento
- `monitoring/urls.py`
- `monitoring/grafana/dashboards/wallclub-django.json`
- `monitoring/prometheus.yml`

### Documentação
- `docs/ARQUITETURA.md`
- `docs/DIRETRIZES.md`
- `docs/deployment/producao.md`
- `docs/releases/RELEASE_v2.2.1.md`

---

## 🚀 Deploy

### Comandos de Deploy (Produção)

```bash
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.124
cd /var/www/WallClub_backend
git pull origin release-2.2.2
docker-compose build wallclub-portais
docker-compose stop wallclub-portais
docker-compose up -d wallclub-portais

# Verificar
docker ps
docker logs wallclub-portais --tail 50
```

### Comandos de Deploy (Desenvolvimento)

```bash
docker exec wallclub-redis redis-cli FLUSHALL
docker-compose down
docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

---

## ✅ Checklist de Validação Pós-Deploy

### Portal Lojista
1. Acessar Conciliação
2. Testar filtros de data de transação e pagamento
3. Exportar relatório em Excel - validar nomes de colunas e percentuais
4. Exportar relatório em CSV - validar formato decimal de percentuais (4 casas)
5. Exportar relatório em PDF - validar layout e formatação
6. Acessar Recebimentos por Loja
7. Validar totalizadores e separação de valores

### Checkout
1. Realizar cadastro de novo cliente
2. Validar campos de endereço desmembrados
3. Verificar campo data_nascimento em busca

### Monitoramento
1. Acessar endpoint `/metrics`
2. Verificar coleta Prometheus
3. Validar dashboards Grafana

---

## 📞 Suporte

Em caso de problemas:
1. Verificar logs em `/var/log/wallclub/`
2. Consultar documentação em `docs/`
3. Verificar dashboards do Grafana
4. Contatar equipe de desenvolvimento
