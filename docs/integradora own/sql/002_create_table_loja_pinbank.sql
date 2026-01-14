-- =====================================================
-- Tabela: loja_pinbank
-- Descrição: Armazena dados específicos da integração com Pinbank
-- Data: 2026-01-13
-- =====================================================

CREATE TABLE IF NOT EXISTS loja_pinbank (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    loja_id INT UNSIGNED NOT NULL COMMENT 'FK para tabela loja',

    -- Dados de integração Pinbank
    codigo_canal INT NULL COMMENT 'Código do canal Pinbank',
    codigo_cliente INT NULL COMMENT 'Código do cliente Pinbank',
    key_value_loja VARCHAR(20) NULL COMMENT 'Chave de identificação da loja na Pinbank',

    -- Status de integração
    ativo BOOLEAN DEFAULT TRUE COMMENT 'Integração ativa',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_loja_pinbank_loja_id (loja_id),
    KEY idx_loja_pinbank_codigo_canal (codigo_canal),
    KEY idx_loja_pinbank_codigo_cliente (codigo_cliente),
    KEY idx_loja_pinbank_key_value (key_value_loja),

    CONSTRAINT fk_loja_pinbank_loja FOREIGN KEY (loja_id)
        REFERENCES loja(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Dados específicos da integração com Pinbank';
