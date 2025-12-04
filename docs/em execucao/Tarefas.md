## Tarefas Pendentes

- Ofertas: preparar pro lojista criar so a dele e mandar pra todos os usuarios do canal
- Email Aclub nao esta indo com layout correto (portal lojista)
- Testar concessao de cashback
- nao envia mensagem de baixar app no checkout
- ⏳ App: Adicionar device_fingerprint no payload de POST /api/v1/cliente/cadastro/validar_otp/
- UK em loja (remover felipe)
- Alteracao em loja (alterar, mudar vendedor, todas as lojas)

Contabilizar
- cupom
- cashback loja
- cashback wall


Visao geral dos testes
- APP OK
    - android 3.1.4 ok
    - ios 3.1.4 wall ok
    - android 3.1.4 wall nao enviei
- POS OK
    - enviar 2.1.4

Ajuste de nome de log e nivel de log (feito)
- apps - ok
    - cliente - ok
    - conta digital - ok
    - oauth - ok
    - ofertas - ok
    - transacoes - ok
- checkout
    - link_pagamento_web
    - link_recorrencia_web
- parametros_wallclub - ok
    - calculadora_base_gestao - ok
- pinbank - ok
    - cargas - ok
    - transacoes - ok
- portais
    - admin
    - controle_acesso
    - corporativo
    - lojista
    - vendas
- posp2 - ok
    - antifraude - ok
- sistema bancario
- wallclub



ALTER TABLE transactiondata_own
  CHANGE COLUMN valor_desconto desconto_wall DECIMAL(10,2) DEFAULT 0.00,
  CHANGE COLUMN valor_cashback cashback_debitado DECIMAL(10,2) DEFAULT 0.00,
  CHANGE COLUMN autorizacao_id autorizacao_uso_saldo_id VARCHAR(40),
  CHANGE COLUMN cashback_concedido cashback_creditado_wall DECIMAL(10,2) DEFAULT 0.00,
  ADD COLUMN cashback_creditado_loja DECIMAL(10,2) DEFAULT 0.00 AFTER cashback_creditado_wall,
  CHANGE COLUMN saldo_usado saldo_debitado DECIMAL(10,2) DEFAULT 0.00;
