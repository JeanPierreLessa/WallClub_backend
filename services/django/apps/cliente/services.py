"""
Services para autenticação de clientes (usuários do APP móvel).
Contém toda a lógica de negócio relacionada à autenticação.
"""
from datetime import datetime, timedelta
from django.db import connection
from django.core.cache import cache
from typing import Dict, Any
import random

from .models import Cliente, ClienteAuth
from wallclub_core.estr_organizacional.canal import Canal
from wallclub_core.integracoes.bureau_service import BureauService
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms
from wallclub_core.utilitarios.log_control import registrar_log
from .services_senha import SenhaService


class ClienteAuthService:
    """Service para autenticação de clientes"""

    @staticmethod
    def cadastrar(cpf, celular, canal_id, email=None):
        """
        Cadastro via POS - apenas para liberar uso de saldo/cashback
        Cliente deve fazer cadastro completo no app para definir senha
        
        Cadastra novo cliente seguindo o fluxo padronizado:
        1. Verifica se CPF já existe no canal
        2. Consulta Bureau de Crédito
        3. Cria cliente com dados do Bureau (SEM SENHA)
        
        Returns:
            dict: {"sucesso": bool, "codigo": int, "mensagem": str}
            Códigos: 0=erro bureau, 1=cadastrado, 2=já existe
        """
        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                registrar_log('apps.cliente', f"CPF inválido no cadastro: {cpf}")
                return {"sucesso": False, "codigo": 0, "mensagem": "CPF inválido"}
            
            
            # Verificar se CPF já existe no canal
            if Cliente.objects.filter(cpf=cpf_limpo, canal_id=canal_id).exists():
                registrar_log('apps.cliente', f"CPF já cadastrado: {cpf_limpo} no canal {canal_id}")
                return {"sucesso": False, "codigo": 2, "mensagem": "CPF já cadastrado neste canal"}
            
            # Consultar Bureau de Crédito (com cache para evitar duplicidade da busca AJAX)
            cache_key_bureau = f"bureau_{cpf_limpo}_{canal_id}"
            dados_bureau = cache.get(cache_key_bureau)
            if not dados_bureau:
                dados_bureau = BureauService.consulta_bureau(cpf_limpo)
                if dados_bureau:
                    cache.set(cache_key_bureau, dados_bureau, 600)  # 10 minutos
            if not dados_bureau:
                registrar_log('apps.cliente', f"CPF reprovado pelo Bureau: {cpf_limpo}")
                return {"sucesso": False, "codigo": 0, "mensagem": "CPF não aprovado pelo Bureau de Crédito"}
            
            # Criar cliente SEM SENHA (será definida no cadastro completo do app)
            # Hash dummy para manter compatibilidade com campo NOT NULL
            from django.contrib.auth.hashers import make_password
            hash_dummy = make_password(None)  # Hash de senha vazia
            
            cliente = Cliente(
                cpf=cpf_limpo,
                canal_id=canal_id,
                nome=dados_bureau['nome'],
                celular=celular,
                email=email or '',
                nome_mae=dados_bureau['mae'],
                dt_nascimento=dados_bureau['nascimento'] if dados_bureau['nascimento'] else None,
                signo=dados_bureau['signo'],
                hash_senha=hash_dummy  # Hash dummy - cliente deve fazer cadastro no app
            )
            cliente.save()
            
            # Criar registro de autenticação
            ClienteAuth.objects.create(
                cliente=cliente,
                senha_temporaria=False,
                last_password_change=None
            )
            
            registrar_log('apps.cliente', 
                f"Cliente cadastrado via POS (sem senha): {cpf_limpo[:3]}***, ID={cliente.id}, Canal={canal_id}")
            
            return {
                "sucesso": True,
                "codigo": 1,
                "mensagem": "Cliente cadastrado com sucesso",
                "cliente_id": cliente.id
            }
            
        except Exception as e:
            registrar_log('apps.cliente', f"Erro no cadastro: {str(e)} - CPF: {cpf}", nivel='ERROR')
            return {"sucesso": False, "codigo": 0, "mensagem": "Erro interno do servidor"}

    @staticmethod
    def obter_dados_cliente(cpf, canal_id):
        """
        Obtém dados do cliente por CPF e canal - OTIMIZADO com cache e ORM
        
        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            
        Returns:
            dict: Dados do cliente ou None se não encontrado
        """
        # Cache por 10 minutos
        cache_key = f"cliente_dados_{cpf}_{canal_id}"
        dados_cache = cache.get(cache_key)
        if dados_cache is not None:
            return dados_cache
        
            
        # OTIMIZAÇÃO: Usar ORM em vez de SQL raw
        try:
            cliente = Cliente.objects.only(
                'nome', 'celular', 'nome_mae', 'dt_nascimento', 'signo'
            ).get(cpf=cpf, canal_id=canal_id)
            
            dados = {
                'nome': cliente.nome,
                'celular': cliente.celular,
                'nome_mae': cliente.nome_mae,
                'dt_nascimento': cliente.dt_nascimento,
                'signo': cliente.signo
            }
            
            # Armazenar no cache
            cache.set(cache_key, dados, 600)  # 10 minutos
            return dados
                
        except Cliente.DoesNotExist:
            # Armazenar resultado negativo no cache (TTL menor)
            cache.set(cache_key, None, 60)  # 1 minuto
            return None
                    
    @staticmethod
    def obter_perfil_cliente(cliente_id):
        """
        Obtém o perfil do cliente (nome, celular e email) por ID - OTIMIZADO com cache e ORM
        
        Args:
            cliente_id (int): ID do cliente
            
        Returns:
            dict: Perfil do cliente com sucesso/dados ou erro
        """
        # Cache por 10 minutos
        cache_key = f"cliente_perfil_{cliente_id}"
        perfil_cache = cache.get(cache_key)
        if perfil_cache is not None:
            return perfil_cache
        
            
        # OTIMIZAÇÃO: Usar ORM em vez de SQL raw
        try:
            cliente = Cliente.objects.only('nome', 'celular', 'email').get(
                id=cliente_id, is_active=True
            )
            
            resultado = {
                'sucesso': True,
                'mensagem': 'Perfil consultado com sucesso',
                'dados': {
                    'nome': cliente.nome,
                    'celular': cliente.celular,
                    'email': cliente.email or ''
                }
            }
            
            
            # Armazenar no cache
            cache.set(cache_key, resultado, 600)  # 10 minutos
            return resultado
                
        except Cliente.DoesNotExist:
            resultado = {
                'sucesso': False,
                'mensagem': 'Cliente não encontrado',
                'dados': None
            }
            
            registrar_log('apps.cliente', f"Cliente não encontrado ID: {cliente_id}")
            
            # Cache resultado negativo (TTL menor)
            cache.set(cache_key, resultado, 60)  # 1 minuto
            return resultado
                    
    @staticmethod
    def atualizar_celular_cliente(cliente_id, novo_celular):
        """
        Atualiza o celular do cliente por ID
        
        Args:
            cliente_id (int): ID do cliente
            novo_celular (str): Novo número de celular
            
        Returns:
            dict: Resultado da operação
        """
        try:
            # Validar formato do celular
            if not ClienteAuthService._validar_celular_brasil(novo_celular):
                return {
                    'sucesso': False,
                    'mensagem': 'Formato de celular inválido. Use formato brasileiro (11 ou 10 dígitos)'
                }
            
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallclub.cliente 
                    SET celular = %s 
                    WHERE id = %s
                """, [novo_celular, cliente_id])
                
                if cursor.rowcount > 0:
                    # Invalidar cache do perfil após atualização
                    cache_key = f"cliente_perfil_{cliente_id}"
                    cache.delete(cache_key)
                    
                    return {
                        'sucesso': True,
                        'mensagem': 'Celular atualizado com sucesso'
                    }
                else:
                    registrar_log('apps.cliente', f"Cliente não encontrado para atualização ID: {cliente_id}")
                    return {
                        'sucesso': False,
                        'mensagem': 'Cliente não encontrado'
                    }
                    
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao atualizar celular: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }

    @staticmethod
    def _validar_celular_brasil(celular):
        """
        Valida formato de celular brasileiro (baseado no PHP original)
        
        Args:
            celular (str): Número de celular
            
        Returns:
            bool: True se válido, False caso contrário
        """
        if not celular:
            return False
            
        # Remover caracteres não numéricos
        numero_limpo = ''.join(filter(str.isdigit, celular))
        
        # Validar tamanho (11 ou 10 dígitos)
        if len(numero_limpo) == 11:
            return True
        elif len(numero_limpo) == 10:
            return True
            
        return False
    
    @staticmethod
    def _get_canal_id_from_marca(marca):
        """
        Busca o canal_id na tabela canal baseado na marca
        """
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM wallclub.canal WHERE marca = %s
                """, [marca])
                resultado = cursor.fetchone()
                
                if resultado:
                    canal_id = resultado[0]
                    return canal_id
                else:
                    return 1  # Valor padrão se não encontrar
                    
        except Exception as e:
            return 1  # Valor padrão em caso de erro

    @staticmethod
    def login(cpf, canal_id, senha=None, firebase_token=None, ip_address=None, request=None):
        """
        Login com validação de senha: valida CPF + SENHA + canal_id, retorna auth_token.
        2FA é obrigatório para obter JWT final.
        
        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            senha (str): Senha do cliente (obrigatória)
            firebase_token (str, optional): Token Firebase para notificações
            ip_address (str, optional): IP do cliente
            request (object, optional): Objeto request do Django
            
        Returns:
            dict: Resultado com auth_token temporário (5min) ou erro
        """
        try:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
            
            # Validar canal_id obrigatório
            if not canal_id:
                return {
                    'sucesso': False,
                    'erro': 'Canal ID é obrigatório'
                }
            
            # NOVO: Validar senha obrigatória
            if not senha:
                return {
                    'sucesso': False,
                    'codigo': 'invalid_request',
                    'mensagem': 'Senha é obrigatória'
                }
            
            # Verificar bloqueio por excesso de tentativas
            from apps.cliente.services_login_persistent import LoginPersistentService
            
            bloqueio = LoginPersistentService.verificar_bloqueio(cpf_limpo)
            
            if bloqueio['bloqueado']:
                tempo_minutos = bloqueio['tempo_restante_segundos'] // 60
                
                mensagem_bloqueio = {
                    'limite_15min_atingido': f'Conta bloqueada por 15 minutos devido a múltiplas tentativas incorretas.',
                    'limite_1h_atingido': f'Conta bloqueada por 1 hora devido a múltiplas tentativas incorretas.',
                    'limite_24h_atingido': 'Conta bloqueada por 24 horas devido a atividade suspeita. Entre em contato com o suporte.'
                }
                
                registrar_log('apps.cliente', 
                    f"Login bloqueado: CPF={cpf_limpo[:3]}***, motivo={bloqueio['motivo']}")
                
                return {
                    'sucesso': False,
                    'codigo': 'account_locked',
                    'mensagem': mensagem_bloqueio.get(bloqueio['motivo'], 'Conta temporariamente bloqueada'),
                    'bloqueio': {
                        'ativo': True,
                        'motivo': bloqueio['motivo'],
                        'bloqueado_ate': bloqueio['bloqueado_ate'].isoformat() if bloqueio['bloqueado_ate'] else None,
                        'retry_after_seconds': bloqueio['tempo_restante_segundos']
                    }
                }
            
            # Rate limiting por CPF (adicional ao controle de tentativas)
            from wallclub_core.seguranca.rate_limiter_2fa import Login2FARateLimiter
            
            allowed, remaining, retry_after = Login2FARateLimiter.check_login_cpf(cpf_limpo)
            if not allowed:
                # Registrar tentativa no banco antes de bloquear
                LoginPersistentService.registrar_tentativa_falha(
                    cpf=cpf_limpo,
                    canal_id=canal_id,
                    motivo_falha='rate_limit_cpf',
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Notificar bloqueio de conta (se cliente existe)
                try:
                    cliente_bloqueado = Cliente.objects.filter(
                        cpf=cpf_limpo,
                        canal_id=canal_id,
                        is_active=True
                    ).first()
                    
                    if cliente_bloqueado:
                        from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                        NotificacaoSegurancaService.notificar_bloqueio_conta(
                            cliente_id=cliente_bloqueado.id,
                            canal_id=cliente_bloqueado.canal_id,
                            celular=cliente_bloqueado.celular,
                            nome=cliente_bloqueado.nome
                        )
                except Exception as e:
                    registrar_log('apps.cliente',
                        f"Erro ao notificar bloqueio (rate limiter): {str(e)}", nivel='WARNING')
                
                return {
                    'sucesso': False,
                    'codigo': 'rate_limit_cpf',
                    'mensagem': 'Muitas tentativas. Conta temporariamente bloqueada.',
                    'bloqueio': {
                        'ativo': True,
                        'motivo': 'rate_limit_cpf',
                        'bloqueado_ate': None,
                        'retry_after_seconds': retry_after
                    }
                }
            
            # Rate limiting por IP
            if ip_address:
                allowed_ip, retry_after_ip = Login2FARateLimiter.check_login_ip(ip_address)
                if not allowed_ip:
                    return {
                        'sucesso': False,
                        'codigo': 'rate_limit_ip',
                        'mensagem': 'Muitas tentativas deste endereço IP.',
                        'bloqueio': {
                            'ativo': True,
                            'motivo': 'rate_limit_ip',
                            'bloqueado_ate': None,
                            'retry_after_seconds': retry_after_ip
                        }
                    }
            
            registrar_log('apps.cliente',
                f"🔍 INICIANDO VALIDAÇÃO LOGIN: CPF={cpf_limpo[:3]}***, Canal={canal_id}, IP={ip_address or 'N/A'}",
                nivel='INFO')
            
            # Buscar cliente por CPF + canal_id
            try:
                cliente = Cliente.objects.get(
                    cpf=cpf_limpo, 
                    canal_id=canal_id, 
                    is_active=True
                )
                registrar_log('apps.cliente',
                    f"  ✓ Cliente encontrado: ID={cliente.id}", nivel='DEBUG')
            except Cliente.DoesNotExist:
                registrar_log('apps.cliente',
                    f"  ✗ CPF não encontrado - REGISTRANDO TENTATIVA FALHA", nivel='WARNING')
                # Registrar tentativa falha (CPF não existe)
                LoginPersistentService.registrar_tentativa_falha(
                    cpf=cpf_limpo,
                    canal_id=canal_id,
                    motivo_falha='cpf_invalido',
                    ip_address=ip_address
                )
                
                registrar_log('apps.cliente', f"CPF não encontrado: {cpf_limpo[:3]}***")
                return {
                    'sucesso': False,
                    'codigo': 'invalid_credentials',
                    'mensagem': 'CPF ou senha incorretos'  # Mensagem genérica por segurança
                }
            
            # NOVO: Verificar se cliente completou cadastro no app
            if not cliente.cadastro_completo:
                registrar_log('apps.cliente', 
                    f"Cliente não completou cadastro: CPF={cpf_limpo[:3]}***, ID={cliente.id}")
                return {
                    'sucesso': False,
                    'codigo': 'incomplete_registration',
                    'mensagem': 'Complete seu cadastro no app antes de fazer login'
                }
            
            # Validar senha
            registrar_log('apps.cliente',
                f"  🔐 Validando senha para cliente_id={cliente.id}", nivel='DEBUG')
            
            if not cliente.check_password(senha):
                registrar_log('apps.cliente',
                    f"  ✗ SENHA INCORRETA - REGISTRANDO TENTATIVA FALHA", nivel='WARNING')
                # Registrar tentativa falha
                resultado_tentativa = LoginPersistentService.registrar_tentativa_falha(
                    cpf=cpf_limpo,
                    canal_id=canal_id,
                    motivo_falha='senha_incorreta',
                    ip_address=ip_address,
                    user_agent=request.META.get('HTTP_USER_AGENT') if request else None
                )
                
                registrar_log('apps.cliente', 
                    f"Senha incorreta: CPF={cpf_limpo[:3]}***, tentativas_15min={resultado_tentativa['tentativas_15min']}")
                
                # Notificar após 3+ tentativas
                if resultado_tentativa['tentativas_15min'] >= 3:
                    try:
                        from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                        NotificacaoSegurancaService.notificar_tentativas_falhas(
                            cliente_id=cliente.id,
                            canal_id=cliente.canal_id,
                            celular=cliente.celular,
                            num_tentativas=resultado_tentativa['tentativas_15min'],
                            nome=cliente.nome
                        )
                    except Exception as e:
                        registrar_log('apps.cliente', 
                            f"Erro ao notificar tentativas falhas: {str(e)}", nivel='WARNING')
                
                # Montar resposta com contador de tentativas
                tentativas_restantes = LoginPersistentService.LIMIT_15MIN - resultado_tentativa['tentativas_15min']
                
                # Se bloqueou agora
                if resultado_tentativa['bloqueado']:
                    tempo_segundos = (resultado_tentativa['bloqueado_ate'] - datetime.now()).total_seconds()
                    
                    # Notificar bloqueio de conta
                    try:
                        from wallclub_core.integracoes.notificacao_seguranca_service import NotificacaoSegurancaService
                        NotificacaoSegurancaService.notificar_bloqueio_conta(
                            cliente_id=cliente.id,
                            canal_id=cliente.canal_id,
                            celular=cliente.celular,
                            nome=cliente.nome
                        )
                    except Exception as e:
                        registrar_log('apps.cliente', 
                            f"Erro ao notificar bloqueio: {str(e)}", nivel='WARNING')
                    
                    return {
                        'sucesso': False,
                        'codigo': 'account_locked',
                        'mensagem': 'Muitas tentativas incorretas. Conta temporariamente bloqueada.',
                        'bloqueio': {
                            'ativo': True,
                            'motivo': resultado_tentativa['motivo'],
                            'bloqueado_ate': resultado_tentativa['bloqueado_ate'].isoformat(),
                            'retry_after_seconds': int(tempo_segundos)
                        }
                    }
                
                # Senha incorreta mas ainda não bloqueou
                return {
                    'sucesso': False,
                    'codigo': 'invalid_credentials',
                    'mensagem': 'CPF ou senha incorretos',
                    'tentativas': {
                        'restantes': max(0, tentativas_restantes),
                        'limite': LoginPersistentService.LIMIT_15MIN,
                        'janela_minutos': 15
                    }
                }
            
            # SENHA VÁLIDA: Registrar sucesso e limpar contadores
            registrar_log('apps.cliente',
                f"  ✅ SENHA VÁLIDA - REGISTRANDO SUCESSO E RESETANDO CONTADORES",
                nivel='INFO')
            
            LoginPersistentService.registrar_tentativa_sucesso(
                cpf=cpf_limpo,
                canal_id=canal_id,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT') if request else None
            )
            
            # CRÍTICO: Resetar também o rate limiter do Redis
            # LoginPersistentService só reseta contadores do banco
            # Mas o rate limiter usa Redis separado
            Login2FARateLimiter.reset_login_attempts(cpf_limpo)
            registrar_log('apps.cliente',
                f"  ✅ Rate limiter Redis resetado para CPF={cpf_limpo[:3]}***",
                nivel='DEBUG')
            
            # Atualizar last_login e firebase_token
            updates = {'last_login': datetime.now()}
            if firebase_token:
                updates['firebase_token'] = firebase_token
            
            Cliente.objects.filter(id=cliente.id).update(**updates)
            
            registrar_log('apps.cliente', f"Login bem-sucedido: CPF={cpf_limpo[:3]}***, cliente_id={cliente.id}")
            
            # Login bem-sucedido: retornar auth_token temporário (5min)
            # JWT final será gerado em /2fa/verificar_necessidade/ ou /2fa/validar_codigo/
            from apps.cliente.jwt_cliente import generate_auth_pending_token
            
            auth_data = generate_auth_pending_token(
                cliente_id=cliente.id,
                cpf=cliente.cpf,
                canal_id=canal_id
            )
            
            if not auth_data:
                registrar_log('apps.cliente', 
                    f"Erro ao gerar auth_token: cliente={cliente.id}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'codigo': 'internal_error',
                    'mensagem': 'Erro ao gerar token de autenticação'
                }
            
            registrar_log('apps.cliente', 
                f"Auth token gerado: cliente={cliente.id}, expira={auth_data['expires_at']}")
            
            return {
                'sucesso': True,
                'codigo': 'success',
                'mensagem': 'Credenciais válidas. Use auth_token para verificar 2FA.',
                'data': {
                    'auth_token': auth_data['auth_token'],
                    'expires_at': auth_data['expires_at'].isoformat()
                }
            }
            
        except Exception as e:
            registrar_log('apps.cliente', f"Erro no login: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'codigo': 'internal_error',
                'erro': 'Erro interno do servidor'
            }

    @staticmethod
    def _buscar_e_migrar_de_cadastro(cpf, senha, canal_id, firebase_token=None, marca_request=None):
        """
        Busca cliente na tabela 'cadastro' legada e migra automaticamente para 'cliente'
        """
        try:
            from django.db import connection
            
            # Buscar na tabela cadastro
            with connection.cursor() as cursor:
                if marca_request is not None:
                    sql = """
                        SELECT id, senha, nome, cpf, celular, token, datahora,
                               nomemae, nascimento, signo, qtd_semapp, marca, 
                               senha_hash, id_estab
                        FROM wclub.cadastro 
                        WHERE cpf = %s AND senha = %s AND marca = %s 
                        LIMIT 1
                    """
                    cursor.execute(sql, [cpf, senha, marca_request])
                else:
                    sql = """
                        SELECT id, senha, nome, cpf, celular, token, datahora,
                               nomemae, nascimento, signo, qtd_semapp, marca, 
                               senha_hash, id_estab
                        FROM wclub.cadastro 
                        WHERE cpf = %s AND senha = %s AND id_estab = %s
                        LIMIT 1
                    """
                    cursor.execute(sql, [cpf, senha, canal_id])
                resultado = cursor.fetchone()
                
                if not resultado:
                    registrar_log('apps.cliente', f"Cliente não encontrado na tabela 'cadastro': {cpf}")
                    return None
                
                # Extrair dados do cadastro
                (id_orig, senha_orig, nome, cpf_orig, celular, token, datahora,
                 nomemae, nascimento, signo, qtd_semapp, marca_orig, 
                 senha_hash, id_estab) = resultado
                
                registrar_log('apps.cliente', f"Cliente encontrado na tabela 'cadastro', migrando: {cpf}")
                
                # Verificar se já existe na tabela cliente (evitar duplicatas)
                # Usar id_estab da tabela cadastro como canal_id
                if Cliente.objects.filter(cpf=cpf, canal_id=id_estab).exists():
                    registrar_log('apps.cliente', f"Cliente já existe na tabela 'cliente': {cpf}")
                    return Cliente.objects.get(cpf=cpf, canal_id=id_estab)
                
                # Migrar dados para a tabela cliente
                from django.contrib.auth.hashers import make_password, check_password
                from datetime import datetime
                
                # Determinar qual senha usar e criptografar
                # CORREÇÃO: Sempre usar senha_orig para evitar hash duplo
                senha_para_usar = senha_orig  # Usar senha original, não hash
                hash_senha = make_password(senha_para_usar)
                
                # Testar se o hash está correto imediatamente
                teste_senha = check_password(senha, hash_senha)
                if not teste_senha:
                    registrar_log('apps.cliente', f"Falha na validação de senha durante migração: {cpf}")
                
                # Converter data de nascimento
                dt_nascimento = ClienteAuthService._converter_data_nascimento(nascimento)
                
                # Converter datahora para datetime
                created_at = datetime.fromtimestamp(datahora) if datahora else datetime.now()
                

                
                # Criar cliente na nova tabela
                # Usar id_estab da tabela cadastro como canal_id
                cliente = Cliente.objects.create(
                    cpf=cpf,
                    canal_id=id_estab,  # ← Usar id_estab da query, não o parâmetro
                    hash_senha=hash_senha,
                    nome=nome,
                    celular=celular,
                    email='',  # Não há email na tabela cadastro
                    firebase_token=firebase_token,
                    nome_mae=nomemae,
                    dt_nascimento=dt_nascimento,
                    signo=signo,
                    qtd_semapp=qtd_semapp,
                    is_active=True,
                    created_at=created_at
                )
                
                # Criar registro de autenticação
                ClienteAuth.objects.create(cliente=cliente)
                
                registrar_log('apps.cliente', f"Cliente migrado automaticamente: {nome} (CPF: {cpf}, Canal: {canal_id})")
                
                return cliente
                
        except Exception as e:
            registrar_log('apps.cliente', f"Erro crítico na migração: {str(e)}", nivel='ERROR')
            registrar_log('apps.cliente', f"Erro ao migrar cliente da tabela cadastro: {str(e)}", nivel='ERROR')
            return None
    
    @staticmethod
    def _converter_data_nascimento(nascimento_str):
        """Converte string de data de nascimento para date"""
        if not nascimento_str:
            return None
            
        try:
            from datetime import datetime
            
            # Limpar string da data
            data_limpa = nascimento_str.strip()
            
            # Formatos possíveis de data
            formatos = [
                '%Y-%m-%dT%H:%M:%SZ',      # 1972-10-15T00:00:00Z
                '%Y-%m-%dT%H:%M:%S',       # 1972-10-15T00:00:00
                '%Y-%m-%d %H:%M:%S',       # 1972-10-15 00:00:00
                '%Y-%m-%d',                # 1972-10-15
                '%d/%m/%Y',                # 15/10/1972
                '%d-%m-%Y',                # 15-10-1972
                '%Y/%m/%d',                # 1972/10/15
            ]
            
            for formato in formatos:
                try:
                    return datetime.strptime(data_limpa, formato).date()
                except ValueError:
                    continue
                    
            # Se nenhum formato funcionou, tentar extrair apenas a parte da data
            if 'T' in data_limpa:
                try:
                    parte_data = data_limpa.split('T')[0]
                    return datetime.strptime(parte_data, '%Y-%m-%d').date()
                except ValueError:
                    pass
                    
            # Se ainda não funcionou, retornar None
            registrar_log('apps.cliente', f"Data de nascimento inválida: {nascimento_str}")
            return None
            
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao converter data {nascimento_str}: {str(e)}")
            return None

    @staticmethod
    def atualizar_email_cliente(cliente_id, novo_email):
        """
        Atualiza o email do cliente por ID
        
        Args:
            cliente_id (int): ID do cliente
            novo_email (str): Novo endereço de email
            
        Returns:
            dict: Resultado da operação
        """
        try:
            # Validar formato do email
            if not ClienteAuthService._validar_email(novo_email):
                return {
                    'sucesso': False,
                    'mensagem': 'Formato de email inválido. Use um email válido'
                }
            
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallclub.cliente 
                    SET email = %s 
                    WHERE id = %s
                """, [novo_email, cliente_id])
                
                if cursor.rowcount > 0:
                    # Invalidar cache do perfil após atualização
                    cache_key = f"cliente_perfil_{cliente_id}"
                    cache.delete(cache_key)
                    
                    return {
                        'sucesso': True,
                        'mensagem': 'Email atualizado com sucesso'
                    }
                else:
                    registrar_log('apps.cliente', f"Cliente não encontrado para atualização de email ID: {cliente_id}")
                    return {
                        'sucesso': False,
                        'mensagem': 'Cliente não encontrado'
                    }
                    
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao atualizar email: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }
    
    @staticmethod
    def _validar_email(email):
        """
        Valida formato de email
        
        Args:
            email (str): Endereço de email
            
        Returns:
            bool: True se válido, False caso contrário
        """
        if not email:
            return False
            
        # Validação básica de email
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def gravar_firebase_token(cliente_id, firebase_token):
        """
        Grava o token Firebase do cliente para notificações push
        
        Args:
            cliente_id (int): ID do cliente
            firebase_token (str): Token Firebase
            
        Returns:
            dict: Resultado da operação
        """
        try:
            if not firebase_token or firebase_token.strip() == '':
                return {
                    'sucesso': False,
                    'mensagem': 'Token Firebase é obrigatório'
                }
            
            
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE wallclub.cliente 
                    SET firebase_token = %s 
                    WHERE id = %s
                """, [firebase_token, cliente_id])
                
                if cursor.rowcount > 0:
                    return {
                        'sucesso': True,
                        'mensagem': 'Token Firebase gravado com sucesso'
                    }
                else:
                    registrar_log('apps.cliente', f"Cliente não encontrado para gravar token Firebase ID: {cliente_id}")
                    return {
                        'sucesso': False,
                        'mensagem': 'Cliente não encontrado'
                    }
                    
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao gravar token Firebase: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno do servidor'
            }
    
    @staticmethod
    def msg_baixar_app(cpf, canal_id):
        """
        Gera nova senha e envia mensagem para baixar o app via WhatsApp/SMS
        
        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            
        Returns:
            dict: Resultado da operação
        """
        try:
            registrar_log('apps.cliente', '========================================')
            registrar_log('apps.cliente', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} cliente.msg_baixar_app')
            registrar_log('apps.cliente', '========================================')
            
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                registrar_log('apps.cliente', f"CPF inválido: {cpf}")
                return {"sucesso": False, "mensagem": "CPF inválido"}
            
            # Buscar cliente
            cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)
            
            # Gerar nova senha aleatória (4 dígitos)
            nova_senha = str(random.randint(1000, 9999))
            
            # Atualizar senha no banco ANTES de enviar
            cliente.set_password(nova_senha)
            cliente.save()
            
            # Marcar senha como temporária no ClienteAuth
            try:
                cliente_auth = ClienteAuth.objects.get(cliente=cliente)
                cliente_auth.senha_temporaria = True
                cliente_auth.save(update_fields=['senha_temporaria'])
            except ClienteAuth.DoesNotExist:
                registrar_log('apps.cliente', f'ClienteAuth não encontrado para cliente={cliente.id}', nivel='WARNING')
            
            # 1. Enviar senha via WhatsApp/SMS
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
            template_senha_whatsapp = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='senha_acesso',
                senha=nova_senha,
                url_ref=nova_senha
            )
            
            whatsapp_senha_enviado = False
            if template_senha_whatsapp:
                whatsapp_senha_enviado = WhatsAppService.envia_whatsapp(
                    numero_telefone=cliente.celular,
                    canal_id=canal_id,
                    nome_template=template_senha_whatsapp['nome_template'],
                    idioma_template=template_senha_whatsapp['idioma'],
                    parametros_corpo=template_senha_whatsapp['parametros_corpo'],
                    parametros_botao=template_senha_whatsapp['parametros_botao']
                )
            
            # SMS senha
            template_senha_sms = MessagesTemplateService.preparar_sms(
                canal_id=canal_id,
                id_template='senha_acesso',
                senha=nova_senha
            )
            
            sms_senha_resultado = {'status': 'failure'}
            if template_senha_sms:
                sms_senha_resultado = enviar_sms(
                    telefone=cliente.celular,
                    mensagem=template_senha_sms['mensagem'],
                    assunto=template_senha_sms['assunto']
                )
            
            # 2. Enviar convite para baixar app (sem parâmetros)
            template_app_whatsapp = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='baixar_app'
            )
            
            whatsapp_app_enviado = False
            if template_app_whatsapp:
                whatsapp_app_enviado = WhatsAppService.envia_whatsapp(
                    numero_telefone=cliente.celular,
                    canal_id=canal_id,
                    nome_template=template_app_whatsapp['nome_template'],
                    idioma_template=template_app_whatsapp['idioma'],
                    parametros_corpo=template_app_whatsapp['parametros_corpo'],
                    parametros_botao=template_app_whatsapp['parametros_botao']
                )
            
            # SMS baixar app (ainda usa senha no SMS)
            template_app_sms = MessagesTemplateService.preparar_sms(
                canal_id=canal_id,
                id_template='baixar_app'
            )
            
            sms_app_resultado = {'status': 'failure'}
            if template_app_sms:
                sms_app_resultado = enviar_sms(
                    telefone=cliente.celular,
                    mensagem=template_app_sms['mensagem'],
                    assunto=template_app_sms['assunto']
                )
            
            # Verificar se pelo menos uma mensagem foi enviada
            alguma_msg_enviada = (
                whatsapp_senha_enviado or 
                whatsapp_app_enviado or 
                sms_senha_resultado.get('status') == 'success' or
                sms_app_resultado.get('status') == 'success'
            )
            
            if not alguma_msg_enviada:
                registrar_log('apps.cliente', f"Falha ao enviar todas as mensagens para CPF: {cpf_limpo}")
                return {"sucesso": False, "mensagem": "Erro ao enviar mensagem"}
            
            registrar_log('apps.cliente', f"Mensagem para baixar app enviada com sucesso - CPF: {cpf_limpo}")
            
            return {
                "sucesso": True,
                "mensagem": "Mensagem enviada via WhatsApp/SMS com nova senha para acessar o app"
            }
            
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente', f"Cliente não encontrado - CPF: {cpf_limpo}, Canal: {canal_id}")
            return {"sucesso": True, "mensagem": "Se o CPF estiver cadastrado, você receberá a mensagem"}
        except Exception as e:
            registrar_log('apps.cliente', f"Erro ao enviar mensagem baixar app: {str(e)}", nivel='ERROR')
            return {"sucesso": False, "mensagem": "Erro interno do servidor"}
    
    @staticmethod
    def obter_cliente_id(cpf: str, canal_id: int) -> Dict[str, Any]:
        """
        Obtém o ID do cliente baseado no CPF e canal.
        
        Args:
            cpf (str): CPF do cliente
            canal_id (int): ID do canal
            
        Returns:
            Dict[str, Any]: Resultado com sucesso/dados ou erro
        """
        registrar_log('apps.cliente', '========================================')
        registrar_log('apps.cliente', f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} cliente.obter_cliente_id')
        registrar_log('apps.cliente', '========================================')
        try:
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            registrar_log('apps.cliente', f"cliente.obter_cliente_id - Buscando cliente - CPF: {cpf_limpo}, Canal: {canal_id}")
            
            cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)
            
            registrar_log('apps.cliente', f"cliente.obter_cliente_id - Cliente encontrado - ID: {cliente.id}")
            
            return {
                "sucesso": True,
                "cliente_id": cliente.id,
                "mensagem": "Cliente encontrado"
            }
            
        except Cliente.DoesNotExist:
            registrar_log('apps.cliente', f"cliente.obter_cliente_id - Cliente não encontrado - CPF: {cpf_limpo}, Canal: {canal_id}")
            return {
                "sucesso": False,
                "cliente_id": None,
                "mensagem": "Cliente não encontrado"
            }
        except Exception as e:
            registrar_log('apps.cliente', f"cliente.obter_cliente_id - Erro ao buscar cliente: {str(e)}", nivel='ERROR')
            return {
                "sucesso": False,
                "cliente_id": None,
                "mensagem": f"Erro interno: {str(e)}"
            }

    @staticmethod
    def excluir_cliente(cliente_id: int) -> Dict[str, Any]:
        """
        Soft delete de cliente (desativa conta e revoga tokens)
        
        Args:
            cliente_id: ID do cliente a ser excluído
            
        Returns:
            dict: {"sucesso": bool, "mensagem": str}
        """
        from django.db import transaction
        from .models import ClienteJWTToken
        
        try:
            with transaction.atomic():
                # Buscar cliente
                try:
                    cliente = Cliente.objects.get(id=cliente_id)
                except Cliente.DoesNotExist:
                    registrar_log('apps.cliente', f"Cliente não encontrado para exclusão: ID={cliente_id}", nivel='WARNING')
                    return {
                        "sucesso": False,
                        "mensagem": "Cliente não encontrado"
                    }
                
                # Verificar se já está inativo
                if not cliente.is_active:
                    registrar_log('apps.cliente', f"Cliente já estava inativo: ID={cliente_id}", nivel='INFO')
                    return {
                        "sucesso": False,
                        "mensagem": "Cliente já está inativo"
                    }
                
                # 1. Desativar cliente
                cliente.is_active = False
                cliente.save(update_fields=['is_active', 'updated_at'])
                
                registrar_log('apps.cliente', 
                    f"Cliente desativado: ID={cliente_id}, CPF={cliente.cpf}, Canal={cliente.canal_id}", 
                    nivel='INFO')
                
                # 2. Revogar todos os tokens JWT ativos
                tokens_revogados = ClienteJWTToken.objects.filter(
                    cliente=cliente,
                    is_active=True
                ).update(
                    is_active=False,
                    revoked_at=datetime.now()
                )
                
                registrar_log('apps.cliente', 
                    f"Tokens JWT revogados: {tokens_revogados} tokens do cliente ID={cliente_id}", 
                    nivel='INFO')
                
                return {
                    "sucesso": True,
                    "mensagem": "Cliente excluído com sucesso",
                    "dados": {
                        "cliente_id": cliente_id,
                        "tokens_revogados": tokens_revogados
                    }
                }
                
        except Exception as e:
            registrar_log('apps.cliente', 
                f"Erro ao excluir cliente ID={cliente_id}: {str(e)}", 
                nivel='ERROR')
            return {
                "sucesso": False,
                "mensagem": "Erro ao excluir cliente"
            }

