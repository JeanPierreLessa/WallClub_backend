#!/bin/bash
# Script para validar que CORE não tem dependências de apps específicos

echo "🔍 Validando CORE limpo..."
echo ""

# Buscar imports problemáticos no nível de módulo
IMPORTS_PROBLEMATICOS=$(grep -r "^from apps\.\|^from checkout\|^from posp2\|^from pinbank\|^from parametros_wallclub" comum/ --include="*.py" 2>/dev/null)

if [ -n "$IMPORTS_PROBLEMATICOS" ]; then
    echo "❌ ERRO: CORE tem imports de apps específicos no nível de módulo:"
    echo "$IMPORTS_PROBLEMATICOS"
    exit 1
fi

# Verificar imports lazy (são aceitáveis)
IMPORTS_LAZY=$(grep -rn "from apps\." comum/ --include="*.py" 2>/dev/null)

if [ -n "$IMPORTS_LAZY" ]; then
    echo "✅ Imports lazy encontrados (ACEITÁVEL):"
    echo "$IMPORTS_LAZY"
    echo ""
fi

echo "✅ CORE está limpo!"
echo ""
echo "📊 Resumo:"
echo "  - Imports no nível de módulo: 0 (✅)"
echo "  - Imports lazy (dentro de funções): $(echo "$IMPORTS_LAZY" | grep -c "from apps\." || echo 0) (✅)"
echo ""
echo "🎯 CORE pronto para ser extraído como package independente!"
