"""
Serviço de Integração com Risk Engine para Checkout Web
Intercepta transações de checkout antes do processamento
"""
from typing import Dict, Any, Tuple, Optional
from decimal import Decimal
from datetime import datetime
import requests
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class CheckoutAntifraudeService:
    """
    Service para análise antifraude em transações de Checkout Web
    Integra com WallClub Risk Engine
    """
    
    @staticmethod
    def _obter_token_oauth() -> Optional[str]:
        """
        Obtém token OAuth do Risk Engine
        Cache implementado no AntifraudeIntegrationService do POSP2
        """
        if not settings.RISK_ENGINE_POS_CLIENT_ID or not settings.RISK_ENGINE_POS_CLIENT_SECRET:
            registrar_log('checkout.antifraude', '⚠️ Credenciais OAuth não configuradas', nivel='WARNING')
            return None
        
        oauth_url = f"{settings.RISK_ENGINE_URL}/oauth/token/"
        
        try:
            registrar_log('checkout.antifraude', f'🔑 Obtendo token OAuth: {oauth_url}')
            
            response = requests.post(
                oauth_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': settings.RISK_ENGINE_POS_CLIENT_ID,
                    'client_secret': settings.RISK_ENGINE_POS_CLIENT_SECRET
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                registrar_log('checkout.antifraude', f'✅ Token OAuth obtido com sucesso (expira em {expires_in}s)')
                return token
            else:
                registrar_log('checkout.antifraude', f'❌ Erro ao obter token OAuth: HTTP {response.status_code}', nivel='ERROR')
                return None
                
        except Exception as e:
            registrar_log('checkout.antifraude', f'❌ Exceção ao obter token OAuth: {str(e)}', nivel='ERROR')
            return None
    
    @staticmethod
    def analisar_transacao(
        cpf: str,
        valor: Decimal,
        modalidade: str,
        parcelas: int,
        loja_id: int,
        canal_id: int,
        numero_cartao: str = None,
        bandeira: str = None,
        ip_address: str = None,
        user_agent: str = None,
        device_fingerprint: str = None,
        cliente_nome: str = None,
        cliente_email: str = None,
        transaction_id: str = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Analisa transação de checkout no Risk Engine
        
        Args:
            cpf: CPF do cliente
            valor: Valor da transação
            modalidade: PIX, CREDITO, DEBITO
            parcelas: Número de parcelas
            loja_id: ID da loja
            canal_id: ID do canal
            numero_cartao: Número do cartão (opcional)
            bandeira: Bandeira do cartão (opcional)
            ip_address: IP do cliente
            user_agent: User agent do browser
            device_fingerprint: Fingerprint do dispositivo
            cliente_nome: Nome do cliente
            cliente_email: Email do cliente
            transaction_id: ID da transação
        
        Returns:
            Tuple (permitir: bool, resultado: dict)
        """
        # Verificar se antifraude está habilitado
        if not settings.ANTIFRAUDE_ENABLED:
            registrar_log('checkout.antifraude', '⚠️ Antifraude desabilitado - aprovando transação')
            return True, {
                'decisao': 'APROVADO',
                'motivo': 'Antifraude desabilitado',
                'score_risco': 0,
                'requer_3ds': False
            }
        
        # Logs detalhados
        registrar_log('checkout.antifraude', '=' * 80)
        registrar_log('checkout.antifraude', '🛡️  INICIANDO ANÁLISE ANTIFRAUDE - CHECKOUT WEB')
        registrar_log('checkout.antifraude', '=' * 80)
        registrar_log('checkout.antifraude', '📋 DADOS DA TRANSAÇÃO:')
        registrar_log('checkout.antifraude', f'   • Transaction ID: {transaction_id}')
        registrar_log('checkout.antifraude', f'   • CPF: {cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-**')
        registrar_log('checkout.antifraude', f'   • Valor: R$ {valor:.2f}')
        registrar_log('checkout.antifraude', f'   • Modalidade: {modalidade}')
        registrar_log('checkout.antifraude', f'   • Parcelas: {parcelas}x')
        registrar_log('checkout.antifraude', f'   • Loja ID: {loja_id} | Canal ID: {canal_id}')
        
        if numero_cartao:
            bin_cartao = numero_cartao[:6] if len(numero_cartao) >= 6 else None
            registrar_log('checkout.antifraude', f'   • BIN Cartão: {bin_cartao}****')
        if bandeira:
            registrar_log('checkout.antifraude', f'   • Bandeira: {bandeira}')
        if ip_address:
            registrar_log('checkout.antifraude', f'   • IP: {ip_address}')
        if user_agent:
            registrar_log('checkout.antifraude', f'   • User Agent: {user_agent[:50]}...')
        
        registrar_log('checkout.antifraude', '')
        
        # Garantir que transaction_id sempre tenha valor
        if not transaction_id:
            transaction_id = f'CHECKOUT-{datetime.now().strftime("%Y%m%d%H%M%S")}-{cpf[-4:]}'
        
        # Preparar payload
        payload = {
            'transacao_id': transaction_id,
            'origem': 'WEB',
            'cpf': cpf,
            'cliente_nome': cliente_nome,
            'valor': float(valor),
            'modalidade': modalidade,
            'parcelas': parcelas,
            'loja_id': loja_id,
            'canal_id': canal_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'device_fingerprint': device_fingerprint
        }
        
        # Adicionar dados de cartão se disponível
        if numero_cartao:
            payload['numero_cartao'] = numero_cartao
        if bandeira:
            payload['bandeira'] = bandeira
        
        # Obter token OAuth
        token = CheckoutAntifraudeService._obter_token_oauth()
        
        # Chamar API
        api_url = f"{settings.RISK_ENGINE_URL}/api/antifraude/analyze/"
        registrar_log('checkout.antifraude', f'🌐 CHAMANDO API ANTIFRAUDE: {api_url}')
        
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        
        try:
            inicio = datetime.now()
            response = requests.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=settings.ANTIFRAUDE_TIMEOUT
            )
            tempo_ms = int((datetime.now() - inicio).total_seconds() * 1000)
            
            if response.status_code == 200:
                data = response.json()
                registrar_log('checkout.antifraude', f'✅ Resposta recebida (HTTP 200) em {tempo_ms/1000:.2f}s')
                
                decisao = data.get('decisao', 'APROVADO')
                score = data.get('score_risco', 0)
                motivo = data.get('motivo', '')
                regras = data.get('regras_acionadas', [])
                tempo_analise = data.get('tempo_analise_ms', 0)
                
                # Logs de resultado
                registrar_log('checkout.antifraude', '')
                registrar_log('checkout.antifraude', '📊 RESULTADO DA ANÁLISE:')
                registrar_log('checkout.antifraude', f'   • Decisão: {decisao}')
                registrar_log('checkout.antifraude', f'   • Score de Risco: {score}/100')
                registrar_log('checkout.antifraude', f'   • Motivo: {motivo}')
                registrar_log('checkout.antifraude', f'   • Tempo de Análise: {tempo_analise}ms')
                
                if regras:
                    registrar_log('checkout.antifraude', '')
                    registrar_log('checkout.antifraude', f'🚨 REGRAS ACIONADAS ({len(regras)}):')
                    for i, regra in enumerate(regras, 1):
                        nome = regra.get('regra', 'Desconhecida')
                        pontos = regra.get('pontos_adicionados', 0)
                        registrar_log('checkout.antifraude', f'   {i}. {nome} (+{pontos} pontos)')
                
                registrar_log('checkout.antifraude', '')
                registrar_log('checkout.antifraude', '-' * 80)
                
                # Decisão
                if decisao == 'APROVADO':
                    registrar_log('checkout.antifraude', f'✅ TRANSAÇÃO APROVADA - Score baixo ({score}), sem indícios de fraude')
                    registrar_log('checkout.antifraude', '➡️  Continuando processamento (Pinbank)')
                    permitir = True
                elif decisao == 'REPROVADO':
                    registrar_log('checkout.antifraude', f'❌ TRANSAÇÃO REPROVADA - Score alto ({score}), risco de fraude detectado', nivel='WARNING')
                    registrar_log('checkout.antifraude', '🚫 Bloqueando transação')
                    permitir = False
                elif decisao == 'REVISAR':
                    registrar_log('checkout.antifraude', f'⚠️ TRANSAÇÃO EM REVISÃO - Score médio ({score}), requer análise manual', nivel='WARNING')
                    registrar_log('checkout.antifraude', '➡️  Processando mas marcando para revisão')
                    permitir = True
                else:
                    registrar_log('checkout.antifraude', f'❓ Decisão desconhecida: {decisao} - Aprovando por segurança', nivel='WARNING')
                    permitir = True
                
                registrar_log('checkout.antifraude', '=' * 80)
                
                resultado = {
                    'decisao': decisao,
                    'score_risco': score,
                    'motivo': motivo,
                    'transacao_id': data.get('transacao_id'),
                    'requer_3ds': data.get('requer_3ds', False),
                    'dados_3ds': data.get('dados_3ds')
                }
                
                return permitir, resultado
            
            else:
                # Log detalhado do erro
                try:
                    error_body = response.json()
                    registrar_log('checkout.antifraude', f'Erro HTTP ao chamar antifraude: {response.status_code}', nivel='ERROR')
                    registrar_log('checkout.antifraude', f'Response body: {error_body}', nivel='ERROR')
                except:
                    registrar_log('checkout.antifraude', f'Erro HTTP ao chamar antifraude: {response.status_code}', nivel='ERROR')
                    registrar_log('checkout.antifraude', f'Response text: {response.text[:500]}', nivel='ERROR')
                
                # Fail-open: aprova em caso de erro
                return True, {
                    'decisao': 'APROVADO',
                    'motivo': f'Erro HTTP {response.status_code} (fail-open)',
                    'score_risco': 0,
                    'requer_3ds': False
                }
        
        except requests.Timeout:
            registrar_log('checkout.antifraude', 'Timeout ao chamar antifraude', nivel='ERROR')
            return True, {
                'decisao': 'APROVADO',
                'motivo': 'Timeout (fail-open)',
                'score_risco': 0,
                'requer_3ds': False
            }
        
        except Exception as e:
            registrar_log('checkout.antifraude', f'Exceção ao chamar antifraude: {str(e)}', nivel='ERROR')
            return True, {
                'decisao': 'APROVADO',
                'motivo': f'Erro: {str(e)} (fail-open)',
                'score_risco': 0,
                'requer_3ds': False
            }
