#!/bin/bash

# DEFINIR SETTINGS BASEADO NO ENVIRONMENT
if [ "$ENVIRONMENT" = "production" ]; then
    export DJANGO_SETTINGS_MODULE="wallclub.settings.production"
    echo "=== WALLCLUB DJANGO - MODO PRODUÇÃO ==="
else
    export DJANGO_SETTINGS_MODULE="wallclub.settings.development"
    echo "=== WALLCLUB DJANGO - MODO DESENVOLVIMENTO ==="
fi

echo "🛡️  MIGRATIONS DESABILITADAS - Banco em produção protegido"
echo "⚙️  Settings: $DJANGO_SETTINGS_MODULE"
echo "🌍 Environment: $ENVIRONMENT"
echo "🐛 Debug: $DEBUG"
echo "📅 $(date)"
echo ""

# VERIFICAR CONEXÃO COM BANCO (sem alterar nada)
echo "🔍 Testando conexão com banco..."
python manage.py check --database default || echo "❌ Erro na conexão com banco"

# COLETAR STATIC FILES AUTOMATICAMENTE EM PRODUÇÃO
if [ "$ENVIRONMENT" = "production" ]; then
    echo "📁 Coletando static files..."
    python manage.py collectstatic --noinput --clear || echo "❌ Erro ao coletar static files"
fi

echo ""
echo "🚀 Iniciando servidor Gunicorn..."
echo "📡 Porta: 8000"
echo "👥 Workers: 3"
echo ""

# INICIAR APENAS O SERVIDOR - SEM TOCAR NO BANCO
exec gunicorn wallclub.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --keep-alive 5
