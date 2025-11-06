# Centralização de Templates e Envio de Emails

**Data:** 05/11/2025  
**Status:** ✅ Concluído

## 📋 Objetivo

Centralizar todos os templates de email e padronizar o envio através do `wallclub_core.integracoes.email_service.EmailService`.

## 🎯 Benefícios

- ✅ **Templates em local único:** `services/django/templates/emails/`
- ✅ **Template base reutilizável:** Estilos e estrutura padronizados
- ✅ **Serviço único de envio:** Sem duplicação de código SMTP
- ✅ **Manutenção simplificada:** Alterações visuais em um único lugar
- ✅ **Logs centralizados:** Rastreamento unificado de envios
- ✅ **Suporte a anexos:** Funcionalidade já implementada no serviço central

## 📁 Estrutura de Templates

```
services/django/templates/emails/
├── base.html                           # Template base com estilos e estrutura
├── autenticacao/
│   ├── primeiro_acesso.html           # Email de criação de conta
│   ├── reset_senha.html               # Email de recuperação de senha
│   ├── senha_alterada.html            # Confirmação de alteração de senha
│   └── confirmacao_troca_senha.html   # Confirmação de troca de senha
└── checkout/
    ├── link_pagamento.html            # Link de pagamento web
    └── link_recorrencia.html          # Link para cadastro de cartão recorrente
```

## 🔄 Migração Realizada

### 1. Templates Criados

| Template | Localização Antiga | Localização Nova |
|----------|-------------------|------------------|
| `primeiro_acesso.html` | `portais/controle_acesso/templates/portais/controle_acesso/emails/` | `templates/emails/autenticacao/` |
| `reset_senha.html` | `portais/controle_acesso/templates/portais/controle_acesso/emails/` | `templates/emails/autenticacao/` |
| `senha_alterada.html` | `portais/controle_acesso/templates/portais/controle_acesso/emails/` | `templates/emails/autenticacao/` |
| `confirmacao_troca_senha.html` | `portais/controle_acesso/templates/portais/controle_acesso/emails/` | `templates/emails/autenticacao/` |
| `link_pagamento.html` | `checkout/templates/checkout/emails/` | `templates/emails/checkout/` |
| `link_recorrencia.html` | `checkout/link_recorrencia_web/templates/recorrencia/email_cadastro_cartao.html` | `templates/emails/checkout/` |

### 2. Services Refatorados

#### `portais/controle_acesso/email_service.py`
**Antes:**
- Criava conexão SMTP manualmente
- Usava `send_mail()` e `get_connection()` diretamente
- Templates em `portais/controle_acesso/emails/`

**Depois:**
- Usa `wallclub_core.integracoes.email_service.EmailService`
- Templates em `emails/autenticacao/`
- Código reduzido em ~40%

#### `checkout/link_recorrencia_web/services.py`
**Antes:**
- Usava `send_mail()` diretamente
- Template em `recorrencia/email_cadastro_cartao.html`

**Depois:**
- Usa `wallclub_core.integracoes.email_service.EmailService`
- Template em `emails/checkout/link_recorrencia.html`

#### Atualizações de Referências
- `portais/lojista/views.py`: Atualizado para `emails/autenticacao/confirmacao_troca_senha.html`
- `checkout/services.py`: Atualizado para `emails/checkout/link_pagamento.html`

## 📧 Tipos de Email no Sistema

### Autenticação (4 emails)
1. **Primeiro Acesso** - Criação de conta com senha temporária
2. **Reset de Senha** - Recuperação de senha esquecida
3. **Senha Alterada** - Confirmação de alteração de senha
4. **Confirmação Troca Senha** - Confirmação de troca de senha no portal lojista

### Checkout (2 emails)
1. **Link de Pagamento** - Envio de link de pagamento web
2. **Link Recorrência** - Cadastro de cartão para cobrança recorrente

### Exports (3 emails - já centralizados)
1. **Export Transações** - Envio de CSV/Excel de transações
2. **Export Vendas** - Envio de CSV de vendas
3. **Export Conciliação** - Envio de CSV de conciliação

**Total:** 9 tipos de email

## 🛠️ Como Usar

### Enviar Email com Template

```python
from wallclub_core.integracoes.email_service import EmailService

# Exemplo: Email de primeiro acesso
resultado = EmailService.enviar_email(
    destinatarios=['usuario@exemplo.com'],
    assunto='WallClub - Primeiro Acesso',
    template_html='emails/autenticacao/primeiro_acesso.html',
    template_context={
        'usuario': usuario_obj,
        'senha_temporaria': 'ABC123',
        'link_primeiro_acesso': 'https://...',
        'validade_horas': 24,
        'canal_nome': 'WallClub',
        'canal_marca': 'wallclub'
    },
    fail_silently=False
)

if resultado['sucesso']:
    print(f"Email enviado: {resultado['mensagem']}")
else:
    print(f"Erro: {resultado['mensagem']}")
```

### Criar Novo Template de Email

1. **Criar arquivo em `templates/emails/[categoria]/`**

```html
{% extends "emails/base.html" %}

{% block title %}Título do Email{% endblock %}

{% block header_title %}🎯 Título no Header{% endblock %}
{% block header_subtitle %}Subtítulo{% endblock %}

{% block content %}
<p>Olá <strong>{{ nome }}</strong>,</p>

<p>Conteúdo do email...</p>

<div class="info-box">
    <p><strong>Info:</strong> {{ info }}</p>
</div>

<p class="text-center">
    <a href="{{ link }}" class="button button-primary">Ação</a>
</p>
{% endblock %}
```

2. **Usar no service**

```python
resultado = EmailService.enviar_email(
    destinatarios=[email],
    assunto='Assunto',
    template_html='emails/categoria/nome_template.html',
    template_context={'nome': 'João', 'info': 'Dados', 'link': 'https://...'},
    fail_silently=False
)
```

## 🎨 Classes CSS Disponíveis no Template Base

- `.email-wrapper` - Container principal
- `.header` - Cabeçalho com gradiente
- `.content` - Área de conteúdo
- `.footer` - Rodapé
- `.button` - Botão padrão (verde)
- `.button-primary` - Botão primário (azul)
- `.alert` - Alerta amarelo (warning)
- `.alert-success` - Alerta verde (sucesso)
- `.alert-info` - Alerta azul (informação)
- `.alert-danger` - Alerta vermelho (perigo)
- `.info-box` - Caixa de informações cinza
- `.text-center` - Centralizar texto

## 🔍 Variáveis de Contexto Comuns

### Autenticação
- `usuario` - Objeto PortalUsuario
- `canal_nome` - Nome do canal
- `canal_marca` - Marca do canal
- `validade_horas` - Validade do link/token

### Checkout
- `cliente_nome` - Nome do cliente
- `loja_nome` - Nome da loja
- `valor` - Valor da transação
- `link_checkout` - URL do checkout
- `validade_minutos` - Validade do link

## ⚠️ Atenções

1. **Templates antigos ainda existem** - Podem ser removidos após validação em produção
2. **Testar todos os fluxos** antes de remover templates antigos:
   - Criação de usuário admin
   - Criação de usuário lojista
   - Reset de senha
   - Alteração de senha
   - Envio de link de pagamento
   - Cadastro de cartão recorrente
   - Exports assíncronos

3. **Configuração de TEMPLATES no settings.py** deve incluir:
```python
TEMPLATES = [
    {
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),  # Templates centralizados
        ],
        ...
    }
]
```

## 📝 Próximos Passos (Opcional)

1. Criar template para **notificações de transação**
2. Criar template para **alertas de segurança**
3. Criar template para **relatórios periódicos**
4. Adicionar **versionamento de templates** (v1, v2)
5. Implementar **preview de emails** em ambiente de desenvolvimento
6. Adicionar **testes automatizados** para envio de emails

## 🔗 Referências

- Serviço centralizado: `wallclub_core/integracoes/email_service.py`
- Templates base: `services/django/templates/emails/base.html`
- Documentação Django Templates: https://docs.djangoproject.com/en/4.2/topics/templates/
