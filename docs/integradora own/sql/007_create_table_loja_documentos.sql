-- =====================================================
-- Tabela: loja_documentos
-- Descrição: Armazena documentos da loja e sócios para cadastro na Own
-- Data: 2026-01-13
-- =====================================================

CREATE TABLE IF NOT EXISTS loja_documentos (
    id INT UNSIGNED NOT NULL AUTO_INCREMENT,
    loja_id INT UNSIGNED NOT NULL COMMENT 'FK para tabela loja',

    -- Tipo de documento
    tipo_documento VARCHAR(50) NOT NULL COMMENT 'CONTRATO_SOCIAL, COMPROVANTE_ENDERECO, CARTAO_CNPJ, RGFRENTE, RGVERSO',

    -- Dados do arquivo
    nome_arquivo VARCHAR(256) NOT NULL COMMENT 'Nome original do arquivo',
    caminho_arquivo VARCHAR(512) NOT NULL COMMENT 'Caminho no S3 ou storage',
    tamanho_bytes BIGINT NULL COMMENT 'Tamanho do arquivo em bytes',
    mime_type VARCHAR(100) NULL COMMENT 'Tipo MIME do arquivo',

    -- Identificação do sócio (para documentos pessoais)
    cpf_socio VARCHAR(11) NULL COMMENT 'CPF do sócio (para docs pessoais: RG)',
    nome_socio VARCHAR(256) NULL COMMENT 'Nome do sócio',

    -- Controle
    ativo BOOLEAN DEFAULT TRUE COMMENT 'Documento ativo',

    -- Auditoria
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    PRIMARY KEY (id),
    KEY idx_loja_docs_loja_id (loja_id),
    KEY idx_loja_docs_tipo (tipo_documento),
    KEY idx_loja_docs_cpf_socio (cpf_socio),
    KEY idx_loja_docs_ativo (ativo),

    CONSTRAINT fk_loja_docs_loja FOREIGN KEY (loja_id)
        REFERENCES loja(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Documentos da loja e sócios para cadastro na Own';

-- Índice composto para buscar documentos de um sócio específico
CREATE INDEX idx_loja_docs_loja_socio ON loja_documentos(loja_id, cpf_socio);
