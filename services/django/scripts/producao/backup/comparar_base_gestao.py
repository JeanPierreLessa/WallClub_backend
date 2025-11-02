#!/usr/bin/env python
"""
Script para comparar os valores entre as tabelas wallclub.baseTransacoesGestao e wclub.baseTransacoesGestao.
Usa o campo var9 (NSU) como chave de comparação.
Ignora os campos idfilaextrato e banco que são irrelevantes para o cálculo.
"""

import os
import sys
import django
import logging
import csv
from decimal import Decimal
from datetime import datetime

# Configurar o ambiente Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.development')
django.setup()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    datefmt='%m/%d/%Y %I:%M:%S %p'
)
logger = logging.getLogger(__name__)

# Importar conexão com o banco
from django.db import connections


def obter_colunas_base_gestao():
    """
    Obtém a lista de colunas da tabela baseTransacoesGestao.
    Retorna uma lista com os nomes das colunas.
    """
    with connections['default'].cursor() as cursor:
        cursor.execute("DESCRIBE wallclub.baseTransacoesGestao")
        colunas = [row[0] for row in cursor.fetchall()]
    
    return colunas


def comparar_base_gestao(limite=50):
    """
    Compara os valores entre as tabelas wallclub.baseTransacoesGestao e wclub.baseTransacoesGestao.
    
    Args:
        limite (int): Limite de registros a serem comparados
    
    Returns:
        dict: Estatísticas de comparação
    """
    logger.info(f"Iniciando comparação entre as tabelas de base de gestão (limite: {limite})")
    
    # Obter colunas da tabela
    colunas = obter_colunas_base_gestao()
    
    # Comparar apenas as variáveis (var1-var20) e usar NSU (var9) como chave
    colunas_comparar = [col for col in colunas if col.startswith('var') and col != 'var9']
    colunas_comparar.append('var9')  # Adicionar NSU para usar como chave
    
    # Consultar dados da tabela wallclub.baseTransacoesGestao (Django)
    with connections['default'].cursor() as cursor:
        cursor.execute(f"""
            SELECT {', '.join(colunas_comparar)}
            FROM wallclub.baseTransacoesGestao
            LIMIT {limite}
        """)
        dados_teste = cursor.fetchall()
        
        # Verificar se temos dados para comparar
        if not dados_teste:
            logger.error("Nenhum registro encontrado na tabela wallclub.baseTransacoesGestao")
            return {"erro": "Nenhum registro encontrado na tabela wallclub.baseTransacoesGestao"}
        
        # Criar dicionário para os dados de teste, indexado por NSU (var9)
        registros_teste = {}
        for registro in dados_teste:
            # Criar dicionário com os valores do registro
            dados_registro = {}
            for i, coluna in enumerate(colunas_comparar):
                dados_registro[coluna] = registro[i]
            
            # Usar var9 (NSU) como chave
            nsu = dados_registro.get('var9')
            if nsu:
                registros_teste[nsu] = dados_registro
        
        # Obter lista de NSUs para consultar na tabela original
        nsus = list(registros_teste.keys())
        if not nsus:
            logger.error("Nenhum NSU válido encontrado na tabela wallclub.baseTransacoesGestao")
            return {"erro": "Nenhum NSU válido encontrado na tabela wallclub.baseTransacoesGestao"}
            
        nsus_str = ', '.join([f"'{nsu}'" for nsu in nsus])
        
        # Consultar dados da tabela original (PHP)
        try:
            with connections['default'].cursor() as cursor_php:
                cursor_php.execute(f"""
                    SELECT {', '.join(colunas_comparar)}
                    FROM wclub.baseTransacoesGestao
                    WHERE var9 IN ({nsus_str})
                """)
                dados_php = cursor_php.fetchall()
                
                if not dados_php:
                    logger.error(f"Nenhum registro encontrado na tabela wclub.baseTransacoesGestao para os NSUs informados")
                    return {"erro": f"Nenhum registro encontrado na tabela wclub.baseTransacoesGestao para os NSUs informados"}
                    
                # Criar dicionário para os dados PHP, indexado por NSU (var9)
                registros_php = {}
                for registro in dados_php:
                    # Criar dicionário com os valores do registro
                    dados_registro = {}
                    for i, coluna in enumerate(colunas_comparar):
                        dados_registro[coluna] = registro[i]
                    
                    # Usar var9 (NSU) como chave
                    nsu = dados_registro.get('var9')
                    if nsu:
                        registros_php[nsu] = dados_registro
                        
        except Exception as e:
            logger.error(f"Erro ao consultar tabela wclub.baseTransacoesGestao: {str(e)}")
            return {"erro": f"Erro ao consultar tabela wclub.baseTransacoesGestao: {str(e)}"}
    
    # Verificar registros que não foram encontrados
    nsus_nao_encontrados = set(registros_teste.keys()) - set(registros_php.keys())
    if nsus_nao_encontrados:
        logger.warning(f"NSUs não encontrados na tabela PHP: {nsus_nao_encontrados}")
    
    # Inicializar estatísticas
    estatisticas = {
        "total_registros": len(set(registros_teste.keys()) & set(registros_php.keys())),  # Interseção
        "campos_divergentes": {},
        "registros_com_divergencia": 0,
        "percentual_divergencia": 0,
        "detalhes_divergencias": []
    }
    
    # Comparar valores entre as tabelas
    registros_com_divergencia = set()
    
    # Iterar sobre os NSUs que existem em ambas as tabelas
    nsus_comuns = set(registros_teste.keys()) & set(registros_php.keys())
    
    for nsu in nsus_comuns:
        registro_django = registros_teste[nsu]
        registro_php = registros_php[nsu]
        
        # Comparar cada campo
        for coluna in colunas_comparar:
            if coluna == 'var9':  # Pular a coluna de NSU que é a chave
                continue
                
            val_django = registro_django.get(coluna)
            val_php = registro_php.get(coluna)
            
            # Inicializar o dicionário de divergências para esta coluna se ainda não existir
            if coluna not in estatisticas["campos_divergentes"]:
                estatisticas["campos_divergentes"][coluna] = {
                    "total_divergencias": 0,
                    "percentual": 0,
                    "exemplos": []
                }
            
            # Converter para o mesmo tipo para comparação
            if isinstance(val_django, (int, float, Decimal)) and isinstance(val_php, (int, float, Decimal)):
                # Comparar valores numéricos com tolerância para diferenças de arredondamento
                try:
                    val_django_float = float(val_django)
                    val_php_float = float(val_php)
                    if abs(val_django_float - val_php_float) > 0.01:  # Tolerância de 0.01
                        divergencia = {
                            "nsu": nsu,
                            "valor_django": val_django_float,
                            "valor_php": val_php_float,
                            "diferenca": val_django_float - val_php_float
                        }
                        
                        estatisticas["campos_divergentes"][coluna]["total_divergencias"] += 1
                        if len(estatisticas["campos_divergentes"][coluna]["exemplos"]) < 5:  # Limitar a 5 exemplos
                            estatisticas["campos_divergentes"][coluna]["exemplos"].append(divergencia)
                        
                        registros_com_divergencia.add(nsu)
                except (ValueError, TypeError):
                    # Se não conseguir converter para float, comparar como strings
                    if str(val_django) != str(val_php):
                        divergencia = {
                            "nsu": nsu,
                            "valor_django": str(val_django),
                            "valor_php": str(val_php)
                        }
                        
                        estatisticas["campos_divergentes"][coluna]["total_divergencias"] += 1
                        if len(estatisticas["campos_divergentes"][coluna]["exemplos"]) < 5:  # Limitar a 5 exemplos
                            estatisticas["campos_divergentes"][coluna]["exemplos"].append(divergencia)
                        
                        registros_com_divergencia.add(nsu)
            elif str(val_django) != str(val_php):
                # Comparar como strings para outros tipos
                divergencia = {
                    "nsu": nsu,
                    "valor_django": str(val_django),
                    "valor_php": str(val_php)
                }
                
                estatisticas["campos_divergentes"][coluna]["total_divergencias"] += 1
                if len(estatisticas["campos_divergentes"][coluna]["exemplos"]) < 5:  # Limitar a 5 exemplos
                    estatisticas["campos_divergentes"][coluna]["exemplos"].append(divergencia)
                
                registros_com_divergencia.add(nsu)
    
    # Remover campos sem divergências
    campos_sem_divergencias = []
    for campo, info in estatisticas["campos_divergentes"].items():
        if info["total_divergencias"] == 0:
            campos_sem_divergencias.append(campo)
    
    for campo in campos_sem_divergencias:
        del estatisticas["campos_divergentes"][campo]
    
    # Calcular percentuais para cada campo
    for campo, info in estatisticas["campos_divergentes"].items():
        info["percentual"] = (info["total_divergencias"] / estatisticas["total_registros"]) * 100 if estatisticas["total_registros"] > 0 else 0
    
    # Calcular estatísticas finais
    estatisticas["registros_com_divergencia"] = len(registros_com_divergencia)
    estatisticas["percentual_divergencia"] = (len(registros_com_divergencia) / estatisticas["total_registros"]) * 100 if estatisticas["total_registros"] > 0 else 0
    
    # Gerar relatório detalhado
    gerar_relatorio_detalhado(estatisticas, registros_teste, registros_php, colunas_comparar)
    
    return estatisticas


def gerar_relatorio_detalhado(estatisticas, registros_teste, registros_php, colunas):
    """
    Gera um relatório detalhado das divergências encontradas.
    
    Args:
        estatisticas (dict): Estatísticas de comparação
        registros_teste (dict): Dicionário com os registros da tabela de teste
        registros_php (dict): Dicionário com os registros da tabela PHP
        colunas (list): Lista de colunas a serem comparadas
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome_arquivo = f"relatorio_comparacao_{timestamp}.csv"
    
    # Obter lista de campos com divergências
    campos_divergentes = list(estatisticas["campos_divergentes"].keys())
    
    if not campos_divergentes:
        logger.info("Nenhuma divergência encontrada para gerar relatório detalhado")
        return
    
    # Criar cabeçalho do CSV
    cabecalho = ['nsu']
    for campo in campos_divergentes:
        cabecalho.extend([f"{campo}_django", f"{campo}_php", f"diff_{campo}"])
    
    # Obter NSUs comuns
    nsus_comuns = set(registros_teste.keys()) & set(registros_php.keys())
    
    try:
        with open(nome_arquivo, 'w', newline='') as arquivo_csv:
            writer = csv.writer(arquivo_csv)
            writer.writerow(cabecalho)
            
            for nsu in nsus_comuns:
                registro_django = registros_teste[nsu]
                registro_php = registros_php[nsu]
                
                # Inicializar linha com o NSU
                linha = [nsu]
                
                # Adicionar valores para cada campo com divergência
                for campo in campos_divergentes:
                    val_django = registro_django.get(campo)
                    val_php = registro_php.get(campo)
                    
                    # Adicionar valores
                    linha.append(str(val_django))
                    linha.append(str(val_php))
                    
                    # Calcular diferença para valores numéricos
                    if isinstance(val_django, (int, float, Decimal)) and isinstance(val_php, (int, float, Decimal)):
                        try:
                            diferenca = float(val_django) - float(val_php)
                            linha.append(str(diferenca))
                        except (ValueError, TypeError):
                            linha.append('N/A')
                    else:
                        linha.append('N/A')
                
                writer.writerow(linha)
        
        logger.info(f"Relatório detalhado salvo em: {nome_arquivo}")
    except Exception as e:
        logger.error(f"Erro ao salvar relatório: {str(e)}")


def exibir_estatisticas(estatisticas):
    """
    Exibe as estatísticas de comparação de forma formatada.
    
    Args:
        estatisticas (dict): Estatísticas de comparação
    """
    print("\n" + "="*80)
    print(f"RELATÓRIO DE COMPARAÇÃO ENTRE TABELAS DE BASE DE GESTÃO")
    print("="*80)
    
    if "erro" in estatisticas:
        print(f"\nERRO: {estatisticas['erro']}")
        return
    
    print(f"\nTotal de registros comparados: {estatisticas['total_registros']}")
    print(f"Registros com divergências: {estatisticas['registros_com_divergencia']} ({estatisticas['percentual_divergencia']:.2f}%)")
    
    if estatisticas["campos_divergentes"]:
        print("\nCampos com divergências:")
        print("-"*80)
        
        for campo, info in sorted(
            estatisticas["campos_divergentes"].items(), 
            key=lambda x: x[1]["total_divergencias"], 
            reverse=True
        ):
            print(f"Campo: {campo}")
            print(f"  - Total de divergências: {info['total_divergencias']} ({info['percentual']:.2f}%)")
            
            if info["exemplos"]:
                print("  - Exemplos de divergências:")
                for exemplo in info["exemplos"]:
                    nsu = exemplo["nsu"]
                    val_django = exemplo.get("valor_django", "N/A")
                    val_php = exemplo.get("valor_php", "N/A")
                    diferenca = exemplo.get("diferenca", "N/A")
                    
                    if diferenca != "N/A":
                        print(f"    * NSU {nsu}: Django={val_django}, PHP={val_php}, Diff={diferenca}")
                    else:
                        print(f"    * NSU {nsu}: Django={val_django}, PHP={val_php}")
            print("-"*80)
    else:
        print("\nNenhuma divergência encontrada! Os valores são idênticos.")
    
    print("\n" + "="*80)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Comparar valores entre tabelas de base de gestão')
    parser.add_argument('--limite', type=int, default=50, help='Limite de registros a serem comparados')
    args = parser.parse_args()
    
    try:
        estatisticas = comparar_base_gestao(args.limite)
        exibir_estatisticas(estatisticas)
    except Exception as e:
        logger.error(f"Erro na execução do script: {str(e)}")
        import traceback
        traceback.print_exc()
