# Setup Local - WallClub Monorepo

## Pré-requisitos
- Docker e Docker Compose instalados
- **AWS CLI configurado** com credenciais válidas (`aws configure`)
- **Acesso ao secret** `wall/dev/db` no AWS Secrets Manager (us-east-1)
- MySQL rodando localmente (acessível via `host.docker.internal`)
- Arquivos `.env` mínimos em cada serviço

## Estrutura de Configuração

```
WallClub_backend/
├── docker-compose.yml          # ← Orquestrador principal
├── services/
│   ├── django/
│   │   ├── .env               # ← Criar este arquivo
│   │   └── Dockerfile
│   └── riskengine/
│       ├── .env               # ← Criar este arquivo
│       └── Dockerfile
```

## Passo 1: Configurar AWS e .env

### 1.1 Verificar acesso ao AWS Secret
```bash
# Testar se consegue acessar o secret de desenvolvimento
aws secretsmanager get-secret-value --secret-id wall/dev/db --region us-east-1
```

### 1.2 Criar services/django/.env
```bash
# Ambiente e Debug
ENVIRONMENT=development
DEBUG=True

# AWS Secrets Manager - Desenvolvimento Local
AWS_ACCESS_KEY_ID=AKIA...seu_key_id
AWS_SECRET_ACCESS_KEY=...sua_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_SECRET_NAME_DEV=wall/dev/db
```

### 1.3 Criar services/riskengine/.env  
```bash
# Ambiente e Debug
ENVIRONMENT=development
DEBUG=True

# AWS Secrets Manager - Desenvolvimento Local
AWS_ACCESS_KEY_ID=AKIA...seu_key_id
AWS_SECRET_ACCESS_KEY=...sua_secret_key
AWS_DEFAULT_REGION=us-east-1
AWS_SECRET_NAME_DEV=wall/dev/db
```

**Nota:** 
- Use as mesmas credenciais AWS em ambos os `.env`
- Obtenha as credenciais em `~/.aws/credentials` ou via `aws configure`
- As configurações do banco (user, password, host) vêm do secret `wall/dev/db`

## Passo 2: Subir todos os serviços

Na raiz do monorepo (`WallClub_backend/`):

```bash
# Build e iniciar todos os containers
docker-compose up -d --build

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um serviço específico
docker-compose logs -f web           # Django
docker-compose logs -f riskengine    # Risk Engine
```

## Passo 3: Verificar containers rodando

```bash
docker-compose ps
```

Você deve ver 5 containers:
- `wallclub-redis` (porta 6379) - Cache e Message Broker
- `wallclub-django` (porta 8003) - API Principal
- `wallclub-riskengine` (porta 8004) - Engine Antifraude
- `wallclub-celery-worker` - Worker unificado (processa tasks de ambos os serviços)
- `wallclub-celery-beat` - Beat unificado (agenda tasks periódicas)

## Passo 4: Testar os serviços

```bash
# Django API
curl http://localhost:8003/

# Risk Engine API
curl http://localhost:8004/
```

## Comandos Úteis

```bash
# Parar todos os containers
docker-compose down

# Parar e remover volumes (CUIDADO: apaga dados do Redis)
docker-compose down -v

# Rebuild apenas um serviço
docker-compose build web
docker-compose up -d web

# Entrar em um container
docker-compose exec web bash
docker-compose exec riskengine bash

# Ver uso de recursos
docker stats

# Limpar cache do Docker
docker system prune -a
```

## Estrutura de Portas

| Serviço      | Porta Local | Porta Container |
|--------------|-------------|-----------------|
| Django       | 8003        | 8000            |
| Risk Engine  | 8004        | 8004            |
| Redis        | 6379        | 6379            |

## Troubleshooting

### Erro de permissão em logs/media
```bash
mkdir -p services/django/logs services/django/media
mkdir -p services/riskengine/logs
chmod -R 755 services/*/logs services/django/media
```

### Container não inicia
```bash
# Ver logs completos
docker-compose logs web

# Verificar se as portas já estão em uso
lsof -i :8003
lsof -i :8004
```

### Problema com wallclub_core
O package `wallclub_core` é montado como volume read-only (`./services/core:/app/services/core:ro`). Se houver problemas, o Docker fará o build do package durante a construção da imagem.

## Desenvolvimento

Para desenvolvimento local SEM Docker:

```bash
# Django
cd services/django
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8003

# Risk Engine (outro terminal)
cd services/riskengine
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py runserver 8004
```
