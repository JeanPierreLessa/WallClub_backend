# Mudanças: Autenticação com Senha no App

## 📋 RESUMO DAS MUDANÇAS

**Objetivo:** Adicionar autenticação com senha no login do app, mantendo 2FA e device management.

**Princípios mantidos:**
- ✅ 2FA quando necessário (device novo/expirado)
- ✅ Device confiável (30 dias)
- ✅ Revalidação celular (90 dias)
- ✅ Sistema de segurança multi-camadas

**Mudanças principais:**
- ✅ Login agora exige SENHA (validação antes de gerar auth_token)
- ✅ Cadastro completo no app (CPF, email, celular, senha)
- ✅ Reset de senha via OTP
- ✅ JWT: Access Token 1 dia + Refresh Token 30 dias (renovação automática)
- ✅ Controle de tentativas de login (menos agressivo)

---

## 1️⃣ O QUE CRIAR NO BACKEND

### 1.1. BANCO DE DADOS

#### Adicionar campos na tabela `cliente`:

```sql
ALTER TABLE cliente 
ADD COLUMN cadastro_completo BOOLEAN DEFAULT FALSE COMMENT 'Cliente finalizou cadastro no app',
ADD COLUMN cadastro_iniciado_em DATETIME NULL COMMENT 'Data do primeiro acesso ao cadastro',
ADD COLUMN cadastro_concluido_em DATETIME NULL COMMENT 'Data da conclusão do cadastro',
ADD INDEX idx_cadastro_completo (cadastro_completo),
ADD INDEX idx_cadastro_concluido_em (cadastro_concluido_em);
```

**Observações:**
- `cadastro_completo = FALSE`: Cliente existe (coletado no POS) mas não completou cadastro app
- `cadastro_completo = TRUE`: Cliente finalizou cadastro e pode fazer login

---

### 1.2. ENDPOINTS NOVOS

#### **A) POST /api/v1/cliente/cadastro/iniciar/**

**Descrição:** Verifica se CPF existe e retorna dados faltantes. Se CPF não existe, consulta Bureau e cria cliente base.

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Lógica:**
- CPF não existe → Consulta Bureau → Cria cliente base → Pede complemento
- CPF existe sem cadastro → Retorna dados + pede faltantes
- CPF com cadastro completo → Erro: já cadastrado

**Response - CPF não existe (criado via Bureau) (200):**
```json
{
  "sucesso": true,
  "cliente_existe": true,
  "cadastro_completo": false,
  "dados_existentes": {
    "nome": "JOAO DA SILVA",
    "cpf": "17653377807"
  },
  "dados_necessarios": ["email", "celular", "senha"],
  "mensagem": "Complete seu cadastro"
}
```

**Response - Cliente existe (POS criou) (200):**
```json
{
  "sucesso": true,
  "cliente_existe": true,
  "cadastro_completo": false,
  "dados_existentes": {
    "nome": "JOAO DA SILVA",
    "cpf": "17653377807",
    "celular": "21987654321"
  },
  "dados_necessarios": ["email", "senha"],
  "mensagem": "Complete seu cadastro"
}
```

**Response - Bureau reprova (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF não aprovado pelo Bureau de Crédito. Verifique seus dados."
}
```

**Response - Já cadastrado (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF já cadastrado. Faça login ou recupere sua senha."
}
```

---

#### **B) POST /api/v1/cliente/cadastro/finalizar/**

**Descrição:** Salva dados do cadastro + envia OTP para validação

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request - Cliente novo:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "nome": "João da Silva",
  "email": "joao@email.com",
  "celular": "21987654321",
  "senha": "Senha@123"
}
```

**Request - Cliente existente (só faltam campos):**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "celular": "21987654321",
  "senha": "Senha@123"
}
```

**Validações backend:**
- CPF válido (mod-11)
- Email válido (regex)
- Celular válido (10-11 dígitos)
- Senha forte (mín 8 chars, letra+número)
- CPF não pode estar com `cadastro_completo=TRUE`

**Response (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código de verificação enviado via SMS",
  "celular_mascarado": "(21) 9****-4321"
}
```

**Response - Erro validação (400):**
```json
{
  "sucesso": false,
  "mensagem": "Senha fraca. Use no mínimo 8 caracteres com letras e números."
}
```

---

#### **C) POST /api/v1/cliente/cadastro/validar_otp/**

**Descrição:** Valida OTP + finaliza cadastro (marca `cadastro_completo=TRUE`)

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "codigo": "123456"
}
```

**Lógica backend:**
```python
# 1. Validar OTP (5min validade, 3 tentativas)
# 2. Se válido:
#    - Marcar cadastro_completo = TRUE
#    - Atualizar cadastro_concluido_em = datetime.now()
#    - Revogar OTP usado
# 3. Retornar sucesso
```

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Cadastro concluído com sucesso! Faça login para acessar sua conta."
}
```

**Response - OTP inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 2
}
```

---

#### **D) POST /api/v1/cliente/senha/reset/solicitar/**

**Descrição:** Envia OTP para reset de senha

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Validações backend:**
- CPF deve existir
- Cliente deve ter `cadastro_completo=TRUE`
- Rate limiting: 3 solicitações por hora

**Response (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via SMS para (21) 9****-4321"
}
```

**Response - Cliente não cadastrado (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF não encontrado. Complete seu cadastro primeiro."
}
```

---

#### **E) POST /api/v1/cliente/senha/reset/validar-otp/**

**Descrição:** Valida OTP + permite criar nova senha

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "codigo": "123456",
  "nova_senha": "NovaSenha@456"
}
```

**Validações backend:**
- OTP válido (5min, 3 tentativas)
- Senha forte (8+ chars, letra+número)
- Hash pbkdf2_sha256

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Senha alterada com sucesso! Faça login com a nova senha."
}
```

**Response - OTP inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 1
}
```

---

### 1.3. ENDPOINTS MODIFICADOS

#### **F) POST /api/v1/cliente/login/** (MODIFICAR)

**Mudança:** Adicionar validação de SENHA antes de gerar `auth_token`

**Request ANTES (sem senha):**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Request AGORA (com senha):**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "senha": "Senha@123"
}
```

**Lógica backend:**
```python
# 1. Validar CPF existe
# 2. Verificar cadastro_completo = TRUE
# 3. NOVO: Validar senha com check_password()
# 4. NOVO: Controlar tentativas de login (Redis)
# 5. Se senha válida → Gera auth_token
# 6. Retorna auth_token (fluxo continua igual)
```

**Response - Senha inválida (401):**
```json
{
  "sucesso": false,
  "mensagem": "CPF ou senha incorretos",
  "tentativas_restantes": 4,
  "bloqueado_em": null
}
```

**Response - Conta bloqueada (403):**
```json
{
  "sucesso": false,
  "mensagem": "Conta temporariamente bloqueada por excesso de tentativas. Tente novamente em 15 minutos.",
  "bloqueado_ate": "2025-10-27T21:35:00Z"
}
```

**Response - Cliente não cadastrado (400):**
```json
{
  "sucesso": false,
  "mensagem": "Complete seu cadastro no app antes de fazer login."
}
```

**Response - Senha válida (200):**
```json
{
  "sucesso": true,
  "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-27T21:23:00Z",
  "mensagem": "Credenciais válidas. Use auth_token para verificar 2FA."
}
```

---

#### **G) POST /oauth/refresh/ (CRIAR/MODIFICAR)**

**Descrição:** Renova access token usando refresh token

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Lógica backend:**
```python
# 1. Validar refresh_token contra tabela cliente_jwt_tokens
# 2. Verificar is_active=TRUE e revoked_at=NULL
# 3. Verificar tipo = 'refresh'
# 4. Gerar novo access_token (1 dia)
# 5. Registrar uso do refresh_token
# 6. Retornar novo access_token
```

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-28T21:18:00Z"
}
```

**Response - Refresh inválido (401):**
```json
{
  "sucesso": false,
  "mensagem": "Refresh token inválido ou expirado. Faça login novamente."
}
```

---

### 1.4. CONTROLE DE TENTATIVAS DE LOGIN

**Implementar em Redis:**

```python
# Chaves:
# login_attempts:{cpf} = contador de tentativas
# login_blocked:{cpf} = timestamp do bloqueio

# Regras:
# 5 tentativas em 15 minutos → Bloqueio 15 minutos
# 10 tentativas em 1 hora → Bloqueio 1 hora
# 15 tentativas em 24 horas → Bloqueio manual (análise)
```

**Estrutura:**
```python
class LoginAttemptControl:
    def registrar_tentativa_falha(cpf):
        # Incrementa contador no Redis
        # Verifica se atingiu limites
        # Se sim, bloqueia temporariamente
        pass
    
    def verificar_bloqueio(cpf):
        # Retorna: (bloqueado: bool, tempo_restante: int)
        pass
    
    def limpar_tentativas(cpf):
        # Após login bem-sucedido, zera contador
        pass
```

---

### 1.5. MUDANÇAS NO JWT

**ANTES:**
```python
ACCESS_TOKEN_LIFETIME = timedelta(days=30)
REFRESH_TOKEN_LIFETIME = timedelta(days=60)
```

**AGORA:**
```python
ACCESS_TOKEN_LIFETIME = timedelta(days=1)  # 24 horas
REFRESH_TOKEN_LIFETIME = timedelta(days=30)  # 30 dias
```

**Impacto:**
- Access token expira em 1 dia (mais seguro)
- App deve usar refresh token automaticamente
- Usuário não percebe (renovação transparente)

---

## 2️⃣ O QUE MUDAR NO APP

### 2.1. TELAS NOVAS

#### **A) Tela: CadastroInicial.js**

**Fluxo:**
1. Link "Novo Cliente?" na tela de login
2. Tela pede CPF
3. Chama `/cadastro/iniciar/` → Backend retorna dados necessários
4. Se cliente existe (POS): preenche campos automaticamente
5. Se não existe: formulário completo
6. Campos: Nome, Email, Celular, Senha, Confirmar Senha
7. Botão "Continuar" → Chama `/cadastro/finalizar/`
8. Navega para CadastroValidarOTP

**Componentes:**
- Input CPF com máscara
- Input Email com validação
- Input Celular com máscara
- Input Senha com ícone mostrar/ocultar
- Input Confirmar Senha
- Validações em tempo real
- Loading states

---

#### **B) Tela: CadastroValidarOTP.js**

**Fluxo:**
1. Recebe CPF via navigation params
2. Mostra: "Enviamos um código para (21) 9****-4321"
3. Input OTP 6 dígitos
4. Timer 5 minutos
5. Botão "Reenviar código" (após 60s)
6. Valida OTP → Chama `/cadastro/validar_otp/` 
7. Sucesso → Modal "Cadastro concluído!" → Navega para Login

**Componentes:**
- OTPInput (6 dígitos)
- Timer countdown
- Botão reenviar
- Modal sucesso

---

#### **C) Tela: ResetSenha.js**

**Fluxo:**
1. Link "Esqueci minha senha" na tela de login
2. Pede CPF
3. Botão "Enviar código" → Chama `/senha/reset/solicitar/`
4. Navega para ResetSenhaValidarOTP

**Componentes:**
- Input CPF com máscara
- Validação CPF
- Loading state

---

#### **D) Tela: ResetSenhaValidarOTP.js**

**Fluxo:**
1. Recebe CPF via navigation params
2. Mostra: "Código enviado para (21) 9****-4321"
3. Input OTP 6 dígitos
4. Input Nova Senha
5. Input Confirmar Nova Senha
6. Botão "Alterar Senha" → Chama `/senha/reset/validar-otp/`
7. Sucesso → Modal "Senha alterada!" → Navega para Login

**Componentes:**
- OTPInput
- Input Senha com validação força
- Indicador de força da senha
- Modal sucesso

---

### 2.2. TELAS MODIFICADAS

#### **E) Tela: Login.js (MODIFICAR)**

**Mudanças:**
1. Adicionar campo SENHA
2. Request login agora envia senha
3. Tratar erro senha incorreta + contador tentativas
4. Tratar erro conta bloqueada
5. Adicionar link "Esqueci minha senha"
6. Adicionar link "Novo Cliente?"

**Antes:**
```jsx
// Apenas CPF
<Input placeholder="CPF" />
<Button onPress={handleLogin}>Entrar</Button>
```

**Agora:**
```jsx
<Input placeholder="CPF" />
<Input placeholder="Senha" secureTextEntry />
<Button onPress={handleLogin}>Entrar</Button>
<TouchableOpacity onPress={() => navigate('ResetSenha')}>
  <Text>Esqueci minha senha</Text>
</TouchableOpacity>
<TouchableOpacity onPress={() => navigate('CadastroInicial')}>
  <Text>Novo Cliente?</Text>
</TouchableOpacity>
```

**Tratamento de erros:**
```jsx
// Senha incorreta
if (response.tentativas_restantes) {
  Alert.alert(
    'Senha incorreta',
    `Tentativas restantes: ${response.tentativas_restantes}`
  );
}

// Conta bloqueada
if (response.bloqueado_ate) {
  Alert.alert(
    'Conta bloqueada',
    'Muitas tentativas. Tente novamente em 15 minutos.'
  );
}
```

---

### 2.3. SERVIÇOS (API)

#### **F) api.js (MODIFICAR/ADICIONAR)**

**Adicionar métodos:**

```javascript
// Cadastro
export const iniciarCadastro = async (cpf, canalId) => {
  return ApiClient.post('/cliente/cadastro/iniciar/', { cpf, canal_id: canalId });
};

export const finalizarCadastro = async (dados) => {
  return ApiClient.post('/cliente/cadastro/finalizar/', dados);
};

export const validarOTPCadastro = async (cpf, codigo) => {
  return ApiClient.post('/cliente/cadastro/validar-otp/', { cpf, codigo });
};

// Reset senha
export const solicitarResetSenha = async (cpf, canalId) => {
  return ApiClient.post('/cliente/senha/reset/solicitar/', { cpf, canal_id: canalId });
};

export const validarOTPResetSenha = async (cpf, codigo, novaSenha) => {
  return ApiClient.post('/cliente/senha/reset/validar-otp/', {
    cpf,
    codigo,
    nova_senha: novaSenha
  });
};

// Refresh token
export const refreshAccessToken = async (refreshToken) => {
  return ApiClient.post('/oauth/refresh/', { refresh_token: refreshToken });
};
```

**Modificar método login:**
```javascript
// ANTES
export const login = async (cpf, canalId) => {
  return ApiClient.post('/cliente/login/', { cpf, canal_id: canalId });
};

// AGORA
export const login = async (cpf, senha, canalId) => {
  return ApiClient.post('/cliente/login/', {
    cpf,
    senha,  // NOVO
    canal_id: canalId
  });
};
```

---

#### **G) AuthContext.js (MODIFICAR)**

**Adicionar interceptor para renovação automática:**

```javascript
// Interceptor de resposta para detectar token expirado
ApiClient.interceptors.response.use(
  response => response,
  async error => {
    if (error.response?.status === 401 && error.response?.data?.codigo === 'token_expired') {
      // Token expirado, tentar renovar com refresh token
      const refreshToken = await SecureStore.getItemAsync('refresh_token');
      
      if (refreshToken) {
        try {
          const response = await refreshAccessToken(refreshToken);
          
          if (response.sucesso) {
            // Salvar novo access token
            await SecureStore.setItemAsync('access_token', response.token);
            
            // Repetir requisição original com novo token
            error.config.headers['Authorization'] = `Bearer ${response.token}`;
            return ApiClient.request(error.config);
          }
        } catch (refreshError) {
          // Refresh falhou, deslogar
          await logout();
          return Promise.reject(refreshError);
        }
      } else {
        // Sem refresh token, deslogar
        await logout();
      }
    }
    
    return Promise.reject(error);
  }
);
```

---

### 2.4. NAVEGAÇÃO

#### **H) AppNavigator.js (ADICIONAR)**

```javascript
// Adicionar novas telas
<Stack.Screen 
  name="CadastroInicial" 
  component={CadastroInicial}
  options={{ title: 'Criar Conta' }}
/>
<Stack.Screen 
  name="CadastroValidarOTP" 
  component={CadastroValidarOTP}
  options={{ title: 'Validar Cadastro' }}
/>
<Stack.Screen 
  name="ResetSenha" 
  component={ResetSenha}
  options={{ title: 'Recuperar Senha' }}
/>
<Stack.Screen 
  name="ResetSenhaValidarOTP" 
  component={ResetSenhaValidarOTP}
  options={{ title: 'Nova Senha' }}
/>
```

---

## 3️⃣ RESUMO DE MUDANÇAS

### Backend:
- ✅ 3 campos novos no banco (cadastro_completo, cadastro_iniciado_em, cadastro_concluido_em)
- ✅ 5 endpoints novos (cadastro iniciar/finalizar/validar, reset solicitar/validar)
- ✅ 2 endpoints modificados (login com senha, refresh token)
- ✅ Controle de tentativas de login (Redis)
- ✅ JWT: Access 1 dia + Refresh 30 dias

### App:
- ✅ 4 telas novas (CadastroInicial, CadastroValidarOTP, ResetSenha, ResetSenhaValidarOTP)
- ✅ 1 tela modificada (Login com campo senha + links)
- ✅ 7 métodos novos na API
- ✅ Interceptor para renovação automática de token
- ✅ Tratamento de erros de senha/bloqueio

---

## 4️⃣ ORDEM DE IMPLEMENTAÇÃO RECOMENDADA

### Fase 1: Backend Base
1. ✅ Adicionar campos no banco
2. ✅ Implementar controle de tentativas (Redis)
3. ✅ Modificar endpoint login (validação senha)
4. ✅ Alterar configuração JWT (1 dia + 30 dias)

### Fase 2: Cadastro
5. ✅ Endpoint iniciar cadastro
6. ✅ Endpoint finalizar cadastro
7. ✅ Endpoint validar OTP cadastro

### Fase 3: Reset Senha
8. ✅ Endpoint solicitar reset
9. ✅ Endpoint validar OTP reset

### Fase 4: Refresh Token
10. ✅ Endpoint refresh token
11. ✅ Validação refresh contra tabela auditoria

### Fase 5: App - Autenticação
12. ✅ Modificar tela Login (campo senha + links)
13. ✅ Implementar interceptor refresh token

### Fase 6: App - Cadastro
14. ✅ Criar tela CadastroInicial
15. ✅ Criar tela CadastroValidarOTP
16. ✅ Integrar com backend

### Fase 7: App - Reset Senha
17. ✅ Criar tela ResetSenha
18. ✅ Criar tela ResetSenhaValidarOTP
19. ✅ Integrar com backend

### Fase 8: Testes
20. ✅ Testar fluxo completo de cadastro
21. ✅ Testar fluxo de reset senha
22. ✅ Testar renovação automática de token
23. ✅ Testar controle de tentativas e bloqueio

---

## 5️⃣ CHECKLIST DE VALIDAÇÃO

### Backend:
- [ ] Campo `cadastro_completo` criado e indexado
- [ ] Login valida senha antes de gerar auth_token
- [ ] Controle de tentativas funciona (5/15min, 10/1h, 15/24h)
- [ ] JWT expira em 1 dia (access) e 30 dias (refresh)
- [ ] Refresh token renova access automaticamente
- [ ] Cadastro completo funciona (iniciar/finalizar/validar)
- [ ] Reset senha funciona (solicitar/validar OTP)
- [ ] Logs de auditoria implementados

### App:
- [ ] Login exige senha
- [ ] Links "Esqueci senha" e "Novo Cliente?" visíveis
- [ ] Cadastro completo funciona end-to-end
- [ ] Reset senha funciona end-to-end
- [ ] Token renova automaticamente (sem logout)
- [ ] Tratamento de erros senha incorreta
- [ ] Tratamento de conta bloqueada
- [ ] UX limpa e intuitiva

---

## 6️⃣ PONTOS DE ATENÇÃO

### Segurança:
- ⚠️ Sempre usar HTTPS em produção
- ⚠️ Nunca logar senhas em plaintext
- ⚠️ Rate limiting em todos endpoints sensíveis
- ⚠️ Validar força da senha no backend (não confiar no app)
- ⚠️ Hash pbkdf2_sha256 com salt único por senha

### UX:
- ⚠️ Mostrar indicador de força da senha em tempo real
- ⚠️ Mascarar celular ao enviar OTP ((21) 9****-4321)
- ⚠️ Timer visível de expiração do OTP (5min)
- ⚠️ Mensagens de erro claras e amigáveis
- ⚠️ Loading states em todas ações de rede

### Performance:
- ⚠️ Usar Redis para controle de tentativas (não MySQL)
- ⚠️ Cache de configurações JWT
- ⚠️ Minimizar chamadas ao banco durante renovação de token

---

## 7️⃣ ENDPOINTS IMPLEMENTADOS

### 📝 ENDPOINTS MODIFICADOS

#### **1. POST /api/v1/cliente/login/**

**Status:** ✅ MODIFICADO

**O que mudou:**
- Campo `senha` agora é **obrigatório**
- Valida senha ANTES de gerar auth_token
- Verifica `cadastro_completo = TRUE`
- Integrado com controle de tentativas (Redis)
- Retorna contador de tentativas e status de bloqueio

**Request ANTES:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Request AGORA:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "senha": "Senha@123"
}
```

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-27T21:40:00Z",
  "mensagem": "Credenciais válidas. Use auth_token para verificar 2FA."
}
```

**Response - Senha incorreta (401):**
```json
{
  "sucesso": false,
  "erro": "CPF ou senha incorretos",
  "tentativas_restantes": 4
}
```

**Response - Conta bloqueada (403):**
```json
{
  "sucesso": false,
  "erro": "Conta bloqueada por 15 minutos devido a múltiplas tentativas incorretas. Tente novamente em 14 minutos.",
  "bloqueado_ate": "2025-10-27T21:49:00Z",
  "bloqueado": true
}
```

**Response - Cadastro incompleto (400):**
```json
{
  "sucesso": false,
  "erro": "Complete seu cadastro no app antes de fazer login",
  "cadastro_incompleto": true
}
```

**Arquivos alterados:**
- `apps/cliente/views.py` - Linha 82: campo senha adicionado
- `apps/cliente/serializers.py` - Linha 14: senha obrigatória
- `apps/cliente/services.py` - Linha 343-510: método `login()` completo

---

### 🆕 ENDPOINTS NOVOS

#### **2. POST /api/v1/cliente/refresh/**

**Status:** ✅ CRIADO

**Descrição:** Renova access token JWT usando refresh token

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_at": "2025-10-28T21:35:00Z"
}
```

**Response - Refresh inválido (401):**
```json
{
  "sucesso": false,
  "mensagem": "Refresh token inválido ou expirado. Faça login novamente.",
  "codigo": "token_expired"
}
```

**Arquivos criados:**
- `apps/cliente/views_refresh_jwt.py` - Endpoint completo
- `apps/cliente/urls.py` - Linha 13: rota registrada

---

#### **3. POST /api/v1/cliente/cadastro/iniciar/**

**Status:** ✅ CRIADO

**Descrição:** Verifica se CPF existe e retorna dados faltantes. Se CPF não existe, consulta Bureau e cria cliente base.

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Lógica:**
1. Verifica se CPF existe no canal
2. **Se NÃO existe:**
   - Consulta Bureau de Crédito
   - Cria cliente base (nome, cpf, dados bureau)
   - Marca `cadastro_completo = FALSE`
   - Retorna dados do Bureau + pede complemento
3. **Se existe sem cadastro completo:**
   - Retorna dados existentes + pede faltantes
4. **Se existe com cadastro completo:**
   - Erro: já cadastrado

**Response - CPF não existe (criado agora via Bureau) (200):**
```json
{
  "sucesso": true,
  "cliente_existe": true,
  "cadastro_completo": false,
  "dados_existentes": {
    "nome": "JOAO DA SILVA",
    "cpf": "17653377807"
  },
  "dados_necessarios": ["email", "celular", "senha"],
  "mensagem": "Complete seu cadastro"
}
```

**Response - Cliente existe (POS criou antes) (200):**
```json
{
  "sucesso": true,
  "cliente_existe": true,
  "cadastro_completo": false,
  "dados_existentes": {
    "nome": "JOAO DA SILVA",
    "cpf": "17653377807",
    "celular": "21987654321"
  },
  "dados_necessarios": ["email", "senha"],
  "mensagem": "Complete seu cadastro"
}
```

**Response - CPF reprovado pelo Bureau (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF não aprovado pelo Bureau de Crédito. Verifique seus dados."
}
```

**Response - Cliente já cadastrado (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF já cadastrado. Faça login ou recupere sua senha."
}
```

**Arquivos criados:**
- `apps/cliente/views_cadastro.py` - Endpoint `iniciar_cadastro()`
- `apps/cliente/services_cadastro.py` - Método `verificar_cpf_cadastro()`
- `apps/cliente/urls.py` - Linha 20: rota registrada

---

#### **4. POST /api/v1/cliente/cadastro/finalizar/**

**Status:** ✅ CRIADO

**Descrição:** Salva dados do cadastro + envia OTP para validação

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request - Cliente novo:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "nome": "João da Silva",
  "email": "joao@email.com",
  "celular": "21987654321",
  "senha": "Senha@123"
}
```

**Request - Cliente existente (só faltam campos):**
```json
{
  "cpf": "17653377807",
  "canal_id": 1,
  "celular": "21987654321",
  "senha": "Senha@123"
}
```

**Validações:**
- CPF: 11 dígitos
- Email: formato válido (regex)
- Celular: 10-11 dígitos
- Senha: mínimo 8 caracteres, letra + número
- `cadastro_completo` não pode ser TRUE

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código de verificação enviado via SMS",
  "celular_mascarado": "(21) 9****-4321"
}
```

**Response - Erro validação (400):**
```json
{
  "sucesso": false,
  "mensagem": "Senha fraca. Use no mínimo 8 caracteres com letras e números."
}
```

**Arquivos criados:**
- `apps/cliente/views_cadastro.py` - Endpoint `finalizar_cadastro()`
- `apps/cliente/services_cadastro.py` - Método `finalizar_cadastro()`
- `apps/cliente/urls.py` - Linha 21: rota registrada

---

#### **5. POST /api/v1/cliente/cadastro/validar_otp/**

**Status:** ✅ CRIADO

**Descrição:** Valida OTP + finaliza cadastro (marca `cadastro_completo=TRUE`)

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "codigo": "123456"
}
```

**Lógica:**
1. Valida OTP (5min validade, 3 tentativas)
2. Se válido:
   - Marca `cadastro_completo = TRUE`
   - Atualiza `cadastro_concluido_em = datetime.now()`
   - Revoga OTP usado
3. Retorna sucesso

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Cadastro concluído com sucesso! Faça login para acessar sua conta."
}
```

**Response - OTP inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido",
  "tentativas_restantes": 2
}
```

**Response - OTP expirado (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código expirado. Solicite um novo código."
}
```

**Arquivos criados:**
- `apps/cliente/views_cadastro.py` - Endpoint `validar_otp_cadastro()`
- `apps/cliente/services_cadastro.py` - Método `validar_otp_cadastro()`
- `apps/cliente/urls.py` - Linha 22: rota registrada

---

#### **6. POST /api/v1/cliente/senha/reset/solicitar/**

**Status:** ✅ CRIADO

**Descrição:** Envia OTP para reset de senha

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "canal_id": 1
}
```

**Validações:**
- CPF deve existir
- Cliente deve ter `cadastro_completo=TRUE`
- Rate limiting: 3 solicitações por hora

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Código enviado via SMS para (21) 9****-4321"
}
```

**Response - Cliente não cadastrado (400):**
```json
{
  "sucesso": false,
  "mensagem": "CPF não encontrado. Complete seu cadastro primeiro."
}
```

**Response - Rate limit (400):**
```json
{
  "sucesso": false,
  "mensagem": "Limite de solicitações atingido. Tente novamente em 1 hora."
}
```

**Arquivos criados:**
- `apps/cliente/views_reset_senha.py` - Endpoint `solicitar_reset_senha()`
- `apps/cliente/services_reset_senha.py` - Método `solicitar_reset()`
- `apps/cliente/urls.py` - Linha 25: rota registrada

---

#### **7. POST /api/v1/cliente/senha/reset/validar/**

**Status:** ✅ CRIADO

**Descrição:** Valida OTP + permite criar nova senha

**Headers:**
```
Authorization: Bearer <oauth_token>
Content-Type: application/json
```

**Request:**
```json
{
  "cpf": "17653377807",
  "codigo": "123456",
  "nova_senha": "NovaSenha@456"
}
```

**Validações:**
- OTP válido (5min, 3 tentativas)
- Senha forte (8+ chars, letra+número)
- Hash pbkdf2_sha256

**Response - Sucesso (200):**
```json
{
  "sucesso": true,
  "mensagem": "Senha alterada com sucesso! Faça login com a nova senha."
}
```

**Response - OTP inválido (400):**
```json
{
  "sucesso": false,
  "mensagem": "Código inválido ou expirado",
  "tentativas_restantes": 1
}
```

**Response - Senha fraca (400):**
```json
{
  "sucesso": false,
  "mensagem": "Senha fraca. Use no mínimo 8 caracteres com letras e números."
}
```

**Arquivos criados:**
- `apps/cliente/views_reset_senha.py` - Endpoint `validar_reset_senha()`
- `apps/cliente/services_reset_senha.py` - Método `validar_reset()`
- `apps/cliente/urls.py` - Linha 26: rota registrada

---

### 📊 RESUMO DE ARQUIVOS CRIADOS/MODIFICADOS

#### **Arquivos Novos (8):**
1. `scripts/sql/adicionar_campos_cadastro_cliente.sql` - Migration SQL
2. `apps/cliente/services_login_attempts.py` - Controle de tentativas (Redis)
3. `apps/cliente/views_refresh_jwt.py` - Endpoint refresh token
4. `apps/cliente/views_cadastro.py` - 3 endpoints cadastro
5. `apps/cliente/services_cadastro.py` - Lógica de cadastro
6. `apps/cliente/views_reset_senha.py` - 2 endpoints reset senha
7. `apps/cliente/services_reset_senha.py` - Lógica reset senha
8. `apps/oauth/views_refresh.py` - Endpoint OAuth refresh (não usado)

#### **Arquivos Modificados (4):**
1. `apps/cliente/jwt_cliente.py` - JWT: Access 1 dia + Refresh 30 dias
2. `apps/cliente/services.py` - Método `login()` com validação senha
3. `apps/cliente/views.py` - Endpoint login aceita senha
4. `apps/cliente/serializers.py` - Campo senha obrigatório
5. `apps/cliente/urls.py` - Rotas dos novos endpoints

#### **Total de linhas adicionadas:** ~1.500 linhas

---

### 🔐 CONTROLE DE TENTATIVAS (Redis)

**Implementação:** `apps/cliente/services_login_attempts.py`

**Regras:**
- **5 tentativas em 15 minutos** → Bloqueio 15 minutos
- **10 tentativas em 1 hora** → Bloqueio 1 hora
- **15 tentativas em 24 horas** → Bloqueio manual (análise)

**Chaves Redis:**
```python
login_attempts_15min:{cpf}   # Contador 15min
login_attempts_1h:{cpf}      # Contador 1h
login_attempts_24h:{cpf}     # Contador 24h
login_blocked:{cpf}          # Status de bloqueio
```

**Métodos:**
- `registrar_tentativa_falha(cpf)` - Incrementa contadores
- `verificar_bloqueio(cpf)` - Retorna status
- `limpar_tentativas(cpf)` - Zera após login sucesso
- `desbloquear_manual(cpf)` - Admin pode desbloquear

---

### ⚙️ JWT CONFIGURAÇÃO

**Arquivo:** `apps/cliente/jwt_cliente.py` (Linha 297-298)

**Antes:**
```python
exp_timestamp = now_timestamp + (30 * 24 * 60 * 60)  # 30 dias
refresh_exp_timestamp = now_timestamp + (60 * 24 * 60 * 60)  # 60 dias
```

**Agora:**
```python
exp_timestamp = now_timestamp + (1 * 24 * 60 * 60)  # 1 dia (segurança)
refresh_exp_timestamp = now_timestamp + (30 * 24 * 60 * 60)  # 30 dias
```

**Impacto:**
- Access token expira em **1 dia** (antes: 30 dias)
- Refresh token expira em **30 dias** (antes: 60 dias)
- App deve usar refresh automaticamente (transparente para usuário)

---

**Documento criado em:** 27/10/2025 21:18
**Última atualização:** 27/10/2025 21:35
**Status:** ✅ Backend 100% implementado
