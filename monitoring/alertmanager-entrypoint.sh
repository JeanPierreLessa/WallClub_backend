#!/bin/sh
set -e

# Copia o arquivo template para um local write-able e expande variáveis
cp /etc/alertmanager/alertmanager.yml /tmp/alertmanager.yml.template

sed -e "s|\${TELEGRAM_MONITOR_BOT_TOKEN}|${TELEGRAM_MONITOR_BOT_TOKEN}|g" \
    -e "s|\${TELEGRAM_MONITOR_BOT_CHAT_ID}|${TELEGRAM_MONITOR_BOT_CHAT_ID}|g" \
    /tmp/alertmanager.yml.template > /tmp/alertmanager.yml

# Inicia o alertmanager com o arquivo expandido
exec /bin/alertmanager --config.file=/tmp/alertmanager.yml --storage.path=/alertmanager
