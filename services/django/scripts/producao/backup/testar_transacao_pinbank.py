#!/usr/bin/env python
"""
Script para testar transação Pinbank com dados de exemplo.
Execute via: docker exec wallclub-prod python manage.py shell < scripts/testar_transacao_pinbank.py
"""
from pinbank.services import PinbankService
import json
from datetime import datetime

def testar_transacao_pinbank():
    """Testa transação completa na API Pinbank"""
    
    print("🔄 Iniciando teste de transação Pinbank...")
    
    try:
        # Inicializar serviço
        service = PinbankService()
        print(" PinbankService inicializado")
        
        # Dados de exemplo para teste (apenas campos essenciais)
        dados_transacao = {
            "CodigoCanal": 395,
            "CodigoCliente": 271681,
            "KeyLoja": "TESTE_WALLCLUB_001",
            "NomeImpresso": "JEAN FERREIRA",
            "DataValidade": "08/33",
            "NumeroCartao": "4110490643279401",
            "CodigoSeguranca": "224",
            "Valor": 5.50,
            "FormaPagamento": "CREDIT_ONE_INSTALLMENT",
            "QuantidadeParcelas": 1,
            "DescricaoPedido": "Teste transacao WallClub Django",
            "IpAddressComprador": "10.0.1.46",
            "CpfComprador": 17653377807,
            "NomeComprador": "Jean Ferreira",
            "TransacaoPreAutorizada": False
        }
        
        print(" Dados da transação preparados:")
        print(f"   Valor: R$ {dados_transacao['Valor']}")
        print(f"   Cartão: {dados_transacao['NumeroCartao'][:4]}****{dados_transacao['NumeroCartao'][-4:]}")
        print(f"   Parcelas: {dados_transacao['QuantidadeParcelas']}x")
        
        # Executar transação
        print("\n🔄 Executando transação...")
        resultado = service.efetuar_transacao(dados_transacao)
        
        # Exibir resultado
        print("\n✅ TRANSAÇÃO EXECUTADA COM SUCESSO!")
        print("=" * 50)
        print(f"Código Autorização: {resultado.get('CodigoAutorizacao', 'N/A')}")
        print(f"NSU Operação: {resultado.get('NsuOperacao', 'N/A')}")
        print(f"Result Code: {resultado.get('ResultCode', 'N/A')}")
        print(f"Mensagem: {resultado.get('Message', 'N/A')}")
        print("=" * 50)
        
        # Salvar resultado completo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/app/logs/transacao_pinbank_teste_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(resultado, f, indent=2, default=str)
        
        print(f"📄 Resultado completo salvo em: {filename}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NA TRANSAÇÃO:")
        print(f"   {str(e)}")
        
        # Salvar erro
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        error_filename = f"/app/logs/erro_transacao_pinbank_{timestamp}.txt"
        
        try:
            with open(error_filename, 'w') as f:
                f.write(f"Erro na transação Pinbank: {str(e)}\n")
                f.write(f"Timestamp: {datetime.now()}\n")
        except Exception as e:
            print(f" Erro salvo em: {error_filename}")
            return False

# Executar o teste
testar_transacao_pinbank()
