# RELEASE 2.2.0 - CHANGELOG

**Data:** 26/01/2026
**Total de Commits:** 420
**Branch:** release-2.2.0

---

## 📊 RESUMO EXECUTIVO

Esta release contém melhorias significativas em:
- Integração com Own Financial (cadastro de lojas)
- Sistema de Cupons e Cashback
- Base de Transações Unificadas
- Relatórios e Exportações
- Sistema de Ofertas
- Segurança e Rate Limiting
- Logs e Monitoramento

---

## 🏦 1. INTEGRAÇÃO OWN FINANCIAL (50+ commits)

### **Cadastro de Lojas**
- Implementação completa do fluxo de cadastro Own Financial
- Upload de documentos do responsável
- Validação de campos e tratamento de erros 400
- Campos editáveis: tarifas, tipo de antecipação, hash de aceite
- Migração de class-based para function-based views
- Autenticação CSRF e credenciais em requisições fetch
- Carregamento de credenciais do Secrets Manager
- Configuração nginx para APIs Own sem rate limit

### **Processamento de Transações**
- Integração com API Own para processamento POS
- Logs detalhados de transações Pinbank
- Automação de carga após pagamentos
- Tratamento de erros e validações

### **Campos Adicionados**
- Gateway Ativo
- URL da Loja
- Aceita E-commerce
- PIX
- Hierarquia WallClub
- CNPJ como identificadorCliente
- CPF do responsável
- Tarifação e tipo de antecipação

---

## 🎟️ 2. SISTEMA DE CUPONS (30+ commits)

### **Validação de Cupons**
- Endpoint interno para gerenciamento de cupons
- Validação em tempo real no checkout web
- Validação de loja existente
- Separação de rotas checkout e POS
- Campo de cupom habilitado após seleção de parcela
- Limpeza de cupom ao trocar parcela

### **Integração com Calculadora**
- Modificação da calculadora para receber valor do cupom
- Ajuste no cálculo do valor final quando parte0 é zero
- Uso de amount (valor real cobrado) nos cálculos
- Campo desconto_wall_parametro_id no processamento POS

### **Tratamento de Erros**
- Logs detalhados de validação
- Tratamento de erro para PORTAIS_INTERNAL_URL indefinida
- Melhoria no tratamento de erros e logging

---

## 💰 3. SISTEMA DE CASHBACK (40+ commits)

### **Cálculo de Cashback**
- Reimplementação com busca direta de parâmetros Wall
- Logs detalhados para debug
- Correção de verificação de tipo wall
- Ajuste na condição para wall 'S'
- Cálculo de cashback Wall integrado

### **Conta Digital**
- Suporte a débito de cashback em ContaDigitalService
- Correção do débito de cashback (afeta_cashback)
- Informações de cashback no extrato
- Endpoint consultar_saldo_cashback
- Marca consultar_saldo como deprecated

### **Movimentações**
- Registro de compras informativas no extrato
- Atualização de tipo de cashback
- Ajuste de nome do plano de cashback
- Status de compra informativa: PROCESSADA (não CONCLUIDA)
- Substituição de ContaDigitalService por MovimentacaoContaDigital

### **Campos Adicionados**
- cashback_wall_parametro_id
- cashback_wall_valor
- cashback_loja_regra_id
- cashback_loja_valor
- cashback_concedido

---

## 📊 4. BASE DE TRANSAÇÕES UNIFICADAS (60+ commits)

### **Implementação**
- Carga de base unificada para transações POS Pinbank
- Carga de transações credenciadora
- Carga automática a cada 30 minutos
- Inserção em base_transacoes_unificadas
- Otimização de query usando subquery para registros únicos por NSU

### **Auditoria e Monitoramento**
- Auditoria de mudanças na base unificada
- Updates seletivos otimizados
- Logs de tempo para INSERT e UPDATE
- Logs de debug para rastreamento de NSU
- Monitoramento de inserção e processamento

### **Cancelamentos**
- Atualização de cancelamentos na carga
- Recálculo de cancelamento NSU
- Remoção de filtros de data
- Log detalhado de traceback para erros

### **Campos e Validações**
- Conversão segura de valores para float
- Correção de cálculo de encargos
- Correção de cálculo de tarifas
- Correção de cálculo do valor da parcela quando vparcela é nulo

---

## 📈 5. RELATÓRIOS E EXPORTAÇÕES (25+ commits)

### **RPR (Relatório de Produção e Receita)**
- Formatação monetária brasileira em totalizadores
- Conversão de percentuais para decimais
- Cálculo de var15 e variavel_nova_15 na linha totalizadora
- Cálculo de novas variáveis totalizadoras
- Formatação de colunas percentuais
- Linha de totais em exportações
- Botão de exportação de resumo
- Reposicionamento de métrica de Lançamentos Manuais

### **Exportações Excel**
- Suporte a tipo Decimal em colunas percentuais
- Formatação de valores monetários negativos
- Tratamento de erros no cálculo de totais
- Padronização de formatação percentual
- Validação de strings vazias

### **Gestão de Transações**
- Formatação de colunas percentuais
- Padronização de espaços em branco
- Filtro de data para transações a partir de 01/10/2025
- Campo processado em ExtratoPOS
- Melhoria de formatação de data

---

## 🎁 6. SISTEMA DE OFERTAS (20+ commits)

### **Funcionalidades**
- Disparo automático agendado de ofertas
- Vinculação com loja
- Validação de disparo
- Restrição de edição de ofertas já disparadas
- Modo visualização para ofertas disparadas
- Lock otimista para evitar disparo duplicado

### **Filtros e Permissões**
- Filtro baseado no tipo de usuário (lojista/grupo econômico)
- Uso de LojistaDataMixin para filtrar por lojas acessíveis
- Verificação de permissões de loja
- Suporte para diferentes cases de atributos de loja
- Logs de debug para rastreamento de filtragem

### **Interface**
- Botão voltar
- Lista todas as lojas (não apenas ativas)
- Campos de data de disparo e loja_id na edição
- Substituição de API interna por OfertaService
- Bloqueio de edição após disparo

---

## 🔒 7. SEGURANÇA E RATE LIMITING (15+ commits)

### **Implementações**
- Rate limiting POS
- Gestão de cartões
- Autenticação OAuth para Risk Engine
- Validação de Risk Engine no script de validação
- Remoção de OAuth para chamadas internas do Risk Engine

### **Validações**
- Verificação de autenticação manual sem redirect para APIs AJAX
- Uso de @login_required para APIs AJAX
- Autenticação e permissão de usuário autenticado
- CSRF e credenciais em requisições fetch

---

## 📝 8. LOGS E MONITORAMENTO (80+ commits)

### **Logs Detalhados**
- Rastreamento de processamento de NSU
- Monitoramento de transações Pinbank
- Debug do cálculo de cashback
- Rastreamento de filtragem de ofertas
- Importação e instanciação da CalculadoraDesconto
- Decisão de encargo/desconto em transação POS
- Mudanças de status NSU
- Recorrências e correção de referência de vendedor

### **Logs de Entrada/Saída**
- Endpoints de processamento de transações
- Payload antes do envio de push notifications
- Busca de canal
- Determinação de portal do usuário

### **Simplificação**
- Simplificação de nomes dos módulos
- Remoção de movimentações informativas
- Padronização de logs

---

## 🛠️ 9. REFATORAÇÕES E MELHORIAS (50+ commits)

### **Código**
- Migração de class-based para function-based views
- Move hardcoded URLs para environment variables
- Lazy imports para evitar importações circulares
- Reordenação de imports
- Padronização de formatação
- Remoção de arquivos obsoletos

### **Calculadora**
- Implementação de calculadora de base gestão para POS
- Serviço de cálculo de desconto no módulo POSP2
- Conversão de valores de string para float
- Cache control headers

### **Checkout**
- Simplificação de simulação de parcelas com cashback integrado
- Conversão de valores de cálculo de pagamento
- Integração com TransacoesPinbankService

### **Serviços**
- Determinação automática de portal e canal em emails
- Descoberta automática de tasks de recorrência
- Move imports para function scope
- Replace datetime.now() com timezone.now()

---

## 🗄️ 10. BANCO DE DADOS E MODELOS (15+ commits)

### **Alterações**
- Mudança da tabela de terminais para WallClub
- Tipo DATETIME
- Flag de ativo para operadores
- Atualização de consulta de vínculos
- Histórico de terminais inativos
- Ajuste de filtros de data

### **Novos Campos**
- desconto_wall_parametro_id
- cashback_wall_parametro_id
- cashback_wall_valor
- cashback_loja_regra_id
- cashback_loja_valor
- processado (ExtratoPOS)
- data_disparo e loja_id (Ofertas)

---

## 📚 11. DOCUMENTAÇÃO (20+ commits)

### **Atualizações**
- Correção de débito de cashback em ContaDigitalService
- Unificação do transactiondata_pos
- Plano de refatoração da base de transações unificadas
- Documentação técnica sobre lógica de impressão de slips POS
- Documentação completa de uso do ConfigManager
- Reorganização de documentação
- Novos guias técnicos
- Atualização de branch para release-2.2.0

### **Scripts de Validação**
- Detecção de decorators @require_http_methods
- Ampliação de detecção de decorators de API interna
- Remoção de validação de variáveis obsoletas
- Atualização de contadores de progresso
- Validação de Risk Engine
- Ajuste de padrões de nomenclatura

---

## ⚙️ 12. INFRAESTRUTURA E DEPLOY (15+ commits)

### **Celery**
- Flag -E para habilitar eventos no worker
- Configuração de concurrency e limit tasks per child
- Ajuste de concurrency para 5 e pool solo mode
- Desabilitação de tarefa periódica de cargas completas Pinbank

### **Nginx**
- Configuração para APIs Own Financial sem rate limit
- Atualização de comandos de deploy
- Inclusão de apis e nginx
- Inclusão de wallclub-portais

### **Comandos de Deploy**
- Atualização para incluir apis
- Atualização para incluir nginx
- Logs de depuração para busca de canal

---

## 🐛 13. CORREÇÕES DE BUGS (40+ commits)

### **Principais Correções**
- Correção de débito de cashback (afeta_cashback)
- Correção de cálculo de encargos e tarifas
- Correção de cálculo do valor da parcela
- Correção de conversão de valores para float
- Correção de verificação de tipo wall
- Correção de importação do timedelta
- Correção de tipo_codigo de CASHBACK_LOJA para CASHBACK_CREDITO
- Correção de porta do Risk Engine (8004 → 8008)

### **Validações**
- Permitir quantidade_pos = 0
- Adicionar hashAceite de volta ao payload
- Usar CNPJ como identificadorCliente
- Incluir CPF do responsável em documentosSocios
- Não marcar campo de busca CNAE como obrigatório
- Remover exibição de 'None' em campos vazios

---

## 📊 ESTATÍSTICAS

- **Total de Commits:** 420
- **Arquivos Alterados:** ~150+
- **Linhas Adicionadas:** ~15.000+
- **Linhas Removidas:** ~5.000+
- **Módulos Impactados:** 12+
- **Novos Endpoints:** 10+
- **Correções de Bugs:** 40+
- **Refatorações:** 50+

---

## ⚠️ BREAKING CHANGES

1. **Conta Digital:** Alteração na lógica de débito de cashback (campo afeta_cashback)
2. **Calculadora:** Modificação para receber valor do cupom
3. **Tabela Terminais:** Mudança para WallClub com tipo DATETIME
4. **API Saldo:** consultar_saldo marcado como deprecated (usar consultar_saldo_cashback)
5. **Status Compra:** Mudança de CONCLUIDA para PROCESSADA

---

## 🚀 PRÓXIMOS PASSOS

1. Testar integração completa Own Financial em produção
2. Validar cálculos de cashback e cupons
3. Monitorar performance da base unificada
4. Revisar logs e ajustar conforme necessário
5. Documentar APIs internas adicionadas
6. Validar exportações RPR com novos campos
