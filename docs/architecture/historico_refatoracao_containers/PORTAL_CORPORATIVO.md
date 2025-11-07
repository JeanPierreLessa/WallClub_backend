# Portal Corporativo - WallClub

**Versão:** 1.0  
**Data:** 06/11/2025  
**Status:** ✅ Em Produção

---

## 📋 Visão Geral

Portal institucional público do WallClub, sem necessidade de autenticação, destinado a apresentar a empresa, serviços e captar leads de clientes e lojistas.

**URLs:**
- `corporativo.wallclub.com.br` (subdomínio específico)
- `wallclub.com.br` (domínio raiz)
- `www.wallclub.com.br` (com www)

---

## 🎯 Objetivos

1. **Apresentação Institucional** - Mostrar a empresa, missão e equipe
2. **Captação de Leads** - Formulário de contato para clientes e lojistas
3. **Marketing** - Divulgar benefícios para clientes e comerciantes
4. **Download do App** - Links para App Store e Google Play
5. **SEO** - Otimização para mecanismos de busca

---

## 📄 Páginas

### 1. Home (`/`)
**Arquivo:** `templates/portais/corporativo/home.html`

**Conteúdo:**
- Hero section com proposta de valor
- 3 cards de serviços principais:
  - Cliente Wall paga menos
  - Menores taxas para lojistas
  - Seguros e assistências
- CTA para download do app
- Links para App Store e Google Play

**Meta Tags:**
- Title: "Wall Club - Descontos e Cashback para Clientes | Recebimento via Cartão"
- Description: "Aproveite os descontos e cashback oferecidos pela Wall Club para aumentar a margem EBITDA da sua loja."

### 2. Para Você Cliente (`/para_voce_cliente/`)
**Arquivo:** `templates/portais/corporativo/para_voce_cliente.html`

**Conteúdo:**
- Hero com proposta de valor para clientes
- Benefícios detalhados:
  - Fácil de usar
  - Parcela menor
  - Mais benefícios (seguros, assistências)
- Seções com imagens ilustrativas
- CTAs para download do app

### 3. Para Você Comerciante (`/para_voce_comerciante/`)
**Arquivo:** `templates/portais/corporativo/para_voce_comerciante.html`

**Conteúdo:**
- Hero com proposta de valor para lojistas
- Benefícios para o negócio:
  - Aumente suas vendas
  - Descontos maiores
  - Reduza suas taxas
- Explicação do sistema revolucionário de pagamentos
- CTA para filiação

### 4. Sobre o Wall Club (`/sobre/`)
**Arquivo:** `templates/portais/corporativo/sobre.html`

**Conteúdo:**
- Nossa história
- Missão e valores
- Equipe (3 sócios fundadores):
  - Fernando Monteiro (CEO)
  - André Sonnenburg (CTO)
  - Luiz Felipe Villac (COO)
- Fotos e biografias dos executivos

### 5. Contato (`/contato/`)
**Arquivo:** `templates/portais/corporativo/contato.html`

**Conteúdo:**
- Formulário de contato com campos:
  - Nome completo
  - Email
  - Telefone
  - Tipo (Consumidor/Lojista)
  - Mensagem
- Informações de contato:
  - Email: atendimento@wallclub.com.br
  - Endereço: Av. Paulista, 726, 18º Andar
  - Horário de atendimento
- Envio via AJAX com feedback visual

### 6. Download App (`/download_app_wall/`)
**Arquivo:** `templates/portais/corporativo/download_app.html`

**Conteúdo:**
- Página standalone para download do app
- Links diretos para App Store e Google Play
- Não está linkada no menu principal (acesso direto)

---

## 🎨 Design e Estilo

### CSS Principal
**Arquivo:** `static/css/modern-style.css`

**Características:**
- Mobile-first approach
- Design system com variáveis CSS
- Paleta de cores:
  - Primary: `#15bfae` (verde água)
  - Primary Dark: `#027368`
  - Secondary: `#2f1c6a` (roxo)
  - Accent: `#fc5185` (rosa)
- Componentes reutilizáveis:
  - Botões (primary, secondary, outline)
  - Cards com hover effects
  - Hero sections responsivas
  - Formulários estilizados

### Responsividade
- **Mobile:** < 768px (menu hambúrguer, layout vertical)
- **Tablet:** 768px - 991px (2 colunas)
- **Desktop:** ≥ 992px (3 colunas, menu horizontal)

### Animações
- Fade in on scroll (IntersectionObserver)
- Hover effects em cards
- Transições suaves (0.3s ease)

---

## 🔧 Implementação Técnica

### Estrutura de Arquivos

```
portais/corporativo/
├── templates/portais/corporativo/
│   ├── base.html                    # Template base
│   ├── home.html                    # Página inicial
│   ├── para_voce_cliente.html       # Para clientes
│   ├── para_voce_comerciante.html   # Para lojistas
│   ├── sobre.html                   # Sobre a empresa
│   ├── contato.html                 # Formulário de contato
│   ├── download_app.html            # Download do app
│   └── includes/
│       ├── menu.html                # Menu de navegação
│       └── footer.html              # Footer
├── static/
│   ├── css/
│   │   └── modern-style.css         # CSS principal
│   ├── images/                      # Imagens do portal
│   └── docs/                        # PDFs (termos, políticas)
├── urls.py                          # Rotas do portal
└── views.py                         # Views do portal
```

### Roteamento

**Middleware:** `wallclub.middleware.subdomain_router.SubdomainRouterMiddleware`

**Mapeamento:**
```python
'corporativo': 'wallclub.urls_corporativo'
```

**URLconf:** `wallclub/urls_corporativo.py`
```python
path('', include('portais.corporativo.urls'))
```

**URLs do App:** `portais/corporativo/urls.py`
```python
path('', home_view, name='home')
path('para_voce_cliente/', para_voce_cliente_view, name='para_voce_cliente')
path('para_voce_comerciante/', para_voce_comerciante_view, name='para_voce_comerciante')
path('sobre/', sobre_view, name='sobre')
path('contato/', contato_view, name='contato')
path('download_app_wall/', download_app_view, name='download_app')
path('api/informacoes/', api_informacoes, name='api_informacoes')
```

### Views

**Arquivo:** `portais/corporativo/views.py`

**Principais funções:**
- `home_view()` - Renderiza home
- `para_voce_cliente_view()` - Renderiza página de clientes
- `para_voce_comerciante_view()` - Renderiza página de comerciantes
- `sobre_view()` - Renderiza sobre
- `contato_view()` - Processa formulário de contato (POST) e renderiza página
- `download_app_view()` - Renderiza página de download
- `api_informacoes()` - API pública com informações corporativas (JSON)

### Formulário de Contato

**Processamento:**
1. Validação de campos obrigatórios
2. Log da mensagem recebida
3. Retorno JSON com sucesso/erro
4. Frontend: AJAX com feedback visual

**TODO:** Implementar envio de email ou salvamento no banco de dados

---

## 🚀 Deploy

### Nginx

**Arquivo:** `/nginx.conf`

```nginx
server {
    listen 80;
    server_name corporativo.wallclub.com.br wallclub.com.br www.wallclub.com.br;
    
    location / {
        proxy_pass http://portais_backend;
        # ... headers
    }
    
    location /static/ {
        alias /staticfiles/;
        expires 30d;
    }
}
```

### Container

**Container:** `wallclub-portais`  
**Porta:** 8005 (interna)  
**Settings:** `wallclub.settings.portais`

### Comandos de Deploy

```bash
# Deploy seletivo do container portais
cd /var/www/WallClub_backend
git pull origin main
docker-compose up -d --build --no-deps wallclub-portais

# Verificar logs
docker logs wallclub-portais --tail 50

# Restart nginx (se necessário)
docker-compose restart nginx
```

### DNS/Load Balancer

**Configuração necessária no AWS Load Balancer:**
- Adicionar regras para `corporativo.wallclub.com.br`
- Adicionar `wallclub.com.br` e `www.wallclub.com.br` (opcional)
- Certificado SSL deve incluir os novos subdomínios

---

## 📊 Métricas e Analytics

### Google Analytics (TODO)
- Implementar tracking de páginas
- Eventos de conversão (formulário enviado, app download)
- Funil de conversão cliente/lojista

### Formulário de Contato
- Logs em `logger.info()` com nome, email e tipo
- TODO: Dashboard de leads no portal admin

---

## 🔐 Segurança

### CSRF Protection
- Formulário de contato usa `{% csrf_token %}`
- Validação no backend

### Rate Limiting
- Nginx: `limit_req zone=portal burst=20 nodelay`
- 10 requisições/segundo por IP

### Headers de Segurança
- HSTS habilitado
- Content-Type nosniff
- XSS protection

---

## 📱 SEO e Meta Tags

### Open Graph
- Implementado em `base.html`
- Customizável por página via blocks

### Canonical URLs
- Definidos para evitar conteúdo duplicado

### Sitemap (TODO)
- Gerar sitemap.xml
- Submeter ao Google Search Console

---

## 🎯 Próximos Passos

- [ ] Implementar envio de email no formulário de contato
- [ ] Adicionar Google Analytics
- [ ] Criar dashboard de leads no portal admin
- [ ] Implementar sitemap.xml
- [ ] Adicionar mais conteúdo SEO (blog?)
- [ ] Testes A/B de conversão
- [ ] Integrar com CRM (Salesforce/HubSpot?)

---

## 📞 Contato Técnico

**Responsável:** Equipe WallClub  
**Última Atualização:** 06/11/2025
