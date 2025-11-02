#!/usr/bin/env python
"""
Script de teste para o método efetuar_transacao_cartao_tokenizado do TransacoesPinbankService
"""
import os
import sys
import django
import json
from datetime import datetime

# Configurar Django
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.base')
django.setup()

from pinbank.services_transacoes_pagamento import TransacoesPinbankService
from wallclub_core.utilitarios.log_control import registrar_log

def testar_transacao_cartao_tokenizado():
    """Testa o método efetuar_transacao_cartao_tokenizado"""
    
    print("🔄 Iniciando teste do método efetuar_transacao_cartao_tokenizado...")
    
    try:
        # Inicializar serviço
        service = TransacoesPinbankService()
        print("✅ TransacoesPinbankService inicializado")
        
        # Dados da transação com cartão tokenizado - todos os campos obrigatórios
        dados_transacao = {
            'cartao_id': '6a730612fb4943d682dc09cd420b2619',  # Cartão já tokenizado
            'valor': 15.00,  # R$ 15,00
            'forma_pagamento': '1',  # 1=Crédito à vista
            'quantidade_parcelas': 1,
            'descricao_pedido': 'Teste transacao tokenizada WallClub Django',
            'ip_address_comprador': '44.214.49.0',
            'cpf_comprador': 17653377807,
            'nome_comprador': 'Jean Ferreira',
            'transacao_pre_autorizada': False
        }
        
        print("📋 Dados da transação tokenizada preparados:")
        print(f"   Cartão ID: {dados_transacao['cartao_id'][:8]}...{dados_transacao['cartao_id'][-8:]}")
        print(f"   Valor: R$ {dados_transacao['valor']:.2f}")
        print(f"   Parcelas: {dados_transacao['quantidade_parcelas']}x")
        print(f"   Forma: {dados_transacao['forma_pagamento']}")
        print(f"   CPF: {dados_transacao['cpf_comprador']}")
        
        # Executar transação
        print("\n🔄 Executando transação com cartão tokenizado...")
        resultado = service.efetuar_transacao_cartao_tokenizado(dados_transacao)
        
        # Exibir resultado
        print("\n📊 RESULTADO DA TRANSAÇÃO TOKENIZADA:")
        print("=" * 70)
        print(f"Sucesso: {resultado.get('sucesso', 'N/A')}")
        print(f"Mensagem: {resultado.get('mensagem', 'N/A')}")
        
        if resultado.get('sucesso'):
            dados = resultado.get('dados', {})
            print(f"NSU: {dados.get('nsu', 'N/A')}")
            print(f"Código Autorização: {dados.get('codigo_autorizacao', 'N/A')}")
            print(f"Result Code: {dados.get('result_code', 'N/A')}")
            print(f"Cartão ID: {dados.get('cartao_id', 'N/A')}")
            print(f"Valor: R$ {dados.get('valor', 'N/A')}")
            print(f"Forma Pagamento: {dados.get('forma_pagamento', 'N/A')}")
            print(f"CPF Comprador: {dados.get('cpf_comprador', 'N/A')}")
            print(f"Nome Comprador: {dados.get('nome_comprador', 'N/A')}")
        else:
            print(f"Result Code: {resultado.get('result_code', 'N/A')}")
            print(f"Validation Result Code: {resultado.get('validation_result_code', 'N/A')}")
            if resultado.get('errors'):
                print("Erros:")
                for error in resultado['errors']:
                    print(f"  - {error.get('ErrorMessage', 'N/A')}")
        
        print("=" * 70)
        
        # Log do resultado
        registrar_log('teste.pinbank.transacao.token', f"Resultado transação tokenizada: {json.dumps(resultado, default=str)}")
        
        # Salvar resultado completo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/app/logs/teste_transacao_tokenizada_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                'dados_entrada': dados_transacao,
                'resultado': resultado,
                'timestamp': timestamp
            }, f, indent=2, default=str)
        
        print(f"📄 Resultado completo salvo em: {filename}")
        
        return resultado.get('sucesso', False)
        
    except Exception as e:
        print(f"\n❌ ERRO NA TRANSAÇÃO TOKENIZADA:")
        print(f"   {str(e)}")
        registrar_log('teste.pinbank.transacao.token', f"ERRO: {str(e)}")
        import traceback
        print(f"   Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("🚀 TESTE DO MÉTODO efetuar_transacao_cartao_tokenizado")
    print("=" * 70)
    
    # Teste com cartão tokenizado
    testar_transacao_cartao_tokenizado()
