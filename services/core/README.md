# WallClub Core

Package compartilhado entre os containers do ecossistema WallClub.

## Componentes

- **database/**: Queries SQL diretas (read-only)
- **decorators/**: Decorators para APIs
- **estr_organizacional/**: Canal, Loja, Regional, Grupo Econômico, Vendedor
- **integracoes/**: Clientes para APIs internas e serviços externos
- **middleware/**: Security, Session Timeout
- **oauth/**: JWT, OAuth 2.0, Decorators de autenticação
- **seguranca/**: 2FA, Device Management, Rate Limiter, Validador CPF
- **services/**: Auditoria
- **templatetags/**: Tags de formatação
- **utilitarios/**: Config Manager, Export Utils, Formatação

## Instalação Local

```bash
pip install -e /path/to/wallclub_core
```

## Instalação em Containers

No `requirements.txt` do container:

```
wallclub_core @ file:///shared/wallclub_core
```

## Versão

**1.0.0** - Extração inicial do módulo `comum/`

## Compatibilidade

- Python >= 3.11
- Django >= 4.2
