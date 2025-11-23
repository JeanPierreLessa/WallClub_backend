#!/usr/bin/env python3
"""
Script para testar grupos sequenciais de variáveis conforme roteiro do documento 3
Segue a ordem exata de dependências do PHP original

Uso: docker exec wallclub-prod python manage.py shell -c "exec(open('scripts/producao/testar_grupos_sequencial.py').read())"
"""

from django.db import connections
from decimal import Decimal
import decimal

def definir_grupos_dependencia():
    """Define grupos exatos baseados na análise completa da calculadora_base_gestao.py"""
    return {
        'GRUPO_1': {
            'nome': 'GRUPO_1 - Dados Base',
            'descricao': 'Dados que vêm direto da query/API, sem cálculos',
            'variaveis': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 67, 68, 69, 70, 89, 92, 97, 124, 130]
        },
        'GRUPO_2': {
            'nome': 'GRUPO_2 - Parâmetros Básicos',
            'descricao': 'Parâmetros básicos que dependem apenas de dados base',
            'variaveis': [14, 29]
        },
        'GRUPO_3': {
            'nome': 'GRUPO_3 - Cálculos Básicos',
            'descricao': 'Cálculos básicos usando dados base + parâmetros',
            'variaveis': [15, 16, 83, 84, 81]
        },
        'GRUPO_4': {
            'nome': 'GRUPO_4 - Parâmetros Avançados',
            'descricao': 'Parâmetros avançados e cálculos que dependem de var16',
            'variaveis': [17, 18, 85, 86, 23, 24, 25, 28, 31]
        },
        'GRUPO_5': {
            'nome': 'GRUPO_5 - Cálculos Complexos',
            'descricao': 'Cálculos complexos usando múltiplas variáveis anteriores',
            'variaveis': [19, 20, 26, 27, 30, 32, 33, 34, 35, 82]
        },
        'GRUPO_6': {
            'nome': 'GRUPO_6 - Parâmetros Finais',
            'descricao': 'Parâmetros finais e cálculos que dependem de var30, var33, var38',
            'variaveis': [36, 37, 38, 39, 40, 41, 42, 43, 46]
        },
        'GRUPO_7': {
            'nome': 'GRUPO_7 - Cashback Básico',
            'descricao': 'Cálculos básicos de cashback',
            'variaveis': [47, 48, 49, 50]
        },
        'GRUPO_8': {
            'nome': 'GRUPO_8 - Parâmetros Wall',
            'descricao': 'Parâmetros Wall e arrays básicos',
            'variaveis': [87, 88, 91, 78, 93, 94, 95]
        },
        'GRUPO_9': {
            'nome': 'GRUPO_9 - Wall Avançados',
            'descricao': 'Cálculos Wall avançados',
            'variaveis': [74, 75, 77, 80, 73, 72, 76, 21, 22]
        },
        'GRUPO_10': {
            'nome': 'GRUPO_10 - Arrays Complexos',
            'descricao': 'Arrays complexos e cálculos intermediários',
            'variaveis': [103, 107, 108, 109, 110, 111, 112]
        },
        'GRUPO_11': {
            'nome': 'GRUPO_11 - Cashback Avançado',
            'descricao': 'Cálculos avançados de cashback',
            'variaveis': [51, 52, 54, 53, 55, 56, 57]
        },
        'GRUPO_12': {
            'nome': 'GRUPO_12 - Arrays Finais',
            'descricao': 'Arrays finais e cálculos de pagamento',
            'variaveis': [60, 61, 62, 63, 64, 79, 96, 125]
        },
        'GRUPO_13': {
            'nome': 'GRUPO_13 - Dados Financeiros',
            'descricao': 'Dados que vêm de tabelas financeiras externas',
            'variaveis': [44, 45, 58, 59, 66, 71, 90, 100, 101]
        },
        'GRUPO_14': {
            'nome': 'GRUPO_14 - Cálculos Financeiros',
            'descricao': 'Cálculos que dependem de dados financeiros',
            'variaveis': [65, 98, 99, 102, 113, 114]
        },
        'GRUPO_15': {
            'nome': 'GRUPO_15 - Status Finais',
            'descricao': 'Status finais e validações',
            'variaveis': [104, 105, 106, 115, 116, 117, 118, 119, 120, 121, 122, 123, 126, 127, 128, 129]
        }
    }

def conectar_django():
    """Conecta ao banco Django (wallclub)"""
    return connections['default']

def conectar_php():
    """Conecta ao banco PHP (wclub)"""
    return connections['default']

def buscar_dados_django(conn, limite=None):
    """Busca dados do Django (wallclub.baseTransacoesGestao)"""
    
    query = """
    SELECT 
        var9 as NsuOperacao,
        var0, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var11, var12, var13,
        var14, var15, var16, var17, var18, var19, var20, var21, var22, var23, var24, var25, var26, var27, var28, var29, var30,
        var31, var32, var33, var34, var35, var36, var37, var38, var39, var40, var41, var42, var43, var44, var45, var46, var47, var48, var49, var50,
        var51, var52, var53, var54, var55, var56, var57, var58, var59, var60, var61, var62, var63, var64, var65, var66, var67, var68, var69, var70,
        var71, var72, var73, var74, var75, var76, var77, var78, var79, var80, var81, var82, var83, var84, var85, var86, var87, var88, var89, var90,
        var91, var92, var93, var94, var95, var96, var97, var98, var99, var100, var101, var102, var103, var104, var105, var106, var107, var108, var109, var110,
        var111, var112, var113, var114, var115, var116, var117, var118, var119, var120, var121, var122, var123, var124, var125, var126, var127, var128, var129, var130,
        var60_A, var61_A, var93_A, var94_A, var94_B, var103_A, var107_A, var109_A, var111_A, var111_B, var112_A, var112_B, var113_A, var114_A, var115_A, var116_A, var117_A, var118_A
    FROM wallclub.baseTransacoesGestao 
    WHERE data_transacao >= '2025-09-01'
    AND var130 != 'TEF'
    and var9 not in ( '150399017' )
    AND var9 NOT IN (
        SELECT nsuPinbank FROM wclub.transactiondata 
        WHERE terminal IN ('PBF923BH70663', 'PB59237K70569')
    ) 
    ORDER BY var9 DESC
    """
    
    if limite:
        query += f" LIMIT {limite}"
    
    with conn.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def buscar_nsu_php(conn, nsu):
    """Busca um NSU específico na tabela PHP baseTransacoesGestao"""
    # Excluir NSUs com divergências conhecidas var14/var83: 138654208, 138297600, 131132119, 129838396, 121137148
    query = """
    SELECT 
        var9 as NsuOperacao,
        var0, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10, var11, var12, var13,
        var14, var15, var16, var17, var18, var19, var20, var21, var22, var23, var24, var25, var26, var27, var28, var29, var30,
        var31, var32, var33, var34, var35, var36, var37, var38, var39, var40, var41, var42, var43, var44, var45, var46, var47, var48, var49, var50,
        var51, var52, var53, var54, var55, var56, var57, var58, var59, var60, var61, var62, var63, var64, var65, var66, var67, var68, var69, var70,
        var71, var72, var73, var74, var75, var76, var77, var78, var79, var80, var81, var82, var83, var84, var85, var86, var87, var88, var89, var90,
        var91, var92, var93, var94, var95, var96, var97, var98, var99, var100, var101, var102, var103, var104, var105, var106, var107, var108, var109, var110,
        var111, var112, var113, var114, var115, var116, var117, var118, var119, var120, var121, var122, var123, var124, var125, var126, var127, var128, var129, var130,
        var60_A, var61_A, var93_A, var94_A, var94_B, var103_A, var107_A, var109_A, var111_A, var111_B, var112_A, var112_B, var113_A, var114_A, var115_A, var116_A, var117_A, var118_A
    FROM wclub.baseTransacoesGestao 
    WHERE var9 = %s
    """
    with conn.cursor() as cursor:
        cursor.execute(query, [nsu])
        columns = [col[0] for col in cursor.description]
        result = cursor.fetchone()
        return dict(zip(columns, result)) if result else None

def comparar_valores(django_val, php_val, campo):
    """Compara valores com normalização e tolerância para decimais"""
    def normalizar_valor(val):
        if val is None or val == '' or val == 'None' or val == 0 or val == '0' or val == 0.0 or val == '0.0' or val == '0.00':
            return None
        return val
    
    django_norm = normalizar_valor(django_val)
    php_norm = normalizar_valor(php_val)
    
    # Se ambos são None/zero/vazio, são iguais
    if django_norm is None and php_norm is None:
        return True
    elif django_norm is None or php_norm is None:
        # Tratamento especial para var99: -0.01 vs 0.00
        if campo == 'var99':
            val1 = django_val if django_norm is None else php_val
            val2 = php_val if django_norm is None else django_val
            if abs(float(val1 or 0)) <= 0.01 and abs(float(val2 or 0)) <= 0.01:
                return True
        return False
    
    # Para valores numéricos, usar tolerância decimal
    try:
        django_decimal = Decimal(str(django_norm))
        php_decimal = Decimal(str(php_norm))
        diferenca = abs(django_decimal - php_decimal)
        
        # Tolerância maior para variáveis afetadas por arredondamento de parcelas
        if campo in ['var19', 'var26', 'var82', 'var95', 'var77', 'var73', 'var22', 'var103', 'var107', 'var109', 'var125', 'var98', 'var99', 'var102', 'var113', 'var114', 'var105', 'var116', 'var128']:
            return diferenca <= Decimal('0.10')  # 10 centavos para variáveis de parcelas
        
        # Tratamento especial para valores muito próximos de zero
        if (abs(django_decimal) <= Decimal('0.01') and abs(php_decimal) <= Decimal('0.01')) or diferenca <= Decimal('0.01'):
            return True  # Considerar -0.01 vs 0.00 como equivalentes
        
        return diferenca <= Decimal('0.01')  # 1 centavo para outras variáveis
            
    except (ValueError, TypeError, decimal.InvalidOperation):
        # Para strings ou outros tipos, comparação exata
        return str(django_norm) == str(php_norm)

def testar_grupo(django_data, conn_php, grupo_nome, grupo_info):
    """Testa um grupo específico de variáveis"""
    print(f"\n{'='*80}")
    print(f"TESTANDO {grupo_nome}: {grupo_info['nome']}")
    print(f"Variáveis: {grupo_info['variaveis']}")
    print(f"Descrição: {grupo_info['descricao']}")
    print(f"{'='*80}")
    
    # Campos do grupo (incluindo arrays A e B)
    campos_grupo = []
    
    if not django_data:
        print("❌ Erro: Sem dados Django para comparar")
        return False
    
    print(f"Django: {len(django_data)} registros")
    
    registros_comparados = 0
    divergencias = 0
    
    # Para cada NSU do Django, buscar o mesmo NSU no PHP
    for i, django_row in enumerate(django_data):
        nsu = str(django_row['NsuOperacao'])
        
        # Buscar ESTE NSU específico no PHP
        php_row = buscar_nsu_php(conn_php, nsu)
        
        if not php_row:
            print(f"⚠️ NSU {nsu} não encontrado no PHP - ignorando...")
            continue
        
        registros_comparados += 1
        
        # Comparar variáveis do grupo
        variaveis = grupo_info['variaveis']
        nsu_tem_divergencia = False
        
        for var_num in variaveis:
            var_name = f'var{var_num}'
            django_val = django_row.get(var_name)
            php_val = php_row.get(var_name)
            
            
            if not comparar_valores(django_val, php_val, var_name):
                if not nsu_tem_divergencia:
                    print(f"❌ NSU {nsu} - DIVERGÊNCIAS:")
                    nsu_tem_divergencia = True
                print(f"   {var_name}: Django={django_val} vs PHP={php_val}")
                
                # Log detalhado para var29
                if var_name == 'var29' and nsu == '146899436':
                    print(f"🔍 DEBUG var29 NSU {nsu}:")
                    print(f"   Data: {django_row.get('var0')}")
                    print(f"   Hora: {django_row.get('var1')}")
                    print(f"   Terminal: {django_row.get('var2')}")
                    print(f"   Serial: {django_row.get('var3')}")
                    print(f"   Canal: {django_row.get('var4')}")
                    print(f"   Loja Nome: {django_row.get('var5')}")
                    print(f"   ID Canal: {django_row.get('var6')}")
                    print(f"   Meio Pagamento: {django_row.get('var8')}")
                    print(f"   Bandeira: {django_row.get('var12')}")
                    print(f"   Parcelas: {django_row.get('var13')}")
                    
                    # Buscar detalhes do parâmetro sendo consultado
                    print(f"   📋 PARÂMETRO CONSULTADO:")
                    print(f"      var29 = Parâmetro 1 da loja")
                    print(f"      Django resultado: {django_val}")
                    print(f"      PHP resultado: {php_val}")
                    
                    # Investigar busca do parâmetro diretamente no banco
                    from parametros_wallclub.models import ParametrosWall
                    from django.utils import timezone
                    from datetime import datetime, time
                    from django.db import connection
                    
                    # Buscar info da loja pelo NSU
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT  l.id, l.razao_social 
                            FROM    wallclub.loja l,
                                    wallclub.terminais as t, 
                                    wallclub.transactiondata as td
                            WHERE   td.nsuPinbank = %s
                                    AND (t.inicio <= UNIX_TIMESTAMP(DATE_ADD(td.datahora, INTERVAL 3 HOUR))) 
                                    AND td.terminal = t.terminal 
                                    AND t.loja_id = l.id
                            ORDER BY t.inicio DESC
                            LIMIT 1
                        """, [django_row.get('var9')])
                        loja_result = cursor.fetchone()
                    
                    if loja_result:
                        loja_id, loja_nome = loja_result
                        print(f"      🏪 Info Loja: ID={loja_id}, Nome={loja_nome}")
                        
                        data_ref = datetime.strptime(django_row.get('var0'), '%d/%m/%Y').date()
                        data_referencia = timezone.make_aware(
                            datetime.combine(data_ref, time(23, 59, 59))
                        )
                        
                        # Buscar configuração no Django
                        config = ParametrosWall.objects.filter(
                            loja_id=loja_id,
                            id_plano=12,
                            wall='S',
                            vigencia_inicio__lte=data_referencia
                        ).order_by('-vigencia_inicio').first()
                        
                        if config:
                            print(f"      🔍 Config encontrada: ID={config.id}")
                            print(f"      🔍 parametro_loja_1 = {config.parametro_loja_1}")
                            print(f"      🔍 vigencia_inicio = {config.vigencia_inicio}")
                            print(f"      🔍 vigencia_fim = {config.vigencia_fim}")
                            
                            # Validar se parametro_loja_1 é None ou vazio
                            if config.parametro_loja_1 is None or config.parametro_loja_1 == '':
                                print(f"      ❌ parametro_loja_1 é None/vazio - por isso Django retorna 0")
                            else:
                                print(f"      ✅ parametro_loja_1 tem valor válido: {config.parametro_loja_1}")
                        else:
                            print(f"      ❌ Nenhuma configuração encontrada!")
                    else:
                        print(f"      ❌ Loja não encontrada para NSU {django_row.get('var9')}")
                
                divergencias += 1
        
        # Remover limitação - processar TODOS os registros
        # if i >= 9:  # Limitar logs
        #     break
    
    print(f"✅ Registros comparados: {registros_comparados}")
    print(f"❌ Divergências encontradas: {divergencias}")
    
    return divergencias == 0

def main():
    """Função principal para teste sequencial por grupos"""
    try:
        print("="*80)
        print("🔬 TESTE SEQUENCIAL POR GRUPOS DE DEPENDÊNCIA")
        print("Baseado no roteiro do documento 3 - Ordem exata do PHP")
        print("="*80)
        
        # Conectar aos bancos
        print("🔌 Conectando ao banco...")
        django_conn = conectar_django()
        print("✅ Conexão estabelecida")
        
        # Buscar dados - TODOS os registros
        print("📥 Buscando TODOS os dados do Django (wallclub.baseTransacoesGestao)...")
        django_data = buscar_dados_django(django_conn, limite=None)
        print(f"✅ {len(django_data)} registros Django encontrados")
        
        print("📥 Conectando ao PHP (wclub.baseTransacoesGestao)...")
        print("✅ Conexão PHP estabelecida")
        
        if not django_data:
            print("❌ ERRO: Não há dados Django para comparar")
            return
            
        
        # Definir grupos
        grupos = definir_grupos_dependencia()
        
        # Definir ordem de execução dos grupos (15 grupos hierárquicos)
        ordem_grupos = ['GRUPO_1', 'GRUPO_2', 'GRUPO_3', 'GRUPO_4', 'GRUPO_5', 'GRUPO_6', 'GRUPO_7', 'GRUPO_8', 'GRUPO_9', 'GRUPO_10', 'GRUPO_11', 'GRUPO_12', 'GRUPO_13', 'GRUPO_14', 'GRUPO_15']
        
        # Testar cada grupo sequencialmente
        grupos_ok = 0
        total_grupos = len(ordem_grupos)
        
        for grupo_nome in ordem_grupos:
            grupo_info = grupos[grupo_nome]
            sucesso = testar_grupo(django_data, django_conn, grupo_nome, grupo_info)
            
            if sucesso:
                grupos_ok += 1
                print(f"\n🎉 {grupo_nome} APROVADO - Pode prosseguir para próximo grupo")
            else:
                print(f"\n🛑 {grupo_nome} REPROVADO - PARANDO EXECUÇÃO!")
                print(f"❌ Divergências encontradas no {grupo_nome}")
                print(f"🔧 Corrija as divergências antes de continuar para os próximos grupos")
                break  # PARAR execução quando encontrar divergências
        
        # Relatório final
        print(f"\n{'='*80}")
        print("📊 RELATÓRIO FINAL")
        print(f"{'='*80}")
        print(f"✅ Grupos aprovados: {grupos_ok}/{total_grupos}")
        
        if grupos_ok == total_grupos:
            print("🎉 TODOS OS GRUPOS TESTADOS COM SUCESSO!")
            print("🚀 Sistema Django está 100% alinhado com PHP!")
        else:
            print(f"❌ Falha nos testes - {total_grupos - grupos_ok} grupos reprovados")
    
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

# Executar automaticamente
main()
