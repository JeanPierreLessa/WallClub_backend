#!/usr/bin/env python
"""
Script de teste para endpoints e-commerce Own Financial (OPPWA API)
Testa todos os métodos implementados em TransacoesOwnService

Uso:
    python scripts/teste_own_ecommerce.py
"""
import os
import sys
import django
from decimal import Decimal

# Configurar Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services', 'django'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')
django.setup()

from adquirente_own.services_transacoes_pagamento import TransacoesOwnService


def print_section(title):
    """Imprime cabeçalho de seção"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_result(resultado):
    """Imprime resultado formatado"""
    import json
    print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))


def teste_1_pagamento_debito():
    """Teste 1: Pagamento débito/crédito simples"""
    print_section("TESTE 1: Pagamento Débito/Crédito")

    service = TransacoesOwnService(loja_id=15)  # Loja teste Own

    # Dados de teste (cartão de teste VISA)
    card_data = {
        'number': '4200000000000000',  # Cartão de teste Visa
        'holder': 'TESTE WALLCLUB',
        'expiry_month': '12',
        'expiry_year': '2027',
        'cvv': '123',
        'brand': 'VISA'
    }

    print("\n📝 Dados do cartão:")
    print(f"  Número: {card_data['number'][:6]}...{card_data['number'][-4:]}")
    print(f"  Titular: {card_data['holder']}")
    print(f"  Validade: {card_data['expiry_month']}/{card_data['expiry_year']}")
    print(f"  Valor: R$ 10,00")
    print(f"  Parcelas: 1x")

    resultado = service.create_payment_debit(
        card_data=card_data,
        amount=Decimal('10.00'),
        parcelas=1,
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)

    return resultado.get('own_payment_id') if resultado.get('sucesso') else None


def teste_2_tokenizacao():
    """Teste 2: Tokenização (PA + createRegistration)"""
    print_section("TESTE 2: Tokenização de Cartão")

    service = TransacoesOwnService(loja_id=15)

    card_data = {
        'number': '4200000000000000',  # Cartão de teste Visa
        'holder': 'TESTE TOKEN WALLCLUB',
        'expiry_month': '12',
        'expiry_year': '2027',
        'cvv': '123',
        'brand': 'VISA'
    }

    print("\n📝 Tokenizando cartão:")
    print(f"  Número: {card_data['number'][:6]}...{card_data['number'][-4:]}")
    print(f"  Titular: {card_data['holder']}")
    print(f"  Valor PA: R$ 1,00")

    resultado = service.create_payment_with_tokenization(
        card_data=card_data,
        amount=Decimal('1.00'),
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)

    return resultado.get('registration_id') if resultado.get('sucesso') else None


def teste_3_consultar_token(registration_id):
    """Teste 3: Consultar detalhes do token"""
    print_section("TESTE 3: Consultar Detalhes do Token")

    if not registration_id:
        print("⚠️ Nenhum registration_id disponível. Pulando teste.")
        return

    service = TransacoesOwnService(loja_id=15)

    print(f"\n📝 Consultando registration: {registration_id}")

    resultado = service.get_registration_details(
        registration_id=registration_id,
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)


def teste_4_listar_tokens():
    """Teste 4: Listar todos os tokens"""
    print_section("TESTE 4: Listar Tokens")

    service = TransacoesOwnService(loja_id=15)

    print("\n📝 Listando todos os registrations da loja...")

    resultado = service.list_registrations(loja_id=15)

    print("\n✅ Resultado:")
    print_result(resultado)


def teste_5_pagamento_com_token(registration_id):
    """Teste 5: Pagamento com token existente"""
    print_section("TESTE 5: Pagamento com Token")

    if not registration_id:
        print("⚠️ Nenhum registration_id disponível. Pulando teste.")
        return None

    service = TransacoesOwnService(loja_id=15)

    print(f"\n📝 Pagamento usando registration: {registration_id}")
    print(f"  Valor: R$ 25,00")
    print(f"  Parcelas: 2x")

    resultado = service.create_payment_with_registration(
        registration_id=registration_id,
        amount=Decimal('25.00'),
        parcelas=2,
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)

    return resultado.get('own_payment_id') if resultado.get('sucesso') else None


def teste_6_estorno(payment_id):
    """Teste 6: Estorno de pagamento"""
    print_section("TESTE 6: Estorno de Pagamento")

    if not payment_id:
        print("⚠️ Nenhum payment_id disponível. Pulando teste.")
        return

    service = TransacoesOwnService(loja_id=15)

    print(f"\n📝 Estornando payment: {payment_id}")
    print(f"  Valor: R$ 10,00")

    resultado = service.refund_payment(
        payment_id=payment_id,
        amount=Decimal('10.00'),
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)


def teste_7_excluir_token(registration_id):
    """Teste 7: Excluir token (deregistration)"""
    print_section("TESTE 7: Excluir Token")

    if not registration_id:
        print("⚠️ Nenhum registration_id disponível. Pulando teste.")
        return

    service = TransacoesOwnService(loja_id=15)

    print(f"\n📝 Excluindo registration: {registration_id}")

    resultado = service.delete_registration(
        registration_id=registration_id,
        loja_id=15
    )

    print("\n✅ Resultado:")
    print_result(resultado)


def teste_8_adapter_pinbank():
    """Teste 8: Métodos adapter (compatibilidade Pinbank)"""
    print_section("TESTE 8: Métodos Adapter (Compatibilidade Pinbank)")

    service = TransacoesOwnService(loja_id=15)

    # Teste efetuar_transacao_cartao (adapter)
    print("\n📝 Testando efetuar_transacao_cartao() [adapter]")

    dados_transacao = {
        'numero_cartao': '4200000000000000',
        'data_validade': '12/2025',
        'codigo_seguranca': '123',
        'nome_impresso': 'TESTE ADAPTER',
        'valor': 5.00,
        'quantidade_parcelas': 1,
        'forma_pagamento': '1',
        'bandeira': 'VISA'
    }

    resultado = service.efetuar_transacao_cartao(dados_transacao)

    print("\n✅ Resultado:")
    print_result(resultado)


def main():
    """Executa todos os testes"""
    print("\n" + "🚀" * 40)
    print("  TESTE COMPLETO - Own Financial E-commerce API (OPPWA)")
    print("🚀" * 40)

    try:
        # Teste 1: Pagamento simples
        payment_id = teste_1_pagamento_debito()

        # Teste 2: Tokenização
        registration_id = teste_2_tokenizacao()

        # Teste 3: Consultar token
        teste_3_consultar_token(registration_id)

        # Teste 4: Listar tokens
        teste_4_listar_tokens()

        # Teste 5: Pagamento com token
        payment_id_token = teste_5_pagamento_com_token(registration_id)

        # Teste 6: Estorno
        teste_6_estorno(payment_id)

        # Teste 7: Excluir token
        teste_7_excluir_token(registration_id)

        # Teste 8: Adapter Pinbank
        teste_8_adapter_pinbank()

        print("\n" + "✅" * 40)
        print("  TODOS OS TESTES CONCLUÍDOS")
        print("✅" * 40 + "\n")

    except Exception as e:
        print("\n" + "❌" * 40)
        print(f"  ERRO: {str(e)}")
        print("❌" * 40 + "\n")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
