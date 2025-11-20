"""
Calculadora de Base de Gestão - Credenciadora
"""

# import logging - removido, usando registrar_log
import decimal
from datetime import datetime as dt, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any
from pinbank.services import PinbankService
from parametros_wallclub.services import ParametrosService
from wallclub_core.utilitarios.funcoes_gerais import proxima_sexta_feira
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log, log_esta_habilitado
from wallclub_core.database.queries import TransacoesQueries
from gestao_financeira.models import BaseTransacoesGestao

# logger removido - usando registrar_log


class CalculadoraBaseCredenciadora:
    """
    Calculadora de valores primários para base de gestão
    Migração fiel da função mainCalculaValoresPrimarios() do PHP
    """

    def __init__(self):
        self.parametros_service = ParametrosService()
        self.pinbank_service = PinbankService()

    def _to_decimal(self, value, casas=2) -> Decimal:
        """Converte qualquer valor para Decimal com precisão especificada"""
        if value is None:
            return Decimal('0')
        if isinstance(value, Decimal):
            return value.quantize(Decimal(f'0.{"0" * casas}'), rounding=ROUND_HALF_UP)
        return Decimal(str(value)).quantize(Decimal(f'0.{"0" * casas}'), rounding=ROUND_HALF_UP)

    def calcular_valores_primarios(self, dados_linha):
        """
        Calcula os valores primários baseados nos dados da linha.
        Replica a lógica do PHP pinbank_cria_base_gestao.php
        """
        from datetime import datetime as dt, timedelta
        try:
            registrar_log('parametros_wallclub.calculadora_base_gestao', f"Iniciando cálculo para NSU: {dados_linha.get('NsuOperacao', 'N/A')}")
            valores = {}

            # Validar se a operação é Club (Wall S) ou Normal (Wall N)
            cpf = dados_linha.get('cpf', '') or ''
            if cpf and len(cpf) > 0:
                wall = 's'
                valores[130] = "Club"
            else:
                wall = 'n'
                valores[130] = "Normal"

            # Capturar informações da Loja, canal e plano
            nsu_operacao = dados_linha['NsuOperacao']

            # Usar info_loja de dados_linha se já existir (Credenciadora/Checkout), senão buscar (Wallet)
            if 'info_loja' in dados_linha:
                info_loja = dados_linha['info_loja']
            else:
                info_loja = self.pinbank_service.pega_info_loja(nsu_operacao)

            # Usar info_canal de dados_linha se já existir (Credenciadora/Checkout), senão buscar (Wallet)
            if 'info_canal' in dados_linha:
                info_canal = dados_linha['info_canal']
            else:
                info_canal = self.pinbank_service.pega_info_canal(nsu_operacao)
            id_plano = self.parametros_service.busca_plano(
                dados_linha['TipoCompra'],
                dados_linha['NumeroTotalParcelas'],
                dados_linha['Bandeira'],
                wall
            )

            # Data de referência dos cálculos
            data_ref = self.parametros_service.converter_para_timestamp(dados_linha['DataTransacao'])
            if data_ref is None:
                raise ValueError(f"Erro ao converter DataTransacao para timestamp: {dados_linha['DataTransacao']}")

            # Estabelecer valores básicos
            valores['id_fila_extrato'] = dados_linha['id']  # ID da fila de extrato
            valores['canal_id'] = info_canal['id']
            valores[0] = dt.fromtimestamp(data_ref).strftime('%d/%m/%Y')
            valores[1] = dt.fromtimestamp(data_ref).strftime('%H:%M:%S')
            valores[2] = dados_linha['SerialNumber']
            valores[3] = dados_linha['idTerminal']
            valores[4] = info_canal['nome']  # Nome do canal (ex: WALL 1)
            valores[5] = info_loja['loja']
            valores[6] = info_loja['id']  # id_loja
            valores[7] = dados_linha['cpf']
            valores[8] = dados_linha['TipoCompra']
            valores[9] = dados_linha['NsuOperacao']
            valores[10] = dados_linha['nsuAcquirer']
            valor_original = dados_linha['valor_original']
            if valor_original is None or valor_original == 0:
                valor_original = dados_linha['ValorBruto']  # usar ValorBruto como fallback
            valores[11] = self._to_decimal(valor_original, 2)
            valores[12] = dados_linha['Bandeira']
            valores[13] = dados_linha['NumeroTotalParcelas']

            # Variáveis secundárias que vem do Pinbank
            # var89 - Parâmetro wall 1 (CORRIGIDO - antes usava ValorTaxaAdm incorretamente)
            param_wall_1 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 1, wall)
            if param_wall_1 is None:
                param_wall_1 = 0
            valores[89] = self._format_decimal(self._to_decimal(param_wall_1, 4), 4)

            # var92 será calculada mais tarde (cópia de var91 após var91 ser definida)
            valores[68] = dados_linha['DescricaoStatus']
            try:
                valores[67] = self._format_decimal(self._to_decimal(dados_linha['ValorSplit'], 2), 2)
            except Exception as e:
                raise ValueError(f"Erro ao calcular valores[67] com ValorSplit={dados_linha['ValorSplit']}: {e}")
            # Variável 97 - DataFuturaPagamento mantém formato ISO original (igual ao PHP)
            data_futura = dados_linha['DataFuturaPagamento']
            if data_futura and str(data_futura) != 'None':
                valores[97] = str(data_futura)
            else:
                valores[97] = None
            # Variável 124 - Valor bruto por parcela (PHP: ValorBrutoParcela direto)
            valores[124] = self._to_decimal(dados_linha['ValorBrutoParcela'], 2)
            # Variável 69 - Status de Recebimento (tratar None)
            descricao_status = dados_linha.get('DescricaoStatusPagamento')
            if descricao_status is None or descricao_status == '':
                # Se não tem status, verificar se tem IdStatusPagamento para inferir
                id_status_pag = dados_linha.get('IdStatusPagamento')
                if id_status_pag == 1:
                    valores[69] = "Pendente"
                elif id_status_pag == 2:
                    valores[69] = "Pago"
                else:
                    valores[69] = "Pendente"  # Default para pendente
            else:
                valores[69] = descricao_status

            # Variável 70 - DataCancelamento (CORRIGIDO - adicionar validação e conversão)
            descricao_status_transacao = dados_linha.get('DescricaoStatus')
            if descricao_status_transacao == 'TRANS. CANCELADA POSTERIOR':
                data_cancelamento = dados_linha.get('DataCancelamento')
                if data_cancelamento and str(data_cancelamento) not in ['None', '0001-01-01T00:00:00']:
                    # Converter de ISO para DD/MM/YYYY
                    try:
                        if isinstance(data_cancelamento, str):
                            # Verificar se não é a data padrão inválida
                            if data_cancelamento.startswith('0001-01-01'):
                                valores[70] = ''
                            else:
                                data_obj = dt.strptime(data_cancelamento[:10], '%Y-%m-%d')
                                valores[70] = data_obj.strftime('%d/%m/%Y')
                        else:
                            valores[70] = data_cancelamento.strftime('%d/%m/%Y')
                    except:
                        valores[70] = ''
                else:
                    valores[70] = ''
            else:
                valores[70] = ''

            # Variável 14 - Percentual de desconto
            if valores[130] == "Normal":
                valores[14] = self._format_decimal(0, 4)
            else:
                param_7 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 7, wall)
                if param_7 is None:
                    valores[14] = None  # Retornar None como no PHP
                else:
                    valores[14] = self._format_decimal(self._to_decimal(param_7, 4), 4)

            # Variável 83 - Cópia da 14
            if valores[14] is None:
                valores[83] = None
            else:
                valores[83] = self._format_decimal(valores[14], 4)

            # Variável 15 - Valor do desconto (PHP: var11 * var14 / 100)
            if valores[14] is None:
                valores[15] = None
            else:
                valores[15] = self._format_decimal(valores[11] * valores[14] / 100, 2)

            # Variável 84 - Cópia da 15
            valores[84] = valores[15]

            # Variável 29 - Parâmetro 1 (arredondado para 0 casas decimais como no PHP)
            param_1 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 1, wall)
            if param_1 is None:
                param_1 = 0
            valores[29] = self._format_decimal(self._to_decimal(param_1, 0), 0)

            # Variável 16 - Valor líquido
            if dados_linha['TipoCompra'] == "DEBITO":
                valores[16] = self._format_decimal(valores[11], 2)
            else:
                diferenca = valores[13] - valores[29]
                if diferenca > 0:
                    valores[16] = self._format_decimal(valores[11], 2)
                else:
                    if valores[14] is None:
                        valores[16] = None
                    else:
                        valores[16] = self._format_decimal(valores[11] * (1 - valores[14]), 2)

            # Variável 81 - Cópia da 16
            valores[81] = valores[16]

            # Variável 17 - Percentual parâmetro 10
            # Sempre buscar o parâmetro_loja_10, independente de ser Normal ou não
            param_10 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 10, wall)
            if param_10 is None:
                param_10 = 0
            self._validar_parametro(param_10, "param_10", f"loja {info_loja['id']}, plano {id_plano}")
            valores[17] = self._format_decimal(self._to_decimal(param_10, 4), 4)

            # Variável 85 - Cópia da 17
            valores[85] = self._format_decimal(valores[17], 4)

            # Variável 18 - Valor da comissão
            valores[18] = self._format_decimal(valores[11] * valores[17], 2)

            # Variável 86 - Cópia da 18
            valores[86] = valores[18]

            # Variável 19 - Valor final
            if dados_linha['TipoCompra'] == "DEBITO":
                valores[19] = self._format_decimal(valores[11], 2)
            else:
                if valores[12] == "PIX":
                    valores[19] = valores[16]
                else:
                    diferenca = valores[13] - valores[29]
                    if diferenca > 0:
                        if valores[14] is None:
                            valores[19] = None
                        else:
                            valores[19] = self._format_decimal(valores[11] * (1 - valores[14]), 2)
                    else:
                        valores[19] = self._format_decimal(valores[11] * (1 - valores[17]), 2)

            # Variável 20 - Valor da parcela
            if valores[19] is None or valores[13] == 0:
                valores[20] = None
            else:
                valores[20] = self._format_decimal(valores[19] / valores[13], 2)

            # Ajuste para Club com parcelas
            if valores[130] == "Club" and valores[13] > 0 and valores[19] is not None:
                # Calcular valor da parcela sem arredondar primeiro
                valor_parcela_exato = valores[19] / valores[13]
                valores[20] = self._format_decimal(valor_parcela_exato, 2)
                # Manter var19 original para evitar duplo arredondamento
                # valores[19] = self._format_decimal(valores[20] * valores[13], 2)

            # Variável 23 - Valor PIX
            valores[23] = self._format_decimal(valores[16], 2)

            # Variável 24 - Parâmetro 14
            param_14 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 14, wall)
            if param_14 is None:
                param_14 = 0
            self._validar_parametro(param_14, "param_14", f"loja {info_loja['id']}, plano {id_plano}")
            valores[24] = self._format_decimal(self._to_decimal(param_14, 4), 4)

            # Variável 25 - Multiplicar por percentual
            if valores[19] is None:
                valores[25] = None
            else:
                valores[25] = self._format_decimal(valores[19] * valores[24], 2)

            # Variável 26 - PIX vs outros
            if valores[12] == "PIX":
                valores[26] = self._format_decimal(valores[23], 2)
            else:
                if valores[19] is None:
                    valores[26] = None
                else:
                    valores[26] = self._format_decimal(valores[19], 2)

            # Variável 82 - Cópia da 26
            valores[82] = valores[26]

            # Variável 28 - Parâmetro 5
            param_5 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 5, wall)
            if param_5 is None:
                param_5 = 0
            self._validar_parametro(param_5, "param_5", f"loja {info_loja['id']}, plano {id_plano}")
            valores[28] = self._format_decimal(self._to_decimal(param_5, 4), 4)

            # Variável 27 - PIX vs outros cálculo (PHP: round sem divisão por 100)
            if valores[12] == "PIX":
                if valores[14] is None:
                    valores[27] = None
                else:
                    valores[27] = self._format_decimal(valores[11] * (1 - valores[14]), 2)
            else:
                valores[27] = self._format_decimal(valores[11] * (1 - valores[28]), 2)

            # Variável 31 - Parâmetro 17
            param_17 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 17, wall)
            if param_17 is None:
                param_17 = 0
            self._validar_parametro(param_17, "param_17", f"loja {info_loja['id']}, plano {id_plano}")
            valores[31] = self._format_decimal(self._to_decimal(param_17, 4), 4)

            # Variável 32 - Valor com taxa 31 aplicada
            if valores[12] == "PIX":
                valores[32] = self._format_decimal(valores[23] * valores[31], 2)
            else:
                valores[32] = self._format_decimal(valores[11] * valores[31], 2)

            # Variável 30 - Diferença entre valor 27 e 32
            if valores[27] is None or valores[32] is None:
                valores[30] = None
            else:
                valores[30] = self._format_decimal(valores[27] - valores[32], 2)

            # Variável 33 - Valor 16 com taxa 31 aplicada
            valores[33] = self._format_decimal(valores[16] * valores[31], 2)

            # Variável 34 - Diferença entre valor 32 e 33
            valores[34] = self._format_decimal(valores[32] - valores[33], 2)

            # Variável 35 - Percentual baseado no valor 11
            if valores[11] > 0:
                valores[35] = self._format_decimal(valores[34] / valores[11], 2)
            else:
                valores[35] = self._format_decimal(0, 2)

            # Variável 36 - ValorTaxaAdm da Pinbank (CORRIGIDO - antes usava param_12)
            # Valor vem em percentual (2.60 = 2.6%), dividir por 100 para obter decimal (0.026)
            valores[36] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaAdm'], 4) / 100, 4)

            # Variável 37 - var19 * var36
            if valores[19] is None:
                valores[37] = None
            else:
                valores[37] = self._format_decimal(valores[19] * valores[36], 2)

            # Variável 38 - var19 - var37
            if valores[19] is None or valores[37] is None:
                valores[38] = None
            else:
                valores[38] = self._format_decimal(valores[19] - valores[37], 2)

            # Variável 39 - ValorTaxaMes da Pinbank (CORRIGIDO - antes usava param_13)
            # Valor vem em percentual (2.60 = 2.6%), dividir por 100 para obter decimal (0.026)
            valores[39] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaMes'], 4) / 100, 4)

            # NOTA: var40, var41, var42 serão calculadas após var44 estar disponível
            # var41 = var19 - var37 - var44 (depende de var44)
            # var40 = var41 / var19 (depende de var41)
            # var42 = soma vRepasse (igual a var44)

            # Variável 46 - Soma dos valores 30 e 33
            if valores[30] is None or valores[33] is None:
                valores[46] = None
            else:
                valores[46] = self._format_decimal(valores[30] + valores[33], 2)

            # Variável 43 - DataFuturaPagamento (converter ISO para DD/MM/YYYY)
            # Formato entrada: 2025-10-25T22:19:47.706
            # Formato saída: 25/10/2025 (10 caracteres - cabe em VARCHAR(20))
            data_futura_pag = dados_linha.get('DataFuturaPagamento')
            if data_futura_pag and str(data_futura_pag) not in ['None', '0001-01-01T00:00:00']:
                try:
                    if isinstance(data_futura_pag, str):
                        # Pegar apenas a parte da data (YYYY-MM-DD)
                        if data_futura_pag.startswith('0001-01-01'):
                            valores[43] = ''
                        else:
                            data_obj = dt.strptime(data_futura_pag[:10], '%Y-%m-%d')
                            valores[43] = data_obj.strftime('%d/%m/%Y')
                    else:
                        valores[43] = data_futura_pag.strftime('%d/%m/%Y')
                except:
                    valores[43] = ''
            else:
                valores[43] = ''

            # Variável 50 - Parâmetro loja 23
            param_23 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 23, wall)
            if param_23 is None:
                param_23 = 0
            valores[50] = self._format_decimal(self._to_decimal(param_23, 4), 4)

            # Variável 49 - var50 * var19
            if valores[19] is None:
                valores[49] = None
            else:
                valores[49] = self._format_decimal(valores[50] * valores[19], 2)

            # Variável 47 - Parâmetro 21
            param_21 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 21, wall)
            if param_21 is None:
                param_21 = 0
            valores[47] = self._format_decimal(self._to_decimal(param_21, 4), 4)

            # Variável 87 - Parâmetro uptal 1
            param_wall_1 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 1, wall)
            if param_wall_1 is None:
                param_wall_1 = 0
            valores[87] = self._format_decimal(self._to_decimal(param_wall_1, 4), 4)

            # Variável 88 - var87 * var19
            if valores[19] is None:
                valores[88] = None
            else:
                valores[88] = self._format_decimal(valores[87] * valores[19], 2)

            # var89 - ValorTaxaAdm da Pinbank (dividir por 100 para converter percentual em decimal)
            valores[89] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaAdm'], 4) / 100, 4)

            # var90 - var89 * var19
            if valores[19] is None:
                valores[90] = None
            else:
                valores[90] = self._format_decimal(valores[89] * valores[19], 2)

            # Variável 91 - Parâmetro uptal 4
            param_wall_4 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 4, wall)
            if param_wall_4 is None:
                param_wall_4 = 0
            valores[91] = self._format_decimal(self._to_decimal(param_wall_4, 4), 4)

            # Variável 92 - ValorTaxaMes da Pinbank (dividir por 100 para converter percentual em decimal)
            valores[92] = self._format_decimal(self._to_decimal(dados_linha['ValorTaxaMes'], 4) / 100, 4)

            # Variável 78 - Cópia da 91
            valores[78] = valores[91]

            # Calcular var44, var41, var40 ANTES de var94 (que usa var40)
            # Variável 44 - Soma de ValorLiquidoRepasse
            vrepasse = self._to_decimal(dados_linha.get('vRepasse') or 0, 2)
            valores[44] = self._format_decimal(vrepasse, 2)

            # Variável 42 - Igual a var44
            valores[42] = valores[44]

            # Variável 41 - var19 - var37 - var44
            if valores[19] is None or valores[37] is None:
                valores[41] = None
            else:
                valores[41] = self._format_decimal(valores[19] - valores[37] - valores[44], 2)

            # Variável 40 - var41 / var19
            if valores[19] is None or valores[19] == 0 or valores[41] is None:
                valores[40] = self._format_decimal(0, 2)
            else:
                valores[40] = self._format_decimal(valores[41] / valores[19], 2)

            # Variável 93 - Array com duas chaves
            valores[93] = {
                "0": self._format_decimal(valores[91] * (1 + valores[13]) / 2, 4),
                "A": self._format_decimal(valores[92] * (1 + valores[13]) / 2, 4)
            }

            # Variável 94 - Array com duas chaves
            if valores[19] is None:
                valores[94] = {
                    "0": None,
                    "A": valores[40]
                }
            else:
                valores[94] = {
                    "0": self._format_decimal(valores[93]["0"] * valores[19], 2),
                    "A": valores[40]
                }

            # Variável 95 - var19 - var90 - var94["A"]
            if valores[19] is None or valores[90] is None or valores[94]["A"] is None:
                valores[95] = None
            else:
                valores[95] = self._format_decimal(valores[19] - valores[90] - valores[94]["A"], 2)

            # Variável 103 - Array com duas chaves (depende de var95)
            valores[103] = {
                "0": self._format_decimal(valores[95] - valores[42], 2)
            }
            valores[103]["A"] = valores[103]["0"]

            # Variável 107 - Array com diferença (depende de var95)
            valores[107] = {"0": self._format_decimal(valores[95] - valores[42], 2)}

            # Variável 80 - Condicional Normal/Club
            if valores[130] == "Normal":
                valores[80] = self._format_decimal(0, 2)
            else:
                if valores[17] == 0:
                    valores[80] = self._format_decimal(0, 2)
                else:
                    valores[80] = self._format_decimal(valores[88] + valores[94]["0"], 2)

            # Variável 73 - Cálculo baseado em Wall e comissão
            if valores[130] == "Normal":
                valores[73] = self._format_decimal(0, 2)
            else:
                if valores[17] == 0:
                    valores[73] = self._format_decimal(0, 2)
                else:
                    valores[73] = self._format_decimal(valores[26] - valores[80] - valores[42], 2)

            # Variável 74 - Parâmetro clientef2 2
            param_clientef2_2 = ParametrosService.retornar_parametro_wall(info_loja['id'], data_ref, id_plano, 2, wall)
            if param_clientef2_2 is None:
                param_clientef2_2 = 0
            valores[74] = self._format_decimal(self._to_decimal(param_clientef2_2, 4), 4)

            # Variável 75 - Produto com parâmetro (PHP: multiplicação direta)
            if valores[19] is None or valores[74] is None:
                valores[75] = None
            else:
                valores[75] = self._format_decimal(valores[19] * valores[74], 2)

            # Variável 77 - Soma dos valores 73 e 75
            if valores[75] is None:
                valores[77] = valores[73]
            else:
                valores[77] = self._format_decimal(valores[73] + valores[75], 2)

            # Variável 22 - Condicional PIX
            if valores[12] == "PIX":
                valores[22] = self._format_decimal(0, 2)
            else:
                valores[22] = self._format_decimal(valores[77], 2)

            # Variável 72 - Percentual baseado em 73 e 11
            if valores[11] > 0:
                valores[72] = self._format_decimal(valores[73] / valores[11], 4)
            else:
                valores[72] = self._format_decimal(0, 4)

            # Variável 76 - Soma dos percentuais 72 e 74
            valores[76] = self._format_decimal(valores[72] + valores[74], 4)

            # Variável 21 - Lógica complexa PIX/Wall/Normal
            if valores[12] == "PIX":
                valores[21] = self._format_decimal(0, 4)
            else:
                if valores[17] == 0:
                    valores[21] = self._format_decimal(0, 4)
                else:
                    if valores[130] == "Normal":
                        valores[21] = self._format_decimal(0, 4)
                    else:
                        valores[21] = self._format_decimal(valores[78], 4)

            # Variável 108 - Parâmetro wall 6 (usa ID da loja, não do canal)
            param_wall_6 = ParametrosService.retornar_parametro_uptal(info_loja['id'], data_ref, id_plano, 6, wall)
            if param_wall_6 is None:
                param_wall_6 = 0
            valores[108] = self._format_decimal(self._to_decimal(param_wall_6, 4), 4)

            # Variável 109 - Array com produto (PHP: valores[109]["0"])
            valores[109] = {"0": self._format_decimal(valores[107]["0"] * valores[108], 2)}

            # Variável 110 - Parâmetro clientef2 2 (igual a 74)
            valores[110] = valores[74]

            # Variável 111 - Array com produto (PHP: valores[111]["0"], valores[111]["A"], valores[111]["B"])
            if valores[26] is not None and valores[110] is not None:
                valores[111] = {"0": self._format_decimal(valores[26] * valores[110], 2)}
            else:
                valores[111] = {"0": self._format_decimal(0, 2)}

            # Variável 111["A"] - Valor do financeiro f111 (se existir)
            f111_value = dados_linha.get('f111')
            if f111_value is not None:
                valores[111]["A"] = self._format_decimal(self._to_decimal(f111_value, 2), 2)
            else:
                valores[111]["A"] = self._format_decimal(0.00, 2)

            # Variável 111["B"] - Diferença entre valores[111]["0"] e valores[111]["A"]
            valores[111]["B"] = self._format_decimal(valores[111]["0"] - valores[111]["A"], 2)

            # Variável 112 - Array com valores (PHP: valores[112]["A"], valores[112]["0"], valores[112]["B"])
            valores[112] = {"A": self._format_decimal(valores[111]["0"], 2)}

            # Variável 112["0"] - Valor do financeiro f112 (se existir)
            f112_value = dados_linha.get('f112')
            if f112_value is not None:
                valores[112]["0"] = self._format_decimal(self._to_decimal(f112_value, 2), 2)
            else:
                valores[112]["0"] = self._format_decimal(0.00, 2)

            # Variável 112["B"] - Soma de valores[111]["A"] + valores[112]["0"]
            valores[112]["B"] = self._format_decimal(valores[111]["A"] + valores[112]["0"], 2)

            # Variável 113 - Array com diferença (PHP: valores[113]["0"] e valores[113]["A"])
            valores[113] = {"0": self._format_decimal(valores[107]["0"] - valores[112]["A"], 2)}

            # Variável 113["A"] - Será definida após valores[107]["A"] estar disponível

            # Variável 114 - Array com diferença final (PHP: valores[114]["0"] e valores[114]["A"])
            valores[114] = {"0": self._format_decimal(valores[113]["0"] - valores[109]["0"], 2)}

            # Variável 114["A"] - Será definida após valores[113]["A"] estar disponível


            # Variável 48 - Parâmetro 20
            param_20 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 20, wall)
            if param_20 is None:
                param_20 = 0
            valores[48] = self._format_decimal(self._to_decimal(param_20, 4), 4)

            # Variável 52 - Parâmetro loja 25
            param_25 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 25, wall)
            if param_25 is None:
                param_25 = 0
            valores[52] = self._format_decimal(self._to_decimal(param_25, 4), 4)

            # Variável 51 - var52 * var19
            if valores[19] is None:
                valores[51] = None
            else:
                valores[51] = self._format_decimal(valores[52] * valores[19], 2)

            # Variável 53 - Parâmetro loja 27
            param_27 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 27, wall)
            if param_27 is None:
                param_27 = 0
            valores[53] = self._format_decimal(self._to_decimal(param_27, 4), 4)

            # Variável 54 - var53 * var19
            if valores[19] is None:
                valores[54] = None
            else:
                valores[54] = self._format_decimal(valores[53] * valores[19], 2)

            # Variável 55 - Soma dos valores 49, 51 e 54
            valores[55] = self._format_decimal(valores[49] + valores[51] + valores[54], 2)

            # Variável 56 - Percentual baseado em 55 e 11
            if valores[11] > 0:
                valores[56] = self._format_decimal(valores[55] / valores[11], 4)
            else:
                valores[56] = self._format_decimal(0, 4)

            # Variável 57 - Condicional para cashback
            if valores[55] == 0:
                valores[57] = "Sem cashback"
            else:
                valores[57] = proxima_sexta_feira(valores[0])

            # Variável 60 - var19 - (param_12 * var19) - (param_14 * var19) + var56
            param_12 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 12, wall)
            if param_12 is None:
                param_12 = 0
            param_14 = ParametrosService.retornar_parametro_loja(info_loja['id'], data_ref, id_plano, 14, wall)
            if param_14 is None:
                param_14 = 0

            if valores[19] is None:
                valores[60] = None
            else:
                valores[60] = self._format_decimal(
                    valores[19] - (self._to_decimal(param_12, 4) * valores[19]) - (self._to_decimal(param_14, 4) * valores[19]) + valores[56],
                    2
                )

            # Variável 61 - var60 - var33
            if valores[60] is None:
                valores[61] = None
            else:
                valores[61] = self._format_decimal(valores[60] - valores[33], 2)

            # Variável 62 - Diferença final
            if valores[30] is None:
                valores[62] = valores[61]
            else:
                valores[62] = self._format_decimal(valores[61] - valores[30], 2)

            # Variável 63 - Percentual baseado em 62 e 11
            if valores[11] > 0:
                valores[63] = self._format_decimal(valores[62] / valores[11], 4)
            else:
                valores[63] = self._format_decimal(0, 4)

            # Variável 64 - Percentual baseado em 62 e 30
            if valores[30] is not None and valores[30] != 0:
                valores[64] = self._format_decimal(valores[62] / valores[30], 4)
            else:
                valores[64] = self._format_decimal(0, 4)

            # Variável 79 - Percentual baseado em 80 e 26
            if valores[26] is not None and valores[26] != 0:
                valores[79] = self._format_decimal(valores[80] / valores[26], 4)
            else:
                valores[79] = self._format_decimal(0, 4)

            # Variável 96 - var0 + 1 dia útil
            from wallclub_core.utilitarios.funcoes_gerais import proximo_dia_util
            valores[96] = proximo_dia_util(valores[0])

            # Variável 125 - Diferença entre 124 e 26
            if valores[26] is not None:
                valores[125] = self._format_decimal(valores[124] - valores[26], 2)
            else:
                valores[125] = self._format_decimal(valores[124], 2)

            # var44, var41, var40 já calculadas acima (antes de var94)

            # Variável 45 - Data de pagamento (preservar se já existe)
            # Se já foi setada uma vez, não mexer mais (preservar data do primeiro pagamento)
            nsu_operacao = dados_linha['NsuOperacao']
            descricao_status_pag = str(dados_linha.get('DescricaoStatusPagamento', '')).strip()

            try:
                registro_existente = BaseTransacoesGestao.objects.filter(var9=nsu_operacao).first()

                if registro_existente and registro_existente.var45:
                    # Preservar data existente
                    valores[45] = registro_existente.var45
                    registrar_log('parametros_wallclub.calculadora_base_gestao',
                                 f"var45 preservada para NSU {nsu_operacao}: {valores[45]}",
                                 nivel='DEBUG')
                else:
                    # Primeira vez ou não tinha data: calcular
                    if descricao_status_pag.startswith('Pago'):
                        from datetime import datetime
                        valores[45] = datetime.now().strftime('%d/%m/%Y')
                        registrar_log('parametros_wallclub.calculadora_base_gestao',
                                     f"var45 calculada para NSU {nsu_operacao} (Pago): {valores[45]}",
                                     nivel='DEBUG')
                    else:
                        valores[45] = ''
            except Exception as e:
                # Se houver erro na busca, calcular normalmente
                registrar_log('parametros_wallclub.calculadora_base_gestao',
                             f"Erro ao buscar var45 para NSU {nsu_operacao}: {str(e)}", nivel='ERROR')
                if descricao_status_pag.startswith('Pago'):
                    from datetime import datetime
                    valores[45] = datetime.now().strftime('%d/%m/%Y')
                else:
                    valores[45] = ''

            # Variável 58 - Valor adicional Wall
            f58 = dados_linha.get('f58')
            if f58 is not None:
                valores[58] = self._format_decimal(self._to_decimal(f58, 2), 2)
            else:
                valores[58] = self._format_decimal(0, 2)

            # Variável 99 - var95 - var44
            if valores[95] is None:
                valores[99] = None
            else:
                valores[99] = self._format_decimal(valores[95] - valores[44], 2)

            # Variável 101 - var44
            valores[101] = self._format_decimal(valores[44], 2)

            # Variável 102 - ZERO
            valores[102] = self._format_decimal(0, 2)

            # Variáveis restantes implementadas conforme lógica PHP original
            # Usar apenas dados da transação + parâmetros importados

            # IMPLEMENTAR COM DADOS REAIS DA QUERY SQL
            # Variáveis que vêm da tabela pagamentos_efetuados (todas varchar)
            # valores[45] já foi calculado acima (data de pagamento) - NÃO sobrescrever
            valores[59] = dados_linha.get('f59') or ''  # var59 da tabela pagamentos_efetuados (varchar)
            valores[66] = dados_linha.get('f66') or ''  # var66 da tabela pagamentos_efetuados (varchar)
            valores[71] = dados_linha.get('f71') or ''  # var71 da tabela pagamentos_efetuados (varchar)
            valores[100] = dados_linha.get('f100') or ''  # var100 da tabela pagamentos_efetuados (varchar)
            # valores[111] e valores[112] já foram calculados como arrays acima
            # valores[111] = dados_linha.get('f111')  # var111 da tabela pagamentos_efetuados
            # valores[112] = dados_linha.get('f112')  # var112 da tabela pagamentos_efetuados

            # Variáveis calculadas baseadas em var103 (já calculada)
            # valores[102] já foi definida anteriormente
            # valores[107] já foi calculado como array acima
            # valores[107] = self._format_decimal(valores[103]["0"], 2)  # Mesmo que var103

            # Variáveis implementadas no PHP original
            # var65 - Lógica de cashback/agendado
            hoje = dt.now().date()
            if valores[55] == 0:
                valores[65] = "Sem Cashback"
            else:
                if valores[58] == 0:
                    try:
                        date_provided = dt.strptime(str(valores[57]), '%d/%m/%Y').date()
                        if date_provided > hoje:
                            valores[65] = "Agendado"
                        else:
                            valores[65] = self._format_decimal(valores[58] - valores[55], 2)
                    except:
                        valores[65] = self._format_decimal(valores[58] - valores[55], 2)
                else:
                    valores[65] = self._format_decimal(valores[58] - valores[55], 2)


            # Variável 98 - Condicional baseada em status pagamento
            if valores[69] == "Pendente":
                valores[98] = "Não Recebido"
            else:
                valores[98] = self._format_decimal(valores[44], 2)


            # Agora que valores[102] está definida, podemos calcular valores[107]["A"] e dependentes
            # Variável 107["A"] - Baseada em valores[102], valores[98] e valores[44]
            if valores[102] == "Não Recebido" or valores[98] == "Não Recebido":
                valores[107]["A"] = self._format_decimal(0, 2)
            else:
                valores[107]["A"] = self._format_decimal(valores[98] - valores[44], 2)

            # Variável 109["A"] - Produto de valores[107]["A"] * valores[108]
            valores[109]["A"] = self._format_decimal(valores[107]["A"] * valores[108], 2)

            # Agora que valores[107]["A"] e valores[109]["A"] estão definidas, podemos calcular as dependentes
            # Variável 113["A"] - Baseada em valores[107]["A"] e valores[112]["B"]
            if valores[107]["A"] == Decimal('0'):
                valores[113]["A"] = "Não Finalizado"
            else:
                valores[113]["A"] = self._format_decimal(valores[107]["A"] - valores[112]["B"], 2)

            # Variável 114["A"] - Baseada em valores[113]["A"] e valores[109]["A"]
            if valores[113]["A"] == "Não Finalizado":
                valores[114]["A"] = "Não Finalizado"
            else:
                valores[114]["A"] = self._format_decimal(valores[113]["A"] - valores[109]["A"], 2)


            # Variáveis 101 e 102 já foram definidas anteriormente

            # Variável 104 - var37
            valores[104] = valores[37]

            # Variável 105 - Condicional baseada em var102 e tipo pagamento
            if valores[102] == "Não Recebido":
                valores[105] = self._format_decimal(0, 2)
            else:
                if valores[12] == "PIX":
                    valores[105] = self._format_decimal(0, 2)
                else:
                    valores[105] = valores[73]

            # Variável 106 - Condicional baseada em var102 e tipo pagamento
            if valores[102] == "Não Recebido":
                valores[106] = self._format_decimal(0, 2)
            else:
                if valores[12] == "DEBITO":
                    valores[106] = self._format_decimal(0, 2)
                elif valores[12] == "PIX":
                    valores[106] = self._format_decimal(0, 2)
                else:
                    valores[106] = valores[75]

            # Variável 115 - Array com valores de cashback
            valores[115] = {
                "0": self._format_decimal(valores[55], 2),
                "A": self._format_decimal(valores[58], 2)
            }

            # Variável 116 - Array com diferenças de cashback
            if "0" in valores[114]:
                valores[116] = {
                    "0": self._format_decimal(valores[114]["0"] - valores[115]["0"], 2)
                }
            else:
                valores[116] = {
                    "0": self._format_decimal(0 - valores[115]["0"], 2)
                }

            if valores[114]["A"] == "Não Finalizado":
                valores[116]["A"] = "Não Finalizado"
            else:
                valores[116]["A"] = self._format_decimal(valores[114]["A"] - valores[115]["A"], 2)

            # Variável 122 - Status de pagamento baseado em cashback
            if valores[115]["A"] != 0:
                valores[122] = "Pago"
            else:
                if valores[115]["0"] != 0:
                    valores[122] = "Pendente"
                else:
                    valores[122] = "Sem Cashback"


            # Variável 117 - Percentual baseado em valores[116] / valores[30]
            valores[117] = {}
            if valores[30] is not None and valores[30] > 0:
                valores[117]["0"] = self._format_decimal(valores[116]["0"] / valores[30], 4)
                if valores[116]["A"] == "Não Finalizado":
                    valores[117]["A"] = "Não Finalizado"
                else:
                    valores[117]["A"] = self._format_decimal(valores[116]["A"] / valores[30], 4)
            else:
                valores[117]["0"] = self._format_decimal(0, 4)
                if valores[116]["A"] == "Não Finalizado":
                    valores[117]["A"] = "Não Finalizado"
                else:
                    valores[117]["A"] = self._format_decimal(0, 4)

            # Variável 118 - Percentual baseado em valores[116] / valores[11]
            valores[118] = {}
            if valores[11] > 0:
                valores[118]["0"] = self._format_decimal(valores[116]["0"] / valores[11], 4)
                if valores[116]["A"] == "Não Finalizado":
                    valores[118]["A"] = "Não Finalizado"
                else:
                    valores[118]["A"] = self._format_decimal(valores[116]["A"] / valores[11], 4)
            else:
                valores[118]["0"] = self._format_decimal(0, 4)
                if valores[116]["A"] == "Não Finalizado":
                    valores[118]["A"] = "Não Finalizado"
                else:
                    valores[118]["A"] = self._format_decimal(0, 4)

            # Variável 119 - Status complexo baseado em datas e valores
            try:
                # var97 agora está no formato ISO, precisa converter corretamente
                if valores[97] and valores[97] != 'None' and str(valores[97]).strip():
                    if 'T' in str(valores[97]):
                        date_provided1 = dt.strptime(str(valores[97])[:19], '%Y-%m-%dT%H:%M:%S').date()
                    else:
                        date_provided1 = dt.strptime(str(valores[97])[:10], '%Y-%m-%d').date()
                else:
                    raise ValueError("var97 é None ou vazio")

                if valores[96] and valores[96] != 'None' and str(valores[96]).strip():
                    date_provided2 = dt.strptime(valores[96], '%d/%m/%Y').date()
                else:
                    raise ValueError("var96 é None ou vazio")

                if valores[69] == "Pendente":
                    if date_provided2 < hoje:
                        valores[119] = "Pendente"
                    else:
                        valores[119] = "Receb. Agendado"
                else:
                    if valores[99] > 0:
                        if date_provided1 <= date_provided2:
                            valores[119] = "OK"
                        else:
                            valores[119] = "Recebido, mas atrasado"
                    else:
                        if valores[99] > 0:
                            if date_provided1 <= date_provided2:
                                valores[119] = "Recebido a maior, OK"
                            else:
                                valores[119] = "Recebido a maior, mas atrasado"
                        else:
                            # Verificar se var98 não é string antes de usar em operação matemática
                            if valores[98] == "Não Recebido":
                                valores[119] = "Pendente"
                            elif valores[98] >= (valores[42] + valores[115]["0"]):
                                if date_provided1 <= date_provided2:
                                    valores[119] = "Pagar. Recebido um pouco a menor, mas dentro do prazo"
                                else:
                                    valores[119] = "Pagar. Recebido um pouco a menor e atrasado"
                            else:
                                valores[119] = "Não Pagar. Valor recebido menor do que o valor a pagar ao EC"
            except (ValueError, TypeError):
                valores[119] = "Erro na Data"

            # Variável 120 - Status de aprovação baseado em var119
            if valores[119] == "Pendente":
                valores[120] = "Não aprovado"
            elif valores[119] == "Receb. Agendado":
                valores[120] = "Não aprovado"
            elif valores[119] == "OK":
                valores[120] = "Aprovado"
            elif valores[119] == "Recebido, mas atrasado":
                valores[120] = "Aprovado"
            elif valores[119] == "Recebido a maior, OK":
                valores[120] = "Aprovado"
            elif valores[119] == "Recebido a maior, mas atrasado":
                valores[120] = "Aprovado"
            elif valores[119] == "Pagar. Recebido um pouco a menor, mas dentro do prazo":
                valores[120] = "Aprovado"
            elif valores[119] == "Pagar. Recebido um pouco a menor e atrasado":
                valores[120] = "Aprovado"
            elif valores[119] == "Não Pagar. Valor recebido menor do que o valor a pagar ao EC":
                valores[120] = "Não aprovado"
            else:
                valores[120] = "Analisar manualmente"

            # Variável 123 - Status de aprovação baseado em data e cashback
            # Replica comportamento do PHP: false <= hoje = true, entra no primeiro bloco
            hoje = dt.now().date()
            try:
                data_provided = dt.strptime(valores[57], '%d/%m/%Y').date()
                if data_provided <= hoje:
                    if valores[120] == "Aprovado":
                        if valores[115]["0"] != 0:
                            valores[123] = "Aprovado"
                        else:
                            valores[123] = "Sem Cashback"
                    else:
                        valores[123] = "Aguardando Aprovação"
                else:
                    if valores[115]["0"] != 0:
                        valores[123] = "Agendado"
                    else:
                        valores[123] = "Sem Cashback"
            except (ValueError, TypeError):
                # PHP: false <= hoje = true, entra no primeiro bloco
                if valores[120] == "Aprovado":
                    if valores[115]["0"] != 0:
                        valores[123] = "Aprovado"
                    else:
                        valores[123] = "Sem Cashback"
                else:
                    valores[123] = "Aguardando Aprovação"

            # Variável 121 - Status de pagamento baseado em var44 e datas
            try:
                # PHP: DateTime::createFromFormat('d/m/Y', $valores[43]) cria datetime 00:00:00
                date_provided = dt.strptime(valores[43], '%d/%m/%Y')
                # PHP: new DateTime() cria datetime com horário atual
                from datetime import datetime
                hoje = datetime.now()  # Usar datetime naive

                # Usar datetime naive para comparação
                date_provided_naive = date_provided

                if valores[44] != 0:
                    valores[121] = "Pago"
                else:
                    # PHP compara datetime completo (com horário), não apenas data
                    if date_provided_naive < hoje:
                        if valores[68] == "TRANS. APROVADO":
                            valores[121] = "Pendente"
                        else:
                            valores[121] = "Oper. Cancelada"
                    else:
                        if valores[68] != "TRANS. APROVADO":
                            valores[121] = "Oper. Cancelada"
                        else:
                            valores[121] = "Agendado"
            except (ValueError, TypeError):
                valores[121] = "Erro na Data"

            # Variável 125 - valores[124] - valores[26] (duplicada - já corrigida acima)
            # Esta linha é redundante e foi removida

            # Variável 126 - Condicional baseada em status (PHP retorna 0, não "Não Recebido")
            if valores[69] == "Pendente":
                valores[126] = "0"
            else:
                if valores[88] is not None:
                    valores[126] = self._format_decimal(valores[90] - valores[88], 2)
                else:
                    valores[126] = self._format_decimal(valores[90], 2)

            # Variável 127 - Diferença percentual baseada em var93
            if "0" in valores[93]:
                valores[127] = self._format_decimal(valores[93]["A"] - valores[93]["0"], 4)
            else:
                valores[127] = valores[93]["A"]

            # Variável 128 - Condicional baseado em var98
            # var98 pode ser string "Não Recebido" quando status é Pendente
            if valores[98] == "Não Recebido" or isinstance(valores[98], str):
                valores[128] = valores[42]
            else:
                valores[128] = self._format_decimal(valores[98] - valores[42], 2)

            # Variável 129 - Lógica baseada em var98 e comparações
            if valores[98] == "PIX":
                valores[129] = "Desconto"
            elif valores[98] == "DEBITO":
                valores[129] = None  # PHP retorna None, não "-"
            else:
                # Replicar exatamente a lógica PHP: se valores[26] < valores[11] (None < number = False no PHP)
                if valores[26] is not None and valores[26] < valores[11]:
                    valores[129] = "Desconto"
                else:
                    # PHP vai para este else quando valores[26] é None ou >= valores[11]
                    if valores[11] > 0:
                        from wallclub_core.utilitarios.funcoes_gerais import calcular_cet
                        cet_resultado = calcular_cet(valores[20], valores[11], valores[13])
                        if cet_resultado is not None:
                            # Limitar a 2 casas decimais e máximo 20 caracteres (VARCHAR(20))
                            cet_formatado = f"{cet_resultado:.2f}"
                            if len(cet_formatado) > 20:
                                valores[129] = None  # PHP retorna None, não "-"
                            else:
                                valores[129] = cet_formatado
                        else:
                            valores[129] = None  # PHP retorna None, não "-"
                    else:
                        valores[129] = None  # PHP retorna None, não "-"

            # Variável 60A - var44 + var57
            # var57 pode ser string "Sem cashback" ou data, então copiar var44
            if isinstance(valores[57], str):
                valores['60A'] = self._format_decimal(valores[44], 2)
            else:
                valores['60A'] = self._format_decimal(valores[44], 2)  # Sempre apenas var44

            # Variável 61A - var60A - var33
            valores['61A'] = self._format_decimal(valores['60A'] - valores[33], 2)

            # Adicionar ID da fila de extrato para mapeamento
            valores['id_fila_extrato'] = dados_linha['id']

            registrar_log('parametros_wallclub.calculadora_base_gestao', f"Cálculo concluído para NSU: {dados_linha.get('NsuOperacao', 'N/A')} - {len(valores)} variáveis calculadas")
            return valores

        except Exception as e:
            registrar_log('parametros_wallclub.calculadora_base_gestao', f"Erro no cálculo para NSU {dados_linha.get('NsuOperacao', 'N/A')}: {str(e)}", nivel='ERROR')
            import traceback
            tb_str = traceback.format_exc()
            registrar_log('parametros_wallclub.calculadora_base_gestao', f"Erro ao calcular valores primários: {str(e)}\nTraceback completo:\n{tb_str}", nivel='ERROR')

            # Log das variáveis que são None no momento do erro
            none_vars = []
            for key, value in valores.items():
                if value is None:
                    none_vars.append(f"valores[{key}]")

            if none_vars:
                registrar_log('parametros_wallclub.calculadora_base_gestao', f"Variáveis None no momento do erro: {', '.join(none_vars)}", nivel='ERROR')

            raise

    def _validar_parametro(self, parametro, nome_parametro, contexto=""):
        """Valida se parâmetro não é None antes de usar"""
        if parametro is None or parametro == 'None' or parametro == '':
            # Retornar 0 como valor padrão para parâmetros inválidos
            return 0
        return parametro

    def _format_decimal(self, valor: float, casas: int) -> float:
        """Formata decimal com precisão específica - replica number_format() do PHP"""
        # Validar se valor é None ou inválido
        if valor is None:
            raise ValueError(f"Valor None passado para _format_decimal")

        try:
            # Usar arredondamento ROUND_HALF_UP para replicar number_format() do PHP
            from decimal import ROUND_HALF_UP
            decimal_valor = Decimal(str(valor))

            if casas == 0:
                return decimal_valor.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
            else:
                # Criar padrão de quantização baseado no número de casas decimais
                quantize_pattern = '0.' + '0' * casas
                return decimal_valor.quantize(Decimal(quantize_pattern), rounding=ROUND_HALF_UP)

        except (ValueError, TypeError, decimal.InvalidOperation) as e:
            raise ValueError(f"Erro ao converter valor '{valor}' (tipo: {type(valor)}) para Decimal: {e}")


