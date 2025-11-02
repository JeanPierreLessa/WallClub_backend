-- Script para migrar dados da tabela financeiro para pagamentos_efetuados
-- Converte estrutura campo/valor para campos específicos (var44, var45, etc.)

-- Limpar tabela de destino (se necessário)
-- TRUNCATE TABLE pagamentos_efetuados;

-- Inserir dados convertidos da tabela financeiro para pagamentos_efetuados
INSERT INTO pagamentos_efetuados (
    nsu, 
    var44, var45, var58, var59, var66, var71, var100, var111, var112,
    created_at, 
    user_id
)
SELECT 
    CAST(nsu AS UNSIGNED) as nsu,
    -- var44: campo 44 (DECIMAL)
    CASE 
        WHEN (SELECT valor FROM wclub.financeiro f44 WHERE f44.nsu = f.nsu AND f44.campo = 44 LIMIT 1) = '' THEN NULL
        ELSE CAST((SELECT valor FROM wclub.financeiro  f44 WHERE f44.nsu = f.nsu AND f44.campo = 44 LIMIT 1) AS DECIMAL(8,2))
    END as var44,
    
    -- var45: campo 45 (VARCHAR)
    NULLIF((SELECT valor FROM wclub.financeiro  f45 WHERE f45.nsu = f.nsu AND f45.campo = 45 LIMIT 1), '') as var45,
    
    -- var58: campo 58 (DECIMAL)
    CASE 
        WHEN (SELECT valor FROM wclub.financeiro  f58 WHERE f58.nsu = f.nsu AND f58.campo = 58 LIMIT 1) = '' THEN NULL
        ELSE CAST((SELECT valor FROM wclub.financeiro  f58 WHERE f58.nsu = f.nsu AND f58.campo = 58 LIMIT 1) AS DECIMAL(8,2))
    END as var58,
    
    -- var59: campo 59 (VARCHAR)
    NULLIF((SELECT valor FROM wclub.financeiro  f59 WHERE f59.nsu = f.nsu AND f59.campo = 59 LIMIT 1), '') as var59,
    
    -- var66: campo 66 (VARCHAR)
    NULLIF((SELECT valor FROM wclub.financeiro  f66 WHERE f66.nsu = f.nsu AND f66.campo = 66 LIMIT 1), '') as var66,
    
    -- var71: campo 71 (VARCHAR)
    NULLIF((SELECT valor FROM wclub.financeiro  f71 WHERE f71.nsu = f.nsu AND f71.campo = 71 LIMIT 1), '') as var71,
    
    -- var100: campo 100 (VARCHAR)
    NULLIF((SELECT valor FROM wclub.financeiro  f100 WHERE f100.nsu = f.nsu AND f100.campo = 100 LIMIT 1), '') as var100,
    
    -- var111: campo 111 (DECIMAL)
    CASE 
        WHEN (SELECT valor FROM wclub.financeiro  f111 WHERE f111.nsu = f.nsu AND f111.campo = 111 LIMIT 1) = '' THEN NULL
        ELSE CAST((SELECT valor FROM wclub.financeiro  f111 WHERE f111.nsu = f.nsu AND f111.campo = 111 LIMIT 1) AS DECIMAL(8,2))
    END as var111,
    
    -- var112: campo 112 (DECIMAL)
    CASE 
        WHEN (SELECT valor FROM wclub.financeiro  f112 WHERE f112.nsu = f.nsu AND f112.campo = 112 LIMIT 1) = '' THEN NULL
        ELSE CAST((SELECT valor FROM wclub.financeiro  f112 WHERE f112.nsu = f.nsu AND f112.campo = 112 LIMIT 1) AS DECIMAL(8,2))
    END as var112,
    
    -- Timestamps
    NOW() as created_at,
    
    -- User padrão (ajustar conforme necessário)
    1 as user_id
    
FROM (
    SELECT DISTINCT nsu 
    FROM wclub.financeiro 
    WHERE campo IN (44, 45, 58, 59, 66, 71, 100, 111, 112)
    AND nsu IS NOT NULL 
    AND nsu != ''
    AND nsu REGEXP '^[0-9]+$'
    AND NOT EXISTS ( 
        SELECT 1 
        FROM   wallclub.pagamentos_efetuados pe 
        WHERE pe.nsu = financeiro.nsu
    )
) f;

-- Verificar resultado
SELECT 
    COUNT(*) as total_registros,
    COUNT(DISTINCT nsu) as nsus_unicos,
    COUNT(var44) as var44_preenchidos,
    COUNT(var45) as var45_preenchidos,
    COUNT(var58) as var58_preenchidos,
    COUNT(var59) as var59_preenchidos,
    COUNT(var66) as var66_preenchidos,
    COUNT(var71) as var71_preenchidos,
    COUNT(var100) as var100_preenchidos,
    COUNT(var111) as var111_preenchidos,
    COUNT(var112) as var112_preenchidos
FROM pagamentos_efetuados;

-- Verificar alguns exemplos
SELECT nsu, var44, var45, var58, var59, var66, var71, var100, var111_A, var112
FROM pagamentos_efetuados 
LIMIT 10;
