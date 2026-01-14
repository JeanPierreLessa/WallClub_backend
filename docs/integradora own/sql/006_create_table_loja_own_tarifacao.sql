-- =====================================================
-- Tabela: loja_own_tarifacao
-- Descrição: Armazena as tarifas da cesta Own associadas à loja
-- Data: 2026-01-13
-- =====================================================

CREATE TABLE IF NOT EXISTS loja_own_tarifacao (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    loja_own_id INT UNSIGNED NOT NULL COMMENT 'FK para tabela loja_own',

    -- Dados da tarifa
    cesta_valor_id INT NOT NULL COMMENT 'ID da tarifa na cesta Own',
    valor DECIMAL(10,2) NOT NULL COMMENT 'Valor da tarifa',
    descricao VARCHAR(256) NULL COMMENT 'Descrição da tarifa',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_loja_own_tarif_loja_own_id (loja_own_id),
    KEY idx_loja_own_tarif_cesta_valor_id (cesta_valor_id),

    CONSTRAINT fk_loja_own_tarif_loja_own FOREIGN KEY (loja_own_id)
        REFERENCES loja_own(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Tarifas da cesta Own associadas à loja';
