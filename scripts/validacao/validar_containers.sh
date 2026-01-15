#!/bin/bash
# scripts/validacao/validar_containers.sh
# Valida containers e portas conforme documentação

echo "=== VALIDAÇÃO: Containers e Portas ==="
echo ""

# Documentado: 9 containers
echo "📄 Documentação afirma: 9 containers"
echo "🔍 Realidade:"
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}" | grep -E "wallclub|nginx|flower" || echo "  (nenhum container wallclub encontrado)"

echo ""
CONTAINER_COUNT=$(docker ps | grep -E "wallclub|nginx" | wc -l)
echo "Total containers ativos: $CONTAINER_COUNT"

if [ $CONTAINER_COUNT -eq 9 ]; then
    echo "✅ VALIDADO: 9 containers conforme documentação"
else
    echo "⚠️  DIVERGÊNCIA: Esperado 9, encontrado $CONTAINER_COUNT"
fi

echo ""
echo "=== Containers Esperados vs Reais ==="

# Lista de containers documentados
CONTAINERS_DOC=(
    "wallclub-portais:8005"
    "wallclub-pos:8006"
    "wallclub-apis:8007"
    "wallclub-riskengine:8008"
    "wallclub-redis:6379"
    "wallclub-celery-worker"
    "wallclub-celery-beat"
    "nginx"
    "wallclub-flower:5555"
)

for container_info in "${CONTAINERS_DOC[@]}"; do
    container_name=$(echo $container_info | cut -d: -f1)
    porta_esperada=$(echo $container_info | cut -d: -f2)

    # Verificar se container existe
    if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        if [ -n "$porta_esperada" ] && [ "$porta_esperada" != "$container_name" ]; then
            # Verificar porta
            porta_real=$(docker port $container_name 2>/dev/null | head -1 | grep -oE "[0-9]+" | head -1)
            if [ "$porta_real" == "$porta_esperada" ] || docker ps | grep $container_name | grep -q "$porta_esperada"; then
                echo "✅ $container_name (porta $porta_esperada)"
            else
                echo "⚠️  $container_name (porta esperada: $porta_esperada, real: $porta_real)"
            fi
        else
            echo "✅ $container_name"
        fi
    else
        echo "❌ $container_name (NÃO ENCONTRADO)"
    fi
done

echo ""
echo "=== Health Checks ==="

# Testar health endpoints
echo "Testando endpoints de saúde..."

# APIs
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8007/api/v1/health/ 2>/dev/null | grep -q "200"; then
    echo "✅ APIs (8007): /api/v1/health/ OK"
else
    echo "⚠️  APIs (8007): /api/v1/health/ não acessível"
fi

# Risk Engine
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8008/api/antifraude/health/ 2>/dev/null | grep -q "200"; then
    echo "✅ Risk Engine (8008): /api/antifraude/health/ OK"
else
    echo "⚠️  Risk Engine (8008): /api/antifraude/health/ não acessível"
fi

# Redis
if docker exec wallclub-redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
    echo "✅ Redis: PONG"
else
    echo "⚠️  Redis: não respondendo"
fi

echo ""
echo "=== Validação Concluída ==="
