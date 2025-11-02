#!/usr/bin/env python
"""
Script para debugar payload Pinbank - testa diferentes combinações
"""
import os
import sys
import django
import json
import requests
from datetime import datetime

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.base')
django.setup()

from pinbank.services import PinbankService

def testar_payload_minimo():
    """Testa com payload absolutamente mínimo"""
    
    print("🔍 Teste 1: Payload mínimo obrigatório")
    
    service = PinbankService()
    token_data = service.obter_token()
    
    # Apenas campos obrigatórios
    payload_minimo = {
        "CodigoCanal": 395,
        "CodigoCliente": "m*TmHVA3onHC",
        "KeyLoja": "5xrfSG03XeYneK8h",
        "Valor": 1.00,
        "FormaPagamento": "CREDIT_ONE_INSTALLMENT"
    }
    
    resultado = executar_teste(service, token_data, payload_minimo, "Mínimo")
    return resultado

def testar_tipos_dados():
    """Testa diferentes tipos de dados"""
    
    print("\n🔍 Teste 2: Tipos de dados")
    
    service = PinbankService()
    token_data = service.obter_token()
    
    # Teste com CodigoCliente como int
    payload_int = {
        "CodigoCanal": 395,
        "CodigoCliente": 271681,  # Como int
        "KeyLoja": "5xrfSG03XeYneK8h",
        "Valor": 1.00,
        "FormaPagamento": "CREDIT_ONE_INSTALLMENT"
    }
    
    resultado1 = executar_teste(service, token_data, payload_int, "CodigoCliente INT")
    
    # Teste com valores como string
    payload_string = {
        "CodigoCanal": "395",  # Como string
        "CodigoCliente": "m*TmHVA3onHC",
        "KeyLoja": "5xrfSG03XeYneK8h",
        "Valor": "1.00",  # Como string
        "FormaPagamento": "CREDIT_ONE_INSTALLMENT"
    }
    
    resultado2 = executar_teste(service, token_data, payload_string, "Valores STRING")
    
    return resultado1 or resultado2

def testar_formas_pagamento():
    """Testa diferentes formas de pagamento"""
    
    print("\n🔍 Teste 3: Formas de pagamento")
    
    service = PinbankService()
    token_data = service.obter_token()
    
    formas = [
        "CREDIT_ONE_INSTALLMENT",
        "DEBIT",
        "PIX"
    ]
    
    for forma in formas:
        payload = {
            "CodigoCanal": 395,
            "CodigoCliente": "m*TmHVA3onHC",
            "KeyLoja": "5xrfSG03XeYneK8h",
            "Valor": 1.00,
            "FormaPagamento": forma
        }
        
        if forma == "PIX":
            # PIX não precisa de parcelas
            pass
        else:
            payload["QuantidadeParcelas"] = 1
            
        resultado = executar_teste(service, token_data, payload, f"FormaPagamento: {forma}")
        if resultado:
            return True
    
    return False

def executar_teste(service, token_data, payload, descricao):
    """Executa um teste específico"""
    
    try:
        print(f"\n--- {descricao} ---")
        print(f"Payload: {json.dumps(payload, indent=2)}")
        
        # Criptografar
        payload_criptografado = service.criptografar_payload(payload)
        
        # Requisição
        url = f"{service.base_url}Transacoes/EfetuarTransacaoEncrypted"
        headers = {
            'Authorization': f"{token_data['token_type']} {token_data['access_token']}",
            'Content-Type': 'application/json',
            'UserName': service.username,
            'RequestOrigin': '5'
        }
        
        response = requests.post(
            url,
            json=json.loads(payload_criptografado),
            headers=headers,
            timeout=30,
            verify=False
        )
        
        resposta = response.json()
        result_code = resposta.get('ResultCode')
        message = resposta.get('Message')
        
        print(f"Status: {response.status_code}")
        print(f"ResultCode: {result_code}")
        print(f"Message: {message}")
        
        if result_code != 3:  # 3 = Bad Request
            print("✅ SUCESSO! Este payload funcionou!")
            return True
        else:
            print("❌ Bad Request")
            return False
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    print("🚀 DEBUG PAYLOAD PINBANK")
    print("=" * 50)
    
    # Teste 1: Payload mínimo
    if testar_payload_minimo():
        return
    
    # Teste 2: Tipos de dados
    if testar_tipos_dados():
        return
    
    # Teste 3: Formas de pagamento
    if testar_formas_pagamento():
        return
    
    print("\n❌ Nenhum payload funcionou")
    print("Possíveis causas:")
    print("1. Credenciais incorretas")
    print("2. Ambiente de teste inativo")
    print("3. Estrutura da API mudou")
    print("4. Campos obrigatórios não identificados")

if __name__ == "__main__":
    main()
