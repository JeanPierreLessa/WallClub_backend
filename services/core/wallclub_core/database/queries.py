"""
Queries SQL Diretas - Sem dependências de modelos entre containers
Usado para leitura de dados de APP2 por outros containers
"""
from django.db import connection
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal


class TransacoesQueries:
    """
    Queries diretas na tabela pinbank.baseTransacoesGestao
    Usado por Portais e Sistema Bancário para relatórios
    """
    
    @staticmethod
    def listar_transacoes_aprovadas(filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Lista transações aprovadas com filtros
        
        Args:
            filtros: {
                'loja_id': str,
                'canal_id': str,
                'data_inicio': datetime,
                'data_fim': datetime,
                'limit': int (default 1000)
            }
        
        Returns:
            Lista de dicionários com dados das transações
        """
        try:
            where_clauses = ["var68 = 'TRANS. APROVADO'"]
            params = []
            
            if filtros.get('loja_id'):
                where_clauses.append("var9 = %s")
                params.append(filtros['loja_id'])
            
            if filtros.get('canal_id'):
                where_clauses.append("var4 = %s")
                params.append(filtros['canal_id'])
            
            if filtros.get('data_inicio'):
                where_clauses.append("data_transacao >= %s")
                params.append(filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                where_clauses.append("data_transacao <= %s")
                params.append(filtros['data_fim'])
            
            limit = filtros.get('limit', 1000)
            
            sql = f"""
                SELECT 
                    id,
                    var0 as data_str,
                    var7 as nsu,
                    var9 as loja_id,
                    var4 as canal_id,
                    var12 as numero_cartao,
                    var13 as valor_bruto,
                    var23 as valor_liquido,
                    var68 as status,
                    data_transacao
                FROM baseTransacoesGestao
                WHERE {' AND '.join(where_clauses)}
                ORDER BY data_transacao DESC
                LIMIT {limit}
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao listar transações: {str(e)}", nivel='ERROR')
            return []
    
    @staticmethod
    def obter_totalizadores(filtros: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula totalizadores de transações (SUM, COUNT, AVG)
        
        Args:
            filtros: mesmos de listar_transacoes_aprovadas
        
        Returns:
            {
                'total_transacoes': int,
                'valor_bruto_total': Decimal,
                'valor_liquido_total': Decimal,
                'valor_medio': Decimal
            }
        """
        try:
            where_clauses = ["var68 = 'TRANS. APROVADO'"]
            params = []
            
            if filtros.get('loja_id'):
                where_clauses.append("var9 = %s")
                params.append(filtros['loja_id'])
            
            if filtros.get('canal_id'):
                where_clauses.append("var4 = %s")
                params.append(filtros['canal_id'])
            
            if filtros.get('data_inicio'):
                where_clauses.append("data_transacao >= %s")
                params.append(filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                where_clauses.append("data_transacao <= %s")
                params.append(filtros['data_fim'])
            
            sql = f"""
                SELECT 
                    COUNT(*) as total_transacoes,
                    COALESCE(SUM(var13), 0) as valor_bruto_total,
                    COALESCE(SUM(var23), 0) as valor_liquido_total,
                    COALESCE(AVG(var13), 0) as valor_medio
                FROM baseTransacoesGestao
                WHERE {' AND '.join(where_clauses)}
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return {
                    'total_transacoes': row[0],
                    'valor_bruto_total': Decimal(str(row[1])),
                    'valor_liquido_total': Decimal(str(row[2])),
                    'valor_medio': Decimal(str(row[3]))
                }
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao calcular totalizadores: {str(e)}", nivel='ERROR')
            return {
                'total_transacoes': 0,
                'valor_bruto_total': Decimal('0'),
                'valor_liquido_total': Decimal('0'),
                'valor_medio': Decimal('0')
            }
    
    @staticmethod
    def buscar_por_nsu(nsu: str, loja_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Busca transação por NSU
        
        Args:
            nsu: Número único da transação
            loja_id: ID da loja (opcional)
        
        Returns:
            Dados da transação ou None
        """
        try:
            params = [nsu]
            where_clauses = ["var7 = %s"]
            
            if loja_id:
                where_clauses.append("var9 = %s")
                params.append(loja_id)
            
            sql = f"""
                SELECT 
                    id,
                    var0 as data_str,
                    var7 as nsu,
                    var9 as loja_id,
                    var4 as canal_id,
                    var12 as numero_cartao,
                    var13 as valor_bruto,
                    var23 as valor_liquido,
                    var68 as status,
                    data_transacao
                FROM baseTransacoesGestao
                WHERE {' AND '.join(where_clauses)}
                ORDER BY id DESC
                LIMIT 1
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
                return None
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao buscar por NSU: {str(e)}", nivel='ERROR')
            return None
    
    @staticmethod
    def verificar_transacao_cancelada(nsu: str) -> bool:
        """
        Verifica se uma transação foi cancelada
        
        Args:
            nsu: Número único da transação
        
        Returns:
            True se cancelada, False caso contrário
        """
        try:
            sql = """
                SELECT 1 
                FROM baseTransacoesGestao
                WHERE var7 = %s 
                AND var68 = 'TRANS. CANCELADO'
                LIMIT 1
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, [nsu])
                return cursor.fetchone() is not None
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao verificar cancelamento: {str(e)}", nivel='ERROR')
            return False
    
    @staticmethod
    def listar_recebimentos_agrupados(filtros: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Lista recebimentos agrupados por data
        Usado por portais/lojista/services_recebimentos.py
        
        Args:
            filtros: {
                'loja_id': str,
                'data_inicio': datetime,
                'data_fim': datetime
            }
        
        Returns:
            Lista com recebimentos agrupados
        """
        try:
            where_clauses = ["var68 = 'TRANS. APROVADO'"]
            params = []
            
            if filtros.get('loja_id'):
                where_clauses.append("var9 = %s")
                params.append(filtros['loja_id'])
            
            if filtros.get('data_inicio'):
                where_clauses.append("data_transacao >= %s")
                params.append(filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                where_clauses.append("data_transacao <= %s")
                params.append(filtros['data_fim'])
            
            sql = f"""
                SELECT 
                    DATE(data_transacao) as data,
                    COUNT(*) as quantidade,
                    SUM(var13) as valor_bruto,
                    SUM(var23) as valor_liquido
                FROM baseTransacoesGestao
                WHERE {' AND '.join(where_clauses)}
                GROUP BY DATE(data_transacao)
                ORDER BY data DESC
                LIMIT 365
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao listar recebimentos agrupados: {str(e)}", nivel='ERROR')
            return []
    
    @staticmethod
    def obter_ids_unicos_por_nsu(filtros: Dict[str, Any]) -> List[int]:
        """
        Retorna IDs únicos (mais recentes) de cada NSU para evitar duplicatas
        Usado por views de transações/vendas
        
        Args:
            filtros: mesmos de listar_transacoes_aprovadas
        
        Returns:
            Lista de IDs únicos
        """
        try:
            where_clauses = ["var68 = 'TRANS. APROVADO'"]
            params = []
            
            if filtros.get('loja_id'):
                where_clauses.append("var9 = %s")
                params.append(filtros['loja_id'])
            
            if filtros.get('canal_id'):
                where_clauses.append("var4 = %s")
                params.append(filtros['canal_id'])
            
            if filtros.get('data_inicio'):
                where_clauses.append("data_transacao >= %s")
                params.append(filtros['data_inicio'])
            
            if filtros.get('data_fim'):
                where_clauses.append("data_transacao <= %s")
                params.append(filtros['data_fim'])
            
            sql = f"""
                SELECT MAX(id) as max_id
                FROM baseTransacoesGestao
                WHERE {' AND '.join(where_clauses)}
                GROUP BY var7
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
                return [row[0] for row in cursor.fetchall()]
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao obter IDs únicos: {str(e)}", nivel='ERROR')
            return []


class TerminaisQueries:
    """
    Queries diretas na tabela posp2.terminal
    Usado por Portais para gestão de terminais
    """
    
    @staticmethod
    def listar_terminais_loja(loja_id: int) -> List[Dict[str, Any]]:
        """
        Lista terminais de uma loja
        
        Args:
            loja_id: ID da loja
        
        Returns:
            Lista de terminais
        """
        try:
            sql = """
                SELECT 
                    id,
                    loja_id,
                    serial_number,
                    modelo,
                    ativo,
                    created_at
                FROM terminal
                WHERE loja_id = %s
                ORDER BY created_at DESC
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, [loja_id])
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao listar terminais: {str(e)}", nivel='ERROR')
            return []
    
    @staticmethod
    def obter_terminal(terminal_id: int) -> Optional[Dict[str, Any]]:
        """
        Busca terminal por ID
        
        Args:
            terminal_id: ID do terminal
        
        Returns:
            Dados do terminal ou None
        """
        try:
            sql = """
                SELECT 
                    id,
                    loja_id,
                    serial_number,
                    modelo,
                    ativo,
                    created_at
                FROM terminal
                WHERE id = %s
                LIMIT 1
            """
            
            with connection.cursor() as cursor:
                cursor.execute(sql, [terminal_id])
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
                return None
        
        except Exception as e:
            from wallclub_core.utilitarios.log_control import registrar_log
            registrar_log('comum.database', f"Erro ao obter terminal: {str(e)}", nivel='ERROR')
            return None
