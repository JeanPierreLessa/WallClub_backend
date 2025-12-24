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
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.pos')
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
        # Executar comando Django SEM capturar output
        # Deixa o output ir direto para stdout/logs
        call_command(*comando_args)

        log_message(f"✅ Concluído: {descricao}")
        return True

    except Exception as e:
        log_message(f"❌ Exceção em: {descricao} - {str(e)}")
        import traceback
        traceback.print_exc()
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
            'comando_args': ['carga_base_unificada', '--limite=5000'],
            'descricao': 'Carga Base Unificada - POS + Credenciadora + Checkout (5000 registros cada)'
        },
        {
            'comando_args': ['ajustes_manuais_base'],
            'descricao': 'Ajustes manuais de base (insere em transactiondata_pos)'
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
