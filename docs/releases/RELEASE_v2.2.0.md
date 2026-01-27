# Release Notes - WallClub Backend v2.2.0

**Data de Release:** 26/01/2026
**Versão:** 2.2.0
**Status:** Stable
**Branch:** release-2.2.0

---

## 📋 Visão Geral

A versão 2.2.0 representa uma evolução significativa da plataforma WallClub, com foco em:
- Integração completa com Own Financial para cadastro e processamento
- Sistema robusto de cupons e cashback
- Unificação da base de transações (POS + Credenciadora)
- Melhorias em relatórios e exportações
- Aprimoramentos de segurança e monitoramento

**Total de Commits:** 420
**Módulos Impactados:** 12+
**Novos Endpoints:** 10+

---

## 🚀 Novas Funcionalidades

### 1. Integração Own Financial

#### Cadastro de Lojas
- Fluxo completo de cadastro de lojas na Own Financial
- Upload e validação de documentos do responsável
- Campos editáveis: tarifas, tipo de antecipação, hash de aceite
- Validação robusta de campos com tratamento de erros 400
- Carregamento seguro de credenciais via AWS Secrets Manager

#### Processamento de Transações
- Integração com API Own para processamento POS
- Automação de carga após confirmação de pagamentos
- Logs detalhados para rastreamento e debug

#### Novos Campos
- Gateway Ativo
- URL da Loja
- Aceita E-commerce
- PIX
- Hierarquia WallClub
- Tarifação e tipo de antecipação

---

### 2. Sistema de Cupons

#### Validação em Tempo Real
- Endpoint interno para gerenciamento de cupons (`/api/internal/cupom/`)
- Validação em tempo real no checkout web
- Validação de loja existente e elegibilidade
- Separação de rotas para checkout e POS

#### Interface de Usuário
- Campo de cupom habilitado após seleção de parcela
- Limpeza automática de cupom ao trocar parcela
- Feedback visual de validação

#### Integração com Calculadora
- Calculadora ajustada para receber valor do cupom
- Cálculo correto do valor final com cupom aplicado
- Campo `desconto_wall_parametro_id` no processamento POS

---

### 3. Sistema de Cashback Aprimorado

#### Cálculo de Cashback
- Reimplementação com busca direta de parâmetros Wall
- Cálculo de cashback Wall integrado ao fluxo POS
- Correção de verificação de tipo wall ('S')
- Logs detalhados para debug e auditoria

#### Conta Digital
- **CORREÇÃO CRÍTICA:** Débito correto de cashback usando campo `afeta_cashback`
- Suporte completo a débito de cashback em `ContaDigitalService`
- Informações detalhadas de cashback no extrato
- Novo endpoint `consultar_saldo_cashback` (recomendado)
- Endpoint `consultar_saldo` marcado como deprecated

#### Movimentações
- Registro de compras informativas no extrato
- Status de compra: `PROCESSADA` (alterado de `CONCLUIDA`)
- Ajuste de tipo de movimentação para `CASHBACK_CREDITO`
- Uso de `MovimentacaoContaDigital` para registro de compras

#### Novos Campos
- `cashback_wall_parametro_id`
- `cashback_wall_valor`
- `cashback_loja_regra_id`
- `cashback_loja_valor`
- `cashback_concedido`

---

### 4. Base de Transações Unificadas

#### Implementação
- Carga automática de transações POS Pinbank
- Carga de transações da credenciadora
- Execução automática a cada 30 minutos via Celery
- Inserção em `base_transacoes_unificadas`
- Otimização de queries com subquery para registros únicos por NSU

#### Auditoria e Performance
- Sistema de auditoria de mudanças
- Updates seletivos otimizados
- Logs de tempo para operações INSERT e UPDATE
- Monitoramento de processamento de NSU

#### Cancelamentos
- Atualização automática de cancelamentos
- Recálculo de valores em cancelamento NSU
- Tratamento robusto de erros com traceback detalhado

---

### 5. Sistema de Ofertas

#### Automação
- Disparo automático agendado de ofertas
- Vinculação de ofertas com lojas específicas
- Lock otimista para evitar disparo duplicado
- Descoberta automática de tasks de recorrência

#### Controle e Validação
- Validação de disparo antes da execução
- Restrição de edição de ofertas já disparadas
- Modo visualização para ofertas disparadas
- Logs de rastreamento de filtragem

#### Filtros e Permissões
- Filtro baseado no tipo de usuário (lojista/grupo econômico)
- Uso de `LojistaDataMixin` para filtrar por lojas acessíveis
- Suporte para diferentes formatos de atributos de loja

#### Interface
- Botão voltar na navegação
- Lista todas as lojas (não apenas ativas)
- Campos de data de disparo e loja_id na edição

---

### 6. Relatórios e Exportações

#### RPR (Relatório de Produção e Receita)
- Formatação monetária brasileira em totalizadores
- Conversão automática de percentuais para decimais
- Cálculo de `var15` e `variavel_nova_15` na linha totalizadora
- Novas variáveis totalizadoras
- Botão de exportação de resumo executivo

#### Exportações Excel
- Suporte a tipo `Decimal` em colunas percentuais
- Formatação correta de valores monetários negativos
- Tratamento de erros no cálculo de totais
- Linha de totais em exportações de transações
- Validação de strings vazias

#### Gestão de Transações
- Formatação padronizada de colunas percentuais
- Filtro de data para transações a partir de 01/10/2025
- Campo `processado` em `ExtratoPOS`
- Melhoria na formatação de datas

---

### 7. Segurança e Rate Limiting

#### Implementações
- Rate limiting para endpoints POS críticos
- Gestão segura de cartões
- Autenticação OAuth para Risk Engine
- Validação de Risk Engine no script de validação completa

#### Validações
- Verificação de autenticação manual para APIs AJAX
- Uso de `@login_required` para APIs AJAX
- CSRF e credenciais em requisições fetch
- Configuração nginx para APIs Own sem rate limit (necessário)

---

## 🔧 Melhorias e Otimizações

### Refatorações de Código
- Migração de class-based para function-based views (Own Financial)
- Move hardcoded URLs para environment variables
- Lazy imports para evitar importações circulares
- Padronização de formatação de código
- Remoção de arquivos obsoletos

### Calculadora
- Implementação de calculadora de base gestão para POS
- Serviço de cálculo de desconto no módulo POSP2
- Conversão segura de valores de string para float
- Cache control headers em respostas

### Checkout
- Simplificação de simulação de parcelas com cashback integrado
- Conversão de valores de cálculo de pagamento
- Integração com `TransacoesPinbankService`
- Determinação automática de portal e canal

### Logs e Monitoramento
- **80+ commits** de melhorias em logs
- Rastreamento detalhado de processamento de NSU
- Monitoramento de transações Pinbank
- Debug do cálculo de cashback
- Logs de entrada/saída em endpoints críticos
- Simplificação de nomes dos módulos nos logs

---

## 🐛 Correções de Bugs

### Críticas
- **Débito de cashback:** Correção do campo `afeta_cashback` em `ContaDigitalService`
- **Cálculo de encargos:** Conversão segura de valores para float
- **Cálculo de tarifas:** Tratamento de valores nulos e zero
- **Valor da parcela:** Correção quando `vparcela` é nulo ou zero

### Importantes
- Verificação de tipo wall para cálculo de cashback
- Importação do `timedelta` para cálculo de data de liberação
- Tipo de movimentação: `CASHBACK_LOJA` → `CASHBACK_CREDITO`
- Porta do Risk Engine: 8004 → 8008
- Replace `datetime.now()` com `timezone.now()` para timezone-aware timestamps

### Validações
- Permitir `quantidade_pos = 0`
- Adicionar `hashAceite` de volta ao payload Own
- Usar CNPJ como `identificadorCliente`
- Incluir CPF do responsável em `documentosSocios`
- Não marcar campo de busca CNAE como obrigatório
- Remover exibição de 'None' em campos vazios

---

## 🗄️ Alterações no Banco de Dados

### Tabelas Modificadas
- **Terminais:** Migração para WallClub com tipo DATETIME
- **Operadores:** Flag de ativo adicionada
- **ExtratoPOS:** Campo `processado` adicionado
- **Ofertas:** Campos `data_disparo` e `loja_id` adicionados

### Novos Campos em TransactionData POS
- `desconto_wall_parametro_id`
- `cashback_wall_parametro_id`
- `cashback_wall_valor`
- `cashback_loja_regra_id`
- `cashback_loja_valor`

---

## 📚 Documentação

### Atualizações
- Correção de débito de cashback em `ContaDigitalService`
- Unificação do `transactiondata_pos`
- Plano de refatoração da base de transações unificadas
- Documentação técnica sobre lógica de impressão de slips POS
- Documentação completa de uso do `ConfigManager`
- Reorganização de documentação em pastas

### Scripts de Validação
- Detecção de decorators `@require_http_methods`
- Ampliação de detecção de decorators de API interna
- Validação de Risk Engine
- Remoção de validação de variáveis obsoletas
- Atualização de contadores de progresso (6 etapas)

---

## ⚙️ Infraestrutura

### Celery
- Flag `-E` para habilitar eventos no worker
- Configuração de concurrency: 5
- Pool mode: solo
- Limit tasks per child configurado
- Desabilitação de tarefa periódica de cargas completas Pinbank

### Nginx
- Configuração específica para APIs Own Financial sem rate limit
- Atualização de comandos de deploy
- Inclusão de wallclub-portais

---

## ⚠️ Breaking Changes

### 1. Conta Digital - Débito de Cashback
**Antes:**
```python
# Debitava sempre de saldo_atual
ContaDigitalService.debitar(cliente_id, canal_id, valor, descricao)
```

**Depois:**
```python
# Verifica campo afeta_cashback do tipo de movimentação
# Se afeta_cashback=True: debita de cashback_disponivel
# Se afeta_cashback=False: debita de saldo_atual
ContaDigitalService.debitar(cliente_id, canal_id, valor, descricao, tipo_codigo='CASHBACK_DEBITO')
```

**Ação Necessária:** Revisar tipos de movimentação e garantir que `afeta_cashback` está configurado corretamente.

---

### 2. Calculadora - Valor do Cupom
**Antes:**
```python
# Calculadora não recebia informação de cupom
calculadora.calcular(valor_original=10.00)
```

**Depois:**
```python
# Calculadora ajusta cálculos considerando cupom
calculadora.calcular(valor_original=10.00, cupom_valor=5.00)
```

**Ação Necessária:** Nenhuma - ajuste é interno e retrocompatível.

---

### 3. Tabela Terminais
**Antes:**
```sql
-- Tabela em outro schema
-- Campos com tipos diferentes
```

**Depois:**
```sql
-- Tabela migrada para WallClub
-- Campos com tipo DATETIME
```

**Ação Necessária:** Executar migration antes do deploy.

---

### 4. API de Saldo - Deprecated
**Antes:**
```python
response = APIInternaService.chamar_api_interna(
    endpoint='/api/internal/cliente/consultar_saldo/',
    ...
)
```

**Depois (Recomendado):**
```python
response = APIInternaService.chamar_api_interna(
    endpoint='/api/internal/cliente/consultar_saldo_cashback/',
    ...
)
```

**Ação Necessária:** Migrar para novo endpoint. Endpoint antigo ainda funciona mas será removido em versão futura.

---

### 5. Status de Compra Informativa
**Antes:**
```python
status = 'CONCLUIDA'
```

**Depois:**
```python
status = 'PROCESSADA'
```

**Ação Necessária:** Ajustar filtros e queries que dependem do status `CONCLUIDA`.

---

## 📊 Estatísticas da Release

- **Total de Commits:** 420
- **Arquivos Alterados:** ~150+
- **Linhas Adicionadas:** ~15.000+
- **Linhas Removidas:** ~5.000+
- **Módulos Impactados:** 12+
- **Novos Endpoints:** 10+
- **Correções de Bugs:** 40+
- **Refatorações:** 50+
- **Melhorias de Logs:** 80+

---

## 🔄 Procedimento de Deploy

### 1. Pré-requisitos
```bash
# Backup do banco de dados
pg_dump wallclub_production > backup_pre_v2.2.0.sql

# Verificar variáveis de ambiente
python manage.py check_env_vars

# Executar script de validação
./scripts/validacao_completa.sh
```

### 2. Migrations
```bash
# Aplicar migrations
python manage.py migrate

# Verificar integridade
python manage.py check
```

### 3. Deploy dos Serviços
```bash
# Django
sudo systemctl restart wallclub-django

# APIs
sudo systemctl restart wallclub-apis

# Portais
sudo systemctl restart wallclub-portais

# Celery
sudo systemctl restart wallclub-celery-worker
sudo systemctl restart wallclub-celery-beat

# Nginx
sudo systemctl reload nginx
```

### 4. Validação Pós-Deploy
```bash
# Verificar logs
sudo tail -f /var/log/wallclub/django.log
sudo tail -f /var/log/wallclub/celery.log

# Testar endpoints críticos
curl -X POST https://api.wallclub.com.br/posp2/trdata_pinbank/
curl -X GET https://api.wallclub.com.br/api/internal/cliente/consultar_saldo_cashback/

# Verificar base unificada
python manage.py shell
>>> from posp2.tasks import carregar_base_unificada_pos
>>> carregar_base_unificada_pos()
```

### 5. Monitoramento
- Verificar logs de erro nos primeiros 30 minutos
- Monitorar métricas de performance
- Validar processamento de transações POS
- Verificar carga da base unificada

---

## 🧪 Testes Recomendados

### Fluxo Completo POS
1. Processar transação sem cupom/cashback
2. Processar transação com cupom
3. Processar transação com cashback
4. Processar transação com cupom + cashback
5. Verificar SLIP gerado
6. Validar base unificada

### Fluxo Checkout
1. Simular parcelas com cashback
2. Aplicar cupom de desconto
3. Validar cupom inválido
4. Processar pagamento
5. Verificar extrato

### Cadastro Own Financial
1. Cadastrar nova loja
2. Upload de documentos
3. Editar tarifas
4. Processar transação Own

---

## 📞 Suporte

Em caso de problemas:
1. Verificar logs em `/var/log/wallclub/`
2. Consultar documentação em `docs/`
3. Executar script de validação: `./scripts/validacao_completa.sh`
4. Contatar equipe de desenvolvimento

---

## 🎯 Próximas Versões

### v2.3.0 (Planejado)
- Melhorias no sistema de antecipação
- Dashboard de métricas em tempo real
- Integração com novos gateways de pagamento
- Otimizações de performance

---

**Desenvolvido por:** Equipe WallClub
**Data de Release:** 26/01/2026
**Versão:** 2.2.0 Stable
