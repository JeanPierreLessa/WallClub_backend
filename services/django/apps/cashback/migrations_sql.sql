-- ============================================
-- MIGRATIONS SQL - SISTEMA DE CASHBACK CENTRALIZADO
-- Data: 25/11/2025
-- ============================================

-- NOTA: Cashback Wall NÃO precisa de tabela separada.
-- Usa diretamente parametros_wallclub (wall='C').

-- Tabela: cashback_regra_loja
CREATE TABLE cashback_regra_loja (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    loja_id BIGINT NOT NULL COMMENT 'ID da loja',
    nome VARCHAR(100) NOT NULL COMMENT 'Nome da regra',
    descricao TEXT NOT NULL COMMENT 'Descrição da regra',
    ativo TINYINT(1) DEFAULT 1 COMMENT 'Regra ativa',
    prioridade INT DEFAULT 0 COMMENT 'Maior número = maior prioridade',
    tipo_desconto VARCHAR(20) NOT NULL COMMENT 'FIXO ou PERCENTUAL',
    valor_desconto DECIMAL(10,2) NOT NULL COMMENT 'Valor fixo em R$ ou percentual',
    valor_minimo_compra DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Valor mínimo da transação',
    valor_maximo_cashback DECIMAL(10,2) DEFAULT NULL COMMENT 'Teto de cashback por transação',
    periodo_retencao_dias INT DEFAULT 0 COMMENT 'Dias de carência antes de liberar',
    periodo_expiracao_dias INT DEFAULT 0 COMMENT 'Dias até expirar após liberação',
    vigencia_inicio DATETIME NOT NULL COMMENT 'Início da vigência',
    vigencia_fim DATETIME NOT NULL COMMENT 'Fim da vigência',
    formas_pagamento JSON DEFAULT NULL COMMENT 'Lista de formas aceitas: ["PIX", "DEBITO", "CREDITO"]',
    dias_semana JSON DEFAULT NULL COMMENT 'Dias da semana: [0,1,2,3,4,5,6] (0=domingo)',
    horario_inicio TIME DEFAULT NULL COMMENT 'Horário início',
    horario_fim TIME DEFAULT NULL COMMENT 'Horário fim',
    limite_uso_cliente_dia INT DEFAULT NULL COMMENT 'Máximo de vezes por cliente/dia',
    limite_uso_cliente_mes INT DEFAULT NULL COMMENT 'Máximo de vezes por cliente/mês',
    orcamento_mensal DECIMAL(10,2) DEFAULT NULL COMMENT 'Orçamento total da loja no mês',
    gasto_mes_atual DECIMAL(10,2) DEFAULT 0.00 COMMENT 'Total gasto no mês atual',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_loja_ativo (loja_id, ativo),
    INDEX idx_vigencia (vigencia_inicio, vigencia_fim),
    FOREIGN KEY (loja_id) REFERENCES loja(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Tabela: cashback_uso
CREATE TABLE cashback_uso (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    tipo_origem VARCHAR(10) NOT NULL COMMENT 'WALL ou LOJA',
    parametro_wall_id BIGINT DEFAULT NULL COMMENT 'ID do ParametrosWall (wall=C) - apenas para WALL',
    regra_loja_id BIGINT DEFAULT NULL COMMENT 'ID da RegraCashbackLoja - apenas para LOJA',
    cliente_id BIGINT NOT NULL COMMENT 'ID do cliente',
    loja_id BIGINT NOT NULL COMMENT 'ID da loja',
    canal_id INT NOT NULL COMMENT 'ID do canal',
    transacao_tipo VARCHAR(20) NOT NULL COMMENT 'POS ou CHECKOUT',
    transacao_id BIGINT NOT NULL COMMENT 'ID da transação',
    valor_transacao DECIMAL(10,2) NOT NULL COMMENT 'Valor da transação',
    valor_cashback DECIMAL(10,2) NOT NULL COMMENT 'Valor do cashback',
    status VARCHAR(20) DEFAULT 'RETIDO' COMMENT 'RETIDO, LIBERADO, EXPIRADO, ESTORNADO',
    aplicado_em DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT 'Data de aplicação',
    liberado_em DATETIME DEFAULT NULL COMMENT 'Data de liberação',
    expira_em DATETIME DEFAULT NULL COMMENT 'Data de expiração',
    movimentacao_id BIGINT DEFAULT NULL COMMENT 'ID da MovimentacaoContaDigital',
    
    INDEX idx_cliente_aplicado (cliente_id, aplicado_em),
    INDEX idx_tipo_status (tipo_origem, status),
    INDEX idx_transacao (transacao_tipo, transacao_id),
    INDEX idx_status_liberado (status, liberado_em),
    INDEX idx_status_expira (status, expira_em),
    FOREIGN KEY (cliente_id) REFERENCES cliente(id),
    FOREIGN KEY (loja_id) REFERENCES loja(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- COMENTÁRIOS E OBSERVAÇÕES
-- ============================================

-- 1. RegraCashback é abstrata, não tem tabela própria
-- 2. Cashback Wall usa DIRETAMENTE parametros_wallclub (wall='C') - SEM tabela intermediária
-- 3. cashback_regra_loja com filtros opcionais (JSON) e limites de uso
-- 4. cashback_uso é o histórico unificado (Wall + Loja)
--    - tipo_origem='WALL' → usa parametro_wall_id
--    - tipo_origem='LOJA' → usa regra_loja_id
-- 5. Todas as tabelas usam utf8mb4_unicode_ci (padrão do projeto)
-- 6. FKs apenas para cliente e loja (outras são IDs manuais)
