# Configuração Nginx para Capturar IP Real

## Problema
Django está recebendo IP interno do Docker (172.18.0.1) em vez do IP real do cliente.

## Solução

Adicionar no bloco `location` do nginx que faz proxy para o Django:

```nginx
server {
    listen 80;
    server_name seu-dominio.com;

    location / {
        proxy_pass http://localhost:8003;
        
        # HEADERS NECESSÁRIOS PARA IP REAL
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Headers adicionais
        proxy_set_header X-Forwarded-Host $host;
        proxy_set_header X-Forwarded-Port $server_port;
    }
}
```

## Comandos para aplicar

```bash
# 1. Editar configuração do nginx
sudo nano /etc/nginx/sites-available/wallclub

# 2. Adicionar os headers proxy_set_header

# 3. Testar configuração
sudo nginx -t

# 4. Recarregar nginx
sudo systemctl reload nginx
```

## Verificação

Após configurar, os logs devem mostrar:
```
IP capturado via HTTP_X_REAL_IP: 186.205.13.105
```

Em vez de:
```
IP capturado via REMOTE_ADDR: 172.18.0.1
```
