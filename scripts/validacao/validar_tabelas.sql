-- scripts/validacao/validar_tabelas.sql
-- Valida tabelas conforme documentação

-- Sistema de Ofertas (5 tabelas documentadas)
SELECT '=== SISTEMA DE OFERTAS ===' AS secao;

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

-- Sistema de Cashback (3 tabelas documentadas)
SELECT '=== SISTEMA DE CASHBACK ===' AS secao;

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

-- Tabela unificada transactiondata_pos
SELECT '=== TRANSACTIONDATA_POS (Unificada) ===' AS secao;

SELECT 'transactiondata_pos' AS tabela,
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS existe
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'wallclub' AND TABLE_NAME = 'transactiondata_pos';

-- Verificar campo 'gateway' (PINBANK/OWN)
SELECT 'Campo gateway existe?' AS validacao,
       CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END AS resultado
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_NAME = 'transactiondata_pos'
  AND COLUMN_NAME = 'gateway';

-- Parâmetros Financeiros
SELECT '=== PARÂMETROS FINANCEIROS ===' AS secao;

SELECT '3.840 configurações ativas' AS documentado,
       COUNT(*) AS real,
       CASE
           WHEN COUNT(*) >= 3800 AND COUNT(*) <= 3900 THEN '✅ OK'
           ELSE CONCAT('⚠️ Divergência: ', COUNT(*))
       END AS status
FROM parametros_loja
WHERE ativo = TRUE;

-- Terminais (campos DATETIME)
SELECT '=== TERMINAIS (DATETIME) ===' AS secao;

SELECT 'Campo inicio é DATETIME?' AS validacao,
       CASE WHEN DATA_TYPE = 'datetime' THEN '✅' ELSE CONCAT('⚠️ ', DATA_TYPE) END AS resultado
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_NAME = 'terminais'
  AND COLUMN_NAME = 'inicio';

SELECT 'Campo fim é DATETIME?' AS validacao,
       CASE WHEN DATA_TYPE = 'datetime' THEN '✅' ELSE CONCAT('⚠️ ', DATA_TYPE) END AS resultado
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_NAME = 'terminais'
  AND COLUMN_NAME = 'fim';

-- Collation
SELECT '=== COLLATION ===' AS secao;

SELECT 'Tabelas com collation diferente de utf8mb4_unicode_ci' AS validacao,
       COUNT(*) AS quantidade
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_COLLATION IS NOT NULL
  AND TABLE_COLLATION != 'utf8mb4_unicode_ci';
