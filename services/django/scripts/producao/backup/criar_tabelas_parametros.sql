-- =====================================================
-- SCRIPT DE CRIAÇÃO DAS TABELAS DE PARÂMETROS WALLCLUB
-- VERSÃO FINAL PARA PRODUÇÃO
-- Data: 2025-08-14
-- =====================================================

-- Usar o banco wallclub
USE wallclub;

-- Desabilitar verificações de chave estrangeira temporariamente
SET FOREIGN_KEY_CHECKS = 0;

-- =====================================================
-- FASE 1: REMOVER TODAS AS TABELAS (ordem inversa das dependências)
-- =====================================================
DROP TABLE IF EXISTS parametros_wallclub_importacoes;
DROP TABLE IF EXISTS parametros_wallclub_historico;
DROP TABLE IF EXISTS parametros_wallclub_futuro;
DROP TABLE IF EXISTS parametros_wallclub;
DROP TABLE IF EXISTS parametros_wallclub_planos;

-- =====================================================
-- FASE 2: CRIAR TODAS AS TABELAS
-- =====================================================

-- =====================================================
-- TABELA: parametros_wallclub_planos
-- Planos de pagamento (lookup table)
-- =====================================================

CREATE TABLE parametros_wallclub_planos (
    id INT PRIMARY KEY COMMENT 'ID único do plano (1-306)',
    id_original_wall INT NULL COMMENT 'ID original da tabela planos (Wall) - para validação',
    id_original_sem_wall INT NULL COMMENT 'ID original da tabela planos (Sem Wall) - para validação',
    nome VARCHAR(255) NOT NULL COMMENT 'Nome do plano',
    prazo_dias INT NOT NULL DEFAULT 0 COMMENT 'Prazo em dias',
    bandeira VARCHAR(50) NULL COMMENT 'Bandeira do cartão',
    ativo BOOLEAN NOT NULL DEFAULT TRUE COMMENT 'Plano ativo',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    criado_por_id INT NULL,
    atualizado_por_id INT NULL,
    
    INDEX idx_planos_ativo (ativo),
    INDEX idx_planos_bandeira (bandeira),
    INDEX idx_planos_validacao_wall (id_original_wall),
    INDEX idx_planos_validacao_sem_wall (id_original_sem_wall)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Planos de pagamento - tabela de lookup';

-- =====================================================
-- TABELA: parametros_wallclub
-- Configurações vigentes (ativas)
-- =====================================================

CREATE TABLE parametros_wallclub (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NOT NULL COMMENT 'ID da loja',
    id_desc INT NULL COMMENT 'ID desc legado - mantido para validação',
    id_plano INT NOT NULL COMMENT 'ID do plano de pagamento',
    wall CHAR(1) NOT NULL COMMENT 'Modalidade: S=Com Wall, N=Sem Wall',
    vigencia_inicio DATETIME NOT NULL COMMENT 'Início da vigência',
    vigencia_fim DATETIME NULL COMMENT 'Fim da vigência',
    
    -- Parâmetros da Loja (1-30)
    parametro_loja_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 1',
    parametro_loja_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 2',
    parametro_loja_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 3',
    parametro_loja_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 4',
    parametro_loja_5 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 5',
    parametro_loja_6 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 6',
    parametro_loja_7 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 7',
    parametro_loja_8 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 8',
    parametro_loja_9 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 9',
    parametro_loja_10 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 10',
    parametro_loja_11 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 11',
    parametro_loja_12 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 12',
    parametro_loja_13 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 13',
    parametro_loja_14 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 14',
    parametro_loja_15 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 15',
    parametro_loja_16 VARCHAR(50) NULL COMMENT 'Parâmetro Loja 16 (texto: Real)',
    parametro_loja_17 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 17',
    parametro_loja_18 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 18',
    parametro_loja_19 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 19',
    parametro_loja_20 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 20',
    parametro_loja_21 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 21',
    parametro_loja_22 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 22',
    parametro_loja_23 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 23',
    parametro_loja_24 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 24',
    parametro_loja_25 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 25',
    parametro_loja_26 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 26',
    parametro_loja_27 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 27',
    parametro_loja_28 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 28',
    parametro_loja_29 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 29',
    parametro_loja_30 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 30',
    
    -- Parâmetros Uptal/Wall (31-36)
    parametro_uptal_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 1',
    parametro_uptal_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 2',
    parametro_uptal_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 3',
    parametro_uptal_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 4',
    parametro_uptal_5 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 5',
    parametro_uptal_6 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 6',
    
    -- Parâmetros Wall/ClientesF (37-40)
    parametro_wall_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 1',
    parametro_wall_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 2',
    parametro_wall_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 3',
    parametro_wall_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 4',
    
    -- Campos de auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    criado_por_id INT NULL,
    atualizado_por_id INT NULL,
    
    -- Chave única: uma configuração por loja/plano/modalidade
    UNIQUE KEY uk_parametros_loja_plano_wall (loja_id, id_plano, wall),
    
    -- Índices para performance
    INDEX idx_parametros_loja (loja_id),
    INDEX idx_parametros_plano (id_plano),
    INDEX idx_parametros_wall (wall),
    INDEX idx_parametros_vigencia (vigencia_inicio, vigencia_fim),
    INDEX idx_parametros_ativo (vigencia_inicio, vigencia_fim, loja_id, wall),
    
    -- Chave estrangeira para planos
    FOREIGN KEY fk_parametros_plano (id_plano) REFERENCES parametros_wallclub_planos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Configurações de parâmetros vigentes (ativas)';

-- =====================================================
-- TABELA: parametros_wallclub_futuro
-- Configurações futuras (agendadas)
-- =====================================================

CREATE TABLE parametros_wallclub_futuro (
    id INT AUTO_INCREMENT PRIMARY KEY,
    loja_id INT NOT NULL COMMENT 'ID da loja',
    id_desc INT NULL COMMENT 'ID desc legado - mantido para validação',
    id_plano INT NOT NULL COMMENT 'ID do plano de pagamento',
    wall CHAR(1) NOT NULL COMMENT 'Modalidade: S=Com Wall, N=Sem Wall',
    vigencia_inicio DATETIME NOT NULL COMMENT 'Início da vigência',
    vigencia_fim DATETIME NULL COMMENT 'Fim da vigência',
    
    -- Parâmetros da Loja (1-30)
    parametro_loja_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 1',
    parametro_loja_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 2',
    parametro_loja_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 3',
    parametro_loja_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 4',
    parametro_loja_5 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 5',
    parametro_loja_6 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 6',
    parametro_loja_7 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 7',
    parametro_loja_8 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 8',
    parametro_loja_9 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 9',
    parametro_loja_10 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 10',
    parametro_loja_11 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 11',
    parametro_loja_12 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 12',
    parametro_loja_13 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 13',
    parametro_loja_14 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 14',
    parametro_loja_15 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 15',
    parametro_loja_16 VARCHAR(50) NULL COMMENT 'Parâmetro Loja 16 (texto: Real)',
    parametro_loja_17 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 17',
    parametro_loja_18 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 18',
    parametro_loja_19 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 19',
    parametro_loja_20 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 20',
    parametro_loja_21 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 21',
    parametro_loja_22 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 22',
    parametro_loja_23 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 23',
    parametro_loja_24 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 24',
    parametro_loja_25 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 25',
    parametro_loja_26 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 26',
    parametro_loja_27 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 27',
    parametro_loja_28 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 28',
    parametro_loja_29 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 29',
    parametro_loja_30 DECIMAL(10,6) NULL COMMENT 'Parâmetro Loja 30',
    
    -- Parâmetros Uptal/Wall (31-36)
    parametro_uptal_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 1',
    parametro_uptal_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 2',
    parametro_uptal_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 3',
    parametro_uptal_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 4',
    parametro_uptal_5 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 5',
    parametro_uptal_6 DECIMAL(10,6) NULL COMMENT 'Parâmetro Uptal 6',
    
    -- Parâmetros Wall/ClientesF (37-40)
    parametro_wall_1 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 1',
    parametro_wall_2 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 2',
    parametro_wall_3 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 3',
    parametro_wall_4 DECIMAL(10,6) NULL COMMENT 'Parâmetro Wall 4',
    
    -- Campos de auditoria
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    criado_por_id INT NULL,
    atualizado_por_id INT NULL,
    
    -- Chave única: uma configuração futura por loja/plano/modalidade
    UNIQUE KEY uk_parametros_futuro_loja_plano_wall (loja_id, id_plano, wall),
    
    -- Índices para performance
    INDEX idx_parametros_futuro_loja (loja_id),
    INDEX idx_parametros_futuro_plano (id_plano),
    INDEX idx_parametros_futuro_wall (wall),
    INDEX idx_parametros_futuro_vigencia (vigencia_inicio, vigencia_fim),
    INDEX idx_parametros_futuro_ativacao (vigencia_inicio),
    
    -- Chave estrangeira para planos
    FOREIGN KEY fk_parametros_futuro_plano (id_plano) REFERENCES parametros_wallclub_planos(id)
        ON UPDATE CASCADE ON DELETE RESTRICT
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Configurações de parâmetros agendadas (futuras)';

-- =====================================================
-- TABELA: parametros_wallclub_historico
-- Histórico de alterações (auditoria)
-- =====================================================

CREATE TABLE parametros_wallclub_historico (
    id INT AUTO_INCREMENT PRIMARY KEY,
    configuracao_vigente_id INT NULL COMMENT 'Referência para configuração vigente',
    configuracao_futura_id INT NULL COMMENT 'Referência para configuração futura',
    loja_id INT NOT NULL COMMENT 'ID da loja (para facilitar consultas)',
    id_plano INT NOT NULL COMMENT 'ID do plano (para facilitar consultas)',
    wall CHAR(1) NOT NULL COMMENT 'Modalidade (para facilitar consultas)',
    acao VARCHAR(20) NOT NULL COMMENT 'Ação realizada',
    campo_alterado VARCHAR(100) NULL COMMENT 'Campo que foi alterado',
    valor_anterior TEXT NULL COMMENT 'Valor antes da alteração',
    valor_novo TEXT NULL COMMENT 'Valor após a alteração',
    usuario_id INT NULL COMMENT 'Usuário que fez a alteração',
    data_alteracao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    observacoes TEXT NULL COMMENT 'Observações sobre a alteração',
    
    -- Índices para consultas de auditoria
    INDEX idx_historico_loja (loja_id),
    INDEX idx_historico_plano (id_plano),
    INDEX idx_historico_wall (wall),
    INDEX idx_historico_data (data_alteracao),
    INDEX idx_historico_usuario (usuario_id),
    INDEX idx_historico_acao (acao),
    INDEX idx_historico_vigente (configuracao_vigente_id),
    INDEX idx_historico_futura (configuracao_futura_id),
    
    -- Chaves estrangeiras
    FOREIGN KEY fk_historico_vigente (configuracao_vigente_id) 
        REFERENCES parametros_wallclub(id) ON DELETE CASCADE,
    FOREIGN KEY fk_historico_futura (configuracao_futura_id) 
        REFERENCES parametros_wallclub_futuro(id) ON DELETE CASCADE
        
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Histórico de alterações nas configurações (auditoria)';

-- =====================================================
-- TABELA: parametros_wallclub_importacoes
-- Controle de importações
-- =====================================================

CREATE TABLE parametros_wallclub_importacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    arquivo_nome VARCHAR(255) NOT NULL COMMENT 'Nome do arquivo importado',
    arquivo_tamanho INT NOT NULL COMMENT 'Tamanho do arquivo em bytes',
    total_linhas INT DEFAULT 0 COMMENT 'Total de linhas no arquivo',
    linhas_importadas INT DEFAULT 0 COMMENT 'Linhas importadas com sucesso',
    linhas_erro INT DEFAULT 0 COMMENT 'Linhas com erro',
    status VARCHAR(20) DEFAULT 'PENDENTE' COMMENT 'Status da importação',
    relatorio_erros TEXT NULL COMMENT 'Relatório detalhado dos erros',
    usuario_id INT NULL COMMENT 'Usuário que fez a importação',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processado_em TIMESTAMP NULL COMMENT 'Data de processamento',
    
    -- Índices para controle
    INDEX idx_importacoes_status (status),
    INDEX idx_importacoes_data (criado_em),
    INDEX idx_importacoes_usuario (usuario_id)
    
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci 
COMMENT='Controle de importações de parâmetros';

-- Reabilitar verificações de chave estrangeira
SET FOREIGN_KEY_CHECKS = 1;

-- =====================================================
-- VERIFICAÇÕES FINAIS
-- =====================================================
SELECT 'Tabelas criadas com sucesso!' as status;

-- Mostrar estrutura das tabelas criadas
SHOW TABLES LIKE 'parametros_wallclub%';

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
