#!/usr/bin/env python3
"""
Script para migrar imports de 'comum' para 'wallclub_core'
"""
import os
import re
from pathlib import Path


def migrate_file(file_path):
    """Migra imports em um arquivo específico."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    
    # Padrões de substituição
    patterns = [
        (r'from comum\.', 'from wallclub_core.'),
        (r'from comum import', 'from wallclub_core import'),
        (r'import comum\.', 'import wallclub_core.'),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    # Só escreve se houve mudanças
    if content != original_content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


def migrate_project(project_path, exclude_dirs=None):
    """Migra todos os arquivos Python de um projeto."""
    if exclude_dirs is None:
        exclude_dirs = {'venv', 'env', '__pycache__', '.git', 'migrations', 'comum'}
    
    project_path = Path(project_path)
    files_updated = 0
    
    for py_file in project_path.rglob('*.py'):
        # Ignora diretórios excluídos
        if any(excluded in py_file.parts for excluded in exclude_dirs):
            continue
        
        try:
            if migrate_file(py_file):
                files_updated += 1
                print(f"✓ {py_file.relative_to(project_path)}")
        except Exception as e:
            print(f"✗ Erro em {py_file}: {e}")
    
    return files_updated


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Uso: python migrate_imports.py <caminho_do_projeto>")
        sys.exit(1)
    
    project_path = sys.argv[1]
    
    print(f"Migrando imports em: {project_path}")
    print("-" * 60)
    
    files_updated = migrate_project(project_path)
    
    print("-" * 60)
    print(f"\n✓ {files_updated} arquivos atualizados")
