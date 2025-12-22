"""
Serviços para ajustes manuais na base de dados Pinbank
Queries de manutenção e correção de dados
MIGRADO: 22/12/2025 - Insere em transactiondata_pos ao invés de transactiondata
"""

from typing import Dict
from django.db import connection
from wallclub_core.utilitarios.log_control import registrar_log


class AjustesManuaisService:
    """
    Serviço para executar ajustes manuais na base de dados
    Correção de inconsistências e sincronização de tabelas
    """

    @staticmethod
    def ajustes_manuais_base() -> Dict[str, int]:
        """
        Executa ajustes manuais na base de dados:
        1. Insere registros faltantes em transactiondata_pos a partir de pinbankExtratoPOS

        Returns:
            Dict com contador de registros inseridos
        """
        registrar_log('pinbank.cargas_pinbank', "Iniciando ajustes manuais da base")

        resultado = {
            'inseridos_transactiondata': 0
        }

        try:
            with connection.cursor() as cursor:
                # 1. Inserir registros faltantes em transactiondata_pos
                registrar_log('pinbank.cargas_pinbank', "Executando INSERT em transactiondata_pos")

                cursor.execute("""
                    INSERT INTO transactiondata_pos
                    ( gateway, datahora, valor_original, nsu_gateway, terminal )
                    SELECT  'PINBANK',
                            REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' ') AS Data_Transacao,
                            p.ValorBruto,
                            p.NsuOperacao,
                            t.terminal
                    FROM    wallclub.pinbankExtratoPOS p,
                            terminais t
                    WHERE   t.terminal = p.SerialNumber
                            AND t.inicio <= REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' ')
                            AND ( t.fim IS NULL OR t.fim >= REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' '))
                            AND NOT EXISTS ( SELECT nsu_gateway FROM transactiondata_pos WHERE nsu_gateway = NsuOperacao AND gateway = 'PINBANK' )
                """)

                resultado['inseridos_transactiondata'] = cursor.rowcount
                registrar_log('pinbank.cargas_pinbank', f"INSERT concluído: {resultado['inseridos_transactiondata']} registros inseridos em transactiondata_pos")

            registrar_log('pinbank.cargas_pinbank', f"Ajustes manuais finalizados com sucesso: {resultado}")
            return resultado

        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank', f"Erro crítico nos ajustes manuais: {str(e)}", nivel='ERROR')
            registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_completo}", nivel='ERROR')
            raise
