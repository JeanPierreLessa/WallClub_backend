# Deploy Produção - Monorepo WallClub

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
```bash
# Pull do código
git pull origin v2.0.0

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
```bash
# Status de todos os containers
docker ps

# Logs individuais
docker logs wallclub-portais --tail 100 -f
docker logs wallclub-apis --tail 100 -f
docker logs wallclub-pos --tail 100 -f
docker logs wallclub-riskengine --tail 100 -f
docker logs wallclub-celery-worker-portais --tail 100 -f
docker logs wallclub-celery-worker-apis --tail 100 -f
docker logs wallclub-celery-beat --tail 100 -f
docker logs nginx --tail 100 -f
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
