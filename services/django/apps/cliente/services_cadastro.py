# apps/cliente/services_cadastro.py
"""
Service para cadastro completo de cliente no app
Data: 27/10/2025
"""

from datetime import datetime
import re
from django.core.cache import cache
from apps.cliente.models import Cliente, ClienteAuth
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms
from wallclub_core.utilitarios.log_control import registrar_log


class CadastroService:
    """Service para cadastro de novos clientes no app"""

    @staticmethod
    def verificar_cpf_cadastro(cpf: str, canal_id: int) -> dict:
        """
        Verifica se CPF existe e retorna dados faltantes

        Args:
            cpf: CPF do cliente
            canal_id: ID do canal

        Returns:
            dict com status e dados necessários
        """
        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF inválido'
                }

            # Verificar se cliente existe
            try:
                cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)

                # Cliente existe - verificar se já completou cadastro
                if cliente.cadastro_completo:
                    registrar_log('apps.cliente',
                        f"CPF já cadastrado: {cpf_limpo[:3]}***")
                    return {
                        'sucesso': False,
                        'mensagem': 'CPF já cadastrado. Faça login ou recupere sua senha.'
                    }

                # Cliente existe mas não completou cadastro
                dados_existentes = {}
                dados_necessarios = []

                if cliente.nome:
                    dados_existentes['nome'] = cliente.nome
                else:
                    dados_necessarios.append('nome')

                if cliente.email:
                    dados_existentes['email'] = cliente.email
                else:
                    dados_necessarios.append('email')

                if cliente.celular:
                    dados_existentes['celular'] = cliente.celular
                else:
                    dados_necessarios.append('celular')

                # Senha sempre necessária
                dados_necessarios.append('senha')

                dados_existentes['cpf'] = cpf_limpo

                registrar_log('apps.cliente',
                    f"Cliente existe sem cadastro completo: {cpf_limpo[:3]}***, ID={cliente.id}")

                return {
                    'sucesso': True,
                    'cliente_existe': True,
                    'cadastro_completo': False,
                    'dados_existentes': dados_existentes,
                    'dados_necessarios': dados_necessarios,
                    'mensagem': 'Complete seu cadastro'
                }

            except Cliente.DoesNotExist:
                # Cliente não existe - consultar Bureau e criar base
                registrar_log('apps.cliente',
                    f"Cliente não existe, consultando Bureau: {cpf_limpo[:3]}***")

                # Consultar Bureau de Crédito
                from wallclub_core.integracoes.bureau_service import BureauService
                from django.core.cache import cache

                cache_key_bureau = f"bureau_{cpf_limpo}_{canal_id}"
                dados_bureau = cache.get(cache_key_bureau)
                if not dados_bureau:
                    dados_bureau = BureauService.consulta_bureau(cpf_limpo)
                    if dados_bureau:
                        cache.set(cache_key_bureau, dados_bureau, 600)  # 10 minutos

                if not dados_bureau:
                    registrar_log('apps.cliente',
                        f"CPF reprovado pelo Bureau: {cpf_limpo[:3]}***")
                    return {
                        'sucesso': False,
                        'mensagem': 'CPF não aprovado pelo Bureau de Crédito. Verifique seus dados.'
                    }

                # Criar cliente base (sem senha, cadastro_completo=FALSE)
                try:
                    cliente = Cliente(
                        cpf=cpf_limpo,
                        canal_id=canal_id,
                        nome=dados_bureau['nome'],
                        nome_mae=dados_bureau.get('mae', ''),
                        dt_nascimento=dados_bureau.get('nascimento') if dados_bureau.get('nascimento') else None,
                        signo=dados_bureau.get('signo', ''),
                        cadastro_completo=False
                    )
                    cliente.save()

                    # Criar registro de autenticação
                    ClienteAuth.objects.create(
                        cliente=cliente,
                        senha_temporaria=False
                    )

                    registrar_log('apps.cliente',
                        f"Cliente base criado via Bureau: {cpf_limpo[:3]}***, ID={cliente.id}")

                    # Retornar dados existentes (do Bureau) + dados necessários
                    dados_existentes = {
                        'nome': cliente.nome,
                        'cpf': cpf_limpo
                    }

                    dados_necessarios = ['email', 'celular', 'senha']

                    return {
                        'sucesso': True,
                        'cliente_existe': True,  # Criado agora
                        'cadastro_completo': False,
                        'dados_existentes': dados_existentes,
                        'dados_necessarios': dados_necessarios,
                        'mensagem': 'Complete seu cadastro'
                    }

                except Exception as e:
                    registrar_log('apps.cliente',
                        f"Erro ao criar cliente base: {str(e)}", nivel='ERROR')
                    return {
                        'sucesso': False,
                        'mensagem': 'Erro ao processar cadastro'
                    }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao verificar CPF cadastro: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao verificar CPF'
            }

    @staticmethod
    def finalizar_cadastro(dados: dict) -> dict:
        """
        Salva dados do cadastro + envia OTP para validação

        Args:
            dados: Dict com cpf, canal_id, nome, email, celular, senha

        Returns:
            dict com resultado
        """
        try:
            cpf = dados.get('cpf')
            canal_id = dados.get('canal_id')
            nome = dados.get('nome')
            email = dados.get('email')
            celular = dados.get('celular')
            senha = dados.get('senha')

            # Validações
            if not cpf or not canal_id or not senha:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF, canal_id e senha são obrigatórios'
                }

            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                return {
                    'sucesso': False,
                    'mensagem': 'CPF inválido'
                }

            # Validar senha forte
            if not CadastroService._validar_senha_forte(senha):
                return {
                    'sucesso': False,
                    'mensagem': 'Senha fraca. Use no mínimo 8 caracteres com letras e números.'
                }

            # Validar email se fornecido
            if email and not CadastroService._validar_email(email):
                return {
                    'sucesso': False,
                    'mensagem': 'Email inválido'
                }

            # Validar celular
            if celular:
                celular_limpo = ''.join(filter(str.isdigit, celular))
                if len(celular_limpo) < 10 or len(celular_limpo) > 11:
                    return {
                        'sucesso': False,
                        'mensagem': 'Celular inválido. Use 10 ou 11 dígitos.'
                    }
            elif not celular:
                return {
                    'sucesso': False,
                    'mensagem': 'Celular é obrigatório'
                }

            # Verificar se cliente existe
            try:
                cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)

                # Atualizar dados faltantes
                if nome:
                    cliente.nome = nome
                if email:
                    cliente.email = email
                if celular:
                    cliente.celular = celular_limpo

                # Atualizar senha
                cliente.set_password(senha)
                cliente.cadastro_iniciado_em = datetime.now()
                cliente.save()

                registrar_log('apps.cliente',
                    f"Dados do cadastro atualizados: {cpf_limpo[:3]}***, ID={cliente.id}")

            except Cliente.DoesNotExist:
                # Criar novo cliente
                if not nome:
                    return {
                        'sucesso': False,
                        'mensagem': 'Nome é obrigatório para novos clientes'
                    }

                cliente = Cliente(
                    cpf=cpf_limpo,
                    canal_id=canal_id,
                    nome=nome,
                    email=email or '',
                    celular=celular_limpo,
                    cadastro_iniciado_em=datetime.now()
                )
                cliente.set_password(senha)
                cliente.save()

                # Criar registro de autenticação
                ClienteAuth.objects.create(
                    cliente=cliente,
                    senha_temporaria=False  # Senha definitiva
                )

                registrar_log('apps.cliente',
                    f"Novo cliente criado: {cpf_limpo[:3]}***, ID={cliente.id}")

            # Gerar e enviar OTP
            codigo_otp = CadastroService._gerar_otp()

            # Salvar OTP no cache (5 minutos)
            cache_key = f"cadastro_otp_{cpf_limpo}"
            cache.set(cache_key, {
                'codigo': codigo_otp,
                'tentativas': 0
            }, 300)  # 5 minutos

            # Enviar OTP via WhatsApp
            from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
            from wallclub_core.integracoes.whatsapp_service import WhatsAppService

            template_whatsapp = MessagesTemplateService.preparar_whatsapp(
                canal_id=canal_id,
                id_template='2fa_login_app',
                codigo=codigo_otp,
                url_ref=codigo_otp
            )

            if template_whatsapp:
                whatsapp_enviado = WhatsAppService.envia_whatsapp(
                    numero_telefone=celular_limpo,
                    canal_id=canal_id,
                    nome_template=template_whatsapp['nome_template'],
                    idioma_template=template_whatsapp['idioma'],
                    parametros_corpo=template_whatsapp['parametros_corpo'],
                    parametros_botao=template_whatsapp.get('parametros_botao')
                )

                if whatsapp_enviado:
                    registrar_log('apps.cliente',
                        f"OTP enviado via WhatsApp: {cpf_limpo[:3]}***")
                else:
                    registrar_log('apps.cliente',
                        f"Falha ao enviar WhatsApp", nivel='WARNING')

            # Mascarar celular para resposta
            celular_mascarado = f"({celular_limpo[:2]}) {celular_limpo[2]}****-{celular_limpo[-4:]}"

            return {
                'sucesso': True,
                'mensagem': 'Código de verificação enviado via WhatsApp',
                'celular_mascarado': celular_mascarado
            }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao finalizar cadastro: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao processar cadastro'
            }

    @staticmethod
    def validar_otp_cadastro(cpf: str, codigo: str, canal_id: int, device_fingerprint: str = None, 
                            ip_address: str = None, user_agent: str = None) -> dict:
        """
        Valida OTP + finaliza cadastro (marca cadastro_completo=TRUE)
        + Registra dispositivo como confiável

        Args:
            cpf: CPF do cliente
            codigo: Código OTP
            canal_id: ID do canal
            device_fingerprint: Fingerprint do dispositivo (opcional)
            ip_address: IP do cliente (opcional)
            user_agent: User agent do cliente (opcional)

        Returns:
            dict com resultado
        """
        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))

            # Buscar OTP no cache
            cache_key = f"cadastro_otp_{cpf_limpo}"
            dados_otp = cache.get(cache_key)

            if not dados_otp:
                return {
                    'sucesso': False,
                    'mensagem': 'Código expirado. Solicite um novo código.'
                }

            # Verificar tentativas
            if dados_otp['tentativas'] >= 3:
                cache.delete(cache_key)
                return {
                    'sucesso': False,
                    'mensagem': 'Número máximo de tentativas excedido. Solicite um novo código.'
                }

            # Validar código
            if dados_otp['codigo'] != codigo:
                dados_otp['tentativas'] += 1
                cache.set(cache_key, dados_otp, 300)

                tentativas_restantes = 3 - dados_otp['tentativas']

                return {
                    'sucesso': False,
                    'mensagem': 'Código inválido',
                    'tentativas_restantes': tentativas_restantes
                }

            # Código válido - marcar cadastro completo
            try:
                cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)
                cliente.cadastro_completo = True
                cliente.cadastro_concluido_em = datetime.now()
                cliente.save()

                # Remover OTP do cache
                cache.delete(cache_key)

                # Registrar dispositivo como confiável (se fornecido)
                if device_fingerprint:
                    from wallclub_core.seguranca.services_device import DeviceManagementService
                    
                    try:
                        DeviceManagementService.registrar_dispositivo(
                            user_id=cliente.id,
                            tipo_usuario='cliente',
                            device_fingerprint=device_fingerprint,
                            ip_address=ip_address or '0.0.0.0',
                            user_agent=user_agent or '',
                            nome_dispositivo='Dispositivo do Cadastro'
                        )
                        registrar_log('apps.cliente',
                            f"✅ Dispositivo registrado no cadastro: cliente={cliente.id}, device={device_fingerprint[:8]}...")
                    except Exception as e:
                        # Não falhar o cadastro se dispositivo não for registrado
                        registrar_log('apps.cliente',
                            f"⚠️ Erro ao registrar dispositivo no cadastro: {str(e)}", nivel='WARNING')

                registrar_log('apps.cliente',
                    f"✅ Cadastro concluído: {cpf_limpo[:3]}***, ID={cliente.id}")

                return {
                    'sucesso': True,
                    'mensagem': 'Cadastro concluído com sucesso! Faça login para acessar sua conta.'
                }

            except Cliente.DoesNotExist:
                return {
                    'sucesso': False,
                    'mensagem': 'Cliente não encontrado'
                }

        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao validar OTP cadastro: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao validar código'
            }

    @staticmethod
    def _gerar_otp() -> str:
        """Gera código OTP de 6 dígitos"""
        import random
        return str(random.randint(100000, 999999))

    @staticmethod
    def _validar_senha_forte(senha: str) -> bool:
        """
        Valida se senha é forte
        Critérios: mínimo 8 caracteres, pelo menos 1 letra e 1 número
        """
        if len(senha) < 8:
            return False

        tem_letra = bool(re.search(r'[a-zA-Z]', senha))
        tem_numero = bool(re.search(r'\d', senha))

        return tem_letra and tem_numero

    @staticmethod
    def _validar_email(email: str) -> bool:
        """Valida formato de email"""
        pattern = r'^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
