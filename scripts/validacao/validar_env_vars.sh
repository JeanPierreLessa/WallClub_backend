#!/bin/bash
# scripts/validacao/validar_env_vars.sh
# Valida variáveis de ambiente conforme documentação

echo "=== VALIDAÇÃO: Variáveis de Ambiente ==="
echo ""

# Documentado em README.md e ARQUITETURA.md
VARS_OBRIGATORIAS=(
    "BASE_URL"
    "CHECKOUT_BASE_URL"
    "PORTAL_LOJISTA_URL"
    "PORTAL_VENDAS_URL"
    "MEDIA_BASE_URL"
    "MERCHANT_URL"
    "DEBUG"
    "ALLOWED_HOSTS"
)

VARS_SEGURANCA=(
    "RISK_ENGINE_ADMIN_CLIENT_ID"
    "RISK_ENGINE_POS_CLIENT_ID"
    "RISK_ENGINE_INTERNAL_CLIENT_ID"
)

echo "📄 Variáveis de URL (Obrigatórias):"
echo ""

# Verificar em cada container principal
CONTAINERS=("wallclub-apis" "wallclub-portais" "wallclub-pos")

for container in "${CONTAINERS[@]}"; do
    echo "🐳 Container: $container"

    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo "  ❌ Container não está rodando"
        continue
    fi

    for var in "${VARS_OBRIGATORIAS[@]}"; do
        valor=$(docker exec $container printenv $var 2>/dev/null)
        if [ -n "$valor" ]; then
            # Truncar valor longo
            if [ ${#valor} -gt 50 ]; then
                valor="${valor:0:47}..."
            fi
            echo "  ✅ $var = $valor"
        else
            echo "  ⚠️  $var = (não definida)"
        fi
    done
    echo ""
done

echo "=== Variáveis de Segurança (OAuth) ==="
echo ""

for container in "${CONTAINERS[@]}"; do
    echo "🐳 Container: $container"

    if ! docker ps --format "{{.Names}}" | grep -q "^${container}$"; then
        echo "  ❌ Container não está rodando"
        continue
    fi

    for var in "${VARS_SEGURANCA[@]}"; do
        valor=$(docker exec $container printenv $var 2>/dev/null)
        if [ -n "$valor" ]; then
            # Mascarar valor sensível
            echo "  ✅ $var = ****${valor: -4}"
        else
            echo "  ⚠️  $var = (não definida)"
        fi
    done
    echo ""
done

echo "=== MERCHANT_URL (Crítica para Own Financial) ==="
MERCHANT_URL=$(docker exec wallclub-pos printenv MERCHANT_URL 2>/dev/null)
if [ -n "$MERCHANT_URL" ]; then
    echo "✅ MERCHANT_URL definida: $MERCHANT_URL"
else
    echo "❌ MERCHANT_URL não definida (CRÍTICO para Own Financial)"
fi

echo ""
echo "=== Validação Concluída ==="
