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

CREATE TABLE IF NOT EXISTS wallclub.credenciaisExtratoContaOwn (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(256) NOT NULL,
    cnpj VARCHAR(14) NOT NULL,
    
    -- Credenciais OAuth 2.0 (APIs Adquirência)
    client_id VARCHAR(256) NOT NULL,
    client_secret VARCHAR(512) NOT NULL,
    scope VARCHAR(256) NOT NULL,
    
    -- Credenciais e-SiTef (Transações)
    entity_id VARCHAR(100) NOT NULL,
    access_token VARCHAR(512) NOT NULL,
    environment VARCHAR(10) DEFAULT 'LIVE',
    
    -- Relacionamento
    cliente_id INT,
    
    -- Controle
    ativo BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP,
    
    -- Índices
    INDEX idx_cliente (cliente_id),
    INDEX idx_cnpj (cnpj)
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
