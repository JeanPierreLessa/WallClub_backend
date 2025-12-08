"""
Serviços V2 para APIs POSP2
Versão com cashback loja integrado
"""

import json
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal, ROUND_HALF_UP

from .services import POSP2Service
from wallclub_core.utilitarios.log_control import registrar_log


class POSP2ServiceV2(POSP2Service):
    """
    Serviço V2 com cashback loja integrado na simulação
    """

    def simular_parcelas_v2(self, valor: float, terminal: str, wall: str = 's', cliente_id: int = 0) -> Dict[str, Any]:
        """
        Simula valores para todas as modalidades incluindo cashback loja.

        Args:
            valor: Valor da transação
            terminal: ID do terminal
            wall: Modalidade (S=Com Wall, N=Sem Wall)
            cliente_id: ID do cliente (0 se não identificado)

        Returns:
            Dict com estrutura completa incluindo cashback loja
        """
        try:
            registrar_log('posp2.v2', '========================================')
            registrar_log('posp2.v2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.v2.simular_parcelas')
            registrar_log('posp2.v2', '========================================')
            registrar_log('posp2.v2', f'Simulando parcelas V2 - Terminal: {terminal}, Valor: {valor}, Cliente: {cliente_id}')

            # Validação de parâmetros
            if not terminal or valor <= 0:
                registrar_log('posp2.v2', 'ERRO: Parâmetros inválidos', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Parâmetros inválidos. Terminal e valor são obrigatórios e valor deve ser maior que zero.',
                    'dados': {'parcelas': {}}
                }

            # Buscar dados do terminal
            dados_terminal = self.obter_dados_terminal(terminal)
            if not dados_terminal or 'loja_id' not in dados_terminal:
                registrar_log('posp2.v2', f'Terminal não encontrado: {terminal}')
                return {
                    'sucesso': False,
                    'mensagem': 'Terminal não encontrado ou não vinculado a uma loja',
                    'dados': {'parcelas': {}}
                }

            loja_id = dados_terminal['loja_id']
            canal_id = dados_terminal.get('canal_id', 1)

            # Usar calculadora do parametros_wallclub
            from parametros_wallclub.services import CalculadoraDesconto
            from apps.cashback.services import CashbackService

            calculadora = CalculadoraDesconto()
            data = datetime.now().strftime('%Y-%m-%d')
            valor_original = Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            parcelas_resultado = {}

            # Simular PIX
            parcelas_resultado["PIX"] = self._simular_modalidade_v2(
                calculadora=calculadora,
                valor_original=valor_original,
                forma='PIX',
                num_parcelas=0,
                loja_id=loja_id,
                canal_id=canal_id,
                cliente_id=cliente_id,
                wall=wall,
                data=data,
                forma_pagamento_key='CASH',
                descricao_base='PIX'
            )

            # Simular DÉBITO
            parcelas_resultado["DEBITO"] = self._simular_modalidade_v2(
                calculadora=calculadora,
                valor_original=valor_original,
                forma='DEBITO',
                num_parcelas=0,
                loja_id=loja_id,
                canal_id=canal_id,
                cliente_id=cliente_id,
                wall=wall,
                data=data,
                forma_pagamento_key='DEBIT',
                descricao_base='Débito'
            )

            # Simular CRÉDITO 1x até 12x
            for num_parcelas in range(1, 13):
                forma = "A VISTA" if num_parcelas == 1 else "PARCELADO SEM JUROS"
                forma_key = "CREDIT_ONE_INSTALLMENT" if num_parcelas == 1 else "CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST"

                parcelas_resultado[num_parcelas] = self._simular_modalidade_v2(
                    calculadora=calculadora,
                    valor_original=valor_original,
                    forma=forma,
                    num_parcelas=num_parcelas,
                    loja_id=loja_id,
                    canal_id=canal_id,
                    cliente_id=cliente_id,
                    wall=wall,
                    data=data,
                    forma_pagamento_key=forma_key,
                    descricao_base='Crédito'
                )

            registrar_log('posp2.v2', f'Simulação V2 concluída - {len(parcelas_resultado)} opções geradas')

            return {
                'sucesso': True,
                'mensagem': 'Simulação realizada com sucesso',
                'dados': {
                    'parcelas': parcelas_resultado,
                    'cards_principais': [3, 6, 10, 12]
                }
            }

        except Exception as e:
            registrar_log('posp2.v2', f'Erro ao simular parcelas V2: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro interno na simulação: {str(e)}',
                'dados': {'parcelas': {}}
            }

    def _simular_modalidade_v2(self, calculadora, valor_original, forma, num_parcelas,
                               loja_id, canal_id, cliente_id, wall, data,
                               forma_pagamento_key, descricao_base):
        """Helper para simular uma modalidade específica"""
        from apps.cashback.services import CashbackService

        # Calcular desconto Wall
        valor_com_desconto = calculadora.calcular_desconto(
            valor_original=valor_original,
            data=data,
            forma=forma,
            parcelas=num_parcelas,
            id_loja=loja_id,
            wall=wall
        )

        if valor_com_desconto is None:
            return None

        # Calcular valor da parcela
        valor_parcela = valor_com_desconto / num_parcelas if num_parcelas > 0 else valor_com_desconto

        # Mensagem para cliente
        if valor_com_desconto < valor_original:
            mensagem = "(c/desconto)"
        elif valor_com_desconto > valor_original:
            mensagem = "(c/encargos)"
        else:
            mensagem = ""

        # Calcular cashback Wall
        valor_cashback_wall = Decimal('0')
        percentual_cashback_wall = Decimal('0')
        cashback_wall_parametro_id = None

        if wall.upper() == 'S':
            try:
                calculadora_cashback = CalculadoraDesconto()
                valor_com_cashback = calculadora_cashback.calcular_desconto(
                    valor_original=valor_com_desconto,
                    data=data,
                    forma=forma,
                    parcelas=num_parcelas,
                    id_loja=loja_id,
                    wall='C'
                )
                # Parâmetros wall='C' com valores positivos aumentam o valor (cashback)
                valor_cashback_wall = valor_com_cashback - valor_com_desconto if valor_com_cashback else Decimal('0')
                percentual_cashback_wall = (valor_cashback_wall / valor_com_desconto * 100) if valor_com_desconto > 0 else Decimal('0')
                cashback_wall_parametro_id = calculadora_cashback.parametro_id
                registrar_log('posp2.v2', f'Cashback Wall calculado: {valor_cashback_wall} (parametro_id: {cashback_wall_parametro_id})')
            except Exception as e:
                registrar_log('posp2.v2', f'Erro ao calcular cashback Wall: {str(e)}', nivel='WARNING')

        # Simular cashback loja
        cashback_loja_info = {"aplicavel": False, "valor": "0.00"}
        valor_cashback_loja = Decimal('0')

        try:
            forma_pagamento_map = {
                'CASH': 'PIX',
                'DEBIT': 'DEBITO',
                'CREDIT_ONE_INSTALLMENT': 'CREDITO',
                'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': 'CREDITO'
            }
            forma_pagamento = forma_pagamento_map.get(forma_pagamento_key, 'CREDITO')

            resultado_loja = CashbackService.simular_cashback_loja(
                loja_id=loja_id,
                cliente_id=cliente_id,
                canal_id=canal_id,
                valor_transacao=valor_com_desconto,
                forma_pagamento=forma_pagamento
            )

            if resultado_loja and resultado_loja.get('aplicavel'):
                valor_cashback_loja = Decimal(str(resultado_loja['valor']))
                cashback_loja_info = {
                    'aplicavel': True,
                    'valor': f"{valor_cashback_loja:.2f}",
                    'regra_id': resultado_loja['regra_id'],
                    'regra_nome': resultado_loja['regra_nome'],
                    'tipo_concessao': resultado_loja['tipo_concessao'],
                    'valor_concessao': f"{resultado_loja['valor_concessao']:.2f}"
                }
        except Exception as e:
            registrar_log('posp2.v2', f'Erro ao simular cashback loja: {str(e)}', nivel='WARNING')

        # Cashback total
        cashback_total = valor_cashback_wall + valor_cashback_loja

        # Descrição formatada
        if num_parcelas == 0:
            descricao = f"{descricao_base}: R$ {valor_com_desconto:.2f}".replace('.', ',')
        elif num_parcelas == 1:
            descricao = f"À vista: R$ {valor_com_desconto:.2f}".replace('.', ',')
        else:
            descricao = f"{num_parcelas}x de R$ {valor_parcela:.2f}".replace('.', ',')

        return {
            "num_parcelas": num_parcelas if num_parcelas > 0 else 1,
            "valor_original": f"{valor_original:.2f}",
            "valor_total": f"{valor_com_desconto:.2f}",
            "valor_parcela": f"{valor_parcela:.2f}",
            "descricao": descricao,
            "forma_pagamento": forma_pagamento_key,
            "mensagem_para_cliente": mensagem,
            "desconto_wall": f"{(valor_original - valor_com_desconto):.2f}",
            "desconto_wall_parametro_id": calculadora.parametro_id,
            "cashback_wall": {
                "valor": f"{valor_cashback_wall:.2f}",
                "percentual": f"{percentual_cashback_wall:.2f}",
                "parametro_id": cashback_wall_parametro_id
            },
            "cashback_loja": cashback_loja_info,
            "cashback_total": f"{cashback_total:.2f}"
        }
