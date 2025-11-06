"""
Service Layer para Portal de Vendas (Checkout Presencial)
Centraliza toda lógica de negócio do portal de vendas.
"""
from decimal import Decimal
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.db import transaction, models
from django.db.models import Sum, Count, F, Q
from django.db.models.functions import Coalesce
from django.core.cache import cache
from django.apps import apps
from wallclub_core.utilitarios.log_control import registrar_log
from portais.controle_acesso.models import PortalUsuario, PortalPermissao, PortalUsuarioAcesso
from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
from wallclub_core.estr_organizacional.loja import Loja
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms
from checkout.services import CheckoutService


class CheckoutVendasService:
    """
    Service para operações do Portal de Vendas (Checkout Presencial).
    Centraliza autenticação, gestão de clientes, checkout e estatísticas.
    """

    # ============================================================================
    # AUTENTICAÇÃO
    # ============================================================================

    @staticmethod
    def autenticar_vendedor(email: str, senha: str) -> Dict[str, Any]:
        """
        Autentica vendedor no portal de vendas.

        Args:
            email: Email do usuário
            senha: Senha do usuário

        Returns:
            Dict com sucesso, mensagem e dados do usuário (se sucesso)
        """
        try:
            # Buscar usuário
            try:
                usuario = PortalUsuario.objects.prefetch_related('permissoes').get(email=email)
                registrar_log('portais.vendas', f"Usuário encontrado: {usuario.email}, ativo={usuario.ativo}")
            except PortalUsuario.DoesNotExist:
                registrar_log('portais.vendas', f"Usuário não encontrado: {email}", nivel='WARNING')
                return {'sucesso': False, 'mensagem': 'Email ou senha inválidos'}

            # Validar senha
            if not usuario.verificar_senha(senha):
                registrar_log('portais.vendas', f"Senha inválida para: {email}", nivel='WARNING')
                return {'sucesso': False, 'mensagem': 'Email ou senha inválidos'}

            # Validar permissão para portal vendas
            if not usuario.permissoes.filter(portal='vendas').exists():
                registrar_log('portais.vendas', f"Tentativa de login sem permissão vendas: {email}", nivel='WARNING')
                return {'sucesso': False, 'mensagem': 'Acesso negado. Apenas vendedores de checkout.'}

            # Validar usuário ativo
            if not usuario.ativo:
                return {'sucesso': False, 'mensagem': 'Usuário inativo. Contate o administrador.'}

            registrar_log('portais.vendas', f"Login realizado com sucesso: {usuario.email}")

            return {
                'sucesso': True,
                'mensagem': f'Bem-vindo, {usuario.nome}!',
                'usuario': {
                    'id': usuario.id,
                    'nome': usuario.nome,
                    'email': usuario.email,
                }
            }

        except Exception as e:
            registrar_log('portais.vendas', f"Erro no login: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Erro ao processar login'}

    # ============================================================================
    # DASHBOARD E ESTATÍSTICAS
    # ============================================================================

    @staticmethod
    def obter_lojas_vendedor(vendedor_id: int) -> List[Any]:
        """
        Busca lojas vinculadas ao vendedor.

        Args:
            vendedor_id: ID do vendedor (PortalUsuario)

        Returns:
            Lista de lojas acessíveis
        """
        try:
            acessos_loja = PortalUsuarioAcesso.objects.filter(
                usuario_id=vendedor_id,
                entidade_tipo='loja',
                ativo=True
            )
            lojas_ids = [acesso.entidade_id for acesso in acessos_loja]
            return HierarquiaOrganizacionalService.filtrar_lojas_por_ids(lojas_ids)
        except Exception as e:
            registrar_log('portais.vendas', f"Erro ao buscar lojas do vendedor {vendedor_id}: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def obter_estatisticas_dashboard(vendedor_id: int) -> Dict[str, Any]:
        """
        Calcula estatísticas do dashboard (vendas aprovadas e captadas).

        Args:
            vendedor_id: ID do vendedor

        Returns:
            Dict com estatísticas de vendas hoje/mês (aprovadas e captadas)
        """
        try:
            # Lazy import
            CheckoutTransaction = apps.get_model('checkout', 'CheckoutTransaction')
            
            # Obter lojas que o vendedor tem acesso
            acessos = PortalUsuarioAcesso.objects.filter(
                usuario_id=vendedor_id, entidade_tipo='loja', ativo=True
            )
            lojas_ids = [acesso.entidade_id for acesso in acessos]
            
            if not lojas_ids:
                return CheckoutVendasService._estatisticas_vazias()
            
            hoje = datetime.now().date()
            inicio_mes = hoje.replace(day=1)

            # Base query: transações aprovadas das lojas do vendedor
            vendas_base = CheckoutTransaction.objects.filter(
                loja_id__in=lojas_ids,
                status='APROVADA'
            )

            # Vendas APROVADAS de hoje
            vendas_hoje = vendas_base.filter(
                processed_at__date=hoje
            ).aggregate(
                quantidade=Count('id'),
                valor_total=Sum(Coalesce(F('valor_transacao_final'), F('valor_transacao_original')))
            )

            # Vendas APROVADAS do mês
            vendas_mes = vendas_base.filter(
                processed_at__date__gte=inicio_mes
            ).aggregate(
                quantidade=Count('id'),
                valor_total=Sum(Coalesce(F('valor_transacao_final'), F('valor_transacao_original')))
            )

            # Vendas CAPTADAS (todas as transações, independente do status)
            captadas_base = CheckoutTransaction.objects.filter(
                loja_id__in=lojas_ids
            )

            # Vendas CAPTADAS de hoje
            captadas_hoje = captadas_base.filter(
                created_at__date=hoje
            ).aggregate(
                quantidade=Count('id'),
                valor_total=Sum('valor_transacao_original')
            )

            # Vendas CAPTADAS do mês
            captadas_mes = captadas_base.filter(
                created_at__date__gte=inicio_mes
            ).aggregate(
                quantidade=Count('id'),
                valor_total=Sum('valor_transacao_original')
            )

            return {
                'vendas_hoje': {
                    'quantidade': vendas_hoje['quantidade'] or 0,
                    'valor_total': vendas_hoje['valor_total'] or Decimal('0.00'),
                },
                'vendas_mes': {
                    'quantidade': vendas_mes['quantidade'] or 0,
                    'valor_total': vendas_mes['valor_total'] or Decimal('0.00'),
                },
                'captadas_hoje': {
                    'quantidade': captadas_hoje['quantidade'] or 0,
                    'valor_total': captadas_hoje['valor_total'] or Decimal('0.00'),
                },
                'captadas_mes': {
                    'quantidade': captadas_mes['quantidade'] or 0,
                    'valor_total': captadas_mes['valor_total'] or Decimal('0.00'),
                },
            }

        except Exception as e:
            registrar_log('portais.vendas', f"Erro ao calcular estatísticas dashboard: {str(e)}", nivel='ERROR')
            return CheckoutVendasService._estatisticas_vazias()

    @staticmethod
    def _estatisticas_vazias() -> Dict[str, Any]:
        """Retorna estrutura de estatísticas vazias"""
        return {
            'vendas_hoje': {'quantidade': 0, 'valor_total': Decimal('0.00')},
            'vendas_mes': {'quantidade': 0, 'valor_total': Decimal('0.00')},
            'captadas_hoje': {'quantidade': 0, 'valor_total': Decimal('0.00')},
            'captadas_mes': {'quantidade': 0, 'valor_total': Decimal('0.00')},
        }

    # ============================================================================
    # GESTÃO DE CLIENTES
    # ============================================================================

    @staticmethod
    @transaction.atomic
    def criar_cliente_checkout(
        loja_id: int,
        tipo_documento: str,
        dados: Dict[str, str],
        ip_address: str,
        user_agent: str
    ) -> Dict[str, Any]:
        """
        Cria cliente no checkout com integração ao app (Bureau + envio de senha).
        """
        try:
            canal_id = None
            try:
                loja = HierarquiaOrganizacionalService.get_loja(loja_id)
                canal_id = loja.canal_id if loja else None
            except Exception as e_loja:
                registrar_log('portais.vendas', f"Erro ao obter loja {loja_id}: {str(e_loja)}", nivel='WARNING')

            # Processar CPF: integração com app/Bureau
            if tipo_documento == 'cpf' and canal_id:
                cpf_limpo = dados.get('cpf', '').replace('.', '').replace('-', '')
                app_cliente = CheckoutVendasService._obter_ou_criar_cliente_app(cpf_limpo, canal_id, dados)

                if app_cliente:
                    dados['nome'] = app_cliente.nome or dados.get('nome')
                    if app_cliente.email and app_cliente.email.strip():
                        dados['email'] = app_cliente.email

            # Lazy import
            from checkout.services import ClienteService
            
            cliente = ClienteService.criar_cliente(
                loja_id=loja_id,
                dados=dados,
                ip_address=ip_address,
                user_agent=user_agent
            )

            registrar_log('portais.vendas', f"Cliente criado: ID={cliente.id}, nome={cliente.nome}")
            return {'sucesso': True, 'mensagem': f'Cliente {cliente.nome} cadastrado!', 'cliente': cliente}

        except Exception as e:
            registrar_log('portais.vendas', f"Erro ao criar cliente: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def _obter_ou_criar_cliente_app(cpf: str, canal_id: int, dados: Dict) -> Optional[Any]:
        """Busca cliente no app; se não existir, cadastra via Bureau."""
        try:
            Cliente = apps.get_model('cliente', 'Cliente')
            
            try:
                app_cliente = Cliente.objects.get(cpf=cpf, canal_id=canal_id, is_active=True)
                registrar_log('portais.vendas', f"Cliente app existe: cpf={cpf[:3]}*** id={app_cliente.id}")
                return app_cliente
            except Cliente.DoesNotExist:
                pass

            # Lazy import do service
            from apps.cliente.services import ClienteAuthService
            
            registrar_log('portais.vendas', f"Cadastrando via Bureau: cpf={cpf[:3]}***")
            resultado = ClienteAuthService.cadastrar(
                cpf=cpf, celular=None, canal_id=canal_id, email=dados.get('email')
            )

            if not resultado or not resultado.get('sucesso'):
                return None

            try:
                return Cliente.objects.get(cpf=cpf, canal_id=canal_id, is_active=True)
            except Cliente.DoesNotExist:
                return None
        except Exception as e:
            registrar_log('portais.vendas', f"Erro obter/criar cliente app: {str(e)}", nivel='ERROR')
            return None

    # Método _enviar_senha_cliente_novo removido:
    # Cliente autogerencia telefone via app no checkout 2FA

    @staticmethod
    def buscar_clientes(vendedor_id: int, busca: Optional[str] = None) -> List[Any]:
        """Busca clientes das lojas do vendedor."""
        try:
            CheckoutCliente = apps.get_model('checkout', 'CheckoutCliente')
            CheckoutClienteTelefone = apps.get_model('link_pagamento_web', 'CheckoutClienteTelefone')
            
            lojas_ids = list(PortalUsuarioAcesso.objects.filter(
                usuario_id=vendedor_id, entidade_tipo='loja', ativo=True
            ).values_list('entidade_id', flat=True))

            registrar_log('portais.vendas', f"Vendedor {vendedor_id} tem acesso às lojas: {lojas_ids}")

            if not lojas_ids:
                registrar_log('portais.vendas', f"Vendedor {vendedor_id} não tem acesso a nenhuma loja", nivel='WARNING')
                return []

            # Query simples sem subquery complexa
            clientes = CheckoutCliente.objects.filter(loja_id__in=lojas_ids).annotate(
                total_cartoes_validos=models.Count('cartoes', filter=Q(cartoes__valido=True))
            )

            total_antes_busca = clientes.count()
            registrar_log('portais.vendas', f"Total clientes antes busca: {total_antes_busca}")

            if busca:
                busca_limpa = busca.replace('.', '').replace('-', '').replace('/', '')
                clientes = clientes.filter(
                    Q(nome__icontains=busca) | Q(cpf=busca_limpa) | Q(cnpj=busca_limpa) | Q(email__icontains=busca)
                )
                registrar_log('portais.vendas', f"Busca '{busca}' encontrou {clientes.count()} clientes")

            resultado = list(clientes.order_by('-created_at'))

            # Buscar telefone ativo de cada cliente (em Python)
            for cliente in resultado:
                if cliente.cpf:
                    telefone_obj = CheckoutClienteTelefone.objects.filter(
                        cpf=cliente.cpf,
                        ativo__in=[1, -1]  # Ativo ou pendente
                    ).order_by('-criado_em').first()

                    if telefone_obj:
                        cliente.celular_ultimos_4 = telefone_obj.telefone[-4:] if len(telefone_obj.telefone) >= 4 else telefone_obj.telefone
                    else:
                        cliente.celular_ultimos_4 = None
                else:
                    cliente.celular_ultimos_4 = None

            registrar_log('portais.vendas', f"Retornando {len(resultado)} clientes")
            return resultado
        except Exception as e:
            registrar_log('portais.vendas', f"Erro buscar clientes: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def buscar_transacoes(
        vendedor_id: int, cpf: Optional[str] = None, status: Optional[str] = None,
        data_inicio: Optional[str] = None, data_fim: Optional[str] = None
    ) -> List[Any]:
        """Busca transações com filtros."""
        try:
            CheckoutTransaction = apps.get_model('checkout', 'CheckoutTransaction')
            
            acessos = PortalUsuarioAcesso.objects.filter(
                usuario_id=vendedor_id, entidade_tipo='loja', ativo=True
            )
            lojas_ids = [acesso.entidade_id for acesso in acessos]

            transacoes = CheckoutTransaction.objects.filter(
                loja_id__in=lojas_ids
            ).select_related('cliente', 'loja').order_by('-created_at')

            if cpf:
                cpf_limpo = cpf.replace('.', '').replace('-', '')
                transacoes = transacoes.filter(Q(cliente__cpf=cpf_limpo) | Q(session__cpf=cpf_limpo))

            if status:
                transacoes = transacoes.filter(status=status)

            if data_inicio:
                try:
                    dt_inicio = datetime.strptime(data_inicio, '%Y-%m-%d')
                    transacoes = transacoes.filter(created_at__gte=dt_inicio)
                except ValueError:
                    pass

            if data_fim:
                try:
                    dt_fim = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                    transacoes = transacoes.filter(created_at__lt=dt_fim)
                except ValueError:
                    pass

            return list(transacoes)
        except Exception as e:
            registrar_log('portais.vendas', f"Erro buscar transações: {str(e)}", nivel='ERROR')
            return []

    # ============================================================================
    # AJAX / UTILITÁRIOS
    # ============================================================================

    @staticmethod
    def buscar_cliente_por_documento(loja_id: int, documento: str) -> Dict[str, Any]:
        """Busca cliente por CPF/CNPJ e retorna com cartões."""
        try:
            documento_limpo = documento.replace('.', '').replace('-', '').replace('/', '')

            # Lazy import
            from checkout.services import ClienteService
            
            if len(documento_limpo) == 11:
                cliente = ClienteService.buscar_cliente(loja_id, cpf=documento_limpo)
            elif len(documento_limpo) == 14:
                cliente = ClienteService.buscar_cliente(loja_id, cnpj=documento_limpo)
            else:
                return {'sucesso': False, 'mensagem': 'Documento inválido'}

            if cliente:
                # Lazy import para evitar erro de undefined
                from checkout.services import CartaoTokenizadoService as CartaoService
                cartoes = CartaoService.listar_cartoes_cliente(cliente.id)
                
                # Buscar telefone ativo do cliente para exibir obfuscado
                telefone_obfuscado = ''
                try:
                    from checkout.link_pagamento_web.models_2fa import CheckoutClienteTelefone
                    cpf_limpo = cliente.cpf.replace('.', '').replace('-', '')
                    telefone_obj = CheckoutClienteTelefone.objects.filter(
                        cpf=cpf_limpo,
                        ativo__in=[1, -1]  # Ativo ou pendente
                    ).first()
                    
                    if telefone_obj:
                        tel = telefone_obj.telefone
                        tel_limpo = tel.replace('(', '').replace(')', '').replace('-', '').replace(' ', '')
                        if len(tel_limpo) >= 10:
                            telefone_obfuscado = f"({tel_limpo[:2]})****{tel_limpo[-4:]}"
                        else:
                            telefone_obfuscado = "****" + tel_limpo[-4:] if len(tel_limpo) >= 4 else tel_limpo
                except Exception:
                    pass
                
                return {
                    'sucesso': True,
                    'cliente': {
                        'id': cliente.id, 'nome': cliente.nome, 'email': cliente.email,
                        'endereco': cliente.endereco,
                        'telefone_obfuscado': telefone_obfuscado,
                    },
                    'cartoes': [{
                        'id': c.id, 'mascarado': c.cartao_mascarado, 'bandeira': c.bandeira,
                        'validade': c.validade, 'apelido': c.apelido or f'{c.bandeira} {c.cartao_mascarado}',
                    } for c in cartoes]
                }
            else:
                return {'sucesso': False, 'mensagem': 'Cliente não encontrado'}
        except Exception as e:
            registrar_log('portais.vendas', f"Erro buscar cliente: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    @staticmethod
    def processar_pagamento_cartao_salvo(
        cliente_id: int,
        cartao_id: int,
        valor_original: Decimal,
        valor_final: Decimal,
        parcelas: int,
        bandeira: str,
        descricao: str,
        ip_address: str,
        user_agent: str,
        pedido_origem: str = None,
        cod_item_origem: str = None,
        vendedor_id: int = None
    ) -> Dict[str, Any]:
        """Processa pagamento com cartão salvo via CheckoutService."""
        try:
            resultado = CheckoutService.processar_pagamento_cartao_tokenizado(
                cliente_id=cliente_id,
                cartao_id=cartao_id,
                valor=valor_final,
                parcelas=parcelas,
                bandeira=bandeira,
                descricao=descricao,
                ip_address=ip_address,
                user_agent=user_agent,
                pedido_origem_loja=pedido_origem,
                cod_item_origem_loja=cod_item_origem,
                portais_usuarios_id=vendedor_id,
                valor_transacao_original=valor_original,
                valor_transacao_final=valor_final
            )
            return resultado
        except Exception as e:
            registrar_log('portais.vendas', f"Erro processar pagamento: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    @staticmethod
    def processar_envio_link_pagamento(
        cliente_id: int,
        loja_id: int,
        valor: Decimal,
        descricao: str,
        pedido_origem: str = None,
        cod_item_origem: str = None,
        vendedor_id: int = None
    ) -> Dict[str, Any]:
        """
        Gera e envia link de pagamento para o cliente via WhatsApp/SMS.
        
        Args:
            cliente_id: ID do cliente checkout
            loja_id: ID da loja
            valor: Valor da transação
            descricao: Descrição do pagamento
            pedido_origem: Número do pedido na loja
            cod_item_origem: Código do item na loja
            vendedor_id: ID do vendedor que gerou o link
            
        Returns:
            Dict com sucesso, mensagem e dados do link gerado
        """
        try:
            # Buscar dados do cliente
            CheckoutCliente = apps.get_model('checkout', 'CheckoutCliente')
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            
            # Buscar telefone ativo do cliente (tabela separada)
            CheckoutClienteTelefone = apps.get_model('link_pagamento_web', 'CheckoutClienteTelefone')
            telefone_obj = None
            telefone = None
            
            if cliente.cpf:
                cpf_limpo = ''.join(filter(str.isdigit, cliente.cpf))
                try:
                    telefone_obj = CheckoutClienteTelefone.objects.filter(
                        cpf=cpf_limpo,
                        ativo=1  # Apenas telefones ativos
                    ).first()
                    if telefone_obj:
                        telefone = telefone_obj.telefone
                except Exception:
                    pass
            
            # Gerar token de checkout
            from checkout.link_pagamento_web.models import CheckoutToken
            from django.conf import settings
            
            token_obj = CheckoutToken.generate_token(
                loja_id=loja_id,
                item_nome=descricao,
                item_valor=valor,
                nome_completo=cliente.nome,
                cpf=cliente.cpf or '',
                celular=telefone or '',
                endereco_completo=cliente.endereco or '',
                created_by=f'Portal Vendas - Vendedor ID {vendedor_id}',
                pedido_origem_loja=pedido_origem
            )
            
            # Gerar URL do link
            base_url = getattr(settings, 'CHECKOUT_BASE_URL', 'https://checkout.wallclub.com.br')
            link_url = f"{base_url}/checkout/{token_obj.token}/"
            
            # Enviar link via WhatsApp/SMS se houver telefone
            if telefone:
                try:
                    # Tentar WhatsApp primeiro
                    WhatsAppService.enviar_link_pagamento(
                        telefone=telefone,
                        nome=cliente.nome,
                        valor=float(valor),
                        link=link_url
                    )
                    registrar_log('portais.vendas', f"Link enviado via WhatsApp para {telefone}")
                except Exception as e:
                    # Fallback para SMS
                    registrar_log('portais.vendas', f"Erro WhatsApp, usando SMS: {str(e)}", nivel='WARNING')
                    mensagem = f"Olá {cliente.nome}! Seu link de pagamento: {link_url}"
                    enviar_sms(telefone, mensagem)
            else:
                registrar_log('portais.vendas', f"Cliente {cliente_id} sem telefone cadastrado", nivel='WARNING')
            
            return {
                'sucesso': True,
                'mensagem': 'Link de pagamento gerado com sucesso!' + (' Enviado via WhatsApp/SMS.' if telefone else ' Cliente sem telefone cadastrado.'),
                'link_url': link_url,
                'token': token_obj.token
            }
            
        except CheckoutCliente.DoesNotExist:
            registrar_log('portais.vendas', f"Cliente {cliente_id} não encontrado", nivel='ERROR')
            return {'sucesso': False, 'mensagem': 'Cliente não encontrado'}
        except Exception as e:
            registrar_log('portais.vendas', f"Erro ao processar envio de link: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao gerar link: {str(e)}'}

    @staticmethod
    def simular_parcelas(valor: float, loja_id: int, bandeira: str = 'MASTERCARD') -> Dict[str, Any]:
        """Simula parcelas usando CheckoutService."""
        try:
            resultado = CheckoutService.simular_parcelas(
                valor=valor, loja_id=loja_id, bandeira=bandeira, wall='S'
            )
            return resultado
        except Exception as e:
            registrar_log('portais.vendas', f"Erro simular parcelas: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    @staticmethod
    def pesquisar_cpf_bureau(cpf: str, loja_id: int) -> Dict[str, Any]:
        """
        Pesquisa CPF seguindo ordem correta:
        1. checkout_cliente (já cadastrado) → redireciona para edição
        2. app cliente → usa nome
        3. Bureau → consulta e usa nome
        """
        try:
            cpf_limpo = cpf.replace('.', '').replace('-', '')

            if not cpf_limpo or len(cpf_limpo) != 11:
                return {'sucesso': False, 'mensagem': 'CPF inválido'}

            # Lazy import
            from checkout.services import ClienteService
            
            # 1. PRIMEIRO: Verificar se já existe em checkout_cliente
            checkout_cliente = ClienteService.buscar_cliente(loja_id, cpf=cpf_limpo)
            if checkout_cliente:
                return {
                    'sucesso': True,
                    'cliente_existe': True,
                    'cliente_id': checkout_cliente.id,
                    'mensagem': f'Cliente {checkout_cliente.nome} já cadastrado. Redirecionando para edição...'
                }
            
            # 2. Buscar canal da loja
            loja = HierarquiaOrganizacionalService.get_loja(loja_id)
            canal_id = loja.canal_id if loja else None

            if not canal_id:
                return {'sucesso': False, 'mensagem': 'Canal da loja não encontrado'}

            # 3. Buscar no app cliente
            Cliente = apps.get_model('cliente', 'Cliente')
            
            try:
                app_cliente = Cliente.objects.get(cpf=cpf_limpo, canal_id=canal_id, is_active=True)
                return {
                    'sucesso': True,
                    'cliente_existe': False,
                    'cliente': {'id': app_cliente.id, 'nome': app_cliente.nome or ''}
                }
            except Cliente.DoesNotExist:
                pass

            # 4. Consultar Bureau
            try:
                from wallclub_core.integracoes.bureau_service import BureauService
                cache_key = f"bureau_{cpf_limpo}_{canal_id}"
                dados_bureau = cache.get(cache_key)

                if not dados_bureau:
                    dados_bureau = BureauService.consulta_bureau(cpf_limpo)
                    if dados_bureau:
                        cache.set(cache_key, dados_bureau, 600)

                if dados_bureau and dados_bureau.get('nome'):
                    return {
                        'sucesso': True,
                        'cliente_existe': False,
                        'cliente': {'id': None, 'nome': dados_bureau.get('nome')}
                    }
                else:
                    return {'sucesso': False, 'mensagem': 'Nome não encontrado no Bureau'}
            except Exception as e:
                registrar_log('portais.vendas', f"Erro Bureau: {str(e)}", nivel='ERROR')
                return {'sucesso': False, 'mensagem': 'Erro ao consultar Bureau'}
        except Exception as e:
            registrar_log('portais.vendas', f"Erro pesquisar CPF: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}

    # ============================================================================
    # RECORRÊNCIA (Fase 5 - Unificação Portal Vendas + Recorrência)
    # ============================================================================

    @staticmethod
    def criar_recorrencia(
        cliente_id: int,
        cartao_tokenizado_id,  # int ou 'novo_cartao'
        descricao: str,
        valor: Decimal,
        tipo_periodicidade: str,
        vendedor_id: int,
        loja_id: int,
        dia_cobranca: int = None,
        mes_cobranca_anual: int = None,
        dia_cobranca_anual: int = None
    ) -> Dict[str, Any]:
        """
        Cria uma recorrência agendada.

        Args:
            cliente_id: ID do CheckoutCliente
            cartao_tokenizado_id: ID do cartão tokenizado ou 'novo_cartao' para enviar link
            descricao: Descrição da cobrança (ex: Mensalidade Academia)
            valor: Valor da cobrança recorrente
            tipo_periodicidade: 'mensal_dia_fixo' ou 'anual_data_fixa'
            vendedor_id: ID do vendedor que criou
            loja_id: ID da loja
            dia_cobranca: Dia do mês (1-31) para mensal_dia_fixo
            mes_cobranca_anual: Mês (1-12) para anual_data_fixa
            dia_cobranca_anual: Dia (1-31) para anual_data_fixa

        Returns:
            Dict com sucesso, mensagem e ID da recorrência criada
        """
        try:
            CheckoutCliente = apps.get_model('checkout', 'CheckoutCliente')
            CheckoutCartaoTokenizado = apps.get_model('checkout', 'CheckoutCartaoTokenizado')
            
            # Validar cliente
            try:
                cliente = CheckoutCliente.objects.get(id=cliente_id, ativo=True)
            except CheckoutCliente.DoesNotExist:
                return {'sucesso': False, 'mensagem': 'Cliente não encontrado ou inativo'}

            # Fluxo 1: Cliente SEM cartão - enviar link para tokenizar
            if cartao_tokenizado_id == 'novo_cartao':
                # Criar recorrência pendente e enviar link de pagamento
                from checkout.models_recorrencia import RecorrenciaAgendada

                with transaction.atomic():
                    recorrencia = RecorrenciaAgendada(
                        cliente=cliente,
                        cartao_tokenizado=None,  # Será preenchido quando cliente tokenizar
                        loja_id=loja_id,
                        vendedor_id=vendedor_id,
                        created_by_vendedor_id=vendedor_id,
                        descricao=descricao,
                        valor_recorrencia=valor,
                        tipo_periodicidade=tipo_periodicidade,
                        dia_cobranca=dia_cobranca,
                        mes_cobranca_anual=mes_cobranca_anual,
                        dia_cobranca_anual=dia_cobranca_anual,
                        status='pendente',  # Aguardando tokenização do cartão
                        tentativas_falhas_consecutivas=0,
                        max_tentativas=3,
                        proxima_cobranca=datetime.now().date()  # Temporário, será recalculado após tokenizar
                    )
                    recorrencia.save()

                    # Enviar link para cliente cadastrar cartão (tokenização)
                    from checkout.link_recorrencia_web.services import RecorrenciaTokenService
                    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService

                    loja = HierarquiaOrganizacionalService.get_loja(loja_id)

                    # Criar token e enviar email via novo service
                    resultado = RecorrenciaTokenService.criar_token_e_enviar_email(
                        recorrencia_id=recorrencia.id,
                        loja_id=loja_id,
                        cliente_nome=cliente.nome,
                        cliente_cpf=cliente.cpf or '',
                        cliente_email=cliente.email,
                        descricao=descricao,
                        valor=valor,
                        loja_nome=loja.razao_social
                    )

                    if resultado['sucesso']:
                        registrar_log(
                            'portais.vendas.recorrencia',
                            f"Recorrência pendente criada: ID={recorrencia.id}, Cliente={cliente.nome}. "
                            f"Link de cadastro enviado para {cliente.email}"
                        )
                        return {
                            'sucesso': True,
                            'mensagem': f'Recorrência criada! Link enviado para {cliente.email} para cadastro do cartão.',
                            'recorrencia_id': recorrencia.id,
                            'link_enviado': True
                        }
                    else:
                        return resultado

            # Fluxo 2: Cliente COM cartão tokenizado
            try:
                cartao = CheckoutCartaoTokenizado.objects.get(
                    id=cartao_tokenizado_id,
                    cliente=cliente,
                    valido=True
                )
            except CheckoutCartaoTokenizado.DoesNotExist:
                return {'sucesso': False, 'mensagem': 'Cartão não encontrado ou inválido'}

            # Validar tipo de periodicidade
            tipos_validos = ['mensal_dia_fixo', 'anual_data_fixa']
            if tipo_periodicidade not in tipos_validos:
                return {'sucesso': False, 'mensagem': f'Tipo de periodicidade inválido. Use: {", ".join(tipos_validos)}'}

            # Validar parâmetros conforme tipo
            if tipo_periodicidade == 'mensal_dia_fixo':
                if not dia_cobranca or dia_cobranca < 1 or dia_cobranca > 31:
                    return {'sucesso': False, 'mensagem': 'Para mensal, informe dia_cobranca entre 1 e 31'}
            elif tipo_periodicidade == 'anual_data_fixa':
                if not mes_cobranca_anual or not dia_cobranca_anual:
                    return {'sucesso': False, 'mensagem': 'Para anual, informe mes_cobranca_anual e dia_cobranca_anual'}
                if mes_cobranca_anual < 1 or mes_cobranca_anual > 12:
                    return {'sucesso': False, 'mensagem': 'mes_cobranca_anual deve estar entre 1 e 12'}
                if dia_cobranca_anual < 1 or dia_cobranca_anual > 31:
                    return {'sucesso': False, 'mensagem': 'dia_cobranca_anual deve estar entre 1 e 31'}

            # Criar recorrência
            from checkout.models_recorrencia import RecorrenciaAgendada

            with transaction.atomic():
                recorrencia = RecorrenciaAgendada(
                    cliente=cliente,
                    cartao_tokenizado=cartao,
                    loja_id=loja_id,
                    vendedor_id=vendedor_id,
                    created_by_vendedor_id=vendedor_id,
                    descricao=descricao,
                    valor_recorrencia=valor,
                    tipo_periodicidade=tipo_periodicidade,
                    dia_cobranca=dia_cobranca,
                    mes_cobranca_anual=mes_cobranca_anual,
                    dia_cobranca_anual=dia_cobranca_anual,
                    status='ativo',
                    tentativas_falhas_consecutivas=0,
                    max_tentativas=3
                )

                # Calcular primeira cobrança
                hoje = datetime.now().date()
                proxima = recorrencia.calcular_proxima_cobranca(hoje)
                proxima = recorrencia.ajustar_para_dia_util(proxima)
                recorrencia.proxima_cobranca = proxima

                recorrencia.save()

            registrar_log(
                'portais.vendas.recorrencia',
                f"Recorrência criada: ID={recorrencia.id}, Cliente={cliente.nome}, "
                f"Tipo={tipo_periodicidade}, Próxima={proxima}"
            )

            return {
                'sucesso': True,
                'mensagem': f'Recorrência {recorrencia.periodicidade_display} criada com sucesso. Próxima cobrança: {proxima.strftime("%d/%m/%Y")}',
                'recorrencia_id': recorrencia.id,
                'proxima_cobranca': proxima.strftime('%Y-%m-%d')
            }

        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao criar recorrência: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao criar recorrência: {str(e)}'}

    @staticmethod
    def listar_recorrencias(
        loja_id: int = None,
        vendedor_id: int = None,
        status: str = None,
        cliente_id: int = None
    ) -> List[Dict[str, Any]]:
        """
        Lista recorrências com filtros opcionais.

        Args:
            loja_id: Filtrar por loja
            vendedor_id: Filtrar por vendedor
            status: ativo, pausado, cancelado, hold, concluido
            cliente_id: Filtrar por cliente

        Returns:
            Lista de dicionários com dados das recorrências
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            queryset = RecorrenciaAgendada.objects.all()

            if loja_id:
                queryset = queryset.filter(loja_id=loja_id)

            if vendedor_id:
                queryset = queryset.filter(vendedor_id=vendedor_id)

            if status:
                queryset = queryset.filter(status=status)

            if cliente_id:
                queryset = queryset.filter(cliente_id=cliente_id)

            recorrencias = queryset.select_related('cliente', 'cartao_tokenizado', 'loja').order_by('-created_at')

            resultado = []
            for rec in recorrencias:
                resultado.append({
                    'id': rec.id,
                    'cliente_nome': rec.cliente.nome if rec.cliente else 'N/A',
                    'cliente_cpf': rec.cliente.cpf if rec.cliente else 'N/A',
                    'valor': float(rec.valor_recorrencia),
                    'periodicidade': rec.periodicidade_display,
                    'proxima_cobranca': rec.proxima_cobranca.strftime('%d/%m/%Y'),
                    'status': rec.get_status_display(),
                    'tentativas_falhas': rec.tentativas_falhas_consecutivas,
                    'total_cobrado': float(rec.total_cobrado),
                    'total_execucoes': rec.total_execucoes,
                    'cartao_mascarado': rec.cartao_tokenizado.cartao_mascarado if rec.cartao_tokenizado else 'N/A',
                    'created_at': rec.created_at.strftime('%d/%m/%Y %H:%M'),
                    'loja_nome': rec.loja.razao_social if rec.loja else 'N/A'
                })

            registrar_log('portais.vendas.recorrencia', f"Listadas {len(resultado)} recorrências")
            return resultado

        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao listar recorrências: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def pausar_recorrencia(recorrencia_id: int, vendedor_id: int) -> Dict[str, Any]:
        """
        Pausa uma recorrência ativa.

        Args:
            recorrencia_id: ID da RecorrenciaAgendada
            vendedor_id: ID do vendedor que está pausando

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)

            if recorrencia.status == 'pausado':
                return {'sucesso': False, 'mensagem': 'Recorrência já está pausada'}

            if recorrencia.status in ['cancelado', 'concluido']:
                return {'sucesso': False, 'mensagem': f'Não é possível pausar recorrência {recorrencia.get_status_display()}'}

            recorrencia.status = 'pausado'
            recorrencia.save(update_fields=['status', 'updated_at'])

            registrar_log(
                'portais.vendas.recorrencia',
                f"Recorrência pausada: ID={recorrencia_id}, Vendedor={vendedor_id}"
            )

            return {'sucesso': True, 'mensagem': 'Recorrência pausada com sucesso'}

        except RecorrenciaAgendada.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Recorrência não encontrada'}
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao pausar recorrência: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao pausar recorrência: {str(e)}'}

    @staticmethod
    def cancelar_recorrencia(recorrencia_id: int, vendedor_id: int) -> Dict[str, Any]:
        """
        Cancela uma recorrência permanentemente.

        Args:
            recorrencia_id: ID da RecorrenciaAgendada
            vendedor_id: ID do vendedor que está cancelando

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)

            if recorrencia.status == 'cancelado':
                return {'sucesso': False, 'mensagem': 'Recorrência já está cancelada'}

            recorrencia.status = 'cancelado'
            recorrencia.save(update_fields=['status', 'updated_at'])

            registrar_log(
                'portais.vendas.recorrencia',
                f"Recorrência cancelada: ID={recorrencia_id}, Vendedor={vendedor_id}"
            )

            return {'sucesso': True, 'mensagem': 'Recorrência cancelada com sucesso'}

        except RecorrenciaAgendada.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Recorrência não encontrada'}
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao cancelar recorrência: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao cancelar recorrência: {str(e)}'}

    @staticmethod
    def processar_cobranca_agendada(recorrencia_id: int) -> Dict[str, Any]:
        """
        Processa uma cobrança recorrente agendada.
        Gera um novo CheckoutTransaction vinculado à recorrência.
        Chamado pelo Celery task.

        Args:
            recorrencia_id: ID da RecorrenciaAgendada

        Returns:
            Dict com sucesso, mensagem e dados da cobrança
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada
            from checkout.services_cartao_controle import CartaoControleService

            recorrencia = RecorrenciaAgendada.objects.select_related(
                'cliente', 'cartao_tokenizado', 'loja'
            ).get(id=recorrencia_id)

            if recorrencia.status != 'ativo':
                return {
                    'sucesso': False,
                    'mensagem': f'Recorrência não está ativa. Status: {recorrencia.get_status_display()}'
                }
            
            # Validar se cartão está válido antes de processar
            if not recorrencia.cartao_tokenizado.valido:
                registrar_log(
                    'portais.vendas.recorrencia',
                    f"Cartão inválido: Recorrencia_ID={recorrencia_id}, "
                    f"Cartao_ID={recorrencia.cartao_tokenizado_id}, "
                    f"Motivo={recorrencia.cartao_tokenizado.motivo_invalidacao}",
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': f'Cartão inválido: {recorrencia.cartao_tokenizado.motivo_invalidacao}',
                    'cartao_invalido': True
                }

            # Processar cobrança via CheckoutService (usa cartão tokenizado)
            resultado = CheckoutService.processar_pagamento_com_cartao_tokenizado(
                cartao_tokenizado_id=recorrencia.cartao_tokenizado_id,
                valor=float(recorrencia.valor_recorrencia),
                parcelas=1,
                vendedor_id=recorrencia.vendedor_id,
                loja_id=recorrencia.loja_id,
                ip_address='0.0.0.0',  # Sistema automático
                user_agent='Celery/RecorrenciaTask'
            )

            # Buscar a transação criada e vincular à recorrência
            if resultado.get('sucesso') and resultado.get('transacao_id'):
                # Vincular transação à recorrência
                from checkout.models import CheckoutTransaction
                transacao = CheckoutTransaction.objects.get(id=resultado['transacao_id'])
                transacao.origem = 'RECORRENCIA'
                transacao.checkout_recorrencia = recorrencia
                transacao.save(update_fields=['origem', 'checkout_recorrencia'])

                # Atualizar próxima cobrança
                hoje = datetime.now().date()
                proxima = recorrencia.calcular_proxima_cobranca(hoje)
                proxima = recorrencia.ajustar_para_dia_util(proxima)

                recorrencia.proxima_cobranca = proxima
                recorrencia.tentativas_falhas_consecutivas = 0
                recorrencia.ultima_tentativa_em = datetime.now()
                recorrencia.ultima_cobranca_sucesso_em = datetime.now()
                recorrencia.save(update_fields=[
                    'proxima_cobranca',
                    'tentativas_falhas_consecutivas',
                    'ultima_tentativa_em',
                    'ultima_cobranca_sucesso_em',
                    'updated_at'
                ])
                
                # RESETAR contador de falhas do cartão (transação aprovada)
                CartaoControleService.registrar_transacao_aprovada(recorrencia.cartao_tokenizado_id)

                registrar_log(
                    'portais.vendas.recorrencia',
                    f"Cobrança recorrente APROVADA: Recorrencia_ID={recorrencia_id}, "
                    f"Transacao_ID={transacao.id}, NSU={resultado.get('nsu')}, Próxima={proxima}"
                )

                return {
                    'sucesso': True,
                    'mensagem': 'Cobrança processada com sucesso',
                    'transacao_id': transacao.id,
                    'nsu': resultado.get('nsu'),
                    'proxima_cobranca': proxima.strftime('%Y-%m-%d')
                }
            else:
                # Incrementar tentativas de falha na recorrência
                recorrencia.tentativas_falhas_consecutivas += 1
                recorrencia.ultima_tentativa_em = datetime.now()
                recorrencia.save(update_fields=['tentativas_falhas_consecutivas', 'ultima_tentativa_em', 'updated_at'])
                
                # INCREMENTAR falhas no cartão (pode invalidar automaticamente)
                controle_resultado = CartaoControleService.registrar_transacao_negada(
                    cartao_id=recorrencia.cartao_tokenizado_id,
                    motivo_falha=resultado.get('mensagem')
                )

                registrar_log(
                    'portais.vendas.recorrencia',
                    f"Cobrança recorrente NEGADA: Recorrencia_ID={recorrencia_id}, "
                    f"Tentativa={recorrencia.tentativas_falhas_consecutivas}, "
                    f"Falhas_Cartao={controle_resultado['falhas_consecutivas']}, "
                    f"Cartao_Invalidado={controle_resultado['cartao_invalidado']}, "
                    f"Erro={resultado.get('mensagem')}",
                    nivel='WARNING'
                )

                return {
                    'sucesso': False,
                    'mensagem': resultado.get('mensagem', 'Erro ao processar cobrança'),
                    'tentativas': recorrencia.tentativas_falhas_consecutivas,
                    'cartao_falhas': controle_resultado['falhas_consecutivas'],
                    'cartao_invalidado': controle_resultado['cartao_invalidado'],
                    'recorrencias_bloqueadas': controle_resultado.get('recorrencias_bloqueadas', 0)
                }

        except RecorrenciaAgendada.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Recorrência não encontrada'}
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao processar cobrança agendada: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao processar cobrança: {str(e)}'}

    @staticmethod
    def retentar_cobranca(recorrencia_id: int) -> Dict[str, Any]:
        """
        Retenta uma cobrança que falhou anteriormente.
        Usa backoff: D+1, D+3, D+7.

        Args:
            recorrencia_id: ID da RecorrenciaAgendada

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)

            if recorrencia.tentativas_falhas_consecutivas >= recorrencia.max_tentativas:
                # Marcar como hold
                return CheckoutVendasService.marcar_hold(recorrencia_id)

            # Calcular próxima tentativa com backoff
            dias_backoff = [1, 3, 7]
            dias_adicionar = dias_backoff[min(recorrencia.tentativas_falhas_consecutivas, len(dias_backoff) - 1)]

            hoje = datetime.now().date()
            proxima_tentativa = hoje + timedelta(days=dias_adicionar)
            proxima_tentativa = recorrencia.ajustar_para_dia_util(proxima_tentativa)

            recorrencia.proxima_cobranca = proxima_tentativa
            recorrencia.save(update_fields=['proxima_cobranca', 'updated_at'])

            registrar_log(
                'portais.vendas.recorrencia',
                f"Retry agendado: Recorrencia_ID={recorrencia_id}, Tentativa={recorrencia.tentativas_falhas_consecutivas}, Próxima={proxima_tentativa}"
            )

            return {
                'sucesso': True,
                'mensagem': f'Nova tentativa agendada para {proxima_tentativa.strftime("%d/%m/%Y")}',
                'proxima_tentativa': proxima_tentativa.strftime('%Y-%m-%d')
            }

        except RecorrenciaAgendada.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Recorrência não encontrada'}
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao retentar cobrança: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def marcar_hold(recorrencia_id: int) -> Dict[str, Any]:
        """
        Marca recorrência como 'hold' após múltiplas falhas.
        Requer intervenção manual.

        Args:
            recorrencia_id: ID da RecorrenciaAgendada

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            recorrencia = RecorrenciaAgendada.objects.get(id=recorrencia_id)

            recorrencia.status = 'hold'
            recorrencia.save(update_fields=['status', 'updated_at'])

            registrar_log(
                'portais.vendas.recorrencia',
                f"Recorrência marcada como HOLD: Recorrencia_ID={recorrencia_id}, Tentativas={recorrencia.tentativas_falhas_consecutivas}",
                nivel='WARNING'
            )

            return {
                'sucesso': True,
                'mensagem': f'Recorrência em HOLD após {recorrencia.tentativas_falhas_consecutivas} falhas. Requer intervenção manual.',
                'status': 'hold'
            }

        except RecorrenciaAgendada.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Recorrência não encontrada'}
        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao marcar hold: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def obter_nao_cobrados(loja_id: int = None, vendedor_id: int = None) -> List[Dict[str, Any]]:
        """
        Obtém relatório de recorrências em HOLD (não cobradas por múltiplas falhas).

        Args:
            loja_id: Filtrar por loja
            vendedor_id: Filtrar por vendedor

        Returns:
            Lista de recorrências em hold
        """
        try:
            from checkout.models_recorrencia import RecorrenciaAgendada

            queryset = RecorrenciaAgendada.objects.filter(status='hold')

            if loja_id:
                queryset = queryset.filter(loja_id=loja_id)

            if vendedor_id:
                queryset = queryset.filter(vendedor_id=vendedor_id)

            holds = queryset.select_related('cliente', 'cartao_tokenizado', 'loja').order_by('-ultima_tentativa_em')

            resultado = []
            for hold in holds:
                resultado.append({
                    'id': hold.id,
                    'cliente_nome': hold.cliente.nome if hold.cliente else 'N/A',
                    'cliente_cpf': hold.cliente.cpf if hold.cliente else 'N/A',
                    'valor': float(hold.valor_recorrencia),
                    'periodicidade': hold.periodicidade_display,
                    'tentativas': hold.tentativas_falhas_consecutivas,
                    'ultima_tentativa': hold.ultima_tentativa_em.strftime('%d/%m/%Y %H:%M') if hold.ultima_tentativa_em else 'N/A',
                    'cartao_mascarado': hold.cartao_tokenizado.cartao_mascarado if hold.cartao_tokenizado else 'N/A',
                    'loja_nome': hold.loja.razao_social if hold.loja else 'N/A'
                })

            registrar_log('portais.vendas.recorrencia', f"Relatório não cobrados: {len(resultado)} recorrências em hold")
            return resultado

        except Exception as e:
            registrar_log('portais.vendas.recorrencia', f"Erro ao obter não cobrados: {str(e)}", nivel='ERROR')
            return []
