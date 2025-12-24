"""
Calculadora de Base de Gestão TEF
Migração fiel de pinbank_cria_base_gestao_tef.php
"""

# import logging - removido, usando registrar_log
from datetime import datetime as dt, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Any, Optional
from wallclub_core.utilitarios.log_control import registrar_log, log_esta_habilitado
from .services import ParametrosService
from wallclub_core.utilitarios.funcoes_gerais import proxima_sexta_feira
from django.db import connection


class CalculadoraTEF:
    """
    Calculadora de valores específicos para transações TEF
    Migração fiel da lógica do pinbank_cria_base_gestao_tef.php
    """
    
    def __init__(self):
        pass
    
    def calcular_valores_tef(self, transacao_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula todos os valores específicos para transações TEF
        Migração completa da função mainCarregaValoresPrimarios() do PHP
        
        Args:
            transacao_data: Dados da transação TEF do Pinbank
            
        Returns:
            Dict com valores calculados (var0 até var130)
        """
        valores = {}
        
        try:
            registrar_log('parametros_wallclub', f"INÍCIO calcular_valores_tef - ID: {transacao_data.get('id', 'N/A')}")
            # Buscar plano e parâmetros
            wall = 'S'  # Assumindo Wall por padrão para TEF
            registrar_log('parametros_wallclub', f"Buscando plano - TipoCompra: {transacao_data.get('TipoCompra', '')}, Parcelas: {transacao_data.get('NumeroTotalParcelas', 1)}, Bandeira: {transacao_data.get('Bandeira', '')}")
            id_plano = ParametrosService.busca_plano(
                transacao_data.get('TipoCompra', ''),
                transacao_data.get('NumeroTotalParcelas', 1),
                transacao_data.get('Bandeira', ''),
                wall
            )
            registrar_log('parametros_wallclub', f"Plano encontrado: {id_plano}")
            
            id_cliente = transacao_data.get('clienteId')
            registrar_log('parametros_wallclub', f"Cliente ID: {id_cliente}")
            data_ref = self._converter_para_timestamp(transacao_data.get('DataTransacao'))
            registrar_log('parametros_wallclub', f"Data referência: {data_ref}")
            
            # Variáveis primárias que vem do Pinbank (migração fiel do PHP)
            registrar_log('parametros_wallclub', "Iniciando cálculo de variáveis primárias...")
            valores = self._calcular_variaveis_primarias({}, transacao_data, data_ref, id_cliente, id_plano)
            registrar_log('parametros_wallclub', f"Variáveis primárias calculadas: {len(valores)} valores")
            
            # Variáveis secundárias que vem do Pinbank
            registrar_log('parametros_wallclub', "Iniciando cálculo de variáveis secundárias...")
            valores = self._calcular_variaveis_secundarias(valores, transacao_data)
            registrar_log('parametros_wallclub', f"Variáveis secundárias calculadas: {len(valores)} valores")
            
            # Cálculos financeiros complexos
            registrar_log('parametros_wallclub', "Iniciando cálculo de variáveis financeiras...")
            valores = self._calcular_variaveis_financeiras(valores, transacao_data, id_cliente, data_ref, id_plano)
            registrar_log('parametros_wallclub', f"Variáveis financeiras calculadas: {len(valores)} valores")
            
            # Status e informações adicionais
            registrar_log('parametros_wallclub', "Iniciando cálculo de status e informações...")
            valores = self._calcular_status_informacoes_completo(valores, transacao_data, id_cliente, data_ref, id_plano)
            registrar_log('parametros_wallclub', f"Status e informações calculadas: {len(valores)} valores")
            
            # Marcar como TEF
            valores['var130'] = 'TEF'
            
            # Preservar ID da transação para mapeamento
            valores['id'] = transacao_data.get('id')
            
            registrar_log('parametros_wallclub', f"FIM calcular_valores_tef - ID {transacao_data.get('id', 'N/A')} - {len(valores)} valores calculados")
            return valores
            
        except Exception as e:
            registrar_log('parametros_wallclub', f"ERRO CRÍTICO ao calcular valores TEF ID {transacao_data.get('id', 'N/A')}: {str(e)}", nivel='ERROR')
            raise
    
    def _calcular_variaveis_primarias(self, valores: Dict[str, Any], transacao_data: Dict[str, Any], 
                                     data_ref: dt, id_cliente: str, id_plano: int) -> Dict[str, Any]:
        """
        Calcula variáveis primárias (var0 até var13)
        Migração fiel das linhas 209-223 do PHP
        """
        valores = {}
        
        # Usar dados reais que vêm da query com JOINs (corrigido)
        canal_id = transacao_data.get('canal_id')
        if canal_id:
            # Mapear canal_id para nome do canal
            mapeamento_canais = {
                1: 'WALL 1',
                2: 'WALL 2', 
                3: 'WALL 3',
                4: 'WALL 4',
                5: 'WALL 5',
                6: 'ACLUB',
                7: 'WALL 7'
            }
            nome_canal = mapeamento_canais.get(canal_id, f'CANAL_{canal_id}')
        else:
            nome_canal = 'WALLCLUB'
        
        # Usar razão social real da query
        razao_social = transacao_data.get('razao_social', '')
        
        # Usar clienteId real da query
        id_loja_real = str(transacao_data.get('clienteId', ''))
        
        registrar_log('parametros_wallclub', f"Dados reais da query - Canal: {nome_canal} (ID: {canal_id}), Loja: {razao_social} (ID: {id_loja_real})")
        
        # Variáveis primárias (migração fiel do PHP)
        valores['var0'] = data_ref.strftime('%d/%m/%Y')  # Data
        valores['var1'] = data_ref.strftime('%H:%M:%S')  # Hora
        valores['var2'] = transacao_data.get('SerialNumber', '')  # Serial
        valores['var3'] = transacao_data.get('idTerminal', '')  # ID Terminal
        valores['var4'] = nome_canal  # Canal
        valores['var5'] = razao_social  # Razão social
        valores['var6'] = id_loja_real  # ID Loja
        valores['var7'] = transacao_data.get('cpf', '')  # CPF
        valores['var8'] = transacao_data.get('TipoCompra', '')  # Tipo compra
        valores['var9'] = transacao_data.get('NsuOperacao', '')  # NSU Operação
        valores['var10'] = transacao_data.get('NsuAcquirer', '')  # NSU Acquirer
        valores['var11'] = float(transacao_data.get('ValorBruto', 0))  # Valor bruto
        valores['var12'] = transacao_data.get('Bandeira', '')  # Bandeira
        valores['var13'] = int(transacao_data.get('NumeroTotalParcelas', 1))  # Parcelas
        
        return valores
    
    def _calcular_variaveis_secundarias(self, valores: Dict[str, Any], transacao_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula variáveis secundárias que vem do Pinbank
        Migração fiel das linhas 225-237 do PHP
        """
        
        # Variáveis secundárias (migração fiel do PHP)
        valores['var89'] = float(transacao_data.get('ValorTaxaAdm', 0)) / 100  # Taxa ADM
        valores['var92'] = float(transacao_data.get('ValorTaxaMes', 0)) / 100  # Taxa Mês
        valores['var68'] = transacao_data.get('DescricaoStatus', '')  # Status
        valores['var67'] = f"{float(transacao_data.get('ValorSplit', 0)):.2f}"  # Valor Split
        valores['var97'] = transacao_data.get('DataFuturaPagamento', '')  # Data pagamento
        valores['var124'] = transacao_data.get('ValorBrutoParcela', 0)  # Valor parcela
        valores['var69'] = transacao_data.get('DescricaoStatusPagamento', '')  # Status pagamento
        valores['var70'] = transacao_data.get('DataCancelamento', '')  # Data cancelamento
        
        return valores
    
    def _calcular_variaveis_financeiras(self, valores: Dict[str, Any], transacao_data: Dict[str, Any], 
                                       id_cliente: str, data_ref: dt, id_plano: int) -> Dict[str, Any]:
        """
        Calcula variáveis financeiras complexas
        Migração fiel das linhas 240-299+ do PHP
        """
        
        # var14 - Percentual de desconto (migração fiel linha 241-245)
        if valores.get('var130') == "Normal":
            valores['var14'] = "0.0000"
        else:
            param_7 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 7, 'S')
            valores['var14'] = f"{float(param_7 or 0):.4f}"
        
        # var83 - Cópia de var14 (linha 249)
        valores['var83'] = valores['var14']
        
        # var15 - Valor do desconto (linha 253)
        val11 = float(valores.get('var11', 0))
        val14 = float(valores.get('var14', 0))
        valores['var15'] = f"{val11 * val14 / 100:.2f}"
        
        # var84 - Cópia de var15 (linha 257)
        valores['var84'] = valores['var15']
        
        # var29 - Prazo limite (linha 263 - TEMP)
        valores['var29'] = "12"
        
        # var16 - Valor pago à vista (linha 268-277)
        if valores.get('var8') == "DEBITO":
            valores['var16'] = f"{val11:.2f}"
        else:
            diferenca = int(valores.get('var13', 1)) - int(valores.get('var29', 12))
            if diferenca > 0:
                valores['var16'] = f"{val11:.2f}"
            else:
                valores['var16'] = f"{val11 * (1 - val14 / 100):.2f}"
        
        # var81 - Cópia de var16 (linha 281)
        valores['var81'] = valores['var16']
        
        # var17 - Percentual taxa intermediação (linha 287-290)
        if valores.get('var130') == "Normal":
            valores['var17'] = "0.0000"
        else:
            param_10 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 10, 'S')
            valores['var17'] = f"{float(param_10 or 0):.4f}"
        
        # var85 - Cópia de var17 (linha 294)
        valores['var85'] = valores['var17']
        
        # var18 - Valor taxa intermediação (linha 298)
        val17 = float(valores.get('var17', 0))
        valores['var18'] = f"{val11 * val17 / 100:.2f}"
        
        # var86 - Cópia de var18 (linha 302)
        valores['var86'] = valores['var18']
        
        # var19 - Valor líquido calculado (linha 306-319)
        if valores.get('var8') == "DEBITO":
            valores['var19'] = f"{val11:.2f}"
        else:
            if valores.get('var12') == "PIX":
                valores['var19'] = valores['var16']
            else:
                diferenca = int(valores.get('var13', 1)) - int(valores.get('var29', 12))
                if diferenca > 0:
                    valores['var19'] = f"{val11 * (1 - val14 / 100):.2f}"
                else:
                    valores['var19'] = f"{val11 * (1 - val17 / 100):.2f}"
        
        # var20 - Valor por parcela (linha 323)
        val13 = int(valores.get('var13', 1))
        val19 = float(valores.get('var19', 0))
        valores['var20'] = f"{val19 / val13:.2f}"
        
        # Ajuste para Club (linha 327-330)
        if valores.get('var130') == "Club" and val13 > 0:
            valores['var20'] = f"{val19 / val13:.2f}"
            valores['var19'] = f"{float(valores['var20']) * val13:.2f}"
        
        # var23 - Valor à vista (linha 334)
        valores['var23'] = f"{float(valores.get('var16', 0)):.2f}"
        
        # var24 - Percentual cashback (linha 338)
        param_14 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 14, 'S')
        valores['var24'] = f"{float(param_14 or 0):.4f}"
        
        # var25 - Valor cashback (linha 342)
        val16 = float(valores.get('var16', 0))
        val24 = float(valores.get('var24', 0))
        valores['var25'] = f"{val16 * val24 / 100:.2f}"
        
        # var26 - Valor base para cálculos (linha 346-350)
        if valores.get('var12') == "PIX":
            valores['var26'] = f"{float(valores.get('var23', 0)):.2f}"
        else:
            valores['var26'] = f"{float(valores.get('var19', 0)):.2f}"
        
        # var82 - Cópia de var26 (linha 354)
        valores['var82'] = valores['var26']
        
        # var28 - Percentual taxa adquirente (linha 358)
        param_5 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 5, 'S')
        valores['var28'] = f"{float(param_5 or 0):.4f}"
        
        # var27 - Valor líquido adquirente (linha 362-366)
        val28 = float(valores.get('var28', 0))
        if valores.get('var12') == "PIX":
            valores['var27'] = f"{val11 * (1 - val14 / 100):.2f}"
        else:
            valores['var27'] = f"{val11 * (1 - val28 / 100):.2f}"
        
        # var31 - Percentual comissão (linha 375)
        param_17 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 17, 'S')
        valores['var31'] = f"{float(param_17 or 0):.4f}"
        
        # var32 - Valor comissão bruta (linha 380-384)
        val31 = float(valores.get('var31', 0))
        if valores.get('var12') == "PIX":
            val23 = float(valores.get('var23', 0))
            valores['var32'] = f"{val23 * val31 / 100:.2f}"
        else:
            valores['var32'] = f"{val11 * val31 / 100:.2f}"
        
        # var30 - Lucro bruto (linha 388)
        val27 = float(valores.get('var27', 0))
        val32 = float(valores.get('var32', 0))
        valores['var30'] = f"{val27 - val32:.2f}"
        
        # var33 - Comissão líquida (linha 392)
        valores['var33'] = f"{val16 * val31 / 100:.2f}"
        
        # var34 - Diferença comissão (linha 396)
        val33 = float(valores.get('var33', 0))
        valores['var34'] = f"{val32 - val33:.2f}"
        
        # var35 - Percentual diferença (linha 400-404)
        if val11 > 0:
            val34 = float(valores.get('var34', 0))
            valores['var35'] = f"{val34 / val11:.2f}"
        else:
            valores['var35'] = "0.00"
        
        # var36 - Percentual taxa F2 (linha 408)
        param_12 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 12, 'S')
        valores['var36'] = f"{float(param_12 or 0):.4f}"
        
        # var37 - Valor taxa F2 (linha 412)
        val36 = float(valores.get('var36', 0))
        valores['var37'] = f"{val16 * val36 / 100:.2f}"
        
        # var38 - Valor após taxa F2 (linha 416)
        val37 = float(valores.get('var37', 0))
        valores['var38'] = f"{val16 - val37:.2f}"
        
        # var39 - Percentual juros (linha 420)
        param_13 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 13, 'S')
        valores['var39'] = f"{float(param_13 or 0):.4f}"
        
        # var40 - Fator juros (linha 424)
        val39 = float(valores.get('var39', 0))
        valores['var40'] = f"{val39 * (1 + val13) / 2:.2f}"
        
        # var41 - Valor juros (linha 428)
        val38 = float(valores.get('var38', 0))
        val40 = float(valores.get('var40', 0))
        valores['var41'] = f"{val38 * val40 / 100:.2f}"
        
        # var46 - Receita total (linha 432)
        val30 = float(valores.get('var30', 0))
        valores['var46'] = f"{val30 + val33:.2f}"
        
        # var42 - Valor após juros (linha 436)
        val41 = float(valores.get('var41', 0))
        valores['var42'] = f"{val38 - val41:.2f}"
        
        # var43 - Data pagamento (linha 440-443)
        param_18 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 18, 'S')
        dias_pagamento = int(float(param_18 or 0))
        data_pagamento = data_ref + timedelta(days=dias_pagamento)
        valores['var43'] = data_pagamento.strftime('%d/%m/%Y')
        
        # var49 - Valor cashback efetivo (linha 448-473)
        valores['var49'] = self._calcular_var49(valores, transacao_data)
        
        # var50 - Percentual cashback (linha 477-481)
        if val11 > 0:
            val49 = float(valores.get('var49', 0))
            valores['var50'] = f"{val49 / val11:.2f}"
        else:
            valores['var50'] = "0.00"
        
        # var47 - Percentual comissão Wall (linha 485)
        param_21 = ParametrosService.retornar_parametro_loja(int(id_cliente), int(data_ref.timestamp()), id_plano, 21, 'S')
        valores['var47'] = f"{float(param_21 or 0):.4f}"
        
        # var87 - Percentual Wall sobre receita (linha 489)
        param_wall_1 = ParametrosService.retornar_parametro_wall(int(id_cliente), int(data_ref.timestamp()), id_plano, 1, 'S')
        valores['var87'] = f"{float(param_wall_1 or 0):.4f}"
        
        # var88 - Valor Wall sobre receita (linha 493)
        val26 = float(valores.get('var26', 0))
        val87 = float(valores.get('var87', 0))
        valores['var88'] = f"{val26 * val87 / 100:.2f}"
        
        # var90 - Valor taxa ADM (linha 497)
        val_bruto = float(transacao_data.get('ValorBruto', 0))
        val89 = float(valores.get('var89', 0))
        valores['var90'] = f"{val_bruto * val89:.2f}"
        
        # var91 - Percentual Wall juros (linha 501)
        param_wall_4 = ParametrosService.retornar_parametro_wall(int(id_cliente), int(data_ref.timestamp()), id_plano, 4, 'S')
        valores['var91'] = f"{float(param_wall_4 or 0):.4f}"
        
        # var78 - Cópia de var91 (linha 505)
        valores['var78'] = valores['var91']
        
        # var93 - Fator Wall juros (linha 514)
        val91 = float(valores.get('var91', 0))
        valores['var93_0'] = f"{val91 * (1 + val13) / 2:.4f}"
        
        # var94 - Valor Wall juros (linha 522)
        val93_0 = float(valores.get('var93_0', 0))
        valores['var94_0'] = f"{val26 * val93_0 / 100:.2f}"
        
        # var95 - Lucro líquido base (linha 526)
        val88 = float(valores.get('var88', 0))
        val94_0 = float(valores.get('var94_0', 0))
        valores['var95'] = f"{val26 - val88 - val94_0:.2f}"
        
        # var80 - Valor Wall total (linha 531-539)
        if valores.get('var130') == "Normal":
            valores['var80'] = "0.00"
        else:
            if val17 == 0:
                valores['var80'] = "0.00"
            else:
                valores['var80'] = f"{val88 + val94_0:.2f}"
        
        # var73 - Lucro líquido efetivo (linha 544-552)
        if valores.get('var130') == "Normal":
            valores['var73'] = "0.00"
        else:
            if val17 == 0:
                valores['var73'] = "0.00"
            else:
                val80 = float(valores.get('var80', 0))
                val42 = float(valores.get('var42', 0))
                valores['var73'] = f"{val26 - val80 - val42:.2f}"
        
        # var74 - Percentual taxa F2 efetivo (linha 556)
        param_f2_2 = ParametrosService.retornar_parametro_wall(int(transacao_data.get('clienteId', 0)), int(data_ref.timestamp()), id_plano, 2, 'S')
        valores['var74'] = f"{float(param_f2_2 or 0):.4f}"
        
        # var75 - Valor taxa F2 efetivo (linha 560)
        val74 = float(valores.get('var74', 0))
        valores['var75'] = f"{val19 * val74 / 100:.2f}"
        
        # var77 - Lucro total efetivo (linha 564)
        val73 = float(valores.get('var73', 0))
        val75 = float(valores.get('var75', 0))
        valores['var77'] = f"{val73 + val75:.2f}"
        
        # var22 - Valor final PIX/Cartão (linha 569-573)
        if valores.get('var12') == "PIX":
            valores['var22'] = "0.00"
        else:
            valores['var22'] = f"{float(valores.get('var77', 0)):.2f}"
        
        # var72 - Percentual lucro efetivo (linha 577-581)
        if val11 > 0:
            valores['var72'] = f"{val73 / val11:.4f}"
        else:
            valores['var72'] = "0.0000"
        
        # var76 - Percentual total efetivo (linha 585)
        val72 = float(valores.get('var72', 0))
        valores['var76'] = f"{val72 + val74:.4f}"
        
        # var21 - Percentual Wall final (linha 590-602)
        if valores.get('var12') == "PIX":
            valores['var21'] = "0.0000"
        else:
            if val17 == 0:
                valores['var21'] = "0.0000"
            else:
                if valores.get('var130') == "Normal":
                    valores['var21'] = "0.0000"
                else:
                    valores['var21'] = f"{float(valores.get('var78', 0)):.4f}"
        
        return valores
    
    def _calcular_var49(self, valores: Dict[str, Any], transacao_data: Dict[str, Any]) -> str:
        """
        Calcula var49 - Valor cashback efetivo
        Migração fiel das linhas 448-473 do PHP
        """
        try:
            if valores.get('var130') == "Normal":
                return "0.00"
            
            if valores.get('var8') == "DEBITO":
                return "0.00"
            
            if valores.get('var12') == "PIX":
                return "0.00"
            
            val13 = int(valores.get('var13', 1))
            if val13 <= 0:
                return "0.00"
            
            val17 = float(valores.get('var17', 0))
            if val17 == 0:
                return "0.00"
            
            val46 = float(valores.get('var46', 0))
            val42 = float(valores.get('var42', 0))
            diferenca = val46 - val42
            
            if round(diferenca, 2) < 0:
                return "0.00"
            else:
                return f"{max(0, diferenca):.2f}"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var49: {str(e)}", nivel='ERROR')
            return "0.00"
    
    def _calcular_status_informacoes_completo(self, valores: Dict[str, Any], transacao_data: Dict[str, Any],
                                            id_cliente: str, data_ref: dt, id_plano: int) -> Dict[str, Any]:
        """
        Calcula status e informações adicionais completas
        Migração das variáveis finais do PHP
        """
        
        # Continuar cálculos das variáveis restantes
        valores = self._calcular_variaveis_avancadas(valores, transacao_data, id_cliente, data_ref, id_plano)
        
        # var121 - Status dependente de pagamento (migração fiel do PHP)
        valores['var121'] = self._calcular_status_pagamento_tef(valores, transacao_data)
        
        # Calcular variáveis de status adicionais
        valores['var119'] = self._calcular_var119(valores)
        valores['var120'] = self._calcular_var120(valores)
        valores['var122'] = self._calcular_var122(valores)
        valores['var123'] = self._calcular_var123(valores)
        valores['var127'] = self._calcular_var127(valores)
        
        return valores
    
    def _calcular_variaveis_avancadas(self, valores: Dict[str, Any], transacao_data: Dict[str, Any],
                                     id_cliente: str, data_ref: dt, id_plano: int) -> Dict[str, Any]:
        """
        Calcula variáveis avançadas (var103-var128)
        Migração das linhas 608-699+ do PHP
        """
        try:
            # var103_0 - Lucro líquido alternativo (linha 614)
            val95 = float(valores.get('var95', 0))
            val42 = float(valores.get('var42', 0))
            valores['var103_0'] = f"{val95 - val42:.2f}"
            
            # var107_0 - Cópia de var103_0 (linha 621)
            valores['var107_0'] = valores['var103_0']
            
            # var108 - Percentual comissão Wall sobre lucro (linha 625)
            param_wall_6 = ParametrosService.retornar_parametro_wall(int(id_cliente), int(data_ref.timestamp()), id_plano, 6, 'S')
            valores['var108'] = f"{float(param_wall_6 or 0):.4f}"
            
            # var109_0 - Comissão Wall sobre lucro (linha 632)
            val107_0 = float(valores.get('var107_0', 0))
            val108 = float(valores.get('var108', 0))
            valores['var109_0'] = f"{val107_0 * val108 / 100:.2f}"
            
            # var110 - Percentual taxa F2 alternativo (linha 636)
            param_f2_alt = ParametrosService.retornar_parametro_wall(int(id_cliente), int(data_ref.timestamp()), id_plano, 2, 'S')
            valores['var110'] = f"{float(param_f2_alt or 0):.4f}"
            
            # var111_0 - Taxa F2 sobre receita (linha 643)
            val26 = float(valores.get('var26', 0))
            val110 = float(valores.get('var110', 0))
            valores['var111_0'] = f"{val26 * val110 / 100:.2f}"
            
            # var112_A, var113_0, var114_0 - Dependem de pagamento Wall (comentados no PHP)
            # Implementar quando necessário
            
            # var51 - Cálculo complexo de cashback (linha 671-698)
            valores['var51'] = self._calcular_var51(valores)
            
            return valores
            
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular variáveis avançadas: {str(e)}", nivel='ERROR')
            return valores
    
    def _calcular_var51(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var51 - Cálculo complexo de cashback
        Migração fiel das linhas 671-698 do PHP
        """
        try:
            if valores.get('var130') == "Normal":
                return "0.00"
            
            if valores.get('var8') == "DEBITO":
                return "0.00"
            
            if valores.get('var12') == "PIX":
                return "0.00"
            
            val13 = int(valores.get('var13', 1))
            val29 = int(valores.get('var29', 12))
            
            if val13 > val29:
                return "0.00"
            
            # Subcondição
            val34 = float(valores.get('var34', 0))
            val114_0 = float(valores.get('var114_0', 0))  # Pode estar comentado no PHP
            val49 = float(valores.get('var49', 0))
            val47 = float(valores.get('var47', 0))
            
            if val34 <= (val114_0 - val49):
                temp_result = val34 * val47 / 100
            else:
                temp_result = (val114_0 - val49) * val47 / 100
            
            # Verificação de resultado negativo
            if temp_result < 0:
                return "0.00"
            else:
                return f"{temp_result:.2f}"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var51: {str(e)}", nivel='ERROR')
            return "0.00"
    
    def _calcular_status_pagamento_tef(self, valores: Dict[str, Any], transacao_data: Dict[str, Any]) -> str:
        """
        Calcula status de pagamento específico para TEF
        Migração fiel da lógica do var121 do PHP (linhas 1185-1202)
        """
        try:
            # var121 - Status de pagamento (linha 1185-1204)
            val44 = float(valores.get('var44', 0))
            
            if val44 != 0:
                return "Pago"
            
            # Data de pagamento (var43)
            data_pagamento_str = valores.get('var43', '')
            if not data_pagamento_str:
                return "Indefinido"
            
            try:
                data_pagamento = dt.strptime(data_pagamento_str, '%d/%m/%Y').date()
                hoje = dt.now().date()
                
                if data_pagamento < hoje:
                    if valores.get('var68') == "TRANS. APROVADO":
                        return "Pendente"
                    else:
                        return "Oper. Cancelada"
                else:
                    if valores.get('var68') != "TRANS. APROVADO":
                        return "Oper. Cancelada"
                    else:
                        return "Agendado"
                        
            except ValueError:
                registrar_log('parametros_wallclub', f"Erro ao converter data de pagamento: {data_pagamento_str}", nivel='ERROR')
                return "Indefinido"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular status de pagamento TEF: {str(e)}", nivel='ERROR')
            return "Indefinido"
    
    def _calcular_var119(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var119 - Status de recebimento
        Migração das linhas 1108-1144 do PHP (comentado mas importante)
        """
        try:
            # Lógica comentada no PHP mas necessária para completude
            val69 = valores.get('var69', '')
            
            if val69 == "Pendente":
                # Comparar data prevista com hoje
                data_prevista_str = valores.get('var96', '')
                if data_prevista_str:
                    try:
                        data_prevista = dt.strptime(data_prevista_str, '%d/%m/%Y').date()
                        hoje = dt.now().date()
                        
                        if data_prevista < hoje:
                            return "Pendente"
                        else:
                            return "Receb. Agendado"
                    except ValueError:
                        return "Pendente"
                return "Pendente"
            
            # Lógica complexa de recebimento
            val99 = float(valores.get('var99', 0))
            
            if val99 > 0:
                # Comparar datas de recebimento
                data_receb_str = valores.get('var97', '')
                data_prev_str = valores.get('var96', '')
                
                try:
                    data_receb = dt.strptime(data_receb_str, '%d/%m/%Y').date()
                    data_prev = dt.strptime(data_prev_str, '%d/%m/%Y').date()
                    
                    if data_receb <= data_prev:
                        return "OK"
                    else:
                        return "Recebido, mas atrasado"
                except ValueError:
                    return "OK"
            
            return "Analisar manualmente"
            
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var119: {str(e)}", nivel='ERROR')
            return "Indefinido"
    
    def _calcular_var120(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var120 - Status de aprovação
        Migração das linhas 1147-1183 do PHP (comentado)
        """
        try:
            var119 = valores.get('var119', '')
            
            if var119 in ["Pendente", "Receb. Agendado"]:
                return "Não aprovado"
            elif var119 in ["OK", "Recebido, mas atrasado", "Recebido a maior, OK", 
                           "Recebido a maior, mas atrasado", 
                           "Pagar. Recebido um pouco a menor, mas dentro do prazo",
                           "Pagar. Recebido um pouco a menor e atrasado"]:
                return "Aprovado"
            elif var119 == "Não Pagar. Valor recebido menor do que o valor a pagar ao EC":
                return "Não aprovado"
            else:
                return "Analisar manualmente"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var120: {str(e)}", nivel='ERROR')
            return "Indefinido"
    
    def _calcular_var122(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var122 - Status de cashback
        Migração das linhas 1207-1215 do PHP (comentado)
        """
        try:
            # var115_A seria o valor pago de cashback
            var115_a = float(valores.get('var115_A', 0))
            var115_0 = float(valores.get('var115_0', 0))
            
            if var115_a != 0:
                return "Pago"
            elif var115_0 != 0:
                return "Pendente"
            else:
                return "Sem Cashback"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var122: {str(e)}", nivel='ERROR')
            return "Sem Cashback"
    
    def _calcular_var123(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var123 - Status de aprovação de cashback
        Migração das linhas 1218-1235 do PHP (comentado)
        """
        try:
            # Data de aprovação (var57)
            data_aprovacao_str = valores.get('var57', '')
            
            if data_aprovacao_str:
                try:
                    data_aprovacao = dt.strptime(data_aprovacao_str, '%d/%m/%Y').date()
                    hoje = dt.now().date()
                    
                    if data_aprovacao <= hoje:
                        var120 = valores.get('var120', '')
                        var115_0 = float(valores.get('var115_0', 0))
                        
                        if var120 == "Aprovado":
                            if var115_0 != 0:
                                return "Aprovado"
                            else:
                                return "Sem Cashback"
                        else:
                            return "Aguardando Aprovação"
                    else:
                        var115_0 = float(valores.get('var115_0', 0))
                        if var115_0 != 0:
                            return "Agendado"
                        else:
                            return "Sem Cashback"
                            
                except ValueError:
                    return "Sem Cashback"
            
            return "Sem Cashback"
            
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var123: {str(e)}", nivel='ERROR')
            return "Sem Cashback"
    
    def _calcular_var127(self, valores: Dict[str, Any]) -> str:
        """
        Calcula var127 - Diferença de fatores Wall
        Migração das linhas 1246-1250 do PHP
        """
        try:
            var93_0 = float(valores.get('var93_0', 0))
            var93_a = float(valores.get('var93_A', 0))
            
            if var93_0 != 0:
                return f"{var93_a - var93_0:.4f}"
            else:
                return f"{var93_a:.4f}"
                
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro ao calcular var127: {str(e)}", nivel='ERROR')
            return "0.0000"
    
    def _converter_para_timestamp(self, data_str: str) -> dt:
        """
        Converte string de data para timestamp
        Migração da função converterParaTimestamp() do PHP
        """
        try:
            if isinstance(data_str, str):
                # Tentar diferentes formatos
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                    try:
                        return dt.strptime(data_str, fmt)
                    except ValueError:
                        continue
            return dt.now()
        except:
            return dt.now()
    
    def processar_lote_tef(self, transacoes_tef: list) -> list:
        """
        Processa um lote de transações TEF
        
        Args:
            transacoes_tef: Lista de transações TEF do Pinbank
            
        Returns:
            Lista de transações processadas com valores calculados
        """
        transacoes_processadas = []
        
        registrar_log('parametros_wallclub', f"INÍCIO processar_lote_tef - {len(transacoes_tef)} transações TEF")
        
        for i, transacao in enumerate(transacoes_tef):
            try:
                registrar_log('parametros_wallclub', f"Processando transação TEF {i+1}/{len(transacoes_tef)} - ID: {transacao.get('id', 'N/A')}")
                valores_calculados = self.calcular_valores_tef(transacao)
                registrar_log('parametros_wallclub', f"Cálculo individual concluído para ID: {transacao.get('id', 'N/A')}")
                
                # Verificar se valores_calculados é válido
                if valores_calculados and isinstance(valores_calculados, dict) and len(valores_calculados) > 0:
                    # Preservar campos originais importantes
                    transacao_completa = valores_calculados.copy()
                    transacao_completa.update({
                        'DataTransacao': transacao.get('DataTransacao'),
                        'DataFuturaPagamento': transacao.get('DataFuturaPagamento'),
                        'NsuOperacao': transacao.get('NsuOperacao'),
                        'id': transacao.get('id')
                    })
                    
                    transacoes_processadas.append(transacao_completa)
                    registrar_log('parametros_wallclub', f"Transação TEF {transacao.get('id', 'N/A')} processada com sucesso - {len(valores_calculados)} valores calculados")
                else:
                    registrar_log('parametros_wallclub', f"ERRO: Transação TEF {transacao.get('id', 'N/A')} retornou valores inválidos: {valores_calculados}", nivel='ERROR')
                
            except Exception as e:
                registrar_log('parametros_wallclub', f"Erro ao processar transação TEF {transacao.get('id', 'N/A')}: {str(e)}", nivel='ERROR')
                registrar_log('parametros_wallclub', f"ERRO na transação TEF {transacao.get('id', 'N/A')}: {str(e)}", nivel='ERROR')
                continue
        
        registrar_log('parametros_wallclub', f"FIM processar_lote_tef - Processadas {len(transacoes_processadas)} de {len(transacoes_tef)} transações TEF")
        return transacoes_processadas
