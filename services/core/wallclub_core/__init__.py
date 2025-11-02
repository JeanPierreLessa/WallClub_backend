"""
WallClub Core - Componentes compartilhados do ecossistema WallClub.

Este package contém funcionalidades compartilhadas entre os containers:
- Django Main (wallclub_django)
- Risk Engine (wallclub-riskengine)

Componentes:
- database: Queries SQL diretas (read-only)
- decorators: Decorators para APIs
- estr_organizacional: Canal, Loja, Regional, Grupo Econômico, Vendedor
- integracoes: Clientes para APIs internas e serviços externos
- middleware: Security, Session Timeout
- oauth: JWT, OAuth 2.0, Decorators de autenticação
- seguranca: 2FA, Device Management, Rate Limiter, Validador CPF
- services: Auditoria
- templatetags: Tags de formatação
- utilitarios: Config Manager, Export Utils, Formatação
"""

__version__ = "1.0.0"
