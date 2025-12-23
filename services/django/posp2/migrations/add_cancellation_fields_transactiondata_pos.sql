-- Adicionar campos de cancelamento em transactiondata_pos
-- Para manter compatibilidade com transactiondata

ALTER TABLE transactiondata_pos
ADD COLUMN applicationName VARCHAR(256) DEFAULT NULL AFTER preAuthorizationConfirmationTimestamp,
ADD COLUMN billPaymentEffectiveDate BIGINT DEFAULT NULL AFTER applicationName;
