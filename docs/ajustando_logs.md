# Ajustando Sistema de Logs - WallClub Backend

**Data:** 07/11/2025  
**Objetivo:** Padronizar e limpar sistema de logs do projeto

## 📋 Visão Geral

O sistema de logs foi refatorado para usar **processos únicos por módulo**, eliminando prefixos redundantes e subprocessos desnecessários.

## 🎯 Padrão Adotado

### Estrutura de Processos

```
apps.*              → APIs Mobile
  - apps.cliente
  - apps.conta_digital
  - apps.oauth
  - apps.ofertas
  - apps.transacoes

portais.*           → Portais Web
  - portais.admin
  - portais.controle_acesso
  - portais.lojista
  - portais.vendas

posp2               → Terminal POS
  - posp2
  - posp2.antifraude

comum.*             → Core (wallclub_core)
  - comum.oauth
```

### Níveis de Log

- **INFO** - Operações normais
- **WARNING** - Alertas (não bloqueiam operação)
- **ERROR** - Erros que precisam atenção
- **DEBUG** - Detalhes técnicos (apenas desenvolvimento)

## ✅ Módulos Ajustados

### 1. POSP2 (Terminal POS)

**Antes:**
```python
registrar_log('posp2', 'posp2.trdata - Iniciando processamento')
registrar_log('posp2', 'posp2.transaction_sync - Sincronizando')
```

**Depois:**
```python
registrar_log('posp2', 'Iniciando processamento')
registrar_log('posp2', 'Sincronizando')
```

**Arquivos alterados:**
- `services_transacao.py` - Removidos prefixos `posp2.trdata -` e `posp2.transaction_sync -`
- `services_conta_digital.py` - Limpeza de logs
- `services_sync.py` - Limpeza de logs

**Estrutura final:**
- `posp2` → `/app/logs/posp2.log`
- `posp2.antifraude` → `/app/logs/posp2antifraude.log`

---

### 2. Apps (APIs Mobile)

#### apps.cliente ✅
**Arquivos:** 8 arquivos
**Processo:** `apps.cliente`
**Status:** Correto, sem alterações necessárias

#### apps.conta_digital ✅
**Arquivos:** 7 arquivos (114 ocorrências)
**Processo:** `apps.conta_digital`
**Status:** Correto, sem alterações necessárias

#### apps.oauth ✅
**Processos:** 2 separados (correto!)
- `apps.oauth` - Endpoints de autenticação (geração de tokens)
- `comum.oauth` - Decorators e validação (middleware/segurança)

**Motivo:** Responsabilidades diferentes, facilita debug

#### apps.ofertas ✅
**Antes:** `apps.ofertas` + `ofertas.internal_api`
**Depois:** `apps.ofertas` (unificado)

**Arquivo alterado:**
- `views_internal_api.py` - 10 ocorrências unificadas

#### apps.transacoes ✅
**Arquivos:** 2 arquivos
**Processo:** `apps.transacoes`
**Status:** Correto, sem alterações necessárias

---

### 3. Portais (Web)

#### portais.admin ✅
**Antes:** `portais.admin` + `portais.admin.dispositivos`
**Depois:** `portais.admin` (unificado)

**Arquivo alterado:**
- `views_dispositivos.py` - 10 ocorrências unificadas

**Arquivos usando logs:**
- `views.py` (3 ocorrências)
- `services_terminais.py` (10 ocorrências)
- `views_grupos_segmentacao.py` (2 ocorrências)
- `views_dispositivos.py` (10 ocorrências)

#### portais.controle_acesso ✅
**Arquivos:** 3 arquivos (19 ocorrências)
**Processo:** `portais.controle_acesso`
**Status:** Correto, sem alterações necessárias

#### portais.corporativo ✅
**Status:** Sem logs (não usa `registrar_log`)

#### portais.lojista ✅
**Arquivos:** 5 arquivos
**Processo:** `portais.lojista`
**Status:** Correto, sem alterações necessárias

#### portais.vendas ✅
**Antes:** `portais.vendas` + `portais.vendas.recorrencia` + `portais.vendas.recorrencia.debug`
**Depois:** `portais.vendas` (unificado)

**Arquivo alterado:**
- `views_recorrencia.py` - 7 ocorrências unificadas

---

## 🗑️ Processos Removidos

Remover do banco de dados `log_parametros`:

```sql
DELETE FROM log_parametros WHERE processo IN (
    'ofertas.internal_api',
    'portais.admin.dispositivos',
    'portais.vendas.recorrencia',
    'portais.vendas.recorrencia.debug'
);
```

---

## 📁 Estrutura de Arquivos de Log

```
/app/logs/
├── apps.cliente.log
├── apps.conta_digital.log
├── apps.oauth.log
├── apps.ofertas.log
├── apps.transacoes.log
├── portais.admin.log
├── portais.controle_acesso.log
├── portais.lojista.log
├── portais.vendas.log
├── posp2.log
├── posp2antifraude.log
├── comum.oauth.log
└── auditoria.transacao.log
```

---

## 🔍 Como Usar

### Adicionar Log em Novo Módulo

```python
from wallclub_core.utilitarios.log_control import registrar_log

# Padrão: registrar_log('processo', 'mensagem', nivel='INFO')
registrar_log('apps.meu_modulo', 'Operação realizada com sucesso')
registrar_log('apps.meu_modulo', 'Erro ao processar', nivel='ERROR')
registrar_log('apps.meu_modulo', 'Detalhes técnicos', nivel='DEBUG')
```

### Configurar no Banco

```sql
INSERT INTO log_parametros (processo, ligado, nivel, arquivo_log, descricao)
VALUES ('apps.meu_modulo', 1, 'INFO', '/app/logs/apps.meu_modulo.log', 'Logs do meu módulo');
```

### Níveis Recomendados por Ambiente

| Ambiente | Nível Padrão | Observação |
|----------|--------------|------------|
| Desenvolvimento | DEBUG | Ver todos os detalhes |
| Homologação | INFO | Operações normais + erros |
| Produção | INFO | Apenas operações e erros |

---

## 📊 Estatísticas

### Antes da Refatoração
- Processos: ~20 (com subprocessos)
- Prefixos redundantes: Sim
- Arquivos de log: ~20

### Depois da Refatoração
- Processos: 13 (únicos por módulo)
- Prefixos redundantes: Não
- Arquivos de log: 13
- Redução: ~35%

---

## ✅ Checklist de Validação

- [x] POSP2 - Prefixos removidos
- [x] apps.cliente - Validado
- [x] apps.conta_digital - Validado
- [x] apps.oauth - Validado (2 processos corretos)
- [x] apps.ofertas - Unificado
- [x] apps.transacoes - Validado
- [x] portais.admin - Unificado
- [x] portais.controle_acesso - Validado
- [x] portais.lojista - Validado
- [x] portais.vendas - Unificado

---

## 🚀 Deploy

Após aplicar as mudanças:

1. **Commit das alterações**
```bash
git add .
git commit -m "refactor: padronizar sistema de logs (processo único por módulo)"
```

2. **Deploy**
```bash
cd /var/www/WallClub_backend
git pull origin main
docker-compose build --no-cache wallclub-portais wallclub-apis wallclub-pos
docker-compose up -d
```

3. **Limpar processos obsoletos do banco**
```sql
DELETE FROM log_parametros WHERE processo IN (
    'ofertas.internal_api',
    'portais.admin.dispositivos',
    'portais.vendas.recorrencia',
    'portais.vendas.recorrencia.debug'
);
```

4. **Verificar logs**
```bash
docker exec wallclub-portais ls -lh /app/logs/
docker logs wallclub-portais --tail 50
```

---

**Responsável:** Equipe WallClub  
**Última atualização:** 07/11/2025
