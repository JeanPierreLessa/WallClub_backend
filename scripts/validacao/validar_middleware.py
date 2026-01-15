#!/usr/bin/env python3
"""
scripts/validacao/validar_middleware.py
Valida middleware conforme documentação
"""

import os

# Documentado em DIRETRIZES.md e cenario_evolucao_arquitetura_JAN2026.md
MIDDLEWARE_DOCUMENTADO = [
    'security_middleware.py',
    'security_validation.py',
    'session_timeout.py',
    'subdomain_router.py',
]

MIDDLEWARE_RECOMENDADO = [
    'correlation_middleware.py',       # Recomendado mas não implementado
    'request_logging_middleware.py',   # Recomendado mas não implementado
]

def validar_middleware():
    print("=== VALIDAÇÃO: Middleware ===\n")

    # Caminho do middleware no wallclub_core
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    middleware_path = os.path.join(base_path, 'services', 'core', 'wallclub_core', 'middleware')

    if not os.path.exists(middleware_path):
        middleware_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/core/wallclub_core/middleware'

    if not os.path.exists(middleware_path):
        print(f"❌ ERRO: Diretório não encontrado: {middleware_path}")
        return

    print(f"📁 Verificando: {middleware_path}\n")

    arquivos_reais = [f for f in os.listdir(middleware_path) if f.endswith('.py') and f != '__init__.py']

    print("📄 Middleware Documentado (Deve Existir):")
    implementados = 0
    for mw in MIDDLEWARE_DOCUMENTADO:
        existe = mw in arquivos_reais
        status = "✅" if existe else "❌"
        print(f"  {status} {mw}")
        if existe:
            implementados += 1

    print(f"\n  Implementados: {implementados}/{len(MIDDLEWARE_DOCUMENTADO)}")

    print("\n📄 Middleware Recomendado (Opcional):")
    for mw in MIDDLEWARE_RECOMENDADO:
        existe = mw in arquivos_reais
        status = "✅ Implementado" if existe else "⏳ Pendente"
        print(f"  {status}: {mw}")

    # Middleware não documentado
    nao_documentados = set(arquivos_reais) - set(MIDDLEWARE_DOCUMENTADO) - set(MIDDLEWARE_RECOMENDADO)
    if nao_documentados:
        print("\n⚠️  Middleware Real (não documentado):")
        for mw in sorted(nao_documentados):
            print(f"  - {mw}")

    print("\n=== Resultado ===")
    if implementados == len(MIDDLEWARE_DOCUMENTADO):
        print("✅ VALIDADO: Todo middleware documentado está implementado")
    else:
        faltando = len(MIDDLEWARE_DOCUMENTADO) - implementados
        print(f"⚠️  DIVERGÊNCIA: {faltando} middleware(s) documentado(s) não encontrado(s)")

if __name__ == '__main__':
    validar_middleware()
