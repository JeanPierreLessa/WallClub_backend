# Especificação de Layout - Portal WallClub

## 1. Visão Geral

Este documento especifica o layout padrão utilizado nos portais WallClub, baseado no Portal Lojista. O layout é responsivo, moderno e utiliza Bootstrap 5.3.0 como framework base.

## 2. Dependências Externas

### 2.1 CSS
```html
<!-- Bootstrap 5.3.0 -->
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">

<!-- Font Awesome 6.4.0 -->
<link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
```

### 2.2 JavaScript
```html
<!-- Bootstrap JS Bundle (inclui Popper) -->
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
```

## 3. Paleta de Cores

### 3.1 Variáveis CSS (`:root`)
```css
:root {
    /* Gradientes Primários - Azul WallClub */
    --primary-gradient: linear-gradient(135deg, #0f2a5a 0%, #1a4480 100%);
    --primary-hover-gradient: linear-gradient(135deg, #0d2348 0%, #153a6e 100%);
    --primary-color: #1a4480;
    --primary-dark: #0f2a5a;

    /* Gradientes de Status */
    --success-gradient: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    --warning-gradient: linear-gradient(135deg, #ffc107 0%, #fd7e14 100%);
    --danger-gradient: linear-gradient(135deg, #dc3545 0%, #e83e8c 100%);
    --info-gradient: linear-gradient(135deg, #17a2b8 0%, #6f42c1 100%);

    /* Sombras */
    --shadow-light: 0 2px 4px rgba(0,0,0,0.1);
    --shadow-medium: 0 4px 6px rgba(0,0,0,0.1);
    --shadow-heavy: 0 8px 15px rgba(0,0,0,0.2);

    /* Border Radius */
    --border-radius: 8px;
    --border-radius-lg: 12px;
    --border-radius-xl: 20px;
}
```

### 3.2 Cores de Fundo
- **Background principal**: `#f8f9fa`
- **Cards/Containers**: `#ffffff`
- **Sidebar**: Gradiente primário (`var(--primary-gradient)`)

## 4. Estrutura de Layout

### 4.1 Layout Desktop (≥992px)

#### Sidebar Fixa (Esquerda)
- **Largura**: 260px
- **Posição**: Fixa (`position: fixed`)
- **Background**: Gradiente primário
- **Z-index**: 1040
- **Overflow**: Auto (scroll vertical)

```html
<aside class="sidebar-desktop d-none d-lg-block">
    <div class="sidebar-header">
        <h4><i class="fas fa-store me-2"></i>Portal Lojista</h4>
        <img src="logo.png" alt="WallClub" height="40">
    </div>

    <ul class="nav flex-column">
        <li class="nav-item">
            <a class="nav-link active" href="#">
                <i class="fas fa-home me-2"></i>Home
            </a>
        </li>
        <!-- Mais itens -->
    </ul>
</aside>
```

#### Conteúdo Principal
- **Margin-left**: 260px (espaço para sidebar)
- **Padding**: 20px
- **Min-height**: 100vh

```html
<div class="main-content">
    <!-- Conteúdo aqui -->
</div>
```

### 4.2 Layout Mobile (<992px)

#### Navbar Fixa (Topo)
- **Posição**: Fixa no topo
- **Background**: Gradiente primário
- **Z-index**: 1030
- **Altura**: ~70px

```html
<nav class="navbar navbar-dark fixed-top navbar-mobile d-lg-none">
    <div class="container-fluid">
        <button class="navbar-toggler" type="button"
                data-bs-toggle="offcanvas" data-bs-target="#menuLateral">
            <span class="navbar-toggler-icon"></span>
        </button>

        <div class="d-flex align-items-center">
            <img src="logo.png" alt="WallClub" height="40">
        </div>
    </div>
</nav>
```

#### Offcanvas Menu (Lateral Deslizante)
- **Largura**: Padrão Bootstrap (320px)
- **Background**: Gradiente primário
- **Z-index**: 1055

```html
<div class="offcanvas offcanvas-start d-lg-none" tabindex="-1" id="menuLateral">
    <div class="offcanvas-header">
        <h5 class="offcanvas-title text-white">Menu Principal</h5>
        <button type="button" class="btn-close btn-close-white"
                data-bs-dismiss="offcanvas"></button>
    </div>
    <div class="offcanvas-body">
        <ul class="nav flex-column">
            <!-- Itens do menu -->
        </ul>
    </div>
</div>
```

#### Conteúdo Principal Mobile
- **Margin-top**: 70px (espaço para navbar)
- **Padding**: 15px 10px

## 5. Componentes

### 5.1 Cards

#### Card Padrão
```html
<div class="card">
    <div class="card-header">
        <h4>Título do Card</h4>
    </div>
    <div class="card-body">
        <!-- Conteúdo -->
    </div>
</div>
```

**Estilos**:
- Border: none
- Border-radius: `var(--border-radius-lg)` (12px)
- Box-shadow: `var(--shadow-medium)`
- Hover: `translateY(-2px)` + sombra mais forte

#### Card Header
- Background: Gradiente primário
- Color: white
- Font-weight: 600
- Border-radius: 12px 12px 0 0

#### Cards de Estatísticas
```html
<div class="stats-card stats-card-hoje">
    <div class="row align-items-center">
        <div class="col-8">
            <div class="stats-value">1.234</div>
            <div class="stats-label">Vendas Hoje</div>
        </div>
        <div class="col-4 text-end">
            <i class="fas fa-shopping-cart stats-icon text-success"></i>
        </div>
    </div>
</div>
```

**Classes de Borda**:
- `.stats-card-hoje`: border-left verde (#28a745)
- `.stats-card-mes`: border-left azul (#007bff)
- `.stats-card-valor-hoje`: border-left amarelo (#ffc107)
- `.stats-card-valor-mes`: border-left ciano (#17a2b8)

### 5.2 Botões

#### Botão Primário
```html
<button class="btn btn-primary">
    <i class="fas fa-search me-2"></i>Buscar
</button>
```

**Estilos**:
- Background: Gradiente primário
- Border: none
- Border-radius: 8px
- Padding: 10px 20px
- Font-weight: 500
- Hover: `translateY(-1px)` + sombra

#### Variações
- `.btn-success` / `.btn-search`: Gradiente verde
- `.btn-warning` / `.btn-export`: Gradiente laranja
- `.btn-danger`: Gradiente vermelho
- `.btn-info`: Gradiente ciano-roxo

### 5.3 Formulários

#### Input Padrão
```html
<div class="mb-3">
    <label for="campo" class="form-label">
        <i class="fas fa-user me-2"></i>Nome do Campo
    </label>
    <input type="text" class="form-control" id="campo">
</div>
```

**Estilos**:
- Border: 2px solid #e9ecef
- Border-radius: 8px
- Padding: 12px 15px
- Font-size: 16px
- Focus: border azul primário + sombra

#### Label
- Font-weight: 600
- Color: #495057
- Margin-bottom: 8px

### 5.4 Tabelas

```html
<div class="table-responsive">
    <table class="table table-striped table-hover smaller-font">
        <thead>
            <tr>
                <th>Coluna 1</th>
                <th>Coluna 2</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Dado 1</td>
                <td>Dado 2</td>
            </tr>
        </tbody>
    </table>
</div>
```

**Estilos**:
- **thead th**: Background gradiente primário, color white, font-weight 600
- **tbody tr hover**: Background rgba(42, 82, 152, 0.05)
- **Border-radius**: 8px (overflow hidden)
- **Box-shadow**: Sombra leve

### 5.5 Navegação Lateral

#### Link de Navegação
```html
<a class="nav-link active" href="#">
    <i class="fas fa-home me-2"></i>Home
</a>
```

**Estilos**:
- Color: rgba(255,255,255,0.9)
- Padding: 12px 20px
- Border-radius: 8px
- Margin: 3px 0
- Hover/Active: background rgba(255,255,255,0.2) + `translateX(5px)`

#### Link de Logout
```html
<a class="nav-link logout-link" href="#">
    <i class="fas fa-sign-out-alt me-2"></i>Sair
</a>
```

**Estilos**:
- Color: #ff6b6b
- Border-top: 1px solid rgba(255,255,255,0.1)
- Margin-top: 15px
- Padding-top: 15px

### 5.6 Filtros e Containers

#### Container de Filtros
```html
<div class="filter-card">
    <form id="filtroForm">
        <!-- Campos de filtro -->
    </form>
</div>
```

**Estilos**:
- Background: white
- Border-radius: 12px
- Padding: 25px
- Box-shadow: Média
- Border-left: 4px solid azul primário

#### Container de Resultados
```html
<div class="results-container">
    <!-- Tabela ou cards de resultados -->
</div>
```

**Estilos**: Idênticos ao filter-card, sem border-left

### 5.7 Alertas

```html
<div class="alert alert-success alert-dismissible fade show" role="alert">
    <i class="fas fa-check-circle me-2"></i>Operação realizada com sucesso!
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
```

**Estilos**:
- Border: none
- Border-radius: 8px
- Box-shadow: Sombra leve

### 5.8 Badges

```html
<span class="badge bg-success">Aprovado</span>
<span class="badge bg-warning">Pendente</span>
<span class="badge bg-danger">Cancelado</span>
```

**Estilos**:
- Font-size: 0.75rem
- Padding: 0.5em 0.75em
- Border-radius: 8px

### 5.9 Page Header Compact

```html
<div class="page-header-compact">
    <h1 class="page-title">
        <i class="fas fa-shopping-cart"></i>Título da Página
    </h1>
    <p class="page-subtitle">Descrição ou subtítulo</p>
</div>
```

**Estilos**:
- Background: white
- Border-radius: 12px
- Padding: 20px 25px
- Box-shadow: Média
- Border-left: 4px solid azul primário

## 6. Páginas de Autenticação

### 6.1 Layout de Login/Auth

```html
<body class="auth-body">
    <div class="auth-container">
        <div class="auth-header">
            <div class="wallclub-logo">
                <i class="fas fa-wallet"></i>
            </div>
            <h1>Portal WallClub</h1>
            <p>Subtítulo ou descrição</p>
        </div>

        <div class="auth-body">
            <form method="post">
                <!-- Campos do formulário -->
            </form>
        </div>
    </div>
</body>
```

**Estilos**:
- **body.auth-body**: Background gradiente primário, flex center
- **auth-container**: Max-width 500px, border-radius 20px
- **auth-header**: Background gradiente, padding 30px
- **wallclub-logo**: Círculo 80x80px, background rgba branco
- **auth-body**: Padding 40px 30px

## 7. Responsividade

### 7.1 Breakpoints

- **Desktop**: ≥992px (lg)
- **Tablet**: 768px - 991px (md)
- **Mobile**: <768px (sm/xs)

### 7.2 Ajustes por Breakpoint

#### Desktop (≥992px)
- Sidebar fixa visível
- Navbar mobile oculta
- Main-content com margin-left 260px
- Padding padrão: 20px

#### Tablet/Mobile (<992px)
- Sidebar oculta
- Navbar mobile visível
- Offcanvas menu
- Main-content com margin-top 70px
- Padding reduzido: 15px 10px

#### Mobile Pequeno (<576px)
- Logo navbar: 35px
- Main-content padding: 10px 5px
- Nav-link padding: 10px 15px
- Font-sizes reduzidos

## 8. Animações e Transições

### 8.1 Transições Padrão
```css
* {
    transition: box-shadow 0.3s ease, transform 0.3s ease;
}
```

### 8.2 Hover Effects
- **Cards**: `translateY(-2px)` + sombra mais forte
- **Botões**: `translateY(-1px)` + sombra
- **Nav-links**: `translateX(5px)` + background

### 8.3 Loading Animation
```html
<div class="loading">
    <i class="fas fa-spinner fa-spin"></i>
    <p>Carregando dados...</p>
</div>
```

**Keyframe**:
```css
@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
```

## 9. Scrollbar Customizada

```css
::-webkit-scrollbar {
    width: 8px;
}

::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

::-webkit-scrollbar-thumb {
    background: var(--primary-gradient);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--primary-hover-gradient);
}
```

## 10. Z-Index Hierarchy

```
1070 - Tooltips e Popovers
1060 - Modais
1055 - Offcanvas Menu
1050 - Dropdowns
1040 - Sidebar Desktop / Botões de ação
1030 - Navbar Mobile
1    - Cards, Tabelas, Conteúdo geral
```

## 11. Utilitários Customizados

### 11.1 Texto com Gradiente
```html
<h1 class="text-gradient">Título com Gradiente</h1>
```

### 11.2 Sombra Customizada
```html
<div class="shadow-custom">Elemento com sombra</div>
```

### 11.3 Borda com Gradiente
```html
<div class="border-gradient">Elemento com borda gradiente</div>
```

## 12. JavaScript - Funções Comuns

### 12.1 Formatação de Moeda
```javascript
function formatarMoeda(valor) {
    if (!valor || valor === '') return '0,00';
    return parseFloat(valor).toFixed(2).replace('.', ',');
}
```

### 12.2 Status Badges
```javascript
function getStatusBadge(status) {
    const s = status.toLowerCase();
    if (s.includes('pago') || s.includes('aprovado')) return 'bg-success';
    if (s.includes('pendente') || s.includes('aguardando')) return 'bg-warning';
    if (s.includes('cancelado') || s.includes('negado')) return 'bg-danger';
    return 'bg-info';
}
```

### 12.3 Validação de Datas
```javascript
function validarDatas() {
    const dataInicial = document.getElementById('data_inicio');
    const dataFinal = document.getElementById('data_fim');

    if (dataInicial && dataFinal && dataInicial.value && dataFinal.value) {
        const inicio = new Date(dataInicial.value);
        const fim = new Date(dataFinal.value);

        if (inicio > fim) {
            alert('A data inicial não pode ser maior que a data final.');
            return false;
        }

        const diffDays = Math.ceil((fim - inicio) / (1000 * 60 * 60 * 24));
        if (diffDays > 365) {
            alert('O período selecionado não pode ser maior que 1 ano.');
            return false;
        }
    }
    return true;
}
```

### 12.4 Loading e Erro
```javascript
function mostrarLoading(containerId = 'resultados') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Carregando dados...</p>
            </div>
        `;
    }
}

function mostrarErro(mensagem, containerId = 'resultados') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${mensagem}
            </div>
        `;
    }
}
```

## 13. Boas Práticas

### 13.1 Acessibilidade
- Sempre usar labels em formulários
- Incluir atributos `alt` em imagens
- Usar `aria-label` quando necessário
- Manter contraste adequado de cores

### 13.2 Performance
- Usar CDN para bibliotecas externas
- Minimizar uso de animações pesadas
- Lazy loading para imagens quando possível
- Evitar z-index desnecessários

### 13.3 Responsividade
- Testar em múltiplos dispositivos
- Usar classes Bootstrap quando possível
- Manter padding/margin proporcionais
- Font-size mínimo de 14px em mobile

### 13.4 Consistência
- Seguir a paleta de cores definida
- Usar variáveis CSS para valores repetidos
- Manter padrão de border-radius
- Aplicar sombras de forma consistente

## 14. Arquivos de Referência

### 14.1 Estrutura de Arquivos
```
portais/lojista/
├── static/
│   ├── css/
│   │   └── lojista.css          # CSS customizado completo
│   ├── js/
│   │   └── lojista-common.js    # Funções JS comuns
│   └── images/
│       └── logo.png
└── templates/
    └── portais/lojista/
        ├── base.html            # Template base
        ├── base_auth.html       # Template para autenticação
        └── [outras páginas]
```

### 14.2 Ordem de Carregamento CSS
1. Bootstrap 5.3.0
2. Font Awesome 6.4.0
3. lojista.css (customizações)

### 14.3 Ordem de Carregamento JS
1. Bootstrap Bundle (final do body)
2. lojista-common.js
3. Scripts específicos da página

---

**Versão**: 1.0
**Última atualização**: 2025
**Baseado em**: Portal Lojista WallClub
