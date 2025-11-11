#!/usr/bin/env python
"""
Script para executar cargas completas sequencialmente:
1. Carga extrato POS (30min)
2. Carga base gestão (recalcula variáveis)
3. Carga Credenciadora (transações de terminais não cadastrados)

Uso:
    python pinbank/cargas_pinbank/executar_cargas_completas.py
    ou
    python manage.py shell -c "exec(open('pinbank/cargas_pinbank/executar_cargas_completas.py').read())"
"""

import os
import sys
import django
from datetime import datetime
from io import StringIO

# Adicionar diretório raiz do projeto ao PYTHONPATH
sys.path.insert(0, '/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')
django.setup()

from django.core.management import call_command

def log_message(message):
    """Log com timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def executar_comando(comando_args, descricao):
    """Executa um management command Django"""
    log_message(f"🔄 Iniciando: {descricao}")
    
    try:
        # Capturar output
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        # Executar comando Django
        call_command(*comando_args)
        
        # Restaurar stdout
        sys.stdout = old_stdout
        output = captured_output.getvalue()
        
        log_message(f"✅ Concluído: {descricao}")
        if output.strip():
            print(output)
        return True
            
    except Exception as e:
        # Restaurar stdout em caso de erro
        sys.stdout = old_stdout
        log_message(f"❌ Exceção em: {descricao} - {str(e)}")
        return False

def main():
    """Executa sequência completa de cargas"""
    log_message("🚀 Iniciando cargas completas sequenciais")
    
    comandos = [
        {
            'comando_args': ['carga_extrato_pos', '80min'],
            'descricao': 'Carga extrato POS (últimos 80 minutos)'
        },
        {
            'comando_args': ['carga_base_gestao', '--limite=10000'],
            'descricao': 'Carga base gestão (recálculo de variáveis - 10000 registros)'
        },
        {
            'comando_args': ['carga_credenciadora', '--limite=10000'],
            'descricao': 'Carga Credenciadora (transações de terminais não cadastrados - 10000 registros)'
        },
        {
            'comando_args': ['ajustes_manuais_base'],
            'descricao': 'Ajustes manuais de base (correções de inconsistências)'
        }
    ]
    
    sucesso_total = True
    
    for i, cmd_info in enumerate(comandos, 1):
        log_message(f"📋 Etapa {i}/{len(comandos)}")
        
        sucesso = executar_comando(cmd_info['comando_args'], cmd_info['descricao'])
        
        if not sucesso:
            log_message(f"💥 Falha na etapa {i}. Interrompendo execução.")
            sucesso_total = False
            break
        
        log_message(f"⏱️ Etapa {i} concluída. Prosseguindo...")
    
    if sucesso_total:
        log_message("🎉 Todas as cargas executadas com sucesso!")
    else:
        log_message("⚠️ Execução interrompida devido a erro.")
        return False
    
    return True

# Executar automaticamente quando carregado via shell
main()
