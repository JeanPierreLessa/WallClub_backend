-- =====================================================
-- QUERIES DE VALIDAÇÃO: base_transacoes_unificadas
-- =====================================================
-- Executar após 2 dias de carga paralela
-- Data prevista: 12/12/2024
-- =====================================================

-- =====================================================
-- 1. CONTAGEM GERAL DE TRANSAÇÕES (NSU únicos)
-- =====================================================

-- Base antiga (baseTransacoesGestao)
SELECT 
    'baseTransacoesGestao' as base,
    COUNT(DISTINCT var9) as total_nsu,
    COUNT(*) as total_linhas,
    MIN(data_transacao) as data_inicio,
    MAX(data_transacao) as data_fim
FROM baseTransacoesGestao
WHERE data_transacao >= '2024-10-01';

-- Base nova (base_transacoes_unificadas)
SELECT 
    'base_transacoes_unificadas' as base,
    COUNT(DISTINCT var9) as total_nsu,
    COUNT(*) as total_linhas,
    MIN(data_transacao) as data_inicio,
    MAX(data_transacao) as data_fim
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-10-01';

-- Diferença (deve ser 0)
SELECT 
    (SELECT COUNT(DISTINCT var9) FROM baseTransacoesGestao WHERE data_transacao >= '2024-10-01') -
    (SELECT COUNT(DISTINCT var9) FROM base_transacoes_unificadas WHERE data_transacao >= '2024-10-01') 
    as diferenca_nsu;


-- =====================================================
-- 2. VALIDAÇÃO DE VALORES (SUM por período)
-- =====================================================

-- Base antiga - Totalizadores por dia
SELECT 
    'baseTransacoesGestao' as base,
    DATE(data_transacao) as data,
    COUNT(DISTINCT var9) as qtd_transacoes,
    SUM(DISTINCT var11) as total_valor_original,
    SUM(DISTINCT var16) as total_desconto,
    SUM(DISTINCT var20) as total_tarifas
FROM baseTransacoesGestao
WHERE data_transacao >= '2024-12-01'
GROUP BY DATE(data_transacao)
ORDER BY data DESC
LIMIT 10;

-- Base nova - Totalizadores por dia
SELECT 
    'base_transacoes_unificadas' as base,
    DATE(data_transacao) as data,
    COUNT(var9) as qtd_transacoes,
    SUM(var11) as total_valor_original,
    SUM(var16) as total_desconto,
    SUM(var20) as total_tarifas
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-12-01'
GROUP BY DATE(data_transacao)
ORDER BY data DESC
LIMIT 10;


-- =====================================================
-- 3. VALIDAÇÃO POR TIPO DE OPERAÇÃO
-- =====================================================

-- Base antiga
SELECT 
    'baseTransacoesGestao' as base,
    tipo_operacao,
    COUNT(DISTINCT var9) as qtd_transacoes
FROM baseTransacoesGestao
WHERE data_transacao >= '2024-12-01'
GROUP BY tipo_operacao;

-- Base nova
SELECT 
    'base_transacoes_unificadas' as base,
    tipo_operacao,
    COUNT(var9) as qtd_transacoes
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-12-01'
GROUP BY tipo_operacao;


-- =====================================================
-- 4. VALIDAÇÃO DE CAMPOS CRÍTICOS (sample)
-- =====================================================

-- Comparar 10 NSUs aleatórios
SELECT 
    bg.var9 as nsu,
    bg.var11 as bg_valor_original,
    btu.var11 as btu_valor_original,
    bg.var13 as bg_parcelas,
    btu.var13 as btu_parcelas,
    bg.var16 as bg_desconto,
    btu.var16 as btu_desconto,
    bg.var20 as bg_tarifas,
    btu.var20 as btu_tarifas,
    CASE 
        WHEN bg.var11 = btu.var11 AND bg.var13 = btu.var13 
             AND bg.var16 = btu.var16 AND bg.var20 = btu.var20 
        THEN 'OK' 
        ELSE 'DIVERGENTE' 
    END as status
FROM (
    SELECT DISTINCT var9, var11, var13, var16, var20
    FROM baseTransacoesGestao
    WHERE data_transacao >= '2024-12-01'
    LIMIT 10
) bg
LEFT JOIN base_transacoes_unificadas btu ON bg.var9 = btu.var9;


-- =====================================================
-- 5. VALIDAÇÃO DE CAMPOS NOVOS (gaps preenchidos)
-- =====================================================

-- Verificar se campos novos foram populados
SELECT 
    COUNT(*) as total,
    COUNT(card_number) as com_card_number,
    COUNT(authorization_code) as com_authorization_code,
    COUNT(amount) as com_amount,
    COUNT(valor_cashback) as com_valor_cashback,
    ROUND(COUNT(card_number) * 100.0 / COUNT(*), 2) as perc_card_number,
    ROUND(COUNT(authorization_code) * 100.0 / COUNT(*), 2) as perc_authorization_code
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-12-01';


-- =====================================================
-- 6. TRANSAÇÕES FALTANDO (NSUs na base antiga que não estão na nova)
-- =====================================================

SELECT 
    bg.var9 as nsu_faltando,
    bg.data_transacao,
    bg.tipo_operacao,
    bg.var11 as valor_original
FROM (
    SELECT DISTINCT var9, data_transacao, tipo_operacao, var11
    FROM baseTransacoesGestao
    WHERE data_transacao >= '2024-12-01'
) bg
LEFT JOIN base_transacoes_unificadas btu ON bg.var9 = btu.var9
WHERE btu.var9 IS NULL
LIMIT 20;


-- =====================================================
-- 7. TRANSAÇÕES EXTRAS (NSUs na base nova que não estão na antiga)
-- =====================================================

SELECT 
    btu.var9 as nsu_extra,
    btu.data_transacao,
    btu.tipo_operacao,
    btu.var11 as valor_original
FROM base_transacoes_unificadas btu
LEFT JOIN (
    SELECT DISTINCT var9
    FROM baseTransacoesGestao
    WHERE data_transacao >= '2024-12-01'
) bg ON btu.var9 = bg.var9
WHERE bg.var9 IS NULL
AND btu.data_transacao >= '2024-12-01'
LIMIT 20;


-- =====================================================
-- 8. VALIDAÇÃO DE PARCELAS (var13)
-- =====================================================

-- Verificar se var13 está correto (INT, não DECIMAL)
SELECT 
    var9,
    var13,
    CASE 
        WHEN var13 = FLOOR(var13) THEN 'OK'
        ELSE 'DECIMAL_INCORRETO'
    END as status_var13
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-12-01'
AND var13 != FLOOR(var13)
LIMIT 10;


-- =====================================================
-- 9. PERFORMANCE - Comparar tempo de execução
-- =====================================================

-- Query típica do portal (base antiga)
-- Executar e anotar tempo
SELECT 
    var9,
    var11,
    var13,
    data_transacao
FROM (
    SELECT 
        var9,
        var11,
        var13,
        data_transacao,
        ROW_NUMBER() OVER (PARTITION BY var9 ORDER BY id) as rn
    FROM baseTransacoesGestao
    WHERE data_transacao >= '2024-12-01'
) t
WHERE rn = 1
LIMIT 100;

-- Query equivalente (base nova)
-- Executar e anotar tempo
SELECT 
    var9,
    var11,
    var13,
    data_transacao
FROM base_transacoes_unificadas
WHERE data_transacao >= '2024-12-01'
LIMIT 100;


-- =====================================================
-- 10. RESUMO EXECUTIVO
-- =====================================================

SELECT 
    'RESUMO VALIDAÇÃO' as tipo,
    (SELECT COUNT(DISTINCT var9) FROM baseTransacoesGestao WHERE data_transacao >= '2024-12-01') as bg_total_nsu,
    (SELECT COUNT(DISTINCT var9) FROM base_transacoes_unificadas WHERE data_transacao >= '2024-12-01') as btu_total_nsu,
    (SELECT COUNT(DISTINCT var9) FROM baseTransacoesGestao WHERE data_transacao >= '2024-12-01') -
    (SELECT COUNT(DISTINCT var9) FROM base_transacoes_unificadas WHERE data_transacao >= '2024-12-01') as diferenca,
    CASE 
        WHEN (SELECT COUNT(DISTINCT var9) FROM baseTransacoesGestao WHERE data_transacao >= '2024-12-01') =
             (SELECT COUNT(DISTINCT var9) FROM base_transacoes_unificadas WHERE data_transacao >= '2024-12-01')
        THEN '✅ VALIDAÇÃO OK'
        ELSE '❌ DIVERGÊNCIA ENCONTRADA'
    END as status;
