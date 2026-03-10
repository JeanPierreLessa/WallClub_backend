#!/bin/sh
set -e

# Expande variáveis de ambiente no arquivo de configuração
envsubst < /etc/alertmanager/alertmanager.yml > /tmp/alertmanager.yml.expanded
mv /tmp/alertmanager.yml.expanded /etc/alertmanager/alertmanager.yml

# Inicia o alertmanager
exec /bin/alertmanager "$@"
