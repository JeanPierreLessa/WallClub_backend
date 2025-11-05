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

## Arquitetura de Portas

### Fluxo de Comunicação
```
Internet → AWS Security Group (8005)
        → EC2 (10.0.1.124)
        → Docker Nginx (8005:80)
        → Containers Django (8005 interna)
```

### Portas Externas (Expostas)
- **Nginx**: 8005 (HTTP temporário, será 80 após SSL) / 443 (HTTPS)

### Portas Internas (Docker Network)
Todos os containers Django escutam na **porta 8005 interna** (não expostas):

- **wallclub-portais**: 8005 (Portais Admin/Lojista/Vendas/Corporativo)
- **wallclub-apis**: 8005 (APIs Mobile + Checkout)
- **wallclub-pos**: 8005 (Terminal POS)
- **wallclub-riskengine**: 8005 (Antifraude)
- **wallclub-redis**: 6379 (Cache + Broker)
- **wallclub-celery-worker-portais**: Worker Celery Portais
- **wallclub-celery-worker-apis**: Worker Celery APIs
- **wallclub-celery-beat**: Beat Celery

### Nginx Upstreams
O Nginx roteia baseado no `server_name`:
- `admin.wallclub.com.br` → `wallclub-portais:8005`
- `lojista.wallclub.com.br` → `wallclub-portais:8005`
- `vendas.wallclub.com.br` → `wallclub-portais:8005`
- `api.wallclub.com.br` → `wallclub-apis:8005`
- `pos.wallclub.com.br` → `wallclub-pos:8005`

### Segurança
- ✅ Containers Django **não expostos** diretamente
- ✅ Apenas Nginx acessível externamente
- ✅ Comunicação interna via rede Docker privada
- ✅ Redis não acessível de fora

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
