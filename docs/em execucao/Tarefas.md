## Tarefas Pendentes

### Portal de Vendas (07/11/2025)
- ✅ Criar sistema de primeiro acesso com link único
- ✅ Corrigir import datetime em primeiro_acesso_view
- ✅ Corrigir busca de clientes (import CheckoutClienteTelefone)
- ✅ Configurar domínio checkout.wallclub.com.br
- ✅ Adicionar checkout.wallclub.com.br ao ALLOWED_HOSTS
- ⏳ **Investigar erro "Erro interno" na página de checkout** (em andamento)
  - Log adicionado para traceback completo
  - Aguardando novo teste para ver erro detalhado

### Outras Tarefas
- Validar Gestao (tem buraco?)
- Email Aclub nao esta indo com layout correto (portal lojista)
- Gestao: contabilizacao de cashback
- Voucher
- Remover a movimentacao maluca na conta corrente quando fechar pedido. so geracao de cash back com bloqueio e testes de conta digital
- nao envia mensagem de baixar app no checkout
- configurar nginx para receber ip real e ver alguns temmplates de remover cliente_auth
- UK em loja (remover felipe)
- Alteracao em loja (alterar, mudar vendedor, todas as lojas)



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
- parametros_wallclub
- pinbank
    - cargas
- portais
    - admin
    - controle_acesso
    - corporativo
    - lojista
    - vendas
- posp2 - ok
    - antifraude - ok

