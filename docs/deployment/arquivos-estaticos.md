# Configuração de Arquivos Estáticos

## Visão Geral

O projeto utiliza **WhiteNoise** para servir arquivos estáticos em produção sem `DEBUG=True` e sem necessidade de nginx.

## Configuração

### 1. Middleware (já configurado)
```python
# wallclub/settings/base.py
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # ← Obrigatório após SecurityMiddleware
    # ... outros middlewares
]
```

### 2. Settings Estáticos
```python
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'  # Destino do collectstatic
```

### 3. Estrutura de Diretórios
```
portais/
├── admin/static/
│   ├── images/logo_wall_admin.png
│   └── js/...
├── lojista/static/
│   ├── css/lojista.css
│   ├── images/logo_wall_lojista.png
│   └── js/lojista-common.js
└── corporativo/static/
    └── images/logo_wall.png
```

## Procedimento Obrigatório após Deploy

### ⚠️ SEMPRE executar após rebuild do container:

```bash
docker exec wallclub-django python manage.py collectstatic --noinput
```

**Por quê?** O rebuild cria um novo container vazio. O `collectstatic` copia arquivos de:
- `/app/portais/*/static/` → `/app/staticfiles/`
- Arquivos do Django Admin
- Outros apps instalados

### Verificar se arquivos foram coletados:

```bash
# Verificar CSS e JS do lojista
docker exec wallclub-django ls -la /app/staticfiles/css/ | grep lojista
docker exec wallclub-django ls -la /app/staticfiles/js/ | grep lojista
docker exec wallclub-django ls -la /app/staticfiles/images/ | grep logo
```

## Troubleshooting

### Problema: Arquivos 404 após deploy
**Causa:** Esqueceu de rodar `collectstatic` após rebuild  
**Solução:**
```bash
docker exec wallclub-django python manage.py collectstatic --noinput
```

### Problema: MIME type 'text/html' em vez de 'application/javascript'
**Causa:** WhiteNoise não está servindo o arquivo, Django retorna página 404  
**Solução:**
1. Verificar se arquivo existe: `docker exec wallclub-django ls /app/staticfiles/js/lojista-common.js`
2. Se não existe, rodar collectstatic
3. Fazer hard refresh no browser (Cmd+Shift+R)

### Problema: Logo quebrado no portal
**Causa:** Arquivo não foi copiado para o container durante build  
**Solução:**
1. Verificar se existe localmente: `ls services/django/portais/lojista/static/images/logo_wall_lojista.png`
2. Se existe localmente mas não no container, fazer rebuild
3. Após rebuild, rodar collectstatic

### Problema: CSS/JS antigo após atualização
**Causa:** Cache do browser ou WhiteNoise  
**Solução:**
```bash
# Hard refresh no browser (Cmd+Shift+R ou Ctrl+Shift+R)

# Limpar cache Django
docker exec wallclub-django python -c "from django.core.cache import cache; cache.clear()"

# Recopilar arquivos
docker exec wallclub-django python manage.py collectstatic --noinput --clear
```

## Fluxo Completo de Deploy

```bash
# 1. Pull do código
git pull origin feature/multi-app-security

# 2. Rebuild container
docker-compose stop web
docker-compose rm -f web
docker-compose build --no-cache web
docker-compose up -d web

# 3. ⚠️ OBRIGATÓRIO: Coletar estáticos
docker exec wallclub-django python manage.py collectstatic --noinput

# 4. Verificar
docker exec wallclub-django ls /app/staticfiles/js/lojista-common.js
docker exec wallclub-django ls /app/staticfiles/css/lojista.css
docker exec wallclub-django ls /app/staticfiles/images/logo_wall_lojista.png
```

## Migração de Arquivos Estáticos

Se adicionar novos arquivos estáticos:

1. **Colocar em** `/portais/[app]/static/`
2. **Commit no Git**
3. **Deploy** (rebuild + collectstatic)

**NÃO colocar arquivos em** `/staticfiles/` - esse é o diretório de DESTINO do collectstatic.

## WhiteNoise vs Nginx

**WhiteNoise:**
- ✅ Simples, sem configuração extra
- ✅ Funciona com DEBUG=False
- ✅ Compressão gzip automática
- ✅ Cache headers otimizados
- ❌ Não serve mídia (uploads)

**Nginx (não usado atualmente):**
- ✅ Mais rápido para arquivos grandes
- ✅ Serve estáticos + mídia
- ❌ Configuração adicional necessária
- ❌ Container extra

Para o projeto atual, **WhiteNoise é suficiente**.
