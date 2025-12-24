"""
Calculadora de Base Unificada
Processa transações de checkout (Wallet) e POS (Credenciadora)
Herda de CalculadoraBaseGestao e adapta entrada de dados

IMPORTANTE: Não busca dados diretamente nas tabelas
Todos os dados devem ser fornecidos via parâmetros
"""

from typing import Dict, Any
from parametros_wallclub.calculadora_base_gestao import CalculadoraBaseGestao
from wallclub_core.utilitarios.log_control import registrar_log


class CalculadoraBaseUnificada(CalculadoraBaseGestao):
    """
    Calculadora unificada para base de transações
    Aceita dados de:
    - checkout_transactions (Wallet - vendas diretas via pinbankExtratoPOS)
    - transactiondata_pos (Credenciadora - POS)
    
    Herda toda a lógica de cálculo da CalculadoraBaseGestao
    Apenas adapta a entrada de dados e adiciona campo tipo_operacao
    
    REGRA: Não busca dados nas tabelas - tudo deve vir via parâmetros
    """
    
    def calcular_valores_primarios(
        self, 
        dados_linha: Dict[str, Any], 
        tipo_operacao: str,
        info_loja: Dict[str, Any],
        info_canal: Dict[str, Any]
    ):
        """
        Calcula os valores primários baseados nos dados da transação.
        
        Args:
            dados_linha: Dict com TODOS os dados da transação (campos do pinbankExtratoPOS)
            tipo_operacao: 'Wallet' ou 'Credenciadora'
            info_loja: Dict com info da loja (obrigatório)
                - id: ID da loja
                - loja_id: ID da loja (mesmo que id)
                - loja: Nome/razão social
                - cnpj: CNPJ da loja
                - canal_id: ID do canal
            info_canal: Dict com info do canal (obrigatório)
                - id: ID do canal
                - codigo_canal: Código do canal
                - codigo_cliente: Código do cliente
                - key_loja: Key da loja
                - canal: Nome do canal
                - nome: Nome do canal
        
        Returns:
            Dict com valores calculados (índices 0-130) + tipo_operacao
        """
        try:
            log_id = dados_linha.get('NsuOperacao', 'N/A')
            
            # Validar tipo_operacao
            if tipo_operacao not in ['Wallet', 'Credenciadora']:
                raise ValueError(f"tipo_operacao inválido: '{tipo_operacao}'. Use 'Wallet' ou 'Credenciadora'")
            
            registrar_log('parametros_wallclub', f"Iniciando cálculo unificado ({tipo_operacao}) ID: {log_id}")
            
            # Validar que info_loja e info_canal foram fornecidos
            if not info_loja or not isinstance(info_loja, dict):
                raise ValueError("info_loja é obrigatório e deve ser um dict")
            if not info_canal or not isinstance(info_canal, dict):
                raise ValueError("info_canal é obrigatório e deve ser um dict")
            
            # Validar campos obrigatórios de info_loja
            campos_obrigatorios_loja = ['id', 'loja', 'canal_id']
            for campo in campos_obrigatorios_loja:
                if campo not in info_loja:
                    raise ValueError(f"Campo obrigatório '{campo}' não encontrado em info_loja")
            
            # Validar campos obrigatórios de info_canal
            campos_obrigatorios_canal = ['id', 'canal']
            for campo in campos_obrigatorios_canal:
                if campo not in info_canal:
                    raise ValueError(f"Campo obrigatório '{campo}' não encontrado em info_canal")
            
            # Chamar método pai (CalculadoraBaseGestao)
            # Passa tabela='transactiondata_pos' para compatibilidade
            valores = super().calcular_valores_primarios(
                dados_linha,
                tabela='transactiondata_pos',
                info_loja=info_loja,
                info_canal=info_canal
            )
            
            # Adicionar tipo_operacao ao resultado
            valores['tipo_operacao'] = tipo_operacao
            
            registrar_log('parametros_wallclub', f"Cálculo unificado concluído ({tipo_operacao}) ID: {log_id}")
            return valores
            
        except Exception as e:
            registrar_log('parametros_wallclub', f"Erro no cálculo unificado: {str(e)}", nivel='ERROR')
            raise
