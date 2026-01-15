#!/bin/bash
# scripts/validacao/validar_tudo.sh
# Script master que executa todas as validações

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  VALIDAÇÃO COMPLETA: DOCUMENTAÇÃO VS CÓDIGO REAL          ║"
echo "║  Data: $(date '+%Y-%m-%d %H:%M:%S')                                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Contadores
TOTAL_VALIDACOES=0
VALIDACOES_OK=0

# 1. Containers
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1/6 - CONTAINERS E PORTAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/validar_containers.sh"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

# 2. APIs Internas
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "2/6 - APIs REST INTERNAS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "$SCRIPT_DIR/validar_apis_internas.py"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

# 3. Middleware
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "3/6 - MIDDLEWARE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "$SCRIPT_DIR/validar_middleware.py"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

# 4. wallclub_core
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "4/6 - ESTRUTURA WALLCLUB_CORE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "$SCRIPT_DIR/validar_wallclub_core.py"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

# 5. Variáveis de Ambiente
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "5/6 - VARIÁVEIS DE AMBIENTE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
bash "$SCRIPT_DIR/validar_env_vars.sh"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

# 6. Risk Engine
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "6/6 - RISK ENGINE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 "$SCRIPT_DIR/validar_riskengine.py"
TOTAL_VALIDACOES=$((TOTAL_VALIDACOES + 1))
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  VALIDAÇÃO CONCLUÍDA                                      ║"
echo "║  Total de validações executadas: $TOTAL_VALIDACOES                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📝 Para validar tabelas SQL, execute manualmente:"
echo "   mysql -u user -p wallclub < $SCRIPT_DIR/validar_tabelas.sql"
echo ""
echo "📊 Próximos passos:"
echo "   1. Revisar divergências encontradas"
echo "   2. Atualizar documentação OU código conforme necessário"
echo "   3. Re-executar validação após correções"
