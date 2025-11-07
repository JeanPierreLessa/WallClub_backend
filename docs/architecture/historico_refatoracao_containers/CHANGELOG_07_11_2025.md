# CHANGELOG - 07/11/2025

## 🎯 Resumo das Alterações

**Objetivo:** Resolver erro de dependência circular entre containers e unificar DNS de APIs.

**Status:** ✅ Implementado, aguardando deploy

---

## 📋 Alterações Principais

### 1. DNS Unificado para APIs

**Antes:**
- `wcapi.wallclub.com.br` → Container APIs (OAuth + Mobile)
- `wcapipos.wallclub.com.br` → Container POS (endpoints POSP2)

**Depois:**
- `wcapi.wallclub.com.br` → **UNIFICADO** com roteamento por path:
  - `/api/oauth/*` → Container APIs (porta 8007)
  - `/api/v1/posp2/*` → Container POS (porta 8006)
  - `/api/internal/*` → Container APIs (porta 8007)
  - `/api/v1/*` → Container APIs (porta 8007)

**Motivo:** Simplificar arquitetura, OAuth centralizado no container APIs.

**Arquivo:** `nginx.conf` (linhas 177-209)

---

### 2. API Interna para Comunicação Entre Containers

**Problema Resolvido:**
```
[2025-11-07 08:24:26] [ERROR] posp2.validar_cpf - No installed app with label 'cliente'.
```

Container POS tentava importar `apps.cliente` diretamente, mas esse app não está instalado no POS.

**Solução:** Criar API HTTP interna para comunicação entre containers.

#### 2.1. Novos Endpoints (Container APIs)

**Arquivo:** `apps/cliente/views_api_interna.py`

6 endpoints criados em `/api/internal/cliente/`:

1. `POST /consultar_por_cpf/` - Buscar cliente por CPF e canal
2. `POST /cadastrar/` - Cadastrar novo cliente (com bureau)
3. `POST /obter_cliente_id/` - Obter ID do cliente
4. `POST /atualizar_celular/` - Atualizar celular
5. `POST /obter_dados_cliente/` - Dados completos
6. `POST /verificar_cadastro/` - Verificar se existe cadastro

**Autenticação:** `@require_oauth_internal` (novo decorator)

#### 2.2. Service Helper

**Arquivo:** `wallclub_core/integracoes/api_interna_service.py`

Classe `APIInternaService` para facilitar chamadas entre containers:

```python
from wallclub_core.integracoes.api_interna_service import APIInternaService

response = APIInternaService.chamar_api_interna(
    metodo='POST',
    endpoint='/api/internal/cliente/consultar_por_cpf/',
    payload={'cpf': '12345678900', 'canal_id': 1},
    contexto='apis'
)
```

**Mapeamento de containers:**
- `apis` → `http://wallclub-apis:8007`
- `pos` → `http://wallclub-pos:8006`
- `portais` → `http://wallclub-portais:8005`
- `riskengine` → `http://wallclub-riskengine:8008`

#### 2.3. Decorator OAuth Interno

**Arquivo:** `wallclub_core/oauth/decorators.py`

Novo decorator `@require_oauth_internal`:
- Aceita tokens OAuth de qualquer contexto servidor
- Valida token via `OAuthService.validate_access_token()`
- Anexa `request.oauth_client` e `request.oauth_token`

---

### 3. Atualização do Container POS

**Arquivos alterados:**
- `posp2/services.py` (3 métodos)
- `posp2/services_transacao.py` (4 imports)
- `posp2/services_conta_digital.py` (1 import)

**Antes:**
```python
from apps.cliente.models import Cliente
from apps.cliente.services import ClienteAuthService

cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id)
```

**Depois:**
```python
from wallclub_core.integracoes.api_interna_service import APIInternaService

response = APIInternaService.chamar_api_interna(
    metodo='POST',
    endpoint='/api/internal/cliente/consultar_por_cpf/',
    payload={'cpf': cpf, 'canal_id': canal_id},
    contexto='apis'
)
cliente = response.get('cliente')
```

---

### 4. Templates de Email Separados por Portal

**Estrutura criada:**
```
templates/emails/
├── admin/
│   ├── base.html (verde #65C97A)
│   ├── primeiro_acesso.html
│   ├── reset_senha.html
│   ├── senha_alterada.html
│   └── confirmacao_troca_senha.html
└── lojista/
    ├── base.html (azul #0f2a5a)
    ├── primeiro_acesso.html
    ├── reset_senha.html
    ├── senha_alterada.html
    └── confirmacao_troca_senha.html
```

**Arquivo:** `portais/controle_acesso/email_service.py`

Métodos atualizados com parâmetro `portal_destino`:
- `enviar_email_primeiro_acesso()`
- `enviar_email_reset_senha()`
- `enviar_email_senha_alterada()`

---

## 📊 Estatísticas

**Arquivos criados:** 13
- 2 bases de email (admin/lojista)
- 8 templates de email
- 2 arquivos de API interna (views + urls)
- 1 service helper (APIInternaService)

**Arquivos modificados:** 8
- nginx.conf
- 3 arquivos do container POS
- 1 email_service.py
- 3 arquivos de documentação

**Endpoints adicionados:** 6 (total agora: 32 APIs internas)

---

## 🚀 Deploy

### Comandos

```bash
cd /var/www/WallClub_backend

# Pull do código
git pull origin v2.0.0

# Rebuild containers afetados
docker-compose up -d --build wallclub-nginx wallclub-pos wallclub-apis

# Verificar logs
docker logs wallclub-pos --tail 50
docker logs wallclub-apis --tail 50
```

### Validação

```bash
# 1. Testar OAuth unificado
curl -X POST https://wcapi.wallclub.com.br/api/oauth/token/ \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "posp2",
    "client_secret": "posp2_N93cAK62qbBq332ElQ4ZZjn26dNhF13Dmn_Lb2ATSftbYFH9bAhsqwPj4gWBw06o",
    "grant_type": "client_credentials"
  }'

# 2. Testar endpoint POS (deve usar API interna)
curl -X POST https://wcapi.wallclub.com.br/api/v1/posp2/valida_cpf/ \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "cpf": "17653377807",
    "terminal": "PBF923BH70663"
  }'
```

**Resultado esperado:** Sem erro `No installed app with label 'cliente'`

---

## 📚 Documentação Atualizada

1. **ARQUITETURA_GERAL.md**
   - Diagrama com DNS unificado
   - Seta de API Interna entre containers
   - Descrição dos 6 novos endpoints

2. **DIRETRIZES_UNIFICADAS.md**
   - Atualizado de 26 para 32 endpoints
   - Exemplo de uso do `APIInternaService`
   - Características do decorator `@require_oauth_internal`

3. **INTEGRACOES.md**
   - Nova seção "Cliente APIs"
   - Exemplos de requisição/resposta
   - Casos de uso

4. **TESTES_POSP2_ENDPOINTS.txt**
   - Todos os endpoints usando `wcapi.wallclub.com.br`
   - Removidas referências a `wcapipos`

---

## ⚠️ Breaking Changes

1. **DNS `wcapipos.wallclub.com.br` REMOVIDO**
   - Atualizar qualquer documentação/código que use esse DNS
   - Usar `wcapi.wallclub.com.br` para todos os endpoints

2. **Container POS não importa mais `apps.cliente`**
   - Qualquer código novo deve usar API interna
   - Não adicionar imports diretos entre containers

---

## 🔍 Troubleshooting

### Erro: "No installed app with label 'cliente'"
**Causa:** Código tentando importar `apps.cliente` no container POS  
**Solução:** Usar `APIInternaService` para chamar API interna

### Erro: 400 Bad Request no OAuth
**Causa:** Usando DNS `wcapipos` em vez de `wcapi`  
**Solução:** Atualizar para `wcapi.wallclub.com.br/api/oauth/token/`

### Erro: Connection refused em API interna
**Causa:** Container APIs não está rodando  
**Solução:** `docker-compose up -d wallclub-apis`

---

## 👥 Equipe

**Desenvolvedor:** Jean Lessa  
**Data:** 07/11/2025  
**Revisão:** Pendente
