"""
Script de Teste - Pré-Autorização + Captura + Estorno
Testa os 3 métodos: efetuar_transacao, capturar_transacao, cancelar_transacao
"""
import os
import sys
import django
from decimal import Decimal
from datetime import datetime

# Configurar Django
sys.path.insert(0, '/Users/jeanlessa/wall_projects/WallClub_backend/services/django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')
django.setup()

from pinbank.services_transacoes_pagamento import TransacoesPinbankService

# ========== CONFIGURAÇÕES DE TESTE ==========
# Credenciais hardcoded para testes locais
USE_CREDENCIAIS_TESTE = True  # True = usar credenciais abaixo | False = usar da loja
CODIGO_CANAL_TESTE = 47
CODIGO_CLIENTE_TESTE = 3510
KEY_LOJA_TESTE = "11384322623341877660"  # Ajustar se necessário
# ============================================


class TransacoesPinbankServiceTeste(TransacoesPinbankService):
    """Serviço de teste que sobrescreve credenciais"""

    def _obter_credenciais_loja(self, loja_id: int = None) -> dict:
        """Sobrescreve para usar credenciais de teste"""
        if USE_CREDENCIAIS_TESTE:
            print(f"   [TESTE] Usando credenciais hardcoded: Canal={CODIGO_CANAL_TESTE}, Cliente={CODIGO_CLIENTE_TESTE}")
            return {
                'codigo_canal': CODIGO_CANAL_TESTE,
                'codigo_cliente': CODIGO_CLIENTE_TESTE,
                'key_loja': KEY_LOJA_TESTE
            }
        else:
            # Usar credenciais da loja normalmente
            return super()._obter_credenciais_loja(loja_id)


def teste_1_pre_autorizacao_e_captura():
    """
    Teste 1: Pré-Autorização + Captura
    - Faz transação com TransacaoPreAutorizada=true
    - Captura a transação
    """
    print("\n" + "="*80)
    print("TESTE 1: PRÉ-AUTORIZAÇÃO + CAPTURA")
    print("="*80)

    loja_id = 1  # Usado apenas se USE_CREDENCIAIS_TESTE=False
    service = TransacoesPinbankServiceTeste(loja_id=loja_id)

    # Dados da transação
    dados_transacao = {
        'valor': Decimal('10.00'),  # R$ 10,00 para teste
        'numero_cartao': '5111111111111111',  # Cartão de teste
        'nome_cartao': 'TESTE PRE AUTORIZACAO',
        'validade_mes': '12',
        'validade_ano': '2025',
        'cvv': '123',
        'numero_parcelas': 1,
        'tipo_compra': 'CREDIT_ONE_INSTALLMENT',
        'terminal_id': 'TESTE001',
        'documento_cliente': '12345678900'
    }

    try:
        # 1. PRÉ-AUTORIZAR
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 1. Fazendo PRÉ-AUTORIZAÇÃO...")
        print(f"   Valor: R$ {dados_transacao['valor']:.2f}")
        print(f"   Cartão: {dados_transacao['numero_cartao'][:6]}******{dados_transacao['numero_cartao'][-4:]}")

        resultado_pre = service.efetuar_transacao(
            dados_transacao=dados_transacao,
            transacao_pre_autorizada=True  # PRÉ-AUTORIZAÇÃO
        )

        print(f"\n   Resultado:")
        print(f"   - Sucesso: {resultado_pre['sucesso']}")
        print(f"   - Mensagem: {resultado_pre['mensagem']}")

        if not resultado_pre['sucesso']:
            print(f"\n   ❌ ERRO na pré-autorização. Abortando teste.")
            return False

        nsu = resultado_pre['dados']['nsu']
        codigo_autorizacao = resultado_pre['dados'].get('codigo_autorizacao', 'N/A')

        print(f"   - NSU: {nsu}")
        print(f"   - Código Autorização: {codigo_autorizacao}")
        print(f"\n   ✅ PRÉ-AUTORIZAÇÃO realizada com sucesso!")

        # Aguardar confirmação para capturar
        input(f"\n   Pressione ENTER para CAPTURAR a transação (NSU: {nsu})...")

        # 2. CAPTURAR
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 2. CAPTURANDO transação...")
        print(f"   NSU: {nsu}")
        print(f"   Valor: R$ {dados_transacao['valor']:.2f}")

        resultado_captura = service.capturar_transacao(
            nsu_operacao=nsu,
            valor=dados_transacao['valor']
        )

        print(f"\n   Resultado:")
        print(f"   - Sucesso: {resultado_captura['sucesso']}")
        print(f"   - Mensagem: {resultado_captura['mensagem']}")

        if resultado_captura['sucesso']:
            codigo_captura = resultado_captura['dados'].get('codigo_autorizacao_captura', 'N/A')
            print(f"   - Código Captura: {codigo_captura}")
            print(f"\n   ✅ CAPTURA realizada com sucesso!")
        else:
            print(f"\n   ❌ ERRO na captura")
            if 'errors' in resultado_captura:
                for error in resultado_captura['errors']:
                    print(f"      - {error.get('ErrorMessage', '')}")

        print("\n" + "-"*80)
        print("TESTE 1 CONCLUÍDO")
        print("-"*80)
        return resultado_captura['sucesso']

    except Exception as e:
        print(f"\n   ❌ ERRO INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def teste_2_transacao_e_estorno():
    """
    Teste 2: Transação Normal + Estorno
    - Faz transação normal (sem pré-autorização)
    - Cancela (estorna) a transação
    """
    print("\n" + "="*80)
    print("TESTE 2: TRANSAÇÃO NORMAL + ESTORNO")
    print("="*80)

    loja_id = 1  # Usado apenas se USE_CREDENCIAIS_TESTE=False
    service = TransacoesPinbankServiceTeste(loja_id=loja_id)

    # Dados da transação
    dados_transacao = {
        'valor': Decimal('5.00'),  # R$ 5,00 para teste
        'numero_cartao': '5111111111111111',  # Cartão de teste
        'nome_cartao': 'TESTE ESTORNO',
        'validade_mes': '12',
        'validade_ano': '2025',
        'cvv': '123',
        'numero_parcelas': 1,
        'tipo_compra': 'CREDIT_ONE_INSTALLMENT',
        'terminal_id': 'TESTE002',
        'documento_cliente': '12345678900'
    }

    try:
        # 1. TRANSAÇÃO NORMAL
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 1. Fazendo TRANSAÇÃO NORMAL...")
        print(f"   Valor: R$ {dados_transacao['valor']:.2f}")
        print(f"   Cartão: {dados_transacao['numero_cartao'][:6]}******{dados_transacao['numero_cartao'][-4:]}")

        resultado_transacao = service.efetuar_transacao(
            dados_transacao=dados_transacao,
            transacao_pre_autorizada=False  # TRANSAÇÃO NORMAL
        )

        print(f"\n   Resultado:")
        print(f"   - Sucesso: {resultado_transacao['sucesso']}")
        print(f"   - Mensagem: {resultado_transacao['mensagem']}")

        if not resultado_transacao['sucesso']:
            print(f"\n   ❌ ERRO na transação. Abortando teste.")
            return False

        nsu = resultado_transacao['dados']['nsu']
        codigo_autorizacao = resultado_transacao['dados'].get('codigo_autorizacao', 'N/A')

        print(f"   - NSU: {nsu}")
        print(f"   - Código Autorização: {codigo_autorizacao}")
        print(f"\n   ✅ TRANSAÇÃO realizada com sucesso!")

        # Aguardar confirmação para estornar
        input(f"\n   Pressione ENTER para ESTORNAR a transação (NSU: {nsu})...")

        # 2. ESTORNAR
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 2. ESTORNANDO transação...")
        print(f"   NSU: {nsu}")
        print(f"   Valor: R$ {dados_transacao['valor']:.2f}")

        resultado_estorno = service.cancelar_transacao(
            nsu_operacao=nsu,
            valor=dados_transacao['valor']
        )

        print(f"\n   Resultado:")
        print(f"   - Sucesso: {resultado_estorno['sucesso']}")
        print(f"   - Mensagem: {resultado_estorno['mensagem']}")

        if resultado_estorno['sucesso']:
            codigo_cancelamento = resultado_estorno['dados'].get('codigo_autorizacao_cancelamento', 'N/A')
            print(f"   - Código Cancelamento: {codigo_cancelamento}")
            print(f"\n   ✅ ESTORNO realizado com sucesso!")
        else:
            print(f"\n   ❌ ERRO no estorno")
            if 'errors' in resultado_estorno:
                for error in resultado_estorno['errors']:
                    print(f"      - {error.get('ErrorMessage', '')}")

        print("\n" + "-"*80)
        print("TESTE 2 CONCLUÍDO")
        print("-"*80)
        return resultado_estorno['sucesso']

    except Exception as e:
        print(f"\n   ❌ ERRO INESPERADO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*80)
    print("TESTES DE PRÉ-AUTORIZAÇÃO, CAPTURA E ESTORNO")
    print("="*80)
    print(f"Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    # Menu
    print("\nEscolha o teste:")
    print("1 - Pré-Autorização + Captura")
    print("2 - Transação Normal + Estorno")
    print("3 - Executar ambos")

    escolha = input("\nOpção (1/2/3): ").strip()

    resultados = []

    if escolha in ['1', '3']:
        resultado_1 = teste_1_pre_autorizacao_e_captura()
        resultados.append(('Teste 1', resultado_1))

    if escolha in ['2', '3']:
        if escolha == '3':
            input("\nPressione ENTER para iniciar Teste 2...")
        resultado_2 = teste_2_transacao_e_estorno()
        resultados.append(('Teste 2', resultado_2))

    # Resumo final
    print("\n" + "="*80)
    print("RESUMO DOS TESTES")
    print("="*80)

    for nome, resultado in resultados:
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{nome}: {status}")

    print("\n" + "="*80)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Testes interrompidos pelo usuário")
    except Exception as e:
        print(f"\n\n❌ ERRO FATAL: {str(e)}")
        import traceback
        traceback.print_exc()
