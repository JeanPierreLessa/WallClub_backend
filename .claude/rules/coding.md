# WallClub - Regras de Código

## Configuração e Dados

**NUNCA hardcode valores de negócio.**

```python
# ❌ ERRADO
taxa = 0.025
url_api = "https://api.example.com"

# ✅ CERTO
from wallclub_core.utilitarios.config_manager import ConfigManager
config = ConfigManager()
taxa = config.get('TAXA_PADRAO', tipo=float)
url_api = config.get('API_EXTERNA_URL')
```

Parâmetros por loja/plano:
```python
from parametros_wallclub.services import ParametrosService
param = ParametrosService.retornar_parametro_loja(
    loja_id, data_ref, id_plano, parametro_num, wall
)
```

---

## Logging

Toda operação crítica deve ser registrada:

```python
from wallclub_core.utilitarios.log_control import registrar_log

registrar_log('modulo.submodulo', f"Operação: {detalhes}", nivel='INFO')
registrar_log('modulo.submodulo', f"Erro: {str(e)}", nivel='ERROR')
```

Níveis: `DEBUG`, `INFO`, `WARNING`, `ERROR`
Destino: `services/django/logs/{modulo}.log`

**Nunca exponha dados sensíveis (CPF, token, senha) em logs.**

---

## Transações de Banco

Use `@transaction.atomic` quando:
- Criar/atualizar múltiplos registros relacionados
- Qualquer operação financeira (saldo, movimentações)

```python
from django.db import transaction

@transaction.atomic
def operacao_critica(self, dados):
    # rollback automático em caso de erro
    pass
```

---

## Valores Monetários

**SEMPRE use `Decimal`, nunca `float`.**

```python
from decimal import Decimal

valor = Decimal('10.50')  # ✅
valor = 10.50             # ❌ (imprecisão de ponto flutuante)
```

Calculadoras disponíveis:
- `CalculadoraBaseGestao` — transações normais (Club/Normal)
- `CalculadoraBaseCredenciadora` — transações credenciadora (`wall='K'`)
- `CalculadoraCheckout` — transações checkout web

---

## Timezone

**SEMPRE use `timezone.now()`, nunca `datetime.now()`.**

```python
from django.utils import timezone
agora = timezone.now()  # ✅ — ciente do fuso (UTC-3 Brasília)
```

---

## Nomenclatura

- Variáveis: `snake_case`
- Classes: `PascalCase`
- Constantes: `UPPER_SNAKE_CASE`
- Arquivos: `snake_case.py`

---

## Estrutura de Views (DRF)

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

## Migrations

**NUNCA use `makemigrations` ou gere arquivos de migration Django.**

Alterações de schema devem ser feitas via SQL puro (ALTER TABLE, CREATE TABLE, etc.).

---

## Regras Invioláveis

- ❌ Nunca hardcode valores de negócio — use ConfigManager ou tabela de parâmetros
- ❌ Nunca faça operação financeira sem `@transaction.atomic`
- ❌ Nunca exponha dados sensíveis em logs ou respostas
- ❌ Nunca crie código não solicitado
- ❌ Nunca assuma estruturas não visíveis no código
- ❌ Nunca gere migrations Django — sempre SQL puro
- ✅ Sempre use decorator de autenticação nas views
- ✅ Sempre valide permissões por loja/grupo
- ✅ Sempre valide saldo antes de débitos
