# Release Notes - WallClub Backend v2.2.1

**Data de Release:** 26/02/2026
**Versão:** 2.2.1
**Status:** Stable
**Branch:** release-2.2.1

---

## 📋 Visão Geral

A versão 2.2.1 representa uma evolução importante da plataforma WallClub, com foco em:
- Sistema completo de monitoramento e observabilidade (Prometheus + Grafana + Alertmanager)
- Refatoração da arquitetura de URLs dos portais
- Refinamento de métricas e cálculos do RPR
- Melhorias na integração Own Financial (ambiente dinâmico, tokens e-commerce)
- Sistema de autenticação 2FA com sliding window
- Endpoint POS para integração direta com terminais

**Total de Commits:** 189
**Módulos Impactados:** 15+
**Novos Endpoints:** 3+

---

## 🚀 Novas Funcionalidades

### 1. Sistema de Monitoramento Completo ⭐

#### Prometheus + Grafana + Alertmanager
- **Prometheus** (porta 9090) - Coleta de métricas com retenção de 15 dias
- **Grafana** (porta 3000) - Dashboards customizados para containers Django
- **Alertmanager** (porta 9093) - Gerenciamento centralizado de alertas
- **Node Exporter** (porta 9100) - Métricas de sistema (CPU, memória, disco)
- **Redis Exporter** (porta 9121) - Métricas detalhadas do Redis

#### Dashboards Customizados
- Monitoramento de containers Django (wallclub-apis, wallclub-portais, wallclub-pos)
- Métricas de performance e uso de recursos
- Alertas configurados para CPU, memória e disco
- Integração com Nginx para acesso via VPN

#### Segurança
- Acesso restrito via VPN (10.0.0.0/16)
- Credenciais gerenciadas via AWS Secrets Manager
- Configuração de datasources via provisioning automático

---

### 2. Refatoração de Arquitetura de URLs

#### Simplificação Estrutural
- **Antes:** 8 arquivos de URLs (urls.py, urls_admin.py, urls_lojista.py, etc.)
- **Depois:** 3 arquivos (urls.py, urls_portais.py, urls_ajax.py)
- Redução de 62.5% na complexidade de roteamento

#### Função Helper Dinâmica
- `get_portal_urls()` - Geração dinâmica de rotas por portal
- Zero duplicação de código
- Manutenção centralizada
- Suporte a múltiplos portais (admin, lojista, vendas, corporativo)

#### Benefícios
- Facilita adição de novos portais
- Reduz erros de configuração
- Melhora legibilidade do código
- Simplifica debugging de rotas

---

### 3. RPR - Refinamento Completo de Métricas

#### Reestruturação de Colunas
- Coluna "Custo ajuste nos Repasses" reposicionada e renomeada
- Nova coluna "Resultado Operacional Ajustado" (Resultado Operacional + Custo ajuste)
- Box "Resultado Financeiro" recalculado (Receita Financeira - Custo Direto)
- "Custos POS/Equip" movido para box Resultado Financeiro

#### Cálculos Aprimorados
- Percentual de comissão dinâmico (tabela `canal_comissao`) em tela e exports
- Média ponderada de parcelas na linha totalizadora
- Cálculo de percentuais totalizadores baseados em totais reais
- Variáveis auxiliares (var113_A, var109_A, var116_A, var118_A) para totalizadores

#### Exportações Excel
- Formatação monetária e percentual correta em totalizadores
- Campo "Ajuste pagos de repasses" no Resumo Executivo
- Células vazias em vez de 0 para campos sem valor
- Tratamento de valores nulos e zero

#### Logs de Debug
- Rastreamento detalhado de percentuais e totais
- Verificação de presença de variáveis auxiliares
- Logs de entrada/saída em cálculos críticos

---

### 4. Own Financial - Melhorias de Integração

#### Ambiente Dinâmico (TEST/LIVE)
- Método centralizado `CredenciaisOwnService.obter_environment()`
- Usado em todos os 7 services da Own
- Facilita testes e homologação
- Configuração por loja via banco de dados

#### API de Tokens E-commerce
- Endpoint de consulta de tokens e-commerce por contrato
- Documentação oficial OPPWA referenciada
- Suporte a `entity_id` e `access_token` específicos por loja
- Integração com `CartaoTokenizadoService`

#### Payload Otimizado
- Merchant: `countryCode` corrigido para formato numérico (076)
- `paymentMethod` movido para `customParameters`
- Campos estruturados de cliente e endereço
- Validação robusta de campos obrigatórios

#### Logs Aprimorados
- Log detalhado do JSON completo na consulta cadastral
- Resposta de erro estruturada (texto + JSON)
- Rastreamento de payload enviado à API
- Identificação de erros 400 com detalhes

---

### 5. Sistema 2FA com Sliding Window

#### Implementação
- Sliding window de 30 dias para dispositivos confiáveis
- Revalidação 2FA forçada a cada 90 dias
- Validação obrigatória de `device_fingerprint` em refresh JWT
- Bypass automático para login Apple/Google

#### Segurança
- Dispositivos confiáveis armazenados com hash
- Expiração automática de dispositivos antigos
- Logs de tentativas de autenticação
- Proteção contra replay attacks

---

### 6. Endpoint POS para Integração Direta ⭐ NOVO

#### Funcionalidade
- Endpoint `/api/internal/checkout/transacao-pos/` para processamento direto de cartão
- Recebe dados do cartão em plaintext via HTTPS (TLS 1.2+)
- Busca ou cria cliente automaticamente
- Consulta Bureau para validação de CPF
- Integração com antifraude e gateway de pagamento

#### Campos Novos
- `operador_pos` em `checkout_transactions` - ID do operador POS
- `bureau_restricoes` em `checkout_cliente` - Restrições do Bureau (JSON)
- Origem `POS` adicionada às opções de transação

#### Fluxo Completo
1. Recebe CPF e dados do cartão
2. Verifica se cliente existe na loja
3. Se não existe: consulta Bureau, valida idade, cria cliente
4. Processa pagamento via `processar_pagamento_cartao_direto`
5. Integra com antifraude (score de risco)
6. Atualiza transação com dados do operador POS
7. Retorna resposta detalhada (sucesso/falha, NSU, código autorização)

#### Validações
- CPF obrigatório e válido
- Dados do cartão completos
- Loja existente e ativa
- Cliente maior de idade (Bureau)
- Antifraude aprovado

#### Segurança
- PCI-DSS compliance (não armazena cartão completo)
- Apenas BIN e últimos 4 dígitos salvos
- Comunicação via HTTPS (TLS 1.2+)
- Rate limiting configurado

---

## 🔧 Melhorias e Otimizações

### Gateway Router
- Seleção dinâmica entre Pinbank e Own Financial
- Roteamento baseado em configuração da loja
- Suporte a múltiplos gateways por loja
- Fallback automático em caso de falha

### Checkout - Campos Estruturados
- `CheckoutCliente` e `CheckoutToken` com endereço estruturado
- Campos: `logradouro`, `numero`, `complemento`, `bairro`, `cidade`, `estado`, `cep`
- Campo `data_nascimento` obrigatório para Own Financial
- Campo `email` validado e obrigatório
- Integração ViaCEP para preenchimento automático

### Portal de Vendas
- Formulários de cadastro/edição atualizados
- Validação de campos estruturados
- Feedback visual de erros
- Preenchimento automático de endereço por CEP

### Redis
- Limite de memória configurado (512MB)
- Política de eviction: `allkeys-lru`
- Otimização de uso de memória
- Monitoramento via Redis Exporter

### Nginx
- Configuração para Prometheus e Alertmanager (acesso VPC)
- Rebuild otimizado (apenas Nginx quando necessário)
- Logs de acesso e erro separados
- Rate limiting configurado por endpoint

---

## 🐛 Correções de Bugs

### Críticas
- **Antifraude:** Import `datetime` faltando em `services.py`
- **Own Financial:** `customer_data` não sendo enviado em `create_payment_debit`
- **Modalidade:** 1 parcela classificada como DÉBITO (corrigido para CRÉDITO)
- **Constraint:** `origem='POS'` não permitida em `checkout_transactions`

### Importantes
- Merchant `countryCode`: 076 (numérico) em vez de BR (alpha-2)
- Grafana provisioning: datasources configurados corretamente
- Alertmanager: simplificação de configuração de variáveis
- Credenciais hardcoded removidas de arquivos de configuração

### Validações
- Teste EXTERNAL desabilitado em produção
- Variáveis auxiliares incluídas no dict linha para totalizadores
- Formatação monetária e percentual em totalizadores RPR
- Células vazias em vez de 0 em exportações Excel

---

## 🗄️ Alterações no Banco de Dados

### Tabelas Modificadas

#### checkout_cliente
```sql
ALTER TABLE checkout_cliente
ADD COLUMN bureau_restricoes JSON DEFAULT NULL
COMMENT 'Restrições encontradas na consulta ao Bureau (JSON)';

CREATE INDEX idx_bureau_restricoes ON checkout_cliente(bureau_restricoes((1024)));
```

#### checkout_transactions
```sql
ALTER TABLE checkout_transactions
ADD COLUMN operador_pos VARCHAR(50) DEFAULT NULL
COMMENT 'ID do operador que processou a transação no POS';

CREATE INDEX idx_operador_pos ON checkout_transactions(operador_pos);

-- Atualizar constraint de origem
ALTER TABLE checkout_transactions
DROP CHECK checkout_transactions_chk_1;

ALTER TABLE checkout_transactions
ADD CONSTRAINT checkout_transactions_chk_1
CHECK (`origem` IN ('LINK', 'CHECKOUT', 'RECORRENCIA', 'POS'));
```

---

## 📚 Documentação

### Atualizações
- Documentação oficial OPPWA referenciada
- Comandos de deploy atualizados (rebuild Nginx)
- ROADMAP atualizado com conclusão do Step 2 (Observabilidade)
- README atualizado com sistema de monitoramento completo

### Novos Documentos
- Dashboard customizado do Grafana documentado
- Configuração de alertas do Alertmanager
- Guia de troubleshooting de monitoramento

---

## ⚙️ Infraestrutura

### Docker Compose
- Novos containers: Prometheus, Grafana, Alertmanager, Node Exporter, Redis Exporter
- Volumes persistentes para dados de métricas
- Rede interna para comunicação entre containers
- Healthchecks configurados

### Nginx
- Configuração para acesso a Prometheus/Alertmanager via VPN
- Rate limiting por endpoint
- Logs estruturados
- Compressão gzip habilitada

### Secrets Manager
- Credenciais do Grafana gerenciadas via AWS
- Tokens de API protegidos
- Rotação automática de secrets

---

## ⚠️ Breaking Changes

### 1. Constraint de Origem em checkout_transactions
**Antes:**
```sql
CHECK (`origem` IN ('LINK', 'CHECKOUT', 'RECORRENCIA'))
```

**Depois:**
```sql
CHECK (`origem` IN ('LINK', 'CHECKOUT', 'RECORRENCIA', 'POS'))
```

**Ação Necessária:** Executar ALTER TABLE antes do deploy.

---

### 2. Modalidade de Pagamento
**Antes:**
```python
# 1 parcela = DÉBITO
modalidade = 'CREDITO' if parcelas > 1 else 'DEBITO'
```

**Depois:**
```python
# Sempre CRÉDITO para cartão de crédito
modalidade = 'CREDITO'
```

**Ação Necessária:** Nenhuma - correção automática.

---

### 3. Customer Data Obrigatório (Own Financial)
**Antes:**
```python
# customer_data opcional
service.create_payment_debit(card_data=card_data, amount=valor)
```

**Depois:**
```python
# customer_data obrigatório
customer_data = {
    'nome_completo': cliente.nome,
    'email': cliente.email,
    'cpf': cliente.cpf,
    'data_nascimento': cliente.data_nascimento.strftime('%Y-%m-%d')
}
service.create_payment_debit(
    card_data=card_data,
    amount=valor,
    customer_data=customer_data
)
```

**Ação Necessária:** Garantir que clientes tenham `data_nascimento` e `email` preenchidos.

---

## 📊 Estatísticas da Release

- **Total de Commits:** 189
- **Arquivos Alterados:** 110
- **Linhas Adicionadas:** ~8.767
- **Linhas Removidas:** ~4.062
- **Módulos Impactados:** 15+
- **Novos Endpoints:** 3
- **Correções de Bugs:** 25+
- **Refatorações:** 30+
- **Melhorias de Logs:** 40+

---

## 🔄 Procedimento de Deploy

### 1. Pré-requisitos
```bash
# Backup do banco de dados
mysqldump wallclub > backup_pre_v2.2.1.sql

# Verificar variáveis de ambiente
python manage.py check

# Pull do código
cd /var/www/WallClub_backend
git pull origin release-2.2.1
```

### 2. Alterações no Banco de Dados
```sql
-- Adicionar coluna bureau_restricoes
ALTER TABLE checkout_cliente
ADD COLUMN bureau_restricoes JSON DEFAULT NULL
COMMENT 'Restrições encontradas na consulta ao Bureau (JSON)';

CREATE INDEX idx_bureau_restricoes ON checkout_cliente(bureau_restricoes((1024)));

-- Adicionar coluna operador_pos
ALTER TABLE checkout_transactions
ADD COLUMN operador_pos VARCHAR(50) DEFAULT NULL
COMMENT 'ID do operador que processou a transação no POS';

CREATE INDEX idx_operador_pos ON checkout_transactions(operador_pos);

-- Atualizar constraint de origem
ALTER TABLE checkout_transactions
DROP CHECK checkout_transactions_chk_1;

ALTER TABLE checkout_transactions
ADD CONSTRAINT checkout_transactions_chk_1
CHECK (`origem` IN ('LINK', 'CHECKOUT', 'RECORRENCIA', 'POS'));
```

### 3. Deploy dos Containers
```bash
# Build e restart dos containers
docker-compose build wallclub-apis nginx
docker-compose stop wallclub-apis nginx
docker-compose up -d wallclub-apis nginx

# Verificar containers
docker ps

# Verificar logs
docker logs wallclub-apis --tail 50
docker logs nginx --tail 50
```

### 4. Validação Pós-Deploy
```bash
# Testar endpoint POS
curl -X POST https://wcapi.wallclub.com.br/api/internal/checkout/transacao-pos/ \
  -H "Content-Type: application/json" \
  -d '{
    "loja_id": 15,
    "operador_pos": "POS-TEST",
    "cpf": "12345678901",
    "card_data": {
      "numero": "4110490655954420",
      "validade": "12/33",
      "cvv": "123",
      "nome_titular": "TESTE",
      "bandeira": "VISA"
    },
    "valor": "10.00",
    "parcelas": 1,
    "descricao": "Teste POS"
  }'

# Verificar Prometheus
curl http://10.0.1.124:9090/-/healthy

# Verificar Grafana
curl http://10.0.1.124:3000/api/health
```

### 5. Monitoramento
- Verificar dashboards do Grafana
- Validar métricas no Prometheus
- Conferir alertas no Alertmanager
- Monitorar logs de erro nos primeiros 30 minutos

---

## 🧪 Testes Recomendados

### Endpoint POS
1. Processar transação com cliente existente
2. Processar transação com cliente novo (consulta Bureau)
3. Validar rejeição de CPF inválido
4. Validar rejeição de menor de idade
5. Verificar integração com antifraude
6. Conferir NSU e código de autorização

### Sistema de Monitoramento
1. Acessar Grafana e verificar dashboards
2. Validar métricas do Prometheus
3. Testar alertas do Alertmanager
4. Verificar métricas de Redis
5. Conferir métricas de sistema (Node Exporter)

### RPR
1. Gerar relatório completo
2. Exportar para Excel
3. Validar totalizadores
4. Conferir percentuais de comissão
5. Verificar Resumo Executivo

---

## 📞 Suporte

Em caso de problemas:
1. Verificar logs em `/var/log/wallclub/`
2. Consultar documentação em `docs/`
3. Verificar dashboards do Grafana
4. Contatar equipe de desenvolvimento

---

## 🎯 Próximas Versões

### v2.2.2 (Planejado)
- Melhorias no endpoint POS
- Otimizações de performance
- Novos dashboards de monitoramento
- Integração com novos gateways

### v2.3.0 (Futuro)
- Sistema de antecipação automática
- Dashboard de métricas em tempo real
- Melhorias no sistema de cashback
- Otimizações de infraestrutura

---

**Desenvolvido por:** Equipe WallClub
**Data de Release:** 26/02/2026
**Versão:** 2.2.1 Stable
