---
description: Auditar e atualizar documentação desatualizada do projeto
---

# Workflow: Auditar Documentação

Este workflow ajuda a identificar e atualizar documentação desatualizada.

## Quando usar

- Após grandes mudanças no projeto
- Periodicamente (mensal/trimestral)
- Antes de onboarding de novos desenvolvedores
- Quando suspeitar que docs estão desatualizados

## Passos

### 1. Listar arquivos de documentação
```bash
find docs/ -name "*.md" -type f
```

### 2. Para cada arquivo, perguntar ao Claude:

**Exemplo:**
```
Leia docs/arquitetura/NOME_DO_ARQUIVO.md e me diga:
1. Quais seções estão desatualizadas baseado no código atual?
2. O que mudou desde a última atualização?
3. O que precisa ser adicionado/removido?
```

### 3. Priorizar atualizações

**Alta prioridade:**
- docs/ARQUITETURA.md (estrutura de containers, integrações)
- docs/DIRETRIZES.md (padrões de código)
- docs/DIRETRIZES_LLM.md (comportamento do assistente)
- .claude/CLAUDE.md (contexto essencial)

**Média prioridade:**
- docs/deployment/*.md (procedimentos de deploy)
- docs/arquitetura/*.md (diagramas e fluxos)
- MEMORY.md (limpar decisões antigas >30 dias)

**Baixa prioridade:**
- docs/em execucao/*.md (histórico de fases)
- docs/riskengine/*.md (específico do módulo)

### 4. Atualizar arquivos

Para cada arquivo desatualizado:
```
Atualize docs/NOME_DO_ARQUIVO.md com base nas mudanças que identifiquei:
- [lista de mudanças]
```

### 5. Validar skills

Verificar se skills ainda apontam para arquivos corretos:
```bash
cat .claude/skills/wallclub-architecture/SKILL.md
cat .claude/skills/wallclub-standards/SKILL.md
```

## Checklist de Auditoria

- [ ] ARQUITETURA.md reflete containers atuais?
- [ ] DIRETRIZES.md tem padrões novos (ex: wall='K')?
- [ ] DIRETRIZES_LLM.md tem regras atualizadas?
- [ ] docs/deployment/ tem procedimentos corretos?
- [ ] docs/arquitetura/ tem diagramas atualizados?
- [ ] MEMORY.md tem apenas decisões recentes (<30 dias)?
- [ ] CHANGELOG.md tem últimas mudanças?
- [ ] README.md tem estatísticas corretas?

## Automação Futura

Considere criar um script que:
1. Compara data de última modificação de código vs docs
2. Lista arquivos com >30 dias de defasagem
3. Gera relatório de auditoria

## Frequência Recomendada

- **Mensal:** Revisar MEMORY.md (limpar >30 dias)
- **Trimestral:** Auditar docs/ARQUITETURA.md e DIRETRIZES.md
- **Semestral:** Auditoria completa de toda documentação
