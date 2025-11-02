#!/bin/bash
# Teste manual simplificado para debugar por que grep não encontra imports

cd /var/www/wallclub_django

echo "=== TESTE 1: Verificar se diretórios existem ==="
ls -ld comum/ portais/ apps/ checkout/ posp2/ pinbank/ parametros_wallclub/ 2>/dev/null
echo ""

echo "=== TESTE 2: Contar arquivos .py em cada diretório ==="
echo "comum/: $(find comum/ -name '*.py' 2>/dev/null | wc -l) arquivos"
echo "portais/: $(find portais/ -name '*.py' 2>/dev/null | wc -l) arquivos"
echo "apps/: $(find apps/ -name '*.py' 2>/dev/null | wc -l) arquivos"
echo ""

echo "=== TESTE 3: Grep simples - buscar 'from apps' em comum/ ==="
grep -r "from apps" comum/ --include="*.py" 2>/dev/null | head -5
echo ""

echo "=== TESTE 4: Grep com escape - buscar 'from apps\.' em comum/ ==="
grep -r "from apps\." comum/ --include="*.py" 2>/dev/null | head -5
echo ""

echo "=== TESTE 5: Grep em portais/ - buscar 'from apps' ==="
grep -r "from apps" portais/ --include="*.py" 2>/dev/null | head -5
echo ""

echo "=== TESTE 6: Grep em portais/ - buscar 'from checkout' ==="
grep -r "from checkout" portais/ --include="*.py" 2>/dev/null | head -5
echo ""

echo "=== TESTE 7: Listar alguns imports reais de comum/ ==="
grep -rh "^from " comum/ --include="*.py" 2>/dev/null | sort | uniq | head -20
echo ""

echo "=== TESTE 8: Listar alguns imports reais de portais/ ==="
grep -rh "^from " portais/ --include="*.py" 2>/dev/null | sort | uniq | head -20
