#!/usr/bin/env python
"""
Script de teste para verificar se as APIs Own estão funcionando
"""
import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.portais')
django.setup()

from adquirente_own.services_consultas import ConsultasOwnService

def testar_cnae():
    print("\n🔍 Testando consulta CNAE...")
    try:
        service = ConsultasOwnService(environment='LIVE')
        resultado = service.consultar_atividades()

        if resultado.get('sucesso'):
            dados = resultado.get('dados', [])
            print(f"✅ CNAE: {len(dados)} atividades retornadas")
            if dados:
                print(f"   Exemplo: {dados[0]}")
        else:
            print(f"❌ CNAE: {resultado.get('mensagem')}")

    except Exception as e:
        print(f"❌ Erro ao consultar CNAE: {str(e)}")
        import traceback
        traceback.print_exc()

def testar_cestas():
    print("\n🔍 Testando consulta Cestas...")
    try:
        service = ConsultasOwnService(environment='LIVE')
        resultado = service.consultar_cestas()

        if resultado.get('sucesso'):
            dados = resultado.get('dados', [])
            print(f"✅ Cestas: {len(dados)} cestas retornadas")
            if dados:
                print(f"   Exemplo: {dados[0]}")
        else:
            print(f"❌ Cestas: {resultado.get('mensagem')}")

    except Exception as e:
        print(f"❌ Erro ao consultar Cestas: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("TESTE DE APIS OWN FINANCIAL")
    print("=" * 60)

    testar_cnae()
    testar_cestas()

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)
