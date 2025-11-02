#!/usr/bin/env python3
"""
Script temporário para exportar transações de clientes específicos para CSV
"""

import os
import sys
import django
import csv
from datetime import datetime

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.base')
django.setup()

from django.db import connection

def executar_query_e_exportar():
    """
    Executa a query de transações e exporta para CSV
    """
    query = """
    SELECT DISTINCT 
           c.cnpj, 
           c.razao_social,
           STR_TO_DATE(CONCAT(btg.var0, ' ', btg.var1), '%d/%m/%Y %H:%i:%s') AS data_hora,
           btg.var0,
           btg.var1,
           btg.var2,
           btg.var3,
           btg.var4,
           btg.var5,
           btg.var6,
           btg.var7,
           btg.var8,
           btg.var9,
           btg.var10,
           btg.var11,
           btg.var12,
           btg.var13,
           btg.var14,
           btg.var15,
           btg.var16,
           btg.var17,
           btg.var18,
           btg.var19,
           btg.var20,
           btg.var21,
           btg.var22,
           btg.var23,
           btg.var24,
           btg.var25,
           btg.var26,
           btg.var27,
           btg.var28,
           btg.var29,
           btg.var30,
           btg.var31,
           btg.var32,
           btg.var33,
           btg.var34,
           btg.var35,
           btg.var36,
           btg.var37,
           btg.var38,
           btg.var39,
           btg.var40,
           btg.var41,
           btg.var42,
           btg.var43,
           btg.var44,
           btg.var45,
           btg.var46,
           btg.var47,
           btg.var48,
           btg.var49,
           btg.var50,
           btg.var51,
           btg.var52,
           btg.var53,
           btg.var54,
           btg.var55,
           btg.var56,
           btg.var57,
           btg.var58,
           btg.var59,
           btg.var60,
           btg.var60_A,
           btg.var61,
           btg.var61_A,
           btg.var62,
           btg.var63,
           btg.var64,
           btg.var65,
           btg.var66,
           btg.var67,
           btg.var68,
           btg.var69,
           btg.var70,
           btg.var71,
           btg.var72,
           btg.var73,
           btg.var74,
           btg.var75,
           btg.var76,
           btg.var77,
           btg.var78,
           btg.var79,
           btg.var80,
           btg.var81,
           btg.var82,
           btg.var83,
           btg.var84,
           btg.var85,
           btg.var86,
           btg.var87,
           btg.var88,
           btg.var89,
           btg.var90,
           btg.var91,
           btg.var92,
           btg.var93,
           btg.var93_A,
           btg.var94,
           btg.var94_A,
           btg.var94_B,
           btg.var95,
           btg.var96,
           btg.var97,
           btg.var98,
           btg.var99,
           btg.var100,
           btg.var101,
           btg.var102,
           btg.var103,
           btg.var103_A,
           btg.var104,
           btg.var105,
           btg.var106,
           btg.var107,
           btg.var107_A,
           btg.var108,
           btg.var109,
           btg.var109_A,
           btg.var110,
           btg.var111,
           btg.var111_A,
           btg.var111_B,
           btg.var112,
           btg.var112_A,
           btg.var112_B,
           btg.var113,
           btg.var113_A,
           btg.var114,
           btg.var114_A,
           btg.var115,
           btg.var115_A,
           btg.var116,
           btg.var116_A,
           btg.var117,
           btg.var117_A,
           btg.var118,
           btg.var118_A,
           btg.var119,
           btg.var120,
           btg.var121,
           btg.var122,
           btg.var123,
           btg.var124,
           btg.var125,
           btg.var126,
           btg.var127,
           btg.var128,
           btg.var129,
           btg.var130
    FROM   wclub.clientes c,
           wclub.baseTransacoesGestao btg 
    WHERE  c.id IN (9,14,27,28,29,30)
           AND btg.var6 = c.id
    ORDER BY data_hora DESC
    """
    
    # Executar query
    with connection.cursor() as cursor:
        cursor.execute(query)
        
        # Obter nomes das colunas
        columns = [col[0] for col in cursor.description]
        
        # Obter dados
        rows = cursor.fetchall()
        
        print(f"Query executada com sucesso. {len(rows)} registros encontrados.")
        
        # Gerar nome do arquivo com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_csv = f"/app/logs/transacoes_clientes_{timestamp}.csv"
        
        # Escrever CSV
        with open(arquivo_csv, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            
            # Escrever cabeçalho
            writer.writerow(columns)
            
            # Escrever dados
            for row in rows:
                # Converter None para string vazia e formatar decimais
                formatted_row = []
                for value in row:
                    if value is None:
                        formatted_row.append('')
                    elif isinstance(value, (int, float)):
                        formatted_row.append(str(value))
                    else:
                        formatted_row.append(str(value))
                writer.writerow(formatted_row)
        
        print(f"Arquivo CSV gerado: {arquivo_csv}")
        print(f"Total de colunas: {len(columns)}")
        print(f"Total de linhas: {len(rows)}")
        
        # Mostrar primeiras colunas para verificação
        print("\nPrimeiras 10 colunas:")
        for i, col in enumerate(columns[:10]):
            print(f"  {i+1}. {col}")
        
        if len(columns) > 10:
            print(f"  ... e mais {len(columns) - 10} colunas")
        
        return arquivo_csv

if __name__ == "__main__":
    try:
        arquivo_gerado = executar_query_e_exportar()
        print(f"\n✅ Exportação concluída com sucesso!")
        print(f"📁 Arquivo: {arquivo_gerado}")
        
    except Exception as e:
        print(f"❌ Erro durante a exportação: {str(e)}")
        sys.exit(1)
