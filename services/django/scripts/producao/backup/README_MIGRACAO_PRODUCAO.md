# MIGRAÇÃO DE PARÂMETROS WALLCLUB PARA PRODUÇÃO

**Versão:** 1.0.0  
**Data:** 2025-08-14  
**Autor:** Sistema WallClub

## 📋 VISÃO GERAL

Este pacote contém todos os scripts e procedimentos necessários para migrar o sistema de parâmetros financeiros WallClub para produção com estrutura limpa e otimizada.

## 🎯 OBJETIVOS DA MIGRAÇÃO

- ✅ **Estrutura DECIMAL**: Campos numéricos como `DECIMAL(10,6)` para cálculos diretos
- ✅ **Nomenclatura Clara**: `parametro_loja_*`, `parametro_uptal_*`, `parametro_wall_*`
- ✅ **Performance Otimizada**: Índices e constraints adequados
- ✅ **Auditoria Completa**: Histórico de alterações e controle de importações
- ✅ **Migration Limpa**: Uma única migration inicial sem histórico
- ✅ **CalculadoraDesconto**: Nova calculadora Django com 94.5% de paridade com PHP

## 📁 ARQUIVOS DO PACOTE

```
scripts/producao/
├── README_MIGRACAO_PRODUCAO.md     # Esta documentação
├── criar_tabelas_parametros.sql    # Script SQL de referência (estrutura final)
├── migrar_dados_producao.py        # Script principal de migração (com rollback)
├── migrar_dados_simples.py         # Script auxiliar de migração simples
├── validar_migracao.py             # Script de validação de dados pós-migração
└── validar_calculos_producao.py    # Script de validação de cálculos (Django vs PHP)
```

```
parametros_wallclub/migrations/
└── 0001_initial_clean.py           # Migration Django única e limpa
```

## 🚀 PROCEDIMENTO DE MIGRAÇÃO

### **FASE 1: PRÉ-MIGRAÇÃO**

#### 1.1 Backup Completo
```bash
# Backup do banco de dados
mysqldump -u root -p wallclub > backup_wallclub_$(date +%Y%m%d_%H%M%S).sql

# Backup do código Django atual
tar -czf backup_django_$(date +%Y%m%d_%H%M%S).tar.gz /path/to/wallclub_django/
```

#### 1.2 Validação do Ambiente
```bash
# Verificar conexão com banco
mysql -u root -p wallclub -e "SELECT COUNT(*) FROM parametros_loja;"

# Verificar ambiente Django
cd /path/to/wallclub_django
source venv/bin/activate
python manage.py check
```

#### 1.3 Janela de Manutenção
- **Recomendado**: Madrugada (02:00 - 06:00)
- **Duração Estimada**: 30-60 minutos
- **Impacto**: Sistema de parâmetros indisponível

### **FASE 2: EXECUÇÃO DA MIGRAÇÃO**

#### 2.1 Limpeza das Migrations Antigas
```bash
# Remover migrations antigas (manter backup)
cd parametros_wallclub/migrations/
mkdir backup_migrations_$(date +%Y%m%d)
mv 0*.py backup_migrations_$(date +%Y%m%d)/
# Manter apenas __init__.py e 0001_initial_clean.py

# Limpar registro de migrations no Django
python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('DELETE FROM django_migrations WHERE app = %s', ['parametros_wallclub'])
print('Migrations limpas do Django')
"
```

#### 2.2 Criação das Tabelas (SQL)
```bash
# Executar script SQL (já inclui DROP das tabelas existentes)
mysql -u root -p wallclub < scripts/producao/criar_tabelas_parametros.sql
```

#### 2.3 Aplicação da Migration Django (Fake)
```bash
# Marcar migration como aplicada (fake) já que tabelas foram criadas pelo SQL
python manage.py migrate parametros_wallclub 0001_initial_clean --fake

# Verificar status
python manage.py showmigrations parametros_wallclub
```

#### 2.3 Verificação da Estrutura
```bash
# Verificar se tabelas foram criadas corretamente
mysql -u root -p wallclub -e "SHOW TABLES LIKE 'parametros_wallclub%';"

# Verificar estrutura DECIMAL dos campos
mysql -u root -p wallclub -e "DESCRIBE parametros_wallclub;" | grep parametro
```

#### 2.4 Migração dos Dados
```bash
# Teste em dry-run primeiro
python scripts/producao/migrar_dados_producao.py --dry-run

# Migração real (rollback automático em caso de erro)
python scripts/producao/migrar_dados_producao.py
```

### **FASE 3: VALIDAÇÃO**

#### 3.1 Validação de Dados
```bash
# Validação da estrutura e integridade dos dados
python scripts/producao/validar_migracao.py --verbose
```

#### 3.2 Validação de Cálculos
```bash
# Validação da CalculadoraDesconto (Django vs PHP)
python scripts/producao/validar_calculos_producao.py --verbose

# Com endpoint customizado (se necessário)
python scripts/producao/validar_calculos_producao.py --endpoint https://wallclub.com.br/apps/calcula_desconto_parcela_para_teste.php
```

#### 3.3 Validação Manual
```sql
-- Verificar contagem de registros
SELECT 
    'parametros_wallclub' as tabela, COUNT(*) as registros 
FROM parametros_wallclub
UNION ALL
SELECT 
    'parametros_wallclub_planos' as tabela, COUNT(*) as registros 
FROM parametros_wallclub_planos;

-- Verificar parâmetros uptal e wall
SELECT COUNT(*) as configs_com_uptal 
FROM parametros_wallclub 
WHERE parametro_uptal_1 IS NOT NULL;

SELECT COUNT(*) as configs_com_wall 
FROM parametros_wallclub 
WHERE parametro_wall_1 IS NOT NULL;

-- Verificar integridade referencial
SELECT COUNT(*) as configs_sem_plano
FROM parametros_wallclub p
LEFT JOIN parametros_wallclub_planos pl ON p.id_plano = pl.id
WHERE pl.id IS NULL;
```

#### 3.4 Testes Funcionais
```bash
# Testar CalculadoraDesconto
python manage.py shell -c "
from parametros_wallclub.services import CalculadoraDesconto
calc = CalculadoraDesconto()
resultado = calc.calcular_desconto(100.0, '2024-01-15', 'PIX', 1, '123456789', 's')
print(f'Cálculo funcionando: {resultado is not None}')
"

# Testar serviços de configuração
python manage.py shell -c "
from parametros_wallclub.services import ParametrosService
config = ParametrosService.get_configuracao_ativa(1, 1, 's')
print(f'Configuração encontrada: {config is not None}')
"
```

### **FASE 4: PÓS-MIGRAÇÃO**

#### 4.1 Monitoramento
- Verificar logs de aplicação
- Monitorar performance das consultas
- Validar cálculos em transações reais

#### 4.2 Limpeza
```bash
# Remover scripts de migração (após validação completa)
# Remover campos id_desc (após período de validação)
```

## 🔄 PLANO DE ROLLBACK

### Em Caso de Falha Durante a Migração:

#### Rollback Automático
- O script `migrar_dados_producao.py` com `--rollback-on-error` faz rollback automático

#### Rollback Manual
```bash
# 1. Parar aplicação Django
systemctl stop wallclub-django

# 2. Restaurar backup do banco
mysql -u root -p wallclub < backup_wallclub_YYYYMMDD_HHMMSS.sql

# 3. Restaurar código Django
tar -xzf backup_django_YYYYMMDD_HHMMSS.tar.gz

# 4. Restaurar migrations antigas
cd parametros_wallclub/migrations/
rm 0001_initial_clean.py
mv backup_migrations_YYYYMMDD/* ./

# 5. Aplicar migrations antigas
python manage.py migrate parametros_wallclub

# 6. Reiniciar aplicação
systemctl start wallclub-django
```

## ⚠️ PONTOS DE ATENÇÃO

### **Dados Inválidos**
- Valores como "#N/D", "Crédito a Vista", "ND" serão **automaticamente rejeitados**
- Isso é **esperado** e **correto** - são dados corrompidos no legado

### **Timezone Warnings**
- Warnings sobre datetime naive são **normais**
- O Django converte automaticamente para timezone-aware

### **Performance**
- Primeira consulta após migração pode ser mais lenta (cache vazio)
- Índices podem precisar de rebuild automático

### **Validação Crítica**
- **OBRIGATÓRIO**: Validar que parâmetros `uptal` e `wall` foram migrados
- **OBRIGATÓRIO**: Testar cálculos com dados reais antes de liberar

## 📊 MÉTRICAS DE SUCESSO

### **Dados Esperados** (baseado em testes):
- **~5.200 configurações** migradas
- **~4.900 configurações** com parâmetros uptal/wall
- **306 planos únicos** criados
- **Taxa de sucesso migração**: > 95%
- **Taxa de paridade cálculos**: ≥ 94.5% (Django vs PHP)

### **Critérios de Aprovação**:
- ✅ Todas as tabelas criadas sem erro
- ✅ Migration Django aplicada com sucesso
- ✅ Dados migrados com taxa de sucesso > 95%
- ✅ Parâmetros uptal e wall presentes
- ✅ CalculadoraDesconto com paridade ≥ 94.5% vs PHP
- ✅ Testes funcionais passando
- ✅ Performance igual ou melhor que sistema atual

## 🆘 CONTATOS DE EMERGÊNCIA

- **Desenvolvedor Principal**: [Seu contato]
- **DBA**: [Contato do DBA]
- **DevOps**: [Contato DevOps]

## 📝 LOG DE EXECUÇÃO

### Template para preenchimento durante a migração:

```
DATA: ___________
HORÁRIO INÍCIO: ___________
EXECUTADO POR: ___________

FASE 1 - PRÉ-MIGRAÇÃO:
[ ] Backup realizado
[ ] Ambiente validado
[ ] Janela de manutenção iniciada

FASE 2 - EXECUÇÃO:
[ ] Migrations antigas removidas
[ ] Tabelas criadas (_____ registros)
[ ] Migration Django aplicada
[ ] Dados migrados (_____ configurações)

FASE 3 - VALIDAÇÃO:
[ ] Validação de dados OK (validar_migracao.py)
[ ] Validação de cálculos OK (validar_calculos_producao.py - ≥94.5%)
[ ] Validação manual OK
[ ] Testes funcionais OK
[ ] CalculadoraDesconto funcionando

FASE 4 - FINALIZAÇÃO:
[ ] Sistema em produção
[ ] Monitoramento ativo
[ ] Documentação atualizada

HORÁRIO FIM: ___________
STATUS FINAL: [ ] SUCESSO [ ] ROLLBACK
OBSERVAÇÕES: _________________________
```

---

## 🎉 CONCLUSÃO

Este pacote de migração foi testado e validado em ambiente de desenvolvimento. Seguindo os procedimentos documentados, a migração deve ser executada com sucesso e sem impacto para os usuários finais.

**Boa migração!** 🚀
