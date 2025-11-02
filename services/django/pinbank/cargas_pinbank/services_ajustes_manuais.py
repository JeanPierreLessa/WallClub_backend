"""
Serviços para ajustes manuais na base de dados Pinbank
Queries de manutenção e correção de dados
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
        1. Insere registros faltantes em transactiondata a partir de pinbankExtratoPOS
        2. Remove duplicatas de baseTransacoesGestao sem idFilaExtrato quando existe versão com idFilaExtrato
        
        Returns:
            Dict com contadores de registros inseridos e deletados
        """
        registrar_log('pinbank.cargas_pinbank', "Iniciando ajustes manuais da base")
        
        resultado = {
            'inseridos_transactiondata': 0,
            'deletados_base_gestao': 0
        }
        
        try:
            with connection.cursor() as cursor:
                # 1. Inserir registros faltantes em transactiondata
                registrar_log('pinbank.cargas_pinbank', "Executando INSERT em transactiondata")
                
                cursor.execute("""
                    INSERT INTO transactiondata 
                    ( datahora, valor_original, nsupinbank, terminal )
                    SELECT  REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' ') AS Data_Transacao,
                            p.ValorBruto,
                            p.NsuOperacao,
                            t.terminal  
                    FROM    wallclub.pinbankExtratoPOS p,
                            terminais t
                    WHERE   t.terminal = p.SerialNumber 
                            AND t.idterminal = p.IdTerminal 
                            AND t.inicio <= UNIX_TIMESTAMP(REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' '))
                            AND ( t.fim = 0 OR t.fim >= UNIX_TIMESTAMP(REPLACE(SUBSTRING_INDEX(p.DataTransacao, '.', 1), 'T', ' ')))
                            AND NOT EXISTS ( SELECT nsupinbank FROM transactiondata WHERE nsupinbank = NsuOperacao )
                """)
                
                resultado['inseridos_transactiondata'] = cursor.rowcount
                registrar_log('pinbank.cargas_pinbank', f"INSERT concluído: {resultado['inseridos_transactiondata']} registros inseridos em transactiondata")
                
                # 2. Deletar duplicatas de baseTransacoesGestao
                registrar_log('pinbank.cargas_pinbank', "Executando DELETE em baseTransacoesGestao")
                
                cursor.execute("""
                    DELETE FROM wallclub.baseTransacoesGestao 
                    WHERE   idFilaExtrato IS NULL 
                            AND var9 IN ( 
                                SELECT var9 FROM (
                                    SELECT DISTINCT var9 
                                    FROM wallclub.baseTransacoesGestao
                                    WHERE idFilaExtrato IS NOT NULL
                                ) AS duplicatas
                            )
                """)
                
                resultado['deletados_base_gestao'] = cursor.rowcount
                registrar_log('pinbank.cargas_pinbank', f"DELETE concluído: {resultado['deletados_base_gestao']} registros deletados de baseTransacoesGestao")
            
            registrar_log('pinbank.cargas_pinbank', f"Ajustes manuais finalizados com sucesso: {resultado}")
            return resultado
            
        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('pinbank.cargas_pinbank', f"Erro crítico nos ajustes manuais: {str(e)}", nivel='ERROR')
            registrar_log('pinbank.cargas_pinbank', f"Traceback completo: {erro_completo}", nivel='ERROR')
            raise
