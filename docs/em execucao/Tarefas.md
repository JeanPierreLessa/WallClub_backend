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

### Gestão Admin (10/11/2025)
- ✅ Filtro "Incluir transações Credenciadora" usando campo `tipo_operacao`
- ✅ Coluna "Tipo de Transação" adicionada como primeira coluna (tabela + exports)
- ✅ App `pinbank` adicionado ao INSTALLED_APPS do container portais
- ✅ Exports (Excel/CSV) funcionando corretamente
- ✅ Excel sem linhas inúteis (headers na linha 1)
- ✅ RPR com filtros JavaScript alinhados ao servidor

### Outras Tarefas
- Validar Gestao (tem buraco?)
- ajeitar pra tirar o sms
- Email Aclub nao esta indo com layout correto (portal lojista)
- Gestao: contabilizacao de cashback
- Voucher
- Testar concessao de cashback
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

