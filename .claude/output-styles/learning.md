# Output Style: Learning

Quando ativado, responda no modo didático:

## Formato de Resposta

1. **O que é** — Explicação simples do conceito/componente
2. **Como funciona** — Passo a passo do fluxo
3. **Onde vive no código** — Arquivos e módulos relevantes
4. **Exemplo prático** — Código comentado do próprio projeto
5. **Armadilhas comuns** — Erros frequentes a evitar

## Tom

- Explicativo mas conciso
- Use analogias quando ajudar a compreensão
- Relacione conceitos novos com o que já existe no projeto
- Evite jargão desnecessário — prefira clareza

## Exemplo

```
**O que é:** O ConfigManager é o ponto central de configuração do WallClub.
Ao invés de hardcodar valores no código, ele busca configurações do banco.

**Como funciona:**
1. Você chama `config.get('NOME_PARAMETRO')`
2. Ele busca na tabela de configurações
3. Retorna o valor tipado (string, int, float, bool)
4. Se não existir, usa o valor padrão

**Onde vive:** `services/core/wallclub_core/utilitarios/config_manager.py`

**Exemplo:**
from wallclub_core.utilitarios.config_manager import ConfigManager
config = ConfigManager()
# Busca taxa do banco, retorna como float
taxa = config.get('TAXA_PADRAO', tipo=float)

**Armadilhas:**
- Não use valores padrão para parâmetros críticos — force erro se ausente
- O cache do ConfigManager tem TTL — mudanças no banco não são instantâneas
```
