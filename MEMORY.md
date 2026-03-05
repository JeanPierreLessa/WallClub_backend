# WallClub Backend - Memory

**Última atualização:** 04/03/2026

---

## 🎯 Contexto Atual de Desenvolvimento

### Features em Desenvolvimento Ativo
- Ajustes na calculadora credenciadora (wall='K')
- Novos parâmetros: parametro_loja_31, parametro_loja_32, parametro_loja_33, parametro_uptal_7

### Decisões Técnicas Recentes (Últimos 7 dias)
- **04/03/2026:** Calculadora credenciadora agora força `wall='K'` para todos os parâmetros
- **04/03/2026:** Variáveis alteradas para buscar de parametros ao invés de extrato Pinbank:
  - var39 = parametro_loja_12
  - var40 = parametro_loja_13
  - var41 = var40 * var26
  - var42 = var26 - var37 - var41 - parametro_loja_31
  - var43 = parametro_loja_18
  - var44 = var19
  - var87 = parametro_uptal_1
  - var89 = parametro_uptal_1
  - var91 = parametro_uptal_4
  - var93[0] = parametro_uptal_5
  - var94[0] = var93[0] * var26
  - var94[A] = parametro_uptal_6
  - var130 = 'Credenciadora'

---

## 🐛 Bugs Conhecidos em Investigação

### Parâmetros wall='K' não carregados
- **Status:** Em investigação
- **Problema:** `get_configuracao_ativa` retorna 0 registros para wall='K'
- **Causa:** Faltam dados na tabela `parametros_wallclub` para wall='K'
- **Próximo passo:** Verificar se importação incluiu registros para wall='K' ou copiar de outra wall

---

## 🧪 Dados de Teste

### Credenciais de Teste
- **Cliente teste:** CPF 17653377807, Canal ID: 1
- **Loja teste:** loja_id=14, id_plano=3
- **NSUs para teste:** 170972868, 172562013

### Valores de Parâmetros (wall='K', loja=14, plano=3)
```sql
parametro_uptal_1 = 0.0078500000
parametro_uptal_4 = ?
parametro_uptal_5 = ?
parametro_uptal_6 = ?
parametro_loja_12 = ?
parametro_loja_13 = ?
parametro_loja_18 = ?
parametro_loja_31 = ?
```

---

## ⚠️ Erros Pré-Existentes (NÃO Corrigir)

_Nenhum erro pré-existente catalogado no momento._

---

## 📝 Notas de Sessão

### Comandos Úteis Recentes
```bash
# Processar NSU específico
docker exec -it wallclub-portais python manage.py carga_base_unificada_credenciadora --nsu 170972868

# Carregar extrato POS
docker exec -it wallclub-portais python manage.py carga_extrato_pos 72h

# Verificar logs
tail -100 services/django/logs/parametros_wallclub.log
```

### Queries SQL Úteis
```sql
-- Verificar parâmetros wall='K'
SELECT id, loja_id, id_plano, wall, parametro_uptal_1, parametro_loja_12
FROM parametros_wallclub
WHERE loja_id = 14 AND id_plano = 3 AND wall = 'K'
ORDER BY data_inicio DESC;

-- Verificar resultado do cálculo
SELECT var87, var89, var91, var93, var94, var94_A, var130
FROM base_transacoes_unificadas
WHERE var9 = '170972868';
```

---

## 🔄 Próximos Passos

1. Resolver problema de parâmetros wall='K' não encontrados
2. Validar cálculos após correção de dados
3. Testar com múltiplos NSUs

---

**Instruções de Uso:**
- Mantenha apenas informações dos últimos 30 dias
- Remova decisões que já foram consolidadas na arquitetura
- Atualize bugs resolvidos para "Resolvido" antes de remover
