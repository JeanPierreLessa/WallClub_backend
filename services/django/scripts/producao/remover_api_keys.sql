-- ============================================
-- REMOVER TABELAS DE API KEYS
-- ============================================
-- Data: 2025-09-30
-- Objetivo: Remover sistema de API Keys - migrado para OAuth 2.0

USE wallclub;

-- Remover tabela de logs de uso de API
DROP TABLE IF EXISTS api_usage;

-- Remover tabela de API Keys
DROP TABLE IF EXISTS api_keys;

-- Verificar se foram removidas
SHOW TABLES LIKE 'api%';

-- ============================================
-- RESULTADO ESPERADO:
-- Empty set (0.00 sec)
-- ============================================
