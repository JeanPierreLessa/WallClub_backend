#!/usr/bin/env python3
"""
Script para analisar dependências entre módulos do WallClub Django.
Mapeia imports para planejar separação em múltiplos containers.
"""

import os
import re
from collections import defaultdict
from pathlib import Path

# Diretório base do projeto
BASE_DIR = Path(__file__).parent.parent

# Módulos que serão separados
MODULES = {
    'APP1_PORTAIS': ['portais', 'sistema_bancario'],
    'APP2_POS': ['posp2', 'pinbank', 'parametros_wallclub'],
    'APP3_APIS': ['apps', 'checkout'],
    'CORE': ['comum'],
    'SETTINGS': ['wallclub'],
}

def extract_imports(file_path):
    """Extrai todos os imports de um arquivo Python."""
    imports = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Padrões de import
        patterns = [
            r'^from\s+([\w\.]+)\s+import',  # from X import Y
            r'^import\s+([\w\.]+)',          # import X
        ]
        
        for line in content.split('\n'):
            line = line.strip()
            for pattern in patterns:
                match = re.match(pattern, line)
                if match:
                    import_path = match.group(1)
                    imports.append(import_path)
                    
    except Exception as e:
        pass
    
    return imports

def get_module_group(import_path):
    """Identifica a qual grupo pertence um import."""
    for group, modules in MODULES.items():
        for module in modules:
            if import_path.startswith(module):
                return group
    return 'EXTERNAL'

def analyze_dependencies():
    """Analisa dependências entre módulos."""
    dependencies = defaultdict(lambda: defaultdict(int))
    file_count = defaultdict(int)
    
    # Percorre todos arquivos Python
    for root, dirs, files in os.walk(BASE_DIR):
        # Ignora alguns diretórios
        if any(x in root for x in ['venv', '.git', 'staticfiles', 'media', '__pycache__', 'migrations']):
            continue
            
        for file in files:
            if not file.endswith('.py'):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, BASE_DIR)
            
            # Identifica módulo do arquivo
            source_module = None
            for group, modules in MODULES.items():
                for module in modules:
                    if rel_path.startswith(module):
                        source_module = group
                        break
                if source_module:
                    break
            
            if not source_module:
                continue
                
            # Extrai imports
            imports = extract_imports(file_path)
            file_count[source_module] += 1
            
            for imp in imports:
                target_module = get_module_group(imp)
                if target_module != 'EXTERNAL' and target_module != source_module:
                    dependencies[source_module][target_module] += 1
    
    return dependencies, file_count

def print_report(dependencies, file_count):
    """Imprime relatório de dependências."""
    print("=" * 80)
    print("ANÁLISE DE DEPENDÊNCIAS - WALLCLUB DJANGO")
    print("=" * 80)
    print()
    
    print("📊 QUANTIDADE DE ARQUIVOS POR MÓDULO:")
    print("-" * 80)
    for module, count in sorted(file_count.items()):
        print(f"  {module:20s}: {count:4d} arquivos")
    print()
    
    print("🔗 DEPENDÊNCIAS ENTRE MÓDULOS:")
    print("-" * 80)
    
    for source in sorted(dependencies.keys()):
        print(f"\n{source}:")
        targets = dependencies[source]
        for target, count in sorted(targets.items(), key=lambda x: -x[1]):
            percentage = (count / file_count.get(source, 1)) * 100
            print(f"  → {target:20s}: {count:4d} imports ({percentage:.1f}% dos arquivos)")
    
    print()
    print("=" * 80)
    print("RECOMENDAÇÕES:")
    print("=" * 80)
    
    # Verifica dependências críticas
    critical_deps = []
    for source, targets in dependencies.items():
        if 'CORE' in targets:
            critical_deps.append((source, 'CORE', targets['CORE']))
    
    print(f"\n✅ Todos os módulos dependem de CORE (comum/):")
    for source, target, count in sorted(critical_deps, key=lambda x: -x[2]):
        print(f"  • {source}: {count} imports")
    
    print(f"\n🎯 Estratégia de separação:")
    print(f"  1. Extrair CORE (comum/) para wallclub-core package")
    print(f"  2. Instalar wallclub-core em todos containers")
    print(f"  3. Separar módulos mantendo acesso ao core")
    
    # Verifica dependências cruzadas (não através do CORE)
    cross_deps = []
    for source, targets in dependencies.items():
        for target, count in targets.items():
            if target != 'CORE' and target != 'SETTINGS':
                cross_deps.append((source, target, count))
    
    if cross_deps:
        print(f"\n⚠️  DEPENDÊNCIAS CRUZADAS (não via CORE):")
        for source, target, count in sorted(cross_deps, key=lambda x: -x[2]):
            print(f"  • {source} → {target}: {count} imports")
            print(f"    Ação: Refatorar para comunicação via API ou mover para CORE")
    else:
        print(f"\n✅ Nenhuma dependência cruzada detectada!")

if __name__ == '__main__':
    print("Analisando dependências...\n")
    dependencies, file_count = analyze_dependencies()
    print_report(dependencies, file_count)
    print("\nAnálise concluída!")
