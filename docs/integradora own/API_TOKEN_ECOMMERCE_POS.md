# API de Token para Transações E-commerce/POS - Own Financial

## Visão Geral

A API de token da Own Financial retorna as credenciais necessárias para processar transações de e-commerce e POS:
- **entity_id**: Identificador da entidade para transações OPPWA
- **access_token**: Token de acesso para autenticação nas transações

Essas credenciais são armazenadas na tabela `loja_own` nos campos `entity_id` e `access_token`.

## Endpoint

```
GET /agilli/ecommerce/token
```

**Ambiente Produção**: `https://acquirer.own.financial/agilli/ecommerce/token`

**Ambiente Sandbox**: `https://acquirer-qa.own.financial/agilli/ecommerce/token`

## Autenticação

Requer token OAuth 2.0 no header:

```
Authorization: Bearer {token_oauth}
```

O token OAuth deve ser obtido através do endpoint `/agilli/v2/auth` conforme documentado em `DOCUMENTACAO_APIs_v3_Descritivo.txt`.

## Parâmetros

### Query Parameters

| Parâmetro | Tipo | Obrigatório | Descrição |
|-----------|------|-------------|-----------|
| numeroContrato | string | Sim | Número do contrato do estabelecimento na Own (formato: XXX-XXX-XX) |

## Exemplo de Requisição

```bash
curl --request GET \
  --url 'https://acquirer.own.financial/agilli/ecommerce/token?numeroContrato=029-196-35' \
  --header 'Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...'
```

## Resposta

### Sucesso (200 OK)

```json
{
  "entity_id": "8ac7a4a07d1234567890abcd",
  "access_token": "OGFjN2E0YTA3ZDEyMzQ1Njc4OTBhYmNk"
}
```

### Campos da Resposta

| Campo | Tipo | Descrição |
|-------|------|-----------|
| entity_id | string | Identificador da entidade para transações OPPWA |
| access_token | string | Token de acesso para autenticação nas transações |

### Erro (400/401/500)

```json
{
  "message": "Contrato não encontrado",
  "timestamp": "2026-02-10T20:15:00.000Z"
}
```

## Uso das Credenciais

As credenciais retornadas (`entity_id` e `access_token`) devem ser utilizadas para:

1. **Transações de E-commerce**: Processar pagamentos via checkout/link de pagamento
2. **Transações de POS**: Processar pagamentos via terminal físico

### Armazenamento

As credenciais são armazenadas na tabela `loja_own`:

```sql
UPDATE loja_own
SET entity_id = '{entity_id}',
    access_token = '{access_token}'
WHERE loja_id = {loja_id};
```

### Segurança

⚠️ **IMPORTANTE**:
- O `access_token` é sensível e deve ser armazenado de forma segura
- Não expor o token em logs ou respostas de API
- Renovar periodicamente conforme política de segurança da Own

## Fluxo de Integração

1. **Cadastrar estabelecimento** via `/parceiro/v2/cadastrarConveniada`
2. **Aguardar aprovação** via webhook de credenciamento
3. **Obter número do contrato** do webhook ou consulta de protocolo
4. **Buscar credenciais** via `/ecommerce/token` usando o número do contrato
5. **Armazenar** `entity_id` e `access_token` na tabela `loja_own`
6. **Utilizar** as credenciais para processar transações

## Observações

- Esta API **NÃO está implementada** na tela de edição de loja
- As credenciais devem ser obtidas via script/comando separado após aprovação do cadastro
- O número do contrato é retornado no webhook de credenciamento quando `status = "SUCESSO"`
- Sem o número do contrato, não é possível obter as credenciais de transação

## Relacionado

- `DOCUMENTACAO_APIs_v3_Descritivo.txt` - Documentação completa da API Own
- `API_TRDATA_OWN.md` - Endpoint para processar transações Own/Ágilli
- `models_cadastro.py` - Modelo `LojaOwn` com campos `entity_id` e `access_token`
