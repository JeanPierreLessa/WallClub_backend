#!/usr/bin/env python3
"""
scripts/validacao/validar_apis_internas.py
Valida APIs REST internas conforme documentação (26 endpoints)
"""

import os
import re
from pathlib import Path

# Documentado em DIRETRIZES.md: 26 APIs REST internas
APIS_DOCUMENTADAS = {
    'cliente': 6,        # consultar_por_cpf, cadastrar, obter_cliente_id, atualizar_celular, obter_dados_cliente, verificar_cadastro
    'conta_digital': 5,  # consultar-saldo, autorizar-uso, debitar-saldo, estornar-saldo, calcular-maximo
    'checkout': 8,       # listar, criar, obter, pausar, reativar, cobrar, atualizar, deletar
    'ofertas': 6,        # listar, criar, obter, atualizar, grupos/listar, grupos/criar
    'parametros': 7,     # configuracoes/loja, configuracoes/contar, configuracoes/ultima, loja/modalidades, planos, importacoes, importacoes/{id}
}

def encontrar_endpoints_api_interna(base_path):
    """Busca por @api_view(['POST']) ou @require_http_methods(["POST"]) em arquivos de API interna"""
    endpoints = {}

    for root, dirs, files in os.walk(base_path):
        # Ignorar venv e __pycache__
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules']]

        for file in files:
            # Buscar por views_api_interna.py OU views_internal_api.py
            if (('api_interna' in file or 'internal_api' in file) and file.startswith('views_')) and file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()

                        # Contar @api_view(['POST']) ou @api_view(["POST"])
                        count_api_view = len(re.findall(r"@api_view\(\[[\'\"]POST[\'\"]\]\)", content))

                        # Contar @require_http_methods(["POST"])
                        count_require = len(re.findall(r"@require_http_methods\(\[\"POST\"\]\)", content))

                        count = count_api_view + count_require

                        if count > 0:
                            # Determinar módulo pelo caminho
                            rel_path = os.path.relpath(filepath, base_path)
                            parts = rel_path.split(os.sep)

                            # Mapear para módulos conhecidos
                            modulo = None
                            if 'cliente' in rel_path:
                                modulo = 'cliente'
                            elif 'conta_digital' in rel_path:
                                modulo = 'conta_digital'
                            elif 'checkout' in rel_path or 'recorrencia' in rel_path:
                                modulo = 'checkout'
                            elif 'ofertas' in rel_path:
                                modulo = 'ofertas'
                            elif 'parametros' in rel_path:
                                modulo = 'parametros'
                            else:
                                modulo = parts[0] if parts else 'outros'

                            endpoints[modulo] = endpoints.get(modulo, 0) + count

                except Exception as e:
                    print(f"  ⚠️  Erro ao ler {filepath}: {e}")

    return endpoints

def listar_arquivos_api_interna(base_path):
    """Lista todos os arquivos de API interna encontrados"""
    arquivos = []

    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ['venv', '__pycache__', '.git', 'node_modules']]

        for file in files:
            if (('api_interna' in file or 'internal_api' in file) and file.startswith('views_')) and file.endswith('.py'):
                filepath = os.path.join(root, file)
                rel_path = os.path.relpath(filepath, base_path)
                arquivos.append(rel_path)

    return arquivos

def validar_apis():
    print("=== VALIDAÇÃO: APIs REST Internas ===\n")

    # Caminho base do Django
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    django_path = os.path.join(base_path, 'services', 'django')

    if not os.path.exists(django_path):
        # Tentar caminho alternativo
        django_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/django'

    if not os.path.exists(django_path):
        print(f"❌ ERRO: Diretório não encontrado: {django_path}")
        return

    print(f"📁 Buscando em: {django_path}\n")

    # Listar arquivos encontrados
    arquivos = listar_arquivos_api_interna(django_path)
    print("📄 Arquivos de API Interna encontrados:")
    for arq in sorted(arquivos):
        print(f"  - {arq}")
    print()

    # Contar endpoints
    endpoints_reais = encontrar_endpoints_api_interna(django_path)

    print("📄 Documentação (DIRETRIZES.md):")
    total_doc = sum(APIS_DOCUMENTADAS.values())
    for modulo, count in sorted(APIS_DOCUMENTADAS.items()):
        print(f"  - {modulo}: {count} endpoints")
    print(f"  TOTAL: {total_doc} endpoints\n")

    print("🔍 Código Real:")
    total_real = sum(endpoints_reais.values())
    for modulo, count in sorted(endpoints_reais.items()):
        status = "✅" if APIS_DOCUMENTADAS.get(modulo, 0) == count else "⚠️"
        print(f"  {status} {modulo}: {count} endpoints")
    print(f"  TOTAL: {total_real} endpoints\n")

    # Comparar
    print("=== Resultado ===")
    if total_doc == total_real:
        print(f"✅ VALIDADO: {total_doc} endpoints conforme documentação")
    else:
        print(f"⚠️  DIVERGÊNCIA: Doc={total_doc}, Real={total_real}")

        # Detalhar divergências
        todos_modulos = set(list(APIS_DOCUMENTADAS.keys()) + list(endpoints_reais.keys()))
        for modulo in sorted(todos_modulos):
            doc = APIS_DOCUMENTADAS.get(modulo, 0)
            real = endpoints_reais.get(modulo, 0)
            if doc != real:
                print(f"  ⚠️  {modulo}: Doc={doc}, Real={real}")

        # Módulos não documentados
        nao_documentados = set(endpoints_reais.keys()) - set(APIS_DOCUMENTADAS.keys())
        if nao_documentados:
            print(f"\n  📝 Módulos não documentados: {', '.join(nao_documentados)}")

if __name__ == '__main__':
    validar_apis()
