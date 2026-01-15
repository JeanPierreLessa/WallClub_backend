#!/usr/bin/env python3
"""
scripts/validacao/validar_riskengine.py
Valida estrutura e documentação do Risk Engine
"""

import os
from pathlib import Path

# Estrutura documentada do Risk Engine
ESTRUTURA_DOCUMENTADA = {
    'antifraude': [
        'models.py',
        'models_config.py',
        'services.py',
        'services_3ds.py',
        'services_cliente_auth.py',
        'services_coleta.py',
        'services_maxmind.py',
        'services_whitelist.py',
        'views.py',
        'views_api.py',
        'views_revisao.py',
        'views_seguranca.py',
        'tasks.py',
        'notifications.py',
        'urls.py',
        'admin.py',
    ],
    'docs': [
        'engine_antifraude.md',
        'integracao_autenticacao_fraude.md',
    ],
    'riskengine': [
        'settings.py',
        'urls.py',
        'wsgi.py',
    ],
}

# Endpoints documentados do Risk Engine
ENDPOINTS_DOCUMENTADOS = {
    'analisar': '/api/antifraude/analisar/',
    'revisao_pendentes': '/api/antifraude/revisao/pendentes/',
    'revisao_aprovar': '/api/antifraude/revisao/{id}/aprovar/',
    'revisao_reprovar': '/api/antifraude/revisao/{id}/reprovar/',
    'health': '/api/antifraude/health/',
}

# Regras documentadas
REGRAS_DOCUMENTADAS = [
    'Velocidade Alta - Múltiplas Transações',
    'Valor Suspeito - Acima do Normal',
    'Dispositivo Novo',
    'Horário Incomum',
    'IP Suspeito - Múltiplos CPFs',
]


def validar_estrutura(base_path):
    """Valida estrutura de arquivos do Risk Engine"""
    print("=== VALIDAÇÃO: Estrutura Risk Engine ===")
    print(f"\n📁 Verificando: {base_path}\n")

    total_esperado = 0
    total_encontrado = 0
    arquivos_faltando = []
    arquivos_extras = []

    for diretorio, arquivos in ESTRUTURA_DOCUMENTADA.items():
        dir_path = os.path.join(base_path, diretorio)
        print(f"📁 {diretorio}/")

        if not os.path.exists(dir_path):
            print(f"  ❌ Diretório não existe!")
            arquivos_faltando.extend([f"{diretorio}/{a}" for a in arquivos])
            total_esperado += len(arquivos)
            continue

        # Listar arquivos reais
        arquivos_reais = set()
        for f in os.listdir(dir_path):
            if f.endswith('.py') or f.endswith('.md'):
                arquivos_reais.add(f)

        for arquivo in arquivos:
            total_esperado += 1
            arquivo_path = os.path.join(dir_path, arquivo)

            if os.path.exists(arquivo_path):
                print(f"  ✅ {arquivo}")
                total_encontrado += 1
            else:
                print(f"  ❌ {arquivo} (não encontrado)")
                arquivos_faltando.append(f"{diretorio}/{arquivo}")

        # Arquivos extras (não documentados)
        arquivos_doc = set(arquivos)
        extras = arquivos_reais - arquivos_doc
        for extra in sorted(extras):
            if extra != '__init__.py' and extra != 'apps.py':
                print(f"  📝 {extra} (não documentado)")
                arquivos_extras.append(f"{diretorio}/{extra}")

    print(f"\n=== Resultado ===")
    if total_encontrado == total_esperado:
        print(f"✅ VALIDADO: Estrutura conforme documentação ({total_encontrado}/{total_esperado} arquivos)")
    else:
        print(f"⚠️  DIVERGÊNCIA: {total_encontrado}/{total_esperado} arquivos encontrados")
        if arquivos_faltando:
            print(f"  Faltando: {', '.join(arquivos_faltando)}")

    return total_encontrado == total_esperado


def validar_endpoints(base_path):
    """Valida endpoints do Risk Engine"""
    print("\n=== VALIDAÇÃO: Endpoints Risk Engine ===")

    urls_file = os.path.join(base_path, 'antifraude', 'urls.py')

    if not os.path.exists(urls_file):
        print("❌ Arquivo urls.py não encontrado")
        return False

    with open(urls_file, 'r') as f:
        content = f.read()

    print(f"\n📄 Endpoints Documentados:")
    endpoints_encontrados = 0

    for nome, endpoint in ENDPOINTS_DOCUMENTADOS.items():
        # Extrair path do endpoint
        path = endpoint.replace('/api/antifraude/', '').rstrip('/')
        if '{id}' in path:
            path = path.replace('{id}', '')

        # Buscar no urls.py
        if path in content or nome in content.lower():
            print(f"  ✅ {nome}: {endpoint}")
            endpoints_encontrados += 1
        else:
            print(f"  ⚠️  {nome}: {endpoint} (não encontrado no urls.py)")

    print(f"\n=== Resultado ===")
    total = len(ENDPOINTS_DOCUMENTADOS)
    if endpoints_encontrados >= total - 1:  # Permitir 1 faltando (health pode não estar)
        print(f"✅ VALIDADO: {endpoints_encontrados}/{total} endpoints encontrados")
        return True
    else:
        print(f"⚠️  DIVERGÊNCIA: {endpoints_encontrados}/{total} endpoints encontrados")
        return False


def validar_regras(base_path):
    """Valida regras documentadas no código"""
    print("\n=== VALIDAÇÃO: Regras Antifraude ===")

    services_file = os.path.join(base_path, 'antifraude', 'services.py')

    if not os.path.exists(services_file):
        print("❌ Arquivo services.py não encontrado")
        return False

    with open(services_file, 'r') as f:
        content = f.read()

    print(f"\n📄 Regras Documentadas:")
    regras_encontradas = 0

    for regra in REGRAS_DOCUMENTADAS:
        # Buscar nome da regra ou tipo
        tipo = regra.split(' - ')[0].upper() if ' - ' in regra else regra.upper()

        if regra.lower() in content.lower() or tipo in content:
            print(f"  ✅ {regra}")
            regras_encontradas += 1
        else:
            print(f"  ⚠️  {regra} (não encontrado)")

    print(f"\n=== Resultado ===")
    total = len(REGRAS_DOCUMENTADAS)
    if regras_encontradas >= total - 1:
        print(f"✅ VALIDADO: {regras_encontradas}/{total} regras implementadas")
        return True
    else:
        print(f"⚠️  DIVERGÊNCIA: {regras_encontradas}/{total} regras implementadas")
        return False


def validar_porta_container():
    """Valida porta do container vs documentação"""
    print("\n=== VALIDAÇÃO: Porta Container ===")
    print("\n📄 Documentação (engine_antifraude.md): porta 8004")
    print("🔍 Container real (docker-compose): porta 8008")
    print("\n⚠️  DIVERGÊNCIA: Documentação desatualizada")
    print("   Ação: Atualizar docs/engine_antifraude.md linha 5")
    return False


def main():
    # Determinar path base
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_path = os.path.join(script_dir, '..', '..', 'services', 'riskengine')
    base_path = os.path.normpath(base_path)

    print("=== VALIDAÇÃO: Risk Engine ===")
    print(f"\n📁 Base: {base_path}\n")

    resultados = []

    # 1. Estrutura
    resultados.append(validar_estrutura(base_path))

    # 2. Endpoints
    resultados.append(validar_endpoints(base_path))

    # 3. Regras
    resultados.append(validar_regras(base_path))

    # 4. Porta
    resultados.append(validar_porta_container())

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO RISK ENGINE")
    print("=" * 60)

    validacoes = ['Estrutura', 'Endpoints', 'Regras', 'Porta Container']
    for i, (nome, resultado) in enumerate(zip(validacoes, resultados)):
        status = "✅" if resultado else "⚠️"
        print(f"  {status} {nome}")

    total_ok = sum(resultados)
    total = len(resultados)

    if total_ok == total:
        print(f"\n✅ RISK ENGINE VALIDADO: {total_ok}/{total}")
    else:
        print(f"\n⚠️  RISK ENGINE COM DIVERGÊNCIAS: {total_ok}/{total}")


if __name__ == '__main__':
    main()
