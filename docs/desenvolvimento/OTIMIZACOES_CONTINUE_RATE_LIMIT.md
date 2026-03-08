# OTIMIZAÇÕES PARA EVITAR RATE LIMIT (TOKENS POR MINUTO) NO CLAUDE + CONTINUE

**Data:** 08/03/2026
**Contexto:** Erro de rate limit quando ultrapassa 450.000 tokens de entrada por minuto

---

## 🎯 PROBLEMA

O erro de rate limit ocorre quando o total de tokens enviados para o modelo dentro de um minuto ultrapassa o limite configurado pela API. No caso apresentado, o limite é de 450.000 tokens de entrada por minuto. 

Em ambientes com IDEs como VSCode/Windsurf usando a extensão Continue, isso normalmente acontece porque o sistema envia muitos arquivos do projeto como contexto.

**Regra prática:** `prompt total ideal < 100k tokens`

Projetos grandes podem facilmente enviar 200k a 400k tokens por requisição se o contexto não estiver controlado.

---

## 🚀 5 OTIMIZAÇÕES DIRETAS

### 1. Limitar o número de arquivos enviados no contexto ⭐⭐⭐⭐⭐

Reduza a quantidade de arquivos que a extensão envia automaticamente para o modelo.

**Configuração sugerida:**
```json
{
  "maxFiles": 5,
  "maxFileSize": 20000
}
```

Isso evita que grandes partes do repositório sejam incluídas no prompt.

**Impacto esperado:** Redução de aproximadamente 70% a 90% no volume de tokens enviados.

---

### 2. Criar um arquivo .continueignore ⭐⭐⭐⭐⭐

Esse arquivo funciona de forma semelhante ao .gitignore. Ele impede que determinados diretórios ou arquivos sejam usados como contexto pela IA.

**Exemplo de conteúdo:**
```
node_modules/
vendor/
dist/
build/
.cache/
docs/
*.log
*.lock
*.md
*.json
coverage/
```

Se houver arquivos Markdown grandes no projeto, também vale ignorá-los explicitamente.

---

### 3. Desativar indexação automática do repositório ⭐⭐⭐⭐

Algumas configurações fazem a extensão enviar automaticamente partes do código do projeto para ajudar o modelo a entender o contexto.

**Desative opções como:**
- Auto context
- Codebase embeddings  
- Auto include related files

Use apenas os arquivos que você abrir manualmente no editor.

---

### 4. Reduzir o tamanho máximo de resposta (maxTokens) ⭐⭐⭐

Se o sistema estiver configurado para respostas muito grandes, o consumo de tokens aumenta.

**Configuração recomendada:**
```json
{
  "maxTokens": 2000
}
```

Evite valores muito altos como 8000 ou mais.

---

### 5. Evitar chamadas paralelas para o modelo ⭐⭐⭐⭐

Algumas extensões possuem modos de agente que executam múltiplas chamadas simultâneas ao modelo.

**Desative recursos como:**
- parallel tool calls
- multi-step agent  
- auto retry

Manter apenas uma requisição ativa por vez reduz significativamente o risco de atingir o limite.

---

## ⚙️ CONFIGURAÇÃO CONTINUE OTIMIZADA

**Arquivo de configuração sugerido:**
```json
{
  "maxFiles": 5,
  "maxFileSize": 20000,
  "maxTokens": 2000,
  "enableAutocomplete": false,
  "enableCodebaseEmbeddings": false,
  "autoIncludeRelatedFiles": false,
  "parallelToolCalls": false
}
```

---

## 📊 RESULTADO ESPERADO

**Antes das otimizações:**
- Consumo: 200k a 400k tokens por requisição
- Rate limit frequente

**Após otimizações:**
- Consumo: 30k a 50k tokens por requisição  
- Rate limit raro/inexistente

**Redução total:** ~80-90% no consumo de tokens

---

## ✅ CHECKLIST DE APLICAÇÃO

### Para WallClub Backend:

- [ ] Criar `.continueignore` com exclusões específicas
- [ ] Configurar `maxFiles: 5` 
- [ ] Configurar `maxTokens: 2000`
- [ ] Desativar auto-context e embeddings
- [ ] Testar consumo de tokens

### Monitoramento:
- [ ] Observar frequência de rate limits
- [ ] Monitorar qualidade das respostas
- [ ] Ajustar maxFiles se necessário (3-7 range)

---

**Aplicado em:** 08/03/2026  
**Status:** Configurações implementadas no projeto WallClub