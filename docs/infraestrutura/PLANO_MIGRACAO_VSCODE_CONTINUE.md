# Plano de Migração: Windsurf → VSCode + Continue.dev + code-server

**Data:** 08/03/2026
**Objetivo:** Reduzir custo de $150/mês → $66/mês (economia de $84/mês)

---

## 💰 Comparação de Custos

| Item | Antes (Windsurf) | Depois (VSCode + Continue) | Economia |
|------|------------------|----------------------------|----------|
| **Editor** | Windsurf $150/mês | VSCode $0 | $150 |
| **IA (Sonnet 4.5)** | Incluído | Claude API $66/mês | -$66 |
| **Mobile** | ❌ Não tem | code-server $0 | $0 |
| **TOTAL** | **$150/mês** | **$66/mês** | **$84/mês** |

**Economia anual:** $1.008

---

## 📋 Plano de Migração (3 Fases)

### **Fase 1: Setup VSCode + Continue no Mac** (1-2h)
- Instalar Continue.dev
- Configurar API key Claude
- Testar Sonnet 4.5
- Validar produtividade

### **Fase 2: Instalar code-server no EC2** (1h)
- Instalar no servidor 10.0.1.124
- Configurar HTTPS
- Testar acesso mobile
- Instalar Continue.dev no code-server

### **Fase 3: Migração Completa** (1 semana)
- Usar VSCode + Continue por 1 semana
- Monitorar custo da API
- Se OK, cancelar Windsurf
- Economia ativa

---

## 🚀 FASE 1: Setup VSCode + Continue no Mac

### 1.1 Instalar Continue.dev

```bash
# 1. Abrir VSCode
# 2. Extensions (Cmd+Shift+X)
# 3. Procurar "Continue"
# 4. Instalar "Continue - Codestral, Claude, and more"
```

### 1.2 Configurar API Key do Claude

```bash
# 1. Pegar API key
# Abrir: https://platform.claude.com/settings/keys
# Criar nova key: "VSCode Continue - WallClub"
# Copiar key

# 2. Configurar Continue
# Cmd+Shift+P → "Continue: Open config.json"
```

### 1.3 Arquivo de Configuração

```json
{
  "models": [
    {
      "title": "Claude Sonnet 4.6 (Melhor)",
      "provider": "anthropic",
      "model": "claude-sonnet-4.6-20250514",
      "apiKey": "SUA_API_KEY_AQUI",
      "contextLength": 200000,
      "completionOptions": {
        "temperature": 0.0,
        "maxTokens": 8000
      }
    },
    {
      "title": "Claude Opus (Mais Inteligente)",
      "provider": "anthropic",
      "model": "claude-opus-4-20250514",
      "apiKey": "SUA_API_KEY_AQUI",
      "contextLength": 200000,
      "completionOptions": {
        "temperature": 0.0,
        "maxTokens": 8000
      }
    },
    {
      "title": "Claude Haiku (Rápido e Barato)",
      "provider": "anthropic",
      "model": "claude-3-5-haiku-20241022",
      "apiKey": "SUA_API_KEY_AQUI",
      "contextLength": 200000,
      "completionOptions": {
        "temperature": 0.0,
        "maxTokens": 4000
      }
    }
  ],
  "tabAutocompleteModel": {
    "title": "Claude Haiku",
    "provider": "anthropic",
    "model": "claude-3-5-haiku-20241022",
    "apiKey": "SUA_API_KEY_AQUI"
  },
  "embeddingsProvider": {
    "provider": "free-trial"
  },
  "allowAnonymousTelemetry": false,
  "docs": [
    {
      "title": "WallClub Docs",
      "startUrl": "file:///Users/jeanlessa/wall_projects/WallClub_backend/docs"
    }
  ]
}
```

⚠️ **IMPORTANTE - SEGURANÇA:**
- **NUNCA** commite este arquivo com a API key real
- Substitua `SUA_API_KEY_AQUI` pela sua key do Claude (https://platform.claude.com/settings/keys)
- Adicione `~/.continue/config.json` ao `.gitignore` se for versionar

**Quando usar cada modelo:**
- **Sonnet 4.6:** Desenvolvimento normal, refatorações, análises ($3/1M tokens)
- **Opus:** Problemas complexos, arquitetura, debugging difícil ($15/1M tokens)
- **Haiku:** Autocomplete, tarefas simples, perguntas rápidas ($0.25/1M tokens - MUITO BARATO)

**Dica:** Use Haiku para autocomplete (já configurado) para economizar muito!

### 1.4 Atalhos do Continue

```bash
# Chat com IA
Cmd+L

# Inline edit (igual Windsurf)
Cmd+I

# Adicionar contexto
Cmd+Shift+L

# Aceitar sugestão
Tab

# Rejeitar sugestão
Esc
```

### 1.5 Testar Funcionalidades

```bash
# 1. Abrir projeto WallClub
cd /Users/jeanlessa/wall_projects/WallClub_backend
code .

# 2. Testar chat (Cmd+L)
"Analise a estrutura do projeto e me dê um resumo"

# 3. Testar inline edit (Cmd+I)
# Selecionar código
# Cmd+I
"Adicione docstring nesta função"

# 4. Testar autocomplete
# Começar a escrever código
# Tab para aceitar sugestões
```

---

## 🖥️ FASE 2: Instalar code-server no EC2

### 2.1 Conectar no Servidor

```bash
ssh -i /Users/jeanlessa/wall_projects/aws/webserver-dev.pem ubuntu@10.0.1.124
```

### 2.2 Instalar code-server

```bash
# Instalar
curl -fsSL https://code-server.dev/install.sh | sh

# Verificar instalação
code-server --version
```

### 2.3 Configurar code-server

```bash
# Criar arquivo de configuração
mkdir -p ~/.config/code-server
cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8443
auth: password
password: SuaSenhaSegura123!
cert: false
EOF
```

### 2.4 Criar Serviço Systemd

```bash
sudo tee /etc/systemd/system/code-server.service > /dev/null << EOF
[Unit]
Description=code-server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/var/www/WallClub_backend
ExecStart=/usr/bin/code-server --config /home/ubuntu/.config/code-server/config.yaml
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Habilitar e iniciar
sudo systemctl enable code-server
sudo systemctl start code-server
sudo systemctl status code-server
```

### 2.5 Configurar Security Group

```bash
# Adicionar regra no Security Group sg-089ad6fe45dff742e
aws ec2 authorize-security-group-ingress \
  --group-id sg-089ad6fe45dff742e \
  --protocol tcp \
  --port 8443 \
  --cidr 0.0.0.0/0 \
  --region us-east-1
```

### 2.6 Acessar code-server

```bash
# Do Mac ou celular
http://10.0.1.124:8443

# Login com senha: SuaSenhaSegura123!
```

### 2.7 Instalar Continue.dev no code-server

```bash
# 1. Acessar http://10.0.1.124:8443
# 2. Extensions (Cmd+Shift+X)
# 3. Procurar "Continue"
# 4. Instalar

# 5. Configurar API key
# Cmd+Shift+P → "Continue: Open config.json"
# Colar mesma configuração do Mac
```

### 2.8 Configurar HTTPS (Opcional - Recomendado)

```bash
# Instalar certbot
sudo apt update
sudo apt install certbot -y

# Gerar certificado (se tiver domínio)
sudo certbot certonly --standalone -d code.wallclub.com.br

# Atualizar config.yaml
cat > ~/.config/code-server/config.yaml << EOF
bind-addr: 0.0.0.0:8443
auth: password
password: SuaSenhaSegura123!
cert: /etc/letsencrypt/live/code.wallclub.com.br/fullchain.pem
cert-key: /etc/letsencrypt/live/code.wallclub.com.br/privkey.pem
EOF

# Reiniciar
sudo systemctl restart code-server
```

---

## 📱 FASE 3: Testar Mobile

### 3.1 Acessar do Celular

```bash
# Safari/Chrome no iPhone/Android
http://10.0.1.124:8443

# Ou se configurou HTTPS
https://code.wallclub.com.br
```

### 3.2 Testar Funcionalidades

```bash
# 1. Login
# 2. Abrir projeto WallClub
# 3. Testar Continue (Cmd+L no teclado virtual)
# 4. Editar código
# 5. Commit/push
```

### 3.3 Adicionar à Home Screen (iOS)

```bash
# Safari → Compartilhar → Adicionar à Tela de Início
# Vira "app" nativo
```

---

## 💰 FASE 4: Monitorar Custos

### 4.1 Acompanhar Uso da API

```bash
# Acessar dashboard
https://platform.claude.com/settings/usage

# Verificar diariamente:
# - Tokens consumidos
# - Custo acumulado
# - Projeção mensal
```

### 4.2 Calcular Economia Real

```bash
# Após 1 semana de uso
# Multiplicar custo semanal × 4

# Exemplo:
# Semana 1: $15
# Projeção mensal: $60
# Economia vs Windsurf: $90/mês
```

### 4.3 Alertas de Custo

```bash
# Configurar alerta no Claude Console
# Settings → Usage → Set Budget Alert
# Alerta em: $80/mês (margem de segurança)
```

---

## ✅ FASE 5: Cancelar Windsurf

### 5.1 Validar Migração

**Checklist antes de cancelar:**
- [ ] VSCode + Continue funcionando no Mac
- [ ] code-server funcionando no servidor
- [ ] Acesso mobile testado e OK
- [ ] Custo API < $80/mês
- [ ] Produtividade igual ou melhor
- [ ] 1 semana de uso sem problemas

### 5.2 Cancelar Windsurf

```bash
# 1. Acessar windsurf.ai
# 2. Settings → Billing
# 3. Cancel Subscription
# 4. Confirmar cancelamento
```

### 5.3 Backup de Configurações

```bash
# Exportar settings do Windsurf (se quiser)
# Settings → Export Settings
# Guardar para referência
```

---

## 🎯 Workflow Pós-Migração

### **De Casa (Mac):**
```bash
# VSCode desktop
cd /Users/jeanlessa/wall_projects/WallClub_backend
code .

# Continue.dev ativo
# Cmd+L para chat
# Cmd+I para inline edit
# Trabalha normalmente
```

### **Fora de Casa (Celular/Tablet):**
```bash
# Navegador
http://10.0.1.124:8443

# VSCode web completo
# Continue.dev funcionando
# Edita código
# Commit/push
```

### **Sincronização:**
```bash
# Antes de sair de casa
git commit -am "WIP: trabalhando em X"
git push

# No celular
git pull
# Continua trabalhando

# Quando terminar
git commit -am "Done: finalizei X"
git push

# De volta em casa
git pull
```

---

## 📊 Comparação de Features

| Feature | Windsurf | VSCode + Continue |
|---------|----------|-------------------|
| **Chat com IA** | ✅ Cascade | ✅ Continue |
| **Inline edit** | ✅ | ✅ |
| **Autocomplete** | ✅ | ✅ |
| **Multi-file edit** | ✅ Excelente | ✅ Bom |
| **Contexto projeto** | ✅ Automático | ✅ Manual (@docs) |
| **Sonnet 4.5** | ✅ Ilimitado | ✅ Ilimitado |
| **Mobile** | ❌ | ✅ code-server |
| **Custo** | $150/mês | $66/mês |
| **Controle API** | ❌ | ✅ Total |

---

## ⚠️ Possíveis Problemas e Soluções

### Problema 1: Continue mais lento que Windsurf
**Solução:**
```bash
# Ajustar timeout no config.json
"completionOptions": {
  "timeout": 30000
}
```

### Problema 2: Autocomplete não funciona bem
**Solução:**
```bash
# Usar modelo mais leve para autocomplete
"tabAutocompleteModel": {
  "model": "claude-3-5-sonnet-20241022"
}
```

### Problema 3: Custo API maior que esperado
**Solução:**
```bash
# Reduzir maxTokens
"completionOptions": {
  "maxTokens": 4000
}

# Usar Sonnet 3.5 para tarefas simples
# Sonnet 4.5 só para tarefas complexas
```

### Problema 4: code-server lento no celular
**Solução:**
```bash
# Aumentar recursos do servidor
# Ou usar apenas para emergências
# Desenvolvimento principal no Mac
```

---

## 💡 Dicas de Otimização

### 1. Use @docs para Contexto
```bash
# No chat do Continue
@docs Como funciona o sistema de cashback?

# Continue busca na pasta docs/
```

### 2. Crie Snippets Customizados
```bash
# VSCode → Preferences → User Snippets
# Criar snippets para código repetitivo
```

### 3. Configure Atalhos
```bash
# VSCode → Preferences → Keyboard Shortcuts
# Ajustar para ficar igual Windsurf
```

### 4. Use Workspaces
```bash
# Salvar workspace do WallClub
# File → Save Workspace As...
# wallclub.code-workspace
```

---

## 📈 Métricas de Sucesso

### Após 1 Mês:

**Custo:**
- [ ] API Claude < $80/mês
- [ ] Economia real > $70/mês

**Produtividade:**
- [ ] Tempo de desenvolvimento igual ou menor
- [ ] Qualidade do código mantida
- [ ] Sem frustração com ferramentas

**Mobile:**
- [ ] code-server usado pelo menos 1x/semana
- [ ] Consegue resolver emergências remotamente

---

## 🔄 Plano de Rollback

Se não funcionar bem:

### Opção 1: Voltar para Windsurf
```bash
# 1. Reativar assinatura Windsurf
# 2. Continuar usando
# Perda: 1 mês de teste
```

### Opção 2: Testar Cursor
```bash
# 1. Baixar Cursor (https://cursor.sh)
# 2. Testar 14 dias grátis
# 3. Se funcionar, assinar $20/mês
# Economia: $130/mês (mas sem Sonnet 4.5 ilimitado)
```

---

## ✅ Checklist de Migração

### Pré-Migração
- [ ] Backup de configurações Windsurf
- [ ] API key Claude criada
- [ ] Servidor EC2 acessível

### Fase 1 - Mac
- [ ] Continue.dev instalado
- [ ] API key configurada
- [ ] Sonnet 4.5 testado
- [ ] Autocomplete funcionando
- [ ] Chat funcionando
- [ ] Inline edit funcionando

### Fase 2 - Servidor
- [ ] code-server instalado
- [ ] Serviço systemd configurado
- [ ] Security Group liberado
- [ ] Acesso web funcionando
- [ ] Continue.dev instalado no code-server
- [ ] HTTPS configurado (opcional)

### Fase 3 - Mobile
- [ ] Acesso do celular OK
- [ ] Continue funcionando no mobile
- [ ] Edição de código testada
- [ ] Git push/pull funcionando

### Fase 4 - Validação
- [ ] 1 semana de uso completo
- [ ] Custo API monitorado
- [ ] Produtividade validada
- [ ] Sem problemas críticos

### Fase 5 - Finalização
- [ ] Windsurf cancelado
- [ ] Economia confirmada
- [ ] Workflow estabelecido

---

## 📚 Links Úteis

- **Continue.dev:** https://continue.dev
- **code-server:** https://github.com/coder/code-server
- **Claude API:** https://platform.claude.com
- **VSCode:** https://code.visualstudio.com

---

## 💰 Resumo Financeiro

### Investimento Inicial:
```
Tempo: 4-5 horas
Custo: $0
```

### Economia Mensal:
```
Windsurf: $150/mês
VSCode + Continue: $66/mês
Economia: $84/mês
```

### Retorno:
```
Mês 1: $84
Ano 1: $1.008
5 anos: $5.040
```

**ROI:** Imediato (sem custo de setup)

---

**Última Atualização:** 08/03/2026
