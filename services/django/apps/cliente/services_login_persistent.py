"""
Sistema de autenticação persistente com banco + Redis
Substitui LoginAttemptControl (Redis-only)
"""
from datetime import datetime, timedelta
from django.core.cache import cache
from django.db import transaction
from apps.cliente.models import Cliente
from apps.cliente.models_autenticacao import ClienteAutenticacao, TentativaLogin, Bloqueio
from wallclub_core.utilitarios.log_control import registrar_log


class LoginPersistentService:
    """
    Service para controle de tentativas e bloqueios com persistência
    Arquitetura híbrida: Banco (fonte da verdade) + Redis (cache)
    """
    
    # Limites de tentativas
    LIMIT_15MIN = 5
    LIMIT_1H = 10
    LIMIT_24H = 15
    
    # Tempos de bloqueio
    BLOCK_15MIN = 900  # 15 minutos
    BLOCK_1H = 3600    # 1 hora
    BLOCK_24H = 86400  # 24 horas
    
    @classmethod
    def registrar_tentativa_falha(cls, cpf, canal_id, motivo_falha, ip_address=None, user_agent=None, device_fingerprint=None):
        """
        Registra tentativa de login falha
        Retorna dict com bloqueio aplicado ou tentativas restantes
        """
        # LOG CRÍTICO: Rastrear TODAS as chamadas
        import traceback
        stack_info = ''.join(traceback.format_stack()[-4:-1])  # Últimas 3 chamadas
        
        registrar_log('apps.cliente',
            f"🚨 TENTATIVA FALHA REGISTRADA: CPF={cpf[:3]}***, Canal={canal_id}, Motivo={motivo_falha}, IP={ip_address or 'N/A'}\nStack: {stack_info}",
            nivel='WARNING')
        
        try:
            with transaction.atomic():
                # Buscar cliente
                try:
                    cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id, is_active=True)
                    registrar_log('apps.cliente',
                        f"  Cliente encontrado: ID={cliente.id}", nivel='DEBUG')
                except Cliente.DoesNotExist:
                    cliente = None
                    registrar_log('apps.cliente',
                        f"  Cliente NÃO encontrado para CPF={cpf[:3]}***", nivel='DEBUG')
                
                # Buscar ou criar estado de autenticação
                if cliente:
                    autenticacao, created = ClienteAutenticacao.objects.get_or_create(
                        cliente=cliente,
                        defaults={
                            'tentativas_15min': 0,
                            'tentativas_1h': 0,
                            'tentativas_24h': 0
                        }
                    )
                else:
                    # CPF não existe - não criar autenticacao mas registrar tentativa
                    autenticacao = None
                
                # 1. Registrar tentativa no histórico
                tentativa = TentativaLogin.objects.create(
                    cliente=cliente,
                    cpf=cpf,
                    canal_id=canal_id,
                    sucesso=False,
                    motivo_falha=motivo_falha,
                    ip_address=ip_address or '0.0.0.0',
                    user_agent=user_agent or '',
                    endpoint='/api/v1/cliente/login/',
                    device_fingerprint=device_fingerprint,
                    estava_bloqueado=autenticacao.esta_bloqueado() if autenticacao else False,
                    tentativas_antes=autenticacao.tentativas_15min if autenticacao else 0
                )
                
                if not autenticacao:
                    # Cliente não existe, não atualizar contadores
                    return {
                        'bloqueado': False,
                        'tentativas_15min': 0,
                        'tentativas_1h': 0,
                        'tentativas_24h': 0,
                        'motivo': None
                    }
                
                # 2. Atualizar contadores
                antes_15min = autenticacao.tentativas_15min
                antes_1h = autenticacao.tentativas_1h
                antes_24h = autenticacao.tentativas_24h
                
                autenticacao.tentativas_15min += 1
                autenticacao.tentativas_1h += 1
                autenticacao.tentativas_24h += 1
                autenticacao.ultima_tentativa_em = datetime.now()
                if ip_address:
                    autenticacao.ultimo_ip = ip_address
                
                registrar_log('apps.cliente',
                    f"📊 CONTADORES INCREMENTADOS: 15min={antes_15min}→{autenticacao.tentativas_15min}, 1h={antes_1h}→{autenticacao.tentativas_1h}, 24h={antes_24h}→{autenticacao.tentativas_24h}",
                    nivel='WARNING')
                
                # 3. Verificar se deve bloquear
                bloqueado = False
                motivo = None
                tempo_bloqueio = 0
                bloqueado_ate = None
                
                if autenticacao.tentativas_24h >= cls.LIMIT_24H:
                    # 15 tentativas em 24h → Bloqueio 24 horas
                    bloqueado = True
                    motivo = "limite_24h_atingido"
                    tempo_bloqueio = cls.BLOCK_24H
                    bloqueado_ate = datetime.now() + timedelta(seconds=tempo_bloqueio)
                    
                    registrar_log('apps.cliente',
                        f"🚨 BLOQUEIO 24h - CPF={cpf[:3]}*** ({autenticacao.tentativas_24h} tentativas em 24h)")
                    
                elif autenticacao.tentativas_1h >= cls.LIMIT_1H:
                    # 10 tentativas em 1h → Bloqueio 1 hora
                    bloqueado = True
                    motivo = "limite_1h_atingido"
                    tempo_bloqueio = cls.BLOCK_1H
                    bloqueado_ate = datetime.now() + timedelta(seconds=tempo_bloqueio)
                    
                    registrar_log('apps.cliente',
                        f"⚠️ BLOQUEIO 1h - CPF={cpf[:3]}*** ({autenticacao.tentativas_1h} tentativas em 1h)")
                    
                elif autenticacao.tentativas_15min >= cls.LIMIT_15MIN:
                    # 5 tentativas em 15min → Bloqueio 15 minutos
                    bloqueado = True
                    motivo = "limite_15min_atingido"
                    tempo_bloqueio = cls.BLOCK_15MIN
                    bloqueado_ate = datetime.now() + timedelta(seconds=tempo_bloqueio)
                    
                    registrar_log('apps.cliente',
                        f"⏱️ BLOQUEIO 15min - CPF={cpf[:3]}*** ({autenticacao.tentativas_15min} tentativas em 15min)")
                
                # 4. Aplicar bloqueio se necessário
                if bloqueado:
                    autenticacao.bloqueado = True
                    autenticacao.bloqueado_ate = bloqueado_ate
                    autenticacao.bloqueio_motivo = motivo
                    
                    # Registrar bloqueio no histórico
                    bloqueio_obj = Bloqueio.objects.create(
                        cliente=cliente,
                        cpf=cpf,
                        canal_id=canal_id,
                        motivo=motivo,
                        tentativas_antes_bloqueio=autenticacao.tentativas_15min,
                        bloqueado_em=datetime.now(),
                        bloqueado_ate=bloqueado_ate,
                        tempo_bloqueio_segundos=tempo_bloqueio,
                        ip_address=ip_address,
                        ativo=True
                    )
                    
                    # Marcar tentativa que gerou bloqueio
                    tentativa.gerou_bloqueio = True
                    tentativa.save()
                    
                    # Cache Redis
                    cache.set(f"login_blocked:{cpf}", True, tempo_bloqueio)
                
                autenticacao.save()
                
                return {
                    'bloqueado': bloqueado,
                    'tentativas_15min': autenticacao.tentativas_15min,
                    'tentativas_1h': autenticacao.tentativas_1h,
                    'tentativas_24h': autenticacao.tentativas_24h,
                    'motivo': motivo,
                    'bloqueado_ate': bloqueado_ate,
                    'bloqueio_obj': bloqueio_obj if bloqueado else None
                }
                
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao registrar tentativa falha: {str(e)}", nivel='ERROR')
            return {
                'bloqueado': False,
                'tentativas_15min': 0,
                'tentativas_1h': 0,
                'tentativas_24h': 0
            }
    
    @classmethod
    def registrar_tentativa_sucesso(cls, cpf, canal_id, ip_address=None, user_agent=None, device_fingerprint=None):
        """
        Registra tentativa de login bem-sucedida
        Reseta contadores e desbloqueia
        """
        # LOG CRÍTICO: Rastrear TODOS os logins bem-sucedidos
        import traceback
        stack_info = ''.join(traceback.format_stack()[-4:-1])  # Últimas 3 chamadas
        
        registrar_log('apps.cliente',
            f"✅ TENTATIVA SUCESSO REGISTRADA: CPF={cpf[:3]}***, Canal={canal_id}, IP={ip_address or 'N/A'}\nStack: {stack_info}",
            nivel='INFO')
        
        try:
            with transaction.atomic():
                # Buscar cliente
                cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id, is_active=True)
                registrar_log('apps.cliente',
                    f"  Cliente encontrado: ID={cliente.id}", nivel='DEBUG')
                
                # Buscar autenticação
                autenticacao, created = ClienteAutenticacao.objects.get_or_create(
                    cliente=cliente,
                    defaults={
                        'tentativas_15min': 0,
                        'tentativas_1h': 0,
                        'tentativas_24h': 0
                    }
                )
                
                # 1. Registrar tentativa no histórico
                TentativaLogin.objects.create(
                    cliente=cliente,
                    cpf=cpf,
                    canal_id=canal_id,
                    sucesso=True,
                    motivo_falha=None,
                    ip_address=ip_address or '0.0.0.0',
                    user_agent=user_agent or '',
                    endpoint='/api/v1/cliente/login/',
                    device_fingerprint=device_fingerprint,
                    estava_bloqueado=False,
                    tentativas_antes=autenticacao.tentativas_15min
                )
                
                # 2. Resetar contadores
                antes_15min = autenticacao.tentativas_15min
                antes_1h = autenticacao.tentativas_1h
                antes_24h = autenticacao.tentativas_24h
                antes_bloqueado = autenticacao.bloqueado
                
                autenticacao.resetar_tentativas()
                autenticacao.ultima_tentativa_em = datetime.now()
                autenticacao.ultimo_sucesso_em = datetime.now()
                if ip_address:
                    autenticacao.ultimo_ip = ip_address
                autenticacao.save()
                
                registrar_log('apps.cliente',
                    f"🔄 CONTADORES RESETADOS: 15min={antes_15min}→0, 1h={antes_1h}→0, 24h={antes_24h}→0, Bloqueado={antes_bloqueado}→False",
                    nivel='INFO')
                
                # 3. Desbloquear bloqueios ativos
                Bloqueio.objects.filter(
                    cpf=cpf,
                    ativo=True
                ).update(
                    ativo=False,
                    desbloqueado_em=datetime.now(),
                    desbloqueado_por='login_sucesso'
                )
                
                # 4. Limpar cache Redis
                cache.delete(f"login_blocked:{cpf}")
                cache.delete(f"login_attempts_15min:{cpf}")
                cache.delete(f"login_attempts_1h:{cpf}")
                cache.delete(f"login_attempts_24h:{cpf}")
                
                registrar_log('apps.cliente',
                    f"✅ Login sucesso - CPF={cpf[:3]}***, contadores resetados")
                
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente',
                f"Cliente não encontrado ao registrar sucesso: {cpf[:3]}***", nivel='WARNING')
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao registrar tentativa sucesso: {str(e)}", nivel='ERROR')
    
    @classmethod
    def verificar_bloqueio(cls, cpf):
        """
        Verifica se CPF está bloqueado
        Retorna dict com status e informações do bloqueio
        """
        try:
            # 1. Verificar cache Redis (rápido)
            if cache.get(f"login_blocked:{cpf}"):
                registrar_log('apps.cliente',
                    f"Bloqueio encontrado no cache: {cpf[:3]}***")
            
            # 2. Verificar banco (fonte da verdade)
            autenticacao = ClienteAutenticacao.objects.filter(
                cliente__cpf=cpf,
                bloqueado=True,
                bloqueado_ate__gt=datetime.now()
            ).select_related('cliente').first()
            
            if autenticacao:
                tempo_restante = (autenticacao.bloqueado_ate - datetime.now()).total_seconds()
                
                # Reconstruir cache se não existir
                if not cache.get(f"login_blocked:{cpf}"):
                    cache.set(f"login_blocked:{cpf}", True, timeout=int(tempo_restante))
                    registrar_log('apps.cliente',
                        f"Cache Redis reconstruído para: {cpf[:3]}***")
                
                return {
                    'bloqueado': True,
                    'motivo': autenticacao.bloqueio_motivo,
                    'bloqueado_ate': autenticacao.bloqueado_ate,
                    'tempo_restante_segundos': int(tempo_restante)
                }
            
            # Não está bloqueado
            return {
                'bloqueado': False,
                'motivo': None,
                'bloqueado_ate': None,
                'tempo_restante_segundos': 0
            }
            
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao verificar bloqueio: {str(e)}", nivel='ERROR')
            return {
                'bloqueado': False,
                'motivo': None,
                'bloqueado_ate': None,
                'tempo_restante_segundos': 0
            }
    
    @classmethod
    def limpar_tentativas(cls, cpf):
        """
        Limpa contadores de tentativas (usado após login com sucesso)
        """
        try:
            autenticacao = ClienteAutenticacao.objects.filter(
                cliente__cpf=cpf
            ).first()
            
            if autenticacao:
                autenticacao.resetar_tentativas()
                autenticacao.save()
                
                # Limpar cache
                cache.delete(f"login_blocked:{cpf}")
                cache.delete(f"login_attempts_15min:{cpf}")
                cache.delete(f"login_attempts_1h:{cpf}")
                cache.delete(f"login_attempts_24h:{cpf}")
                
                registrar_log('apps.cliente',
                    f"Tentativas limpas: {cpf[:3]}***")
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao limpar tentativas: {str(e)}", nivel='ERROR')
