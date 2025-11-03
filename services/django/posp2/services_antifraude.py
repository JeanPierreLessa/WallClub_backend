"""
Integração POSP2 com Risk Engine (Antifraude)
Fase 2 - Semana 14

Intercepta transações POS antes de processar no Pinbank
"""
import requests
import json
from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class AntifraudeIntegrationService:
    """
    Service para integrar POSP2 com engine antifraude
    
    Fluxo:
    1. Antes de processar transação no Pinbank
    2. Chamar /api/antifraude/analyze/
    3. Avaliar decisão (APROVADO/REPROVADO/REVISAO/REQUER_3DS)
    4. Se APROVADO: continua processamento normal
    5. Se REPROVADO: bloqueia transação
    6. Se REVISAO: continua mas marca para revisão manual
    7. Se REQUER_3DS: retorna URL de autenticação
    """
    
    def __init__(self):
        self.riskengine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8004')
        self.enabled = getattr(settings, 'ANTIFRAUDE_ENABLED', False)
        self.timeout = getattr(settings, 'ANTIFRAUDE_TIMEOUT', 5)
        # Usar credenciais POS específicas para transações POS
        self.oauth_client_id = getattr(settings, 'RISK_ENGINE_POS_CLIENT_ID', None)
        self.oauth_client_secret = getattr(settings, 'RISK_ENGINE_POS_CLIENT_SECRET', None)
        self._cached_token = None
        self._token_expires_at = None
    
    def esta_habilitado(self) -> bool:
        """Verifica se integração com antifraude está habilitada"""
        return self.enabled
    
    def analisar_transacao_pos(
        self,
        cpf: str,
        valor: Decimal,
        modalidade: str,
        parcelas: int,
        numero_cartao: Optional[str],
        bandeira: Optional[str],
        terminal: str,
        loja_id: int,
        canal_id: int,
        nsu: Optional[str] = None,
        cliente_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Analisa transação POS no antifraude
        
        Args:
            cpf: CPF do cliente
            valor: Valor da transação
            modalidade: PIX, CREDITO, DEBITO
            parcelas: Número de parcelas
            numero_cartao: Número completo do cartão (opcional)
            bandeira: Bandeira do cartão (VISA, MASTER, etc)
            terminal: ID do terminal POS
            loja_id: ID da loja
            canal_id: ID do canal
            nsu: NSU da transação (opcional)
            cliente_id: ID do cliente (opcional)
        
        Returns:
            {
                'sucesso': bool,
                'permitir_transacao': bool,
                'decisao': str,
                'score_risco': int,
                'motivo': str,
                'transacao_id': str,
                'requer_3ds': bool,
                'dados_3ds': dict (se requer_3ds=True)
            }
        """
        if not self.esta_habilitado():
            registrar_log('posp2.antifraude', 'Antifraude desabilitado - permitindo transação')
            return {
                'sucesso': True,
                'permitir_transacao': True,
                'decisao': 'APROVADO',
                'score_risco': 0,
                'motivo': 'Antifraude desabilitado',
                'transacao_id': None,
                'requer_3ds': False,
                'dados_3ds': None
            }
        
        try:
            registrar_log(
                'posp2.antifraude',
                '=' * 80
            )
            registrar_log(
                'posp2.antifraude',
                '🛡️  INICIANDO ANÁLISE ANTIFRAUDE'
            )
            registrar_log(
                'posp2.antifraude',
                '=' * 80
            )
            
            # Preparar payload
            transaction_id = nsu or f'POS-{datetime.now().strftime("%Y%m%d%H%M%S")}'
            payload = {
                'transaction_id': transaction_id,
                'origem': 'POS',
                'cpf': cpf,
                'cliente_id': cliente_id,
                'valor': float(valor),
                'modalidade': modalidade,
                'parcelas': parcelas,
                'terminal': terminal,
                'loja_id': loja_id,
                'canal_id': canal_id
            }
            
            registrar_log(
                'posp2.antifraude',
                f'📋 DADOS DA TRANSAÇÃO:'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Transaction ID: {transaction_id}'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • CPF: {cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-**'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Valor: R$ {valor:,.2f}'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Modalidade: {modalidade}'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Parcelas: {parcelas}x'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Terminal: {terminal}'
            )
            registrar_log(
                'posp2.antifraude',
                f'   • Loja ID: {loja_id} | Canal ID: {canal_id}'
            )
            
            # Adicionar dados do cartão se disponíveis
            if numero_cartao:
                payload['numero_cartao'] = numero_cartao
                bin_cartao = numero_cartao[:6]
                registrar_log(
                    'posp2.antifraude',
                    f'   • BIN Cartão: {bin_cartao}****'
                )
            if bandeira:
                payload['bandeira'] = bandeira
                registrar_log(
                    'posp2.antifraude',
                    f'   • Bandeira: {bandeira}'
                )
            
            registrar_log(
                'posp2.antifraude',
                f'\n🌐 CHAMANDO API ANTIFRAUDE: {self.riskengine_url}/api/antifraude/analyze/'
            )
            
            # Chamar API antifraude
            response = requests.post(
                f'{self.riskengine_url}/api/antifraude/analyze/',
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                
                registrar_log(
                    'posp2.antifraude',
                    f'✅ Resposta recebida (HTTP 200) em {response.elapsed.total_seconds():.2f}s'
                )
                
                if not data.get('sucesso'):
                    registrar_log(
                        'posp2.antifraude',
                        f'❌ Erro na análise: {data.get("mensagem")}',
                        nivel='ERROR'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'⚠️  FAIL-OPEN: Permitindo transação por segurança operacional'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        '=' * 80
                    )
                    return self._resultado_fallback('Erro na análise antifraude')
                
                decisao = data.get('decisao')
                score = data.get('score_risco', 0)
                motivo = data.get('motivo', '')
                tempo_ms = data.get('tempo_analise_ms', 0)
                regras = data.get('regras_acionadas', [])
                
                registrar_log(
                    'posp2.antifraude',
                    '\n📊RESULTADO DA ANÁLISE:'
                )
                registrar_log(
                    'posp2.antifraude',
                    f'   • Decisão: {decisao}'
                )
                registrar_log(
                    'posp2.antifraude',
                    f'   • Score de Risco: {score}/100'
                )
                registrar_log(
                    'posp2.antifraude',
                    f'   • Motivo: {motivo}'
                )
                registrar_log(
                    'posp2.antifraude',
                    f'   • Tempo de Análise: {tempo_ms}ms'
                )
                
                if regras:
                    registrar_log(
                        'posp2.antifraude',
                        f'\n🚨 REGRAS ACIONADAS ({len(regras)}):'
                    )
                    for i, regra in enumerate(regras, 1):
                        if isinstance(regra, dict):
                            nome = regra.get('nome', 'Desconhecida')
                            pontos = regra.get('pontos', 0)
                            registrar_log(
                                'posp2.antifraude',
                                f'   {i}. {nome} (+{pontos} pontos)'
                            )
                else:
                    registrar_log(
                        'posp2.antifraude',
                        f'\n✅ Nenhuma regra acionada (transação normal)'
                    )
                
                # Avaliar decisão
                permitir = decisao in ['APROVADO', 'REVISAO']
                
                registrar_log(
                    'posp2.antifraude',
                    '\n' + '-' * 80
                )
                
                if decisao == 'APROVADO':
                    registrar_log(
                        'posp2.antifraude',
                        f'✅ TRANSAÇÃO APROVADA - Score baixo ({score}), sem indicácios de fraude'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'➡️  Continuando processamento normal (Pinbank + Cashback)'
                    )
                
                elif decisao == 'REVISAO':
                    registrar_log(
                        'posp2.antifraude',
                        f'⚠️  TRANSAÇÃO EM REVISÃO - Score médio ({score}), revisar manualmente'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'➡️  Processando transação, mas marcada para revisão posterior'
                    )
                
                elif decisao == 'REPROVADO':
                    registrar_log(
                        'posp2.antifraude',
                        f'❌ TRANSAÇÃO REPROVADA - Score alto ({score}) ou blacklist'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'🚫 BLOQUEANDO transação - NÃO será processada no Pinbank',
                        nivel='ERROR'
                    )
                
                elif decisao == 'REQUER_3DS':
                    registrar_log(
                        'posp2.antifraude',
                        f'🔐 REQUER AUTENTICAÇÃO 3DS - Score/valor exigem validação extra'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'📱 Cliente precisará completar desafio do banco emissor'
                    )
                    if data.get('dados_3ds'):
                        auth_id = data['dados_3ds'].get('auth_id')
                        registrar_log(
                            'posp2.antifraude',
                            f'   • Auth ID: {auth_id}'
                        )
                        registrar_log(
                            'posp2.antifraude',
                            f'   • Método: {data["dados_3ds"].get("metodo", "BROWSER")}'
                        )
                
                registrar_log(
                    'posp2.antifraude',
                    '=' * 80
                )
                
                resultado = {
                    'sucesso': True,
                    'permitir_transacao': permitir,
                    'decisao': decisao,
                    'score_risco': score,
                    'motivo': motivo,
                    'transacao_id': data.get('transacao_id'),
                    'requer_3ds': data.get('requer_3ds', False),
                    'dados_3ds': data.get('dados_3ds')
                }
                
                return resultado
            
            else:
                # Log detalhado do erro
                try:
                    error_body = response.json()
                    registrar_log(
                        'posp2.antifraude',
                        f'Erro HTTP ao chamar antifraude: {response.status_code}',
                        nivel='ERROR'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'Response body: {error_body}',
                        nivel='ERROR'
                    )
                except:
                    registrar_log(
                        'posp2.antifraude',
                        f'Erro HTTP ao chamar antifraude: {response.status_code}',
                        nivel='ERROR'
                    )
                    registrar_log(
                        'posp2.antifraude',
                        f'Response text: {response.text[:500]}',
                        nivel='ERROR'
                    )
                return self._resultado_fallback(f'Erro HTTP {response.status_code}')
        
        except requests.Timeout:
            registrar_log('posp2.antifraude', 'Timeout ao chamar antifraude', nivel='ERROR')
            return self._resultado_fallback('Timeout')
        
        except Exception as e:
            registrar_log(
                'posp2.antifraude',
                f'Exceção ao chamar antifraude: {str(e)}',
                nivel='ERROR'
            )
            return self._resultado_fallback(f'Exceção: {str(e)}')
    
    def consultar_decisao(self, transacao_id: str) -> Optional[Dict[str, Any]]:
        """
        Consulta decisão de uma transação no antifraude
        
        Args:
            transacao_id: ID da transação
        
        Returns:
            Dados da decisão ou None se não encontrada
        """
        if not self.esta_habilitado():
            return None
        
        try:
            response = requests.get(
                f'{self.riskengine_url}/api/antifraude/decision/{transacao_id}/',
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            
            return None
        
        except Exception as e:
            registrar_log(
                'posp2.antifraude',
                f'Erro ao consultar decisão: {str(e)}',
                nivel='ERROR'
            )
            return None
    
    def validar_3ds(
        self,
        auth_id: str,
        transacao_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Valida resultado de autenticação 3DS
        
        Args:
            auth_id: ID da autenticação 3DS
            transacao_id: ID da transação (opcional)
        
        Returns:
            {
                'sucesso': bool,
                'autenticado': bool,
                'eci': str,
                'cavv': str,
                'xid': str
            }
        """
        if not self.esta_habilitado():
            return {
                'sucesso': False,
                'autenticado': False,
                'mensagem': 'Antifraude desabilitado'
            }
        
        try:
            payload = {'auth_id': auth_id}
            if transacao_id:
                payload['transacao_id'] = transacao_id
            
            response = requests.post(
                f'{self.riskengine_url}/api/antifraude/validate-3ds/',
                json=payload,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            
            return {
                'sucesso': False,
                'autenticado': False,
                'mensagem': f'Erro HTTP {response.status_code}'
            }
        
        except Exception as e:
            registrar_log(
                'posp2.antifraude',
                f'Erro ao validar 3DS: {str(e)}',
                nivel='ERROR'
            )
            return {
                'sucesso': False,
                'autenticado': False,
                'mensagem': str(e)
            }
    
    def _get_headers(self) -> Dict[str, str]:
        """Retorna headers para requisições HTTP (sem OAuth - rede interna)"""
        return {
            'Content-Type': 'application/json'
        }
    
    def _resultado_fallback(self, motivo: str) -> Dict[str, Any]:
        """
        Resultado fallback em caso de erro (fail-open)
        
        Por segurança do negócio, em caso de erro na análise,
        permitimos a transação para não bloquear operação
        """
        return {
            'sucesso': True,
            'permitir_transacao': True,  # Fail-open
            'decisao': 'APROVADO',
            'score_risco': 50,  # Score neutro
            'motivo': f'Fallback: {motivo}',
            'transacao_id': None,
            'requer_3ds': False,
            'dados_3ds': None
        }


def interceptar_transacao_pos(
    cpf: str,
    valor: Decimal,
    modalidade: str,
    parcelas: int,
    terminal: str,
    loja_id: int,
    canal_id: int,
    numero_cartao: Optional[str] = None,
    bandeira: Optional[str] = None,
    nsu: Optional[str] = None,
    cliente_id: Optional[int] = None
) -> Tuple[bool, Dict[str, Any]]:
    """
    Função auxiliar para interceptar transação POS
    
    Args:
        (mesmos argumentos de analisar_transacao_pos)
    
    Returns:
        (permitir: bool, resultado: dict)
    """
    service = AntifraudeIntegrationService()
    resultado = service.analisar_transacao_pos(
        cpf=cpf,
        valor=valor,
        modalidade=modalidade,
        parcelas=parcelas,
        numero_cartao=numero_cartao,
        bandeira=bandeira,
        terminal=terminal,
        loja_id=loja_id,
        canal_id=canal_id,
        nsu=nsu,
        cliente_id=cliente_id
    )
    
    permitir = resultado.get('permitir_transacao', True)
    return permitir, resultado
