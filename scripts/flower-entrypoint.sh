#!/bin/bash
set -e

# Buscar credenciais do AWS Secrets Manager
echo "Buscando credenciais do Flower do AWS Secrets Manager..."

SECRET_ID="wall/prod/db"

# Buscar o secret completo
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id $SECRET_ID --query SecretString --output text)

# Extrair FLOWER_USER e FLOWER_PASSWD
export FLOWER_USER=$(echo $SECRET_JSON | jq -r '.FLOWER_USER // "admin"')
export FLOWER_PASSWD=$(echo $SECRET_JSON | jq -r '.FLOWER_PASSWD // "wallclub2025"')

echo "Credenciais carregadas: usuário=$FLOWER_USER"

# Iniciar Flower com autenticação
exec celery --broker=redis://wallclub-redis:6379/0 flower --port=5555 --basic_auth=$FLOWER_USER:$FLOWER_PASSWD
