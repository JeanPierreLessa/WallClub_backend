-- =====================================================
-- Tabela: veriff_session
-- Descricao: Sessoes de verificacao de identidade via Veriff
-- Data: 2026-03-12
-- =====================================================

CREATE TABLE IF NOT EXISTS veriff_session (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    cliente_id BIGINT UNSIGNED NOT NULL COMMENT 'FK para tabela cliente',
    canal_id INT NOT NULL,
    session_id VARCHAR(100) NOT NULL COMMENT 'ID da sessao Veriff',
    session_url VARCHAR(500) NOT NULL COMMENT 'URL para o SDK abrir',
    status VARCHAR(30) NOT NULL DEFAULT 'created' COMMENT 'created, submitted, approved, declined, resubmission_requested, expired, abandoned',
    decision_time DATETIME NULL COMMENT 'Quando Veriff decidiu',
    veriff_reason TEXT NULL COMMENT 'Motivo da decisao',
    vendor_data VARCHAR(255) NULL COMMENT 'Dados extras enviados',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uk_veriff_session_id (session_id),
    KEY idx_veriff_cliente_id (cliente_id),
    KEY idx_veriff_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Sessoes de verificacao de identidade via Veriff';
