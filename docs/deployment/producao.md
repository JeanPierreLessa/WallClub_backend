# Deploy Produção - Monorepo WallClub

**Última Atualização:** 09/11/2025

## ⚠️ Mudanças Importantes

### Portal Admin - URLs Sem Prefixo

**Antes:** `https://wcadmin.wallclub.com.br/portal_admin/...`
**Agora:** `https://wcadmin.wallclub.com.br/...` (responde na raiz)

**Exemplos:**
- Login: `https://wcadmin.wallclub.com.br/`
- Dashboard: `https://wcadmin.wallclub.com.br/home/`
- Usuários: `https://wcadmin.wallclub.com.br/usuarios/`
- Reset senha: `https://wcadmin.wallclub.com.br/reset-senha/{token}/`
- Primeiro acesso: `https://wcadmin.wallclub.com.br/primeiro_acesso/{token}/`
- **Dashboard Celery:** `https://wcadmin.wallclub.com.br/celery/`
- **Dashboard Antifraude:** `https://wcadmin.wallclub.com.br/antifraude/`

**Motivo:** SubdomainRouterMiddleware roteia `wcadmin.wallclub.com.br` para `wallclub.urls_admin` que responde na raiz.

**Impacto:**
- ✅ Emails de reset de senha corrigidos
- ✅ Emails de primeiro acesso corrigidos
- ✅ Templates HTML atualizados
- ✅ Redirects internos corrigidos
- ✅ Dashboard Celery implementado (monitoramento de tasks e workers)
- ⚠️ Dashboard Celery: tasks agendadas não aparecem (em investigação)

## SSH
```bash
# Servidor antigo
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.46

# Servidor novo (atual)
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.124
cd /var/www/WallClub_backend
```

## Deploy Completo (Primeira Vez)
```bash
# Pull do código
git pull origin main

# Criar diretórios de logs
sudo mkdir -p /var/www/wallclub_backend/services/django/logs
sudo mkdir -p /var/www/wallclub_backend/services/django/media
sudo mkdir -p /var/www/wallclub_backend/services/riskengine/logs
sudo chown -R 1000:1000 /var/www/wallclub_backend/services/django/logs
sudo chown -R 1000:1000 /var/www/wallclub_backend/services/django/media
sudo chown -R 1000:1000 /var/www/wallclub_backend/services/riskengine/logs

# Subir todos os containers
docker-compose down
docker-compose up -d

# Verificar status
docker ps
```

## Deploy de Rotina (Atualizar Código)
## Prune
docker image prune -a
docker system prune -a --volumes
docker system df

```bash
# Pull do código
cd /var/www/WallClub_backend
git pull origin v2.0.0
docker-compose build --no-cache
docker-compose down
docker-compose up -d

# Rebuild e restart (apenas containers Django)
docker-compose build --no-cache wallclub-portais wallclub-apis wallclub-pos
docker-compose down
docker-compose up -d

# Verificar
docker ps
docker logs wallclub-portais --tail 50
```

## Deploy Rápido (Apenas restart)
```bash
docker-compose restart wallclub-portais wallclub-apis wallclub-pos wallclub-riskengine
```


## Logs e Monitoramento

### Dashboards Web
- **Celery:** `https://wcadmin.wallclub.com.br/celery/`
  - Tasks agendadas (8 configuradas no celery.py)
  - Workers ativos
  - Estatísticas de execução
  - ⚠️ Tasks agendadas não aparecem (em investigação)
- **Flower:** `https://flower.wallclub.com.br/`
  - Monitoramento completo do Celery
  - Tasks em tempo real
- **Antifraude:** `https://wcadmin.wallclub.com.br/antifraude/`
  - Revisão manual de transações
  - Blacklist/Whitelist

### Logs de Containers
```bash
# Status de todos os containers
docker ps

# Logs individuais
docker logs wallclub-portais --tail 100 -f
docker logs wallclub-apis --tail 100 -f
docker logs wallclub-pos --tail 100 -f
docker logs wallclub-riskengine --tail 100 -f
docker logs wallclub-celery-worker --tail 100 -f
docker logs wallclub-celery-beat --tail 100 -f
docker logs nginx --tail 100 -f
```

### Logs de Aplicação
```bash
# Logs do Django (por módulo)
tail -f services/django/logs/portais.admin.log
tail -f services/django/logs/portais.vendas.log
tail -f services/django/logs/checkout.2fa.log
tail -f services/django/logs/posp2.log

# Flush Redis (limpar cache e filas)
docker exec wallclub-redis redis-cli FLUSHALL
docker-compose restart wallclub-celery-worker wallclub-celery-beat
```

## Arquitetura de Roteamento (Híbrida)

### Fluxo de Comunicação Completo
```
Internet → ALB/DNS
        → Servidor 46 (10.0.1.46) - Nginx Gateway
        ├─→ Backends Locais (PHP/Django legado)
        └─→ Servidor 124 (10.0.1.124) - Nginx Container → Django Containers
```

### Servidor 46 (Gateway - Nginx Sistema)
**Domínios Legados** (backends locais):
- `admin.wallclub.com.br` → PHP local
- `lojista.wallclub.com.br` → PHP local
- `api.wallclub.com.br` → Django local (porta 8000)
- `riskmanager.wallclub.com.br` → Django local (porta 8004)

**Novos Domínios** (proxy para servidor 124):
- `wcadmin.wallclub.com.br` → `http://10.0.1.124:8005`
- `wcvendas.wallclub.com.br` → `http://10.0.1.124:8005`
- `wclojista.wallclub.com.br` → `http://10.0.1.124:8005`
- `wcapi.wallclub.com.br` → `http://10.0.1.124:8005`
- `apipos.wallclub.com.br` → `http://10.0.1.124:8005`
- `checkout.wallclub.com.br` → `http://10.0.1.124:8005`

**Configuração:** `/etc/nginx/sites-available/default`

### Servidor 124 (Containers Docker)

#### Portas Externas
- **Nginx Container**: 8005 (recebe do servidor 46)

#### Portas Internas (Docker Network)
Cada container Django escuta em sua própria porta interna:
- **wallclub-portais**: 8005 (Admin/Lojista/Vendas/Corporativo)
- **wallclub-apis**: 8007 (APIs Mobile + Checkout)
- **wallclub-pos**: 8006 (Terminal POS)
- **wallclub-riskengine**: 8008 (Antifraude)
- **wallclub-redis**: 6379 (Cache + Broker)
- **wallclub-celery-worker-portais**: Worker Celery Portais
- **wallclub-celery-worker-apis**: Worker Celery APIs
- **wallclub-celery-beat**: Beat Celery

#### Nginx Container Upstreams
O Nginx container roteia baseado no `server_name`:
- `wcadmin.wallclub.com.br` → `wallclub-portais:8005`
- `wcvendas.wallclub.com.br` → `wallclub-portais:8005`
- `wclojista.wallclub.com.br` → `wallclub-portais:8005`
- `wcapi.wallclub.com.br` → `wallclub-apis:8007`
- `apipos.wallclub.com.br` → `wallclub-pos:8006`
- `checkout.wallclub.com.br` → `wallclub-apis:8007`

**Configuração:** `/var/www/WallClub_backend/nginx.conf`

### Security Groups AWS
- **Servidor 46**: Porta 80/443 aberta para internet
- **Servidor 124**: Porta 8005 aberta para servidor 46 (10.0.0.0/16)

### Segurança
- ✅ Containers Django **não expostos** diretamente
- ✅ Apenas Nginx acessível externamente
- ✅ Comunicação interna via rede Docker privada
- ✅ Redis não acessível de fora
- ✅ Servidor 124 só aceita conexões do servidor 46

## Troubleshooting

### Erro: ContainerConfig
```bash
docker-compose down
docker-compose rm -f
docker-compose up -d
```

### Erro: Connection refused Redis
- Verificar se REDIS_PORT=6379 (porta interna, não 6380)
- Verificar se container Redis está rodando: `docker ps | grep redis`

### Push notifications não funcionam
- Verificar certificados em `/app/services/core/wallclub_core/integracoes/firebase_configs/`
- Verificar certificados em `/app/services/core/wallclub_core/integracoes/apn_configs/`

## Limpeza e Manutenção
```bash
# Parar todos os containers
docker-compose down

# Remover containers parados
docker container prune -f

# Remover imagens não utilizadas
docker image prune -a -f

# Limpeza completa (CUIDADO!)
docker system prune -a -f

# Verificar espaço
docker system df
```
