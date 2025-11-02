"""
Service para integração com Risk Engine (wallclub-riskengine)
"""
import requests
from decimal import Decimal
from typing import Dict, List, Optional
from wallclub_core.utilitarios.log_control import registrar_log


class AntifraudeService:
    """
    Service para comunicação com Risk Engine
    Container: wallclub-riskengine (porta 8004)
    """

    # URL base do Risk Engine (ajustar conforme ambiente)
    BASE_URL = 'https://riskmanager.wallclub.com.br/api/antifraude'

    @classmethod
    def listar_pendentes(cls) -> Dict:
        """
        Lista transações aguardando revisão manual

        Returns:
            dict: {
                'total': int,
                'pendentes': [...]
            }
        """
        try:
            registrar_log('portais.admin', 'Buscando transações pendentes de revisão antifraude')

            response = requests.get(
                f'{cls.BASE_URL}/revisao/pendentes/',
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                registrar_log('portais.admin', f'Pendentes encontrados: {data.get("total", 0)}')
                return data
            else:
                registrar_log('portais.admin', f'Erro ao buscar pendentes: {response.status_code}', nivel='ERROR')
                return {'total': 0, 'pendentes': []}

        except requests.exceptions.RequestException as e:
            registrar_log('portais.admin', f'Erro de conexão com Risk Engine: {str(e)}', nivel='ERROR')
            return {'total': 0, 'pendentes': [], 'erro_conexao': True}

    @classmethod
    def aprovar_transacao(cls, decisao_id: int, usuario_id: int, observacao: str) -> Dict:
        """
        Aprova transação após revisão manual

        Args:
            decisao_id: ID da decisão no Risk Engine
            usuario_id: ID do usuário que está aprovando
            observacao: Observação da revisão

        Returns:
            dict: Resposta do Risk Engine
        """
        try:
            registrar_log('portais.admin', f'Aprovando transação {decisao_id} - Usuário: {usuario_id}')

            response = requests.post(
                f'{cls.BASE_URL}/revisao/{decisao_id}/aprovar/',
                json={
                    'usuario_id': usuario_id,
                    'observacao': observacao
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                registrar_log('portais.admin', f'Transação {decisao_id} aprovada com sucesso')
                return {'sucesso': True, 'mensagem': data.get('mensagem', 'Transação aprovada')}
            else:
                erro = response.json().get('erro', 'Erro desconhecido')
                registrar_log('portais.admin', f'Erro ao aprovar {decisao_id}: {erro}', nivel='ERROR')
                return {'sucesso': False, 'mensagem': erro}

        except requests.exceptions.RequestException as e:
            registrar_log('portais.admin', f'Erro de conexão ao aprovar: {str(e)}', nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Erro de conexão com Risk Engine'}

    @classmethod
    def reprovar_transacao(cls, decisao_id: int, usuario_id: int, observacao: str) -> Dict:
        """
        Reprova transação após revisão manual

        Args:
            decisao_id: ID da decisão no Risk Engine
            usuario_id: ID do usuário que está reprovando
            observacao: Observação da revisão

        Returns:
            dict: Resposta do Risk Engine
        """
        try:
            registrar_log('portais.admin', f'Reprovando transação {decisao_id} - Usuário: {usuario_id}')

            response = requests.post(
                f'{cls.BASE_URL}/revisao/{decisao_id}/reprovar/',
                json={
                    'usuario_id': usuario_id,
                    'observacao': observacao
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                registrar_log('portais.admin', f'Transação {decisao_id} reprovada')
                return {'sucesso': True, 'mensagem': data.get('mensagem', 'Transação reprovada')}
            else:
                erro = response.json().get('erro', 'Erro desconhecido')
                registrar_log('portais.admin', f'Erro ao reprovar {decisao_id}: {erro}', nivel='ERROR')
                return {'sucesso': False, 'mensagem': erro}

        except requests.exceptions.RequestException as e:
            registrar_log('portais.admin', f'Erro de conexão ao reprovar: {str(e)}', nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Erro de conexão com Risk Engine'}

    @classmethod
    def listar_historico(cls, limit: int = 50) -> Dict:
        """
        Lista histórico de revisões realizadas

        Args:
            limit: Limite de registros

        Returns:
            dict: {
                'total': int,
                'revisoes': [...]
            }
        """
        try:
            registrar_log('portais.admin', f'Buscando histórico de revisões (limit={limit})')

            response = requests.get(
                f'{cls.BASE_URL}/revisao/historico/',
                params={'limit': limit},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                registrar_log('portais.admin', f'Histórico: {data.get("total", 0)} revisões')
                return data
            else:
                registrar_log('portais.admin', f'Erro ao buscar histórico: {response.status_code}', nivel='ERROR')
                return {'total': 0, 'revisoes': []}

        except requests.exceptions.RequestException as e:
            registrar_log('portais.admin', f'Erro de conexão ao buscar histórico: {str(e)}', nivel='ERROR')
            return {'total': 0, 'revisoes': [], 'erro_conexao': True}

    @classmethod
    def obter_metricas_dashboard(cls, dias: int = 7) -> Dict:
        """
        Obtém métricas completas do dashboard do Risk Engine

        Args:
            dias: Número de dias para análise (padrão: 7)

        Returns:
            dict: Métricas agregadas do Risk Engine
        """
        try:
            registrar_log('portais.admin', f'Buscando métricas de antifraude (últimos {dias} dias)')

            response = requests.get(
                f'{cls.BASE_URL}/dashboard/',
                params={'dias': dias},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                registrar_log('portais.admin', f'Dashboard: {data.get("transacoes", {}).get("total", 0)} transações')
                
                # Adicionar pendentes ao retorno
                pendentes = cls.listar_pendentes()
                data['pendentes'] = {
                    'total': pendentes.get('total', 0),
                    'erro_conexao': pendentes.get('erro_conexao', False)
                }
                
                return data
            else:
                registrar_log('portais.admin', f'Erro ao buscar dashboard: {response.status_code}', nivel='ERROR')
                return cls._metricas_vazias()

        except requests.exceptions.RequestException as e:
            registrar_log('portais.admin', f'Erro de conexão ao buscar dashboard: {str(e)}', nivel='ERROR')
            metricas = cls._metricas_vazias()
            metricas['pendentes']['erro_conexao'] = True
            return metricas

    @classmethod
    def _metricas_vazias(cls) -> Dict:
        """
        Retorna estrutura de métricas vazia para fallback
        """
        return {
            'periodo': {'dias': 0, 'data_inicio': '', 'data_fim': ''},
            'transacoes': {'total': 0, 'por_origem': {}},
            'decisoes': {
                'aprovadas': 0,
                'reprovadas': 0,
                'revisao': 0,
                'total': 0,
                'taxa_aprovacao': 0
            },
            'scores': {'medio': 0, 'minimo': 0, 'maximo': 0},
            'performance': {'tempo_medio_ms': 0, 'tempo_p95_ms': 0},
            'blacklist': {'total': 0, 'ativos': 0, 'bloqueios_periodo': 0},
            'whitelist': {'total': 0, 'automaticas': 0, 'manuais': 0, 'vip': 0},
            'regras_top': [],
            'pendentes': {'total': 0, 'erro_conexao': False}
        }
