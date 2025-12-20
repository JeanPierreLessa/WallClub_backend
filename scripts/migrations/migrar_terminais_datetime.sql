-- =====================================================
-- MIGRAÇÃO: wclub.terminais → wallclub.terminais
-- Objetivo: Criar tabela real com DATETIME e ajustar datas de fim
-- Data: 2025-12-20
-- =====================================================

-- PASSO 1: Corrigir duplicatas em wclub.terminais
-- =====================================================
-- Terminal PBF9242F71873 tem 2 registros ativos idênticos (IDs 49 e 70)
-- Manter ID 49 (primeiro criado) e encerrar ID 70 (duplicata)

UPDATE wclub.terminais
SET fim = UNIX_TIMESTAMP(NOW())
WHERE id = 70;

-- backup
-- wallclub.terminais source

CREATE OR REPLACE
ALGORITHM = UNDEFINED VIEW `wallclub`.`terminais` AS
select
    `terminais`.`id` AS `id`,
    `terminais`.`id_cliente` AS `loja_id`,
    `terminais`.`terminal` AS `terminal`,
    `terminais`.`idterminal` AS `idterminal`,
    `terminais`.`endereco` AS `endereco`,
    `terminais`.`contato` AS `contato`,
    `terminais`.`inicio` AS `inicio`,
    `terminais`.`fim` AS `fim`
from
    `terminais`;

-- PASSO 2: Dropar view existente
-- =====================================================
DROP VIEW IF EXISTS wallclub.terminais;

-- PASSO 3: Criar tabela wallclub.terminais com estrutura correta
-- =====================================================
CREATE TABLE wallclub.terminais (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NULL,
    terminal VARCHAR(256) NULL,
    idterminal VARCHAR(256) NULL,
    endereco VARCHAR(1024) NULL,
    contato VARCHAR(256) NULL,
    inicio DATETIME NULL COMMENT 'Data/hora de início de uso do terminal',
    fim DATETIME NULL COMMENT 'Data/hora de encerramento do terminal',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_terminal (terminal),
    INDEX idx_loja_id (loja_id),
    INDEX idx_loja_terminal (loja_id, terminal),
    INDEX idx_loja_vigencia (loja_id, inicio, fim)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tabela de terminais POS - migrada de wclub.terminais em 2025-12-20';

-- PASSO 4: Migrar dados de wclub.terminais para wallclub.terminais
-- =====================================================
-- Converter Unix timestamp para DATETIME
-- Tratar casos especiais:
-- - inicio = 0 ou NULL → NULL
-- - fim = 0 ou NULL → NULL
-- - timestamps inválidos (ex: 20251113) → NULL

INSERT INTO wallclub.terminais (
    id,
    loja_id,
    terminal,
    idterminal,
    endereco,
    contato,
    inicio,
    fim
)
SELECT
    id,
    id_cliente AS loja_id,
    terminal,
    idterminal,
    endereco,
    contato,
    -- Converter inicio: apenas se >= 946684800 (2000-01-01) e <= 2147483647 (2038-01-19)
    CASE 
        WHEN inicio IS NULL OR inicio = 0 THEN NULL
        WHEN inicio >= 946684800 AND inicio <= 2147483647 THEN FROM_UNIXTIME(inicio)
        ELSE NULL
    END AS inicio,
    -- Converter fim: apenas se >= 946684800 (2000-01-01) e <= 2147483647 (2038-01-19)
    CASE 
        WHEN fim IS NULL OR fim = 0 THEN NULL
        WHEN fim >= 946684800 AND fim <= 2147483647 THEN FROM_UNIXTIME(fim)
        ELSE NULL
    END AS fim
FROM wclub.terminais
ORDER BY id;

-- PASSO 5: Validações e relatório
-- =====================================================

-- 5.1: Contar registros migrados
SELECT
    'MIGRAÇÃO CONCLUÍDA' AS status,
    COUNT(*) AS total_registros,
    SUM(CASE WHEN inicio IS NOT NULL THEN 1 ELSE 0 END) AS com_inicio,
    SUM(CASE WHEN fim IS NOT NULL THEN 1 ELSE 0 END) AS com_fim,
    SUM(CASE WHEN inicio IS NULL AND fim IS NULL THEN 1 ELSE 0 END) AS sem_datas
FROM wallclub.terminais;

-- 5.2: Verificar terminais ativos por loja
SELECT
    'TERMINAIS ATIVOS POR LOJA' AS relatorio,
    loja_id,
    COUNT(*) AS qtd_terminais_ativos
FROM wallclub.terminais
WHERE (fim IS NULL OR fim > NOW())
  AND inicio IS NOT NULL
GROUP BY loja_id
ORDER BY loja_id;

-- PASSO 6: Backup e limpeza (COMENTADO - executar manualmente após validação)
-- =====================================================

-- 6.1: Criar backup da tabela antiga (DESCOMENTAR APÓS VALIDAÇÃO)
CREATE TABLE wclub.terminais_backup_20251220 AS SELECT * FROM wclub.terminais;

-- 6.2: Dropar tabela antiga (DESCOMENTAR APÓS VALIDAÇÃO E BACKUP)
-- DROP TABLE wclub.terminais;

-- =====================================================
-- FIM DA MIGRAÇÃO
-- =====================================================

-- NOTAS IMPORTANTES:
-- 1. A view wallclub.terminais foi substituída por tabela real
-- 2. Campos inicio/fim agora são DATETIME (antes INT unix timestamp)
-- 3. Duplicata do terminal PBF9242F71873 (ID 70) foi encerrada
-- 4. Registros com timestamps inválidos (ex: 20251113) foram convertidos para NULL
-- 5. A tabela wclub.terminais foi preservada (dropar manualmente após validação)
-- 6. Índices criados para otimizar queries de vigência

-- PRÓXIMOS PASSOS:
-- 1. Validar dados migrados (executar SELECTs de validação acima)
-- 2. Atualizar código Python (models.py e queries SQL)
-- 3. Testar em desenvolvimento
-- 4. Criar backup: CREATE TABLE wclub.terminais_backup_20251220 AS SELECT * FROM wclub.terminais;
-- 5. Dropar tabela antiga: DROP TABLE wclub.terminais;
