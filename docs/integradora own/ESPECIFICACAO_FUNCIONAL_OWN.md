# ESPECIFICAÇÃO FUNCIONAL - INTEGRAÇÃO OWN FINANCIAL

**Versão:** 1.0  
**Data:** 04/11/2025  
**Responsável:** Product Owner  
**Status:** Especificação Inicial

---

## 📋 ÍNDICE

1. [Visão Geral](#visão-geral)
2. [Objetivos do Projeto](#objetivos-do-projeto)
3. [Comparativo: Pinbank vs Own Financial](#comparativo-pinbank-vs-own-financial)
4. [Decisões Estratégicas](#decisões-estratégicas)
5. [Processos e Fluxos](#processos-e-fluxos)
6. [Funcionalidades por Módulo](#funcionalidades-por-módulo)
7. [Novas Funcionalidades](#novas-funcionalidades)
8. [Plano de Trabalho](#plano-de-trabalho)
9. [Riscos e Mitigações](#riscos-e-mitigações)

---

## 🎯 VISÃO GERAL

### Contexto

O WallClub atualmente opera exclusivamente com **Pinbank** como gateway/adquirente. A integração com **Own Financial** visa:

1. **Diversificar** adquirentes (reduzir dependência única)
2. **Ampliar** funcionalidades (gestão de estabelecimentos, equipamentos)
3. **Oferecer** opções para diferentes perfis de loja
4. **Negociar** melhores condições comerciais

### O que é Own Financial?

Own Financial é uma **adquirente** que opera através de:

- **Transações:** Via protocolo TEF usando SiTef/CardSE
- **Gestão:** Via APIs REST para consultas e configurações
- **Bandeiras:** Visa, Mastercard, Elo (crédito e débito)

### Diferencial Principal

Enquanto Pinbank oferece API REST direta, Own Financial opera via **TEF** (protocolo de máquinas de cartão), exigindo software intermediário (SiTef).

---

## 🎯 OBJETIVOS DO PROJETO

### Objetivos de Negócio

1. Reduzir risco operacional com múltiplos adquirentes
2. Melhorar margens através de negociação de taxas
3. Ampliar portfólio de funcionalidades
4. Atender diferentes perfis de estabelecimentos

### Objetivos Funcionais

1. Permitir lojas operarem com Own ou Pinbank
2. Manter experiência unificada (transparência)
3. Adicionar funcionalidades de gestão
4. Implementar consultas para ambos gateways

---

## 📊 COMPARATIVO: PINBANK VS OWN FINANCIAL

### Transações

| Aspecto | Pinbank | Own Financial |
|---------|---------|---------------|
| Método | API REST | TEF (via SiTef) |
| Tempo resposta | 1-3s | 3-5s |
| Tokenização | ✅ Sim | ❌ Não |
| Bandeiras | Visa, Master, Elo | Visa, Master, Elo |

### Consultas

| Aspecto | Pinbank | Own Financial |
|---------|---------|---------------|
| Consulta transações | ✅ Sim | ✅ Sim |
| Consulta liquidações | ✅ Sim | ✅ Sim (mais detalhado) |
| Dados antecipação | ❌ Não | ✅ Sim |

### Gestão

| Funcionalidade | Pinbank | Own Financial |
|----------------|---------|---------------|
| Credenciamento | ❌ Manual | ✅ API completa |
| Gestão equipamentos | ❌ Não | ✅ Sim |
| Gestão canais WL | ❌ Não | ✅ Sim |
| Consulta tarifas | ❌ Não | ✅ Sim |

---

## 🎯 DECISÕES ESTRATÉGICAS

### 1. Seleção de Gateway

**Decisão:** WallClub escolhe gateway no cadastro da loja

**Critérios:**
- Perfil da loja (online vs físico)
- Faturamento esperado
- Necessidades específicas

**Regra Inicial:**
- Padrão: Pinbank
- Own: Sob demanda

### 2. Troca de Gateway

**Decisão:** Permitir troca com restrições

**Processo:**
1. Loja solicita via portal
2. WallClub analisa viabilidade
3. Se aprovado: credencia no novo gateway
4. Transações novas vão para novo gateway
5. Transações antigas permanecem no original

**Impactos:**
- Recorrências precisam ser recriadas
- Cartões tokenizados não migram
- Histórico fica dividido

### 3. Convivência

**Decisão:** Loja opera com UM gateway por vez

**Exceção:** Período de transição (máx 30 dias)

### 4. Credenciamento Own

**Decisão:** Processo híbrido

**Fluxo:**
1. Loja preenche formulário extenso
2. Loja faz upload de documentos
3. WallClub valida
4. WallClub envia para Own via API
5. Own analisa (1-3 dias)
6. Own aprova/reprova

### 5. Infraestrutura TEF

**Decisão:** SiTef em servidor dedicado

**Justificativa:**
- Permite transações web
- Centraliza gestão
- Facilita manutenção

---

## 🔄 PROCESSOS E FLUXOS

### Processo 1: Cadastro Nova Loja (Own)

```
1. Loja preenche cadastro completo:
   - Dados cadastrais (CNPJ, razão, CNAE, MCC)
   - Endereço completo
   - Dados bancários
   - Faturamento previsto
   - Configuração antecipação
   - Dados dos sócios

2. Loja faz upload documentos:
   - RG frente/verso (sócios)
   - CPF (sócios)
   - Comprovante endereço
   - Contrato social

3. WallClub valida dados

4. WallClub envia para Own via API
   - Recebe protocolo

5. Own analisa (1-3 dias)

6. Own retorna resultado:
   - Aprovado: número contrato
   - Reprovado: motivo

7. WallClub notifica loja

8. Se aprovado: loja pode operar
```

### Processo 2: Transação de Venda

**Pinbank (atual):**
```
Cliente → Checkout → Pinbank API → Resposta (1-3s)
```

**Own (novo):**
```
Cliente → Checkout → SiTef → CardSE → Own → Resposta (3-5s)
```

**Diferença para usuário:** Nenhuma (transparente)

### Processo 3: Consulta Transações

```
1. Lojista acessa portal
2. Sistema identifica gateway da loja
3. Sistema consulta API apropriada
4. Sistema normaliza dados
5. Sistema exibe (mesma interface)
```

### Processo 4: Conciliação

```
1. Carga automática diária (02:00)
2. Sistema busca transações (API do gateway)
3. Sistema salva em BaseTransacoesGestao
4. Lojista vê no portal (mesma tela)
```

### Processo 5: Troca de Gateway

```
1. Loja solicita troca
2. WallClub analisa e comunica impactos
3. Se loja confirma: inicia credenciamento
4. Após aprovação: altera gateway_ativo
5. Transações novas vão para novo gateway
6. Período transição (até 30 dias)
```

---

## 🖥️ FUNCIONALIDADES POR MÓDULO

### Portal Lojista

#### Existentes (Mantém)

**Menu: Transações**
- Listar transações
- Filtrar por período/status
- Ver detalhes
- **Novo:** Coluna "Gateway"

**Menu: Extrato Financeiro**
- Valores a receber
- Valores recebidos
- **Novo:** Filtrar por gateway

**Menu: Conciliação**
- Comparar vendas vs recebimentos
- Mantém funcionamento

#### Novas (Own)

**Menu: Configurações → Gateway**
- Ver gateway atual
- Solicitar troca

**Menu: Credenciamento Own**
- Preencher dados
- Upload documentos
- Acompanhar protocolo

**Menu: Equipamentos POS**
- Listar equipamentos
- Solicitar novo/troca

**Menu: Antecipação**
- Ver configuração
- Ver histórico
- Solicitar alteração

### Portal Admin

#### Existentes (Mantém)

**Menu: Lojas**
- Listar/criar/editar
- **Novo:** Selecionar gateway

**Menu: Transações**
- Ver todas transações
- **Novo:** Filtrar por gateway

#### Novas (Own)

**Menu: Credenciamento Own**
- Listar solicitações
- Validar documentos
- Enviar para Own
- Acompanhar protocolos

**Menu: Gestão Gateways**
- Dashboard comparativo
- Volume por gateway
- Performance

**Menu: Equipamentos POS**
- Listar todos
- Associar/trocar/desativar

**Menu: Protocolos Own**
- Listar protocolos
- Ver status
- Reenviar se reprovado

**Menu: Cestas Tarifas**
- Listar cestas disponíveis
- Ver tarifas por modalidade

---

## 🆕 NOVAS FUNCIONALIDADES

### 1. Credenciamento Automatizado

**Descrição:** Processo completo via portal

**Benefício:**
- Reduz trabalho manual
- Acelera onboarding
- Rastreabilidade

**Telas:**
- Formulário credenciamento
- Upload documentos
- Validação (admin)
- Acompanhamento protocolos

### 2. Gestão Equipamentos POS

**Descrição:** Controle de equipamentos

**Funcionalidades:**
- Listar por loja
- Associar/trocar/desativar
- Ver histórico

### 3. Gestão Antecipação

**Descrição:** Configuração de antecipação

**Funcionalidades:**
- Ver configuração atual
- Ver histórico detalhado
- Solicitar alteração

### 4. Consulta Cestas Tarifas

**Descrição:** Transparência de preços

**Funcionalidades:**
- Listar cestas
- Ver tarifas por modalidade
- Comparar cestas

### 5. Dashboard Gateways

**Descrição:** Visão consolidada

**Métricas:**
- Volume por gateway
- Taxa de aprovação
- Tempo médio resposta
- Valores transacionados

### 6. Gestão Canais White Label

**Descrição:** Para sub-adquirentes

**Funcionalidades:**
- Cadastrar canais
- Associar estabelecimentos
- Relatórios por canal

---

## 📅 PLANO DE TRABALHO

### Fase 0: Preparação (1 semana)

**Objetivos:**
- Validar especificação
- Definir prioridades
- Obter aprovações

**Entregas:**
- Especificação aprovada
- Cronograma detalhado
- Alocação recursos

### Fase 1: Infraestrutura e Consultas (2-3 semanas)

**Objetivos:**
- Conectividade com Own
- Consultas básicas

**Entregas:**
- Autenticação OAuth 2.0
- API consulta transações
- API consulta liquidações
- Cargas automáticas
- Exibição no portal

### Fase 2: Credenciamento (2-3 semanas)

**Objetivos:**
- Processo de credenciamento
- Cadastro via portal

**Entregas:**
- Formulário completo
- Upload documentos
- Validação interna
- Integração API Own
- Acompanhamento protocolos

### Fase 3: Infraestrutura TEF (3-4 semanas)

**Objetivos:**
- Instalar SiTef
- Processar transações

**Entregas:**
- SiTef configurado
- Cliente SiTef (socket)
- Gateway Own integrado
- Roteador de gateways

### Fase 4: Gestão Equipamentos (2 semanas)

**Objetivos:**
- Controle de equipamentos

**Entregas:**
- CRUD equipamentos
- Associação a lojas
- Histórico

### Fase 5: Funcionalidades Extras (2-3 semanas)

**Objetivos:**
- Antecipação, cestas, canais

**Entregas:**
- Gestão antecipação
- Consulta cestas
- Gestão canais WL
- Dashboard gateways

### Fase 6: Testes e Homologação (2 semanas)

**Objetivos:**
- Testes completos
- Validação usuários

**Entregas:**
- Testes integração
- Testes E2E
- Homologação usuários
- Documentação

### Fase 7: Deploy Produção (1 semana)

**Objetivos:**
- Implantação gradual

**Entregas:**
- Deploy infraestrutura
- Migração lojas piloto
- Monitoramento
- Suporte

---

## ⚠️ RISCOS E MITIGAÇÕES

### Risco 1: Complexidade TEF

**Descrição:** Protocolo TEF mais complexo que API REST

**Impacto:** Alto  
**Probabilidade:** Alta

**Mitigação:**
- Contratar consultoria especializada
- Testes extensivos
- Documentação detalhada
- Treinamento equipe

### Risco 2: Tempo Credenciamento

**Descrição:** Own demora 1-3 dias para aprovar

**Impacto:** Médio  
**Probabilidade:** Alta

**Mitigação:**
- Comunicar prazo claramente
- Manter Pinbank como padrão
- Processo de validação interna antes

### Risco 3: Dependência SiTef

**Descrição:** Licença e manutenção SiTef

**Impacto:** Alto  
**Probabilidade:** Média

**Mitigação:**
- Negociar contrato adequado
- Plano de contingência
- Monitoramento proativo

### Risco 4: Migração de Lojas

**Descrição:** Lojas podem querer trocar gateway

**Impacto:** Médio  
**Probabilidade:** Média

**Mitigação:**
- Processo claro de troca
- Comunicação de impactos
- Suporte dedicado

### Risco 5: Performance TEF

**Descrição:** TEF pode ser mais lento (3-5s)

**Impacto:** Baixo  
**Probabilidade:** Alta

**Mitigação:**
- Otimizar conexões
- Timeout adequado
- Feedback visual ao usuário

---

## 📊 MÉTRICAS DE SUCESSO

### Métricas de Adoção

- Número de lojas usando Own
- % de transações por gateway
- Taxa de aprovação credenciamento

### Métricas Operacionais

- Tempo médio credenciamento
- Taxa de sucesso transações
- Tempo resposta transações
- Uptime SiTef

### Métricas Financeiras

- Volume transacionado por gateway
- Economia em taxas
- Custo operacional

### Métricas de Qualidade

- Taxa de erro transações
- Tempo resolução incidentes
- Satisfação lojistas

---

## 📝 PRÓXIMOS PASSOS

1. **Validar especificação** com stakeholders
2. **Priorizar funcionalidades** (MVP vs completo)
3. **Definir cronograma** detalhado
4. **Alocar recursos** (dev, QA, infra)
5. **Contratar licença SiTef**
6. **Iniciar Fase 1** (Infraestrutura)

---

**Documento elaborado por:** Product Owner  
**Revisão necessária:** Tech Lead, Arquiteto, Stakeholders  
**Próxima revisão:** Após validação inicial
