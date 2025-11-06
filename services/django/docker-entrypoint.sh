#!/bin/bash
set -e

echo "🚀 Iniciando container Django..."

# Executar collectstatic automaticamente
echo "📁 Coletando arquivos estáticos..."
python manage.py collectstatic --noinput --clear

echo "✅ Arquivos estáticos coletados"
echo "🌐 Iniciando Gunicorn..."

# Executar o comando passado como argumento (CMD do Dockerfile)
exec "$@"
