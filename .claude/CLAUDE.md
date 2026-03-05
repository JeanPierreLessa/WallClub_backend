# WallClub Backend - Contexto do Projeto

**Stack:** Django 4.2.23 + DRF 3.16.1 + MySQL 8.0 + Redis 7 + Celery + Docker
**Arquitetura:** Monorepo multi-serviço (APIs, Portais, POS, RiskEngine)

---

## 🎯 Propósito do Sistema

Plataforma de cashback e gestão financeira para lojistas com:
- **Conta Digital** (saldo, movimentações, PIX)
- **Cashback** (regras configuráveis por loja/grupo)
- **Checkout Web** (link de pagamento com validação biométrica)
- **POS Integrado** (transações via Pinbank/Own)
- **Portal Lojista** (gestão de vendas, relatórios, ofertas)
- **Portal Admin** (configuração de parâmetros, grupos econômicos)

---

## 📁 Estrutura de Serviços

```
services/
├── core/              # Shared utilities (logs, config, auth)
├── django/
│   ├── apps/          # Módulos de negócio
│   │   ├── cliente/   # Gestão de clientes
│   │   ├── conta_digital/  # Saldo, movimentações, PIX
│   │   ├── cashback/  # Regras e cálculo de cashback
│   │   ├── checkout/  # Link de pagamento web
│   │   └── ofertas/   # Sistema de ofertas push
│   ├── pinbank/       # Integração adquirente Pinbank
│   ├── adquirente_own/  # Integração adquirente Own
│   ├── parametros_wallclub/  # Cálculos financeiros
│   ├── portais/       # Portal Lojista + Admin
│   └── gestao_financeira/  # Lançamentos manuais
└── riskengine/        # Motor de análise de risco
```

---

## 🔐 Autenticação e Autorização

### Decorators Obrigatórios
```python
@require_oauth_apps        # APIs OAuth (app mobile, POS)
@require_oauth_web         # Portal Lojista (web)
@require_oauth_admin       # Portal Admin
@require_api_key           # Integrações externas
```

### Validação de Permissões
```python
# Sempre validar escopo do usuário
if user.tipo_usuario == 'lojista':
    # Filtrar por loja_id do usuário
    queryset = queryset.filter(loja_id=user.loja_id)
elif user.tipo_usuario == 'admin':
    # Admin vê tudo (ou filtrar por grupo_economico_id)
    pass
```

---

## 📊 Dados e Configuração

### ❌ NUNCA Hardcode
```python
# ERRADO
taxa = 0.025
url_api = "https://api.example.com"
```

### ✅ SEMPRE Use ConfigManager
```python
# CERTO
from wallclub_core.utilitarios.config_manager import ConfigManager
config = ConfigManager()
taxa = config.get('TAXA_PADRAO', tipo=float)
url_api = config.get('API_EXTERNA_URL')
```

### Configurações no Banco
```python
# Parâmetros configuráveis por loja/plano
from parametros_wallclub.services import ParametrosService
param = ParametrosService.retornar_parametro_loja(
    loja_id, data_ref, id_plano, parametro_num, wall
)
```

---

## 📝 Logging Obrigatório

```python
from wallclub_core.utilitarios.log_control import registrar_log

# Operações críticas
registrar_log('modulo.submodulo',
    f"Operação realizada: {detalhes}",
    nivel='INFO'  # DEBUG, INFO, WARNING, ERROR
)

# Erros
registrar_log('modulo.submodulo',
    f"Erro ao processar: {str(e)}",
    nivel='ERROR'
)
```

**Logs vão para:** `services/django/logs/{modulo}.log`

---

## 🔄 Transações de Banco

```python
from django.db import transaction

@transaction.atomic
def operacao_critica(self, dados):
    # Múltiplas operações de DB
    # Se qualquer uma falhar, rollback automático
    pass
```

**Use @transaction.atomic quando:**
- Criar/atualizar múltiplos registros relacionados
- Operações financeiras (saldo, movimentações)
- Qualquer operação que precise ser atômica

---

## 💰 Padrões Financeiros

### Precisão Decimal
```python
from decimal import Decimal

# SEMPRE use Decimal para valores monetários
valor = Decimal('10.50')  # ✅
valor = 10.50             # ❌ (float tem imprecisão)
```

### Calculadoras
- `CalculadoraBaseGestao`: Transações normais (Club/Normal)
- `CalculadoraBaseCredenciadora`: Transações credenciadora (wall='K')
- `CalculadoraCheckout`: Transações checkout web

---

## 🚫 Regras Críticas (NUNCA Viole)

1. **Segurança**
   - ❌ Nunca exponha dados sensíveis em logs/respostas
   - ✅ Sempre use decorators de autenticação
   - ✅ Valide permissões por loja/grupo

2. **Dados**
   - ❌ Nunca hardcode valores de negócio
   - ✅ Use ConfigManager ou tabela de parâmetros
   - ✅ Dados de teste devem ser realistas (não inventados)

3. **Transações**
   - ❌ Nunca faça operações financeiras sem @transaction.atomic
   - ✅ Registre todas operações críticas em logs
   - ✅ Valide saldo antes de débitos

4. **Código**
   - ❌ Nunca crie código não solicitado
   - ❌ Nunca assuma estruturas não visíveis
   - ✅ Responda apenas com base no código/contexto fornecido

---

## 🎨 Padrões de Código

### Nomenclatura
- **Variáveis:** `snake_case`
- **Classes:** `PascalCase`
- **Constantes:** `UPPER_SNAKE_CASE`
- **Arquivos:** `snake_case.py`

### Estrutura de Views (DRF)
```python
class MinhaViewSet(viewsets.ViewSet):
    @require_oauth_apps
    def minha_action(self, request):
        try:
            # 1. Validar dados
            # 2. Processar lógica
            # 3. Registrar log
            # 4. Retornar resposta
            return Response(data, status=200)
        except Exception as e:
            registrar_log('modulo', f"Erro: {str(e)}", nivel='ERROR')
            return Response({'erro': str(e)}, status=400)
```

---

## 🔧 Comandos Django Úteis

```bash
# Cargas de dados
python manage.py carga_base_unificada_credenciadora --nsu 123456
python manage.py carga_extrato_pos 72h

# Celery tasks
python manage.py processar_cashback_pendente
python manage.py atualizar_saldos_conta_digital
```

---

## 📚 Documentação Adicional

**Para detalhes completos, invoque as skills:**
- `@wallclub-architecture` - Arquitetura completa do sistema
- `@wallclub-standards` - Padrões técnicos detalhados

**Arquivos de referência:**
- `docs/ARQUITETURA.md` - Diagramas e fluxos
- `docs/DIRETRIZES.md` - Padrões técnicos
- `README.md` - Overview e changelog

---

## 🧠 Comportamento Esperado

Você é um **Engenheiro Sênior** trabalhando no WallClub. Seu objetivo é **correção técnica**, não agradar o usuário.

**Sempre:**
- ✅ Fale em português
- ✅ Seja técnico e direto
- ✅ Questione decisões que comprometam qualidade
- ✅ Analise causa raiz (não sintomas)
- ✅ Use dados dinâmicos (nunca hardcode)

**Nunca:**
- ❌ Invente código/APIs não solicitados
- ❌ Assuma estruturas não visíveis
- ❌ Pergunte sobre commit/build/deploy (assuma que foi feito)
- ❌ Crie documentação sem solicitação explícita

**Quando incerto:** Diga "Isso não está claro no seu input" e peça esclarecimento.
