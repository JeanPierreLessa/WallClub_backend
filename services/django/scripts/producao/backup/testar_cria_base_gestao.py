#!/usr/bin/env python
import os
import sys
import django
from decimal import Decimal

# Configurar ambiente Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.development')
django.setup()

from django.db import connection
from cargas_pinbank.management.commands.cria_base_gestao_teste import Command

def testar_loja_16_credito():
    """
    Testa o cálculo para Loja 16 CRÉDITO
    """
    print("\n=== TESTE LOJA 16 CRÉDITO ===")
    
    # Limpar tabelas de teste
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM teste_baseTransacoesGestao WHERE loja_id = 16")
        cursor.execute("DELETE FROM teste_baseTransacoesGestaoErroCarga WHERE loja_id = 16")
        
        # Inserir registro de teste para Loja 16 CRÉDITO
        cursor.execute("""
        INSERT INTO teste_pinbankExtratoPOS (
            id, NsuOperacao, NumeroParcela, DataTransacao, ValorBruto, 
            ValorLiquido, TipoTransacao, Bandeira, loja_id, CPF, lido
        ) VALUES (
            999901, '123456', 1, '2023-01-01', 100.00, 
            95.00, 'CREDITO', 'VISA', 16, '12345678900', 0
        )
        """)
    
    # Executar comando
    cmd = Command()
    cmd.handle()
    
    # Verificar resultados
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT valores_72, valores_74, valores_76, valores_26
        FROM teste_baseTransacoesGestao
        WHERE loja_id = 16 AND nsu_operacao = '123456'
        """)
        resultado = cursor.fetchone()
        
        if resultado:
            valores_72, valores_74, valores_76, valores_26 = resultado
            print(f"valores[72] = {valores_72} (Esperado: 1.0 para param_10=-0.01)")
            print(f"valores[74] = {valores_74}")
            print(f"valores[76] = {valores_76} (Soma de valores[72] + valores[74])")
            print(f"valores[26] = {valores_26} (Valor final com ajustes)")
        else:
            print("Nenhum resultado encontrado para Loja 16 CRÉDITO")

def testar_loja_1_parcelado():
    """
    Testa o cálculo para Loja 1 PARCELADO
    """
    print("\n=== TESTE LOJA 1 PARCELADO ===")
    
    # Limpar tabelas de teste
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM teste_baseTransacoesGestao WHERE loja_id = 1")
        cursor.execute("DELETE FROM teste_baseTransacoesGestaoErroCarga WHERE loja_id = 1")
        
        # Inserir registro de teste para Loja 1 PARCELADO
        cursor.execute("""
        INSERT INTO teste_pinbankExtratoPOS (
            id, NsuOperacao, NumeroParcela, DataTransacao, ValorBruto, 
            ValorLiquido, TipoTransacao, Bandeira, loja_id, CPF, lido
        ) VALUES (
            999902, '654321', 1, '2023-01-01', 200.00, 
            190.00, 'CREDITO', 'MASTERCARD', 1, '98765432100', 0
        )
        """)
    
    # Executar comando
    cmd = Command()
    cmd.handle()
    
    # Verificar resultados
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT valores_72, valores_74, valores_76, valores_26
        FROM teste_baseTransacoesGestao
        WHERE loja_id = 1 AND nsu_operacao = '654321'
        """)
        resultado = cursor.fetchone()
        
        if resultado:
            valores_72, valores_74, valores_76, valores_26 = resultado
            print(f"valores[72] = {valores_72}")
            print(f"valores[74] = {valores_74}")
            print(f"valores[76] = {valores_76} (Soma de valores[72] + valores[74])")
            print(f"valores[26] = {valores_26} (Valor final com ajustes)")
        else:
            print("Nenhum resultado encontrado para Loja 1 PARCELADO")

def testar_loja_15_parcelado():
    """
    Testa o cálculo para Loja 15 PARCELADO
    """
    print("\n=== TESTE LOJA 15 PARCELADO ===")
    
    # Limpar tabelas de teste
    with connection.cursor() as cursor:
        cursor.execute("DELETE FROM teste_baseTransacoesGestao WHERE loja_id = 15")
        cursor.execute("DELETE FROM teste_baseTransacoesGestaoErroCarga WHERE loja_id = 15")
        
        # Inserir registro de teste para Loja 15 PARCELADO
        cursor.execute("""
        INSERT INTO teste_pinbankExtratoPOS (
            id, NsuOperacao, NumeroParcela, DataTransacao, ValorBruto, 
            ValorLiquido, TipoTransacao, Bandeira, loja_id, CPF, lido
        ) VALUES (
            999903, '789012', 1, '2023-01-01', 300.00, 
            285.00, 'CREDITO', 'MASTERCARD', 15, '45678912300', 0
        )
        """)
    
    # Executar comando
    cmd = Command()
    cmd.handle()
    
    # Verificar resultados
    with connection.cursor() as cursor:
        cursor.execute("""
        SELECT valores_72, valores_74, valores_76, valores_26
        FROM teste_baseTransacoesGestao
        WHERE loja_id = 15 AND nsu_operacao = '789012'
        """)
        resultado = cursor.fetchone()
        
        if resultado:
            valores_72, valores_74, valores_76, valores_26 = resultado
            print(f"valores[72] = {valores_72}")
            print(f"valores[74] = {valores_74}")
            print(f"valores[76] = {valores_76} (Soma de valores[72] + valores[74])")
            print(f"valores[26] = {valores_26} (Valor final com ajustes)")
        else:
            print("Nenhum resultado encontrado para Loja 15 PARCELADO")

if __name__ == "__main__":
    print("Iniciando testes de cálculos financeiros...")
    testar_loja_16_credito()
    testar_loja_1_parcelado()
    testar_loja_15_parcelado()
    print("\nTestes concluídos!")
