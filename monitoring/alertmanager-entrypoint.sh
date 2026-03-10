#!/bin/sh
set -e

# Expande variáveis de ambiente no arquivo de configuração usando sed
cp /etc/alertmanager/alertmanager.yml /tmp/alertmanager.yml.template

sed -e "s|\${TELEGRAM_MONITOR_BOT_TOKEN}|${TELEGRAM_MONITOR_BOT_TOKEN}|g" \
    -e "s|\${TELEGRAM_MONITOR_BOT_CHAT_ID}|${TELEGRAM_MONITOR_BOT_CHAT_ID}|g" \
    /tmp/alertmanager.yml.template > /etc/alertmanager/alertmanager.yml

# Inicia o alertmanager
exec /bin/alertmanager "$@"
