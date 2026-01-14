-- =====================================================
-- Script: Migração de Dados Pinbank
-- Descrição: Migra dados das colunas antigas da tabela loja para loja_pinbank
-- Data: 2026-01-13
-- =====================================================

-- =====================================================
-- PASSO 1: Inserir dados na tabela loja_pinbank
-- =====================================================
INSERT INTO loja_pinbank (
    loja_id,
    codigo_canal,
    codigo_cliente,
    key_value_loja,
    ativo,
    created_at,
    updated_at
)
SELECT
    id AS loja_id,
    pinbank_CodigoCanal AS codigo_canal,
    pinbank_CodigoCliente AS codigo_cliente,
    pinbank_KeyValueLoja AS key_value_loja,
    TRUE AS ativo,
    created_at,
    NOW() AS updated_at
FROM loja
WHERE (
    pinbank_CodigoCanal IS NOT NULL
    OR pinbank_CodigoCliente IS NOT NULL
    OR pinbank_KeyValueLoja IS NOT NULL
)
AND NOT EXISTS (
    SELECT 1 FROM loja_pinbank WHERE loja_pinbank.loja_id = loja.id
);

-- =====================================================
-- PASSO 2: Verificar migração
-- =====================================================
SELECT
    'Dados Pinbank Migrados' AS status,
    COUNT(*) AS total_registros_migrados
FROM loja_pinbank;

-- Comparar dados originais vs migrados
SELECT
    l.id,
    l.cnpj,
    l.razao_social,
    l.pinbank_CodigoCanal AS original_codigo_canal,
    lp.codigo_canal AS novo_codigo_canal,
    l.pinbank_CodigoCliente AS original_codigo_cliente,
    lp.codigo_cliente AS novo_codigo_cliente,
    l.pinbank_KeyValueLoja AS original_key_value,
    lp.key_value_loja AS novo_key_value
FROM loja l
LEFT JOIN loja_pinbank lp ON l.id = lp.loja_id
WHERE (
    l.pinbank_CodigoCanal IS NOT NULL
    OR l.pinbank_CodigoCliente IS NOT NULL
    OR l.pinbank_KeyValueLoja IS NOT NULL
)
LIMIT 10;
