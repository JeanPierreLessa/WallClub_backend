"""
Serviços para consultas auxiliares na API Own Financial
- Consulta CNAE/MCC (consultarAtividades)
- Consulta Cestas de Tarifas (consultarCesta)
"""

from typing import Dict, Any, List, Optional
from django.core.cache import cache
from adquirente_own.services import OwnService
from wallclub_core.utilitarios.log_control import registrar_log


class ConsultasOwnService:
    """Serviço para consultas auxiliares na API Own"""

    CACHE_TIMEOUT_CNAE = 3600  # 1 hora
    CACHE_TIMEOUT_CESTAS = 1800  # 30 minutos

    def __init__(self, environment: str = 'LIVE'):
        """
        Inicializa serviço de consultas

        Args:
            environment: 'LIVE' ou 'TEST'
        """
        self.own_service = OwnService(environment=environment)
        self.environment = environment

    def consultar_atividades(self, descricao: Optional[str] = None) -> Dict[str, Any]:
        """
        Consulta atividades CNAE/MCC na API Own

        Endpoint: GET /parceiro/v2/consultarAtividades

        Args:
            descricao: Filtro por descrição (opcional)

        Returns:
            {
                'sucesso': bool,
                'dados': [
                    {
                        'codCnae': str,
                        'descCnae': str,
                        'codMcc': int
                    }
                ]
            }
        """
        try:
            # Verificar cache se não houver filtro
            if not descricao:
                cache_key = f'own_cnae_all_{self.environment}'
                cached = cache.get(cache_key)
                if cached:
                    registrar_log('own.cnae', '✅ CNAE em cache (lista completa)')
                    return {'sucesso': True, 'dados': cached}

            # Obter credenciais
            credenciais = self.own_service.obter_credenciais_white_label(self.environment)
            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais não encontradas'
                }

            # Preparar parâmetros
            params = {}
            if descricao:
                params['descCnae'] = descricao

            # Fazer requisição
            registrar_log('own.cnae', f'🔍 Consultando atividades CNAE/MCC: {descricao or "todas"}')

            resultado = self.own_service.fazer_requisicao_autenticada(
                method='GET',
                endpoint='/parceiro/v2/consultarAtividades',
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope'],
                params=params
            )

            if not resultado.get('sucesso'):
                return resultado

            dados = resultado.get('dados', [])

            # Cachear se for lista completa
            if not descricao and dados:
                cache_key = f'own_cnae_all_{self.environment}'
                cache.set(cache_key, dados, timeout=self.CACHE_TIMEOUT_CNAE)
                registrar_log('own.cnae', f'💾 {len(dados)} atividades CNAE cacheadas')

            registrar_log('own.cnae', f'✅ {len(dados)} atividades encontradas')

            return {
                'sucesso': True,
                'dados': dados
            }

        except Exception as e:
            registrar_log('own.cnae', f'❌ Erro ao consultar atividades: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao consultar atividades: {str(e)}'
            }

    def consultar_cestas(self, nome_cesta: Optional[str] = None) -> Dict[str, Any]:
        """
        Consulta cestas de tarifas na API Own

        Endpoint: GET /parceiro/v2/consultarCesta

        Args:
            nome_cesta: Filtro por nome da cesta (opcional)

        Returns:
            {
                'sucesso': bool,
                'dados': [
                    {
                        'cestaId': int,
                        'nomeCesta': str,
                        'cestaValorId': int,
                        'valor': float,
                        'descricao': str
                    }
                ]
            }
        """
        try:
            # Verificar cache se não houver filtro
            if not nome_cesta:
                cache_key = f'own_cestas_all_{self.environment}'
                cached = cache.get(cache_key)
                if cached:
                    registrar_log('own.cestas', '✅ Cestas em cache (lista completa)')
                    return {'sucesso': True, 'dados': cached}

            # Obter credenciais
            credenciais = self.own_service.obter_credenciais_white_label(self.environment)
            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais não encontradas'
                }

            # Preparar parâmetros
            params = {}
            if nome_cesta:
                params['nomeCesta'] = nome_cesta

            # Fazer requisição
            registrar_log('own.cestas', f'🔍 Consultando cestas de tarifas: {nome_cesta or "todas"}')

            resultado = self.own_service.fazer_requisicao_autenticada(
                method='GET',
                endpoint='/parceiro/v2/consultarCesta',
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope'],
                params=params
            )

            if not resultado.get('sucesso'):
                return resultado

            dados = resultado.get('dados', [])

            # Cachear se for lista completa
            if not nome_cesta and dados:
                cache_key = f'own_cestas_all_{self.environment}'
                cache.set(cache_key, dados, timeout=self.CACHE_TIMEOUT_CESTAS)
                registrar_log('own.cestas', f'💾 {len(dados)} cestas cacheadas')

            registrar_log('own.cestas', f'✅ {len(dados)} cestas encontradas')

            return {
                'sucesso': True,
                'dados': dados
            }

        except Exception as e:
            registrar_log('own.cestas', f'❌ Erro ao consultar cestas: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao consultar cestas: {str(e)}'
            }

    def obter_tarifas_cesta(self, cesta_id: int) -> Dict[str, Any]:
        """
        Obtém todas as tarifas de uma cesta específica

        Args:
            cesta_id: ID da cesta

        Returns:
            {
                'sucesso': bool,
                'cesta_id': int,
                'nome_cesta': str,
                'tarifas': [
                    {
                        'cesta_valor_id': int,
                        'valor': float,
                        'descricao': str
                    }
                ]
            }
        """
        try:
            # Consultar todas as cestas
            resultado = self.consultar_cestas()

            if not resultado.get('sucesso'):
                return resultado

            # Filtrar tarifas da cesta específica
            todas_cestas = resultado.get('dados', [])
            tarifas_cesta = [c for c in todas_cestas if c.get('cestaId') == cesta_id]

            if not tarifas_cesta:
                return {
                    'sucesso': False,
                    'mensagem': f'Cesta {cesta_id} não encontrada'
                }

            # Agrupar tarifas
            nome_cesta = tarifas_cesta[0].get('nomeCesta', '')
            tarifas = [
                {
                    'cesta_valor_id': t.get('cestaValorId'),
                    'valor': t.get('valor'),
                    'descricao': t.get('descricao', '')
                }
                for t in tarifas_cesta
            ]

            registrar_log('own.cestas', f'✅ {len(tarifas)} tarifas encontradas para cesta {cesta_id}')

            return {
                'sucesso': True,
                'cesta_id': cesta_id,
                'nome_cesta': nome_cesta,
                'tarifas': tarifas
            }

        except Exception as e:
            registrar_log('own.cestas', f'❌ Erro ao obter tarifas da cesta: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao obter tarifas: {str(e)}'
            }

    def buscar_cnae_por_descricao(self, descricao: str) -> List[Dict[str, Any]]:
        """
        Busca CNAE por descrição (helper para frontend)

        Args:
            descricao: Texto para buscar

        Returns:
            Lista de atividades encontradas
        """
        resultado = self.consultar_atividades(descricao=descricao)

        if resultado.get('sucesso'):
            return resultado.get('dados', [])

        return []

    def listar_todas_cestas(self) -> List[Dict[str, Any]]:
        """
        Lista todas as cestas disponíveis (helper para frontend)
        Agrupa por cestaId para evitar duplicatas

        Returns:
            Lista de cestas únicas
        """
        resultado = self.consultar_cestas()

        if not resultado.get('sucesso'):
            return []

        # Agrupar por cestaId para evitar duplicatas
        cestas_dict = {}
        for item in resultado.get('dados', []):
            cesta_id = item.get('cestaId')
            if cesta_id and cesta_id not in cestas_dict:
                cestas_dict[cesta_id] = {
                    'cestaId': cesta_id,
                    'nomeCesta': item.get('nomeCesta', '')
                }

        return list(cestas_dict.values())
