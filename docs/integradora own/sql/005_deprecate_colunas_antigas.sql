-- =====================================================
-- Script: Deprecação de Colunas Antigas
-- Descrição: Renomeia colunas antigas adicionando prefixo DEPRECATED_
-- Data: 2026-01-13
-- IMPORTANTE: Executar APÓS migração de dados (scripts 003 e 004)
-- =====================================================

-- =====================================================
-- ANÁLISE: Colunas a deprecar
-- =====================================================
-- senha -> não utilizada (autenticação via conta_digital)
-- cod_cliente -> não utilizada
-- aceite -> não utilizada
-- nomebanco -> substituída por codigo_banco
-- numerobanco -> substituída por codigo_banco
-- conta -> substituída por numero_conta + digito_conta
-- pinbank_CodigoCanal -> migrada para loja_pinbank
-- pinbank_CodigoCliente -> migrada para loja_pinbank
-- pinbank_KeyValueLoja -> migrada para loja_pinbank

-- =====================================================
-- PASSO 1: Renomear colunas (adicionar prefixo DEPRECATED_)
-- =====================================================

-- Colunas não utilizadas
ALTER TABLE loja CHANGE COLUMN senha DEPRECATED_senha VARCHAR(256) NULL;
ALTER TABLE loja CHANGE COLUMN cod_cliente DEPRECATED_cod_cliente VARCHAR(256) NULL;
ALTER TABLE loja CHANGE COLUMN aceite DEPRECATED_aceite INT NOT NULL DEFAULT 0;

-- Colunas bancárias antigas (substituídas)
ALTER TABLE loja CHANGE COLUMN nomebanco DEPRECATED_nomebanco VARCHAR(256) NULL;
ALTER TABLE loja CHANGE COLUMN numerobanco DEPRECATED_numerobanco VARCHAR(256) NULL;
ALTER TABLE loja CHANGE COLUMN conta DEPRECATED_conta VARCHAR(256) NULL;

-- Colunas Pinbank (migradas para loja_pinbank)
ALTER TABLE loja CHANGE COLUMN pinbank_CodigoCanal DEPRECATED_pinbank_CodigoCanal INT NULL;
ALTER TABLE loja CHANGE COLUMN pinbank_CodigoCliente DEPRECATED_pinbank_CodigoCliente INT NULL;
ALTER TABLE loja CHANGE COLUMN pinbank_KeyValueLoja DEPRECATED_pinbank_KeyValueLoja VARCHAR(20) NULL;

-- =====================================================
-- PASSO 2: Remover índices das colunas deprecated
-- =====================================================

-- Verificar índices existentes antes de remover
-- SELECT * FROM information_schema.statistics
-- WHERE table_schema = 'wclub'
-- AND table_name = 'loja'
-- AND column_name IN ('cod_cliente', 'pinbank_CodigoCanal', 'pinbank_KeyValueLoja');

-- Remover índices se existirem
DROP INDEX IF EXISTS idx_loja_cod_cliente ON loja;
DROP INDEX IF EXISTS idx_loja_pinbank_CodigoCanal ON loja;
DROP INDEX IF EXISTS idx_loja_pinbank_KeyValueLoja ON loja;

-- =====================================================
-- PASSO 3: Adicionar comentários explicativos
-- =====================================================

ALTER TABLE loja MODIFY COLUMN DEPRECATED_senha VARCHAR(256) NULL
    COMMENT 'DEPRECATED: Não utilizada - autenticação via conta_digital';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_cod_cliente VARCHAR(256) NULL
    COMMENT 'DEPRECATED: Não utilizada';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_aceite INT NOT NULL DEFAULT 0
    COMMENT 'DEPRECATED: Não utilizada';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_nomebanco VARCHAR(256) NULL
    COMMENT 'DEPRECATED: Substituída por codigo_banco';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_numerobanco VARCHAR(256) NULL
    COMMENT 'DEPRECATED: Substituída por codigo_banco';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_conta VARCHAR(256) NULL
    COMMENT 'DEPRECATED: Substituída por numero_conta + digito_conta';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_pinbank_CodigoCanal INT NULL
    COMMENT 'DEPRECATED: Migrada para tabela loja_pinbank';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_pinbank_CodigoCliente INT NULL
    COMMENT 'DEPRECATED: Migrada para tabela loja_pinbank';

ALTER TABLE loja MODIFY COLUMN DEPRECATED_pinbank_KeyValueLoja VARCHAR(20) NULL
    COMMENT 'DEPRECATED: Migrada para tabela loja_pinbank';

-- =====================================================
-- PASSO 4: Relatório de colunas deprecated
-- =====================================================

SELECT
    COLUMN_NAME,
    COLUMN_TYPE,
    IS_NULLABLE,
    COLUMN_COMMENT
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wclub'
  AND TABLE_NAME = 'loja'
  AND COLUMN_NAME LIKE 'DEPRECATED_%'
ORDER BY COLUMN_NAME;

-- =====================================================
-- NOTA: Remoção física das colunas
-- =====================================================
-- As colunas deprecated podem ser removidas fisicamente após:
-- 1. Validação em produção (mínimo 3 meses)
-- 2. Confirmação de que nenhum código as utiliza
-- 3. Backup completo do banco de dados
--
-- Comando para remoção futura (NÃO EXECUTAR AGORA):
-- ALTER TABLE loja
--     DROP COLUMN DEPRECATED_senha,
--     DROP COLUMN DEPRECATED_cod_cliente,
--     DROP COLUMN DEPRECATED_aceite,
--     DROP COLUMN DEPRECATED_nomebanco,
--     DROP COLUMN DEPRECATED_numerobanco,
--     DROP COLUMN DEPRECATED_conta,
--     DROP COLUMN DEPRECATED_pinbank_CodigoCanal,
--     DROP COLUMN DEPRECATED_pinbank_CodigoCliente,
--     DROP COLUMN DEPRECATED_pinbank_KeyValueLoja;
