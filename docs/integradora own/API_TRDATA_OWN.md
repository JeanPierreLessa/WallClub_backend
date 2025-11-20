# API TRDATA_OWN - Endpoint para Transações Own/Ágilli

## Endpoint
```
POST /posp2/trdata_own/
```

## Autenticação
OAuth 2.0 - Bearer Token (mesmo do endpoint Pinbank)

## Headers
```
Authorization: Bearer {access_token}
Content-Type: application/json
```

---

## REQUEST

### Estrutura JSON

```json
{
  "celular": "21999730901",
  "cpf": "17653377807",
  "trdata": "{\"nsuTerminal\":\"117\",\"nsuHost\":\"000117\",\"authorizationCode\":\"200832\",\"amount\":\"990\",\"originalAmount\":\"990\",\"paymentMethod\":\"CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST\",\"totalInstallments\":2,\"brand\":\"VISA\",\"cardNumber\":\"************9797\",\"terminal\":\"1490306603\",\"terminalTimestamp\":1763639819,\"hostTimestamp\":1763639819,\"status\":\"APPROVED\",\"capturedTransaction\":1,\"transactionReturn\":\"00\",\"operationId\":1,\"txTransactionId\":\"251120000004146865\",\"cnpj\":\"54430621000134\",\"sdk\":\"agilli\",\"valororiginal\":\"R$10,00\"}",
  "terminal": "1490306603",
  "valororiginal": "R$10,00",
  "operador_pos": "",
  "valor_desconto": 0,
  "valor_cashback": 0,
  "cashback_concedido": 0,
  "autorizacao_id": "",
  "modalidade_wall": ""
}
```

### Campos Obrigatórios

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `trdata` | String (JSON) | Dados da transação retornados pelo SDK Ágilli |
| `terminal` | String | ID do terminal (Build.SERIAL) |
| `valororiginal` | String | Valor formatado (ex: "R$10,00") |

### Campos Opcionais

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `celular` | String | Celular do cliente (para Wall Club) |
| `cpf` | String | CPF do cliente (para Wall Club) |
| `operador_pos` | String | Código do operador |
| `valor_desconto` | Decimal | Desconto Wall Club aplicado |
| `valor_cashback` | Decimal | Cashback creditado |
| `cashback_concedido` | Decimal | Cashback concedido na transação |
| `autorizacao_id` | String | ID da autorização de uso de saldo |
| `modalidade_wall` | String | 'S'=Wall, 'N'=Sem Wall, 'C'=Cashback |

### Estrutura do campo `trdata`

O campo `trdata` deve conter um **JSON string escapado** com os dados retornados pelo SDK Ágilli.

**Importante:** O JSON deve ser convertido para string e escapado antes de enviar no request.

#### JSON original (antes de escapar):

```json
{
  "nsuTerminal": "117",
  "nsuHost": "000117",
  "authorizationCode": "200832",
  "amount": "990",
  "originalAmount": "990",
  "paymentMethod": "CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST",
  "totalInstallments": 2,
  "brand": "VISA",
  "cardNumber": "************9797",
  "terminal": "1490306603",
  "terminalTimestamp": 1763639819,
  "hostTimestamp": 1763639819,
  "status": "APPROVED",
  "capturedTransaction": 1,
  "transactionReturn": "00",
  "operationId": 1,
  "txTransactionId": "251120000004146865",
  "cnpj": "54430621000134",
  "sdk": "agilli",
  "valororiginal": "R$10,00"
}
```

#### Como enviar (JSON escapado como string):

```json
{
  "trdata": "{\"nsuTerminal\":\"117\",\"nsuHost\":\"000117\",\"authorizationCode\":\"200832\",\"amount\":\"990\",\"originalAmount\":\"990\",\"paymentMethod\":\"CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST\",\"totalInstallments\":2,\"brand\":\"VISA\",\"cardNumber\":\"************9797\",\"terminal\":\"1490306603\",\"terminalTimestamp\":1763639819,\"hostTimestamp\":1763639819,\"status\":\"APPROVED\",\"capturedTransaction\":1,\"transactionReturn\":\"00\",\"operationId\":1,\"txTransactionId\":\"251120000004146865\",\"cnpj\":\"54430621000134\",\"sdk\":\"agilli\",\"valororiginal\":\"R$10,00\"}"
}
```

#### Campos obrigatórios no `trdata`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `txTransactionId` | String | **ID único da transação Own** (chave principal) |
| `amount` | String/Integer | Valor em centavos (ex: "990" = R$9,90) |
| `originalAmount` | String/Integer | Valor original em centavos |
| `brand` | String | Bandeira (VISA, MASTER, ELO, etc) |
| `status` | String | Status da transação (APPROVED, etc) |
| `operationId` | Integer | 1=Crédito, 2=Débito, 3=Voucher, 4=PIX, 5=Parc.Inteligente |
| `paymentMethod` | String | Método de pagamento (CREDIT_ONE_INSTALLMENT, etc) |
| `totalInstallments` | Integer | Número de parcelas |
| `cnpj` | String | CNPJ do estabelecimento |
| `sdk` | String | Deve ser "agilli" |
| `terminal` | String | ID do terminal |

#### Campos recomendados no `trdata`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `nsuTerminal` | String | NSU do terminal |
| `nsuHost` | String | NSU do host Own |
| `authorizationCode` | String | Código de autorização |
| `transactionReturn` | String | Código de retorno (ex: "00") |
| `cardNumber` | String | Número do cartão mascarado |
| `terminalTimestamp` | Integer | Unix timestamp do terminal |
| `hostTimestamp` | Integer | Unix timestamp do host |
| `capturedTransaction` | Integer | 1=capturada, 0=não capturada |
| `valororiginal` | String | Valor formatado (ex: "R$10,00") |

#### Campos opcionais do Ágilli (comprovantes)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `customerTicket` | String (TEXT) | Comprovante formatado do cliente gerado pelo Ágilli |
| `estabTicket` | String (TEXT) | Comprovante formatado do estabelecimento gerado pelo Ágilli |
| `e2ePixId` | String | ID E2E do PIX (apenas para Parcelamento Inteligente) |

**Nota:** Esses campos são opcionais e serão salvos na base se enviados. Podem ser úteis para reimpressão de comprovantes.

---

## RESPONSE - SUCESSO

### HTTP Status: 200 OK

#### Com Wall Club (CPF informado)

```json
{
  "sucesso": true,
  "mensagem": "Dados processados com sucesso",
  "cpf": "*******807",
  "nome": "João da Silva",
  "estabelecimento": "Loja Teste",
  "cnpj": "54430621000134",
  "data": "2025-11-20 10:30:45",
  "forma": "PARCELADO SEM JUROS",
  "parcelas": 2,
  "nopwall": "251120000004146865",
  "autwall": "200832",
  "terminal": "1490306603",
  "nsu": "000117",
  "voriginal": "Valor original da loja: R$ 10.00",
  "desconto": "Valor do desconto CLUB: R$ 0.10",
  "vdesconto": "Valor total pago:\nR$ 9.90",
  "pagoavista": "Valor pago à loja à vista: R$ 9.90",
  "vparcela": "R$ 4.95",
  "tarifas": "Tarifas CLUB: -- ",
  "encargos": ""
}
```

#### Com Saldo Cashback Usado

```json
{
  "sucesso": true,
  "mensagem": "Dados processados com sucesso",
  "cpf": "*******807",
  "nome": "João da Silva",
  "estabelecimento": "Loja Teste",
  "cnpj": "54430621000134",
  "data": "2025-11-20 10:30:45",
  "forma": "DEBITO",
  "parcelas": 1,
  "nopwall": "251120000004146865",
  "autwall": "200832",
  "terminal": "1490306603",
  "nsu": "000117",
  "voriginal": "Valor original da loja: R$ 10.00",
  "desconto": "Valor do desconto CLUB: R$ 0.10",
  "saldo_usado": "Saldo utilizado de cashback: R$ 2.00",
  "cashback_concedido": "Cashback concedido: R$ 0.50",
  "vdesconto": "Valor total pago:\nR$ 7.90",
  "pagoavista": "Valor pago à loja à vista: R$ 7.90",
  "vparcela": "R$ 7.90",
  "tarifas": "Tarifas CLUB: -- ",
  "encargos": ""
}
```

#### Sem Wall Club (venda normal)

```json
{
  "sucesso": true,
  "mensagem": "Dados processados com sucesso",
  "cpf": "",
  "nome": "",
  "estabelecimento": "Loja Teste",
  "cnpj": "54430621000134",
  "data": "2025-11-20 10:30:45",
  "forma": "A VISTA",
  "parcelas": 1,
  "nopwall": "251120000004146865",
  "autwall": "200832",
  "terminal": "1490306603",
  "nsu": "000117",
  "voriginal": "Valor da transação: R$ 10.00",
  "pagoavista": "Valor pago à loja: R$ 10.00",
  "vparcela": "R$ 10.00"
}
```

### Campos do Response

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `sucesso` | Boolean | Sim | true se processado com sucesso |
| `mensagem` | String | Sim | Mensagem de status |
| `cpf` | String | Sim | CPF mascarado (*******XXX) ou vazio |
| `nome` | String | Sim | Nome do cliente ou vazio |
| `estabelecimento` | String | Sim | Nome fantasia da loja |
| `cnpj` | String | Sim | CNPJ do estabelecimento |
| `data` | String | Sim | Data/hora (YYYY-MM-DD HH:MM:SS) |
| `forma` | String | Sim | Forma de pagamento |
| `parcelas` | Integer | Sim | Número de parcelas |
| `nopwall` | String | Sim | ID da transação Own (txTransactionId) |
| `autwall` | String | Sim | Código de autorização |
| `terminal` | String | Sim | ID do terminal |
| `nsu` | String | Sim | NSU do host Own |
| `voriginal` | String | Sim | Texto formatado do valor original |
| `desconto` | String | Condicional | Desconto Wall Club (se aplicável) |
| `saldo_usado` | String | Condicional | Saldo cashback usado (se aplicável) |
| `cashback_concedido` | String | Condicional | Cashback concedido (se aplicável) |
| `vdesconto` | String | Condicional | Valor total pago (com Wall Club) |
| `pagoavista` | String | Sim | Valor pago à loja |
| `vparcela` | String | Sim | Valor da parcela |
| `tarifas` | String | Condicional | Tarifas (com Wall Club) |
| `encargos` | String | Condicional | Encargos (com Wall Club) |

---

## RESPONSE - ERRO

### HTTP Status: 200 OK (com sucesso: false)

```json
{
  "sucesso": false,
  "mensagem": "Descrição do erro"
}
```

### Possíveis Erros

| Mensagem | Causa |
|----------|-------|
| `Campos obrigatórios ausentes: trdata, terminal ou valororiginal` | Faltam campos obrigatórios |
| `Erro ao decodificar JSON` | JSON malformado |
| `Erro ao decodificar trdata` | Campo trdata não é JSON válido |
| `Campo txTransactionId ausente no trdata` | Falta identificador único da transação |
| `Transação já processada: {txTransactionId}` | Transação duplicada (idempotência) |
| `Erro ao processar transação` | Erro genérico no processamento |

---

## EXEMPLO COMPLETO

### Request

```bash
curl -X POST https://wcapi.wallclub.com.br/posp2/trdata_own/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "celular": "21999730901",
    "cpf": "17653377807",
    "trdata": "{\"nsuTerminal\":\"117\",\"nsuHost\":\"000117\",\"authorizationCode\":\"200832\",\"amount\":\"990\",\"originalAmount\":\"990\",\"paymentMethod\":\"CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST\",\"totalInstallments\":2,\"brand\":\"VISA\",\"cardNumber\":\"************9797\",\"terminal\":\"1490306603\",\"terminalTimestamp\":1763639819,\"hostTimestamp\":1763639819,\"status\":\"APPROVED\",\"capturedTransaction\":1,\"transactionReturn\":\"00\",\"operationId\":1,\"txTransactionId\":\"251120000004146865\",\"cnpj\":\"54430621000134\",\"sdk\":\"agilli\"}",
    "terminal": "1490306603",
    "valororiginal": "R$9,90"
  }'
```

### Response

```json
{
  "sucesso": true,
  "transaction_id": 12345,
  "txTransactionId": "251120000004146865",
  "nsuHost": "000117",
  "authorizationCode": "200832",
  "valor": 9.90,
  "parcelas": 2,
  "bandeira": "VISA",
  "loja": "Loja Teste",
  "cnpj": "54430621000134",
  "terminal": "1490306603",
  "data_hora": "20/11/2025 10:30:45"
}
```

---

## DIFERENÇAS vs ENDPOINT PINBANK

| Aspecto | Pinbank `/trdata/` | Own `/trdata_own/` |
|---------|-------------------|-------------------|
| Tabela | `transactiondata` | `transactiondata_own` |
| Identificador único | `nsuPinbank` | `txTransactionId` |
| Campos específicos | nsuAcquirer, nsuPinbank | operationId, transactionReturn, cnpj |
| SDK | pinbank | agilli |
| Validação duplicidade | Por nsuPinbank | Por txTransactionId |

---

## IDEMPOTÊNCIA

O endpoint valida duplicidade pelo campo `txTransactionId`. Se uma transação com o mesmo `txTransactionId` já existir na base, retorna erro:

```json
{
  "sucesso": false,
  "mensagem": "Transação já processada: 251120000004146865"
}
```

Isso garante que a mesma transação não seja processada duas vezes.

---

## NOTAS IMPORTANTES

1. **Campo `sdk`**: Deve sempre ser "agilli" no trdata
2. **Formato de valor**: `valororiginal` aceita formato brasileiro (R$10,00)
3. **Timestamps**: `terminalTimestamp` e `hostTimestamp` devem ser Unix timestamp
4. **Valores em centavos**: `amount` e `originalAmount` devem estar em centavos (ex: 990 = R$9,90)
5. **Autenticação**: Usa o mesmo token OAuth do endpoint Pinbank
