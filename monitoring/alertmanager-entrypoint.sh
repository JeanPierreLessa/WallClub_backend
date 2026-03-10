#!/bin/sh
set -e

echo "Buscando credenciais do Telegram do AWS Secrets Manager..."

SECRET_ID="wall/prod/db"

# Buscar o secret completo
SECRET_JSON=$(aws secretsmanager get-secret-value --secret-id $SECRET_ID --query SecretString --output text)

# Extrair variáveis do Telegram
export TELEGRAM_MONITOR_BOT_TOKEN=$(echo $SECRET_JSON | jq -r '.TELEGRAM_MONITOR_BOT_TOKEN // ""')
export TELEGRAM_MONITOR_BOT_CHAT_ID=$(echo $SECRET_JSON | jq -r '.TELEGRAM_MONITOR_BOT_CHAT_ID // ""')

echo "Credenciais carregadas: chat_id=$TELEGRAM_MONITOR_BOT_CHAT_ID"

# Copia o arquivo template para um local write-able e expande variáveis
cp /etc/alertmanager/alertmanager.yml /tmp/alertmanager.yml.template

sed -e "s|\${TELEGRAM_MONITOR_BOT_TOKEN}|${TELEGRAM_MONITOR_BOT_TOKEN}|g" \
    -e "s|\${TELEGRAM_MONITOR_BOT_CHAT_ID}|${TELEGRAM_MONITOR_BOT_CHAT_ID}|g" \
    /tmp/alertmanager.yml.template > /tmp/alertmanager.yml

# Inicia o alertmanager com o arquivo expandido
exec /bin/alertmanager --config.file=/tmp/alertmanager.yml --storage.path=/alertmanager
