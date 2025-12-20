-- Tabela de auditoria para rastrear mudanças em base_transacoes_unificadas
-- Objetivo: identificar quais colunas realmente mudam para otimizar UPDATEs

CREATE TABLE IF NOT EXISTS auditoria_base_unificada_mudancas (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    var9 VARCHAR(20) COMMENT 'NSU',
    tipo_operacao VARCHAR(20) COMMENT 'Credenciadora ou Wallet',
    colunas_alteradas TEXT COMMENT 'Lista de colunas que mudaram (JSON)',
    qtd_colunas_alteradas INT COMMENT 'Quantidade de colunas alteradas',
    data_auditoria DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_var9 (var9),
    INDEX idx_data (data_auditoria)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Auditoria de mudanças em base_transacoes_unificadas para análise de performance';
