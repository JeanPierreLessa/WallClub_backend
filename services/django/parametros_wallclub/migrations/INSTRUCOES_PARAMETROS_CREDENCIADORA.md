# Instruções - Novos Parâmetros Credenciadora

**Data:** 02/03/2026
**Objetivo:** Adicionar suporte a 4 novos parâmetros para cálculos de credenciadora

---

## 📋 Resumo das Mudanças

### Novos Parâmetros

1. **parametro_loja_31** (133): Rebate Parcelado a pagar Operador (%)
2. **parametro_loja_32** (137): Rebate Parcelado a pagar Loja (%)
3. **parametro_loja_33** (141): Tarifa por Transação a pagar pela Loja (R$)
4. **parametro_uptal_7** (143): Tarifa por Transação pagar pela Wall (R$)

### Novo Tipo Wall

- **'K'**: Credenciadora (adicionado às opções S, N, C)

---

## 🚀 Passo a Passo de Execução

### 1. Executar SQL no Banco de Dados

```bash
# Conectar ao MySQL
mysql -u root -p wallclub

# Executar o script
source /var/www/WallClub_backend/services/django/parametros_wallclub/migrations/add_parametros_credenciadora.sql
```

**Ou copiar e colar manualmente:**

```sql
-- 1) parametro_loja_31
ALTER TABLE parametros_wallclub
ADD COLUMN parametro_loja_31 DECIMAL(12,10) NULL
COMMENT 'Rebate Parcelado a pagar Operador (%)';

-- 2) parametro_loja_32
ALTER TABLE parametros_wallclub
ADD COLUMN parametro_loja_32 DECIMAL(12,10) NULL
COMMENT 'Rebate Parcelado a pagar Loja (%)';

-- 3) parametro_loja_33
ALTER TABLE parametros_wallclub
ADD COLUMN parametro_loja_33 DECIMAL(12,10) NULL
COMMENT 'Tarifa por Transação a pagar pela Loja (R$)';

-- 4) parametro_uptal_7
ALTER TABLE parametros_wallclub
ADD COLUMN parametro_uptal_7 DECIMAL(12,10) NULL
COMMENT 'Tarifa por Transação pagar pela Wall (R$)';
```

**Verificar:**

```sql
SELECT
    COLUMN_NAME,
    DATA_TYPE,
    COLUMN_TYPE,
    COLUMN_COMMENT
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'wallclub'
  AND TABLE_NAME = 'parametros_wallclub'
  AND COLUMN_NAME IN ('parametro_loja_31', 'parametro_loja_32', 'parametro_loja_33', 'parametro_uptal_7')
ORDER BY COLUMN_NAME;
```

**Resultado esperado:**
```
+---------------------+-----------+----------------+--------------------------------------------------+
| COLUMN_NAME         | DATA_TYPE | COLUMN_TYPE    | COLUMN_COMMENT                                   |
+---------------------+-----------+----------------+--------------------------------------------------+
| parametro_loja_31   | decimal   | decimal(12,10) | Rebate Parcelado a pagar Operador (%)            |
| parametro_loja_32   | decimal   | decimal(12,10) | Rebate Parcelado a pagar Loja (%)                |
| parametro_loja_33   | decimal   | decimal(12,10) | Tarifa por Transação a pagar pela Loja (R$)      |
| parametro_uptal_7   | decimal   | decimal(12,10) | Tarifa por Transação pagar pela Wall (R$)        |
+---------------------+-----------+----------------+--------------------------------------------------+
```

---

### 2. Deploy do Código

```bash
cd /var/www/WallClub_backend
git pull origin main
docker-compose up -d --build --no-deps wallclub-portais
```

---

### 3. Testar no Portal Admin

**URL:** https://wcadmin.wallclub.com.br/parametros/

#### 3.1. Verificar Tipo 'K' (Credenciadora)

1. Acessar **Parâmetros > Importar Parâmetros**
2. Verificar se o campo "Modalidade Wall" tem a opção **'K - Credenciadora'**

#### 3.2. Testar Importação de Planilha

**Preparar planilha de teste com as novas colunas:**

| loja_id | id_plano | wall | parametro_loja_31 | parametro_loja_32 | parametro_loja_33 | parametro_uptal_7 |
|---------|----------|------|-------------------|-------------------|-------------------|-------------------|
| 1       | 1        | K    | 0.0150            | 0.0200            | 0.50              | 0.30              |

**Importar e verificar:**

```sql
-- Verificar se foi importado corretamente
SELECT
    id,
    loja_id,
    id_plano,
    wall,
    parametro_loja_31,
    parametro_loja_32,
    parametro_loja_33,
    parametro_uptal_7,
    vigencia_inicio
FROM parametros_wallclub
WHERE wall = 'K'
ORDER BY id DESC
LIMIT 5;
```

---

### 4. Testar ParametrosService

**Console Django:**

```bash
docker exec -it wallclub-portais python manage.py shell
```

```python
from parametros_wallclub.services import ParametrosService
from datetime import datetime

# Testar busca de parâmetro loja 31
loja_id = 1
id_plano = 1
wall = 'K'
data_ref = int(datetime.now().timestamp())

# Parâmetro loja 31
param_31 = ParametrosService.retornar_parametro_loja(loja_id, data_ref, id_plano, 31, wall)
print(f"parametro_loja_31: {param_31}")

# Parâmetro loja 32
param_32 = ParametrosService.retornar_parametro_loja(loja_id, data_ref, id_plano, 32, wall)
print(f"parametro_loja_32: {param_32}")

# Parâmetro loja 33
param_33 = ParametrosService.retornar_parametro_loja(loja_id, data_ref, id_plano, 33, wall)
print(f"parametro_loja_33: {param_33}")

# Parâmetro uptal 7
param_uptal_7 = ParametrosService.retornar_parametro_uptal(loja_id, data_ref, id_plano, 7, wall)
print(f"parametro_uptal_7: {param_uptal_7}")
```

**Resultado esperado:**
```
parametro_loja_31: 0.0150
parametro_loja_32: 0.0200
parametro_loja_33: 0.50
parametro_uptal_7: 0.30
```

---

### 5. Testar get_parametro()

```python
from parametros_wallclub.models import ParametrosWall

# Buscar configuração
config = ParametrosWall.objects.filter(wall='K').first()

if config:
    # Testar método get_parametro
    print(f"Parâmetro 31: {config.get_parametro(31)}")
    print(f"Parâmetro 32: {config.get_parametro(32)}")
    print(f"Parâmetro 33: {config.get_parametro(33)}")
    print(f"Parâmetro 37 (uptal_7): {config.get_parametro(37)}")
else:
    print("Nenhuma configuração com wall='K' encontrada")
```

---

## 📊 Mapeamento de Códigos

### Parâmetros Loja (1-33)

| Código | Campo              | Descrição                                    |
|--------|--------------------|----------------------------------------------|
| 31     | parametro_loja_31  | Rebate Parcelado a pagar Operador (%)        |
| 32     | parametro_loja_32  | Rebate Parcelado a pagar Loja (%)            |
| 33     | parametro_loja_33  | Tarifa por Transação a pagar pela Loja (R$)  |

### Parâmetros Uptal (1-7)

| Código | Campo              | Descrição                                    |
|--------|--------------------|----------------------------------------------|
| 7      | parametro_uptal_7  | Tarifa por Transação pagar pela Wall (R$)    |

### Tipos Wall

| Código | Descrição      |
|--------|----------------|
| S      | Com Wall       |
| N      | Sem Wall       |
| C      | Cashback       |
| K      | Credenciadora  |

---

## ✅ Checklist de Validação

- [ ] SQL executado com sucesso
- [ ] Colunas criadas no banco (verificar com query)
- [ ] Deploy realizado (container wallclub-portais)
- [ ] Tipo 'K' aparece no portal admin
- [ ] Importação de planilha funciona com novos campos
- [ ] ParametrosService.retornar_parametro_loja(31-33) funciona
- [ ] ParametrosService.retornar_parametro_uptal(7) funciona
- [ ] Model.get_parametro() retorna valores corretos

---

## 🔧 Arquivos Modificados

1. **`parametros_wallclub/models.py`**
   - Adicionado tipo 'K' no campo `wall`
   - Adicionados campos `parametro_loja_31`, `parametro_loja_32`, `parametro_loja_33`
   - Adicionado campo `parametro_uptal_7`
   - Atualizado método `get_parametro()` para suportar códigos 1-33 (loja) e 31-37 (uptal)

2. **`parametros_wallclub/services.py`**
   - Atualizado comentário de `retornar_parametro_loja()`: (1-33)
   - Atualizado comentário de `retornar_parametro_uptal()`: (1-7)
   - Atualizado loop de debug: `range(1, 8)`

3. **`parametros_wallclub/migrations/add_parametros_credenciadora.sql`**
   - Script SQL para criar as 4 novas colunas

---

## 📝 Próximos Passos

Após validação, os novos parâmetros estarão disponíveis para:

1. **CalculadoraBaseCredenciadora**: Usar nos cálculos das variáveis
2. **Portal Admin**: Importação e edição via interface
3. **Cargas Automáticas**: Processar planilhas com novos campos

---

**Responsável:** Jean Lessa
**Status:** Pronto para execução
