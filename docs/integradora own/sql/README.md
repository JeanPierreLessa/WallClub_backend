# Scripts SQL - Integração Own Financial

## 📋 Ordem de Execução

Execute os scripts na seguinte ordem:

### 1️⃣ Criação de Tabelas
```bash
# 1. Criar tabela loja_own
mysql -u wclub -p wclub < 001_create_table_loja_own.sql

# 2. Criar tabela loja_pinbank
mysql -u wclub -p wclub < 002_create_table_loja_pinbank.sql

# 3. Criar tabela loja_own_tarifacao
mysql -u wclub -p wclub < 006_create_table_loja_own_tarifacao.sql

# 4. Criar tabela loja_documentos
mysql -u wclub -p wclub < 007_create_table_loja_documentos.sql
```

### 2️⃣ Migração de Dados
```bash
# 5. Migrar dados bancários (numerobanco -> codigo_banco, conta -> numero_conta + digito_conta)
mysql -u wclub -p wclub < 003_migrate_dados_bancarios.sql

# 6. Migrar dados Pinbank para nova tabela
mysql -u wclub -p wclub < 004_migrate_dados_pinbank.sql
```

### 3️⃣ Deprecação de Colunas Antigas
```bash
# 7. Deprecar colunas antigas (adiciona prefixo DEPRECATED_)
mysql -u wclub -p wclub < 005_deprecate_colunas_antigas.sql
```

---

## 📊 Estrutura de Tabelas Criadas

### `loja_own`
Armazena dados específicos da integração com Own Financial.

**Campos principais:**
- `cadastrar`: Indica se deve cadastrar na Own
- `conveniada_id`: ID do estabelecimento na Own
- `status_credenciamento`: PENDENTE, APROVADO, REPROVADO, PROCESSANDO
- `protocolo`: Protocolo de cadastro
- `id_cesta`: ID da cesta de tarifas

### `loja_pinbank`
Armazena dados específicos da integração com Pinbank.

**Campos principais:**
- `codigo_canal`: Código do canal Pinbank
- `codigo_cliente`: Código do cliente Pinbank
- `key_value_loja`: Chave de identificação

### `loja_own_tarifacao`
Armazena tarifas da cesta Own associadas à loja.

**Campos principais:**
- `loja_own_id`: FK para loja_own
- `cesta_valor_id`: ID da tarifa na cesta Own
- `valor`: Valor da tarifa

### `loja_documentos`
Armazena documentos da loja e sócios.

**Campos principais:**
- `tipo_documento`: CONTRATO_SOCIAL, COMPROVANTE_ENDERECO, CARTAO_CNPJ, RGFRENTE, RGVERSO
- `caminho_arquivo`: Caminho no S3
- `cpf_socio`: CPF do sócio (para docs pessoais)

---

## 🔄 Migração de Dados

### Dados Bancários
- `numerobanco` → `codigo_banco` (padronizado com 3 dígitos)
- `conta` → `numero_conta` + `digito_conta` (separado)
- `nomebanco` → mantido temporariamente como DEPRECATED

### Dados Pinbank
- `pinbank_CodigoCanal` → `loja_pinbank.codigo_canal`
- `pinbank_CodigoCliente` → `loja_pinbank.codigo_cliente`
- `pinbank_KeyValueLoja` → `loja_pinbank.key_value_loja`

---

## ⚠️ Colunas Deprecadas

As seguintes colunas foram renomeadas com prefixo `DEPRECATED_`:

### Não Utilizadas
- `DEPRECATED_senha` - Autenticação via conta_digital
- `DEPRECATED_cod_cliente` - Não utilizada
- `DEPRECATED_aceite` - Não utilizada

### Substituídas
- `DEPRECATED_nomebanco` → Substituída por `codigo_banco`
- `DEPRECATED_numerobanco` → Substituída por `codigo_banco`
- `DEPRECATED_conta` → Substituída por `numero_conta` + `digito_conta`

### Migradas
- `DEPRECATED_pinbank_CodigoCanal` → Migrada para `loja_pinbank`
- `DEPRECATED_pinbank_CodigoCliente` → Migrada para `loja_pinbank`
- `DEPRECATED_pinbank_KeyValueLoja` → Migrada para `loja_pinbank`

**Nota:** As colunas deprecated podem ser removidas fisicamente após validação em produção (mínimo 3 meses).

---

## ✅ Validação

Após executar os scripts, validar:

```sql
-- 1. Verificar tabelas criadas
SHOW TABLES LIKE 'loja_%';

-- 2. Verificar migração de dados bancários
SELECT
    COUNT(*) AS total,
    SUM(CASE WHEN codigo_banco IS NOT NULL THEN 1 ELSE 0 END) AS com_codigo_banco,
    SUM(CASE WHEN numero_conta IS NOT NULL THEN 1 ELSE 0 END) AS com_numero_conta
FROM loja;

-- 3. Verificar migração Pinbank
SELECT COUNT(*) FROM loja_pinbank;

-- 4. Verificar colunas deprecated
SELECT COLUMN_NAME
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wclub'
  AND TABLE_NAME = 'loja'
  AND COLUMN_NAME LIKE 'DEPRECATED_%';
```

---

## 🔙 Rollback (se necessário)

Caso precise reverter as alterações:

```sql
-- Remover tabelas criadas
DROP TABLE IF EXISTS loja_own_tarifacao;
DROP TABLE IF EXISTS loja_documentos;
DROP TABLE IF EXISTS loja_own;
DROP TABLE IF EXISTS loja_pinbank;

-- Reverter nomes de colunas deprecated
ALTER TABLE loja CHANGE COLUMN DEPRECATED_senha senha VARCHAR(256) NULL;
ALTER TABLE loja CHANGE COLUMN DEPRECATED_cod_cliente cod_cliente VARCHAR(256) NULL;
-- ... (continuar para todas as colunas)
```

**⚠️ IMPORTANTE:** Fazer backup completo antes de executar qualquer script!
