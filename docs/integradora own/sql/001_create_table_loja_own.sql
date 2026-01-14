-- =====================================================
-- Tabela: loja_own
-- Descrição: Armazena dados específicos da integração com Own Financial
-- Data: 2026-01-13
-- =====================================================

CREATE TABLE IF NOT EXISTS loja_own (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    loja_id INT UNSIGNED NOT NULL COMMENT 'FK para tabela loja',

    -- Controle de cadastro
    cadastrar BOOLEAN DEFAULT FALSE COMMENT 'Indica se deve cadastrar na Own',

    -- Dados de credenciamento
    conveniada_id VARCHAR(50) NULL COMMENT 'ID do estabelecimento na Own',
    status_credenciamento VARCHAR(50) NULL COMMENT 'Status: PENDENTE, APROVADO, REPROVADO, PROCESSANDO',
    protocolo VARCHAR(50) NULL COMMENT 'Protocolo de cadastro na Own',
    data_credenciamento DATETIME NULL COMMENT 'Data do credenciamento',
    mensagem_status TEXT NULL COMMENT 'Mensagem de retorno da Own',

    -- Configurações de tarifação
    id_cesta INT NULL COMMENT 'ID da cesta de tarifas Own',

    -- Configurações de captura
    aceita_ecommerce BOOLEAN DEFAULT FALSE COMMENT 'Aceita pagamentos e-commerce',

    -- Controle de sincronização
    sincronizado BOOLEAN DEFAULT FALSE COMMENT 'Dados sincronizados com Own',
    ultima_sincronizacao DATETIME NULL COMMENT 'Data da última sincronização',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    UNIQUE KEY uq_loja_own_loja_id (loja_id),
    KEY idx_loja_own_conveniada_id (conveniada_id),
    KEY idx_loja_own_status (status_credenciamento),
    KEY idx_loja_own_protocolo (protocolo),

    CONSTRAINT fk_loja_own_loja FOREIGN KEY (loja_id)
        REFERENCES loja(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Dados específicos da integração com Own Financial';

-- Índices adicionais para performance
CREATE INDEX idx_loja_own_cadastrar ON loja_own(cadastrar);
CREATE INDEX idx_loja_own_sincronizado ON loja_own(sincronizado);
