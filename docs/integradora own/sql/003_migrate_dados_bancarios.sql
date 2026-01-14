-- =====================================================
-- Script: Migração de Dados Bancários
-- Descrição: Migra dados das colunas antigas para as novas colunas padronizadas
-- Data: 2026-01-13
-- =====================================================

-- =====================================================
-- PASSO 1: Migrar dados de 'numerobanco' para 'codigo_banco'
-- =====================================================
UPDATE loja
SET codigo_banco = LPAD(numerobanco, 3, '0')
WHERE numerobanco IS NOT NULL
  AND numerobanco != ''
  AND codigo_banco IS NULL;

-- =====================================================
-- PASSO 2: Migrar dados de 'conta' para 'numero_conta' e 'digito_conta'
-- Assumindo formato: "123456-7" ou "123456"
-- =====================================================

-- Migrar número da conta (parte antes do hífen ou tudo se não houver hífen)
UPDATE loja
SET numero_conta = CASE
    WHEN conta LIKE '%-%' THEN SUBSTRING_INDEX(conta, '-', 1)
    ELSE conta
END
WHERE conta IS NOT NULL
  AND conta != ''
  AND numero_conta IS NULL;

-- Migrar dígito da conta (parte depois do hífen, se existir)
UPDATE loja
SET digito_conta = CASE
    WHEN conta LIKE '%-%' THEN SUBSTRING_INDEX(conta, '-', -1)
    ELSE NULL
END
WHERE conta IS NOT NULL
  AND conta != ''
  AND conta LIKE '%-%'
  AND digito_conta IS NULL;

-- =====================================================
-- PASSO 3: Verificar dados migrados
-- =====================================================

-- Relatório de migração
SELECT
    'Dados Bancários Migrados' AS status,
    COUNT(*) AS total_lojas,
    SUM(CASE WHEN codigo_banco IS NOT NULL THEN 1 ELSE 0 END) AS com_codigo_banco,
    SUM(CASE WHEN numero_conta IS NOT NULL THEN 1 ELSE 0 END) AS com_numero_conta,
    SUM(CASE WHEN digito_conta IS NOT NULL THEN 1 ELSE 0 END) AS com_digito_conta
FROM loja;

-- Lojas com dados antigos mas sem migração (possíveis problemas)
SELECT
    id,
    cnpj,
    razao_social,
    numerobanco,
    codigo_banco,
    conta,
    numero_conta,
    digito_conta
FROM loja
WHERE (
    (numerobanco IS NOT NULL AND numerobanco != '' AND codigo_banco IS NULL)
    OR
    (conta IS NOT NULL AND conta != '' AND numero_conta IS NULL)
)
LIMIT 10;
