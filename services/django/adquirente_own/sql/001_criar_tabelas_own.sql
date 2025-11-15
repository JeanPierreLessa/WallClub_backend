-- =====================================================
-- Script de criação das tabelas do módulo Own Financial
-- Versão: 1.0
-- Data: 15/11/2025
-- =====================================================

-- =====================================================
-- 1. Modificar tabela baseTransacoesGestao
-- =====================================================

-- Adicionar campo adquirente para identificar origem da transação
ALTER TABLE wallclub.baseTransacoesGestao
ADD COLUMN adquirente VARCHAR(20) DEFAULT 'PINBANK' AFTER tipo_operacao;

ALTER TABLE wallclub.baseTransacoesGestao_audit
ADD COLUMN adquirente VARCHAR(20) DEFAULT 'PINBANK' AFTER tipo_operacao;


-- Criar índice para performance
CREATE INDEX idx_adquirente ON wallclub.baseTransacoesGestao(adquirente);

-- =====================================================
-- 2. Criar tabela ownExtratoTransacoes
-- =====================================================

CREATE TABLE IF NOT EXISTS wallclub.ownExtratoTransacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    lido BOOLEAN DEFAULT 0,

    -- Identificação
    cnpjCpfCliente VARCHAR(14) NOT NULL,
    cnpjCpfParceiro VARCHAR(14),
    identificadorTransacao VARCHAR(50) NOT NULL UNIQUE,

    -- Dados da transação
    data DATETIME NOT NULL,
    numeroSerieEquipamento VARCHAR(50),
    valor DECIMAL(10,2) NOT NULL,
    quantidadeParcelas INT NOT NULL,
    mdr DECIMAL(10,2) NOT NULL,
    valorAntecipacaoTotal DECIMAL(10,2),
    taxaAntecipacaoTotal DECIMAL(12,10),

    -- Status e classificação
    statusTransacao VARCHAR(50) NOT NULL,
    bandeira VARCHAR(30) NOT NULL,
    modalidade VARCHAR(100) NOT NULL,
    codigoAutorizacao VARCHAR(20),
    numeroCartao VARCHAR(20),

    -- Dados da parcela
    parcelaId BIGINT,
    statusPagamento VARCHAR(30),
    dataHoraTransacao DATETIME,
    mdrParcela DECIMAL(10,2),
    numeroParcela INT,
    valorParcela DECIMAL(10,2),
    dataPagamentoPrevista DATE,
    dataPagamentoReal DATE,
    valorAntecipado DECIMAL(10,2),
    taxaAntecipada DECIMAL(12,10),
    antecipado CHAR(1),
    numeroTitulo VARCHAR(20),

    -- Controle
    processado BOOLEAN DEFAULT 0,

    -- Índices
    INDEX idx_identificador (identificadorTransacao),
    INDEX idx_cnpj_cliente (cnpjCpfCliente),
    INDEX idx_data (data),
    INDEX idx_lido (lido),
    INDEX idx_processado (processado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 3. Criar tabela ownLiquidacoes
-- =====================================================

CREATE TABLE IF NOT EXISTS wallclub.ownLiquidacoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,

    lancamentoId BIGINT NOT NULL UNIQUE,
    statusPagamento VARCHAR(30) NOT NULL,
    dataPagamentoPrevista DATE NOT NULL,
    numeroParcela INT NOT NULL,
    valor DECIMAL(10,2) NOT NULL,
    dataPagamentoReal DATE NOT NULL,
    antecipada CHAR(1) NOT NULL,
    identificadorTransacao VARCHAR(50) NOT NULL,
    bandeira VARCHAR(30) NOT NULL,
    modalidade VARCHAR(100) NOT NULL,
    codigoCliente VARCHAR(14) NOT NULL,
    docParceiro VARCHAR(14) NOT NULL,
    nsuTransacao VARCHAR(50) NOT NULL,
    numeroTitulo VARCHAR(20) NOT NULL,

    processado BOOLEAN DEFAULT 0,

    -- Índices
    INDEX idx_lancamento (lancamentoId),
    INDEX idx_identificador (identificadorTransacao),
    INDEX idx_data_pagamento (dataPagamentoReal),
    INDEX idx_processado (processado)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 4. Criar tabela credenciaisExtratoContaOwn
-- =====================================================
-- Armazena credenciais OAuth 2.0 do cliente White Label (WallClub)
-- Cada registro representa um conjunto de credenciais para acessar APIs Own
-- As lojas individuais são identificadas via docParceiro nas consultas

CREATE TABLE IF NOT EXISTS wallclub.credenciaisExtratoContaOwn (
    id INT AUTO_INCREMENT PRIMARY KEY,

    -- Identificação do Cliente White Label (WallClub)
    nome VARCHAR(256) NOT NULL COMMENT 'Nome do cliente White Label',
    cnpj_white_label VARCHAR(14) NOT NULL COMMENT 'CNPJ do cliente White Label (usado como cnpjCliente nas APIs)',

    -- Credenciais OAuth 2.0 (APIs Adquirência)
    -- Recebidas por email após cadastro como cliente Own
    client_id VARCHAR(256) NOT NULL COMMENT 'Identificador do cliente Own',
    client_secret VARCHAR(512) NOT NULL COMMENT 'Chave secreta OAuth 2.0',
    scope VARCHAR(256) NOT NULL COMMENT 'Escopo de integração liberado',

    -- Credenciais e-SiTef (Transações E-commerce)
    -- Usadas para processar pagamentos via OPPWA
    entity_id VARCHAR(100) NOT NULL COMMENT 'Entity ID para transações e-SiTef',
    access_token VARCHAR(512) NOT NULL COMMENT 'Access token e-SiTef',

    -- Ambiente
    environment VARCHAR(10) DEFAULT 'LIVE' COMMENT 'Ambiente: LIVE ou TEST',

    -- Controle
    ativo BOOLEAN DEFAULT 1 COMMENT 'Credencial ativa',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,

    -- Índices
    UNIQUE INDEX idx_cnpj_white_label (cnpj_white_label),
    INDEX idx_environment (environment)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =====================================================
-- 5. Comentários nas tabelas
-- =====================================================

ALTER TABLE wallclub.ownExtratoTransacoes
COMMENT = 'Armazena transações consultadas da API Own Financial';

ALTER TABLE wallclub.ownLiquidacoes
COMMENT = 'Armazena liquidações consultadas da API Own Financial';

ALTER TABLE wallclub.credenciaisExtratoContaOwn
COMMENT = 'Credenciais de acesso às APIs Own Financial (OAuth 2.0 + e-SiTef)';

-- =====================================================
-- FIM DO SCRIPT
-- =====================================================
