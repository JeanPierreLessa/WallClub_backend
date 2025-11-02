#!/usr/bin/env python3
"""
Script para comparar cálculos Django LOCAL vs PHP PRODUÇÃO
Usado para validar se a lógica de cálculo está correta antes da migração completa

EXECUÇÃO: docker exec wallclub-local python manage.py shell -c "exec(open('scripts/producao/comparar_django_local_vs_php_prod.py').read())"
"""

import requests
from decimal import Decimal
from parametros_wallclub.services import CalculadoraDesconto

def testar_endpoint_php(valor, id_loja, forma_pagamento, parcelas, wall):
    """Testa o endpoint PHP de produção"""
    url = "https://posp2.wallclub.com.br/calcula_desconto_para_teste.php"
    
    data = {
        'valoro': valor,
        'data': '2025-08-21',
        'forma': forma_pagamento,
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
                if json_response.get('sucesso'):
                    return float(json_response.get('resultado'))
                else:
                    raise Exception(json_response.get('erro', 'Erro desconhecido'))
            except json.JSONDecodeError:
                # Fallback para resposta em texto puro
                return float(response.text.strip())
        else:
            raise Exception(f"{response.status_code} {response.reason}")

    except Exception as e:
        print(f"❌ Erro no PHP: {e}")
        return None

def testar_django_local(valor, id_loja, forma_pagamento, parcelas, wall):
    """Testa a calculadora Django local"""
    try:
        # Testar conexão primeiro
        from django.db import connection
        connection.ensure_connection()
        
        calculadora = CalculadoraDesconto()
        resultado = calculadora.calcular_desconto(
            valor_original=valor,
            data="2025-08-15",
            forma=forma_pagamento,
            parcelas=parcelas,
            terminal=str(id_loja),
            wall=wall
        )
        return resultado, getattr(calculadora, 'id_plano_encontrado', None)
    except Exception as e:
        return None, f"Erro no Django: {e}"

def comparar_resultados(django_result, php_result):
    """Compara os resultados e retorna se são equivalentes"""
    if django_result is None or php_result is None:
        return False
    
    diferenca = abs(django_result - php_result)
    percentual = (diferenca / php_result * 100) if php_result != 0 else 0
    
    print(f"🐍 Django: R$ {django_result:.2f}")
    print(f"🐘 PHP:    R$ {php_result:.2f}")
    print(f"📊 Diff:   R$ {diferenca:.2f} ({percentual:.2f}%)")
    
    if diferenca < 0.01:  # Tolerância de 1 centavo
        print("✅ MATCH - Resultados idênticos!")
        return True
    else:
        print("❌ DIVERGÊNCIA - Resultados diferentes!")
        return False

def main():
    print("🔥 COMPARAÇÃO DJANGO LOCAL vs PHP PRODUÇÃO")
    print("Testando lógica de cálculo com dados locais")
    print()
    
    # BASE DE TESTE ATUALIZADA - WALL S, PLANOS 1-14, VIGÊNCIA ATIVA
    combinacoes_teste = [
        # LOJA 1
        (1, 6, 1), (1, 6, 2), (1, 6, 3), (1, 6, 4), (1, 6, 5), (1, 6, 6), (1, 6, 7), (1, 6, 8), (1, 6, 9), (1, 6, 10), (1, 6, 11), (1, 6, 12), (1, 6, 13), (1, 6, 14),
        
        # LOJA 6
        (6, 611, 1), (6, 611, 2), (6, 611, 3), (6, 611, 4), (6, 611, 5), (6, 611, 6), (6, 611, 7), (6, 611, 8), (6, 611, 9), (6, 611, 10), (6, 611, 11), (6, 611, 12), (6, 611, 13), (6, 611, 14),
        
        # LOJA 7
        (7, 1, 1), (7, 1, 2), (7, 1, 3), (7, 1, 4), (7, 1, 5), (7, 1, 6), (7, 1, 7), (7, 1, 8), (7, 1, 9), (7, 1, 10), (7, 1, 11), (7, 1, 12), (7, 1, 13), (7, 1, 14),
        
        # LOJA 8
        (8, 2, 1), (8, 2, 2), (8, 2, 3), (8, 2, 4), (8, 2, 5), (8, 2, 6), (8, 2, 7), (8, 2, 8), (8, 2, 9), (8, 2, 10), (8, 2, 11), (8, 2, 12), (8, 2, 13), (8, 2, 14),
        
        # LOJA 9
        (9, 3, 1), (9, 3, 2), (9, 3, 3), (9, 3, 4), (9, 3, 5), (9, 3, 6), (9, 3, 7), (9, 3, 8), (9, 3, 9), (9, 3, 10), (9, 3, 11), (9, 3, 12), (9, 3, 13), (9, 3, 14),
        
        # LOJA 12
        (12, 6, 1), (12, 6, 2), (12, 6, 3), (12, 6, 4), (12, 6, 5), (12, 6, 6), (12, 6, 7), (12, 6, 8), (12, 6, 9), (12, 6, 10), (12, 6, 11), (12, 6, 12), (12, 6, 13), (12, 6, 14),
        
        # LOJA 13
        (13, 2, 1), (13, 2, 2), (13, 2, 3), (13, 2, 4), (13, 2, 5), (13, 2, 6), (13, 2, 7), (13, 2, 8), (13, 2, 9), (13, 2, 10), (13, 2, 11), (13, 2, 12), (13, 2, 13), (13, 2, 14),
        
        # LOJA 14
        (14, 511, 1), (14, 511, 2), (14, 511, 3), (14, 511, 4), (14, 511, 5), (14, 511, 6), (14, 511, 7), (14, 511, 8), (14, 511, 9), (14, 511, 10), (14, 511, 11), (14, 511, 12), (14, 511, 13), (14, 511, 14),
        
        # LOJA 15
        (15, 5, 1), (15, 5, 2), (15, 5, 3), (15, 5, 4), (15, 5, 5), (15, 5, 6), (15, 5, 7), (15, 5, 8), (15, 5, 9), (15, 5, 10), (15, 5, 11), (15, 5, 12), (15, 5, 13), (15, 5, 14),
        
        # LOJA 16
        (16, 711, 1), (16, 711, 2), (16, 711, 3), (16, 711, 4), (16, 711, 5), (16, 711, 6), (16, 711, 7), (16, 711, 8), (16, 711, 9), (16, 711, 10), (16, 711, 11), (16, 711, 12), (16, 711, 13), (16, 711, 14),
        
        # LOJA 20
        (20, 711, 1), (20, 711, 2), (20, 711, 3), (20, 711, 4), (20, 711, 5), (20, 711, 6), (20, 711, 7), (20, 711, 8), (20, 711, 9), (20, 711, 10), (20, 711, 11), (20, 711, 12), (20, 711, 13), (20, 711, 14),
        
        # LOJA 21
        (21, 711, 1), (21, 711, 2), (21, 711, 3), (21, 711, 4), (21, 711, 5), (21, 711, 6), (21, 711, 7), (21, 711, 8), (21, 711, 9), (21, 711, 10), (21, 711, 11), (21, 711, 12), (21, 711, 13), (21, 711, 14),
        
        # LOJA 22
        (22, 711, 1), (22, 711, 2), (22, 711, 3), (22, 711, 4), (22, 711, 5), (22, 711, 6), (22, 711, 7), (22, 711, 8), (22, 711, 9), (22, 711, 10), (22, 711, 11), (22, 711, 12), (22, 711, 13), (22, 711, 14),
        
        # LOJA 23
        (23, 914, 1), (23, 914, 2), (23, 914, 3), (23, 914, 4), (23, 914, 5), (23, 914, 6), (23, 914, 7), (23, 914, 8), (23, 914, 9), (23, 914, 10), (23, 914, 11), (23, 914, 12), (23, 914, 13), (23, 914, 14),
        
        # LOJA 24
        (24, 914, 1), (24, 914, 2), (24, 914, 3), (24, 914, 4), (24, 914, 5), (24, 914, 6), (24, 914, 7), (24, 914, 8), (24, 914, 9), (24, 914, 10), (24, 914, 11), (24, 914, 12), (24, 914, 13), (24, 914, 14),
        
        # LOJA 25
        (25, 914, 1), (25, 914, 2), (25, 914, 3), (25, 914, 4), (25, 914, 5), (25, 914, 6), (25, 914, 7), (25, 914, 8), (25, 914, 9), (25, 914, 10), (25, 914, 11), (25, 914, 12), (25, 914, 13), (25, 914, 14),
        
        # LOJA 26
        (26, 611, 1), (26, 611, 2), (26, 611, 3), (26, 611, 4), (26, 611, 5), (26, 611, 6), (26, 611, 7), (26, 611, 8), (26, 611, 9), (26, 611, 10), (26, 611, 11), (26, 611, 12), (26, 611, 13), (26, 611, 14)
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
        14: ("PARCELADO SEM JUROS", 12), # PARCELADO 12x
    }
    
    valor_teste = 110.0
    wall = 's'
    
    total_testes = 0
    testes_ok = 0
    
    for loja_id, id_desc, id_plano in combinacoes_teste:
        if id_plano not in plano_para_forma:
            continue
            
        forma_pagamento, parcelas = plano_para_forma[id_plano]
        
        print("=" * 60)
        print(f"TESTE: {forma_pagamento} {parcelas}x Wall {wall.upper()} - Loja {loja_id} (Plano {id_plano})")
        print(f"Params: valor={valor_teste}, id_loja={loja_id}, forma={forma_pagamento}, parcelas={parcelas}, wall={wall}")
        print("=" * 60)
        
        # Testar Django LOCAL
        django_result, id_plano_encontrado = testar_django_local(
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
        
        print(f"🆔 ID_PLANO: {id_plano}")
        
        if django_result is not None and php_result is not None:
            total_testes += 1
            if comparar_resultados(django_result, php_result):
                testes_ok += 1
        else:
            print("❌ ERRO - Um dos cálculos falhou")
        
        print()
    
    # Relatório final
    print("=" * 60)
    print("📊 RELATÓRIO FINAL")
    print("=" * 60)
    print(f"✅ Testes OK: {testes_ok}")
    print(f"❌ Divergências: {total_testes - testes_ok}")
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
