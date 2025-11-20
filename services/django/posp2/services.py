"""
Serviços para APIs POSP2
Migração fiel dos scripts PHP originais
"""

import json
import hashlib
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal, ROUND_HALF_UP
from django.db import connection, transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings

from .models import POSP2Transaction, VersaoTerminal
from wallclub_core.utilitarios.funcoes_gerais import proxima_sexta_feira, calcular_cet, formatar_valor_brasileiro
from parametros_wallclub.services import ParametrosService, CalculadoraDesconto
from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
from pinbank.services import PinbankService
from wallclub_core.utilitarios.log_control import registrar_log
from django.apps import apps
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
from gestao_financeira.models import BaseTransacoesGestao
from wallclub_core.seguranca.validador_cpf import ValidadorCPFService

class POSP2Service:
    """
    Serviço principal para operações POSP2
    Migração das funcionalidades do PHP original
    """
    def __init__(self):
        self.parametros_service = ParametrosService()
        self.pinbank_service = PinbankService()

    def validar_versao_terminal(self, versao: str) -> Dict[str, Any]:
        """
        Valida se uma versão de terminal é permitida
        Formato padronizado da API POSP2
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.validar_versao')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.validar_versao - Validando versão do terminal: {versao}')

            # Validação de entrada
            if not versao or versao.strip() == '':
                registrar_log('posp2', 'posp2.validar_versao - ERRO: Parâmetro versao_terminal não fornecido', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Parâmetro versao_terminal não fornecido',
                    'dados': {
                        'permitida': False
                    }
                }

            # Buscar versão no banco
            versao_obj = VersaoTerminal.objects.filter(
                versao_terminal=versao
            ).first()

            # Se não encontrou, retorna erro
            if not versao_obj:
                registrar_log('posp2', f'posp2.validar_versao - ERRO: Versão terminal não encontrado: {versao}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Versão terminal não encontrado',
                    'dados': {
                        'permitida': False
                    }
                }

            # Verificar se a versão é permitida
            if versao_obj.permitida:
                registrar_log('posp2', f'posp2.validar_versao - Versão {versao} é PERMITIDA')
                return {
                    'sucesso': True,
                    'mensagem': 'Versão permitida',
                    'dados': {
                        'permitida': True,
                        'versao': versao
                    }
                }
            else:
                registrar_log('posp2', f'posp2.validar_versao - Versão {versao} NÃO é permitida')
                return {
                    'sucesso': True,
                    'mensagem': 'Versão não permitida',
                    'dados': {
                        'permitida': False,
                        'versao': versao
                    }
                }

        except Exception as e:
            registrar_log('posp2', f'Erro ao validar versão terminal: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno na validação',
                'dados': {
                    'permitida': False
                }
            }

    def simular_parcelas(self, valor: float, terminal: str, wall: str = 's') -> Dict[str, Any]:
        """
        Simula valores para todas as modalidades de pagamento
        Replica exatamente o comportamento do simula_parcelas.php
        Formato padronizado da API POSP2
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.simular_parcelas')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.simular_parcelas - Simulando parcelas - Terminal: {terminal}, Valor: {valor}')

            # Validação de parâmetros (igual ao PHP)
            if not terminal or valor <= 0:
                registrar_log('posp2', 'posp2.simular_parcelas - ERRO: Parâmetros inválidos', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Parâmetros inválidos. Terminal e valor são obrigatórios e valor deve ser maior que zero.',
                    'dados': {
                        'parcelas': {}
                    }
                }

            # Buscar dados do terminal (já valida existência e associação com loja)
            dados_terminal = self.obter_dados_terminal(terminal)
            if not dados_terminal or 'loja_id' not in dados_terminal:
                registrar_log('posp2', f'posp2.simular_parcelas - Terminal não encontrado ou não associado a loja: {terminal}')
                return {
                    'sucesso': False,
                    'mensagem': 'Terminal não encontrado ou não vinculado a uma loja',
                    'dados': {
                        'parcelas': {}
                    }
                }

            id_loja = dados_terminal['loja_id']

            # Usar data atual em runtime
            data = datetime.now().strftime('%Y-%m-%d')

            # Converter valor para Decimal com precisão exata
            valor_original = Decimal(str(valor)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Definir nomenclatura de retorno (igual ao PHP)
            sem_desconto = ""
            com_desconto = "(c/desconto)"
            com_encargos = ""

            # Usar calculadora do parametros_wallclub
            from parametros_wallclub.services import CalculadoraDesconto
            calculadora = CalculadoraDesconto()

            # Preparar array de resultados (igual ao PHP)
            parcelas_resultado = {}

            # 1. SIMULAR PIX (igual ao PHP)
            registrar_log('posp2', 'posp2.simular_parcelas - Simulando PIX')
            valor_com_desconto = calculadora.calcular_desconto(
                valor_original=valor_original,
                data=data,
                forma='PIX',
                parcelas=0,
                id_loja=id_loja,
                wall=wall
            )

            if valor_com_desconto is not None:
                # Define se é desconto, encargos ou normal (igual ao PHP)
                mensagem_para_cliente = sem_desconto
                if valor_com_desconto < valor_original:
                    mensagem_para_cliente = com_desconto
                elif valor_com_desconto > valor_original:
                    mensagem_para_cliente = com_encargos

                # Adicionado em 18/08/2025 (igual ao PHP)
                if mensagem_para_cliente == sem_desconto:
                    mensagem_para_cliente = ""

                # Calcular cashback usando CalculadoraDesconto com wall='C'
                valor_cashback = Decimal('0')
                if wall.upper() == 'S':
                    from parametros_wallclub.services import CalculadoraDesconto
                    calculadora_cashback = CalculadoraDesconto()

                    try:
                        # Cashback calculado sobre valor COM DESCONTO usando id_loja já resolvido
                        valor_com_cashback = calculadora_cashback.calcular_desconto(
                            valor_original=valor_com_desconto,
                            data=datetime.now().strftime('%Y-%m-%d'),
                            forma='PIX',
                            parcelas=0,
                            id_loja=id_loja,
                            wall='C'
                        )
                        valor_cashback = valor_com_desconto - valor_com_cashback if valor_com_cashback else 0
                    except Exception as e:
                        registrar_log('posp2', f'Erro ao calcular cashback: {str(e)}', nivel='ERROR')
                        valor_cashback = Decimal('0')

                # Calcular percentual de cashback
                percentual_cashback = (valor_cashback / valor_com_desconto * 100) if valor_com_desconto > 0 else 0

                parcelas_resultado["PIX"] = {
                    "num_parcelas": 1,
                    "valor_total": f"{valor_com_desconto:.2f}",
                    "valor_parcela": f"{valor_com_desconto:.2f}",
                    "descricao": f"PIX: R$ {valor_com_desconto:.2f}".replace('.', ','),
                    "forma_pagamento": "CASH",
                    "mensagem_para_cliente": mensagem_para_cliente,
                    "valor_cashback": f"{valor_cashback:.2f}",
                    "percentual_cashback": f"{percentual_cashback:.2f}"
                }
                registrar_log('posp2', f'posp2.simular_parcelas - Resultado PIX: Total={valor_com_desconto}, Cashback={valor_cashback}')

            # 2. SIMULAR DÉBITO (igual ao PHP)
            registrar_log('posp2', 'posp2.simular_parcelas - Simulando DÉBITO')
            valor_com_desconto = calculadora.calcular_desconto(
                valor_original=valor_original,
                data=data,
                forma='DEBITO',
                parcelas=0,
                id_loja=id_loja,
                wall=wall
            )

            if valor_com_desconto is not None:
                # Define se é desconto, encargos ou normal (igual ao PHP)
                mensagem_para_cliente = sem_desconto
                if valor_com_desconto < valor_original:
                    mensagem_para_cliente = com_desconto
                elif valor_com_desconto > valor_original:
                    mensagem_para_cliente = com_encargos

                # Adicionado em 18/08/2025 (igual ao PHP)
                if mensagem_para_cliente == sem_desconto:
                    mensagem_para_cliente = ""

                # Calcular cashback usando CalculadoraDesconto com wall='C'
                valor_cashback = Decimal('0')
                if wall.upper() == 'S':
                    from parametros_wallclub.services import CalculadoraDesconto
                    calculadora_cashback = CalculadoraDesconto()

                    try:
                        # Cashback calculado sobre valor COM DESCONTO usando id_loja já resolvido
                        valor_com_cashback = calculadora_cashback.calcular_desconto(
                            valor_original=valor_com_desconto,
                            data=datetime.now().strftime('%Y-%m-%d'),
                            forma='DEBITO',
                            parcelas=0,
                            id_loja=id_loja,
                            wall='C'
                        )
                        valor_cashback = valor_com_desconto - valor_com_cashback if valor_com_cashback else 0
                    except Exception as e:
                        registrar_log('posp2', f'Erro ao calcular cashback: {str(e)}', nivel='ERROR')
                        valor_cashback = Decimal('0')

                # Calcular percentual de cashback
                percentual_cashback = (valor_cashback / valor_com_desconto * 100) if valor_com_desconto > 0 else 0

                parcelas_resultado["DEBITO"] = {
                    "num_parcelas": 1,
                    "valor_total": f"{valor_com_desconto:.2f}",
                    "valor_parcela": f"{valor_com_desconto:.2f}",
                    "descricao": f"Débito: R$ {valor_com_desconto:.2f}".replace('.', ','),
                    "forma_pagamento": "DEBIT",
                    "mensagem_para_cliente": mensagem_para_cliente,
                    "valor_cashback": f"{valor_cashback:.2f}",
                    "percentual_cashback": f"{percentual_cashback:.2f}"
                }
                registrar_log('posp2', f'posp2.simular_parcelas - Resultado DÉBITO: Total={valor_com_desconto}, Cashback={valor_cashback}')

            # 3. SIMULAR CRÉDITO 1x até 12x (igual ao PHP)
            for parcelas in range(1, 13):
                # Definir o tipo de forma de pagamento com base no número de parcelas (igual ao PHP)
                if parcelas == 1:
                    formap = "CREDIT_ONE_INSTALLMENT"
                    formapx = "A VISTA"
                else:
                    formap = "CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST"
                    formapx = "PARCELADO SEM JUROS"

                registrar_log('posp2', f'posp2.simular_parcelas - Simulando parcela {parcelas} com forma {formapx}')

                valor_com_desconto = calculadora.calcular_desconto(
                    valor_original=valor_original,
                    data=data,
                    forma=formapx,
                    parcelas=parcelas,
                    id_loja=id_loja,
                    wall=wall
                )

                if valor_com_desconto is not None:
                    # Calcular o valor da parcela (igual ao PHP)
                    valor_parcela = valor_com_desconto / parcelas

                    # Define se é desconto, encargos ou normal (igual ao PHP)
                    mensagem_para_cliente = sem_desconto
                    if valor_com_desconto < valor_original:
                        mensagem_para_cliente = com_desconto
                    elif valor_com_desconto > valor_original:
                        mensagem_para_cliente = com_encargos

                    # Calcular cashback usando CalculadoraDesconto com wall='C'
                    valor_cashback = Decimal('0')
                    if wall.upper() == 'S':
                        from parametros_wallclub.services import CalculadoraDesconto
                        calculadora_cashback = CalculadoraDesconto()

                        try:
                            # Cashback calculado sobre valor COM DESCONTO usando id_loja já resolvido
                            valor_com_cashback = calculadora_cashback.calcular_desconto(
                                valor_original=valor_com_desconto,
                                data=datetime.now().strftime('%Y-%m-%d'),
                                forma=formapx,
                                parcelas=parcelas,
                                id_loja=id_loja,
                                wall='C'
                            )
                            valor_cashback = valor_com_desconto - valor_com_cashback if valor_com_cashback else 0
                        except Exception as e:
                            registrar_log('posp2', f'Erro ao calcular cashback: {str(e)}', nivel='ERROR')
                            valor_cashback = 0.0

                    # Calcular percentual de cashback
                    percentual_cashback = (valor_cashback / valor_com_desconto * 100) if valor_com_desconto > 0 else 0

                    parcelas_resultado[parcelas] = {
                        "num_parcelas": parcelas,
                        "valor_total": f"{valor_com_desconto:.2f}",
                        "valor_parcela": f"{valor_parcela:.2f}",
                        "descricao": (f"À vista: R$ {valor_com_desconto:.2f}".replace('.', ',')
                                    if parcelas == 1
                                    else f"{parcelas}x de R$ {valor_parcela:.2f}".replace('.', ',')),
                        "forma_pagamento": formap,
                        "mensagem_para_cliente": mensagem_para_cliente,
                        "valor_cashback": f"{valor_cashback:.2f}",
                        "percentual_cashback": f"{percentual_cashback:.2f}"
                    }

                    registrar_log('posp2', f'posp2.simular_parcelas - Resultado parcela {parcelas}: Total={valor_com_desconto}, Parcela={valor_parcela}, Cashback={valor_cashback}')

            registrar_log('posp2', f'posp2.simular_parcelas - Simulação concluída - {len(parcelas_resultado)} opções geradas')

            resposta_json = {
                'sucesso': True,
                'mensagem': 'Simulação realizada com sucesso',
                'dados': {
                    'parcelas': parcelas_resultado,
                    'cards_principais': [3, 6, 10, 12]
                }
            }

            registrar_log('posp2', f'posp2.simular_parcelas - JSON de resposta: {resposta_json}')

            return resposta_json

        except Exception as e:
            registrar_log('posp2', f'Erro ao simular parcelas: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno na simulação',
                'dados': {
                    'parcelas': {}
                }
            }

    def calcular_desconto_parcela(self, valoro: float, forma: str,
                                 parcelas: int, terminal: str, wall: str = 's') -> Dict[str, Any]:
        """
        Calcula desconto para forma de pagamento e parcelas específicas
        Wrapper que delega para parametros_wallclub.CalculadoraDesconto
        Formato padronizado da API POSP2
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.calcular_desconto')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.calcular_desconto - Calculando desconto - Terminal: {terminal}, Valor: {valoro}, Forma: {forma}, Parcelas: {parcelas}, Wall: {wall}')

            # Validar parâmetros (igual ao PHP)
            if not terminal or valoro <= 0 or not forma:
                registrar_log('posp2', 'posp2.calcular_desconto - ERRO: Parâmetros inválidos', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Parâmetros inválidos. Terminal, valor e forma são obrigatórios e valor deve ser maior que zero.',
                    'dados': {
                        'parcelas': {}
                    }
                }

            # Buscar dados do terminal (já valida existência e associação com loja)
            dados_terminal = self.obter_dados_terminal(terminal)
            if not dados_terminal or 'loja_id' not in dados_terminal:
                registrar_log('posp2', f'posp2.calcular_desconto - Terminal não encontrado ou não associado a loja: {terminal}')
                return {
                    'sucesso': False,
                    'mensagem': 'Terminal não encontrado ou não vinculado a uma loja',
                    'dados': {
                        'parcelas': {}
                    }
                }

            id_loja = dados_terminal['loja_id']

            # Validar forma de pagamento (igual ao PHP)
            if forma not in ['CASH', 'DEBIT', 'CREDIT_ONE_INSTALLMENT', 'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST']:
                registrar_log('posp2', f'posp2.calcular_desconto - Forma de pagamento inválida: {forma}')
                return {
                    'sucesso': False,
                    'mensagem': 'Forma de pagamento inválida. Use CASH, DEBIT, CREDIT_ONE_INSTALLMENT ou CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST',
                    'dados': {
                        'parcelas': {}
                    }
                }

            # Definir nomenclatura de retorno (igual ao PHP)
            sem_desconto = ""
            com_desconto = "(c/desconto)"
            com_encargos = ""

            # Converter valor para Decimal com precisão exata
            valor_original = Decimal(str(valoro)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Validar forma de pagamento e ajustar parâmetros (igual ao PHP)
            if forma == "CASH":
                parcelas = 0  # CASH (PIX) não tem parcelamento
                formapx = "PIX"  # Nome usado internamente na calculadora
            elif forma == "DEBIT":
                parcelas = 0  # DEBIT não tem parcelamento
                formapx = "DEBITO"  # Nome usado internamente na calculadora
            elif forma == "CREDIT_ONE_INSTALLMENT":
                parcelas = 1  # Crédito à vista
                formapx = "A VISTA"  # Nome usado internamente na calculadora
            elif forma == "CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST":
                # Parcelas já definidas pelo parâmetro
                formapx = "PARCELADO SEM JUROS"  # Nome usado internamente na calculadora

            registrar_log('posp2', f'posp2.calcular_desconto - Forma de pagamento: {forma} (interno: {formapx}) com {parcelas} parcela(s)')

            # Log dos valores recebidos na função
            registrar_log('posp2', f'[DEBUG] posp2.calcular_desconto - Valores recebidos: valoro={valoro}, forma={forma}, parcelas_original={parcelas}, terminal={terminal}, wall={wall}')
            registrar_log('posp2', f'[DEBUG] posp2.calcular_desconto - Dados do terminal: {dados_terminal}')
            registrar_log('posp2', f'[DEBUG] posp2.calcular_desconto - Valores processados: valor_original={valor_original}, formapx={formapx}, parcelas_ajustadas={parcelas}, id_loja={id_loja}')

            # Log dos parâmetros de entrada
            registrar_log('posp2', f'[DEBUG]posp2.calcular_desconto - Parâmetros de entrada: valor_original={valor_original}, data_atual={datetime.now().strftime("%Y-%m-%d")}, forma={formapx}, parcelas={parcelas}, id_loja={id_loja}, wall={wall}')

            # Usar calculadora do parametros_wallclub
            from parametros_wallclub.services import CalculadoraDesconto
            calculadora = CalculadoraDesconto()

            # Calcular o valor com desconto (usando data atual em runtime)
            data_atual = datetime.now().strftime('%Y-%m-%d')

            valor_com_desconto = calculadora.calcular_desconto(
                valor_original=valor_original,
                data=data_atual,
                forma=formapx,
                parcelas=parcelas,
                id_loja=id_loja,
                wall=wall
            )

            registrar_log('posp2', f'posp2.calcular_desconto - Valores: original={valor_original}, calculado={valor_com_desconto}')

            # Se calculadora retornou None, usar valor original
            if valor_com_desconto is None:
                valor_com_desconto = valor_original
                registrar_log('posp2', 'posp2.calcular_desconto - Calculadora retornou None - usando valor original')

            # Calcular o valor da parcela (se aplicável)
            valor_parcela = valor_com_desconto
            if parcelas > 0:
                valor_parcela = valor_com_desconto / parcelas
            valor_parcela = Decimal(str(valor_parcela)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            # Define se é desconto, encargos ou normal (igual ao PHP)
            mensagem_para_cliente = sem_desconto
            if valor_com_desconto < valor_original:
                mensagem_para_cliente = com_desconto
            elif valor_com_desconto > valor_original:
                mensagem_para_cliente = com_encargos

            if mensagem_para_cliente == sem_desconto and (forma == "CASH" or forma == "DEBIT"):
                mensagem_para_cliente = ""

            # Definir a chave para o array de resultados (igual ao PHP)
            chave = parcelas
            if forma == "CASH":
                chave = "PIX"
            elif forma == "DEBIT":
                chave = "DEBITO"

            # Definir a descrição formatada (igual ao PHP)
            if forma == "CASH":
                descricao = f"PIX: R$ {valor_com_desconto:.2f}".replace('.', ',')
            elif forma == "DEBIT":
                descricao = f"Débito: R$ {valor_com_desconto:.2f}".replace('.', ',')
            elif parcelas == 1:
                descricao = f"À vista: R$ {valor_com_desconto:.2f}".replace('.', ',')
            else:
                descricao = f"{parcelas}x de R$ {valor_parcela:.2f}".replace('.', ',')

            # Calcular cashback usando CalculadoraDesconto com wall='C'
            valor_cashback = Decimal('0')
            if wall.upper() == 'S':
                from parametros_wallclub.services import CalculadoraDesconto
                calculadora_cashback = CalculadoraDesconto()

                try:
                    dados_terminal_cashback = self.obter_dados_terminal(terminal)
                    id_loja = dados_terminal_cashback.get('loja_id', 1) if dados_terminal_cashback else 1

                    registrar_log('posp2', f'[CASHBACK] Calculando cashback - id_loja={id_loja}, forma={formapx}, parcelas={parcelas}, valor_com_desconto={valor_com_desconto}, wall=C')

                    # IMPORTANTE: Cashback calculado sobre valor COM DESCONTO
                    valor_com_cashback = calculadora_cashback.calcular_desconto(
                        valor_original=valor_com_desconto,  # Valor já descontado
                        data=datetime.now().strftime('%Y-%m-%d'),
                        forma=formapx,
                        parcelas=parcelas,
                        id_loja=id_loja,
                        wall='C'
                    )

                    # Log do plano encontrado pela calculadora
                    id_plano_cashback = calculadora_cashback.id_plano_encontrado
                    registrar_log('posp2', f'[CASHBACK] Plano encontrado: id_plano={id_plano_cashback}')
                    registrar_log('posp2', f'[CASHBACK] Resultado: valor_com_desconto={valor_com_desconto}, valor_com_cashback={valor_com_cashback}')

                    if valor_com_cashback is None:
                        registrar_log('posp2', '[CASHBACK] AVISO: valor_com_cashback retornou None - configuração wall=C não encontrada?')
                        valor_cashback = 0
                    else:
                        valor_cashback = valor_com_desconto - valor_com_cashback
                        registrar_log('posp2', f'[CASHBACK] Cashback calculado: {valor_cashback}')
                except Exception as e:
                    registrar_log('posp2', f'Erro ao calcular cashback: {str(e)}', nivel='ERROR')
                    valor_cashback = Decimal('0')

            # Calcular percentual de cashback
            percentual_cashback = (valor_cashback / valor_com_desconto * 100) if valor_com_desconto > 0 else 0

            # Preparar resultado no formato padronizado da API
            parcela_resultado = {
                "num_parcelas": 1 if parcelas == 0 else parcelas,
                "valor_total": f"{valor_com_desconto:.2f}",
                "valor_parcela": f"{valor_parcela:.2f}",
                "descricao": descricao,
                "forma_pagamento": forma,
                "mensagem_para_cliente": mensagem_para_cliente,
                "valor_cashback": f"{valor_cashback:.2f}",
                "percentual_cashback": f"{percentual_cashback:.2f}"
            }

            registrar_log('posp2', f'posp2.calcular_desconto - Resultado do cálculo: {parcela_resultado}')

            return {
                'sucesso': True,
                'mensagem': 'Cálculo realizado com sucesso',
                'dados': {
                    'parcelas': {
                        chave: parcela_resultado
                    }
                }
            }

        except Exception as e:
            registrar_log('posp2', f'Erro ao calcular desconto: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno no cálculo',
                'dados': {
                    'parcelas': {}
                }
            }

    def valida_cpf(self, cpf: str, terminal: str) -> Dict[str, Any]:
        """
        Valida CPF seguindo a lógica complexa do PHP valida_cpf.php
        Replica comportamento completo: consulta cliente, bureau, inserção
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.validar_cpf')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.validar_cpf - INÍCIO valida_cpf - CPF: {cpf}, Terminal: {terminal}')

            # Validação de entrada
            if not cpf or not terminal:
                registrar_log('posp2', 'posp2.validar_cpf - ERRO - Parâmetros obrigatórios não informados', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'erro_sistema',
                    'dados': {
                        'mensagem_cliente': 'Parâmetros obrigatórios não informados'
                    }
                }

            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                registrar_log('posp2', f'posp2.validar_cpf - ERRO - CPF inválido: {cpf}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'erro_sistema',
                    'dados': {
                        'mensagem_cliente': 'CPF inválido'
                    }
                }

            # Validar CPF completo (dígitos verificadores + blacklist)
            validacao_cpf = ValidadorCPFService.validar_cpf_completo(cpf_limpo, usar_cache=True)
            if not validacao_cpf['valido']:
                registrar_log('posp2', f'posp2.validar_cpf - ERRO - {validacao_cpf["motivo"]}: {cpf_limpo[:3]}***{cpf_limpo[-2:]}', nivel='WARNING')
                return {
                    'sucesso': False,
                    'mensagem': 'cpf_bloqueado',
                    'dados': {
                        'mensagem_cliente': validacao_cpf['motivo']
                    }
                }

            # Verificar se terminal existe e obter dados
            dados_terminal = self.obter_dados_terminal(terminal)
            if not dados_terminal or 'canal_id' not in dados_terminal:
                registrar_log('posp2', f'posp2.validar_cpf - ERRO - Terminal não encontrado: {terminal}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'erro_sistema',
                    'dados': {
                        'mensagem_cliente': 'Estabelecimento não encontrado para terminal'
                    }
                }

            canal_id = dados_terminal['canal_id']
            registrar_log('posp2', f'posp2.validar_cpf - VALIDAÇÃO - Terminal: {terminal}, Canal ID: {canal_id}')

            # Lógica de checagem do CPF consolidada

            resultado = {
                'id': '',
                'celular': '',
                'mensagem': '',
                'mensagem_cliente': ''
            }

            # 1. Buscar cliente no cadastro usando API interna
            try:
                from wallclub_core.integracoes.api_interna_service import APIInternaService
                
                # Chamar API interna para buscar cliente
                response = APIInternaService.chamar_api_interna(
                    metodo='POST',
                    endpoint='/api/internal/cliente/consultar_por_cpf/',
                    payload={
                        'cpf': cpf_limpo,
                        'canal_id': canal_id
                    },
                    contexto='apis'
                )
                
                if response.get('sucesso') and response.get('cliente'):
                    cliente_data = response['cliente']
                    resultado['id'] = str(cliente_data.get('id', ''))
                    resultado['celular'] = cliente_data.get('celular', '')
                    tem_firebase_token = bool(cliente_data.get('firebase_token'))
                    
                    registrar_log('posp2', f'posp2.validar_cpf - CONSULTA valida_cpf - CPF encontrado no cadastro, ID: {resultado["id"]}, Celular: {resultado["celular"]}')
                    
                    # 2. Verificar se possui token Firebase
                    if tem_firebase_token:
                        resultado['mensagem'] = 'cpf_cadastrado'
                        resultado['mensagem_cliente'] = 'CPF autorizado'
                        registrar_log('posp2', f'posp2.validar_cpf - SAÍDA valida_cpf - CPF já cadastrado: {cpf_limpo}')

                        return {
                            'sucesso': True,
                            'mensagem': resultado['mensagem'],
                            'dados': {
                                'id': resultado['id'],
                                'celular': resultado['celular'],
                            'mensagem_cliente': resultado['mensagem_cliente']
                        }
                    }
                    
                    # 3. Cliente cadastrado, tem celular, mas sem token firebase (sem app)
                    if resultado['celular'] and not tem_firebase_token:
                        resultado['mensagem'] = 'cpf_cadastrado_sem_app'
                        resultado['mensagem_cliente'] = 'CPF autorizado'
                        registrar_log('posp2', f'posp2.validar_cpf - SAÍDA valida_cpf - Cliente sem app: {cpf_limpo}')

                        return {
                            'sucesso': True,
                            'mensagem': resultado['mensagem'],
                            'dados': {
                                'id': resultado['id'],
                                'celular': resultado['celular'],
                                'mensagem_cliente': resultado['mensagem_cliente']
                            }
                        }
                    
                    # 4. Cliente cadastrado mas sem celular
                    if not resultado['celular']:
                        resultado['mensagem'] = 'cpf_cadastrado_sem_celular'
                        resultado['mensagem_cliente'] = 'CPF autorizado'
                        registrar_log('posp2', f'posp2.validar_cpf - SAÍDA valida_cpf - Cliente sem celular: {cpf_limpo}')

                        return {
                            'sucesso': True,
                            'mensagem': resultado['mensagem'],
                            'dados': {
                                'id': resultado['id'],
                                'celular': '',
                                'mensagem_cliente': resultado['mensagem_cliente']
                            }
                        }
                else:
                    registrar_log('posp2', 'posp2.validar_cpf - CONSULTA valida_cpf - CPF não encontrado no cadastro')
            except Exception as e:
                registrar_log('posp2', f'posp2.validar_cpf - ERRO ao consultar cliente via API: {str(e)}', nivel='ERROR')

            # 5. CPF não existe no cadastro - consultar bureau via API interna
            try:
                # Chamar API interna para cadastrar cliente (já faz bureau + inserção)
                response = APIInternaService.chamar_api_interna(
                    metodo='POST',
                    endpoint='/api/internal/cliente/cadastrar/',
                    payload={
                        'cpf': cpf_limpo,
                        'celular': '',
                        'canal_id': canal_id
                    },
                    contexto='apis'
                )
                
                resultado_cadastro = response if response else {'sucesso': False, 'mensagem': 'Erro ao chamar API'}

                if not resultado_cadastro['sucesso']:
                    if resultado_cadastro.get('codigo') == 0:
                        # Erro do bureau
                        registrar_log('posp2', 'posp2.validar_cpf - ERRO valida_cpf - CPF não autorizado pelo bureau', nivel='ERROR')
                        resultado['mensagem'] = 'erro_bureau'
                        resultado['mensagem_cliente'] = 'CPF não autorizado'
                    elif resultado_cadastro.get('codigo') == 2:
                        # CPF já existe - continua fluxo
                        registrar_log('posp2', f'posp2.validar_cpf - AVISO valida_cpf - CPF já cadastrado: {cpf_limpo}')
                        resultado['mensagem'] = 'cpf_novo_pedir_celular'
                        resultado['mensagem_cliente'] = 'Por favor informar o número do celular'
                    else:
                        # Erro genérico
                        registrar_log('posp2', f'posp2.validar_cpf - ERRO valida_cpf - Erro no cadastro: {resultado_cadastro["mensagem"]}', nivel='ERROR')
                        resultado['mensagem'] = 'erro_sistema'
                        resultado['mensagem_cliente'] = 'Erro no processamento do CPF. Tente novamente mais tarde.'
                else:
                    # Sucesso no cadastro
                    registrar_log('posp2', f'posp2.validar_cpf - INSERÇÃO valida_cpf - Novo cadastro inserido para CPF: {cpf_limpo}')
                    resultado['mensagem'] = 'cpf_novo_pedir_celular'
                    resultado['mensagem_cliente'] = 'Por favor informar o número do celular'

                registrar_log('posp2', f'posp2.validar_cpf - RESPOSTA valida_cpf - CPF: {cpf_limpo}, Terminal: {terminal}, Resultado: {resultado}')

                return {
                    'sucesso': True,
                    'mensagem': resultado['mensagem'],
                    'dados': {
                        'id': resultado['id'],
                        'celular': resultado['celular'],
                        'mensagem_cliente': resultado['mensagem_cliente']
                    }
                }

            except Exception as e:
                registrar_log('posp2', f'posp2.validar_cpf - ERRO EXCEPCIONAL valida_cpf - {str(e)}', nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'erro_sistema',
                    'dados': {
                        'mensagem_cliente': 'Erro no processamento do CPF. Tente novamente mais tarde.'
                    }
                }

        except Exception as e:
            registrar_log('posp2', f'posp2.validar_cpf - ERRO EXCEPCIONAL valida_cpf - {str(e)}')

    def listar_operadores_pos(self, terminal: str) -> Dict[str, Any]:
        """
        Lista operadores POS para um terminal específico
        Busca pelo número do terminal e retorna operadores válidos
        """
        try:

            # Buscar ID do terminal pelo número do terminal
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM terminais WHERE terminal = %s
                """, [terminal])

                terminal_row = cursor.fetchone()
                if not terminal_row:
                    return {
                        'sucesso': False,
                        'mensagem': f'Terminal {terminal} não encontrado',
                        'lista_operadores': []
                    }

                terminal_id = terminal_row[0]

                # Buscar operadores para este terminal_id
                cursor.execute("""
                    SELECT id, operador
                    FROM terminais_operadores_pos
                    WHERE terminal_id = %s AND valido = 1
                    ORDER BY operador
                """, [terminal_id])

                operadores = cursor.fetchall()

                lista_operadores = [
                    {
                        'id': op[0],
                        'operador_pos': op[1]
                    }
                    for op in operadores
                ]

                registrar_log('posp2', f'posp2.operadores - Encontrados {len(lista_operadores)} operadores para terminal {terminal}')

                return {
                    'sucesso': True,
                    'mensagem': f'Operadores encontrados para terminal {terminal}',
                    'lista_operadores': lista_operadores
                }

        except Exception as e:
            registrar_log('posp2', f'posp2.operadores - Erro ao listar operadores: {e}')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao consultar operadores: {str(e)}',
                'lista_operadores': []
            }

    def obter_logo_pos(self, terminal_id: str) -> Dict[str, Any]:
        """
        Retorna logo em base64 para terminal POS
        Migração de logo_pos.php
        """
        try:
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.logo_pos')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.logo_pos - Obtendo logo para terminal: {terminal_id}')

            # Buscar nome do logo na base de dados
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT c.logo_pos
                    FROM   terminais t, loja l, canal c
                    WHERE  t.terminal = %s
                           AND t.loja_id = l.id
                           AND l.canal_id = c.id
                    LIMIT 1
                """, [terminal_id])

                row = cursor.fetchone()
                if not row:
                    registrar_log('posp2', f'posp2.logo_pos - Terminal não encontrado: {terminal_id}')
                    return {
                        'sucesso': False,
                        'mensagem': 'Terminal não encontrado'
                    }

                logo_pos = row[0] if row[0] else 'logo_padrao.png'

            return {
                'sucesso': True,
                'mensagem': 'Logo obtido com sucesso',
                'logo_pos': logo_pos
            }

        except Exception as e:
            registrar_log('posp2', f'posp2.logo_pos - Erro ao obter logo: {str(e)}')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao obter logo'
            }

    def _buscar_id_loja(self, terminal: str) -> Optional[int]:
        """
        Busca ID da loja pelo terminal
        Replica comportamento do PHP que usa terminal como identificador da loja
        """
        try:
            # Buscar dados do terminal que incluem o ID da loja
            dados_terminal = self.obter_dados_terminal(terminal)
            if dados_terminal and 'id_loja' in dados_terminal:
                return int(dados_terminal['id_loja'])

            # Fallback: tentar converter terminal diretamente para ID da loja
            # (comportamento do PHP original onde terminal = id_loja)
            try:
                return int(terminal)
            except ValueError:
                return None

        except Exception as e:
            registrar_log('posp2', f'posp2.validar_cpf - Erro ao buscar ID da loja para terminal {terminal}: {str(e)}')
            return None

    def obter_dados_terminal(self, terminal_id: str) -> Dict[str, Any]:
        """
        Obtém dados completos do terminal
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT  terminais.terminal terminal,
                            terminais.idterminal idterminal,
                            loja.id   loja_id,
                            canal.id  canal_id,
                            loja.razao_social nome_loja,
                            canal.nome nome_canal
                    FROM    wallclub.terminais,
                            wallclub.loja,
                            wallclub.canal
                    WHERE   terminais.terminal = %s
                            AND terminais.loja_id = loja.id
                            AND loja.canal_id = canal.id
                            AND terminais.inicio <= NOW()
                            AND (terminais.fim >= NOW() or terminais.fim is null or terminais.fim = 0)
                    LIMIT 1
                """, [terminal_id])

                row = cursor.fetchone()
                if row:
                    return {
                        'terminal': row[0],
                        'idterminal': row[1],
                        'loja_id': row[2],
                        'canal_id': row[3],
                        'nome_loja': row[4],
                        'nome_canal': row[5]
                    }
                else:
                    return {}

        except Exception as e:
            registrar_log('posp2', f'Erro ao obter dados terminal: {str(e)}', nivel='ERROR')
            return {}

    def processar_cashback_pos(self, cpf: str, canal_id: int, nsu_transacao: str,
                              resultado_calculo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa crédito de cashback após transação POS aprovada

        Args:
            cpf: CPF do cliente
            canal_id: ID do canal
            nsu_transacao: NSU da transação
            resultado_calculo: Resultado do calcular_cashback()

        Returns:
            Dict com sucesso/mensagem
        """
        try:
            from apps.conta_digital.services import ContaDigitalService
            from wallclub_core.integracoes.api_interna_service import APIInternaService

            if not resultado_calculo.get('sucesso'):
                return {
                    'sucesso': False,
                    'mensagem': 'Cálculo de cashback falhou'
                }

            valor_cashback = resultado_calculo.get('valor_cashback', 0)

            if valor_cashback <= 0:
                return {
                    'sucesso': True,
                    'mensagem': 'Sem cashback a creditar'
                }

            # Buscar cliente_id via API interna
            resultado_cliente = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/cliente/obter_cliente_id/',
                payload={'cpf': cpf, 'canal_id': canal_id},
                contexto='apis'
            )
            if not resultado_cliente.get('sucesso'):
                registrar_log('posp2.cashback', f'Cliente não encontrado: {cpf[:3]}***')
                return {
                    'sucesso': False,
                    'mensagem': 'Cliente não encontrado'
                }

            cliente_id = resultado_cliente['cliente_id']

            # Creditar cashback
            descricao = f"{resultado_calculo.get('forma', 'COMPRA')} {resultado_calculo.get('parcelas', 1)}x"
            resultado_credito = ContaDigitalService.creditar_cashback_transacao_pos(
                cliente_id=cliente_id,
                canal_id=canal_id,
                valor_cashback=Decimal(str(valor_cashback)),
                nsu_transacao=nsu_transacao,
                descricao=descricao,
                data_liberacao=None  # Por enquanto, liberar imediatamente
            )

            if resultado_credito['sucesso']:
                registrar_log('posp2.cashback',
                            f'Cashback creditado: NSU {nsu_transacao}, '
                            f'Cliente {cpf[:3]}***, Valor R$ {valor_cashback:.2f}')
            else:
                registrar_log('posp2.cashback',
                            f'Erro ao creditar cashback: {resultado_credito["mensagem"]}')

            return resultado_credito

        except Exception as e:
            registrar_log('posp2.cashback', f'Erro ao processar cashback: {str(e)}')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao processar cashback: {str(e)}'
            }

    def atualiza_celular_envia_msg_app(self, cpf: str, terminal: str, celular: str) -> Dict[str, Any]:
        """
        Atualiza celular do cliente e envia mensagem para baixar o app com nova senha.

        Args:
            cpf (str): CPF do cliente
            terminal (str): Terminal para buscar o canal_id
            celular (str): Número do celular para atualizar

        Returns:
            Dict[str, Any]: Resultado da operação com sucesso/mensagem
        """
        try:
            from wallclub_core.integracoes.api_interna_service import APIInternaService
            
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} posp2.atualiza_celular_envia_msg_app')
            registrar_log('posp2', '========================================')
            registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Iniciando processo - CPF: {cpf[:3]}***, Terminal: {terminal}, Celular: {celular}')

            # Buscar canal_id a partir do terminal
            dados_terminal = self.obter_dados_terminal(terminal)
            if not dados_terminal or 'canal_id' not in dados_terminal:
                registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Terminal não encontrado ou sem canal_id: {terminal}')
                return {
                    "sucesso": False,
                    "mensagem": "Terminal não encontrado ou inválido"
                }

            canal_id = dados_terminal['canal_id']
            registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Canal_id obtido do terminal: {canal_id}')

            # a. Obter cliente_id via API interna
            resultado_cliente = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/cliente/obter_cliente_id/',
                payload={'cpf': cpf, 'canal_id': canal_id},
                contexto='apis'
            )
            if not resultado_cliente.get("sucesso", False):
                registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Falha ao obter cliente_id: {resultado_cliente.get("mensagem", "")}')
                return resultado_cliente

            cliente_id = resultado_cliente.get("cliente_id")
            registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Cliente_id obtido: {cliente_id}')

            # b. Atualizar celular do cliente via API interna
            resultado_atualizacao = APIInternaService.chamar_api_interna(
                metodo='POST',
                endpoint='/api/internal/cliente/atualizar_celular/',
                payload={'cliente_id': cliente_id, 'celular': celular},
                contexto='apis'
            )
            if not resultado_atualizacao.get("sucesso", False):
                registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Falha ao atualizar celular: {resultado_atualizacao.get("mensagem", "")}')
                return resultado_atualizacao

            registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Celular atualizado com sucesso')

            # c. Enviar mensagem para baixar app
            enviar_baixar_ok = False
            try:
                if celular and celular.strip():
                    registrar_log('posp2', f'[DEBUG] Tentando preparar template baixar_app para canal_id={canal_id}')
                    tpl = MessagesTemplateService.preparar_whatsapp(
                        canal_id=canal_id,
                        id_template='baixar_app'
                    )
                    registrar_log('posp2', f'[DEBUG] Template preparado: {tpl}')
                    
                    if tpl:
                        registrar_log('posp2', f'[DEBUG] Enviando WhatsApp baixar_app - Template: {tpl["nome_template"]}, Idioma: {tpl["idioma"]}, Corpo: {tpl["parametros_corpo"]}, Botao: {tpl["parametros_botao"]}')
                        resultado_whatsapp = WhatsAppService.envia_whatsapp(
                            numero_telefone=celular,
                            canal_id=canal_id,
                            nome_template=tpl['nome_template'],
                            idioma_template=tpl['idioma'],
                            parametros_corpo=tpl['parametros_corpo'],
                            parametros_botao=tpl['parametros_botao']
                        )
                        registrar_log('posp2', f'[DEBUG] Resultado envio WhatsApp baixar_app: {resultado_whatsapp}')
                        enviar_baixar_ok = resultado_whatsapp
                    else:
                        registrar_log('posp2', '[WARNING] Template baixar_app retornou None - template não encontrado no banco', nivel='WARNING')
                    # Enviar também SMS, se existir template
                    try:
                        tpl_sms = MessagesTemplateService.preparar_sms(
                            canal_id=canal_id,
                            id_template='baixar_app'
                        )
                        if tpl_sms:
                            enviar_sms(
                                telefone=celular,
                                mensagem=tpl_sms['mensagem'],
                                assunto=tpl_sms.get('assunto', 'WallClub')
                            )
                    except Exception as e_sms:
                        registrar_log('posp2', f"[POS] Falha SMS baixar_app: {str(e_sms)}", nivel='WARNING')
                registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - baixar_app enviado={enviar_baixar_ok}')
            except Exception as e:
                registrar_log('posp2', f'posp2.atualiza_celular_envia_msg_app - Falha ao enviar baixar_app: {str(e)}', nivel='WARNING')

            # Resposta final
            if enviar_baixar_ok:
                return {
                    "sucesso": True,
                    "mensagem": "Celular atualizado e mensagem de download do app enviada"
                }
            else:
                return {
                    "sucesso": False,
                    "mensagem": "Celular atualizado, mas falha ao enviar mensagens"
                }

        except Exception as e:
            registrar_log('posp2', f'Erro no processo atualiza_celular_envia_msg_app: {str(e)}', nivel='ERROR')
            return {
                "sucesso": False,
                "mensagem": f"Erro interno: {str(e)}"
            }

