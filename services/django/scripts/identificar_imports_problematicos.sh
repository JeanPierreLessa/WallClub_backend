#!/bin/bash
# Script para identificar imports problemáticos para separação em containers
# Data: 30/10/2025

echo "================================================================================"
echo "IDENTIFICAÇÃO DE IMPORTS PROBLEMÁTICOS - WALLCLUB DJANGO"
echo "================================================================================"
echo ""

# Função para contar e mostrar imports (sem ^ no padrão para pegar com espaços)
show_imports() {
    local title="$1"
    local pattern="$2"
    local search_path="$3"
    
    echo "=== $title ==="
    echo ""
    
    # Busca simples sem filtro adicional
    local results=$(grep -rn "$pattern" $search_path --include="*.py" 2>/dev/null || true)
    local count=$(echo "$results" | grep -v "^$" | wc -l | tr -d ' ')
    
    echo "Total: $count imports"
    echo ""
    
    if [ "$count" -gt 0 ]; then
        echo "$results" | head -30
        if [ "$count" -gt 30 ]; then
            echo ""
            echo "... (mostrando apenas 30 de $count)"
        fi
    fi
    
    echo ""
    echo "--------------------------------------------------------------------------------"
    echo ""
}

# 🔴 CRÍTICO: CORE importando de apps específicos
echo "🔴 BLOQUEADORES CRÍTICOS (CORE não pode importar de apps específicos)"
echo "================================================================================"
echo ""

show_imports "1. CORE → APP3_APIS (apps/)" \
    "from apps\." \
    "comum/"

show_imports "2. CORE → APP3_APIS (checkout/)" \
    "from checkout" \
    "comum/"

show_imports "3. CORE → APP2_POS (posp2/)" \
    "from posp2" \
    "comum/"

show_imports "4. CORE → APP2_POS (pinbank/)" \
    "from pinbank" \
    "comum/"

show_imports "5. CORE → APP2_POS (parametros_wallclub/)" \
    "from parametros_wallclub" \
    "comum/"

# ⚠️ ALTO: Dependências cruzadas entre apps
echo ""
echo "⚠️  DEPENDÊNCIAS CRUZADAS (devem ser resolvidas antes da separação)"
echo "================================================================================"
echo ""

show_imports "6. APP1_PORTAIS → APP3_APIS (apps/)" \
    "from apps\." \
    "portais/ sistema_bancario/"

show_imports "7. APP1_PORTAIS → APP3_APIS (checkout/)" \
    "from checkout" \
    "portais/ sistema_bancario/"

show_imports "8. APP1_PORTAIS → APP2_POS (posp2/)" \
    "from posp2" \
    "portais/ sistema_bancario/"

show_imports "9. APP1_PORTAIS → APP2_POS (pinbank/)" \
    "from pinbank" \
    "portais/ sistema_bancario/"

show_imports "10. APP2_POS → APP3_APIS (apps/)" \
    "from apps\." \
    "posp2/ pinbank/ parametros_wallclub/"

show_imports "11. APP2_POS → APP3_APIS (checkout/)" \
    "from checkout" \
    "posp2/ pinbank/ parametros_wallclub/"

show_imports "12. APP3_APIS → APP2_POS (posp2/)" \
    "from posp2" \
    "apps/ checkout/"

show_imports "13. APP3_APIS → APP2_POS (pinbank/)" \
    "from pinbank" \
    "apps/ checkout/"

show_imports "14. APP3_APIS → APP2_POS (parametros_wallclub/)" \
    "from parametros_wallclub" \
    "apps/ checkout/"

echo ""
echo "================================================================================"
echo "ANÁLISE CONCLUÍDA"
echo "================================================================================"
echo ""
echo "Próximos passos:"
echo "  1. Corrigir BLOQUEADORES CRÍTICOS (itens 1-5)"
echo "  2. Refatorar dependências cruzadas (itens 6-14)"
echo "  3. Validar: CORE deve ter zero imports de apps específicos"
echo ""
