"""
Middleware de Validação de Segurança
Integração com Risk Engine para validar logins
Fase 4 - Semana 23
"""
import requests
import json
import logging
from django.http import JsonResponse
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('wallclub.security')


class SecurityValidationMiddleware(MiddlewareMixin):
    """
    Middleware que valida IP/CPF antes de permitir login
    Integra com Risk Engine via API validate-login
    """
    
    # URLs que devem ser validadas (endpoints de login)
    PROTECTED_URLS = [
        '/oauth/token/',
        '/admin/login/',
        '/lojista/login/',
        '/vendas/login/',
        '/api/login/',
    ]
    
    def process_request(self, request):
        """
        Valida se IP ou CPF está bloqueado antes de processar login
        """
        # Verificar se é uma URL protegida
        if not any(request.path.startswith(url) for url in self.PROTECTED_URLS):
            return None
        
        # Apenas validar em POST (tentativa de login)
        if request.method != 'POST':
            return None
        
        try:
            # Extrair IP do request
            ip = self.get_client_ip(request)
            
            # Extrair CPF do body (se disponível)
            cpf = self.extract_cpf(request)
            
            # Se não temos nem IP nem CPF, permitir (fail-open)
            if not ip and not cpf:
                logger.warning("⚠️ Validação de segurança: IP e CPF não disponíveis")
                return None
            
            # Detectar portal
            portal = self.detect_portal(request)
            
            # Chamar Risk Engine
            is_blocked, block_info = self.validate_with_risk_engine(ip, cpf, portal)
            
            if is_blocked:
                # Bloquear acesso
                logger.warning(
                    f"🚫 Login bloqueado - {block_info['tipo'].upper()}: {block_info.get('valor', 'N/A')} | "
                    f"Portal: {portal} | Motivo: {block_info.get('motivo', 'N/A')[:100]}"
                )
                
                return JsonResponse({
                    'error': 'Acesso bloqueado',
                    'message': 'Seu acesso foi bloqueado por motivos de segurança.',
                    'tipo': block_info['tipo'],
                    'contato': 'Entre em contato com o suporte para mais informações.'
                }, status=403)
            
            # Permitir acesso
            logger.info(f"✅ Validação de segurança OK - IP: {ip} | CPF: {cpf[:3] if cpf else 'N/A'}*** | Portal: {portal}")
            return None
            
        except Exception as e:
            # Em caso de erro, fail-open (permitir acesso)
            logger.error(f"❌ Erro na validação de segurança: {str(e)} - Permitindo acesso (fail-open)")
            return None
    
    def get_client_ip(self, request):
        """
        Extrai IP do cliente considerando proxies
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def extract_cpf(self, request):
        """
        Extrai CPF do body da requisição
        """
        try:
            if request.content_type == 'application/json':
                body = json.loads(request.body)
                # Tentar diferentes campos possíveis
                return body.get('cpf') or body.get('username') or body.get('login')
            elif request.content_type == 'application/x-www-form-urlencoded':
                return request.POST.get('cpf') or request.POST.get('username') or request.POST.get('login')
        except Exception as e:
            logger.debug(f"Não foi possível extrair CPF: {str(e)}")
        return None
    
    def detect_portal(self, request):
        """
        Detecta qual portal está sendo acessado baseado na URL
        """
        path = request.path
        
        if '/admin/' in path:
            return 'admin'
        elif '/lojista/' in path:
            return 'lojista'
        elif '/vendas/' in path:
            return 'vendas'
        elif '/api/' in path or '/oauth/' in path:
            return 'app'
        else:
            return 'web'
    
    def validate_with_risk_engine(self, ip, cpf, portal):
        """
        Chama API do Risk Engine para validar IP/CPF
        
        Returns:
            tuple: (is_blocked: bool, block_info: dict)
        """
        try:
            # URL do Risk Engine
            risk_engine_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
            validate_url = f"{risk_engine_url}/antifraude/validate-login/"
            
            # Token OAuth para autenticação
            oauth_token = self.get_risk_engine_token()
            
            # Payload
            payload = {
                'ip': ip or 'unknown',
                'cpf': cpf or 'unknown',
                'portal': portal
            }
            
            # Headers
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {oauth_token}'
            }
            
            # Fazer request
            response = requests.post(
                validate_url,
                json=payload,
                headers=headers,
                timeout=2  # Timeout curto para não travar
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('bloqueado'):
                    return True, {
                        'tipo': data.get('tipo'),
                        'valor': ip if data.get('tipo') == 'ip' else cpf,
                        'motivo': data.get('motivo'),
                        'bloqueio_id': data.get('bloqueio_id')
                    }
                else:
                    return False, {}
            else:
                logger.warning(f"Risk Engine retornou status {response.status_code}")
                return False, {}
                
        except requests.Timeout:
            logger.warning("⚠️ Timeout ao validar com Risk Engine - Permitindo acesso (fail-open)")
            return False, {}
        except requests.ConnectionError:
            logger.warning("⚠️ Erro de conexão com Risk Engine - Permitindo acesso (fail-open)")
            return False, {}
        except Exception as e:
            logger.error(f"❌ Erro ao validar com Risk Engine: {str(e)} - Permitindo acesso (fail-open)")
            return False, {}
    
    def get_risk_engine_token(self):
        """
        Obtém token OAuth para autenticar com Risk Engine
        Usa cache Redis para não gerar token a cada request
        """
        from django.core.cache import cache
        
        # Tentar obter do cache
        token = cache.get('risk_engine_oauth_token')
        if token:
            return token
        
        try:
            # Gerar novo token
            oauth_url = getattr(settings, 'RISK_ENGINE_URL', 'http://wallclub-riskengine:8000')
            token_url = f"{oauth_url}/oauth/token/"
            
            client_id = getattr(settings, 'RISK_ENGINE_CLIENT_ID', 'wallclub-django')
            client_secret = getattr(settings, 'RISK_ENGINE_CLIENT_SECRET', '')
            
            response = requests.post(
                token_url,
                json={
                    'grant_type': 'client_credentials',
                    'client_id': client_id,
                    'client_secret': client_secret
                },
                timeout=2
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                
                # Armazenar no cache (90% do tempo de expiração)
                cache.set('risk_engine_oauth_token', token, expires_in * 0.9)
                
                return token
            else:
                logger.error(f"Erro ao obter token do Risk Engine: {response.status_code}")
                return ''
                
        except Exception as e:
            logger.error(f"Erro ao gerar token OAuth para Risk Engine: {str(e)}")
            return ''
