#!/usr/bin/env python
"""
Script de diagnóstico para identificar problemas na busca de parâmetros
"""

import os
import sys
import django

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.services import RetornaParametrosWall
from parametros_wallclub.models import ParametrosWall
from datetime import datetime
from django.db import connection

def diagnosticar_parametros():
    """Diagnostica problemas na busca de parâmetros"""
    
    print("=== DIAGNÓSTICO DE PARÂMETROS ===")
    
    service = RetornaParametrosWall()
    
    # Dados de teste baseados na comparação
    id_loja = 1  # Assumindo loja 1
    id_plano = 1  # Assumindo plano 1
    data_ref = int(datetime.now().timestamp())
    wall = 's'
    
    print(f"Testando: Loja {id_loja}, Plano {id_plano}, Wall '{wall}'")
    print(f"Data referência: {datetime.fromtimestamp(data_ref)}")
    
    # 1. Verificar se existem configurações no banco
    print("\n1. VERIFICANDO CONFIGURAÇÕES NO BANCO:")
    configs = ParametrosWall.objects.filter(loja_id=id_loja)
    print(f"   Total configurações para loja {id_loja}: {configs.count()}")
    
    configs_plano = ParametrosWall.objects.filter(loja_id=id_loja, id_plano=id_plano)
    print(f"   Configurações para loja {id_loja}, plano {id_plano}: {configs_plano.count()}")
    
    configs_wall = ParametrosWall.objects.filter(loja_id=id_loja, id_plano=id_plano, wall=wall.upper())
    print(f"   Configurações para loja {id_loja}, plano {id_plano}, wall '{wall.upper()}': {configs_wall.count()}")
    
    if configs_wall.exists():
        config = configs_wall.first()
        print(f"   Configuração encontrada - ID: {config.id}")
        print(f"   vigencia_inicio: {config.vigencia_inicio}")
        print(f"   vigencia_fim: {config.vigencia_fim}")
        print(f"   parametro_loja_1: {config.parametro_loja_1}")
        print(f"   parametro_loja_7: {config.parametro_loja_7}")
        print(f"   parametro_loja_10: {config.parametro_loja_10}")
    
    # 2. Testar busca de parâmetros via service
    print("\n2. TESTANDO BUSCA VIA SERVICE:")
    
    param_1 = service.retorna_parametro_loja(id_loja, id_plano, 1, data_ref, wall)
    print(f"   Parâmetro 1: {param_1}")
    
    param_7 = service.retorna_parametro_loja(id_loja, id_plano, 7, data_ref, wall)
    print(f"   Parâmetro 7: {param_7}")
    
    param_10 = service.retorna_parametro_loja(id_loja, id_plano, 10, data_ref, wall)
    print(f"   Parâmetro 10: {param_10}")
    
    param_17 = service.retorna_parametro_loja(id_loja, id_plano, 17, data_ref, wall)
    print(f"   Parâmetro 17: {param_17}")
    
    # 3. Testar busca manual com filtros detalhados
    print("\n3. TESTANDO BUSCA MANUAL:")
    data_referencia = datetime.fromtimestamp(data_ref)
    
    manual_config = ParametrosWall.objects.filter(
        loja_id=id_loja,
        id_plano=id_plano,
        wall=wall.upper(),
        vigencia_inicio__lte=data_referencia
    ).order_by('-vigencia_inicio').first()
    
    if manual_config:
        print(f"   Configuração manual encontrada - ID: {manual_config.id}")
        print(f"   parametro_loja_1: {manual_config.parametro_loja_1}")
    else:
        print("   Nenhuma configuração encontrada na busca manual")
    
    # 4. Verificar todas as lojas disponíveis
    print("\n4. VERIFICANDO LOJAS DISPONÍVEIS:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT loja_id FROM parametros_wallclub ORDER BY loja_id LIMIT 10")
        lojas = cursor.fetchall()
        print(f"   Lojas com configurações: {[loja[0] for loja in lojas]}")
    
    # 5. Verificar planos disponíveis para loja 1
    print("\n5. VERIFICANDO PLANOS PARA LOJA 1:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT id_plano FROM parametros_wallclub WHERE loja_id = 1 ORDER BY id_plano LIMIT 20")
        planos = cursor.fetchall()
        print(f"   Planos para loja 1: {[plano[0] for plano in planos]}")
    
    # 6. Verificar wall disponíveis
    print("\n6. VERIFICANDO MODALIDADES WALL:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT wall FROM parametros_wallclub WHERE loja_id = 1 AND id_plano = 1")
        walls = cursor.fetchall()
        print(f"   Modalidades para loja 1, plano 1: {[w[0] for w in walls]}")

if __name__ == "__main__":
    diagnosticar_parametros()
