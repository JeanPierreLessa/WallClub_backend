# WallClub - Regras de Teste

## Estrutura de Testes

Testes ficam em `tests/` dentro de cada app Django:
```
services/django/apps/<modulo>/tests/
├── test_views.py       # Testes de endpoints/views
├── test_services.py    # Testes de lógica de negócio
├── test_models.py      # Testes de modelos
└── test_tasks.py       # Testes de tasks Celery
```

---

## Regras Obrigatórias

### 1. Dados Realistas
```python
# ❌ ERRADO - dados inventados
cliente = Cliente(nome="Test", cpf="00000000000")

# ✅ CERTO - dados realistas (mas fictícios)
cliente = Cliente(nome="Maria Silva", cpf="12345678901")
```

### 2. Banco Real para Integrações
- Testes de integração devem usar banco de dados real (não mocks)
- Use `@pytest.mark.django_db` ou `TransactionTestCase`
- Mocks apenas para serviços externos (Pinbank, Own, Firebase)

### 3. Operações Financeiras
```python
from decimal import Decimal

# Sempre teste com Decimal
assert saldo == Decimal('100.50')  # ✅
assert saldo == 100.50             # ❌
```

### 4. Autenticação em Testes de View
```python
# Sempre teste com autenticação adequada
self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

# Teste cenários sem autenticação (deve retornar 401/403)
response = self.client.get('/api/v1/endpoint/')
assert response.status_code in [401, 403]
```

### 5. Permissões por Escopo
```python
# Teste que lojista só vê dados da própria loja
# Teste que admin vê dados de todas as lojas
# Teste que usuário sem permissão recebe 403
```

---

## O Que Testar

### Sempre testar:
- Lógica de cálculo financeiro (cashback, taxas, slip)
- Validações de entrada (dados inválidos, campos obrigatórios)
- Permissões de acesso (lojista vs admin vs anônimo)
- Fluxos críticos (checkout, movimentações de saldo)
- Edge cases (saldo zero, valores negativos, limites)

### Não precisa testar:
- CRUD simples do Django/DRF (framework já testa)
- Serializers triviais sem lógica customizada
- Admin registrations

---

## Nomenclatura

```python
# Padrão: test_<ação>_<cenário>_<resultado_esperado>
def test_debitar_saldo_insuficiente_retorna_erro(self):
def test_calcular_cashback_loja_sem_regra_usa_padrao(self):
def test_login_biometrico_dispositivo_invalido_retorna_403(self):
```

---

## Execução

```bash
# Rodar todos os testes
python manage.py test

# Rodar testes de um módulo
python manage.py test apps.conta_digital.tests

# Rodar teste específico
python manage.py test apps.conta_digital.tests.test_services.TestSaldoService
```
