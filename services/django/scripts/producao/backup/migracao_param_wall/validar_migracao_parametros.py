#!/usr/bin/env python3
"""
VALIDAÇÃO DA MIGRAÇÃO DE PARÂMETROS
Compara dados migrados no Django vs sistema legado
"""

import os
import sys
import django
import pymysql
import json

# Configurar Django para PRODUÇÃO
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.models import ParametrosWall

def conectar_banco_legado():
    """Conecta ao banco legado wclub."""
    return pymysql.connect(
        host='10.0.1.107',
        user='user_python',
        password='sblYcQ(@p.9',
        database='wclub',
        charset='utf8mb4'
    )

def buscar_parametros_django(loja_id, id_plano, wall):
    """Busca parâmetros no Django."""
    try:
        config = ParametrosWall.objects.get(
            loja_id=loja_id,
            id_plano=id_plano,
            wall=wall,
            vigencia_fim__isnull=True
        )
        
        # Extrair apenas parametro_loja_1 a parametro_loja_30
        parametros = {}
        for i in range(1, 31):
            campo = f'parametro_loja_{i}'
            valor = getattr(config, campo, None)
            # Incluir todos os parâmetros, mesmo None
            parametros[i] = str(valor) if valor is not None else None
        
        return parametros
    except ParametrosWall.DoesNotExist:
        return {}

def buscar_parametros_legado(loja_id, id_plano_legado):
    """Busca parâmetros no sistema legado."""
    conn = conectar_banco_legado()
    cursor = conn.cursor()
    
    sql = """
    SELECT
      /* parâmetros desse id_desc (plano específico) em JSON */
      (
        SELECT JSON_ARRAYAGG(JSON_OBJECT('parametro', p.parametro, 'valor', p.valor))
        FROM wclub.parametros_loja p
        WHERE p.id_desc = (
          SELECT r2.id_desc
          FROM wclub.rel_loja_param r2
          WHERE r2.id_cliente = %s
          ORDER BY r2.inicio DESC, r2.id DESC
          LIMIT 1
        )
          AND p.id_plano = %s
      ) AS parametros_json
    """
    
    cursor.execute(sql, (loja_id, id_plano_legado))
    resultado = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if not resultado or not resultado[0]:
        return {}
    
    # Processar JSON
    parametros_list = json.loads(resultado[0])
    parametros = {}
    
    for item in parametros_list:
        parametro = item['parametro']
        valor = item['valor']
        if 1 <= parametro <= 30:
            parametros[parametro] = str(valor) if valor is not None else None
    
    return parametros

def validar_loja_plano(loja_id, id_plano, wall):
    """Valida uma combinação específica loja/plano/wall."""
    
    # Mapear para plano legado
    if wall == 'S':
        id_plano_legado = id_plano
    else:  # wall == 'N'
        id_plano_legado = id_plano + 999
    
    # Buscar dados (sem print de progresso)
    parametros_django = buscar_parametros_django(loja_id, id_plano, wall)
    parametros_legado = buscar_parametros_legado(loja_id, id_plano_legado)
    
    # Comparar
    divergencias = 0
    for i in range(1, 31):
        valor_django = parametros_django.get(i)
        valor_legado = parametros_legado.get(i)
        
        # Normalizar valores para comparação
        def normalizar_valor(valor):
            if valor is None or valor == 'None':
                return None
            try:
                # Tentar converter para float e depois string sem zeros desnecessários
                return str(float(valor)).rstrip('0').rstrip('.')
            except (ValueError, TypeError):
                return str(valor)
        
        valor_django_norm = normalizar_valor(valor_django)
        valor_legado_norm = normalizar_valor(valor_legado)
        
        if valor_django_norm != valor_legado_norm:
            divergencias += 1
            # Só printa se há divergências
            if divergencias == 1:  # Primeira divergência, mostra cabeçalho
                print(f"\n❌ ERRO - Loja {loja_id}, Plano {id_plano}, Wall {wall} (Plano legado: {id_plano_legado})")
            print(f"   Param {i}: Django='{valor_django}' vs Legado='{valor_legado}'")
    
    return divergencias == 0

def main():
    """Executa validação."""
    print("🚀 Iniciando validação da migração de parâmetros...")
    
    # Buscar todos os casos da base de dados
    print("📋 Buscando todos os casos da base de dados...")
    casos_teste = list(ParametrosWall.objects.filter(
        vigencia_fim__isnull=True
    ).values_list('loja_id', 'id_plano', 'wall').order_by('loja_id', 'id_plano', 'wall'))
    
    print(f"📊 Total de casos encontrados: {len(casos_teste)}")
    print("🔍 Validando... (mostrando apenas erros)\n")
    
    sucessos = 0
    total = len(casos_teste)
    
    for loja_id, id_plano, wall in casos_teste:
        if validar_loja_plano(loja_id, id_plano, wall):
            sucessos += 1
    
    print(f"\n🎉 Validação concluída!")
    print(f"📊 Sucessos: {sucessos}/{total}")
    print(f"📈 Taxa de sucesso: {(sucessos/total)*100:.1f}%")
    
    if sucessos == total:
        print("✅ Migração validada com sucesso!")
    else:
        print(f"❌ Encontradas divergências: {total - sucessos} casos com problemas")

if __name__ == '__main__':
    main()
