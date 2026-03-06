# Prompt: Otimização de Contexto para Claude Code

Use este prompt em qualquer projeto para implementar a estrutura otimizada de contexto do Claude Code, reduzindo consumo de tokens em até 97%.

---

## 📋 Prompt para Copiar e Colar

```
Preciso otimizar o contexto do Claude Code neste projeto seguindo as melhores práticas oficiais da Codeium/Windsurf.

Objetivo: Reduzir consumo de tokens mantendo contexto essencial disponível.

Implemente a seguinte estrutura:

## 1. Criar .claude/CLAUDE.md (~200 linhas)

Arquivo que será carregado automaticamente em toda sessão.

Conteúdo obrigatório:
- Stack técnica (linguagem, framework, banco, versões)
- Propósito do sistema (1-2 parágrafos)
- Estrutura de diretórios (principais pastas)
- Regras críticas do projeto (autenticação, dados, logs, transações)
- Padrões de código fundamentais
- Comandos mais usados
- Comportamento esperado do assistente

Formato: Markdown conciso, direto ao ponto, sem floreios.

## 2. Criar MEMORY.md (raiz do projeto, ~50 linhas)

Arquivo para memória persistente entre sessões.

Seções obrigatórias:
- **Decisões Técnicas Recentes** (últimos 7 dias)
- **Bugs em Investigação** (ativos no momento)
- **Dados de Teste** (IDs, CPFs, tokens para testes)
- **Comandos Úteis** (comandos específicos do projeto)
- **Queries SQL Úteis** (se aplicável)
- **Próximos Passos** (TODOs de curto prazo)

Nota: Este arquivo deve ser atualizado manualmente conforme trabalho no projeto.

## 3. Criar .claude/hooks.json

Arquivo de validações automáticas que rodam em eventos específicos.

Criar hook PreToolUse que AVISE (não bloqueie) sobre:
- Segurança: falta de autenticação, validação, exposição de dados
- Dados: valores hardcoded, tipos incorretos (float vs Decimal)
- Logs: falta de logging em operações críticas
- Transações: operações de DB sem transação atômica
- Documentação: quando atualizar MEMORY.md, CHANGELOG.md, README.md

Formato JSON conforme documentação oficial.

## 4. Criar Skills

Transformar documentação extensa em skills (carregadas sob demanda).

Para cada documento grande (>500 linhas):
- Criar .claude/skills/[nome-skill]/SKILL.md
- Frontmatter YAML com name e description
- Conteúdo: resumo + instrução para ler arquivo original

Exemplos de skills:
- Arquitetura do sistema
- Padrões técnicos detalhados
- Guias de deployment
- Documentação de APIs

## 5. Criar CHANGELOG.md

Se não existir, extrair histórico de mudanças do README.md ou commits.

Formato cronológico reverso (mais recente primeiro).

## 6. Enxugar README.md

Manter apenas:
- Overview do projeto
- Como rodar localmente
- Estrutura básica
- Link para CHANGELOG.md
- Estatísticas principais

Remover: changelog extenso, histórico detalhado (mover para CHANGELOG.md).

## 7. Criar Workflow de Auditoria

Criar .windsurf/workflows/auditar-documentacao.md

Workflow para auditar periodicamente se documentação está atualizada.

---

Após implementar, me mostre:
1. Quantas linhas eram carregadas antes (se houver docs existentes)
2. Quantas linhas serão carregadas agora
3. Percentual de redução
4. Lista de skills criadas
5. Resumo do hook implementado

Siga rigorosamente os padrões oficiais da documentação Codeium/Windsurf.
```

---

## 📚 Referências

- [Context Awareness](https://docs.codeium.com/windsurf/context-awareness)
- [Skills](https://docs.codeium.com/windsurf/skills)
- [Hooks](https://docs.codeium.com/windsurf/hooks)
- [Memory](https://docs.codeium.com/windsurf/memory)

---

## 🎯 Resultado Esperado

Após executar este prompt, você terá:

```
projeto/
├── .claude/
│   ├── CLAUDE.md              # ~200 linhas (carregado sempre)
│   ├── hooks.json             # Validações automáticas
│   └── skills/
│       ├── [skill-1]/
│       │   └── SKILL.md
│       └── [skill-2]/
│           └── SKILL.md
├── .windsurf/
│   └── workflows/
│       └── auditar-documentacao.md
├── MEMORY.md                  # ~50 linhas (atualizado manualmente)
├── CHANGELOG.md               # Histórico completo
└── README.md                  # Enxuto e objetivo
```

**Redução típica:** 85-97% no consumo de tokens

---

## 💡 Dicas de Uso

1. **Atualize MEMORY.md regularmente** (ao fim de cada sessão de trabalho)
2. **Invoque skills quando necessário** (`@nome-da-skill`)
3. **Use o workflow de auditoria** mensalmente ou após grandes mudanças
4. **Mantenha .claude/CLAUDE.md enxuto** (máximo 300 linhas)
5. **Documente decisões importantes** no MEMORY.md imediatamente

---

## ⚠️ Importante

- **Não delete** documentação original (docs/, README.md extenso, etc)
- **Skills apenas referenciam** os arquivos originais
- **Fonte de verdade** continua sendo os arquivos em `docs/`
- **Atualização:** Sempre atualize arquivos originais, skills refletem automaticamente

---

**Criado em:** 04/03/2026
**Baseado em:** Otimização implementada no WallClub Backend
**Artigo de referência:** https://www.tabnews.com.br/andersonlimadev/como-criei-uma-skill-que-economiza-84-por-cento-dos-tokens-no-claude-code
