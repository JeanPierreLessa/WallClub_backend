#!/usr/bin/env python3
"""
Script para comparar cálculos de desconto entre Django PRODUÇÃO e PHP PRODUÇÃO
Baseado no script local, mas adaptado para ambiente de produção

Uso: docker exec wallclub-prod python manage.py shell -c "exec(open('scripts/producao/comparar_django_prod_vs_php_prod.py').read())"
"""

import requests
from decimal import Decimal
from parametros_wallclub.services import CalculadoraDesconto

def definir_grupos_dependencia():
    """Define grupos de variáveis por dependência"""
    return {
        'BASE': {
            'vars': list(range(0, 14)),  # var0-13: dados brutos
            'descricao': 'Dados brutos - sem dependências'
        },
        'NIVEL_1': {
            'vars': [14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
            'descricao': 'Dependem apenas do BASE',
            'dependencias': ['BASE']
        },
        'NIVEL_2': {
            'vars': list(range(31, 61)),  # var31-60
            'descricao': 'Dependem de BASE + NÍVEL 1',
            'dependencias': ['BASE', 'NIVEL_1']
        },
        'NIVEL_3': {
            'vars': list(range(61, 91)),  # var61-90
            'descricao': 'Dependem de níveis anteriores',
            'dependencias': ['BASE', 'NIVEL_1', 'NIVEL_2']
        },
        'NIVEL_4': {
            'vars': list(range(91, 131)),  # var91-130
            'descricao': 'Dependem de todos anteriores',
            'dependencias': ['BASE', 'NIVEL_1', 'NIVEL_2', 'NIVEL_3']
        }
    }

def testar_grupo(django_data, php_data, grupo_nome, grupo_info):
    """Testa um grupo específico de variáveis"""
    print(f"\n{'='*80}")
    print(f"TESTANDO GRUPO {grupo_nome}: {grupo_info['descricao']}")
    print(f"Variáveis: var{min(grupo_info['vars'])}-var{max(grupo_info['vars'])}")
    if 'dependencias' in grupo_info:
        print(f"Dependências: {', '.join(grupo_info['dependencias'])}")
    print(f"{'='*80}")
    
    # Filtrar apenas campos deste grupo
    campos_grupo = []
    for var_num in grupo_info['vars']:
        campos_grupo.extend([f'var{var_num}', f'var{var_num}_A', f'var{var_num}_B'])
    
    # Comparar apenas este grupo
    divergencias_grupo = {}
    total_registros = len(django_data)
    
    for django_row in django_data:
        nsu = django_row['NsuPinbank']
        php_row = next((row for row in php_data if row['NsuPinbank'] == nsu), None)
        
        if php_row:
            for campo in campos_grupo:
                if campo in django_row and campo in php_row:
                    django_val = django_row[campo]
                    php_val = php_row[campo]
                    
                    if django_val != php_val:
                        if campo not in divergencias_grupo:
                            divergencias_grupo[campo] = []
                        divergencias_grupo[campo].append({
                            'nsu': nsu,
                            'django': django_val,
                            'php': php_val
                        })
    
    # Relatório do grupo
    if not divergencias_grupo:
        print(f"✅ GRUPO {grupo_nome}: 100% DE BATIMENTO!")
        return True
    else:
        print(f"❌ GRUPO {grupo_nome}: {len(divergencias_grupo)} campos com divergências")
        
        for campo, divergencias in sorted(divergencias_grupo.items()):
            percentual = (len(divergencias) / total_registros) * 100
            print(f"  - {campo}: {len(divergencias)} divergências ({percentual:.1f}%)")
            
            # Mostrar alguns exemplos
            for i, div in enumerate(divergencias[:3]):
                print(f"    * NSU {div['nsu']}: Django={div['django']}, PHP={div['php']}")
        
        return False

def main():
    """Função principal para comparar dados por grupos de dependência"""
    print("="*80)
    print("RELATÓRIO DE COMPARAÇÃO POR GRUPOS DE DEPENDÊNCIA")
    print("="*80)
    
    # Conectar aos bancos
    django_conn = conectar_django()
    php_conn = conectar_php()
    
    try:
        # Buscar dados do Django
        django_data = buscar_dados_django(django_conn)
        
        # Buscar dados do PHP
        php_data = buscar_dados_php(php_conn)
        
        # Definir grupos
        grupos = definir_grupos_dependencia()
        
        # Testar cada grupo sequencialmente
        for grupo_nome, grupo_info in grupos.items():
            sucesso = testar_grupo(django_data, php_data, grupo_nome, grupo_info)
            
            if not sucesso:
                print(f"\n❌ PARANDO NO GRUPO {grupo_nome} - Corrija as divergências antes de continuar")
                break
        else:
            print(f"\n🎉 TODOS OS GRUPOS TESTADOS COM SUCESSO!")
        
    finally:
        django_conn.close()
        php_conn.close()

def testar_django_producao(valor, id_loja, forma_pagamento, parcelas, wall):
    """Testa a calculadora Django produção - COPIADO EXATAMENTE DO SCRIPT LOCAL"""
    try:
        # Testar conexão primeiro
        from django.db import connection
        connection.ensure_connection()
        
        calculadora = CalculadoraDesconto()
        resultado = calculadora.calcular_desconto(
            valor_original=valor,
            data="2025-08-21",
            forma=forma_pagamento,
            parcelas=parcelas,
            id_loja=id_loja,  # Usar id_loja diretamente
            wall=wall
        )
        id_plano_encontrado = getattr(calculadora, 'id_plano_encontrado', None)
        return resultado, id_plano_encontrado, None
    except Exception as e:
        return None, f"Erro no Django: {e}", None

def testar_endpoint_php(valor, id_loja, forma_pagamento, parcelas, wall):
    """Testa o endpoint PHP PRODUÇÃO - USANDO NOVO ENDPOINT COM ID_LOJA"""
    url = "https://posp2.wallclub.com.br/calcula_desconto_parcela_para_teste.php"
    
    # Mapear formas de pagamento Django para formato do novo endpoint
    forma_mapeada = {
        'PIX': 'CASH',
        'DEBITO': 'DEBIT', 
        'A VISTA': 'CREDIT_ONE_INSTALLMENT',
        'PARCELADO SEM JUROS': 'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST'
    }.get(forma_pagamento, forma_pagamento)
    
    data = {
        'valoro': valor,
        'data': '2025-08-21',
        'forma': forma_mapeada,
        'parcelas': parcelas,
        'wall': wall,
        'id_loja': str(id_loja)
    }
    
    try:
        response = requests.post(url, data=data, timeout=10)
        
        if response.status_code == 200:
            try:
                import json
                json_response = json.loads(response.text.strip())
                
                # Novo formato: {"erro":0,"mensagem":"...","parcelas":{"4":{"valor_total":"110.00",...}}}
                if json_response.get('erro') == 0:
                    parcelas_data = json_response.get('parcelas', {})
                    
                    # Pegar o primeiro resultado das parcelas
                    if parcelas_data:
                        primeira_parcela = next(iter(parcelas_data.values()))
                        valor_total = primeira_parcela.get('valor_total')
                        if valor_total:
                            return float(valor_total)
                    
                    raise Exception("Formato de resposta inesperado")
                else:
                    raise Exception(json_response.get('mensagem', 'Erro desconhecido'))
            except json.JSONDecodeError:
                # Fallback para resposta em texto puro
                return float(response.text.strip())
        else:
            raise Exception(f"{response.status_code} {response.reason}")

    except Exception as e:
        print(f"❌ Erro no PHP: {e}")
        return None

def comparar_resultados(django_result, php_result):
    """Compara os resultados com tolerância de 1 centavo"""
    if django_result is None or php_result is None:
        return False, False
    
    # Converter para Decimal para precisão
    django_decimal = Decimal(str(django_result)).quantize(Decimal('0.01'))
    php_decimal = Decimal(str(php_result)).quantize(Decimal('0.01'))
    
    diferenca = abs(django_decimal - php_decimal)
    percentual = (diferenca / django_decimal * 100) if django_decimal != 0 else 0
    
    # Verificar se PHP retornou zero
    php_zero = (php_decimal == Decimal('0.00'))
    
    print(f"🐍 Django: R$ {django_decimal}")
    print(f"🐘 PHP:    R$ {php_decimal}")
    print(f"📊 Diff:   R$ {diferenca} ({percentual:.2f}%)")
    
    if diferenca <= Decimal('0.01'):  # Tolerância de 1 centavo
        print("✅ MATCH - Resultados idênticos!")
        return True, php_zero
    else:
        if php_zero:
            print("❌ DIVERGÊNCIA - PHP retornou ZERO!")
        else:
            print("❌ DIVERGÊNCIA - Resultados diferentes!")
        return False, php_zero

def main():
    print("🔥 COMPARAÇÃO DJANGO PRODUÇÃO vs PHP PRODUÇÃO")
    print("Testando lógica de cálculo em ambiente de produção")
    print()
    
    # TESTE FOCADO - APENAS LOJA 26 (id_desc=2)
    combinacoes_teste = [
        # LOJA 1 (id_desc=6)
        (1, 6, 1), (1, 6, 2), (1, 6, 3), (1, 6, 4), (1, 6, 5), (1, 6, 6), (1, 6, 7), (1, 6, 8), (1, 6, 9), (1, 6, 10), (1, 6, 11), (1, 6, 12), (1, 6, 13), (1, 6, 14),
        
        # LOJA 6 (id_desc=611)
        (6, 611, 1), (6, 611, 2), (6, 611, 3), (6, 611, 4), (6, 611, 5), (6, 611, 6), (6, 611, 7), (6, 611, 8), (6, 611, 9), (6, 611, 10), (6, 611, 11), (6, 611, 12), (6, 611, 13), (6, 611, 14),
        
        # LOJA 7 (id_desc=1)
        (7, 1, 1), (7, 1, 2), (7, 1, 3), (7, 1, 4), (7, 1, 5), (7, 1, 6), (7, 1, 7), (7, 1, 8), (7, 1, 9), (7, 1, 10), (7, 1, 11), (7, 1, 12), (7, 1, 13), (7, 1, 14),
      
        # LOJA 14 (id_desc=511)
        (14, 511, 1), (14, 511, 2), (14, 511, 3), (14, 511, 4), (14, 511, 5), (14, 511, 6), (14, 511, 7), (14, 511, 8), (14, 511, 9), (14, 511, 10), (14, 511, 11), (14, 511, 12), (14, 511, 13), (14, 511, 14),
        
        # LOJA 15 (id_desc=5)
        (15, 5, 1), (15, 5, 2), (15, 5, 3), (15, 5, 4), (15, 5, 5), (15, 5, 6), (15, 5, 7), (15, 5, 8), (15, 5, 9), (15, 5, 10), (15, 5, 11), (15, 5, 12), (15, 5, 13), (15, 5, 14),
        
        # LOJA 16 (id_desc=711)
        (16, 711, 1), (16, 711, 2), (16, 711, 3), (16, 711, 4), (16, 711, 5), (16, 711, 6), (16, 711, 7), (16, 711, 8), (16, 711, 9), (16, 711, 10), (16, 711, 11), (16, 711, 12), (16, 711, 13), (16, 711, 14),
        
        # LOJA 20 (id_desc=711)
        (20, 711, 1), (20, 711, 2), (20, 711, 3), (20, 711, 4), (20, 711, 5), (20, 711, 6), (20, 711, 7), (20, 711, 8), (20, 711, 9), (20, 711, 10), (20, 711, 11), (20, 711, 12), (20, 711, 13), (20, 711, 14),
        
        # LOJA 21 (id_desc=711)
        (21, 711, 1), (21, 711, 2), (21, 711, 3), (21, 711, 4), (21, 711, 5), (21, 711, 6), (21, 711, 7), (21, 711, 8), (21, 711, 9), (21, 711, 10), (21, 711, 11), (21, 711, 12), (21, 711, 13), (21, 711, 14),
        
        # LOJA 22 (id_desc=711)
        (22, 711, 1), (22, 711, 2), (22, 711, 3), (22, 711, 4), (22, 711, 5), (22, 711, 6), (22, 711, 7), (22, 711, 8), (22, 711, 9), (22, 711, 10), (22, 711, 11), (22, 711, 12), (22, 711, 13), (22, 711, 14),
        
        # LOJA 23 (id_desc=914)
        (23, 914, 1), (23, 914, 2), (23, 914, 3), (23, 914, 4), (23, 914, 5), (23, 914, 6), (23, 914, 7), (23, 914, 8), (23, 914, 9), (23, 914, 10), (23, 914, 11), (23, 914, 12), (23, 914, 13), (23, 914, 14),
        
        # LOJA 24 (id_desc=914)
        (24, 914, 1), (24, 914, 2), (24, 914, 3), (24, 914, 4), (24, 914, 5), (24, 914, 6), (24, 914, 7), (24, 914, 8), (24, 914, 9), (24, 914, 10), (24, 914, 11), (24, 914, 12), (24, 914, 13), (24, 914, 14),
        
        # LOJA 26 (id_desc=2) - TESTE FOCADO
        (26, 2, 1), (26, 2, 2), (26, 2, 3), (26, 2, 4), (26, 2, 5), (26, 2, 6), (26, 2, 7), (26, 2, 8), (26, 2, 9), (26, 2, 10), (26, 2, 11), (26, 2, 12), (26, 2, 13), (26, 2, 14)
    ]
    
    # Mapear planos para formas de pagamento corretas
    plano_para_forma = {
        1: ("PIX", 1),                    # PIX
        2: ("A VISTA", 1),               # À VISTA
        3: ("DEBITO", 1),                # DÉBITO
        4: ("PARCELADO SEM JUROS", 2),   # PARCELADO 2x
        5: ("PARCELADO SEM JUROS", 3),   # PARCELADO 3x
        6: ("PARCELADO SEM JUROS", 4),   # PARCELADO 4x
        7: ("PARCELADO SEM JUROS", 5),   # PARCELADO 5x
        8: ("PARCELADO SEM JUROS", 6),   # PARCELADO 6x
        9: ("PARCELADO SEM JUROS", 7),   # PARCELADO 7x
        10: ("PARCELADO SEM JUROS", 8),  # PARCELADO 8x
        11: ("PARCELADO SEM JUROS", 9),  # PARCELADO 9x
        12: ("PARCELADO SEM JUROS", 10), # PARCELADO 10x
        13: ("PARCELADO SEM JUROS", 11), # PARCELADO 11x
        14: ("PARCELADO SEM JUROS", 12)  # PARCELADO 12x
    }
    
    # Valor de teste
    valor_teste = 110.0
    wall = 's'  # Wall S
    
    # Contadores
    total_testes = 0
    testes_ok = 0
    divergencias_php_zero = 0
    
    # Executar todos os testes
    for loja_id, id_desc, id_plano in combinacoes_teste:
        forma_pagamento, parcelas = plano_para_forma[id_plano]
        
        print("=" * 60)
        print(f"TESTE: {forma_pagamento} {parcelas}x Wall S - Loja {loja_id} (Plano {id_plano})")
        print(f"Params: valor={valor_teste}, id_loja={loja_id}, forma={forma_pagamento}, parcelas={parcelas}, wall={wall}")
        print("=" * 60)
        
        # Testar Django PRODUÇÃO
        django_result, id_plano_encontrado, id_desc_encontrado = testar_django_producao(
            valor=valor_teste,
            id_loja=loja_id,
            forma_pagamento=forma_pagamento,
            parcelas=parcelas,
            wall=wall
        )
        
        # Testar PHP PRODUÇÃO
        php_result = testar_endpoint_php(
            valor=valor_teste,
            id_loja=loja_id,
            forma_pagamento=forma_pagamento,
            parcelas=parcelas,
            wall=wall
        )
        
        print(f"🆔 ID_PLANO: {id_plano} (encontrado: {id_plano_encontrado})")
        print(f"🏷️  ID_DESC: {id_desc} (encontrado: {id_desc_encontrado})")
        
        if django_result is not None and php_result is not None:
            total_testes += 1
            match, php_zero = comparar_resultados(django_result, php_result)
            if match:
                testes_ok += 1
            elif php_zero:
                divergencias_php_zero += 1
        else:
            print("❌ ERRO - Um dos cálculos falhou")
        
        print()
    
    # Relatório final
    print("=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    print(f"✅ Testes OK: {testes_ok}")
    print(f"❌ Divergências: {total_testes - testes_ok}")
    print(f"🚫 Divergências por PHP=0: {divergencias_php_zero}")
    print(f"🔄 Outras divergências: {total_testes - testes_ok - divergencias_php_zero}")
    print(f"📊 Total: {total_testes}")
    
    if total_testes > 0:
        taxa_sucesso = (testes_ok / total_testes) * 100
        print(f"🎯 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        if taxa_sucesso == 100:
            print("🎉 PERFEITO! Todos os testes passaram!")
        elif taxa_sucesso >= 90:
            print("✅ MUITO BOM! Maioria dos testes passou.")
        elif taxa_sucesso >= 70:
            print("⚠️  ATENÇÃO! Muitas divergências encontradas.")
        else:
            print("🚨 CRÍTICO! Muitos testes falharam.")

# Executar automaticamente quando chamado via shell
main()
