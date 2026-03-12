-- =====================================================
-- Tabela: terminal_own
-- Descricao: Vinculo entre terminal POS e cadastro na Own Financial
-- Data: 2026-03-12
-- =====================================================

CREATE TABLE IF NOT EXISTS terminal_own (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    terminal_id INT UNSIGNED NOT NULL COMMENT 'FK para tabela terminais',
    numero_contrato VARCHAR(50) NOT NULL COMMENT 'Numero do contrato Own',
    modelo VARCHAR(50) NOT NULL COMMENT 'Modelo do equipamento POS',
    numero_serie VARCHAR(256) NOT NULL COMMENT 'Numero de serie enviado a Own',
    ativo TINYINT(1) NOT NULL DEFAULT 1 COMMENT 'Vinculo ativo na Own',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_terminal_own_terminal_id (terminal_id),
    KEY idx_terminal_own_contrato (numero_contrato),
    KEY idx_terminal_own_ativo (ativo)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Vinculo entre terminal POS e cadastro na Own Financial';
