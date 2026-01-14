# Formulário de Cadastro de Estabelecimento - Own Financial

## 📋 Dados do Estabelecimento

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **cnpj** | String (14) | ✅ Sim | CNPJ do estabelecimento (apenas números) | 12345678000199 |
| **razaoSocial** | String | ✅ Sim | Razão social da empresa | LANCHONETE TESTE LTDA |
| **nomeFantasia** | String | ✅ Sim | Nome fantasia do estabelecimento | LANCHONETE DO ZE |
| **email** | String | ✅ Sim | E-mail de contato | contato@lanchonete.com.br |
| **cnae** | String | ✅ Sim | Código CNAE (consultar API auxiliar) | 5611-2/03 |
| **ramoAtividade** | String | ✅ Sim | Descrição da atividade (consultar API auxiliar) | LANCHONETES, CASAS DE CHA, DE SUCOS E SIMILARES |
| **mcc** | String | ✅ Sim | Código MCC (consultar API auxiliar) | 5814 |
| **faturamentoPrevisto** | Decimal | ✅ Sim | Faturamento mensal previsto em reais | 50000 |
| **faturamentoContratado** | Decimal | ✅ Sim | Faturamento contratado em reais | 50000 |

## 📞 Dados de Contato

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **dddComercial** | String (2) | ✅ Sim | DDD do telefone comercial | 11 |
| **telefoneComercial** | String | ✅ Sim | Telefone comercial (sem formatação) | 987654321 |
| **dddCel** | String (2) | ✅ Sim | DDD do celular | 11 |
| **telefoneCelular** | String | ✅ Sim | Telefone celular (sem formatação) | 999887766 |

## 📍 Endereço

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **cep** | String (8) | ✅ Sim | CEP (apenas números) | 01310100 |
| **logradouro** | String | ✅ Sim | Nome da rua/avenida | Avenida Paulista |
| **numeroEndereco** | Integer | ✅ Sim | Número do endereço | 1000 |
| **complemento** | String | ❌ Não | Complemento do endereço | Loja 10 |
| **bairro** | String | ✅ Sim | Bairro | Bela Vista |
| **municipio** | String | ✅ Sim | Cidade | São Paulo |
| **uf** | String (2) | ✅ Sim | Estado (sigla) | SP |

## 🏦 Dados Bancários

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **codBanco** | String (3) | ✅ Sim | Código do banco (3 dígitos) | 001 |
| **agencia** | String | ✅ Sim | Número da agência (sem dígito) | 1234 |
| **digAgencia** | String (1) | ❌ Não | Dígito verificador da agência | 5 |
| **numConta** | String | ✅ Sim | Número da conta (sem dígito) | 123456 |
| **digConta** | String (1) | ✅ Sim | Dígito verificador da conta | 7 |

## 💳 Configurações de Pagamento

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **quantidadePos** | Integer | ✅ Sim | Quantidade de máquinas POS | 1 |
| **antecipacaoAutomatica** | String (1) | ✅ Sim | Antecipação automática? (S/N) | N |
| **taxaAntecipacao** | Decimal | ✅ Sim | Taxa de antecipação (%) | 0 |
| **tipoAntecipacao** | String | ✅ Sim | Tipo de antecipação (ROTATIVO/FIXO) | ROTATIVO |

## 👤 Responsável

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **responsavelAssinatura** | String | ✅ Sim | Nome do responsável legal | José da Silva |

## 📄 Documentos dos Sócios

Para cada sócio, fornecer:

| Campo | Tipo | Obrigatório | Descrição | Exemplo |
|-------|------|-------------|-----------|---------|
| **identificacao** | String (11) | ✅ Sim | CPF do sócio (apenas números) | 12345678900 |
| **anexos** | Array | ✅ Sim | Lista de documentos do sócio | - |

### Tipos de Anexos por Sócio:
- **RGFRENTE**: Foto da frente do RG (base64)
- **RGVERSO**: Foto do verso do RG (base64)

## 📎 Documentos da Empresa

| Tipo de Documento | Obrigatório | Descrição |
|-------------------|-------------|-----------|
| **CONTRATO_SOCIAL** | ✅ Sim | Contrato social da empresa (PDF em base64) |
| **COMPROVANTE_ENDERECO** | ❌ Não | Comprovante de endereço (PDF em base64) |
| **CARTAO_CNPJ** | ❌ Não | Cartão CNPJ (PDF em base64) |

## 🌐 Outros Meios de Captura

Se o estabelecimento aceitar pagamentos online:

| Campo | Valor |
|-------|-------|
| **meioCaptura** | ECOMMERCE |

---

## ⚙️ Campos Técnicos (Preenchidos pelo Sistema)

| Campo | Descrição | Valor Padrão |
|-------|-----------|--------------|
| **cnpjCanalWL** | CNPJ do canal White Label | "" (vazio) |
| **cnpjOrigem** | CNPJ de origem | "" (vazio) |
| **identificadorCliente** | Identificador único do cliente no sistema | Gerado automaticamente |
| **urlCallback** | URL para receber notificações de status | https://wcapi.wallclub.com.br/webhook/cadastro/ |
| **tipoContrato** | Tipo de contrato | W (White Label) |
| **codConfiguracao** | Código de configuração | "" (vazio) |
| **cnpjParceiro** | CNPJ do WallClub | 54430621000134 |
| **idCesta** | ID da cesta de tarifas | Fornecido pela Own |
| **tarifacao** | Array de tarifas | Fornecido pela Own |
| **protocoloCore** | Protocolo do core | "" (vazio) |
| **hashAceite** | Hash de aceite | "" (vazio) |
| **terminais** | Lista de terminais | [] (vazio) |

---

## 📝 Observações Importantes

1. **CNAE/MCC**: Consultar a API `consultarAtividades` para obter os códigos corretos
2. **Cestas de Tarifas**: Atualmente não há cestas disponíveis no sandbox - contatar a Own
3. **Documentos**: Todos os arquivos devem ser convertidos para **base64**
4. **CPF/CNPJ**: Enviar apenas números, sem pontos, traços ou barras
5. **Telefones**: Enviar sem formatação (apenas números)
