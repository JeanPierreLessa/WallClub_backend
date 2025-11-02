# DIRETRIZES TÉCNICAS WALLCLUB DJANGO

## REGRAS FUNDAMENTAIS DE COMPORTAMENTO

### 1. COMUNICAÇÃO E VALIDAÇÃO:
- Fale sempre em português
- Seja técnico e direto - linguagem simples, clara, sem floreios
- Responda SOMENTE com base no código/contexto visível
- Faça perguntas breves e objetivas para esclarecer
- Liste opções com prós e contras quando houver múltiplas alternativas
- Respeite o formato solicitado: comentário, código puro, JSON, markdown, etc.

### 2. CONTROLE DE ESCOPO ABSOLUTO:
- **NUNCA** invente códigos, variáveis, métodos ou APIs - diga "Isso não está claro no seu input"
- **NUNCA** crie código não solicitado explicitamente
- **NUNCA** complete funções/estruturas sem pedido direto
- **NUNCA** tome decisões de simplificação que empurrem problemas para frente
- **NUNCA** use dados hardcoded (só quando explicitamente solicitado)
- Antes de responder: "Essa resposta foi solicitada exatamente?"

### 3. CONFIRMAÇÃO OBRIGATÓRIA:
- Sempre perguntar antes de propor soluções que exijam ações do usuário
- Consultar usuário antes de mudar abordagem quando algo falhar
- Validar requisitos e escopo antes de implementar
- **NUNCA** assumir o que o usuário quer

### 3.1. CONTAINERS DESACOPLADOS (Fase 6A/6B/6C - 02/11/2025):

**REGRA DE OURO: ZERO IMPORTS DIRETOS ENTRE CONTAINERS**

**PROIBIDO:**
```python
# ❌ ERRADO
from posp2.models import Terminal
from checkout.models import CheckoutCliente
```

**OBRIGATÓRIO:**
```python
# ✅ CORRETO - Lazy import
from django.apps import apps
def minha_funcao():
    Terminal = apps.get_model('posp2', 'Terminal')
```

**3 Estratégias de Comunicação:**
1. **APIs REST Internas (70%)**: 26 endpoints `/api/internal/*` (OAuth 2.0, sem rate limiting)
2. **SQL Direto (25%)**: `comum/database/queries.py` (somente leitura)
3. **Lazy Imports (5%)**: `apps.get_model()` quando absolutamente necessário

**CORE Limpo:**
- `comum/*` NUNCA importa de `apps/*`, `posp2/*`, `checkout/*`, `portais/*`
- Caller deve passar dados necessários

**Validação:**
```bash
bash scripts/validar_dependencias.sh
# Esperado: ✓ SUCESSO: Containers desacoplados!
```

## CONFIGURAÇÕES TÉCNICAS OBRIGATÓRIAS

### 4. BANCO DE DADOS E INFRAESTRUTURA:
- **NUNCA** usar fallback para banco - dados sempre via AWS Secrets
- **NÃO** usar migrations Django
- APIs: autenticação obrigatória (OAuth 2.0 + JWT)
- **ENDPOINTS**: **SEMPRE** usar método POST (nunca GET, PUT, DELETE)
  - Parâmetros sempre no body JSON
  - Simplifica integração com terminais POS
  - Evita problemas com cache e logs de URL

### 4.1. CRIAÇÃO DE TABELAS MySQL (OBRIGATÓRIO):
**Collation Padronizada:**
- **SEMPRE** usar `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`
- **Aplicar em**: Database, Tables E Columns (tripla padronização)
- **Motivo**: Evita erro "Illegal mix of collations" em JOINs e WHERE
- **IMPORTANTE**: `utf8mb4_unicode_ci` é compatível entre MySQL 5.7 e 8.0

**Template Obrigatório para CREATE TABLE:**
```sql
CREATE TABLE nome_tabela (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    campo_texto VARCHAR(255) COLLATE utf8mb4_unicode_ci,
    campo_numero DECIMAL(10,2),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Conversão de Tabelas Existentes:**
```sql
-- Converter tabela inteira (estrutura + dados + todas colunas)
ALTER TABLE nome_tabela 
  CONVERT TO CHARACTER SET utf8mb4 
  COLLATE utf8mb4_unicode_ci;
```

**Verificação de Collations:**
```sql
-- Listar tabelas com collation diferente
SELECT TABLE_NAME, TABLE_COLLATION 
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'wallclub' 
AND TABLE_COLLATION != 'utf8mb4_0900_ai_ci'
ORDER BY TABLE_NAME;

-- Listar colunas com collation diferente
SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'wallclub'
AND COLLATION_NAME IS NOT NULL
AND COLLATION_NAME != 'utf8mb4_0900_ai_ci'
ORDER BY TABLE_NAME, COLUMN_NAME;
```

**NUNCA usar COLLATE em queries:**
- ❌ `WHERE campo COLLATE utf8mb4_0900_ai_ci = valor`
- ✅ Padronizar collation no schema, queries ficam limpas
- Se precisar COLLATE na query = schema está errado

### 5. TIMEZONE E DATAS:
- USE_TZ=False no Django
- **NUNCA** usar timezone.now() ou timezone.make_aware()
- **SEMPRE** usar datetime.now() naive
- Container configurado com TZ=America/Sao_Paulo

### 6. VALORES MONETÁRIOS E PERCENTUAIS:
- **Frontend**: Aceitar entrada brasileira (vírgula decimal)
- **Backend**: Converter vírgula→ponto antes de processar
- **Banco**: DECIMAL sempre com ponto
- **Exibição Monetária**: R$ 2.030,22 (ponto=milhares, vírgula=decimal)
- **Exibição Percentual**: 0,2 → 20,00% (multiplicar por 100)
- **Campos HTML**: type="text" para monetários (evitar flechinhas)

### 6.1. CHECKOUT 2FA - SISTEMA DE TELEFONE (30/10/2025):
**Tabela:** `checkout_cliente_telefone`

**Status:**
- `-1` (Pendente): Aguardando primeira confirmação 2FA
- `0` (Desabilitado): Cliente desabilitou ou telefone substituído
- `1` (Ativo): Confirmado após 2FA e pronto para uso

**Regras críticas:**
1. **Imutabilidade:** Campo `primeira_transacao_aprovada_em` trava telefone (não pode mais alterar)
2. **Inativação automática:** Ao marcar primeira transação, **TODOS os outros telefones** do mesmo CPF são inativados (ativo=0)
3. **Exibição obfuscada:** Telefone bloqueado mostra `(21)****0901` abaixo do nome
4. **Unique constraint:** `(cpf, telefone)` - um CPF não pode ter telefone duplicado ativo

**Model:** `checkout/link_pagamento_web/models_2fa.py`
```python
class CheckoutClienteTelefone(models.Model):
    cpf = CharField(max_length=11)  # CPF do cliente
    telefone = CharField(max_length=15)  # Com DDD
    ativo = IntegerField(default=-1)  # -1=Pendente, 0=Desabilitado, 1=Ativo
    primeira_transacao_aprovada_em = DateTimeField(null=True)  # Trava telefone
    telefone_anterior = CharField(max_length=15, null=True)  # Auditoria
    mudado_em = DateTimeField(null=True)  # Auditoria
    
    def marcar_primeira_transacao_aprovada(self):
        """Marca transação + INATIVA todos outros telefones do CPF"""
        self.primeira_transacao_aprovada_em = datetime.now()
        self.ativo = 1
        self.save()
        # CRÍTICO: Inativa outros
        CheckoutClienteTelefone.objects.filter(
            cpf=self.cpf
        ).exclude(id=self.id).update(ativo=0)
```

**Service:** `checkout/link_pagamento_web/services_2fa.py`
- `validar_otp_e_processar()` - Valida OTP + marca telefone se transação aprovada

### 7. URLS DE ARQUIVOS E IMAGENS:
- **SEMPRE** salvar URLs completas no banco: `https://apidj.wallclub.com.br/media/...`
- **NUNCA** salvar URLs relativas (`/media/...`) - apps móveis precisam de URLs absolutas
- **Upload de arquivos**: usar `default_storage.save()` e gerar URL completa
- **Nginx**: configurar `/media/` para servir arquivos estáticos
- **Estrutura**: `media/ofertas/YYYYMMDD_HHMMSS_nome_arquivo.ext`
- **Validação**: Aceitar vírgula e ponto no input

### 8. SISTEMA DE NOTIFICAÇÕES (24/10/2025):
**Princípio: Templates Dinâmicos sem Hardcode**

**Push Notifications (iOS/Android):**
- **NUNCA** hardcodar valores de `category` ou outros campos do template
- **SEMPRE** usar valores dinâmicos do template do banco (`templates_envio_msg`)
- **Category iOS**: Usar `tipo_push` do template (ex: `autorizacao_saldo`, não `AUTORIZACAO_SALDO`)
- **Token Completo**: Enviar IDs completos (UUIDs), não truncados para exibição
- **Valor na API**: Retornar `valor_solicitado` + `valor_bloqueado` para estados diferentes

**SMS:**
- **URL Encoding**: Usar `quote(mensagem, safe=':/')` para preservar URLs
- **NUNCA** usar `safe=''` que codifica caracteres `:` e `/` das URLs
- **Resultado**: `https://tinyurl.com/abc` mantém formato correto no SMS

**Exemplo Correto - Push iOS:**
```python
# ❌ ERRADO: Hardcode
payload["aps"]["category"] = "AUTORIZACAO_SALDO"
autorizacao_id=autorizacao_id[:8]

# ✅ CORRETO: Dinâmico
payload["aps"]["category"] = tipo_push  # Do template
autorizacao_id=autorizacao_id  # UUID completo
```

**Exemplo Correto - SMS:**
```python
# ❌ ERRADO: Codifica tudo
mensagem_encoded = quote(mensagem, safe='')  
# Resultado: https:%2F%2Ftinyurl.com%2Fabc

# ✅ CORRETO: Preserva URLs
mensagem_encoded = quote(mensagem, safe=':/')
# Resultado: https://tinyurl.com/abc
```

**Arquivos Corrigidos (24/10/2025):**
- `comum/integracoes/apn_service.py` - categoria dinâmica
- `posp2/services_conta_digital.py` - token completo
- `apps/conta_digital/services_autorizacao.py` - valor_solicitado na API
- `comum/integracoes/sms_service.py` - URL encoding correto
- `apps/conta_digital/models.py` - timezone fix em esta_expirada()

### INTEGRAÇÕES EXTERNAS (VALIDAÇÃO OPERACIONAL):
- Integrações com serviços externos (ex: MaxMind, gateways, bureaus) só podem ser marcadas como CONCLUÍDAS após validação operacional (resposta 200/OK na API em produção)
- Enquanto a validação estiver pendente, documentar como: "IMPLEMENTADO — VALIDAÇÃO PENDENTE" e seguir com o cronograma macro
- O código deve possuir fallback seguro (ex: score neutro) em caso de falha técnica ou credenciais inválidas
- Registrar no README e no ROTEIRO o status de validação para total transparência de andamento

### 9. SISTEMA DE LOGIN SIMPLIFICADO - MODELO FINTECH (25/10/2025):
**Filosofia:** Toda senha é via SMS/WhatsApp com revalidação recorrente (30 dias)

**Princípios do Novo Modelo:**
- ✅ **NÃO existe "senha definitiva"** - Toda senha é via SMS (4 dígitos)
- ✅ **JWT válido 30 dias** (era 1 dia) - Revalidação mais frequente
- ✅ **Celular revalidado a cada 30 dias** (era 90 dias)
- ✅ **Biometria desde primeiro acesso** - Zero fricção no onboarding
- ✅ **2FA apenas quando necessário** - Novo device ou token expirado

**Inspiração:** Nubank, PicPay, Inter, C6 Bank, Neon

**Fluxo Completo:**
```
Cadastro → Senha SMS (4 dígitos) → Login → JWT 30 dias → Biometria
                                          ↓
                                  (Após 30 dias)
                                          ↓
                                  2FA → Novo JWT 30 dias
```

**Fluxo de Dispositivos:**
- **Clientes:** Limite de 1 dispositivo confiável (validade 30 dias)
- **Vendedores/Lojistas:** Limite de 2 dispositivos
- **Admins:** Sem limite

**Troca de Device:**
- Detecção automática no login (não é tela dedicada)
- Backend retorna erro `device_limite_atingido` com info do device atual
- App mostra modal: "Trocar device?" → Cliente confirma → 2FA → Endpoint `/dispositivos/trocar-no-login/`
- Fluxo reativo, não proativo

**Token Expirado (após 30 dias):**
- Cliente tenta acessar → Recebe erro `token_expired`
- Solicita código 2FA via WhatsApp
- Valida código → Recebe novo JWT 30 dias
- Biometria continua funcionando

**Endpoints Login:**
- `/cliente/login/` - SEMPRE retorna JWT 30 dias (independente do tipo de senha)
- `/cliente/2fa/solicitar_codigo/` - Solicita código 2FA via WhatsApp
- `/cliente/2fa/validar_codigo/` - Valida código + registra device + retorna JWT
- `/cliente/senha/solicitar_troca/` - Envia código OTP via WhatsApp
- ~~/cliente/senha/criar_definitiva/~~ - **REMOVIDO FISICAMENTE** (28/10/2025) - 162 linhas deletadas

**Campos Deprecated:**
- `senha_temporaria` (models.py) - Campo mantido para compatibilidade, mas não usado

**Código Removido (28/10/2025):**
- `views_senha.criar_senha_definitiva()` - Endpoint deprecated ✅
- `services_senha.criar_senha_definitiva()` - Service deprecated ✅
- Rota já havia sido removida anteriormente

**Documentação:** `docs/fluxo_login_revalidacao.md`

### 9.1. BYPASS 2FA - TESTES APPLE/GOOGLE (31/10/2025):
**Objetivo:** Permitir que revisores Apple/Google testem app sem dependência de SMS/WhatsApp

**Implementação:**
- Campo `bypass_2fa` no modelo Cliente (default=False)
- Verificação no início de `services_2fa_login.verificar_necessidade_2fa()`
- Cliente com bypass ativo: retorna JWT diretamente (pula etapas de OTP)
- Log WARNING registra cada uso do bypass

**Fluxo Normal vs Bypass:**
```python
# Cliente Normal
1. POST /cliente/login/ → auth_token
2. POST /cliente/2fa/verificar_necessidade/ → necessario=true
3. POST /cliente/2fa/solicitar_codigo/ → OTP via WhatsApp
4. POST /cliente/2fa/validar_codigo/ → JWT final

# Cliente com Bypass (bypass_2fa=TRUE)
1. POST /cliente/login/ → auth_token
2. POST /cliente/2fa/verificar_necessidade/ → JWT DIRETO ✅
   # Response:
   {
     "necessario": false,
     "motivo": "bypass_2fa_teste",
     "token": "eyJ...",
     "refresh_token": "eyJ...",
     "expires_at": "2025-11-30T..."
   }
```

**Segurança:**
- ✅ Apenas clientes específicos (flag individual no banco)
- ✅ Rastreável via logs: `⚠️ BYPASS 2FA ATIVADO: cliente=123`
- ✅ Reversível: `UPDATE cliente SET bypass_2fa=FALSE`
- ✅ Não quebra fluxo: app já trata `necessario=false` (dispositivo confiável)

**Migration SQL:**
```sql
ALTER TABLE cliente 
ADD COLUMN bypass_2fa BOOLEAN DEFAULT FALSE 
COMMENT 'Bypass 2FA para testes Apple/Google';
```

**Ativar/Desativar:**
```sql
-- Ativar para cliente de teste
UPDATE cliente SET bypass_2fa = TRUE WHERE cpf = '11111111111' AND canal_id = 1;

-- Desativar após aprovação
UPDATE cliente SET bypass_2fa = FALSE WHERE cpf = '11111111111' AND canal_id = 1;
```

**Arquivos:** `apps/cliente/models.py`, `apps/cliente/services_2fa_login.py`, `scripts/producao/release_3.1.0/001_add_bypass_2fa.sql`

### 9.2. SEGURANÇA DE TOKENS JWT - VALIDAÇÃO OBRIGATÓRIA (26/10/2025):
**CRÍTICO:** Falha grave de segurança identificada e corrigida

**PROBLEMA IDENTIFICADO:**
- Método `authenticate()` apenas decodificava JWT sem validar contra tabela de auditoria
- Tokens podiam ser usados mesmo após revogação (is_active=False)
- Novo login não revogava tokens anteriores
- Sistema aceitava múltiplos tokens ativos simultaneamente

**CORREÇÕES APLICADAS:**

**1. Validação Contra Tabela de Auditoria (OBRIGATÓRIO):**
```python
# ❌ ERRADO: Apenas decodificar JWT
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
if payload.get('token_type') != 'access':
    raise exceptions.AuthenticationFailed('Token inválido')
return (ClienteUser(payload), token)

# ✅ CORRETO: Validar contra tabela cliente_jwt_tokens
payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

# CRÍTICO: Validar contra tabela de auditoria
jti = payload.get('jti')
if jti:
    jwt_record = ClienteJWTToken.validate_token(token, jti)
    if not jwt_record:
        raise exceptions.AuthenticationFailed('Token inválido ou revogado')
    jwt_record.record_usage()  # Registrar uso
else:
    # Token sem JTI - rejeitar por segurança
    raise exceptions.AuthenticationFailed('Token inválido')

return (ClienteUser(payload), token)
```

**2. Revogação de Tokens Anteriores ao Gerar Novo:**
```python
# ✅ OBRIGATÓRIO: Revogar tokens ativos antes de criar novo
tokens_revogados = ClienteJWTToken.objects.filter(
    cliente=cliente,
    is_active=True
).update(
    is_active=False,
    revoked_at=datetime.utcnow()
)

registrar_log('apps.cliente', 
    f"🔒 {tokens_revogados} token(s) revogado(s) para cliente_id={cliente.id}")

# Criar novo token
ClienteJWTToken.create_from_token(cliente, token, jti, expires_at, ...)
```

**REGRAS DE OURO:**
1. ✅ **SEMPRE validar JWT contra tabela de auditoria** - nunca confiar apenas na decodificação
2. ✅ **SEMPRE revogar tokens anteriores** ao gerar novo token
3. ✅ **SEMPRE incluir JTI** no payload do token (rejeitar tokens sem JTI)
4. ✅ **SEMPRE registrar uso** do token (last_used, ip_address)
5. ✅ **NUNCA permitir múltiplos tokens ativos** para o mesmo cliente

**ARQUIVOS CORRIGIDOS (26/10/2025):**
- `apps/cliente/jwt_cliente.py` (ClienteJWTAuthentication.authenticate + generate_cliente_jwt_token)

**IMPACTO:**
- **ANTES:** Token revogado (is_active=0) continuava funcionando ❌
- **DEPOIS:** Token revogado é rejeitado imediatamente ✅

**AÇÃO NECESSÁRIA:**
- ⚠️ Verificar se checkout/outros sistemas têm o mesmo problema
- ⚠️ Aplicar mesma lógica em TODOS os sistemas de autenticação via token

### 10. GESTÃO DE VARIÁVEIS E ESCOPO (24/10/2025):
**Regra de Ouro: Resolver Variáveis UMA ÚNICA VEZ**

**PROBLEMA IDENTIFICADO:**
- Buscar `id_loja` múltiplas vezes no mesmo fluxo causa sobrescrita acidental
- Exemplo: `posp2/services.py` buscava `id_loja` 4 vezes (PIX, DÉBITO, À VISTA, PARCELADOS)
- Resultado: Formas de pagamento usando loja errada (loja 1 em vez de loja 31)

**SOLUÇÃO APLICADA:**
```python
# ✅ CORRETO: Resolver id_loja UMA VEZ no início
id_loja = dados_terminal['loja_id']  # Linha 145

# ✅ USAR a variável já resolvida em todos cálculos
valor_com_cashback = calculadora.calcular_desconto(
    id_loja=id_loja,  # Usar variável do escopo pai
    wall='C'
)

# ❌ ERRADO: Buscar novamente sobrescreve a variável
with connection.cursor() as cursor:
    cursor.execute("SELECT loja_id FROM terminais WHERE terminal = %s", [terminal])
    id_loja = cursor.fetchone()[0]  # SOBRESCREVE!
```

**BOAS PRÁTICAS:**
1. **Resolver dependências no início** do método/função
2. **Usar variáveis locais** quando precisar de valores temporários
3. **Nunca sobrescrever** variáveis já resolvidas do escopo pai
4. **Documentar** quando uma variável é "canônica" para todo o fluxo
5. **Validar** que cálculos subsequentes usam a mesma referência

**IMPACTO DO BUG:**
- À VISTA retornava R$ 99.00 (loja 1: desconto 1%) em vez de R$ 103.93 (loja 31: acréscimo 3.93%)
- DÉBITO e outras formas também afetadas
- Correção: Remover queries SQL desnecessárias, usar `id_loja` resolvido na linha 145

**ARQUIVO CORRIGIDO:**
- `posp2/services.py` (24/10/2025)
- Backup: `posp2/services.py.backup_20251024_140331`

### 11. CARGAS PINBANK - LIÇÕES APRENDIDAS (25/10/2025):
**Contexto**: Sistema de carga automática de transações (TEF, Credenciadora, Checkout)

**PROBLEMA 1: Bug do Último Lote (<100 registros)**
- **Causa**: Lógica processava apenas lotes completos de 100
- **Sintoma**: Último lote com registros restantes não era processado
- **Solução**: Adicionar processamento explícito do último lote após loop principal
```python
# Processar último lote se houver registros restantes
if lote_atual:
    with transaction.atomic():
        for row_lote in lote_atual:
            # processar registro
```

**PROBLEMA 2: Queries Duplicadas (info_loja/info_canal)**
- **Causa**: Credenciadora/Checkout buscavam info_loja/info_canal via NSU em cada iteração
- **Impacto**: Queries desnecessárias, performance degradada
- **Solução**: Montar info_loja e info_canal diretamente dos dados da query SQL
```python
# Montar info_loja a partir dos dados já disponíveis
linha['info_loja'] = {
    'id': linha.get('clienteId'),
    'loja_id': linha.get('clienteId'),
    'loja': linha.get('razao_social'),
    'cnpj': linha.get('cnpj'),
    'canal_id': linha.get('canal_id')
}
linha['info_canal'] = self.pinbank_service.pega_info_canal_por_id(linha.get('canal_id'))
```

**PROBLEMA 3: Sobrescrita de Variáveis Calculadas**
- **Causa**: Linha 755 de `calculadora_base_credenciadora.py` sobrescrevia var45
```python
# ❌ ERRADO: Anulava cálculo anterior (linha 690-729)
valores[45] = dados_linha.get('f45') or ''  # f45 não existe, retorna ''
```
- **Sintoma**: var45 (data de pagamento) ficava vazia após cálculo correto
- **Solução**: Remover linha que sobrescreve, documentar que var45 já foi calculado
```python
# ✅ CORRETO: Preservar cálculo anterior
# valores[45] já foi calculado acima (data de pagamento) - NÃO sobrescrever
```

**PROBLEMA 4: Preservação de Data de Pagamento**
- **Requisito**: var45 (data de pagamento) deve ser imutável após primeiro registro
- **Implementação**: Buscar registro existente antes de calcular
```python
registro_existente = BaseTransacoesGestao.objects.filter(var9=nsu_operacao).first()
if registro_existente and registro_existente.var45:
    valores[45] = registro_existente.var45  # Preservar data original
else:
    if descricao_status_pag.startswith('Pago'):
        valores[45] = datetime.now().strftime('%d/%m/%Y')  # Primeira vez
```

**PROBLEMA 5: Import Ausente**
- **Causa**: `BaseTransacoesGestao` usado sem import
- **Sintoma**: `AttributeError: name 'BaseTransacoesGestao' is not defined`
- **Solução**: Adicionar import no topo do arquivo
```python
from pinbank.models import BaseTransacoesGestao
```

**PROBLEMA 6: var4 com Valor Incorreto**
- **Causa**: Usava `info_canal['canal']` que retornava ID (ex: 395) em vez de nome
- **Solução**: Usar `info_canal['nome']` para retornar nome do canal (ex: "WALL 1")
```python
valores[4] = info_canal['nome']  # Nome do canal (ex: WALL 1)
```

**ARQUIVOS CORRIGIDOS (25/10/2025):**
- `parametros_wallclub/calculadora_base_credenciadora.py` (1178 linhas)
- `pinbank/cargas_pinbank/services_carga_credenciadora.py`
- `pinbank/cargas_pinbank/services_carga_checkout.py`

**REGRAS DE OURO:**
1. ✅ **Processar lote residual**: Sempre verificar `if lote_atual:` após loop
2. ✅ **Montar dados localmente**: Evitar queries dentro de loops de 100+ registros
3. ✅ **Não sobrescrever variáveis**: Documentar quando variável já foi calculada
4. ✅ **Preservar histórico**: Dados críticos (datas, valores) devem ser imutáveis
5. ✅ **Imports completos**: Verificar todos models usados estão importados
6. ✅ **Logs de debug**: Adicionar logs temporários para rastrear fluxo de dados

### 8. ARQUITETURA DOCKER - 5 CONTAINERS ORQUESTRADOS (19/10/2025):
**Orquestração Centralizada**: docker-compose.yml no projeto principal

**Containers em Produção:**
1. **wallclub-prod-release300** (porta 8003)
   - Django principal com Gunicorn
   - 3 workers, 2GB RAM, 1.5 CPU
   - Network: default + wallclub-network
   
2. **wallclub-redis** (porta 6379)
   - Cache compartilhado (tokens OAuth, sessões)
   - Volume persistente: redis_data
   - restart: always
   
3. **wallclub-riskengine** (porta 8004)
   - APIs antifraude isoladas
   - 3 workers Gunicorn, 512MB RAM, 0.5 CPU
   - Build: ../wallclub_django_risk_engine
   
4. **wallclub-celery-worker**
   - Tasks assíncronas (detectores antifraude)
   - 4 workers, 256MB RAM, 0.5 CPU
   - 2 tasks: detectar_atividades_suspeitas, bloquear_automatico_critico
   
5. **wallclub-celery-beat**
   - Scheduler de tasks periódicas
   - 128MB RAM, 0.25 CPU
   - Executa tasks a cada 5min (suspeitas) e 10min (bloqueios)

**Deploy Unificado:**
```bash
cd /var/www/wallclub_django
docker-compose up -d --build  # Sobe os 5 containers
```

**Opção de Deploy Seletivo:**
```bash
# Atualiza Django + Risk Engine (mantém Redis rodando)
docker-compose up -d --build --no-deps web riskengine celery-worker celery-beat
```

**Benefícios da Arquitetura:**
- ✅ Isolamento de responsabilidades (APIs, Cache, Tasks, Scheduler)
- ✅ Escalabilidade independente por container
- ✅ Resiliência (falha em task não afeta APIs)
- ✅ Logs separados por função
- ✅ Deploy atômico (sobe tudo junto)
- ✅ Zero downtime de cache (deploy seletivo)

### 8.1. RISK ENGINE - ANTIFRAUDE (IMPLEMENTADO):
- **Container Separado**: Risk Engine roda em container próprio (porta 8004)
- **Integração**: Django principal chama via HTTP (`RISKENGINE_URL`)
- **Intercepção**: Sempre ANTES de processar no gateway de pagamento (Pinbank)
- **Fail-Open**: Em caso de erro/timeout, PERMITIR transação (não bloquear operação)
- **Logs Detalhados**: Registrar dados, análise, decisão, score, tempo, regras acionadas
- **Timeout Configurado**: 5 segundos padrão (não adicionar latência excessiva)
- **Flag de Habilitação**: `ANTIFRAUDE_ENABLED=True/False` no .env
- **3D Secure**: Casca implementada, requer contratação de gateway real (Adyen, Cybersource, Braspag)
- **Configurações Necessárias**:
  ```bash
  RISKENGINE_URL=http://wallclub-riskengine:8004  # URL interna Docker
  ANTIFRAUDE_ENABLED=True
  ANTIFRAUDE_TIMEOUT=5
  ```

### 8.2. SISTEMA DE SEGURANÇA MULTI-PORTAL (FASE 4 - SEMANA 23 - COMPLETO 18/10/2025):
**Objetivo**: Detectar, monitorar e bloquear atividades suspeitas em tempo real

**Arquitetura**:
- **Risk Engine**: Análise e armazenamento (BloqueioSeguranca, AtividadeSuspeita)
- **Django WallClub**: Middleware de validação + Portal Admin
- **Celery**: 6 detectores automáticos executados periodicamente

**1. Risk Engine - Detectores Automáticos (Celery Tasks)**:
- `detectar_atividades_suspeitas()` - Executa a cada 5 minutos
- `bloquear_automatico_critico()` - Executa a cada 10 minutos
- **6 Detectores**:
  1. **Login Múltiplo** (Sev 4) - Mesmo CPF em 3+ IPs/10min
  2. **Tentativas Falhas** (Sev 5) - 5+ reprovações/5min → Bloqueio automático
  3. **IP Novo** (Sev 3) - CPF usando IP nunca visto
  4. **Horário Suspeito** (Sev 2) - Transações 02:00-05:00 AM
  5. **Velocidade Transação** (Sev 4) - 10+ transações/5min
  6. **Localização Anômala** - IP de país diferente <1h (preparado)

**2. APIs de Segurança (Risk Engine)**:
- `POST /api/antifraude/validate-login/` - Valida IP/CPF antes do login (fail-open)
- `GET /api/antifraude/suspicious/` - Lista atividades com filtros
- `POST /api/antifraude/block/` - Bloqueio manual IP/CPF
- `POST /api/antifraude/investigate/` - Investiga e toma ação
- `GET /api/antifraude/blocks/` - Lista bloqueios ativos/inativos

**3. Middleware de Validação (Django)**:
```python
# comum/middleware/security_validation.py
class SecurityValidationMiddleware:
    # Intercepta: /oauth/token/, /admin/login/, /lojista/login/, /vendas/login/
    # Valida IP + CPF com Risk Engine
    # Bloqueio: HTTP 403 se bloqueado
    # Fail-open: permite acesso em erro do Risk Engine
    # Cache: token OAuth em Redis
```

**4. Portal Admin - Telas de Segurança**:
- **Atividades Suspeitas** (`/admin/seguranca/atividades/`):
  - Dashboard com estatísticas
  - Filtros: status, tipo, portal, período
  - Modal de investigação com 5 ações
  - Paginação (25 itens)

- **Bloqueios** (`/admin/seguranca/bloqueios/`):
  - Criar bloqueio manual (IP ou CPF)
  - Histórico completo
  - Filtros: tipo, status, período

**Configurações .env**:
```bash
RISK_ENGINE_URL=http://wallclub-riskengine:8004
ANTIFRAUDE_ENABLED=True
ANTIFRAUDE_TIMEOUT=5
```

**Credenciais OAuth (AWS Secrets Manager - wall/prod/db)**:
- Separadas por contexto para melhor controle de acesso
- `RISK_ENGINE_ADMIN_CLIENT_ID/SECRET` - Portal Admin
- `RISK_ENGINE_POS_CLIENT_ID/SECRET` - POSP2 + Checkout
- `RISK_ENGINE_INTERNAL_CLIENT_ID/SECRET` - Serviços internos

**Princípio Fundamental**: Fail-open - Sistema NUNCA bloqueia por falha técnica

### 9. SISTEMA MULTI-PORTAL DE CONTROLE DE ACESSO (IMPLEMENTADO):
- **Arquitetura**: 3 tabelas (`portais_usuarios`, `portais_permissoes`, `portais_usuario_acesso`)
- **Múltiplos Portais**: Usuário pode ter acesso simultâneo a admin + lojista + recorrência + vendas
- **Níveis Granulares por Portal**:
  - **Admin**: `admin_total`, `admin_superusuario`, `admin_canal`
  - **Lojista**: `lojista_admin`, `grupo_economico`, `lojista`
- **Controle Hierárquico**: `portais_usuario_acesso` define entidades específicas
  - `entidade_tipo`: loja, grupo_economico, canal, regional, vendedor
  - `entidade_id`: ID específico da entidade
  - Exemplo: admin_canal com canal_id=6 vê apenas dados do canal ACLUB
- **Services Centralizados**:
  - `ControleAcessoService`: Verificação de permissões e filtros hierárquicos
  - `AutenticacaoService`: Login multi-portal com sessões isoladas
  - `UsuarioService`: CRUD com criação de permissões e vínculos automáticos
- **Decorators**: 
  - Portal Admin: `@require_admin_access`, `@require_funcionalidade('nome_funcao')`
  - Portal Vendas: `@requer_checkout_vendedor`, `@requer_permissao('recurso')` - controle granular de recursos
- **Logs**: Usar categoria `'portais.controle_acesso'` para auditoria de usuários

### 10. ARQUITETURA DE SERVICES (FASE 3 - CONCLUÍDA 17/10/2025):
- **Views são Controllers**: Views devem ser finas, apenas orquestração
- **Lógica de Negócio em Services**: Toda lógica complexa deve estar em services
- **NUNCA acessar models.objects diretamente nas views**: Sempre usar métodos do service

### 11. CHECKOUT E RECORRÊNCIAS (FASE 5 - CONCLUÍDA 21/10/2025):
- **Fluxos Separados**: `link_pagamento_web/` (pagamento único) vs `link_recorrencia_web/` (tokenização)
- **link_pagamento_web/**: Cliente paga AGORA → Processa transação → Tokeniza cartão (opcional)
- **link_recorrencia_web/**: Cliente cadastra cartão → Tokeniza via Pinbank → Ativa recorrência (sem pagamento)
- **RecorrenciaToken**: Validade 72h (vs 30min do CheckoutToken)
- **Email Diferenciado**: "Cadastre seu cartão para cobrança recorrente" (não "Pague agora")
- **Template Simplificado**: Sem escolha de parcelas, sem simulação - foco em tokenização
- **Callback Específico**: Atualiza `RecorrenciaAgendada` (status='ativo', calcula próxima_cobranca)
- **Campo descricao**: Obrigatório - usado nas notificações ao cliente sobre cobranças
- **Services Implementados**:
  - `RPRService`: Relatório Produção Receita (buscar_canais, buscar_transacoes)
  - `RecorrenciaService`: Gestão de recorrências (7 métodos)
  - `OfertaService`: Gestão de ofertas (listar, obter, disparar push)
  - `ParametrosService`: Configurações financeiras (9 métodos auxiliares)
  - `OTPService`: ✅ 2FA base (gerar, validar OTP - comum/seguranca/services_2fa.py)
  - `CheckoutSecurityService`: ✅ Segurança checkout (rate limiting, limite progressivo, Risk Engine)
- **Padrão de Nomeação de Métodos**:
  - `listar_*()`: Retorna lista completa
  - `buscar_*()`: Retorna lista filtrada
  - `obter_*()`: Retorna objeto único (ou None)
  - `criar_*()`: Cria novo registro
  - `atualizar_*()`: Atualiza registro existente
- **Resultado**: 25 queries diretas eliminadas, 22 métodos criados, 100% das views críticas refatoradas

### 11. SISTEMA 2FA CHECKOUT WEB (FASE 4 - SEMANA 21 - COMPLETO 18/10/2025):
**Estratégia**: Cliente autogerencia telefone + múltiplas camadas de segurança

**Princípios:**
- 🔴 Cliente cadastra próprio telefone (vendedor NUNCA tem acesso)
- 🔴 Telefone imutável após primeira transação aprovada
- 🔴 2FA SEMPRE (cartão novo E tokenizado)
- 🔴 Fail-open em APIs externas (WhatsApp, Risk Engine)

**Implementação Técnica:**

**1. Modelos (`checkout/link_pagamento_web/models_2fa.py`):**
```python
class CheckoutClienteTelefone:
    cpf = CharField(max_length=11, db_index=True)
    telefone = CharField(max_length=15, db_index=True)
    ativo = BooleanField(default=True)
    primeira_transacao_aprovada_em = DateTimeField(null=True)
    # Histórico completo de telefones por CPF

class CheckoutRateLimitControl:
    chave = CharField(max_length=100, unique=True)  # telefone/cpf/ip
    tentativas = IntegerField(default=0)
    ultima_tentativa = DateTimeField()
    bloqueado_ate = DateTimeField(null=True)
```

**2. Serviços (`checkout/link_pagamento_web/services_2fa.py`):**
- `CheckoutSecurityService.solicitar_otp()` - Gera OTP + envia WhatsApp
- `CheckoutSecurityService.validar_otp_e_processar()` - Valida + processa pagamento
- `CheckoutSecurityService.verificar_rate_limit()` - Controle tentativas
- `CheckoutSecurityService.validar_limite_progressivo()` - Primeiras transações
- `CheckoutSecurityService.verificar_multiplos_cartoes()` - Máx 3 cartões/90 dias

**3. APIs REST (`checkout/link_pagamento_web/views_2fa.py`):**
- `POST /api/v1/checkout/2fa/solicitar-otp/` - Etapa 1: Gerar + enviar OTP
- `POST /api/v1/checkout/2fa/validar-otp/` - Etapa 2: Validar + processar
- `GET /api/v1/checkout/2fa/limite-progressivo/<cpf>/<telefone>/` - Consulta limites

**4. Integração WhatsApp (Template CURRENCY):**
```python
# Formato Meta documentado
valor_currency = {
    "type": "currency",
    "currency": {
        "fallback_value": f"R${valor:.2f}",  # "R$10.00"
        "code": "BRL",
        "amount_1000": int(valor * 1000)  # 10.00 → 10000
    }
}
# Template: autorizar_transacao_cartao
# Parâmetros: [codigo_otp, valor_currency, ultimos_4_digitos]
```

**5. Frontend (`templates/checkout/checkout.html`):**
- Modal 3 etapas: Formulário → Loading → OTP → Sucesso/Erro
- Input OTP com 6 dígitos (auto-habilita botão)
- Tratamento erros com contador de tentativas

**Validações Implementadas:**
- ✅ Rate Limiting: 3 tent/telefone, 5 tent/cpf, 10 tent/ip (BD + Redis)
- ✅ OTP 6 dígitos com expiração 5 minutos
- ✅ Limite progressivo: 5 transações/30min para telefones novos
- ✅ Múltiplos cartões: máx 3 cartões diferentes/90 dias por telefone
- ✅ Device fingerprint blacklist
- ✅ Integração Risk Engine (fail-open)
- ✅ Collation uniforme: CPF em `utf8mb4_unicode_ci`

**Fluxo Completo:**
1. Vendedor cria link (CPF + valor + descrição)
2. Cliente acessa e preenche: telefone + cartão
3. Sistema envia OTP via WhatsApp (template formatado)
4. Cliente digita código
5. Sistema valida + processa Pinbank
6. Resultado: aprovação/erro com detalhes

**Status Atual:** ⏸️ Backend 100% funcional - Aguardando autorização Pinbank para produção

**Arquivos Principais:**
- `checkout/link_pagamento_web/models_2fa.py` (2 models)
- `checkout/link_pagamento_web/services_2fa.py` (CheckoutSecurityService)
- `checkout/link_pagamento_web/views_2fa.py` (3 endpoints)
- `checkout/link_pagamento_web/templates/checkout/checkout.html` (modal OTP)
- `comum/integracoes/whatsapp_service.py` (suporte CURRENCY)
- `portais/vendas/services.py` (busca clientes com telefone)

**Logs:** `checkout.2fa` (todas validações, bloqueios, tentativas)

### 12. DEVICE MANAGEMENT - TRUSTED DEVICES (FASE 4 - SEMANA 22 - COMPLETO 18/10/2025):
**Estratégia**: Controle de dispositivos confiáveis com limite por tipo de usuário

**Princípios:**
- 🔴 Cliente: Até 2 dispositivos ativos
- 🔴 Vendedor/Lojista: Até 2 dispositivos
- 🔴 Admin: Sem limite
- 🔴 Dispositivo confiável válido por 30 dias
- 🔴 Troca de senha: invalida TODOS os dispositivos
- 🔴 Device fingerprint do app NUNCA é sobrescrito pelo backend

**Implementação Técnica:**

**1. Service (`comum/seguranca/services_device.py`):**
```python
class DeviceManagementService:
    LIMITES_DISPOSITIVOS = {
        'cliente': 2,      # Até 2 dispositivos por cliente
        'vendedor': 2,
        'lojista': 2,
        'admin': None      # Sem limite
    }
    VALIDADE_DIAS = 30  # Dispositivo confiável por 30 dias
```

**2. Métodos Principais:**
- `calcular_fingerprint(dados_dispositivo)` - Hash MD5 único (User-Agent + Screen + Timezone)
- `registrar_dispositivo(user_id, tipo, dados, ip)` - Cadastro com verificação de limite
- `validar_dispositivo(user_id, tipo, fingerprint)` - Verifica confiança e validade
- `listar_dispositivos(user_id, tipo)` - Lista com status e dias restantes
- `revogar_dispositivo(dispositivo_id)` - Remove confiança individual
- `revogar_todos_dispositivos(user_id, tipo)` - Para troca de senha
- `notificar_novo_dispositivo()` - Push/SMS/Email (placeholder para Semana 23)

**3. Portal Admin (`portais/admin/views_dispositivos.py`):**
- `GET /admin/dispositivos/` - Lista todos com filtros
- `GET /admin/dispositivos/dashboard/` - Estatísticas (ativos, revogados, expirados)
- `GET /admin/dispositivos/usuario/` - Buscar por user_id + tipo
- `POST /admin/dispositivos/revogar/` - Revogar individual (admin)
- `POST /admin/dispositivos/revogar-todos/` - Revogar todos do usuário

**4. Menu Portal Admin:**
- Localização: Menu lateral após "Antifraude"
- Ícone: 📱 (mobile-alt)
- URL: `/admin/dispositivos/`

**Regras de Negócio:**
- ✅ Limite 2 dispositivos para clientes (3º bloqueado automaticamente)
- ✅ Validade 30 dias (após expirar: solicitar 2FA novamente)
- ✅ Cliente pode optar por "não confiar" (sempre pedir 2FA)
- ✅ Troca de senha: revogar_todos_dispositivos() automático
- ✅ Dispositivo expirado: flag `expirado=True`, necessário revalidar
- ✅ Device fingerprint fornecido pelo app é usado SEM modificação (31/10/2025)
- ✅ Verificação de dispositivo existente usa fingerprint COMPLETO (31/10/2025)

**Device Fingerprint (Cálculo):**
```python
# CRÍTICO: App calcula e envia fingerprint pronto
# Backend NUNCA recalcula ou modifica o fingerprint do app

# Componentes concatenados (lado do app):
- user_agent: Navigator.userAgent (normalizado sem versão)
- screen_resolution: "1920x1080"
- timezone: "America/Sao_Paulo"
- platform: "iOS" / "Android" / "Windows"
- language: "pt-BR"

# Hash MD5 final: 32 caracteres hexadecimais
# Backend aceita fingerprint do app SEM validação/recálculo
```

**Integração App Móvel:**
- Documentação completa: `docs/fase4/TELA_MEUS_DISPOSITIVOS_APP.md`
- Tela "Meus Dispositivos" em: Configurações > Segurança
- Cliente visualiza dispositivo único cadastrado
- Ações: Remover dispositivo, Revalidar (se expirado)
- Implementação: Equipe Mobile (consumir APIs Django)

**Fluxo Login App:**
1. App calcula fingerprint e envia no login
2. Backend verifica se dispositivo já existe (comparação de fingerprint COMPLETO)
3. Se novo + limite atingido (≥2): **BLOQUEAR** (mensagem: "Remova dispositivo atual")
4. Se novo + dentro do limite (<2): registrar + solicitar 2FA
5. Se existente + válido (<30 dias): login direto (bypass 2FA)
6. Se existente + expirado (>30 dias): solicitar 2FA + renovar validade

**Correções 31/10/2025:**
- ✅ Backend usa fingerprint do app SEM modificação
- ✅ Verificação compara fingerprint completo (antes: apenas 16 chars)
- ✅ Elimina duplicidade de dispositivos

**Models Reutilizados:**
- `DispositivoConfiavel` (já existe em `comum/seguranca/models.py`)
- Campos: user_id, tipo_usuario, device_fingerprint, nome_dispositivo, confiavel_ate, ativo

**Status Atual:** ✅ Backend 100% funcional - Aguardando implementação mobile

**Arquivos Principais:**
- `comum/seguranca/services_device.py` (DeviceManagementService)
- `comum/seguranca/models.py` (DispositivoConfiavel - Semana 20)
- `portais/admin/views_dispositivos.py` (5 endpoints)
- `portais/admin/urls.py` (rotas configuradas)

### 13. SISTEMA DE MENSAGENS - WHATSAPP + SMS (29/10/2025):
**Princípio**: Envio confiável de mensagens com fallback e templates corretos

**WhatsApp Business API (Meta):**
- **Templates por Categoria:**
  - `AUTHENTICATION` - Sempre entregue (OTP, 2FA) - Ex: `2fa_login_app`
  - `UTILITY` - Transacional, não requer opt-in - Ex: convites, alertas
  - `MARKETING` - Requer opt-in explícito do usuário
- **Status "accepted" ≠ entregue:** Meta aceita requisição mas pode não entregar
- **Causas de não entrega:**
  - Template categoria MARKETING sem opt-in do usuário
  - Template em análise (Pending) ou rejeitado
  - Qualidade baixa (denúncias, bloqueios)
  - Rate limit por número (muitos envios para mesmo destinatário)
- **Boas práticas:**
  - Usar UTILITY para convites/notificações funcionais
  - Não testar excessivamente no mesmo número (Meta bloqueia)
  - Verificar status/qualidade no Meta Business Manager
  - Logs sempre em DEBUG: payload enviado + response completa

**SMS (LocaPlataforma):**
- **Formato URL correto:** `/API_KEY/TELEFONE/MENSAGEM/SHORTCODE/ASSUNTO`
- **Encoding:** URL encode completo (`safe=''`) para mensagem e assunto
- **SHORTCODE:** Usar `SHORTCODE_PREMIUM` (não `SHORTCODE`)
- **Boas práticas:**
  - Assunto curto e simples (ex: "Convite WallClub")
  - Mensagem com URL deve ter encoding completo
  - Sempre logar URL construída para debug

**Templates no Banco (`templates_envio_msg`):**
```sql
id|canal_id|tipo    |id_template|mensagem           |parametros_esperados|idioma|
12|       1|WHATSAPP|baixar_app |msg_baixar_app     |[]                  |pt_BR |
13|       1|SMS     |baixar_app |Baixe o app...     |[]                  |pt_BR |
```
- Campo `mensagem` = nome do template no Meta (WhatsApp) ou texto (SMS)
- Cache de 1 hora: limpar Redis após alterar templates
- `MessagesTemplateService` busca por `canal_id + tipo + id_template`

**Revalidação de Celular (90 dias):**
- Campo `celular_validado_em` adicionado no model `Cliente`
- Atualizado automaticamente ao validar OTP 2FA com sucesso
- Verificação em `RevalidacaoCelularService.verificar_validade_celular()`
- Se NULL ou >90 dias: bloqueia login até revalidar via OTP
- Rate limit checado ANTES de exigir revalidação (evita travamento)

**Constraint Dispositivos Confiáveis:**
- **Problema:** UNIQUE(user_id, device_fingerprint, ativo) impedia múltiplos inativos
- **Solução:** Coluna virtual `unique_check` + índice UNIQUE condicional
- Permite histórico completo (múltiplos inativos) mas apenas 1 ativo
```sql
ALTER TABLE otp_dispositivo_confiavel
ADD COLUMN unique_check VARCHAR(100) AS (
    CASE WHEN ativo = 1 THEN CONCAT(user_id, '-', device_fingerprint) ELSE NULL END
) VIRTUAL;
ADD UNIQUE INDEX idx_unique_active_device (unique_check);
DROP INDEX unique_user_device_ativo;
```
- Usar `.update()` ao invés de `.save()` para revogar dispositivos

**Arquivos Principais:**
- `comum/integracoes/whatsapp_service.py` (WhatsAppService)
- `comum/integracoes/sms_service.py` (SMSService)
- `comum/integracoes/messages_template_service.py` (MessagesTemplateService)
- `apps/cliente/services_revalidacao_celular.py` (RevalidacaoCelularService)
- `apps/cliente/services_2fa_login.py` (verificação rate limit)
- `comum/seguranca/services_device.py` (revogar_dispositivo corrigido)

### 14. SISTEMA DE LOGS PADRONIZADO (28/10/2025):
**Princípio**: Logs com níveis apropriados para facilitar debug e monitoramento

**Níveis de Log Definidos:**
- **DEBUG**: Informações técnicas detalhadas (validações bem-sucedidas, fluxo normal, valores de variáveis)
- **INFO**: Operações importantes concluídas (criação, atualização, envio, renovação)
- **WARNING**: Situações anômalas mas não críticas (validações negadas, dados não encontrados, tentativas inválidas)
- **ERROR**: Falhas críticas de sistema (exceções, erros de conexão, falhas de processamento)

**Padrão de Uso:**
```python
# ✅ DEBUG: Validações bem-sucedidas, fluxo normal
registrar_log('comum.oauth', f"Token válido: {token.client.name}", nivel='DEBUG')
registrar_log('apps.cliente', f"IP capturado via {header}: {ip}", nivel='DEBUG')

# ✅ INFO: Operações concluídas com sucesso
registrar_log('comum.oauth', f"Token renovado: {token.client.name}", nivel='INFO')
registrar_log('comum.integracoes', "Email enviado com sucesso", nivel='INFO')

# ✅ WARNING: Validações negadas, dados não encontrados
registrar_log('comum.oauth', "Token expirado", nivel='WARNING')
registrar_log('comum.seguranca', "Rate limit atingido", nivel='WARNING')

# ✅ ERROR: Erros de sistema, exceções
registrar_log('comum.integracoes', f"Erro ao enviar email: {str(e)}", nivel='ERROR')
registrar_log('comum.oauth', "Erro no rate limiter", nivel='ERROR')
```

**Módulos Padronizados (28/10/2025):**

**1. comum/estr_organizacional/** ✅
- Erros em criação/atualização → ERROR
- Validações (campos obrigatórios) → WARNING
- Operações concluídas → INFO

**2. comum/integracoes/** ✅
- CPF inválido/não encontrado → WARNING
- Template não encontrado → WARNING
- Sucesso em envios → INFO
- Logs de depuração → DEBUG
- Erros de conexão → ERROR

**3. comum/middleware/** ✅
- Rate limit excedido → WARNING
- Requisição inválida → WARNING
- Sessão expirada → WARNING
- Possível sequestro de sessão → ERROR
- API Request (DEBUG mode) → INFO
- Erros de sistema → ERROR

**4. comum/oauth/** ✅
- Token válido → DEBUG
- Token expirado/não encontrado → WARNING
- Tentativa sem token → WARNING
- Token renovado/revogado → INFO
- Limpeza de tokens → INFO
- Erros críticos → ERROR

**5. comum/seguranca/** ✅
- Fingerprint calculado → DEBUG
- Dispositivo validado → DEBUG
- Validação CPF (cache) → DEBUG
- Dispositivo registrado/renovado → INFO
- OTP gerado/validado → INFO
- CPF bloqueado → WARNING
- Rate limit atingido → WARNING
- Erros de sistema → ERROR

**6. apps/cliente/** ✅
- Autenticação JWT (fluxo normal) → DEBUG
- IP capturado → DEBUG
- Senha trocada com sucesso → INFO
- Código 2FA gerado → INFO
- Tentativa senha incorreta → WARNING
- Erros de validação → WARNING
- Erros de sistema → ERROR

**Hierarquia de Logs em Produção:**
```
ERROR    → Sistema registra erros
WARNING  → Sistema registra warnings + erros
INFO     → Sistema registra info + warnings + erros
DEBUG    → Sistema registra TUDO (debug + info + warnings + erros)
```

**Boas Práticas:**
1. ✅ **Sempre especificar nível** - Não deixar registrar_log() sem parâmetro nivel
2. ✅ **Categoria consistente** - Usar 'comum.modulo' ou 'apps.modulo' (ex: 'comum.oauth', 'apps.cliente')
3. ✅ **Mensagens descritivas** - Incluir contexto relevante (IDs, valores, ações)
4. ✅ **DEBUG para fluxo normal** - Não poluir logs de produção com validações bem-sucedidas
5. ✅ **INFO para operações importantes** - Registrar conclusões de processos críticos
6. ✅ **WARNING para anomalias** - Situações que merecem atenção mas não impedem operação
7. ✅ **ERROR para falhas** - Exceções, erros de conexão, falhas críticas

**Status Atual:** ✅ 6 módulos principais padronizados (28/10/2025)
- `portais/admin/templates/portais/admin/base.html` (menu atualizado)
- `docs/fase4/TELA_MEUS_DISPOSITIVOS_APP.md` (especificação mobile)

**Logs:** `comum.seguranca.device` (registros, validações, revogações)

### 13. SIMPLIFICAÇÃO DE PORTAIS (24/10/2025):
**Princípio: Consolidar funcionalidades e reduzir código duplicado**

**Portal de Recorrência Removido:**
- ✅ Todas funcionalidades migradas para `portal_vendas`
- ✅ Pasta `portais/recorrencia/` deletada
- ✅ URL `/portal_recorrencia/` removida de `urls.py`
- ✅ Removido de `INSTALLED_APPS` no `settings/base.py`
- ✅ Cookie `wallclub_recorrencia_session` removido do middleware

**Correções de Sessão:**
- ✅ Redirect de sessão expirada corrigido: `/portal_admin/` (sem `/login/`)
- ✅ Dashboard vendas com autenticação obrigatória (`@requer_checkout_vendedor`)
- ✅ Timeout de sessão: 30 minutos (configurável via `PORTAL_SESSION_TIMEOUT_MINUTES`)
- ✅ Sessão renova a cada request (`SESSION_SAVE_EVERY_REQUEST = True`)

**Arquitetura Atual - 4 Portais Ativos:**
1. `/portal_admin/` - Administrativo (cookie: `wallclub_admin_session`)
2. `/portal_lojista/` - Lojista (cookie: `wallclub_lojista_session`)
3. `/portal_corporativo/` - Corporativo (cookie: `wallclub_corporativo_session`)
4. `/portal_vendas/` - Vendas + Recorrências (cookie: `wallclub_vendas_session`)

**Decorators Corrigidos:**
```python
# ❌ ANTES: Redirecionava para URL inexistente
return redirect(f'/portal_{portal}/login/')

# ✅ DEPOIS: Redireciona para raiz do portal
return redirect(f'/portal_{portal}/')
```

**Arquivos Modificados (24/10/2025):**
- `wallclub/urls.py` - Rota de recorrência removida
- `wallclub/settings/base.py` - App recorrencia removido
- `portais/controle_acesso/middleware.py` - Cookie mapping atualizado
- `portais/controle_acesso/decorators.py` - Redirect corrigido (3 ocorrências)
- `portais/vendas/views.py` - Dashboard com decorator de autenticação

**Benefícios:**
- ✅ Menos código para manter (-7 arquivos, -400 linhas)
- ✅ UX consistente (vendas spot e recorrência no mesmo portal)
- ✅ Zero duplicação de lógica de negócio
- ✅ Preparação para Fase 6 (quebra em containers)

### 14. SISTEMA DE AUTENTICAÇÃO JWT CUSTOMIZADO (28/10/2025):
**Princípio: Autenticação segura para apps mobile com JWT customizado independente do sistema administrativo**

**Arquitetura Implementada:**
- ✅ JWT customizado EXCLUSIVO para clientes (mobile/API)
- ✅ Totalmente independente do Django User/Session dos portais
- ✅ OAuth 2.0 para apps (client credentials)
- ✅ 2FA obrigatório para novos dispositivos
- ✅ Refresh tokens reutilizáveis (30 dias)
- ✅ Access tokens renováveis (1 dia)

**Fluxo Completo de Autenticação:**
```
1. Login → Credenciais válidas → auth_token (2 min)
2. Verificar dispositivo → Novo? → Solicitar 2FA
3. Validar 2FA → Registrar dispositivo (30 dias) → JWT final
4. JWT final → access_token (1 dia) + refresh_token (30 dias)
5. Refresh → Renovar access_token sem nova autenticação
```

**Endpoints Implementados (18 cenários testados):**

**FASE 1 - Cadastro (3 endpoints):**
- `POST /api/v1/cliente/cadastro/iniciar/` - Envia OTP via WhatsApp
- `POST /api/v1/cliente/cadastro/validar_otp/` - Valida código
- `POST /api/v1/cliente/cadastro/finalizar/` - Cria senha e completa cadastro

**FASE 2 - Login e Rate Limiting (5 cenários):**
- `POST /api/v1/cliente/login/` - Autenticação com senha
- Rate limiting: 5 tentativas/15min, 10/1h, 20/24h
- Bloqueio automático progressivo (1h, 24h)
- Contadores em `cliente_autenticacao` e `cliente_bloqueios`

**FASE 3 - Reset de Senha (3 endpoints):**
- `POST /api/v1/cliente/senha/solicitar_reset/` - Envia código OTP
- `POST /api/v1/cliente/senha/validar_codigo_reset/` - Valida e troca senha
- Histórico de senhas salvo em `cliente_senhas_historico`

**FASE 4 - 2FA e Dispositivos (5 endpoints):**
- `POST /api/v1/cliente/2fa/verificar_necessidade/` - Verifica se precisa 2FA
- `POST /api/v1/cliente/2fa/solicitar_codigo/` - Envia OTP 2FA
- `POST /api/v1/cliente/2fa/validar_codigo/` - Valida e gera JWT final
- `POST /api/v1/cliente/dispositivos/meus/` - Lista dispositivos confiáveis
- `POST /api/v1/cliente/dispositivos/revogar/` - Revoga dispositivo
- Limite: 2 dispositivos por cliente (30 dias de validade)

**FASE 5 - Refresh Token (2 testes):**
- `POST /api/v1/cliente/refresh/` - Renova access_token
- Refresh token preservado (não é recriado)
- Access tokens anteriores revogados automaticamente

**Tabelas Implementadas:**
```sql
-- Controle de autenticação e bloqueios
cliente_autenticacao        -- Tentativas, bloqueios, contadores
cliente_bloqueios           -- Histórico de bloqueios

-- Códigos OTP
otp_autenticacao            -- Códigos 2FA e cadastro (6 dígitos)

-- Dispositivos confiáveis
otp_dispositivo_confiavel   -- device_fingerprint, 30 dias validade

-- Tokens JWT
cliente_jwt_tokens          -- Auditoria completa de tokens
  ├─ token_type: 'access' ou 'refresh'
  ├─ token_hash: SHA256 do token
  ├─ is_active: Controle de revogação
  └─ expires_at: Expiração

-- Senhas
cliente_senhas_historico    -- Histórico de trocas de senha
```

**Segurança Implementada:**
- ✅ Rate limiting com bloqueio progressivo
- ✅ OTP via WhatsApp (códigos de 6 dígitos, 5 min validade)
- ✅ 2FA obrigatório para novos dispositivos
- ✅ Device fingerprinting para rastreamento
- ✅ Limite de 2 dispositivos por cliente
- ✅ Refresh tokens reutilizáveis (não descartáveis)
- ✅ Access tokens de curta duração (1 dia)
- ✅ Revogação automática de tokens antigos
- ✅ Auditoria completa com IP e user-agent
- ✅ Histórico de senhas (impede reutilização)

**Arquivos Principais:**
```
apps/cliente/
├── jwt_cliente.py                 -- Autenticação JWT customizada
├── models.py                      -- ClienteJWTToken, historico senhas
├── services_login_persistent.py   -- Rate limiting e bloqueios
├── services_2fa_login.py          -- 2FA e dispositivos
├── views_2fa_login.py             -- Endpoints 2FA
├── views_refresh_jwt.py           -- Refresh token
├── views_dispositivos.py          -- Gerenciamento dispositivos
└── views_senha.py                 -- Reset de senha

comum/seguranca/
├── models.py                      -- OTP, dispositivos confiáveis
└── services_device.py             -- Gerenciamento de dispositivos
```

**Correções Aplicadas (28/10/2025):**
```sql
-- 1. Adicionar token_type para diferenciar access/refresh
ALTER TABLE cliente_jwt_tokens 
ADD COLUMN token_type VARCHAR(20) NOT NULL DEFAULT 'access';
CREATE INDEX idx_cliente_jwt_tokens_token_type ON cliente_jwt_tokens(token_type);

-- 2. Permitir NULL em user_agent (refresh não tem request)
ALTER TABLE cliente_jwt_tokens 
MODIFY COLUMN user_agent TEXT NULL;
```

**Lógica de Refresh Token:**
- Login normal: Revoga TODOS os tokens anteriores (access + refresh)
- Refresh: Revoga apenas access tokens, preserva refresh token
- Refresh token NÃO é recriado (reutilizável por 30 dias)
- Novo access token gerado a cada refresh (1 dia de validade)

**Status de Testes:**
- ✅ 18 cenários testados e validados em produção
- ✅ Documentação completa em `docs/TESTE_CURL_USUARIO.md`
- ✅ Sistema 100% funcional (28/10/2025)

**Logs e Monitoramento:**
- `logs/apps.cliente.log` - Autenticação, 2FA, tokens
- `logs/comum.seguranca.log` - Dispositivos, OTP
- `logs/apps.oauth.log` - Tokens OAuth

### 14. PORTAL ADMIN - CORREÇÕES (18/10/2025):
- ✅ Cookies de sessão isolados por portal (Portal Vendas: `wallclub_vendas_session`)
- ✅ Validação tipos que exigem referência: `operador`, `lojista`, `admin_canal`, `grupo_economico`, `vendedor`
- ✅ Bloqueio acesso operador sem loja vinculada (`portais/vendas/decorators.py`)
- ✅ Mapeamento correto: `operador` → `entidade_tipo=loja` em `portais_usuario_acesso`

### 15. DISPOSITIVOS CONFIÁVEIS - CORREÇÕES CRÍTICAS (26/10/2025):
**Problema:** Sistema não criava novo registro ao reativar dispositivo revogado

**Correções Aplicadas:**

**1. Rate Limiter - cache.ttl() não existe no LocMemCache:**
```python
# ❌ ERRADO: Método não existe no backend padrão Django
ttl = cache.ttl(cache_key)
return False, 0, ttl if ttl > 0 else cls.LOGIN_BLOCK_DURATION

# ✅ CORRETO: Retornar timeout padrão configurado
return False, 0, cls.LOGIN_BLOCK_DURATION
```
- **Arquivo:** `comum/seguranca/rate_limiter_2fa.py` (linhas 40, 67, 166)
- **Motivo:** `cache.ttl()` é específico do `django-redis`, não existe no `LocMemCache`

**2. Feature Flag - Extrair cliente_id do JWT:**
```python
# ❌ ERRADO: Aceitar cliente_id no body (inseguro)
cliente_id = request.data.get('cliente_id')

# ✅ CORRETO: Extrair do JWT automaticamente
cliente_id = None
if hasattr(request, 'user') and hasattr(request.user, 'cliente_id'):
    cliente_id = request.user.cliente_id
```
- **Arquivo:** `apps/views.py` (endpoint `/api/v1/feature_flag/`)
- **Decorator:** Alterado de `@require_oauth_apps` para `@require_jwt_only`

**4. Revalidação de Celular (90 dias) - Usar auth_token em vez de JWT:**
```python
# ❌ ERRADO: Endpoints requerem JWT (cliente não consegue logar se celular expirado)
@require_jwt_only
def verificar_status_celular(request):
    cliente_id = request.user.cliente_id

# ✅ CORRETO: Usar auth_token (OAuth) - valida ANTES do login completo
@require_oauth_apps
def verificar_status_celular(request):
    auth_token = request.data.get('auth_token')
    payload = validate_auth_pending_token(auth_token)
    cliente_id = payload.get('cliente_id')
```
- **Arquivos:** `apps/cliente/views_revalidacao.py` (3 endpoints)
- **Endpoints:** `/celular/status/`, `/celular/solicitar_codigo/`, `/celular/validar_codigo/`
- **Razão:** Cliente com celular expirado não consegue JWT, então precisa validar com auth_token

**5. OTPService - Remover parâmetro 'contexto' inexistente:**
```python
# ❌ ERRADO: Parâmetro não existe na assinatura do método
OTPService.gerar_otp(
    user_id=cliente_id,
    tipo_usuario='cliente',
    telefone=cliente.celular,
    contexto='revalidacao_celular'  # Parâmetro inválido
)

# ✅ CORRETO: Usar apenas parâmetros válidos
OTPService.gerar_otp(
    user_id=cliente_id,
    tipo_usuario='cliente',
    telefone=cliente.celular,
    ip_solicitacao=request.META.get('REMOTE_ADDR')  # Opcional
)
```
- **Arquivo:** `apps/cliente/services_revalidacao_celular.py`
- **Verificação:** Checar chave de retorno `'success'` (não `'sucesso'`)

**5.1. WhatsAppService - Usar envia_whatsapp() padrão:**
```python
# ❌ ERRADO: Método envia_template() foi removido (duplicado)
WhatsAppService.envia_template(
    celular=telefone,
    template_name='2fa_login_app',
    parametros_body=[codigo],
    canal_id=canal_id
)

# ✅ CORRETO: Usar envia_whatsapp() padrão do projeto
WhatsAppService.envia_whatsapp(
    numero_telefone=telefone,
    canal_id=canal_id,
    nome_template='2fa_login_app',
    idioma_template='pt_BR',
    parametros_corpo=[codigo],      # Body: 1 parâmetro
    parametros_botao=[codigo]       # Button URL: 1 parâmetro
)
```
- **Template 2fa_login_app:** Requer 2 parâmetros (1 body + 1 button URL)
- **Consolidação:** Método `envia_template()` removido (28/10/2025) - era duplicado de `envia_whatsapp()`
- **Arquivo:** `comum/seguranca/services_2fa.py` - método `enviar_otp_whatsapp()`

---

## 19. PADRONIZAÇÃO DE NOMENCLATURA (REGRA CRÍTICA)

**PROBLEMA IDENTIFICADO (28/10/2025):**
Inconsistência causando bugs em validações OTP - código checava chaves inexistentes.

### 19.1. Padrão de Respostas

**API Endpoints (Externo - Cliente final):**
```python
# ✅ SEMPRE usar português nos endpoints externos
return Response({
    'sucesso': True,      # Português
    'mensagem': 'Operação realizada',
    'codigo': '123456'    # Campo de OTP sempre 'codigo'
}, status=status.HTTP_200_OK)
```

**Services Internos:**
```python
# ✅ SEMPRE usar inglês em services internos
def validar_otp(...):
    return {
        'success': True,    # Inglês
        'mensagem': 'Código válido'
    }
```

### 19.2. Campos de OTP Padronizados

**Campo de entrada OTP:**
```python
# ✅ CORRETO: Sempre 'codigo' (sem underline)
codigo = request.data.get('codigo')

# ❌ ERRADO: Variações inconsistentes
codigo_2fa = request.data.get('codigo_2fa')      # NÃO USAR
codigo_otp = request.data.get('codigo_otp')      # NÃO USAR
code = request.data.get('code')                  # NÃO USAR
```

### 19.3. Validação de Services

**Checando retorno de OTPService:**
```python
# ✅ CORRETO: Service retorna 'success' (inglês)
validacao = OTPService.validar_otp(user_id=1, tipo_usuario='cliente', codigo=codigo)
if not validacao['success']:  # Chave em inglês
    return Response({'sucesso': False, 'mensagem': validacao['mensagem']})

# ❌ ERRADO: Checando chave em português
if not validacao['sucesso']:  # Service não retorna 'sucesso'
    # BUG: Chave não existe, sempre será False
```

### 19.4. Tabela de Referência

| Contexto | Chave Status | Campo OTP | Idioma |
|----------|-------------|-----------|--------|
| API Response | `sucesso` | `codigo` | Português |
| Services | `success` | `codigo` | Inglês/PT |
| Logs | - | - | Português |
| Exceptions | - | - | Inglês |

### 19.5. Endpoints Corrigidos (28/10/2025)

**Arquivo:** `apps/cliente/views_senha.py`

1. **POST /senha/criar_definitiva/**
   - `codigo_2fa` → `codigo` ✅
   - `validacao['sucesso']` → `validacao['success']` ✅

2. **POST /senha/trocar/**
   - `codigo_2fa` → `codigo` ✅
   - `validacao['sucesso']` → `validacao['success']` ✅

**Endpoints Já Padronizados:**
- `/cadastro/validar_otp/` ✅ usa `codigo`
- `/senha/reset/validar/` ✅ usa `codigo`
- `/celular/validar_codigo/` ✅ usa `codigo`
- `/2fa/validar_codigo/` ✅ usa `codigo`

---

**6. Sistema 2FA - Detectar celular expirado automaticamente:**
```python
# ✅ Integrado em verificar_necessidade_2fa()
from apps.cliente.services_revalidacao_celular import RevalidacaoCelularService
validade_celular = RevalidacaoCelularService.verificar_validade_celular(cliente_id)

if validade_celular['precisa_revalidar']:
    return {
        'necessario': True,
        'motivo': 'celular_expirado',
        'dispositivo_confiavel': confiavel,
        'mensagem': 'Seu celular precisa ser revalidado para continuar usando o app',
        'dias_expirado': abs(validade_celular['dias_restantes'])
    }
```
- **Arquivo:** `apps/cliente/services_2fa_login.py` (linha 106-120)
- **Template WhatsApp:** Unificado - usa `'2fa_login_app'` para todos códigos de segurança

**3. Device Management - Criar novo registro ao invés de UPDATE:**
```python
# ❌ ERRADO: Reativar dispositivo revogado com UPDATE
dispositivo_revogado.ativo = True
dispositivo_revogado.revogado_em = None
dispositivo_revogado.save()  # Perde histórico

# ✅ CORRETO: Criar NOVO registro para manter auditoria
# Se dispositivo não existe OU foi revogado → INSERT novo registro
# Histórico completo preservado
```
- **Arquivo:** `comum/seguranca/services_device.py` (linhas 94-139)
- **Motivo:** Auditoria completa - cada revogação/reativação = novo registro

**4. Constraint UNIQUE - device_fingerprint:**
```sql
-- ❌ PROBLEMA: Constraint UNIQUE impede criar novo registro
UNIQUE KEY `device_fingerprint` (`device_fingerprint`)

-- ✅ SOLUÇÃO: UNIQUE composto (permite histórico)
ALTER TABLE otp_dispositivo_confiavel 
DROP INDEX device_fingerprint,
ADD UNIQUE KEY `unique_user_device_ativo` (`user_id`, `device_fingerprint`, `ativo`);
```
- **Tabela:** `otp_dispositivo_confiavel`
- **Motivo:** Garante apenas 1 registro ativo por user+device, permite histórico completo

**5. Limites de Dispositivos:**
- **Cliente:** Até **2 dispositivos ATIVOS** (não 1)
- **Vendedor/Lojista:** 2 dispositivos
- **Admin:** Sem limite
- **Validade:** 30 dias

**Arquivos Corrigidos:**
- `comum/seguranca/rate_limiter_2fa.py` - Método ttl removido
- `apps/views.py` - Feature flag com JWT
- `comum/seguranca/services_device.py` - Lógica de criação corrigida
- `scripts/sql/fix_device_constraint.sql` - Constraint UNIQUE composta

## PADRÕES DE CÓDIGO

### 7. NOMENCLATURA OBRIGATÓRIA:
- **Variáveis**: snake_case (ex: `usuario_id`, `data_inicio`)
- **Funções**: snake_case (ex: `buscar_usuario`, `calcular_desconto`)
- **Classes**: PascalCase (ex: `UsuarioService`, `PagamentoEfetuado`)
- **Constantes**: UPPER_SNAKE_CASE (ex: `TIPO_CHOICES`, `STATUS_PENDENTE`)
- **Arquivos**: snake_case.py (ex: `views_pagamentos.py`, `services_usuario.py`)
- **Templates**: snake_case.html (ex: `usuario_form.html`, `pagamentos_list.html`)

### 8. ESTRUTURA DE ARQUIVOS:
- **Views**: Separar por domínio (`views_pagamentos.py`, `views_usuarios.py`)
- **Services**: Um service por modelo (`services_usuario.py`, `services_pagamento.py`)
- **Templates**: Agrupar por funcionalidade em subpastas
- **Utilitários**: Centralizar em `comum/utilitarios/`

### 9. PADRÕES DE CÓDIGO:
- **Imports**: Sempre no topo, agrupados (stdlib, django, terceiros, locais)
- **Docstrings**: Obrigatório em classes e funções públicas
- **Comentários**: Explicar "por que", não "o que"
- **Validação**: Sempre validar entrada de dados
- **Logs Customizados**: **OBRIGATÓRIO** usar `registrar_log(processo, mensagem, nivel='INFO')` do `comum.utilitarios.log_control`
- **Nível ERROR**: **OBRIGATÓRIO** usar `nivel='ERROR'` em todos os blocos `except` (captura de erros)
- **Processo de Log**: Usar nome do módulo (ex: `portais.admin`, `sistema_bancario`, `autenticacao`)
- **Controle Dinâmico**: Logs podem ser ligados/desligados via banco sem restart da aplicação

## PADRÕES DE LAYOUT/TEMPLATES

### 10. ESTRUTURA HTML OBRIGATÓRIA:

**Template Base Padrão:**
```html
{% extends "portais/admin/base.html" %}
{% load formatacao_tags %}
{% load controle_acesso_tags %}

{% block title %}Título Específico{% endblock %}

{% block navbar_actions %}
<!-- Botões de navegação (voltar, etc.) -->
{% endblock %}

{% block extra_css %}
<!-- CSS específico da página -->
{% endblock %}

{% block content %}
<!-- Page Header Obrigatório -->
<div class="page-header-compact">
    <div class="d-flex align-items-center">
        <i class="fas fa-icon me-2" style="color: var(--primary-color);"></i>
        <h1 class="mb-0">Título da Página</h1>
    </div>
</div>

<!-- Mensagens do Sistema -->
{% if messages %}
    {% for message in messages %}
        <div class="alert alert-{{ message.tags }} alert-dismissible fade show" role="alert">
            {{ message }}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        </div>
    {% endfor %}
{% endif %}

<!-- Conteúdo Principal -->
<div class="container">
    <!-- Botões com controle de acesso -->
    {% if request|tem_acesso:'funcionalidade_create' %}
    <button class="btn btn-success">Criar</button>
    {% endif %}
    
    <!-- Conteúdo específico aqui -->
</div>
{% endblock %}

{% block extra_js %}
<script src="{% static 'js/nome_template.js' %}"></script>
{% endblock %}
```

### 11. COMPONENTES REUTILIZÁVEIS OBRIGATÓRIOS:

**Estruturas Padronizadas por Tipo:**

**A) Páginas de Listagem:**
- `page-header-compact` com ícone e título
- `navbar_actions` para botão voltar
- `container` (não `container-fluid`) para conteúdo
- `table-responsive` com `data-table` class
- Paginação padrão abaixo da tabela
- Total de registros centralizado
- **Controle de Acesso**: Botões condicionais com `{% if request|tem_acesso:'funcionalidade' %}`

**B) Páginas de Formulário:**
- `page-header-compact` com breadcrumb
- `card` structure para formulários
- Botões padronizados (`btn-success`, `btn-secondary`)
- Validação client-side via JavaScript separado

**C) Componentes Obrigatórios:**
- **Breadcrumb**: Navegação hierárquica
- **Mensagens**: Sistema de alerts Bootstrap
- **Modais**: Confirmação de ações destrutivas
- **Botão Voltar**: Sempre em `navbar_actions`

### 12. CLASSES CSS PADRONIZADAS:

**Estrutura de Layout:**
- **Container Principal**: `container` (não `container-fluid`)
- **Page Header**: `page-header-compact`
- **Tabelas**: `table-responsive` + `data-table`
- **Cards**: `card`, `card-header`, `card-body`

**Botões Padronizados:**
- **Primário**: `btn btn-success btn-colorido`
- **Secundário**: `btn btn-secondary btn-colorido`
- **Perigo**: `btn btn-danger btn-colorido`
- **Info**: `btn btn-info btn-colorido`
- **Voltar**: `btn btn-outline-light btn-sm` (navbar)

**Formulários:**
- **Inputs**: `form-control`
- **Labels**: `form-label`
- **Grupos**: `form-group`
- **Validação**: `form-text text-muted`

## PADRÕES DE VARIÁVEIS

### 13. TIPOS DE DADOS POR CONTEXTO:
- **IDs**: `PositiveIntegerField` ou `BigAutoField`
- **Valores Monetários**: `DecimalField(max_digits=10, decimal_places=2)`
- **Percentuais**: `DecimalField(max_digits=12, decimal_places=10)` (10 casas decimais para precisão financeira)
- **Dias/Prazos**: `IntegerField` (para campos que representam quantidade de dias)
- **Datas**: `DateTimeField` (sempre naive com datetime.now())
- **Status**: `CharField` com `choices`
- **Textos**: `CharField` (até 255) ou `TextField` (maior)

**IMPORTANTE - Parâmetros Financeiros:**
- Campos percentuais (MDR, taxas, descontos): `DECIMAL(12,10)` no banco
- Campos de prazo/dias: `INT` no banco
- Sempre usar `Decimal` com `ROUND_HALF_UP` para cálculos
- **OBRIGATÓRIO:** `from decimal import Decimal, ROUND_HALF_UP` quando usar `quantize()`
- NUNCA usar `float()` para valores monetários ou percentuais
- NUNCA aplicar `abs()` diretamente em strings - converter para `Decimal` primeiro

### 14. FORMATAÇÃO DE DADOS:
- **Monetário**: Usar `{% moeda %}` template tag
- **Percentual**: Usar `{% percentual %}` template tag
- **Datas**: Formato brasileiro `dd/mm/yyyy HH:MM`
- **Range de datas**: Data início sempre 00:00:00, data fim sempre 23:59:59
- **Input**: `type="text"` para valores monetários
- **Validação**: Aceitar vírgula e ponto, converter para ponto

## ANTI-DUPLICAÇÃO

### 15. UTILITÁRIOS CENTRALIZADOS:
- **Formatação**: `comum/utilitarios/formatacao.py`
- **Validação**: `comum/utilitarios/validacao.py`
- **Autenticação**: `comum/autenticacao/decorators.py`
- **Paginação**: `comum/utilitarios/paginacao.py`

### 15.1. DECORATORS DE TRATAMENTO DE ERROS (API):
**Localização**: `comum/decorators/api_decorators.py`

**Usar APENAS em views Django puras (não DRF):**
- `@handle_api_errors` - Captura JSONDecodeError (400) e Exception (500) com log automático
- `@validate_required_params(*params)` - Valida parâmetros obrigatórios no body (400 se faltando)

**COMPATIBILIDADE CRÍTICA:**
- ✅ **Usar em**: Views com `JsonResponse` (POSP2, Checkout, endpoints Django puros)
- ❌ **NÃO usar em**: Views DRF com `@api_view` e `Response` (apps, ofertas, transações)
- **Motivo**: Incompatibilidade entre `JsonResponse` (Django) e `Response` (DRF)

**Ordem dos Decorators:**
```python
@csrf_exempt              # 1º - Django
@require_http_methods     # 2º - Django  
@require_oauth_*          # 3º - OAuth
@handle_api_errors        # 4º - Tratamento erros
@validate_required_params # 5º - Validação params
def minha_view(request):
    pass
```

**Benefícios:**
- Elimina try/except repetitivo
- Validação consistente de parâmetros
- Logs automáticos de exceções
- Mensagens de erro padronizadas

**Endpoints Candidatos:**
- POSP2: `validar_senha_e_saldo`, `solicitar_autorizacao_saldo`, `verificar_autorizacao`, `simula_parcelas`, `trdata`
- Checkout Link: `gerar_token`, `simular_parcelas`, `processar_pagamento`
- Portais: Endpoints AJAX que retornam JSON (avaliar caso a caso)

### 16. SERVICES OBRIGATÓRIOS:
- **NUNCA** manipular models diretamente nas views
- **SEMPRE** criar service para lógica de negócio
- **SEMPRE** usar services para operações CRUD financeiras

### 17. SISTEMA DE CONTROLE DE ACESSO DOS PORTAIS:

#### 17.1. ARQUITETURA DE 2 TABELAS:

**1. `portais_permissoes` - Define O QUE o usuário pode acessar:**
```sql
CREATE TABLE portais_permissoes (
    id BIGINT PRIMARY KEY,
    usuario_id BIGINT,
    portal ENUM('admin', 'lojista', 'recorrencia', 'vendas'),
    nivel_acesso VARCHAR(50),  -- Nível granular (ex: admin_total, admin_superusuario)
    recursos_permitidos JSON
);
```

**2. `portais_usuario_acesso` - Define ONDE o usuário tem acesso:**
```sql
CREATE TABLE portais_usuario_acesso (
    id BIGINT PRIMARY KEY,
    usuario_id BIGINT,
    portal ENUM('admin', 'lojista', 'recorrencia', 'vendas'),  -- NOVO: Permite lojas diferentes por portal
    entidade_tipo ENUM('loja', 'grupo_economico', 'canal', 'admin_canal', 'admin_loja'),
    entidade_id BIGINT,
    ativo BOOLEAN,
    UNIQUE (usuario_id, portal, entidade_tipo, entidade_id)  -- NOVO: Constraint com portal
);
```

#### 17.2. NÍVEIS GRANULARES POR PORTAL:

**Portal Admin (`NIVEIS_ADMIN`):**
- `admin_total`: Acesso completo sem filtros (inclui parâmetros)
- `admin_superusuario`: Acesso quase total (sem parâmetros)
- `admin_canal`: Admin com filtro por canal
- `leitura_canal`: Apenas leitura com filtro por canal

**Portal Lojista (`NIVEIS_LOJISTA`):**
- `admin_lojista`: Acesso completo lojista (todas as lojas)
- `grupo_economico`: Filtro por grupo econômico
- `lojista`: Filtro por loja específica

**Portal Recorrência:**
- `operador`: Operador de recorrência (vinculado a loja)

**Portal Vendas:**
- `operador`: Operador de vendas (vinculado a loja)

#### 17.3. SEÇÕES PERMITIDAS POR NÍVEL:

```python
SECOES_POR_NIVEL = {
    'admin_total': ['dashboard', 'usuarios', 'transacoes', 'parametros', 
                    'relatorios', 'hierarquia', 'pagamentos', 'gestao_admin', 
                    'terminais', 'rpr'],
    'admin_superusuario': ['dashboard', 'usuarios', 'transacoes', 'relatorios',
                           'hierarquia', 'gestao_admin', 'terminais', 'rpr'],
    'admin_canal': ['dashboard', 'transacoes', 'relatorios', 'hierarquia',
                    'terminais', 'rpr', 'usuarios_canal'],
}
```

#### 17.4. DECORATORS E VALIDAÇÃO:

**1. `@require_admin_access` - Validação genérica:**
```python
@require_admin_access
def dashboard(request):
    # Garante que usuário tem ALGUMA permissão no portal admin
    pass
```

**2. `@require_secao_permitida('secao')` - Validação granular:**
```python
@require_secao_permitida('gestao_admin')
def base_transacoes_gestao(request):
    # Valida se seção está em SECOES_POR_NIVEL[nivel_usuario]
    pass
```

**Fluxo de validação:**
1. Busca permissão: `PortalPermissao.objects.get(usuario=usuario, portal='admin')`
2. Obtém nível: `nivel_acesso = 'admin_superusuario'`
3. Busca seções: `SECOES_POR_NIVEL.get('admin_superusuario', [])`
4. Valida: `'gestao_admin' in secoes_permitidas`

#### 17.5. TEMPLATE TAGS:

**1. `{% tem_secao_permitida 'secao' as var %}` - Controle de menu:**
```django
{% tem_secao_permitida 'gestao_admin' as pode_gestao_admin %}
{% if pode_gestao_admin %}
    <a href="...">Gestão Admin</a>
{% endif %}
```

**2. `{% nivel_usuario %}` - Obtém nível do usuário:**
```django
{% nivel_usuario as nivel %}
{{ nivel }}  <!-- admin_superusuario -->
```

#### 17.6. CRIAÇÃO DE USUÁRIOS - LÓGICA:

**Exemplo: Usuário com múltiplos portais:**
```python
acessos_para_criar = [
    {
        'portal': 'admin',
        'tipo_usuario': None,  # admin_total/superusuario não cria acesso
        'referencia_id': '',
        'nivel_granular': 'admin_superusuario'
    },
    {
        'portal': 'lojista',
        'tipo_usuario': 'admin_canal',
        'referencia_id': '6',  # Canal ID
        'nivel_granular': 'admin_canal'
    },
    {
        'portal': 'recorrencia',
        'tipo_usuario': 'loja',
        'referencia_id': '26',  # Loja A
        'nivel_granular': 'operador'
    },
    {
        'portal': 'vendas',
        'tipo_usuario': 'loja',
        'referencia_id': '30',  # Loja B (diferente!)
        'nivel_granular': 'operador'
    }
]

# Cria em portais_permissoes:
PortalPermissao.objects.create(
    usuario=usuario,
    portal='admin',
    nivel_acesso='admin_superusuario'
)

# Cria em portais_usuario_acesso (somente se tipo_usuario != None):
PortalUsuarioAcesso.objects.get_or_create(
    usuario=usuario,
    portal='recorrencia',  # Campo PORTAL permite lojas diferentes
    entidade_tipo='loja',
    entidade_id=26
)
```

#### 17.7. REGRAS CRÍTICAS:

1. **Admin Total e Super Usuário NÃO criam registro em `portais_usuario_acesso`**
   - Razão: Têm acesso global, sem filtro de entidade

2. **Campo `portal` em `portais_usuario_acesso` é OBRIGATÓRIO**
   - Permite: Recorrência → Loja A, Vendas → Loja B
   - Sem ele: Constraint `UNIQUE(usuario_id, entidade_tipo, entidade_id)` impede

3. **Delete + Insert ao editar usuário**
   - Apaga todas permissões/acessos antigos
   - Recria do zero
   - Garante consistência, mas perde histórico

4. **Validação em 2 camadas:**
   - Decorator: Bloqueia acesso via URL direta
   - Template tag: Esconde links no menu
   - Ambos devem usar mesma lógica (`ControleAcessoService`)

#### 17.8. ROTAS E NAVEGAÇÃO:

**Portal Admin:**
- Rota raiz (`/portal_admin/`) → Tela de login
- Dashboard em `/portal_admin/home/` (protegido)
- Se já autenticado na raiz → Redireciona para `/home/`
- Redirects hardcoded substituídos por named URLs (`portais_admin:dashboard`)

**Portal Lojista:**
- Rota raiz (`/portal_lojista/`) → Tela de login
- Comportamento idêntico aos dois portais

#### 17.9. FILTROS DE LISTAGEM POR NÍVEL:

**Usuários (`/portal_admin/usuarios/`):**
```python
if nivel_usuario == 'admin_canal':
    # Filtra apenas usuários do mesmo canal
    usuarios = PortalUsuario.objects.filter(id__in=usuarios_com_acesso)
elif nivel_usuario == 'admin_superusuario':
    # Filtra usuários SEM acesso ao portal admin
    usuarios = PortalUsuario.objects.exclude(id__in=usuarios_com_admin)
else:
    # Admin total vê todos
    usuarios = PortalUsuario.objects.all()
```

**Regra Crítica:**
- `admin_superusuario` **NÃO pode** visualizar nem gerenciar usuários com permissão no portal admin
- `admin_canal` **SÓ visualiza** usuários vinculados ao seu canal
- `admin_total` visualiza todos os usuários sem restrição

#### 17.10. DEBUGGING:

**Logs de desenvolvimento removidos:**
- ❌ Logs debug `DECORATOR_SECAO`, `TEM_SECAO_PERMITIDA`, `CANAL_DEBUG` foram removidos
- ✅ Mantidos apenas logs de operações críticas (erro, auditoria)
- Sistema mais limpo e performático em produção

**Queries de diagnóstico:**
```sql
-- Ver permissões do usuário
SELECT * FROM portais_permissoes WHERE usuario_id = X;

-- Ver acessos do usuário
SELECT * FROM portais_usuario_acesso WHERE usuario_id = X;

-- Ver níveis disponíveis
SELECT DISTINCT nivel_acesso FROM portais_permissoes;
```
- Services devem ter validação e logs customizados (`registrar_log`)
- **Separação por responsabilidade**: Criar services específicos quando lógica cresce (ex: `services_notificacoes.py`, `services_conta_digital.py`, `services_ajustes_manuais.py`)
- **Exemplos**: 
  - `PagamentoService` - operações bancárias e auditoria
  - `OfertaService` - CRUD ofertas, disparo push, segmentação customizada, grupos de segmentação
  - `CalculadoraDesconto` - cálculos financeiros validados vs PHP
  - `NotificationService` - push Firebase/APN com templates dinâmicos e fallback automático (produção → sandbox)
  - `NotificacaoService` - listar e marcar notificações como lidas (apps/cliente/services_notificacoes.py)
  - `APNService` - certificado híbrido (Sandbox & Production), tenta produção primeiro, se BadDeviceToken tenta sandbox
  - `CashbackService` - concessão de cashback com retenção automática (30 dias hardcoded)
  - `ClienteAuthService` - autenticação, cadastro, reset senha, perfil (apps/cliente/services.py)
  - `AjustesManuaisService` - ajustes e correções de dados (pinbank/cargas_pinbank/services_ajustes_manuais.py)
  - `ContaDigitalService` - gestão de conta digital (saldo, cashback, movimentações)

### 16.1. CONTROLE DE ACESSO CENTRALIZADO (OPÇÃO 2):
- **Estrutura**: Sistema baseado apenas em permissões (sem campo `tipo_usuario`)
- **Models**: `PortalUsuario`, `PortalPermissao`, `PortalUsuarioAcesso`
- **Tabelas**: Usa tabelas existentes (`portais_usuarios`, `portais_permissoes`, `portais_usuario_acesso`)
- **Decorator Views**: `@require_funcionalidade('nome_funcionalidade', portal='admin', nivel_minimo='leitura')`
- **Service**: `ControleAcessoService` para verificar permissões
- **Vínculos**: Sistema `entidade_tipo`/`entidade_id` (loja, canal, regional, grupo_economico, vendedor)
- **Permissões Granulares**: Campo JSON `recursos_permitidos` para controle específico por funcionalidade
- **Flexibilidade Máxima**: Sem tipos fixos, controle total via permissões
- **Localização**: Sistema centralizado em `portais/controle_acesso/`

### 16.2. GESTÃO DE USUÁRIOS SIMPLIFICADA:
- **Formulário**: Dropdown único para seleção de tipo (admin_canal, regional_leitura, vendedor_leitura, lojista, grupo_economico)
- **Portal Automático**: Sistema determina portal (admin/lojista) baseado no tipo selecionado
- **Permissões Automáticas**: Criação automática de permissões com nível "admin" padrão
- **Campo Referência**: Dinâmico baseado no tipo selecionado (canal, regional, vendedor, loja, grupo_economico)
- **Checkboxes Removidos**: Não há mais seleção manual de portais ou status ativo
- **Lógica Simplificada**: Uma seleção → portal determinado → permissões criadas → referência vinculada

### 17. TEMPLATES BASE E VALIDAÇÃO:

**Herança Obrigatória:**
- Usar herança de templates obrigatoriamente
- Componentes repetidos devem virar includes
- **JavaScript**: Um arquivo JS separado por template (ex: `usuario_form.js`, `pagamentos_list.js`)
- **Carregamento otimizado**: Apenas JS necessário por página via `{% block extra_js %}`

**Validação de Estrutura:**
- **Container**: Sempre usar `<div class="container">` para conteúdo principal
- **Page Header**: Obrigatório `page-header-compact` em todas as páginas
- **Navegação**: Botão voltar sempre em `{% block navbar_actions %}`
- **Mensagens**: Sistema de alerts sempre após page-header
- **Tabelas**: Sempre dentro de `table-responsive` com `data-table`

**Checklist de Layout:**
- [ ] Page header com ícone e título?
- [ ] Botão voltar em navbar_actions?
- [ ] Container principal definido?
- [ ] Mensagens do sistema incluídas?
- [ ] JavaScript em arquivo separado?

## COMPORTAMENTO DE DESENVOLVIMENTO

### 18. CONFIRMAÇÃO OBRIGATÓRIA:
- SEMPRE perguntar antes de alterar código existente
- SEMPRE confirmar escopo antes de implementar
- SEMPRE validar requisitos antes de começar
- NUNCA assumir o que o usuário quer

### 19. CHECKLIST PRÉ-IMPLEMENTAÇÃO:
- [ ] Entendi exatamente o que foi solicitado?
- [ ] Preciso de mais informações do usuário?
- [ ] Vou seguir os padrões estabelecidos?
- [ ] Estou evitando duplicação de código?
- [ ] Vou usar os utilitários existentes?

## PROCESSO ITERATIVO DE EVOLUÇÃO

### 20. IDENTIFICAÇÃO DE PROBLEMAS RECORRENTES:

**Problemas de Layout Identificados:**
- **Containers inconsistentes**: Mistura de `container` e `container-fluid`
- **Navegação despadronizada**: Botões inline vs `navbar_actions`
- **Headers variados**: Falta de `page-header-compact` padrão
- **Posicionamento incorreto**: Elementos fora do container principal

**Padrões Documentados:**
- Durante desenvolvimento, sempre documentar padrões que se repetem
- Quando encontrar código duplicado ou inconsistente, propor padronização
- Capturar decisões arquiteturais para futura referência
- Registrar soluções que funcionaram bem para reutilização

### 21. ATUALIZAÇÃO DAS DIRETRIZES:
- Quando identificar novo padrão, perguntar: "Isso deveria virar diretriz?"
- Propor adição de nova regra com justificativa técnica
- Sempre validar com usuário antes de incluir nova diretriz
- Manter histórico de mudanças para rastreabilidade

### 22. APLICAÇÃO RETROATIVA:
- Quando nova diretriz for aprovada, identificar código existente que precisa ajuste
- Propor refatoração gradual, não mudanças em massa
- Priorizar áreas críticas ou com maior impacto
- Sempre confirmar escopo de refatoração com usuário

### 23. FEEDBACK CONTÍNUO:
- Questionar efetividade das diretrizes durante uso
- Propor simplificações quando regras são muito complexas
- Sugerir remoção de diretrizes que não agregam valor
- Manter diretrizes vivas e relevantes ao projeto atual

## PADRÕES EMERGENTES E ESPECIALIZADOS

### 24. CONTROLE DE ACESSO GRANULAR:
- **Níveis Hierárquicos**: Usar nomenclatura padronizada (`admin_total`, `admin_canal`, `leitura_canal`, `leitura_regional`, `leitura_vendedor`)
- **Múltiplos Acessos**: Usuário pode ter acesso simultâneo a múltiplas entidades (canal + regional + vendedor)
- **Decorators Específicos**: `@require_secao_permitida('nome_secao')` para controle por seção, `@require_acesso_padronizado()` para controle geral
- **Template Tags Obrigatórias**: `{% if request|tem_acesso:'funcionalidade' %}`, `{% tem_secao_permitida 'secao' %}`, `{{ request.user|nivel_usuario }}`
- **Filtros Automáticos**: Implementar filtros por canal/entidade em todas as queries de dados sensíveis
- **Mapeamento de Constantes**: Converter strings para constantes usando Service centralizado

### 25. FORMULÁRIOS COMPLEXOS E REFERÊNCIAS DINÂMICAS:
- **Campos Dinâmicos**: Usar JavaScript para carregar campos baseado em seleção (`carregarCampoReferencia()`)
- **Seleção Múltipla**: Implementar interface para múltiplos acessos com checkboxes organizados por categoria
- **Validação Global**: Tratamento de exceções em fluxos complexos com `try/except` abrangente
- **AJAX Endpoints**: Criar endpoints específicos para carregamento dinâmico (`ajax_lojas`, `ajax_grupos_economicos`)
- **Limpeza de Campos**: Implementar limpeza automática de campos dependentes quando seleção pai muda
- **Logs Detalhados**: Registrar operações críticas de criação/edição com `registrar_log()`

### 26. NOMENCLATURA HIERÁRQUICA DE LOGS:
- **REGRA FUNDAMENTAL**: Usar caminho do módulo do arquivo como processo
  - Arquivo em `apps/cliente/services.py` → processo: `apps.cliente`
  - Arquivo em `comum/integracoes/sms_service.py` → processo: `comum.integracoes`
  - Arquivo em `portais/admin/views.py` → processo: `portais.admin`
  - Arquivo em `pinbank/cargas_pinbank/services.py` → processo: `pinbank.cargas_pinbank`
- **Processos Cadastrados no Banco** (tabela `log_parametros`):
  - `apps.cliente`, `apps.transacoes`, `apps.ofertas`, `apps.conta_digital`, `apps.oauth`
  - `portais.admin`, `portais.lojista`, `portais.recorrencia`, `portais.controle_acesso`
  - `comum.integracoes`, `comum.estr_organizacional`, `comum.middleware`, `comum.oauth`, `comum.utilitarios`
  - `pinbank`, `pinbank.cargas_pinbank`
  - `parametros_wallclub`, `sistema_bancario`, `posp2`, `checkout.link_pagamento_web`
- **Controle Dinâmico**: Todos os logs devem usar `registrar_log()` para controle via banco
- **Níveis Obrigatórios**:
  - `nivel='ERROR'` - **OBRIGATÓRIO** em todos os blocos `except` (tratamento de erros)
  - `nivel='INFO'` - Padrão para operações normais e auditoria
  - `nivel='DEBUG'` - Informações detalhadas apenas em desenvolvimento
- **Exemplo Completo**:
  ```python
  # Arquivo: comum/integracoes/sms_service.py
  from comum.utilitarios.log_control import registrar_log
  
  def enviar_sms(telefone, mensagem):
      try:
          # Logs normais usam caminho do módulo
          registrar_log('comum.integracoes', f'Enviando SMS para {telefone}')
          resultado = api_sms.enviar(telefone, mensagem)
          return resultado
      except Exception as e:
          # OBRIGATÓRIO: nivel='ERROR' em exceções
          registrar_log('comum.integracoes', f'Erro ao enviar SMS: {str(e)}', nivel='ERROR')
          return False
  ```

### 27. JAVASCRIPT SEPARADO E ORGANIZADO:
- **Um Arquivo por Template**: Cada template deve ter arquivo JS específico (`usuario_form.js`, `pagamentos_list.js`)
- **Carregamento Otimizado**: Usar `{% block extra_js %}` para carregar apenas JS necessário
- **Localização Padrão**: Arquivos em `static/js/` com nomenclatura `nome_template.js`
- **Funções Nomeadas**: Evitar funções anônimas, usar nomes descritivos (`carregarCampoReferencia`, `validarFormulario`)
- **Inicialização**: Usar `document.addEventListener('DOMContentLoaded', function() {})` para inicialização
- **Reutilização**: Criar arquivo `common.js` para funções compartilhadas entre templates
- **Portal Específico**: Criar arquivos comuns por portal (`lojista-common.js`, `admin-common.js`)
- **Exportações AJAX**: Implementar feedback visual e processamento em background para exportações grandes

### 28. NAVEGAÇÃO E BREADCRUMBS OBRIGATÓRIOS:
- **Breadcrumbs Obrigatórios**: Toda página deve ter navegação hierárquica clara
- **Estrutura Padrão**: `Home > Seção > Subseção > Página Atual`
- **Botão Voltar**: Sempre em `{% block navbar_actions %}` com classe `btn btn-outline-light btn-sm`
- **Links Ativos**: Marcar página atual como ativa nos breadcrumbs
- **Controle de Acesso**: Breadcrumbs devem respeitar permissões do usuário
- **Responsividade**: Breadcrumbs devem colapsar em dispositivos móveis
- **Navegação Genérica**: Usar `history.back()` JavaScript para botão voltar quando não há URL específica
- **Portal Lojista**: Remover page headers e back buttons desnecessários para interface mais limpa

### 29. EXPORTAÇÕES E PROCESSAMENTO EM BACKGROUND:
- **Limite Inteligente**: Export direto até 5.000 registros, processamento em background acima disso
- **Processamento em Batch**: Dados processados em lotes para evitar sobrecarga de memória
- **Export por Email**: Arquivos grandes são gerados em background e enviados por email
- **Interface AJAX**: JavaScript para lidar com respostas JSON e downloads diretos
- **Feedback Visual**: Loading states e mensagens de progresso durante exportações
- **Validação CSRF**: Sempre incluir token CSRF em formulários de exportação
- **Otimização SQL**: Usar agregações SQL em vez de Python para cálculos de totais

### 30. CONTROLE DE ACESSO BASEADO EM PERMISSÕES:
- **Validação Granular**: Verificar permissões específicas antes de exibir dados
- **Filtros por Loja**: Aplicar filtros automáticos baseados no acesso do usuário
- **Queries Otimizadas**: Usar `select_related` e campos inteiros em vez de ForeignKeys quando possível
- **Fallback N/A**: Sempre ter fallback para campos que podem ser nulos (ex: "N/A")
- **Transações Atômicas**: Usar `@transaction.atomic` para operações críticas
- **Logs de Auditoria**: Registrar todas as operações de exportação e acesso a dados sensíveis

### 31. FORMATAÇÃO E VALIDAÇÃO DE DADOS:
- **Campos NSU**: Usar input type="text" com pattern numérico (não "number")
- **Valores Monetários**: Preservar formatação original, não substituir pontos
- **Case-Sensitive**: Preservar case das colunas no processamento de CSV
- **Validação Nulos**: Sempre validar valores nulos e undefined nos formulários
- **Datas Flexíveis**: Suportar múltiplos formatos de data (DD/MM/YYYY, YYYY-MM-DD)
- **Parâmetros SQL**: Usar formatos fixos em vez de parâmetros dinâmicos quando possível

### 32. SISTEMA OAUTH 2.0 COMPLETO (IMPLEMENTADO):
- **Client Credentials Flow**: Sistema principal de autenticação para APIs
- **Múltiplos Contextos Ativos**: `apps`, `checkout`, `posp2`, `pinbank`
- **Decorators Obrigatórios por Contexto**:
  - `@require_oauth_apps` - APIs de aplicativos móveis
  - `@require_oauth_checkout` - Sistema de checkout seguro
  - `@require_oauth_posp2` - Operações POSP2
  - `@require_oauth_pinbank` - Integrações Pinbank
  - __Rotas POSP2 publicadas em__: `/api/v1/posp2/` (mapeadas em `wallclub/urls.py` → `include('posp2.urls')`)
- **Tokens JWT**: Expiração configurável (24h padrão)
- **Refresh Automático**: Sistema de renovação com fallback
- **Coexistência**: Compatibilidade com API Keys durante transição
- **Logs Detalhados**: Auditoria completa de autenticação

### 33. SISTEMA DE RECORRÊNCIA (IMPLEMENTADO):
- **Portal Completo**: Gestão de pagamentos recorrentes
- **Dashboard**: Métricas e filtros avançados
- **Autenticação Própria**: Login/logout independente
- **Interface Responsiva**: Bootstrap 5 com JavaScript modular
- **Paginação Otimizada**: Busca avançada com filtros
- **Integração**: Sistema de transações e notificações

### 34. PORTAL DE VENDAS - CHECKOUT PRESENCIAL (IMPLEMENTADO):
- **Core Compartilhado**: Models e services em `/checkout/` (CheckoutCliente, CheckoutCartaoTokenizado, CheckoutTransaction)
- **Autenticação**: Sistema próprio com `PortalUsuario`, `PortalPermissao`, `PortalUsuarioAcesso`
- **Sessão Isolada**: `vendas_authenticated`, `vendedor_id` (separado de outros portais)
- **Decorator**: `@requer_checkout_vendedor` valida permissão `portal='vendas'`
- **CRUD Clientes**: Cadastro com CEP via ViaCEP, CPF/CNPJ validado
  - __Regra de Cadastro CPF__: Consultar/cadastrar `apps.cliente.Cliente` via `ClienteAuthService.cadastrar()` (inclui Bureau + envio `senha_de_acesso_wallclub`) e usar o nome oficial do Cliente do app ao criar `checkout.CheckoutCliente`. Após cadastro no app, enviar também `baixar_app_wallclub` (sem reset de senha).
- **Tokenização Cartões**: Integração com Pinbank via `CartaoTokenizadoService`
- **Checkout com 3 Opções de Pagamento**:
  - **Cartão Salvo**: Pulldown exibe número mascarado (4110########9403) + apelido, usa `efetuar_transacao_cartao_tokenizado`
  - **Digitar Cartão**: Campos para número/validade/CVV/nome, transação direta com `efetuar_transacao` (não salva cartão)
  - **Cadastrar Novo**: Redireciona para tela de tokenização (salva para uso futuro)
- **Cálculo de Parcelas Avançado**:
  - Botão "Calcular Parcelas" após digitar valor + bandeira
  - `CheckoutService.simular_parcelas(valor, loja_id, bandeira, wall)` - usa `id_loja` diretamente (sem terminal)
  - Suporta cálculo diferente por bandeira (diferente do POS que é fixo em Mastercard)
  - Calcula: PIX, DÉBITO, CRÉDITO 1x, CRÉDITO 2-12x com descontos e cashback
  - Interface exibe parcelas ordenadas com valor por parcela e descrição
- **Processamento Dual**:
  - `CheckoutService.processar_pagamento_cartao_tokenizado()` - cartão salvo
  - `CheckoutService.processar_pagamento_cartao_direto()` - cartão digitado (campos: numero_cartao, validade, cvv, nome_titular)
- **Interface Adaptativa**: Dropdown de loja só aparece se vendedor tem múltiplas lojas
- **Logs Padronizados**: `registrar_log('portais.vendas', mensagem, nivel)` e `registrar_log('checkout.simulacao', mensagem, nivel)`
- **Correções Aplicadas**:
  - CEP limpo (somente números) antes de salvar
  - Logs detalhados de tokenização e erros do Pinbank
  - Tratamento completo de exceções em services
  - Calculadora usa `id_loja` ao invés de `terminal` (conceito diferente do POS)

### 35. RISK ENGINE E INTEGRAÇÃO ANTIFRAUDE (IMPLEMENTADO - 16/10/2025):

**Container Separado (Porta 8004):**
- **Arquitetura**: Risk Engine roda em container Django isolado
- **Network**: `wallclub-network` (compartilhada entre containers)
- **Comunicação**: OAuth 2.0 (client_credentials) + Bearer token
- **Credenciais OAuth**: Separadas por contexto (Admin, POS, Internal) via AWS Secrets Manager
- **Banco**: MySQL compartilhado entre containers
- **Cache**: Redis compartilhado
- **Deploy**: Independente, permite escalar separadamente

**Integração POSP2 (✅ CONCLUÍDO):**
- **Interceptação**: Antes do Pinbank em `posp2/services_transacao.py` linha ~333
- **Service**: `posp2/services_antifraude.py` (374 linhas)
- **Dados Enviados**: CPF, valor, modalidade, parcelas, terminal, loja_id, canal_id, BIN cartão, bandeira, NSU
- **Decisões**: APROVADO (continua), REPROVADO (bloqueia), REVISAR (processa + marca)
- **Fail-open**: Erro no antifraude não bloqueia transação
- **Logs**: Detalhados em `logs/posp2.antifraude.log`

**Integração Checkout Web - Link de Pagamento (✅ CONCLUÍDO 22/10/2025):**
- **Interceptação**: Antes do Pinbank em `checkout/link_pagamento_web/services.py` linha ~117-183
- **Service**: `checkout/services_antifraude.py` (268 linhas)
- **Dados Enviados**: CPF, valor, modalidade, parcelas, número_cartao, bandeira, IP, user_agent, device_fingerprint, cliente_nome, transaction_id
- **Decisões**: 
  - **APROVADO** → Processa normalmente no Pinbank
  - **REPROVADO** → status='BLOQUEADA_ANTIFRAUDE', não processa, retorna erro para cliente
  - **REVISAR** → status='PENDENTE_REVISAO', processa no Pinbank + notifica analista
- **Campos no Model (checkout_transactions)**:
  - `score_risco` (INT) - Score 0-100
  - `decisao_antifraude` (VARCHAR) - APROVADO/REPROVADO/REVISAR
  - `motivo_bloqueio` (TEXT) - Motivo da decisão
  - `antifraude_response` (JSON) - Resposta completa Risk Engine
  - `revisado_por`, `revisado_em`, `observacao_revisao` - Revisão manual
- **Status Novos**: `BLOQUEADA_ANTIFRAUDE`, `PENDENTE_REVISAO`
- **Fail-open**: Erro no antifraude aprova transação (segurança operacional)
- **Logs**: `registrar_log('checkout.link_pagamento_web', mensagem)` com emojis 🛡️✅❌⚠️
- **SQL Migration**: `scripts/sql/adicionar_campos_antifraude_checkout.sql`

**Padrão de Integração Service Layer:**
```python
# portais/admin/services_antifraude.py
class AntifraudeService:
    BASE_URL = 'http://wallclub-riskengine:8004/api/antifraude'  # Container hostname
    
    @classmethod
    def obter_metricas_dashboard(cls, dias: int = 7) -> Dict:
        """Consome API do Risk Engine"""
        response = requests.get(f'{cls.BASE_URL}/dashboard/', params={'dias': dias})
        if response.status_code == 200:
            return response.json()
        return cls._metricas_vazias()  # Fallback seguro
```

**Padrão de Dashboard Integrado:**
- **View**: Aceita parâmetros GET (`?dias=7`) e passa para service
- **Service**: Consome API do container remoto
- **Template**: Exibe métricas completas com fallback para dados vazios
- **Filtros de Período**: Botões de navegação (Hoje, 7, 30, 90 dias)
- **Métricas Completas**: Transações, decisões, performance, blacklist, whitelist, top regras

**Benefícios da Arquitetura:**
- **Isolamento**: Falha no Risk Engine não afeta portal principal
- **Escalabilidade**: Containers podem escalar independentemente
- **Manutenibilidade**: Código antifraude isolado do core
- **Deploy**: Atualizações independentes sem afetar outros serviços
- **Segurança**: OAuth token validation entre containers

**Requirements Risk Engine:**
- `boto3` para AWS Secrets Manager
- Mesmo stack Django do portal principal
- Dockerfile otimizado (Python 3.11-slim)
- Recursos limitados (512MB RAM, 0.5 CPU)

### 36. PROBLEMAS CONHECIDOS E PENDENTES:

#### CHECKOUT - ENVIO "BAIXAR_APP" NÃO FUNCIONA (PENDENTE):
- **Status**: ⚠️ PROBLEMA NÃO RESOLVIDO
- **Descrição**: Template WhatsApp/SMS "baixar_app" não é enviado no fluxo de novo cadastro via Checkout (portal vendas)
- **Comportamento Esperado**:
  1. Cliente novo cadastrado no Checkout → Enviar WhatsApp "baixar_app" ANTES do cadastro
  2. Em seguida, chamar `ClienteAuthService.cadastrar()` (envia senha)
  3. Também enviar SMS "baixar_app" se template existir
- **Evidências**:
  - Logs mostram apenas envio de senha, não de "baixar_app"
  - Templates "baixar_app" existem no banco para canal_id=1 (WhatsApp e SMS, ativos)
  - POS funciona corretamente (envia "baixar_app" + senha na ordem)
  - Container rebuilds com `--no-cache` não resolvem
  - Git push/pull confirmados, mas container não reflete alterações
- **Código Implementado** (não funcional):
  - `portais/vendas/views.py::cliente_form`: Logs de diagnóstico adicionados
  - Cache Bureau implementado (evita consulta dupla) ✅
  - Ordem de envio: "baixar_app" → `cadastrar()` (senha)
  - SMS "baixar_app" também implementado
- **Próximos Passos** (quando retomar):
  1. Verificar manualmente no container se código está atualizado: `docker exec wallclub-prod-release300 grep -n "Preparando envio baixar_app" /app/portais/vendas/views.py`
  2. Se não estiver: investigar processo de deploy (Dockerfile COPY, volumes, cache)
  3. Validar se `MessagesTemplateService.preparar_whatsapp(canal_id, 'baixar_app')` retorna template
  4. Conferir logs `portais.vendas.log` para mensagens de diagnóstico
  5. Comparar fluxo POS (funcionando) vs Checkout (não funciona)
- **Tempo Investido**: ~2h30 (16/10/2025)
- **Decisão**: Pausado para priorizar outras features

### 36. NOTIFICAÇÕES PUSH FIREBASE (IMPLEMENTADO):
- **Firebase Cloud Messaging**: Integração completa com arquitetura refatorada
- **Templates Dinâmicos**: Sistema de templates no banco (`templates_envio_msg`)
  - Tipo: `PUSH`, `SMS`, `WHATSAPP`
  - Formato JSON: `{"title": "...", "body": "..."}`
  - Variáveis substituíveis: `{valor}`, `{autorizacao_id}`, etc
  - Fallback automático se template não encontrado
- **Arquitetura Core**:
  - `_enviar_push_core(cpf, id_template, template_vars, custom_data, tipo)` - Para transações
  - `_enviar_client_id_push_core(cliente_id, id_template, template_vars, custom_data, tipo)` - Para autorizações
  - Métodos específicos usam o core (zero duplicação)
- **Notificações Automáticas**: Transações de cartão e autorizações de saldo em tempo real
- **Busca Otimizada**: 
  - `get_user_token_by_cpf(cpf)` - Busca por CPF
  - `get_user_token_by_cliente_id(cliente_id)` - Busca por ID (retorna token + CPF)
- **Sistema de Fallback**: Múltiplos tokens por usuário
- **Registro de Notificações**: Todas notificações salvas na tabela para auditoria
- **Logs Detalhados**: Auditoria de envios
- **Integração**: Sistema de transações em tempo real

### 35. API PINBANK ATUALIZADA (IMPLEMENTADO):
- **Novo Padrão**: Tokenização de cartão atualizada
- **OAuth 2.0**: Autenticação com Pinbank
- **Notificações Push**: Automáticas para transações
- **Fallback**: Múltiplas tentativas
- **Cache Inteligente**: Performance otimizada
- **Logs Detalhados**: Auditoria completa

### 36. CORREÇÃO DE LOOPS DE AUTENTICAÇÃO:
- **Problema Comum**: Inconsistência entre definição e verificação de sessão
- **Causa**: Login define `usuario_id` mas views verificam `authenticated`
- **Solução**: Sempre definir ambos os campos na sessão:
  ```python
  request.session['portal_authenticated'] = True
  request.session['portal_usuario_id'] = usuario.id
  ```
- **Verificação Padrão**: Views devem verificar `portal_authenticated`
- **Debugging**: Verificar código no container vs local para inconsistências
- **Containers**: Usar `docker exec container cat arquivo` para verificar código atual
- **Correção Direta**: `docker exec container sed -i 's/old/new/g' arquivo` quando necessário

### 37. SISTEMA DE PRIMEIRO ACESSO E REDIRECIONAMENTO INTELIGENTE (IMPLEMENTADO):
- **Problema**: Usuários não conseguiam fazer login após criação
- **Causa**: Campo `email_verificado=False` por padrão
- **Solução**: Ativação via token de primeiro acesso
- **Redirecionamento Inteligente**:
  ```python
  # Lógica implementada em primeiro_acesso_view
  if len(portais_usuario) > 1:
      # Múltiplas permissões -> portal admin
      redirect_url = 'portais_admin:login'
  elif len(portais_usuario) == 1:
      # Uma permissão -> portal específico
      portal = portais_usuario[0]
      if portal == 'lojista':
          redirect_url = '/portal_lojista/'
      elif portal == 'corporativo':
          redirect_url = '/portal_corporativo/'
      elif portal == 'recorrencia':
          redirect_url = '/portal_recorrencia/'
  ```
- **Logs de Debug**: Implementado log da senha temporária para debug
- **Email com Contexto**: Sistema de emails usa contexto dinâmico por canal

### 38. OTIMIZAÇÕES DE PERFORMANCE - SQL DIRETO (IMPLEMENTADO 17/10/2025):

**Problema Identificado:**
- Views com ORM Django pesado causando lentidão em produção
- Múltiplas iterações em Python sobre querysets grandes
- Paginação com objetos ORM carregados na memória
- Cálculos de totais feitos em Python ao invés de SQL

**Solução Aplicada:**
- **SQL Direto**: Usar `cursor.execute()` para queries complexas
- **Agregações no Banco**: `SUM()`, `COUNT()`, `GROUP BY` ao invés de Python
- **Window Functions**: `ROW_NUMBER() OVER()` para deduplicação eficiente
- **Paginação Manual**: Retornar dicts ao invés de objetos ORM (zero overhead)
- **Queries Consolidadas**: Múltiplas agregações em 1 única passada pelo banco

**Quando Usar SQL Direto:**
1. **Queries com Agregações Complexas**: Múltiplos `SUM()`, `COUNT()`, `AVG()` em uma consulta
2. **Deduplicação com Window Functions**: `ROW_NUMBER() OVER(PARTITION BY ... ORDER BY ...)`
3. **Dashboards com Métricas**: Consolidar várias agregações em 1 query
4. **Relatórios com Grande Volume**: Evitar carregar objetos ORM desnecessários
5. **Iterações em Python**: Se você está iterando para calcular totais, use SQL

**Padrão de Implementação:**

```python
from django.db import connection

# 1. Construir WHERE clause dinamicamente
where_conditions = ["status = 'APROVADO'"]
params = []

if filtro_data:
    where_conditions.append("data >= %s")
    params.append(filtro_data)

where_clause = " AND ".join(where_conditions)

# 2. Query com agregações consolidadas
sql = f"""
    SELECT 
        COUNT(DISTINCT id) as total,
        SUM(valor) as soma_valores,
        AVG(valor) as media_valores,
        canal,
        COUNT(*) as transacoes_por_canal
    FROM tabela
    WHERE {where_clause}
    GROUP BY canal
"""

# 3. Executar e processar
with connection.cursor() as cursor:
    cursor.execute(sql, params)
    columns = [col[0] for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]

# 4. Paginação manual (se necessário)
sql_paginado = f"""
    SELECT * FROM (
        SELECT *, ROW_NUMBER() OVER(PARTITION BY nsu ORDER BY id DESC) as rn
        FROM tabela
        WHERE {where_clause}
    ) t WHERE rn = 1
    ORDER BY data DESC
    LIMIT %s OFFSET %s
"""

cursor.execute(sql_paginado, params + [per_page, offset])
```

**Última Atualização:** 23/10/2025

---
4. `views_conciliacao.py` - Subquery otimizada → muito rápido
5. `views.py` (dashboard) - 4 queries → 1 consolidada → instantâneo

**Portal Admin:**
6. `views.py` (dashboard) - 2 queries → 1 consolidada → instantâneo
7. `views_rpr.py` - 3 iterações + múltiplas agregações → SQL consolidado (12 agregações) → ganho MASSIVO
8. `views_transacoes.py` - ORM pesado → SQL direto + totais no SQL → muito rápido

**Benefícios Alcançados:**
- ⚡ Tempo de resposta reduzido drasticamente
- 🚀 Eliminação de gargalos de ORM
- 📊 Múltiplas agregações em 1 passada pelo banco
- 💾 Redução de uso de memória
- 🔥 View RPR: de extremamente pesada para muito rápida
- ✅ Zero iterações em Python nas views críticas

**Quando NÃO Usar SQL Direto:**
- Queries simples com poucos registros
- CRUD básico (create, read, update, delete)
- Relacionamentos simples que o ORM gerencia bem
- Quando a legibilidade do código é mais importante que performance

**Observações Importantes:**
- SQL Injection: SEMPRE usar parâmetros (`%s`) ao invés de interpolação de strings
- Mantenibilidade: Documentar queries complexas com comentários
- Testes: Validar resultados comparando com versão ORM quando possível
- Migration: Não usar SQL direto em migrations, apenas em views/services

### 39. DEBUGGING DE AUTENTICAÇÃO:
- **Verificar Senha**: `usuario.verificar_senha(senha)` funciona corretamente
- **Verificar Permissões**: `usuario.pode_acessar_portal('portal')` 
- **Verificar Status**: `ativo=True`, `email_verificado=True`
- **Logs Essenciais**: Sempre logar senha temporária gerada para debug
- **Teste Completo**: Usar `AutenticacaoService.autenticar_usuario()` para validar fluxo completo

### 39. PADRÃO DE URLs COM UNDERSCORE:
- **URLs de Autenticação**: Usar underscore ao invés de hífen
- **Padrão Obrigatório**: `primeiro_acesso`, `reset_senha`, `validar_usuario`
- **Aplicação**: Tanto em URLs Django quanto em links de email
- **Consistência**: Manter padrão em todos os portais (admin, lojista, corporativo, recorrência)
- **Exemplos Corretos**:
  - `/portal_admin/primeiro_acesso/<token>/`
  - `/portal_lojista/{marca}/primeiro_acesso/<token>/`
  - `/portal_admin/reset_senha/<token>/`

### 40. SISTEMA DE EMAIL COM MARCA PERSONALIZADA (IMPLEMENTADO):
- **Identificação Automática**: Canal baseado no tipo de acesso do usuário
- **Tipos Suportados**: 
  - `grupo_economico` → referência é o canal direto
  - `lojista` → busca canal via loja (`loja.canal_id`)
  - `canal` → referência direta do canal
- **URLs Personalizadas**: `/portal_lojista/{marca}/primeiro_acesso/{token}/`
- **Fallback Inteligente**: Canal do usuário logado quando não identificado
- **Logs de Auditoria**: Canal utilizado registrado nos logs para debug
- **Implementação**: `EmailService.enviar_email_primeiro_acesso()` com contexto dinâmico

### 41. CSS DE AUTENTICAÇÃO POR PORTAL (IMPLEMENTADO):
- **Portal Lojista**: CSS específico em `staticfiles/css/lojista.css`
- **Classes Obrigatórias**: `.auth-body`, `.auth-container`, `.auth-card`, `.auth-header`
- **Template Base**: `base_auth.html` carrega CSS específico do portal
- **Design Consistente**: Cores e gradientes específicos por portal
- **Responsividade**: Layout adaptável para dispositivos móveis
- **Build Docker**: Sempre usar `--no-cache` para atualizar arquivos estáticos

### 42. PERGUNTAR ANTES DE ASSUMIR:
- **Regra Fundamental**: Quando houver qualquer dúvida sobre requisitos, arquitetura ou implementação, SEMPRE perguntar ao usuário antes de assumir ou implementar
- **Não Fazer Suposições**: Nunca assumir o que o usuário quer sem confirmação explícita
- **Validar Escopo**: Sempre confirmar entendimento antes de começar implementação
- **Exemplos de Dúvidas**: Onde implementar, como integrar, qual abordagem usar, que dados usar
- **Consequência**: Implementações baseadas em suposições geram retrabalho e frustração

### 43. SISTEMA ADMIN_CANAL IMPLEMENTADO:
- **Funcionalidade**: Tipo de usuário "admin_canal" para portal lojista
- **Criação**: Portal admin pode criar usuários admin_canal com seleção de canal específico
- **Template**: Dropdown "🌐 Admin Canal" em `tipo_lojista` com endpoint `ajax_canais`
- **Views.py**: Mapeamento `admin_canal` → `entidade_tipo_lojista = 'admin_canal'`
- **JavaScript**: Carregamento dinâmico de canais via AJAX quando selecionado
- **Lógica pós-commit**: Reconhece `admin_canal` e usa referência direta como canal_id
- **Portal Lojista**: Sistema de permissões existente já reconhece admin_canal automaticamente
- **Email personalizado**: URL com marca correta baseada no canal selecionado
- **Controle de acesso**: Admin_canal tem acesso restrito apenas ao portal lojista
- **Banco de dados**: Usa ENUM existente `admin_canal` na tabela `portais_usuario_acesso`

### 44. MIGRAÇÃO OAUTH 2.0 - API KEYS REMOVIDAS (IMPLEMENTADO):
- **Sistema Unificado**: 100% OAuth 2.0 - API Keys completamente removidas
- **Pasta Removida**: `comum/autenticacao/` deletada - era exclusiva para API Keys
- **Decorators OAuth**: Todos em `comum/oauth/decorators.py`
  - `require_oauth_apps` - Apps móveis (aceita JWT de clientes)
  - `require_oauth_posp2` - Terminal POS/POSP2
  - `require_oauth_checkout` - Checkout web
- **Models Removidos**: `APIKey` e `APIUsage` deletados
- **Tabelas Removidas**: `api_keys` e `api_usage` (script: `scripts/producao/remover_api_keys.sql`)
- **INSTALLED_APPS**: `comum.autenticacao` removido - usar apenas `comum.oauth`
- **Views Sistema**: `apps/conta_digital/views_system.py` desabilitado
  - Endpoints `/system/creditar/`, `/system/debitar/` removidos
  - Métodos internos `ContaDigitalService` continuam funcionando
  - Uso interno via chamada direta ao service (sem HTTP)
- **POSP2 Migrado**: 9 views usando OAuth + 2 views obsoletas removidas
- **Import Padrão**: `from comum.oauth.decorators import require_oauth_*`

### 45. SISTEMA DE CHECKOUT REFATORADO - TRANSAÇÕES RASTREÁVEIS (IMPLEMENTADO):
- **Arquitetura Dupla**: Link de Pagamento Público + Portal de Vendas compartilham core
- **Core Compartilhado**: `/checkout/` (CheckoutCliente, CheckoutCartaoTokenizado, CheckoutTransaction, CheckoutTransactionAttempt)
- **Novo Fluxo de Transação**:
  1. **Vendedor cria transaction PENDENTE**:
     - View: `portais/vendas/processar_envio_link`
     - Campos preenchidos: `token`, `cliente`, `loja_id`, `valor_transacao`, `vendedor_id`, `origem='CHECKOUT'`, `status='PENDENTE'`
     - Campos NULL: `nsu`, `codigo_autorizacao`, `forma_pagamento`, `parcelas`, `ip_address_cliente`, `processed_at`
     - Envia email com link para cliente
  2. **Cliente acessa link e processa pagamento**:
     - View: `checkout/link_pagamento_web/ProcessarCheckoutView`
     - Busca transaction existente via campo `token`
     - **SE APROVADO**: Atualiza transaction com `nsu`, `codigo_autorizacao`, `forma_pagamento`, `parcelas`, `ip_address_cliente`, `user_agent_cliente`, `processed_at`, `status='APROVADA'`
     - **SE NEGADO**: Cria `CheckoutTransactionAttempt` com `tentativa_numero`, `erro_pinbank`, `pinbank_response`, `ip_address_cliente`, `numero_cartao_hash`
     - **SE 3 tentativas**: Atualiza transaction `status='NEGADA'`
- **CheckoutTransaction Refatorado**:
  - Campo `token` (VARCHAR 100, UNIQUE) para relacionar com CheckoutToken
  - Campo `vendedor_id` (BIGINT) para rastreamento
  - Campo `origem` (CHECKOUT=Portal vendas link, LINK=API direta)
  - Timestamps separados: `created_at` (vendedor), `processed_at` (cliente)
  - Campos nullable: `forma_pagamento`, `nsu`, `codigo_autorizacao` (preenchidos apenas quando cliente processa)
- **CheckoutTransactionAttempt** (NOVA TABELA):
  - Registra tentativas frustradas sem poluir CheckoutTransaction
  - Campos: `transaction_id`, `tentativa_numero`, `erro_pinbank`, `pinbank_response`, `ip_address_cliente`, `user_agent_cliente`, `numero_cartao_hash`, `attempted_at`
  - Auditoria completa de falhas de pagamento
- **Rastreamento Completo**: Vendedor → Token → Transaction PENDENTE → Cliente → Tentativas → Transaction APROVADA/NEGADA
- **Documentação**: `docs/4. sistema_checkout_completo.md` (merge de link_pagamento + portal_vendas)
- **Benefícios**:
  - Zero duplicação: uma transaction do início ao fim
  - Rastreabilidade: vendedor_id em todas transações
  - Auditoria: todas tentativas registradas separadamente
  - Performance: queries otimizadas via token

### 45. SISTEMA DE NOTIFICAÇÕES PUSH MULTI-CANAL (IMPLEMENTADO):
- **Push correto por canal**: Sistema busca canal_id da LOJA (não do cliente)
- **Clientes multi-canal**: Cliente pode estar em múltiplos canais (ex: canal 1 e 6)
- **Lógica implementada**: `posp2/services.py` busca canal via `loja_info.get('canal_id')`
- **Validação**: Verifica se cliente existe no canal específico da loja
- **pega_info_loja()**: Retorna `{id, loja_id, loja, cnpj, canal_id}`
- **Bundle ID dinâmico**: Busca `bundle_id` da tabela `canal` (não hardcoded)
- **APN Service**: `comum/integracoes/apn_service.py` usa `Canal.get_canal(canal_id).bundle_id`
- **Templates unificados**: `comum/integracoes/messages_template_service.py`
  - SMS: Template controla se adiciona nome do canal
  - PUSH: Template controla title/body completos
  - Sem concatenação automática de canal_nome
- **Query extrato**: Migrada de `loja/terminais` para `baseTransacoesGestao`
  - Filtra por: `btg.var7 = cpf` AND `canal.id = canal_id`
  - Join: `baseTransacoesGestao → canal → transactiondata`
  - Respeita canal correto do cliente

### 46. LIMPEZA COMPLETA DO SISTEMA DE LOGGING (IMPLEMENTADO):
- **Problema Resolvido**: Erros críticos de logging e dependências circulares em produção
- **Padrão Único**: **OBRIGATÓRIO** usar apenas `registrar_log()` - NUNCA `import logging` direto
- **Imports Removidos**: Todos os `import logging` removidos dos arquivos do projeto (exceto `log_control.py`)
- **Logger Órfãos**: Todos os `logger = logging.getLogger()` removidos completamente
- **Dependências Circulares**: Chamadas `registrar_log()` removidas de `config_manager.py` (inicialização Django)
- **Correções Críticas**:
  - `NameError: LOGGING not defined` em `production.py` → configuração removida (já em `base.py`)
  - `NameError: name 'logging' is not defined` em `calculadora_base_gestao.py` → logger removido
  - Import errors em `portais/recorrencia/services.py` → typo corrigido + imports adicionados
- **Padrão Obrigatório**:
  ```python
  # ❌ NUNCA MAIS USAR:
  import logging
  logger = logging.getLogger(__name__)
  logger.info("mensagem")
  
  # ✅ SEMPRE USAR:
  from comum.utilitarios.log_control import registrar_log
  registrar_log('modulo.submodulo', 'mensagem', nivel='INFO')
  registrar_log('modulo.submodulo', f'Erro: {str(e)}', nivel='ERROR')  # OBRIGATÓRIO em except
  ```
- **Verificação**: Sistema limpo - container sobe sem erros de logging ou imports
- **Status**: ✅ Produção estabilizada - todos os erros críticos corrigidos

### 47. MÓDULO PINBANK REFATORADO (IMPLEMENTADO):
- **Estrutura de Services Separados**:
  - `pinbank/services.py` - Integração API Pinbank (tokens, autenticação, consulta extrato POS)
  - `pinbank/services_consulta_apps.py` - Consultas para apps mobile (extrato, comprovante)
  - `pinbank/services_transacoes_pagamento.py` - Transações e tokenização de cartões
  - `pinbank/cargas_pinbank/services.py` - ETL e cargas de dados Pinbank
- **Nomenclatura Padronizada**: Todos arquivos de serviços iniciam com `services_`
- **Separação de Responsabilidades**: Cada arquivo tem escopo bem definido
- **Uso Obrigatório de Decimal**:
  - `from decimal import Decimal` - SEMPRE importar
  - **NUNCA** usar `float()` para valores monetários
  - Usar `Decimal('0.00')` para inicialização de valores zerados
  - Queries SQL retornam `Decimal` nativamente - não converter para `float()`
  - F-strings funcionam normalmente: `f"R$ {valor:.2f}"` com Decimal
- **Comprovante com Cashback**:
  - Campo `valor_cashback` extraído de `transactiondata.valor_cashback`
  - Campo `valor_pago_cliente` calculado: `vdesconto - valor_cashback`
  - Ambos formatados com `R$` no JSON de saída
  - Disponíveis em todos os 6 casos de comprovante (PIX, DÉBITO, PARCELADO, etc)
- **Verificação de Cancelamentos**: Usa ORM Django com `BaseTransacoesGestao.objects.filter()`
  - Busca por `var9` (NSU) e `var68` (status) com valores `'TRANS. CANCELADA POSTERIOR'` ou `'TRANS. CANCELADA POR CHARGEBACK'`
  - Método `.exists()` para performance otimizada

### 27. CHECKOUT E LINK DE PAGAMENTO:
- **Autenticação Dupla**: Geração do token (OAuth2 autenticado) + Acesso à página (token público único)
- **Token Único**: 
  - SHA-256 de URL-safe (48 bytes) com validade de **30 minutos**
  - Sistema de **3 tentativas** por token
  - Marca como `used=True` apenas após: (1) transação aprovada OU (2) 3 tentativas falhadas
  - Campo `tentativas_pagamento` incrementado a cada falha
  - Bloqueio automático após 3 tentativas com mensagem detalhada
- **Dados do Cliente** (salvos no token e transacão):
  - `nome_completo`, `cpf`, `celular`, `endereco_completo` (obrigatórios)
  - `pedido_origem_loja` (opcional) - ID do pedido no sistema de origem para rastreamento
  - Campos são **readonly** no checkout (vem pré-preenchidos do token)
- **Cálculo de Parcelas**: 
  - API calcula TODAS bandeiras × TODAS parcelas (1-12x) de uma vez
  - Retorna apenas parcelas calculadas com sucesso (filtro de None)
  - Frontend troca visualização ao mudar bandeira (sem nova requisição)
  - NUNCA calcular individualmente - sempre em batch
- **CalculadoraDesconto**: 
  - Método: `calcular_desconto(valor_original, data, forma, parcelas, id_loja, wall)`
  - NÃO aceita parâmetro `bandeira` - usar apenas `forma` e `parcelas`
  - Retorna None se configuração não existe (filtrar no backend)
- **Mensagens de Erro**:
  - Exibe motivo específico da negação (vem do Pinbank)
  - Mostra tentativas restantes (ex: "Você ainda tem 2 tentativa(s) restante(s)")
  - Bloqueia formulário após 3 tentativas
- **Simulador DermaDream**: `/api/v1/checkout/simula_dermadream/`
  - Simula fluxo completo: OAuth → Gerar Token → Checkout → Pagamento
  - Apenas para testes (será removido em produção)
- **Indicação de Encargos**:
  - Diferenca > 0.5% = "(+ X% juros)"
  - Diferenca < -0.5% = "(X% desc.)"
  - Entre -0.5% e 0.5% = sem indicação
- **Bandeiras Dinâmicas**: Select populado apenas com bandeiras que têm parcelas calculadas
- **Interface Dinâmica**: JavaScript vanilla para troca de parcelas ao mudar bandeira (sem frameworks)
- **CSS Paleta WallClub**: Azul escura (--primary-gradient: #0f2a5a → #1a4480)
- **CSS Inline**: Nunca usar arquivos CSS externos - sempre inline no template
- **Parse de Templates**: Valores Django no JavaScript: `parseInt('{{ loja_id }}')`, `parseFloat('{{ valor }}')`
- **Validação Frontend**: Máscaras de CPF, celular, cartão e validade via JavaScript
- **Rate Limiting**: Geração (10/min), Acesso (30/min), Processamento (5/min)
- **Models**:
  - CheckoutToken: token, loja_id, item_nome, item_valor, expires_at, used, created_by
  - CheckoutSession: token (FK), cpf, nome, celular, endereco, parcelas, tipo_pagamento
  - CheckoutTransaction: session (FK), loja (FK para comum.Loja), nsu, status, valor_transacao, cpf_cliente
- **Foreign Keys**: 
  - CheckoutTransaction.loja_id: FK para comum.Loja (ON DELETE RESTRICT)
  - Sempre gravar loja_id nas transações (aprovadas e negadas)
- **Integração Pinbank**: Criar transação via `BaseTransacoesGestao.criar_transacao_checkout()`
- **Documentação**: Manter `docs/4. link_pagamento.md` atualizado

### 28. SISTEMA DE AUTORIZAÇÃO DE USO DE SALDO NO POS:
- **Fluxo Completo**: Validação senha → Solicitação → Push notification → Aprovação cliente → Débito
- **Segurança Auth Tokens**:
  - Redis armazena tokens temporários (15min) após validação de senha
  - `cliente_id` extraído do token (nunca aceito da requisição)
  - Validação: token existe? expirou? terminal correto? valor <= saldo?
- **Model AutorizacaoUsoSaldo**:
  - Status: `PENDENTE` → `APROVADO`/`NEGADO` → `CONCLUIDA`/`ESTORNADA`/`EXPIRADO`
  - Expiração: 180 segundos (3 minutos)
  - Bloqueio de saldo apenas após aprovação do cliente
- **Endpoints POSP2** (OAuth POSP2):
  - `validar_senha_e_saldo` - Valida senha + retorna saldo + auth_token
  - `solicitar_autorizacao_saldo` - Cria autorização + envia push (requer auth_token)
  - `verificar_autorizacao` - Polling de status (POST)
  - `debitar_saldo_transacao` - Debita saldo bloqueado após aprovação
  - `finalizar_transacao_saldo` - Confirma transação
  - `estornar_saldo_transacao` - Estorna em caso de falha
- **Endpoints Cliente** (JWT):
  - `aprovar_uso_saldo` - Cliente aprova no app
  - `negar_uso_saldo` - Cliente nega no app
  - `verificar_autorizacao` - Cliente verifica status da autorização
- **Formato de Resposta Padrão**:
  - `{"sucesso": bool, "mensagem": str, ...}` (NUNCA `success`/`error`/`data`)
  - Campos diretos no root: `status`, `valor_bloqueado`, `pode_processar`
- **Lógica `pode_processar`**:
  - `PENDENTE`: `true` (cliente pode aprovar no app)
  - `APROVADO`: `true` (POS pode debitar se não expirou)
  - `NEGADO`/`EXPIRADO`/`CONCLUIDA`/`ESTORNADA`: `false`
- **Bloqueio de Saldo**:
  - `valor_bloqueado`: `null` quando status = `PENDENTE`
  - `valor_bloqueado`: `<valor>` após aprovação (status = `APROVADO`)
  - Saldo bloqueado em `conta.saldo_bloqueado` para prevenir double-spending
- **Push Notification**:
  - Enviado automaticamente ao criar autorização
  - Template dinâmico do banco (`templates_envio_msg`)
  - Firebase Service com método core `_enviar_client_id_push_core()`
- **Auditoria**: Todos os endpoints usam `registrar_log()` com nível apropriado

### 47. SISTEMA DE CACHE REDIS (IMPLEMENTADO):
- **Infraestrutura Docker**: Redis 7-alpine em network isolada
- **Configuração de Rede**:
  - Network: `wallclub-network` (bridge)
  - Redis IP fixo: `172.18.0.2` (não muda enquanto network existir)
  - Django IP: `172.18.0.3`
  - Sem port mapping (segurança - apenas comunicação interna)
- **Settings Django**:
  - Backend: `django.core.cache.backends.redis.RedisCache`
  - Location: `redis://172.18.0.2:6379/1`
  - Fallback automático para `LocMemCache` se Redis indisponível
  - Teste de ping no startup para selecionar backend
- **Pacotes Necessários**:
  - `redis==5.0.1`
  - `django-redis==5.4.0`
- **Uso no Código**:
  ```python
  from django.core.cache import cache
  
  # Armazenar dados temporários
  cache.set('chave', valor, timeout=900)  # 15 minutos
  
  # Recuperar dados
  dados = cache.get('chave')
  
  # Deletar
  cache.delete('chave')
  ```
- **Casos de Uso Implementados**:
  - Auth tokens POSP2 (15 minutos de validade)
  - Sessões temporárias de autenticação
  - Dados de validação de senha + saldo
- **Persistência**: Volume `redis_data` para persistência AOF (Append-Only File)
- **Deploy**: Redis criado uma vez, Django rebuilda normalmente
- **Status**: ✅ Produção com RedisCache funcionando

### 48. MENU LATERAL RESPONSIVO NOS PORTAIS (IMPLEMENTADO):
- **Arquitetura Dual**: Menu lateral fixo (desktop) + Hamburguer (mobile)
- **Breakpoint**: 992px (Bootstrap lg) - transforma layout automaticamente
- **Desktop (≥992px)**:
  - Sidebar fixo 280px à esquerda (`.sidebar-desktop d-none d-lg-block`)
  - Menu sempre visível sem hamburguer
  - Layout flex: `body { display: flex; height: 100vh; overflow: hidden; }`
  - Content area: `margin-left: 280px`, scroll vertical independente
  - Header da sidebar: logo + nome do usuário/portal
- **Mobile (<992px)**:
  - Navbar fixa no topo com hamburguer (`.navbar-mobile d-lg-none`)
  - Offcanvas slide-in (`.offcanvas d-lg-none`)
  - Content: `padding-top: 70px`

### 49. SISTEMA DE AUTORIZAÇÃO DE USO DE SALDO - COMPLETO (10/10/2025):
- **Fluxo Implementado**: Validação → Autorização → Aprovação → Débito → Estorno
- **Débito Automático**: Método `debitar_saldo_autorizado(autorizacao_id, nsu_transacao)` validado
  - Chamado automaticamente após INSERT em `transactiondata` (se `autorizacao_id` presente)
  - Usa `@transaction.atomic` + `select_for_update()` (lock pessímista)
  - Valida `pode_debitar()` (status='APROVADO' + não expirado)
  - Libera `saldo_bloqueado` após débito
  - Atualiza status → 'CONCLUIDA'
  - Registra `nsu_transacao` + `movimentacao_debito_id`
- **Negação com Liberação**: Método `negar_autorizacao()` refatorado
  - Aceita negar PENDENTE ou APROVADO
  - Libera `saldo_bloqueado` se estava APROVADO (cliente mudou de ideia)
  - Valida expiração antes de processar
  - Retorna `{"bloqueio_liberado": bool}` no response
- **Expiração Automática**: Django command criado
  - Arquivo: `apps/conta_digital/management/commands/expirar_autorizacoes_saldo.py`
  - Execução: `python manage.py expirar_autorizacoes_saldo --verbose`
  - Cron: `* * * * * docker exec wallclub-prod-release300 python manage.py expirar_autorizacoes_saldo`
  - Busca PENDENTE/APROVADO expirados, libera bloqueios, marca como EXPIRADO
- **Slip de Impressão**: Campo `saldo_usado` adicionado
  - Busca valor via `AutorizacaoService.verificar_autorizacao(autorizacao_id)`
  - Exibido abaixo de "Valor do desconto CLUB"
  - Só aparece quando `autorizacao_id` presente E aprovado
  - Formato: "Saldo utilizado de cashback: R$ XX,XX"
- **Timezone**: Todas as ocorrências de `timezone.now()` substituídas por `datetime.now()`
- **Arquivos**:
  - `apps/conta_digital/services_autorizacao.py` - Métodos corrigidos
  - `posp2/services_transacao.py` - Débito após INSERT + campo saldo_usado
  - `apps/conta_digital/management/commands/expirar_autorizacoes_saldo.py` - Command criado
  - Sidebar desktop oculto automaticamente
- **Estilo Padronizado**:
  - Gradient azul: `--primary-color: #0f2a5a` → `--secondary-color: #1a4480`
  - Nav-link hover/active: `background: rgba(255,255,255,0.1)` + `transform: translateX(5px)`
  - Logout separado: `border-top: 1px solid rgba(255,255,255,0.1)`
- **Portais Implementados**:
  - ✅ Portal Vendas: `portais/vendas/templates/vendas/base.html`
  - ✅ Portal Lojista: `portais/lojista/templates/portais/lojista/base.html`
- **CSS Específico**: Cada portal tem CSS próprio (lojista.css, vendas.css)
- **Media Queries Obrigatórias**:
  ```css
  @media (min-width: 992px) {
    .sidebar-desktop { display: block; }
    .navbar-mobile { display: none; }
    .main-content { margin-left: 280px; height: 100vh; overflow-y: auto; }
  }
  @media (max-width: 991px) {
    .sidebar-desktop { display: none; }
    .main-content { margin-top: 70px; }
  }
  ```

### 50. CORREÇÕES DE DÉBITO DE SALDO E CÁLCULO COM SALDO USADO (11/10/2025):
- **Bug Corrigido**: `ContaDigitalService.debitar()` retorna objeto, não dict
  - `apps/conta_digital/services_autorizacao.py` linha 316
  - Antes: `resultado['movimentacao']['id']` (erro: object is not subscriptable)
  - Depois: `movimentacao.id` (correto)
  - Acesso direto aos atributos: `.saldo_anterior`, `.saldo_posterior`, `.id`
- **Propagação de autorizacao_id**: Adicionado ao dict `dados_trdata`
  - `posp2/services_transacao.py` linha 191-192
  - Permite `_gerar_slip_impressao()` buscar saldo usado
  - Campos propagados: `autorizacao_id`, `modalidade_wall`
- **Cálculo com Saldo Usado**: Valores ajustados no slip de impressão
  - `vdesconto_final = parte0 - saldo_cashback_usado`
  - `vparcela_ajustado = vdesconto_final / parcelas`
  - Aplicado em 3 seções: PIX/DÉBITO, PARCELADO (desconto>=0), PARCELADO (desconto<0)
  - Logs de debug: linha 788-789
- **Campo cards_principais**: Adicionado ao retorno de `simular_parcelas()`
  - `posp2/services.py` linha 380
  - Retorna: `"cards_principais": [3, 6, 10, 12]` (hardcoded)
  - Valores representam opções de parcelamento destacadas
  - Pode conter: "DEBITO", "PIX", "A VISTA", ou números 2-12
- **Arquivos Modificados**:
  - `apps/conta_digital/services_autorizacao.py` (linhas 314-348)
  - `posp2/services_transacao.py` (linhas 183-193, 766-789, 830, 852, 873)
  - `posp2/services.py` (linha 380)
  - `curls_teste/posp2.txt` (linha 75)

### 51. SISTEMA DE TRANSAÇÕES PINBANK - PADRÕES (14/10/2025):
- **Serviços Separados**:
  - `pinbank/services_transacoes_pagamento.py` - Transações com cartão (direto e tokenizado)
  - `pinbank/services_consulta_apps.py` - Consultas de extrato e comprovante
  - `pinbank/services.py` - Integração base e autenticação
- **Endpoints Implementados**:
  - `efetuar_transacao_cartao()` - Transação com dados completos do cartão (EfetuarTransacaoEncrypted)
  - `efetuar_transacao_cartao_tokenizado()` - Transação com CartaoId do Pinbank (EfetuarTransacaoCartaoIdEncrypted)
  - `incluir_cartao_tokenizado()` - Tokenização de cartão (IncluirCartaoEncrypted)
  - `consulta_dados_cartao_tokenizado()` - Consulta cartão salvo
- **FormaPagamento Automático**:
  - **1 parcela**: `FormaPagamento = "1"` (crédito à vista)
  - **2-12 parcelas**: `FormaPagamento = "2"` (parcelado)
  - Lógica aplicada em ambos métodos: `forma_pagamento = '1' if qtd_parcelas == 1 else '2'`
- **Valor em Centavos**:
  - **Backend**: Sempre multiplicar por 100 antes de enviar ao Pinbank
  - **Cálculo**: `Valor = int(dados.get('valor') * 100)`
  - **Exemplo**: R$ 10.50 → 1050 centavos
- **Simulação de Parcelas**:
  - **PIX**: Comentado (não usado no checkout)
  - **DÉBITO**: Comentado (não usado no checkout)
  - **CRÉDITO 1x**: À vista sem juros
  - **PARCELADO 2-12x**: Sem juros (CalculadoraDesconto)
  - Arquivo: `checkout/services.py` - método `simular_parcelas()`
- **Estrutura de Payload**:
  ```python
  # EfetuarTransacaoEncrypted (cartão direto)
  {
    "Data": {
      "CodigoCanal": int,
      "CodigoCliente": int,
      "KeyLoja": str,
      "NomeImpresso": str,
      "DataValidade": str,  # MM/YY
      "NumeroCartao": str,
      "CodigoSeguranca": str,
      "Valor": int,  # Centavos
      "FormaPagamento": str,  # "1" ou "2"
      "QuantidadeParcelas": int,
      "DescricaoPedido": str,
      "IpAddressComprador": str,
      "CpfComprador": str | int,
      "NomeComprador": str,
      "TransacaoPreAutorizada": bool
    }
  }
  
  # EfetuarTransacaoCartaoIdEncrypted (cartão tokenizado)
  {
    "Data": {
      "CodigoCanal": int,
      "CodigoCliente": int,
      "KeyLoja": str,
      "CartaoId": str,  # Token Pinbank
      "Valor": int,  # Centavos
      "FormaPagamento": str,  # "1" ou "2"
      "QuantidadeParcelas": int,
      "DescricaoPedido": str,
      "IpAddressComprador": str,
      "CpfComprador": str | int,
      "NomeComprador": str,
      "TransacaoPreAutorizada": bool
    }
  }
  ```
- **Erros Comuns Resolvidos**:
  - `ParseInt32` error: Causado por strings em campos numéricos - usar conversão explícita `int()`
  - Valor incorreto: Sempre enviar em centavos (multiplicar por 100)
  - FormaPagamento fixo: Deve variar com quantidade de parcelas
  - CPF/CNPJ: **SEMPRE** enviar como `int`, nunca como string (remove zeros à esquerda)
  - NSU e codigo_autorizacao: Extrair de `resultado['dados']`, não direto de `resultado`

### 22. VALORES DE TRANSAÇÃO - CHECKOUT:
- **valor_transacao_original**: Valor digitado pelo usuário (sem desconto)
- **valor_transacao_final**: Valor do pulldown de parcelas (com desconto aplicado)
- **Regra**: Pinbank SEMPRE recebe `valor_transacao_final`
- **Fluxo**:
  ```python
  # Portal Vendas
  valor_original = Decimal(request.POST.get('valor'))  # Digitado
  valor_final = Decimal(request.POST.get('valor_total_parcela'))  # Do pulldown
  
  # Link de Pagamento  
  valor_original = token_obj.item_valor  # Token
  valor_final = serializer.validated_data.get('valor_total')  # Do pulldown
  
  # Service
  CheckoutService.processar_pagamento_cartao_tokenizado(
      valor=valor_final,  # Pinbank usa este
      valor_transacao_original=valor_original,
      valor_transacao_final=valor_final
  )
  ```

### 23. FORMATO DE PARCELAS NO PULLDOWN:
- **Formato Padrão**: `3x de R$ 30,00 (s/juros) - Valor Total: R$ 90,00`
- **Com Cashback**: `3x de R$ 30,00 (s/juros) - Valor Total: R$ 90,00 (cashback R$ 5,00)`
- **Regra**: Cashback só aparece se > 0
- **Dados no option**:
  ```javascript
  option.dataset.valorDesconto = dados.valor_desconto;  // Valor total
  option.dataset.cashback = dados.cashback || 0;
  ```

### 24. EMAIL BACKEND - DESENVOLVIMENTO:
- **Desenvolvimento**: Comentado em `wallclub/settings/development.py`
  - Por padrão usa AWS SES (definido em base.py)
  - Para testar sem enviar: descomentar `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'`
- **Produção**: `EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'`
  - Envia via AWS SES
  - Requer credenciais AWS configuradas
- **Arquivo**: `wallclub/settings/development.py`

### 25. LINKPAGAMENTOSERVICE - ARQUITETURA REFATORADA (2025-10-14):
- **Local**: `checkout/link_pagamento_web/services.py`
- **Classe**: `LinkPagamentoService`
- **Método Principal**: `processar_checkout_link_pagamento()`
  - **Parâmetros**:
    - `token`: Token do checkout
    - `dados_cartao`: Dict com numero_cartao, cvv, data_validade, bandeira
    - `dados_sessao`: Dict com cpf, nome, celular, endereco, parcelas, tipo_pagamento, valor_total, salvar_cartao
    - `ip_address`: IP do cliente
    - `user_agent`: User agent do cliente
  - **Retorno**: Dict com sucesso, transacao_id, nsu, codigo_autorizacao, mensagem, tentativas_restantes

- **Função Utilitária**: `sanitize_for_json(obj)`
  - Converte `Decimal` para `float` recursivamente
  - **CRÍTICO**: JSONField não serializa Decimal automaticamente
  - Aplicar antes de salvar `pinbank_response` em models

- **View Refatorada**: `ProcessarCheckoutView`
  - **Antes**: ~250 linhas com lógica de negócio
  - **Depois**: ~50 linhas (apenas orquestração)
  - **Padrão**: View valida → prepara dados → chama service → retorna Response
  - **Zero manipulação direta de models na view**

- **Bug Corrigido**: `valor_total` não preenchido automaticamente
  - **Solução**: JavaScript atualiza campo ao selecionar bandeira
  - **Arquivo**: `checkout/templates/checkout/checkout.html`

- **Serialização JSON**:
  ```python
  # SEMPRE aplicar sanitize_for_json ao salvar pinbank_response
  transacao.pinbank_response = sanitize_for_json(resultado_transacao)
  
  # SEMPRE converter Decimal no retorno de services
  return {
      'valor_original': float(valor_original),
      'valor_final': float(valor_final)
  }
  ```

- **Arquivos Modificados**:
  - `checkout/link_pagamento_web/services.py` (novo arquivo, 251 linhas)
  - `checkout/link_pagamento_web/views.py` (refatorado, ProcessarCheckoutView)
  - `checkout/templates/checkout/checkout.html` (bug valor_total)
  - `wallclub/settings/development.py` (EMAIL_BACKEND comentado)

### 53. SISTEMA DE AUDITORIA CENTRALIZADO (17/10/2025):
**Localização**: `comum/services/auditoria_service.py` (570 linhas) - **CENTRALIZADO**

**Migração**: `apps/cliente/services_security.py` **DEPRECADO** (redireciona para service central)

**Componentes**:
- **Model**: `AuditoriaValidacaoSenha` (tabela `cliente_auditoria_validacao_senha`)
- **Service**: `AuditoriaService` centralizado com 8 métodos
- **Padrão de Logs**: `auditoria.XX` (6 tipos de log)
- **Integrações**: POS, middleware, validador CPF, estrutura organizacional

**Métodos Implementados**:

1. **Auditoria de Login** (migrado de services_security.py):
   - `registrar_tentativa_login()` - Toda tentativa registrada (sucesso/falha)
   - `verificar_bloqueio()` - Validação CPF/IP bloqueado
   - `obter_estatisticas_cpf()` - Estatísticas por CPF (taxa sucesso, IPs)
   - `obter_tentativas_suspeitas()` - Detecção de padrões de ataque
   - **Bloqueio**: 5 falhas/15min → bloqueio 30min (Redis cache)
   - **Integração**: Atualiza `cliente_auth` automaticamente

2. **Auditoria de Transações** (novo):
   - `registrar_transacao()` - Criação, cancelamento, estorno, alterações
   - Campos: transacao_id, usuario_id, valor_anterior/novo, status_anterior/novo, motivo, ip
   - **Integrado com POS**: `posp2/services_transacao.py`

3. **Auditoria de Usuários** (novo):
   - `registrar_usuario()` - CRUD, mudança perfil/permissões
   - Campos: usuario_id, executado_por, dados_alterados, ip

4. **Auditoria de Configurações** (novo):
   - `registrar_configuracao()` - Parâmetros Wall, regras antifraude, blacklist
   - Campos: tipo, config_id, usuario_id, valor_anterior/novo, descricao

5. **Auditoria de Dados Sensíveis** (novo):
   - `registrar_dados_sensiveis()` - CPF, email, telefone, senha
   - **Mascaramento automático**: `123.***.**-00`, `a***@email.com`, `(11) *****-1234`
   - Campos: tipo, cliente_id, campo, executado_por, ip

**Padrão de Logs (auditoria.XX)**:
```python
# Arquivos gerados em logs/
auditoria.login.log              # Login/senha/bloqueios
auditoria.transacao.log          # Transações POS/financeiras
auditoria.usuario.log            # Usuários/permissões
auditoria.configuracao.log       # Canal/Loja/Regional/Parâmetros
auditoria.dados_sensiveis.log    # CPF/email/telefone/senha (mascarado)
auditoria.middleware.log         # API requests/rate limit/exceptions
```

**Uso (Import Centralizado)**:
```python
from comum.services.auditoria_service import AuditoriaService

# Login: Verificar bloqueio
bloqueado, motivo, tempo = AuditoriaService.verificar_bloqueio(
    cpf=cpf_limpo, ip_address=ip_address
)

# Login: Registrar tentativa
AuditoriaService.registrar_tentativa_login(
    cpf=cpf_limpo,
    sucesso=False,
    ip_address=ip_address,
    canal_id=canal_id,
    endpoint='/api/v1/cliente/login/',
    cliente_id=cliente.id,
    motivo_falha='senha_incorreta'
)

# Transação: Registrar criação
AuditoriaService.registrar_transacao(
    acao='criacao',
    transacao_id=nsu,
    usuario_id=0,
    valor_novo=100.50,
    status_novo='APROVADA',
    motivo='Transação POS - Terminal: 12345',
    ip_address=None
)

# Dados Sensíveis: Registrar alteração CPF
AuditoriaService.registrar_dados_sensiveis(
    tipo='cpf',
    cliente_id=123,
    campo='cpf',
    valor_anterior='12345678900',
    valor_novo='98765432100',
    executado_por=1,
    ip_address='192.168.1.1'
)
# Log gerado: "Cliente 123 - Campo cpf alterado" (valores mascarados)
```

**Configurações**:
- `MAX_TENTATIVAS_FALHAS = 5`
- `JANELA_TEMPO_MINUTOS = 15`
- `TEMPO_BLOQUEIO_MINUTOS = 30`

**Rate Limiting Coordenado**:
- Rate limit global: 6 req/min (permite 5 falhas + 1 margem)
- Auditoria: bloqueio após 5 falhas
- Trabalham em conjunto sem conflito

**Compliance**:
- Histórico completo para auditoria
- Rastreabilidade de todas tentativas
- Análise de padrões suspeitos
- Conformidade LGPD/PCI-DSS

**Arquivos**:
- `comum/services/auditoria_service.py` - Service centralizado (570 linhas) ✅
- `apps/cliente/services_security.py` - DEPRECADO (redireciona para service central)
- `comum/models.py` - Model AuditoriaValidacaoSenha
- `posp2/services_transacao.py` - Integrado com AuditoriaService
- `comum/middleware/security_middleware.py` - Usa auditoria.middleware
- `comum/seguranca/validador_cpf.py` - Usa auditoria.dados_sensiveis
- `comum/estr_organizacional/*.py` - Usa auditoria.configuracao (Canal, Loja, Regional, GrupoEconomico)
- `scripts/producao/criar_tabela_auditoria.sql` - Script SQL
- `wallclub/settings/base.py` - API_RATE_LIMITS ajustado

**Registro no Banco (log_parametros)**:
```sql
INSERT INTO log_parametros (processo, ligado, nivel, arquivo_log, descricao)
VALUES ('auditoria.middleware', 1, 'DEBUG', 'auditoria.middleware.log', 'API requests/rate limit');
-- + 5 outros registros (login, transacao, usuario, configuracao, dados_sensiveis)
```

### 54. MOVIMENTAÇÕES CONTA DIGITAL - FLUXO SIMPLIFICADO (15/10/2025):
- **Sistema Unificado**: Apenas 2 tipos de movimentações por transação POS
- **Método Removido**: `ContaDigitalService.criar_lancamentos_transacao_pos()` (duplicava cashback)
  - Criava 4 lançamentos redundantes (crédito cartão, desconto, débito compra, cashback)
  - Gerava duplicação de cashback junto com `CashbackService.concessao_cashback()`
  - Removido de `apps/conta_digital/services.py` (linhas 780-949)
  - Chamada removida de `posp2/services_transacao.py` (linhas 354-378)

- **Fluxo Atual (Simplificado)**:

### 55. VALIDAÇÃO CPF + DECORATORS POSP2 + TEMPLATES WHATSAPP/SMS (16/10/2025):
**Localização**: `comum/seguranca/` + `posp2/views.py` + `templates_envio_msg`

**Componentes**:
1. **ValidadorCPFService** (`comum/seguranca/validador_cpf.py`, 227 linhas):
   - Validação dígitos verificadores (algoritmo mod-11)
   - Blacklist CPF (tabela `blacklist_cpf`)
   - Cache Redis 24h para CPFs válidos
   - Método: `validar_cpf_completo(cpf, usar_cache=True)`

2. **Model BlacklistCPF** (`comum/seguranca/models.py`, 91 linhas):
   - Campos: cpf, motivo, bloqueado_por, ativo
   - Métodos: `adicionar()`, `remover()`, `verificar()`, `listar_ativos()`
   - Índices: cpf (UNIQUE), ativo, created_at

3. **Decorators API** (`comum/decorators/api_decorators.py`):
   - `@handle_api_errors`: Trata exceções de forma padronizada
   - `@validate_required_params(*params)`: Valida parâmetros obrigatórios
   - Aplicados em 13 endpoints POSP2

4. **Integração POSP2** (`posp2/services.py`):
   - `valida_cpf()` agora valida blacklist antes de processar
   - Retorna: `{"sucesso": false, "mensagem": "cpf_bloqueado", "dados": {"mensagem_cliente": "motivo"}}`

**Templates WhatsApp/SMS Padronizados**:
- **senha_acesso**: Envio de senha (reset, cadastro, POS)
  - WhatsApp: `senha_de_acesso_wallclub` (Facebook)
  - SMS: "Seu código de verificação é {senha}..."
  - Parâmetros: `["senha"]`

- **baixar_app**: Convite para baixar app
  - WhatsApp: `baixar_app_wallclub` (Facebook)
  - SMS: "Baixe o app Wall Club..."
  - Parâmetros: `[]` (sem variáveis)

**Fluxos de Mensagens**:
- **Reset de senha**: `senha_acesso` (WhatsApp + SMS)
- **Cadastro manual**: `senha_acesso` (WhatsApp + SMS)
- **Cadastro POS**: `senha_acesso` + `baixar_app` (2 mensagens)

**Melhorias WhatsAppService** (`comum/integracoes/whatsapp_service.py`):
- `.strip()` em facebook_url e facebook_token (previne espaços)
- Uso correto de `templates_envio_msg.mensagem` (nome no Facebook)

**Endpoints Refatorados (POSP2)**:
- ~90 linhas de validações manuais removidas
- 13 endpoints com decorators aplicados
- Código mais limpo e manutenível

**Arquivos Modificados**:
- `comum/seguranca/validador_cpf.py` (novo)
- `comum/seguranca/models.py` (novo)
- `posp2/views.py` (13 endpoints refatorados)
- `posp2/services.py` (integração blacklist)
- `apps/cliente/services.py` (templates padronizados)
- `comum/integracoes/whatsapp_service.py` (.strip())
- `comum/integracoes/messages_template_service.py` (correção)
- SQL: `scripts/producao/criar_tabela_blacklist_cpf.sql`

**Commit**: `f7d3be4` - feat: Implementa validação CPF + decorators POSP2
  1. **CRÉDITO Cashback** (se `cashback_concedido > 0`):
     - Método: `CashbackService.concessao_cashback()` → `ContaDigitalService.creditar_cashback_transacao_pos()`
     - Tabela: `MovimentacaoContaDigital`
     - Campo: `cashback_bloqueado` (não `saldo_atual`)
     - Tipo: `CASHBACK_CREDITO`
     - Status: `RETIDO`
     - Retenção: **30 dias hardcoded** (`CashbackService.DIAS_RETENCAO`)
     - Data Liberação: `datetime.now() + timedelta(days=30)`
     - Arquivo: `posp2/services_conta_digital.py` (linhas 473-548)
  
  2. **DÉBITO Uso de Saldo** (se `autorizacao_id` presente):
     - Método: `AutorizacaoService.debitar_saldo_autorizado()`
     - Tabela: `MovimentacaoContaDigital`
     - Campo: `cashback_disponivel` (saldo já liberado)
     - Tipo: `DEBITO_SALDO`
     - Status: `PROCESSADA`
     - Referência: NSU da transação
     - Lock: Pessimista (`select_for_update()`)
     - Arquivo: `apps/conta_digital/services_autorizacao.py`

- **Processamento em TRDataService**:
  - Linha 308-330: Determina `modalidade_wall` (S/N) baseado em cadastro do cliente
  - Linha 535-583: Concede cashback via `CashbackService.concessao_cashback()` se `cashback_concedido > 0`
  - Linha 1194-1221: Debita saldo autorizado via `AutorizacaoService.debitar_saldo_autorizado()` se `autorizacao_id` presente
  - NÃO cria mais 4 lançamentos de crédito/débito/desconto (removido)

- **Benefícios**:
  - [✓] Elimina duplicação de cashback
  - [✓] Fluxo claro e direto (1 movimento por ação)
  - [✓] Retenção automática de 30 dias
  - [✓] Liberação automática após período
  - [✓] Logs detalhados de todas as etapas

- **Arquivos Modificados**:
  - `apps/conta_digital/services.py` (método criar_lancamentos_transacao_pos removido)
  - `posp2/services_transacao.py` (linhas 308-330 simplificadas, chamada removida)

### 54. WALLCLUB RISK ENGINE - SISTEMA ANTIFRAUDE (16/10/2025):
**Localização**: Projeto separado `/wallclub-riskengine/` (porta 8004)

**Arquitetura**:
- **Container Independente**: Deploy separado do monolito principal
- **Banco Compartilhado**: MySQL wallclub (mesmas tabelas)
- **Cache Compartilhado**: Redis DB 2 (isolado do principal)
- **Comunicação**: HTTP entre apps (callback após revisão)

**Tabelas Criadas** (script SQL):
1. **antifraude_transacao_risco**: Dados normalizados de POS/App/Web
   - Campos: transacao_id, origem (POS/APP/WEB), cliente_id, cpf, valor, modalidade
   - Device tracking: ip_address, device_fingerprint, user_agent
   - Cartão: bin_cartao (6 dígitos), bandeira
   - Contexto: loja_id, canal_id, terminal
   - Índices otimizados: cpf+data, ip+data, device+data, bin+data

2. **antifraude_regra**: Regras configuráveis
   - Tipos: VELOCIDADE, VALOR, LOCALIZACAO, DISPOSITIVO, HORARIO, CARTAO, CUSTOM
   - Configuração JSON: `parametros` (ex: `{"max_transacoes": 3, "janela_minutos": 10}`)
   - Peso: 1-10 (impacto no score)
   - Ação: APROVAR, REPROVAR, REVISAR, ALERTAR
   - Prioridade: 1-100 (ordem de execução)

3. **antifraude_decisao**: Decisões do motor
   - Score: 0-100 (quanto maior, mais arriscado)
   - Decisão: APROVADO (<50), REVISAO (50-80), REPROVADO (>80)
   - Revisão manual: revisado_por, revisado_em, observacao_revisao
   - Performance: tempo_analise_ms

**Services Implementados**:
1. **ColetaDadosService**: Normaliza dados de diferentes origens
   - `normalizar_transacao_pos()` - Terminal físico
   - `normalizar_transacao_app()` - App móvel (extrai IP, User-Agent, device_fingerprint)
   - `normalizar_transacao_web()` - Checkout web
   - `registrar_transacao()` - Salva no banco

2. **AnaliseRiscoService**: Motor de decisão
   - `analisar_transacao()` - Executa todas regras ativas
   - Cálculo score: `peso * 10` por regra acionada (máx 100)
   - Decisão automática baseada em score e ações das regras
   - Notifica equipe se REVISAO necessária

3. **NotificacaoService**: Alertas de revisão
   - Email para NOTIFICACAO_EMAIL
   - Slack para SLACK_WEBHOOK_URL (opcional)
   - Callback para app principal após revisão manual

**Regras Implementadas** (5 básicas):
1. **Velocidade Alta** (peso 8, REVISAR): >3 transações/10min mesmo CPF
2. **Valor Suspeito** (peso 7, REVISAR): Valor 3x maior que média do cliente
3. **Dispositivo Novo** (peso 5, ALERTAR): Primeiro uso do device_fingerprint
4. **Horário Incomum** (peso 4, ALERTAR): Transações 00h-05h
5. **IP Suspeito** (peso 9, REVISAR): >5 CPFs diferentes no mesmo IP/24h

**Fluxo de Revisão Manual**:
1. **Transação suspeita** → Score alto → REVISAO
2. **Sistema notifica** → Email + Slack
3. **Dashboard**: `GET /api/antifraude/revisao/pendentes/`
4. **Analista decide**:
   - Aprovar: `POST /api/antifraude/revisao/{id}/aprovar/`
   - Reprovar: `POST /api/antifraude/revisao/{id}/reprovar/`
5. **Callback** → App principal processa ou cancela

**Endpoints API**:
- `POST /api/antifraude/analisar/` - Análise em tempo real (<200ms)
- `GET /api/antifraude/decisao/{transacao_id}/` - Consulta decisão
- `GET /api/antifraude/historico/{cliente_id}/` - Histórico do cliente
- `GET /api/antifraude/revisao/pendentes/` - Lista aguardando revisão
- `POST /api/antifraude/revisao/{id}/aprovar/` - Aprova transação
- `POST /api/antifraude/revisao/{id}/reprovar/` - Reprova transação
- `GET /api/antifraude/revisao/historico/` - Histórico de revisões

**Integração com App Principal**:
```python
# App principal envia para análise
response = requests.post(
    'http://wallclub-riskengine:8004/api/antifraude/analisar/',
    json={...}
)

if decisao['decisao'] == 'APROVADO':
    processar_pagamento()
elif decisao['decisao'] == 'REPROVADO':
    bloquear_transacao()
else:  # REVISAO
    marcar_pendente_revisao()
```

**Deploy**:
- Container: `wallclub-riskengine:v1.0`
- Porta: 8004
- Network: `wallclub-network` (compartilhada)
- Recursos: 512MB RAM, 0.5 CPU
- Restart: always

**Documentação**: `/wallclub-riskengine/docs/engine_antifraude.md`

---

## IMPLEMENTAÇÕES RECENTES (OUTUBRO/2025)

### CHECKOUT WEB - LINK DE PAGAMENTO
- **Módulo:** `checkout/link_pagamento_web/`
- **Service Principal:** `CheckoutLinkPagamentoService` (334 linhas)
- **Funcionalidades:**
  - Geração links pagamento únicos (UUID)
  - Sessão temporária (30 min)
  - Cálculo descontos tempo real (Pinbank)
  - Tokenização cartões
  - Integração antifraude (Risk Engine)
  - Limite progressivo R$100→R$200→R$500

**APIs Públicas:**
- POST /checkout/criar-link/
- GET /checkout/<token>/
- POST /checkout/<token>/iniciar-sessao/
- POST /checkout/<token>/calcular-desconto/
- POST /checkout/<token>/processar-pagamento/

### CARGAS AUTOMÁTICAS PINBANK
- **Módulo:** `pinbank/cargas_pinbank/`
- **Calculadora:** `calculadora_tef.py` (632 linhas, 130+ variáveis)
- **Tabela Destino:** `baseTransacoesGestao`
- **Auditoria:** Triggers SQL automáticos (INSERT/UPDATE/DELETE)

**Commands:**
```bash
python manage.py processar_carga_tef
python manage.py processar_carga_credenciadora
```

**Campos Críticos:**
- `tipo_operacao` VARCHAR(20) - 'Credenciadora' ou 'Wallet'
- `banco` VARCHAR(10) - 'PIN-TEF' ou 'PIN'

### INTEGRAÇÃO PINBANK - TOKENIZAÇÃO
- **Service:** `TransacoesPinbankService.incluir_cartao_tokenizado()`
- **Endpoint:** `/Transacoes/IncluirCartaoEncrypted`
- **Apelido Auto:** `{codigo_cliente}-{ultimos_4_digitos}`
- **Credenciais:** Dinâmicas por loja (CodigoCanal/CodigoCliente)

### GESTÃO DE TERMINAIS POS (23/10/2025)
**Módulo:** `portais/admin/`

**Funcionalidades:**
- **Cadastro de Terminais:** Associação terminal ↔ loja com validação de duplicatas
- **Validação Ativa:** Não permite cadastrar número de série já ativo (fim=0 ou fim>hoje)
- **Encerramento:** Define timestamp atual (não meia-noite)
- **Campos Timestamp:** `inicio` e `fim` (UNIX timestamp, não datetime)
- **Model:** `posp2.models.Terminal` com `db_table='terminais'` (plural)
- **Métodos Helper:** `set_inicio_date()` e `set_fim_date()` convertem date→timestamp

**Service:** `TerminaisService`
- `criar_terminal()` - Valida duplicatas ativos
- `encerrar_terminal()` - Define `fim = int(datetime.now().timestamp())`
- `obter_lojas_para_select()` - Lista lojas filtradas por canal

**Templates:**
- `/portal_admin/terminais/` - Listagem com ações
- `/portal_admin/terminais/novo/` - Formulário cadastro

### 2FA NO LOGIN DO APP MÓVEL (23/10/2025)
**Localização:** `apps/cliente/`

**Arquitetura:**
- **Service:** `ClienteAuth2FAService` - Lógica de verificação e validação
- **Views:** `views_2fa_login.py` - Endpoints públicos (OAuth)
- **Models:** `DispositivoConfiavel` (comum/seguranca/models.py)
- **OTP:** `AutenticacaoOTP` com validade de 5 minutos

**Fluxo Completo:**
1. Cliente faz login com novo device → Sistema retorna `device_limite_atingido`
2. App solicita código 2FA → Endpoint envia via WhatsApp
3. Cliente valida código → Endpoint troca dispositivo (remove antigos + registra novo)
4. Login completo com novo device confiável (válido 30 dias)

**Endpoints:**
- `POST /api/v1/cliente/2fa/verificar_necessidade/` - Verifica se device precisa 2FA
- `POST /api/v1/cliente/2fa/solicitar_codigo/` - Envia código via WhatsApp (OAuth)
- `POST /api/v1/cliente/2fa/validar_codigo/` - Valida código + registra device
- `POST /api/v1/cliente/dispositivos/trocar_no_login/` - Troca device após validar 2FA
- `GET /api/v1/cliente/dispositivos/meus/` - Lista devices confiáveis (JWT)
- `POST /api/v1/cliente/dispositivos/revogar/` - Revoga device específico (JWT)

**Template WhatsApp:**
- **ID:** `2fa_login_app`
- **Nome Facebook:** `2fa_login_app`
- **Parâmetros:** `["codigo", "url_ref"]` (url_ref = código repetido)
- **Corpo:** "Seu código de verificação é {{1}}. Para sua segurança, não o compartilhe."
- **Botão:** URL fixa ou dinâmica com código

**Regras de Dispositivo:**
- **Limite:** 1 dispositivo por cliente (app móvel)
- **Validade:** 30 dias desde último acesso
- **Troca de senha:** Invalida TODOS dispositivos confiáveis
- **Novo device:** Sempre exige 2FA obrigatório
- **Device expirado:** >30 dias → Exige novo 2FA

**Contextos que Exigem 2FA:**
- `novo_dispositivo` - Device não cadastrado
- `dispositivo_expirado` - >30 dias sem uso
- `alteracao_dados` - Mudança de dados sensíveis
- `transferencia` - Transferências bancárias
- `primeira_transacao_dia` - Primeira transação diária
- `transacao_alto_valor` - Valores >R$ 100

**Response Login com Device Limite:**
```json
{
  "sucesso": false,
  "erro": "device_limite_atingido",
  "mensagem": "Você já possui 1 dispositivo cadastrado",
  "cliente_id": 107,
  "device_existente": {
    "nome_dispositivo": "Android Tablet",
    "ultimo_acesso": "2025-10-23T20:00:00"
  },
  "requer_2fa_para_trocar": true
}
```

**Arquivos Criados/Modificados:**
- `apps/cliente/views_2fa_login.py` - 4 endpoints públicos
- `apps/cliente/views_dispositivos.py` - 3 endpoints autenticados
- `apps/cliente/services_2fa_login.py` - Lógica 2FA (459 linhas)
- `apps/cliente/services.py` - Login retorna dict completo (linha 513-520)
- `comum/seguranca/services_device.py` - Gestão dispositivos
- `comum/seguranca/services_2fa.py` - OTP service
- SQL: Template `2fa_login_app` em `templates_envio_msg`

**Correções Aplicadas:**
- ✅ `device_fingerprint` opcional em solicitar_codigo (troca de celular)
- ✅ Campo `success` em vez de `sucesso` (OTPService)
- ✅ Busca código do banco (não depende de DEBUG mode)
- ✅ Log com device_fingerprint None tratado
- ✅ Template com parâmetros corretos `["codigo", "url_ref"]`
- ✅ `url_ref` recebe código (não URL literal)
- ✅ Response login inclui `cliente_id` no erro device_limite_atingido
- ✅ Validação OTP usando campo `success` correto

### CORREÇÕES CRÍTICAS APLICADAS (23/10/2025)
1. `transaction_id` → `transacao_id` (payload antifraude)
2. `codigo_cliente` → `codigoCliente` (camelCase query)
3. Credenciais hardcoded → dinâmicas
4. Sobrescrição campos com string vazia
5. Event listener bandeira duplicado
6. Método tokenizar_cartao() → incluir_cartao_tokenizado()
7. quantidade_parcelas string→int (FormaPagamento)
8. **Login API:** View retornava apenas `sucesso` e `mensagem`, descartando campos extras
   - Corrigido: retorna dicionário completo do service
   - Erro `device_limite_atingido` agora inclui: `erro`, `mensagem`, `device_existente`, `requer_2fa_para_trocar`
9. **Terminais:** Tabela `terminais` (plural) mapeada corretamente
   - Campo `terminal` adicionado ao model
   - Validação de duplicatas usando tabela correta
   - Timestamp atual no encerramento (não meia-noite)
10. **Portal Admin - Lojas:** Campos `cidade` e `estado` removidos (não existem na tabela)
11. **Portal Admin - Loja Edit:** Funcionalidade completa implementada
    - URL: `/portal_admin/hierarquia/loja/<id>/editar/`
    - Template: `loja_edit.html`
    - Botão de edição na listagem de lojas do grupo
12. **Formulário Loja:** Campo `aceite` removido (sempre criado com 0)

### 67. RELEASE 3.1.0 - AUTENTICAÇÃO COM SENHA (27/10/2025):

**Sistema Completo de Cadastro e Login com Senha:**

**Endpoints de Cadastro (3 etapas):**
1. `POST /api/v1/cliente/cadastro/iniciar/`
   - Verifica se CPF existe
   - Se não existe: consulta Bureau + cria cliente base automaticamente
   - Retorna dados existentes + campos faltantes
   - Request: `{"cpf": "12345678900", "canal_id": 1}`

2. `POST /api/v1/cliente/cadastro/finalizar/`
   - Salva dados do cadastro (nome, email, celular, senha)
   - Valida senha forte (8+ caracteres, letras + números)
   - Envia OTP via WhatsApp (template `2fa_login_app`)
   - Request: `{"cpf", "canal_id", "nome", "email", "celular", "senha"}`

3. `POST /api/v1/cliente/cadastro/validar_otp/`
   - Valida OTP (6 dígitos)
   - Marca `cadastro_completo=TRUE`
   - Request: `{"cpf", "codigo", "canal_id"}`

**Endpoints de Reset Senha (2 etapas):**
1. `POST /api/v1/cliente/senha/reset/solicitar/`
   - Envia OTP via WhatsApp
   - Rate limiting: 3 tentativas/hora
   - Request: `{"cpf", "canal_id"}`

2. `POST /api/v1/cliente/senha/reset/validar/`
   - Valida OTP + define nova senha
   - Request: `{"cpf", "codigo", "nova_senha", "canal_id"}`

**Endpoint de Login:**
- `POST /api/v1/cliente/login/`
  - Valida CPF + Senha obrigatório
  - Controle de tentativas Redis: 5/15min, 10/1h, 15/24h
  - Retorna JWT (Access 1 dia + Refresh 30 dias)
  - Request: `{"cpf", "senha", "canal_id", "device_fingerprint"}`

**Endpoint de Refresh Token:**
- `POST /api/v1/cliente/refresh/`
  - Renova Access Token usando Refresh Token
  - Request: `{"refresh_token"}`

**Model Cliente - Novos Campos:**
```python
cadastro_completo = models.BooleanField(default=False)
cadastro_iniciado_em = models.DateTimeField(null=True, blank=True)
cadastro_concluido_em = models.DateTimeField(null=True, blank=True)
```

**Correção Redis Crítica:**
- Problema: Django usava `LocMemCache` (memória local por worker)
- OTP salvo em um worker, validação ocorria em outro worker diferente
- Solução: `settings/base.py` alterado para usar hostname `wallclub-redis`
- `connection_pooling.py` LOCATION: `redis://wallclub-redis:6379/1`
- Era: IP fixo `172.18.0.2` (errado, IPs mudam)
- Agora: `RedisCache` funcionando corretamente

**Controle de Tentativas de Login:**
- Implementado em `apps/cliente/services_login_attempts.py`
- Redis cache keys: `login_attempts_{cpf}_{periodo}`
- Períodos: 15min, 1h, 24h
- Bloqueio automático após limites atingidos

**Alterações JWT:**
- Access Token: 30 dias → 1 dia (mais seguro)
- Refresh Token: 60 dias → 30 dias
- Motivo: Senha agora é obrigatória (não apenas SMS temporário)

**Envio de OTP:**
- SMS removido completamente
- WhatsApp único canal (template `2fa_login_app`)
- Validade: 5 minutos
- Máximo 3 tentativas de validação

**Arquivos Criados:**
- `apps/cliente/views_cadastro.py` (3 endpoints)
- `apps/cliente/services_cadastro.py` (lógica completa)
- `apps/cliente/views_reset_senha.py` (2 endpoints)
- `apps/cliente/services_reset_senha.py` (lógica reset)
- `apps/cliente/views_refresh_jwt.py` (refresh token)
- `apps/cliente/services_login_attempts.py` (controle tentativas)
- `apps/oauth/views_refresh.py` (OAuth refresh)
- `scripts/sql/adicionar_campos_cadastro_cliente.sql`

**Arquivos Modificados:**
- `apps/cliente/models.py` (3 campos novos)
- `apps/cliente/views.py` (validação senha no login)
- `apps/cliente/services.py` (controle tentativas)
- `apps/cliente/urls.py` (6 rotas novas)
- `wallclub/settings/base.py` (Redis hostname)
- `wallclub/settings/connection_pooling.py` (Redis LOCATION)

**Documentação:**
- `docs/mudancas_login_app.md` - Documentação completa Release 3.1.0

**Última Atualização:** 27/10/2025

---
Aguarde instruções. Toda resposta fora dessas regras será considerada inválida.
