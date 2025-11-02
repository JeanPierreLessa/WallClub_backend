# Deploy Produção - Monorepo WallClub

## SSH
```bash
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.46
cd /var/www/wallclub_backend
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
git pull origin main

# Rebuild e restart
docker-compose build --no-cache web riskengine celery-worker celery-beat
docker-compose down
docker-compose up -d

# Verificar
docker ps
docker logs wallclub-django-monorepo --tail 50
```

## Deploy Rápido (Apenas restart)
```bash
docker-compose restart web riskengine celery-worker celery-beat
```


## Logs e Monitoramento
```bash
# Status de todos os containers
docker ps

# Logs individuais
docker logs wallclub-django-monorepo --tail 100 -f
docker logs wallclub-riskengine-monorepo --tail 100 -f
docker logs wallclub-celery-worker-monorepo --tail 100 -f
docker logs wallclub-celery-beat-monorepo --tail 100 -f
docker logs wallclub-redis-monorepo --tail 100 -f

# Logs do Docker Compose
docker-compose logs -f web
docker-compose logs -f riskengine
docker-compose logs -f celery-worker
docker-compose logs -f celery-beat
```

## Containers e Portas
- **wallclub-django-monorepo**: Django (porta 8003)
- **wallclub-riskengine-monorepo**: Risk Engine/Antifraude (porta 8004)
- **wallclub-redis-monorepo**: Redis (porta 6380 externa, 6379 interna)
- **wallclub-celery-worker-monorepo**: Worker Celery
- **wallclub-celery-beat-monorepo**: Beat Celery

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
