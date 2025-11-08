# Changelog - 07/11/2025

## Portal de Vendas - Melhorias e Correções

### ✅ Sistema de Primeiro Acesso
- **Implementado:** Sistema de primeiro acesso com link único para vendedores
- **Rota:** `https://wcvendas.wallclub.com.br/primeiro_acesso/<token>/`
- **Funcionalidade:** 
  - Link único gerado pelo admin
  - Vendedor define senha no primeiro acesso
  - Token expira após uso ou 24h
  - Validação de força de senha

### ✅ Correções de Bugs

#### 1. Import datetime faltando
- **Arquivo:** `portais/vendas/views.py`
- **Problema:** `NameError: name 'datetime' is not defined`
- **Solução:** Adicionado `from datetime import datetime` no topo do arquivo

#### 2. Busca de clientes não funcionando
- **Arquivo:** `portais/vendas/services.py`
- **Problema:** `App 'link_pagamento_web' doesn't have a 'CheckoutClienteTelefone' model`
- **Solução:** Alterado import de `apps.get_model()` para import direto:
  ```python
  from checkout.link_pagamento_web.models_2fa import CheckoutClienteTelefone
  ```

### ✅ Configuração de Domínio Checkout

#### 1. URL de Link de Pagamento
- **Arquivo:** `checkout/services.py`
- **Alteração:** URL do link de pagamento corrigida
- **Antes:** `https://wcadmin.wallclub.com.br/api/v1/checkout/?token=...`
- **Depois:** `https://checkout.wallclub.com.br/api/v1/checkout/?token=...`

#### 2. ALLOWED_HOSTS
- **Arquivo:** `services/django/.env` (produção)
- **Adicionado:** `checkout.wallclub.com.br`
- **Linha:** `ALLOWED_HOSTS=...,checkout.wallclub.com.br`

#### 3. Nginx
- **Arquivo:** `nginx.conf`
- **Status:** Já estava configurado corretamente
- **Domínios:** `checkout.wallclub.com.br` e `wccheckout.wallclub.com.br`
- **Backend:** `wallclub-apis:8007`

### ⏳ Em Investigação

#### Erro "Erro interno" na página de checkout
- **Status:** Em andamento
- **Ação tomada:** Adicionado traceback completo no log
- **Arquivo:** `checkout/link_pagamento_web/views.py`
- **Próximo passo:** Aguardando novo teste para ver erro detalhado

## Commits Realizados
1. `feat: adicionar sistema de primeiro acesso para portal vendas`
2. `fix: adicionar import datetime em primeiro_acesso_view do portal vendas`
3. `fix: importar CheckoutClienteTelefone diretamente do módulo`
4. `fix: usar domínio checkout.wallclub.com.br para links de pagamento`
5. `fix: adicionar checkout.wallclub.com.br ao ALLOWED_HOSTS`
6. `fix: corrigir URL checkout e ALLOWED_HOSTS`
7. `debug: adicionar traceback completo no erro do checkout`

## Arquivos Modificados
- `services/django/portais/vendas/views.py`
- `services/django/portais/vendas/services.py`
- `services/django/portais/vendas/urls.py`
- `services/django/portais/vendas/templates/vendas/primeiro_acesso.html`
- `services/django/checkout/services.py`
- `services/django/checkout/link_pagamento_web/views.py`
- `services/django/.env.production`
- `docs/em execucao/Tarefas.md`

## Deploy
- **Branch:** `v2.0.0`
- **Containers atualizados:** `wallclub-portais`, `wallclub-apis`
- **Servidor:** Produção (10.0.1.124)
