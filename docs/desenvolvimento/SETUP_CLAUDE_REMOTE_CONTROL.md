# Setup Claude Code Remote Control - Trabalhar no WallClub pelo Celular

**Data:** 08/03/2026
**Objetivo:** Configurar Claude Code Remote Control para continuar sessões de desenvolvimento pelo celular

---

## 📱 O que é Claude Code Remote Control?

Recurso lançado em fevereiro/2026 que permite:
- ✅ Continuar sessão do Claude Code pelo celular/tablet
- ✅ Código roda **localmente** no seu computador (não na nuvem)
- ✅ Sincroniza sessão CLI com claude.ai/code e app mobile
- ✅ Reconecta automaticamente se laptop dormir ou rede cair

**Diferença do Cursor:**
- **Claude:** Código fica local, acesso remoto à sessão
- **Cursor:** Código vai para nuvem

---

## ✅ Requisitos

### 1. Plano Claude
- ✅ Pro, Max, Team ou Enterprise
- ❌ API keys não suportadas

### 2. Autenticação
```bash
# Fazer login no Claude CLI
claude
/login
```

### 3. Workspace Trust
```bash
# Rodar claude no projeto pelo menos 1 vez
cd /Users/jeanlessa/wall_projects/WallClub_backend
claude
# Aceitar o workspace trust dialog
```

---

## 🚀 Como Usar

### Opção 1: Iniciar Nova Sessão Remote Control

```bash
cd /Users/jeanlessa/wall_projects/WallClub_backend

# Comando básico
claude remote-control

# Com nome customizado
claude remote-control "WallClub Backend"

# Com logs detalhados
claude remote-control --verbose --name "WallClub Backend"

# Com sandbox (isolamento de filesystem)
claude remote-control --sandbox --name "WallClub Backend"
```

**O que aparece:**
- URL da sessão (ex: https://claude.ai/code/session/abc123)
- QR Code (pressione ESPAÇO para mostrar/esconder)
- Status de conexão

---

### Opção 2: Ativar Remote Control em Sessão Existente

```bash
# Se já está em uma sessão do Claude
/remote-control

# Ou o atalho
/rc

# Com nome
/remote-control WallClub Backend
```

---

## 📱 Acessar do Celular

### Método 1: Escanear QR Code
1. Rode `claude remote-control` no terminal
2. Pressione ESPAÇO para mostrar QR code
3. Escaneie com app Claude (iOS/Android)
4. Sessão abre automaticamente

### Método 2: URL Direto
1. Copie a URL que aparece no terminal
2. Abra no navegador do celular
3. Ou cole no app Claude

### Método 3: Lista de Sessões
1. Abra https://claude.ai/code no celular
2. Ou abra app Claude
3. Procure sessão pelo nome
4. Sessões Remote Control têm ícone de computador com bolinha verde

**Apps:**
- iOS: https://apps.apple.com/us/app/claude-by-anthropic/id6473753684
- Android: https://play.google.com/store/apps/details?id=com.anthropic.claude

---

## ⚙️ Configuração Permanente

### Ativar Remote Control para TODAS as sessões

```bash
# Abrir configuração
/config

# Procurar por "remote_control_enabled"
# Mudar para: true

# Salvar
```

Agora toda sessão `claude` já inicia com Remote Control ativo.

---

## 🎯 Casos de Uso para WallClub

### 1. Continuar Debug Fora do Escritório
```bash
# No Mac (escritório)
cd /Users/jeanlessa/wall_projects/WallClub_backend
claude remote-control "Debug Checkout"

# Pedir para Claude investigar erro
"Analise os logs do checkout e identifique o problema"

# Sair do escritório
# Abrir no celular e continuar a conversa
"Já identificou a causa? Pode corrigir?"
```

### 2. Revisar Código em Qualquer Lugar
```bash
# Iniciar sessão
claude remote-control "Review PR #123"

# Pedir análise
"Revise o PR #123 e aponte problemas"

# Continuar revisão no celular durante almoço
```

### 3. Monitorar Deploy
```bash
# Antes do deploy
claude remote-control "Deploy v2.2.3"

# Acompanhar pelo celular
"Monitore os logs do deploy e me avise se der erro"
```

### 4. Resolver Incidente de Produção
```bash
# Sessão de emergência
claude remote-control "INCIDENTE - Checkout Down"

# Investigar do celular
"Verifique logs de erro do checkout nas últimas 2 horas"
"Qual container está com problema?"
"Pode reiniciar o serviço?"
```

---

## 🔒 Segurança

### O que acontece:
- ✅ Código **nunca sai** do seu Mac
- ✅ Sessão roda localmente
- ✅ Claude Code acessa seu filesystem local
- ✅ Conexão criptografada (HTTPS)

### O que NÃO acontece:
- ❌ Código não vai para nuvem da Anthropic
- ❌ Arquivos não são copiados para servidor remoto
- ❌ Outras pessoas não veem sua sessão (privada)

### Sandbox Mode (opcional):
```bash
# Isola filesystem e rede
claude remote-control --sandbox --name "WallClub"
```

**Quando usar sandbox:**
- Testando código não confiável
- Quer limitar acesso ao filesystem
- Precisa de isolamento de rede

**Quando NÃO usar:**
- Desenvolvimento normal (limita funcionalidades)
- Precisa acessar banco de dados
- Precisa fazer git push/pull

---

## ⚠️ Limitações

### 1. Máquina Precisa Estar Ligada
- ❌ Se desligar o Mac, sessão cai
- ✅ Se Mac dormir, reconecta automaticamente quando acordar
- ✅ Se rede cair, reconecta automaticamente

### 2. Uma Sessão Ativa por Vez
- ❌ Não pode ter múltiplas sessões Remote Control simultâneas
- ✅ Pode ter várias sessões normais do Claude

### 3. Precisa Manter Terminal Aberto
- ❌ Se fechar terminal, sessão encerra
- ✅ Pode minimizar terminal

---

## 🆚 Comparação: Remote Control vs Claude Code Web

| Feature | Remote Control | Claude Code Web |
|---------|----------------|-----------------|
| **Onde roda** | Seu Mac | Nuvem Anthropic |
| **Filesystem** | Local | Cloud workspace |
| **Acesso offline** | ❌ Não | ✅ Sim |
| **Precisa Mac ligado** | ✅ Sim | ❌ Não |
| **Segurança** | ✅ Código local | ⚠️ Código na nuvem |
| **Ambiente custom** | ✅ Seu setup | ❌ Ambiente padrão |
| **Acesso mobile** | ✅ Sim | ✅ Sim |

**Quando usar Remote Control:**
- Quer código 100% local
- Tem ambiente customizado (Docker, DBs locais)
- Precisa de segurança máxima
- Pode manter Mac ligado

**Quando usar Claude Code Web:**
- Quer trabalhar de qualquer lugar
- Não quer depender de máquina local
- Precisa de acesso 24/7
- Trabalha em equipe (workspaces compartilhados)

---

## 🛠️ Troubleshooting

### Problema: "Session disconnected"
```bash
# Verificar se Mac está acordado
# Verificar conexão de internet
# Sessão reconecta automaticamente
```

### Problema: "Workspace not trusted"
```bash
cd /Users/jeanlessa/wall_projects/WallClub_backend
claude
# Aceitar trust dialog
# Depois rodar remote-control
```

### Problema: "Authentication required"
```bash
claude
/login
# Fazer login no navegador
```

### Problema: QR Code não aparece
```bash
# Pressionar ESPAÇO no terminal
# Ou copiar URL manualmente
```

---

## 📊 Comandos Úteis Durante Sessão

```bash
# Renomear sessão
/rename "Novo Nome"

# Mostrar QR code
# Pressionar ESPAÇO

# Ativar modo mobile (interface otimizada)
/mobile

# Ver status da conexão
/status

# Encerrar Remote Control (mas manter sessão local)
/remote-control off
```

---

## 💡 Dicas

### 1. Use Nomes Descritivos
```bash
# Ruim
claude remote-control

# Bom
claude remote-control "WallClub - Fix Checkout Bug #456"
```

### 2. Mantenha Mac Conectado na Energia
- Evita Mac dormir durante sessão longa
- Garante disponibilidade contínua

### 3. Use Screen/Tmux para Persistência
```bash
# Criar sessão tmux
tmux new -s wallclub

# Rodar Claude dentro do tmux
claude remote-control "WallClub Backend"

# Detach: Ctrl+B, D
# Reattach: tmux attach -t wallclub
```

### 4. Configure Notificações no App
- Receba alertas quando Claude terminar tarefas
- Útil para deploys longos ou análises demoradas

---

## 🎬 Workflow Recomendado

### Cenário: Trabalhar no WallClub de Casa

**1. No Mac (antes de sair):**
```bash
cd /Users/jeanlessa/wall_projects/WallClub_backend
tmux new -s wallclub
claude remote-control --verbose --name "WallClub - $(date +%d/%m)"
```

**2. Pedir tarefa inicial:**
```
"Analise os logs de erro do checkout das últimas 24h e
identifique os 3 problemas mais críticos"
```

**3. Sair de casa com Mac ligado**

**4. No celular (Uber, café, etc):**
- Abrir app Claude
- Encontrar sessão "WallClub - 08/03"
- Continuar conversa
- Revisar análise do Claude
- Pedir correções

**5. Voltar para casa:**
- Continuar no Mac
- Ou manter no celular

**6. Finalizar:**
```bash
# No Mac
Ctrl+C (encerra Claude)
tmux kill-session -t wallclub
```

---

## 📚 Links Úteis

- **Documentação Oficial:** https://code.claude.com/docs/en/remote-control
- **App iOS:** https://apps.apple.com/us/app/claude-by-anthropic/id6473753684
- **App Android:** https://play.google.com/store/apps/details?id=com.anthropic.claude
- **Claude Code Web:** https://claude.ai/code

---

## ✅ Checklist de Setup

- [ ] Verificar plano Claude (Pro/Max/Team/Enterprise)
- [ ] Instalar Claude CLI (se ainda não tem)
- [ ] Fazer login: `claude` → `/login`
- [ ] Aceitar workspace trust no projeto WallClub
- [ ] Instalar app Claude no celular
- [ ] Testar primeira sessão Remote Control
- [ ] Escanear QR code e acessar do celular
- [ ] Configurar `remote_control_enabled: true` (opcional)
- [ ] Configurar tmux para persistência (opcional)

---

**Última Atualização:** 08/03/2026
