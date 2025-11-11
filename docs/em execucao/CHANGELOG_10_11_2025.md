# Changelog - 10/11/2025

## Gestão Admin - Filtro por Tipo de Transação

### Contexto
Necessidade de separar transações do sistema Wallet das transações da Credenciadora (TEF) nos relatórios administrativos.

### Alterações Implementadas

#### 1. Campo `tipo_operacao` como Primeira Coluna
**Arquivos modificados:**
- `services/django/portais/admin/utils/column_mappings.py`
- `services/django/portais/admin/views_transacoes.py`
- `services/django/portais/admin/views_rpr.py`

**Mudanças:**
- Adicionado `"tipo_operacao": "Tipo de Transação"` no mapeamento de colunas
- Campo `tipo_operacao` incluído como primeira coluna em:
  - Tabela HTML (Gestão Admin e RPR)
  - Export Excel
  - Export CSV
  - Export CSV em background

**Valores possíveis:**
- `Wallet` - Transações do sistema Wallet
- `Credenciadora` - Transações da credenciadora/TEF

#### 2. Filtro "Incluir transações Credenciadora"
**Arquivos modificados:**
- `services/django/portais/admin/views_transacoes.py`
- `services/django/portais/admin/templates/portais/admin/base_transacoes_gestao.html`
- `services/django/portais/admin/views_rpr.py`
- `services/django/portais/admin/templates/portais/admin/relatorio_producao_receita.html`
- `services/django/portais/admin/services_rpr.py`

**Comportamento:**
- **Checkbox desmarcado (padrão):** Mostra apenas `tipo_operacao = 'Wallet'`
- **Checkbox marcado:** Mostra ambos (`Wallet` + `Credenciadora`)

**Implementação:**
```python
# Filtro tipo_operacao (Credenciadora/Wallet)
if not filtros.get('incluir_tef'):
    where_conditions.append("tipo_operacao = 'Wallet'")
```

#### 3. App `pinbank` no Container Portais
**Arquivo modificado:**
- `services/django/wallclub/settings/portais.py`

**Mudança:**
```python
INSTALLED_APPS = [
    # ... outros apps
    'pinbank',  # Para acesso aos modelos de transações
]
```

**Motivo:**
- Funções de export usam ORM Django com modelo `BaseTransacoesGestao`
- Modelo está no app `pinbank`
- Sem o app no INSTALLED_APPS, ocorria erro: `No installed app with label 'pinbank'`

**Import atualizado:**
```python
# Antes (causava erro)
BaseTransacoesGestao = apps.get_model('pinbank', 'BaseTransacoesGestao')

# Depois (funciona)
from pinbank.models import BaseTransacoesGestao
```

## Exports Excel - Remoção de Linhas Inúteis

### Contexto
Arquivos Excel exportados tinham 2 linhas inúteis antes dos dados:
- Linha 1: Título (ex: "Transacoes Gestao")
- Linha 2: (vazia)
- Linha 3: Cabeçalhos
- Linha 4+: Dados

### Alterações Implementadas

**Arquivo modificado:**
- `services/core/wallclub_core/utilitarios/export_utils.py`

**Funções atualizadas:**
- `exportar_excel()`
- `criar_excel_em_arquivo()`

**Mudança:**
```python
# Antes
linha_atual = 1
if titulo:
    ws.merge_cells(f'A1:{get_column_letter(len(dados[0]))}1')
    ws['A1'] = titulo
    ws['A1'].font = Font(bold=True, size=16)
    ws['A1'].alignment = Alignment(horizontal="center")
    linha_atual = 3

# Depois
# Cabeçalhos começam na linha 1 (sem título)
linha_atual = 1
```

**Resultado:**
- Linha 1: Cabeçalhos
- Linha 2+: Dados

## RPR - Alinhamento de Filtros JavaScript

### Contexto
Tabela AJAX do RPR estava trazendo todas as transações (sem filtro de data) quando a página carregava, enquanto os cards de métricas usavam filtros padrão (mês corrente).

### Problema Identificado
```javascript
// Antes (pegava da URL - vazios na primeira carga)
filtrosAtuais = {
    data_inicial: urlParams.get('data_inicial') || '',
    data_final: urlParams.get('data_final') || '',
    incluir_tef: urlParams.get('incluir_tef') || '',  // String vazia
};
```

**Logs mostravam:**
```
[INFO] RPR - Filtros aplicados: {'data_inicial': '', 'data_final': '', 'incluir_tef': True}
[INFO] RPR - Total de registros encontrados: 19091  # Todas as transações!
```

### Alterações Implementadas

**Arquivo modificado:**
- `services/django/portais/admin/templates/portais/admin/relatorio_producao_receita.html`

**Mudança:**
```javascript
// Depois (pega dos inputs do formulário - já vêm preenchidos do servidor)
filtrosAtuais = {
    data_inicial: document.getElementById('data_inicial').value || '',
    data_final: document.getElementById('data_final').value || '',
    canal: document.getElementById('canal').value || '',
    loja: document.getElementById('loja').value || '',
    incluir_tef: document.getElementById('incluir_tef').checked ? '1' : '0',
    nsu: ''
};
```

**Resultado:**
- Tabela AJAX usa mesmos filtros que os cards (primeiro dia do mês até hoje)
- Checkbox `incluir_tef` corretamente interpretado como boolean

## Arquivos Modificados

### Core (wallclub_core)
- `services/core/wallclub_core/utilitarios/export_utils.py`

### Django - Portais Admin
- `services/django/wallclub/settings/portais.py`
- `services/django/portais/admin/utils/column_mappings.py`
- `services/django/portais/admin/views_transacoes.py`
- `services/django/portais/admin/views_rpr.py`
- `services/django/portais/admin/services_rpr.py`
- `services/django/portais/admin/templates/portais/admin/base_transacoes_gestao.html`
- `services/django/portais/admin/templates/portais/admin/relatorio_producao_receita.html`

### Documentação
- `docs/em execucao/Tarefas.md`
- `README.md`

## Deploy Necessário

```bash
cd /var/www/WallClub_backend
git pull origin v2.0.0
docker-compose build wallclub-portais
docker-compose up -d wallclub-portais
```

**Nota:** Como `wallclub_core` foi alterado, o rebuild do container é obrigatório.

## Testes Recomendados

### Gestão Admin
1. ✅ Verificar coluna "Tipo de Transação" como primeira coluna
2. ✅ Testar checkbox "Incluir transações Credenciadora"
3. ✅ Exportar Excel e verificar que começa na linha 1
4. ✅ Exportar CSV e verificar coluna tipo_operacao

### RPR
1. ✅ Verificar coluna "Tipo de Transação" como primeira coluna
2. ✅ Testar checkbox "Incluir transações Credenciadora"
3. ✅ Verificar que tabela AJAX usa filtros de data corretos
4. ✅ Exportar Excel/CSV e verificar estrutura

## Observações

- Campo `tipo_operacao` já existia na tabela `baseTransacoesGestao`
- Apenas foi exposto nas views e exports
- Filtro padrão: apenas transações Wallet (comportamento mais comum)
- Usuário pode marcar checkbox para incluir Credenciadora quando necessário
