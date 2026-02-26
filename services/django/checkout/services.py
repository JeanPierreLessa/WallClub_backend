"""
Services para o sistema de checkout.
Lógica de negócio compartilhada entre link de pagamento e portal de vendas.
"""
from typing import Dict, Any, Optional
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from wallclub_core.utilitarios.log_control import registrar_log
from .models import CheckoutCliente, CheckoutCartaoTokenizado, CheckoutTransaction
from pinbank.services_transacoes_pagamento import TransacoesPinbankService
from .services_gateway_router import GatewayRouter


class ClienteService:
    """Serviço para gerenciamento de clientes do checkout"""

    @staticmethod
    def criar_cliente(loja_id: int, dados: Dict[str, Any], ip_address: str = None, user_agent: str = None) -> CheckoutCliente:
        """
        Cria novo cliente de checkout

        Args:
            loja_id: ID da loja
            dados: Dict com cpf/cnpj, nome, email, endereco, cep
            ip_address: IP do cliente
            user_agent: User agent do cliente

        Returns:
            CheckoutCliente criado

        Raises:
            ValidationError: Se dados inválidos ou cliente já existe
        """
        from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService

        try:
            # Validar loja existe
            loja = HierarquiaOrganizacionalService.get_loja(loja_id)
            if not loja:
                raise ValidationError(f'Loja {loja_id} não encontrada')

            # Validar CPF ou CNPJ
            cpf = dados.get('cpf', '').replace('.', '').replace('-', '') if dados.get('cpf') else None
            cnpj = dados.get('cnpj', '').replace('.', '').replace('/', '').replace('-', '') if dados.get('cnpj') else None

            if not cpf and not cnpj:
                raise ValidationError('CPF ou CNPJ é obrigatório')

            if cpf and cnpj:
                raise ValidationError('Informe apenas CPF ou CNPJ, não ambos')

            # Verificar duplicidade
            if cpf:
                if CheckoutCliente.objects.filter(loja_id=loja_id, cpf=cpf).exists():
                    raise ValidationError(f'Cliente com CPF {cpf} já cadastrado nesta loja')

            if cnpj:
                if CheckoutCliente.objects.filter(loja_id=loja_id, cnpj=cnpj).exists():
                    raise ValidationError(f'Cliente com CNPJ {cnpj} já cadastrado nesta loja')

            # Criar cliente
            cliente = CheckoutCliente.objects.create(
                loja_id=loja_id,
                cpf=cpf,
                cnpj=cnpj,
                nome=dados['nome'],
                email=dados['email'],
                endereco=dados.get('endereco'),
                cep=dados.get('cep'),
                ip_address=ip_address,
                user_agent=user_agent,
                ativo=True
            )

            registrar_log('checkout', f"Cliente criado: {cliente.id} - {cliente.nome}")
            return cliente

        except Loja.DoesNotExist:
            raise ValidationError(f'Loja {loja_id} não encontrada')
        except Exception as e:
            registrar_log('checkout', f"Erro ao criar cliente: {str(e)}", nivel='ERROR')
            raise

    @staticmethod
    def buscar_cliente(loja_id: int, cpf: str = None, cnpj: str = None) -> Optional[CheckoutCliente]:
        """
        Busca cliente por CPF ou CNPJ

        Args:
            loja_id: ID da loja
            cpf: CPF do cliente (apenas números)
            cnpj: CNPJ do cliente (apenas números)

        Returns:
            CheckoutCliente ou None
        """
        try:
            if cpf:
                return CheckoutCliente.objects.get(loja_id=loja_id, cpf=cpf, ativo=True)
            elif cnpj:
                return CheckoutCliente.objects.get(loja_id=loja_id, cnpj=cnpj, ativo=True)
            return None
        except CheckoutCliente.DoesNotExist:
            return None

    @staticmethod
    def atualizar_cliente(cliente_id: int, dados: Dict[str, Any]) -> CheckoutCliente:
        """
        Atualiza dados do cliente

        Args:
            cliente_id: ID do cliente
            dados: Dict com campos a atualizar (nome, email, endereco, cep, data_nascimento, logradouro, numero, etc)

        Returns:
            CheckoutCliente atualizado
        """
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)

            # Atualizar apenas campos permitidos (não altera CPF/CNPJ)
            if 'nome' in dados:
                cliente.nome = dados['nome']
            if 'email' in dados:
                cliente.email = dados['email']
            if 'data_nascimento' in dados:
                cliente.data_nascimento = dados['data_nascimento']
            # celular removido - gerenciado por checkout_cliente_telefone (2FA)
            if 'endereco' in dados:
                cliente.endereco = dados['endereco']
            if 'cep' in dados:
                cliente.cep = dados['cep']
            if 'logradouro' in dados:
                cliente.logradouro = dados['logradouro']
            if 'numero' in dados:
                cliente.numero = dados['numero']
            if 'complemento' in dados:
                cliente.complemento = dados['complemento']
            if 'bairro' in dados:
                cliente.bairro = dados['bairro']
            if 'cidade' in dados:
                cliente.cidade = dados['cidade']
            if 'estado' in dados:
                cliente.estado = dados['estado']

            cliente.save()

            registrar_log('checkout', f"Cliente atualizado: {cliente.id}")
            return cliente

        except CheckoutCliente.DoesNotExist:
            raise ValidationError('Cliente não encontrado')

    @staticmethod
    def inativar_cliente(cliente_id: int):
        """Inativa cliente (soft delete)"""
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            cliente.ativo = False
            cliente.save()

            registrar_log('checkout', f"Cliente inativado: {cliente.id}")

        except CheckoutCliente.DoesNotExist:
            raise ValidationError('Cliente não encontrado')

    @staticmethod
    def reativar_cliente(cliente_id: int):
        """Reativa cliente"""
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            cliente.ativo = True
            cliente.save()

            registrar_log('checkout', f"Cliente reativado: {cliente.id}")

        except CheckoutCliente.DoesNotExist:
            raise ValidationError('Cliente não encontrado')

    @staticmethod
    def buscar_ou_criar_cliente_pos(
        loja_id: int,
        cpf: str,
        nome: str = None,
        email: str = None,
        data_nascimento: str = None,
        ip_address: str = None
    ) -> tuple[CheckoutCliente, bool]:
        """
        Busca ou cria cliente para transação POS com validação Bureau

        Args:
            loja_id: ID da loja
            cpf: CPF do cliente (apenas números)
            nome: Nome do cliente (opcional se já existir)
            email: Email do cliente (opcional, gera genérico se não informado)
            data_nascimento: Data de nascimento YYYY-MM-DD (opcional)
            ip_address: IP do terminal POS

        Returns:
            tuple: (CheckoutCliente, criado: bool)

        Raises:
            ValidationError: Se CPF inválido, não existe no Bureau ou menor de idade
        """
        import json
        from datetime import datetime
        from wallclub_core.integracoes.bureau_service import BureauService
        from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService

        try:
            # Limpar CPF
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            if len(cpf_limpo) != 11:
                raise ValidationError('CPF inválido')

            # Validar loja
            loja = HierarquiaOrganizacionalService.get_loja(loja_id)
            if not loja:
                raise ValidationError(f'Loja {loja_id} não encontrada')

            # Buscar cliente existente
            cliente_existente = ClienteService.buscar_cliente(loja_id, cpf=cpf_limpo)
            if cliente_existente:
                registrar_log('checkout', f"Cliente POS encontrado: {cliente_existente.id} - {cpf_limpo}")
                return (cliente_existente, False)

            # Cliente não existe - consultar Bureau
            registrar_log('checkout', f"Cliente POS não existe, consultando Bureau: {cpf_limpo}")
            dados_bureau = BureauService.consulta_bureau(cpf_limpo)

            if not dados_bureau:
                raise ValidationError('CPF não encontrado no Bureau ou irregular')

            # Validar idade (maior de 18 anos)
            nascimento_bureau = dados_bureau.get('nascimento')
            if nascimento_bureau:
                try:
                    dt_nascimento = datetime.strptime(nascimento_bureau, '%Y-%m-%d')
                    idade = (datetime.now() - dt_nascimento).days // 365
                    if idade < 18:
                        raise ValidationError('Cliente menor de idade')
                except ValueError:
                    registrar_log('checkout', f"Erro ao validar idade - data: {nascimento_bureau}", nivel='WARNING')

            # Preparar dados do cliente
            nome_final = nome or dados_bureau.get('nome', 'Cliente POS')
            email_final = email or f"pos_{cpf_limpo}@wallclub.com.br"
            data_nascimento_final = data_nascimento or nascimento_bureau

            # Verificar restrições (loga mas não bloqueia)
            restricoes = dados_bureau.get('restricoes', [])
            bureau_restricoes_json = None
            if restricoes:
                bureau_restricoes_json = json.dumps(restricoes, ensure_ascii=False)
                registrar_log(
                    'checkout',
                    f"Cliente POS com restrições no Bureau: {cpf_limpo} - {len(restricoes)} restrição(ões)",
                    nivel='WARNING'
                )

            # Criar cliente
            cliente = CheckoutCliente.objects.create(
                loja_id=loja_id,
                cpf=cpf_limpo,
                nome=nome_final,
                email=email_final,
                data_nascimento=data_nascimento_final,
                bureau_restricoes=bureau_restricoes_json,
                ip_address=ip_address,
                ativo=True
            )

            registrar_log('checkout', f"Cliente POS criado via Bureau: {cliente.id} - {nome_final}")
            return (cliente, True)

        except ValidationError:
            raise
        except Exception as e:
            registrar_log('checkout', f"Erro ao buscar/criar cliente POS: {str(e)}", nivel='ERROR')
            raise ValidationError(f'Erro ao processar cliente: {str(e)}')


class CartaoTokenizadoService:
    """Serviço para tokenização e gerenciamento de cartões via gateway da loja (Pinbank ou OWN)"""

    @staticmethod
    def tokenizar_cartao(cliente_id: int, dados_cartao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tokeniza cartão via gateway da loja (Pinbank ou OWN) e salva no banco

        Args:
            cliente_id: ID do cliente
            dados_cartao: Dict com numero, validade, cvv, nome_titular, bandeira

        Returns:
            Dict com sucesso, cartao_id, mensagem

        Raises:
            ValidationError: Se cliente não existe ou dados inválidos
        """
        from checkout.services_gateway_router import GatewayRouter

        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)

            # Determinar gateway da loja
            gateway = GatewayRouter.obter_gateway_loja(cliente.loja_id)

            # Validar dados do cartão
            numero = dados_cartao.get('numero', '').replace(' ', '')
            validade = dados_cartao.get('validade', '')  # MM/YY ou MM/YYYY
            cvv = dados_cartao.get('cvv', '')
            nome_titular = dados_cartao.get('nome_titular', '')

            if not all([numero, validade, cvv, nome_titular]):
                raise ValidationError('Dados do cartão incompletos')

            # SEGURANÇA: Verificar se cartão já existe para ESTE cliente
            # Reutilizar token APENAS para o mesmo cliente (evita fraude)
            # Comparar: primeiros 6 + últimos 4 dígitos + validade
            primeiros_6 = numero[:6]
            ultimos_4 = numero[-4:]
            mascara_busca = f"{primeiros_6}******{ultimos_4}"

            # Converter validade para MM/YY antes de comparar
            validade_comparacao = validade
            if '/' in validade:
                partes = validade.split('/')
                if len(partes[1]) == 4:  # YYYY
                    validade_comparacao = f"{partes[0]}/{partes[1][2:]}"  # MM/YYYY -> MM/YY

            # Buscar cartão APENAS para este cliente específico
            cartao_existente = CheckoutCartaoTokenizado.objects.filter(
                cliente=cliente,  # MESMO cliente
                cartao_mascarado=mascara_busca,
                validade=validade_comparacao,
                valido=True
            ).first()

            if cartao_existente:
                registrar_log('checkout', f"Cartão já tokenizado para este cliente - Reutilizando: {cartao_existente.id}")
                return {
                    'sucesso': True,
                    'cartao_id': cartao_existente.id,
                    'cartao_mascarado': cartao_existente.cartao_mascarado,
                    'mensagem': 'Cartão já cadastrado'
                }

            # VERIFICAR SE CARTÃO EXISTE PARA OUTRO CLIENTE (segurança)
            cartao_outro_cliente = CheckoutCartaoTokenizado.objects.filter(
                cartao_mascarado=mascara_busca,
                validade=validade_comparacao,
                valido=True
            ).exclude(cliente=cliente).first()

            if cartao_outro_cliente:
                registrar_log('checkout',
                    f"SEGURANÇA: Tentativa de cadastrar cartão já vinculado a outro cliente - "
                    f"Cliente atual: {cliente.id}, Cartão: ****{ultimos_4}",
                    nivel='WARNING'
                )
                return {
                    'sucesso': False,
                    'mensagem': 'Cartão já utilizado por outro cliente. Use outro cartão.'
                }

            # Validade já convertida acima

            # Tokenizar via gateway correto da loja
            registrar_log('checkout', f"Iniciando tokenização via {gateway} para cliente {cliente_id}")

            if gateway == GatewayRouter.GATEWAY_OWN:
                # Tokenizar via OWN
                from adquirente_own.services_transacoes_pagamento import TransacoesOwnService
                import os
                # Determinar ambiente: production -> LIVE, development -> TEST
                env = os.getenv('ENVIRONMENT', 'development')
                own_env = 'LIVE' if env == 'production' else 'TEST'

                own_service = TransacoesOwnService(loja_id=cliente.loja_id, environment=own_env)

                # Converter dados para formato OWN
                card_data = {
                    'number': numero,
                    'holder': nome_titular.upper(),
                    'expiry_month': validade.split('/')[0],
                    'expiry_year': validade.split('/')[1],
                    'cvv': cvv,
                    'brand': dados_cartao.get('bandeira', 'VISA').upper()
                }

                resultado = own_service.incluir_cartao_tokenizado(card_data)
                registrar_log('checkout', f"Resposta OWN: {resultado}")

            else:
                # Tokenizar via Pinbank
                from pinbank.services_transacoes_pagamento import TransacoesPinbankService

                pinbank_service = TransacoesPinbankService(loja_id=cliente.loja_id)

                cpf_limpo = cliente.cpf.replace('.', '').replace('-', '')

                payload_tokenizacao = {
                    'numero_cartao': numero,
                    'data_validade': validade,  # MM/YY
                    'codigo_seguranca': cvv,
                    'nome_impresso': nome_titular.upper(),
                    'cpf_comprador': int(cpf_limpo)
                }

                resultado = pinbank_service.incluir_cartao_tokenizado(payload_tokenizacao)
                registrar_log('checkout', f"Resposta Pinbank: {resultado}")

            if not resultado.get('sucesso'):
                mensagem = resultado.get('mensagem', 'Erro ao tokenizar cartão')
                erro_detalhe = resultado.get('erro', '')
                registrar_log('checkout', f"Erro tokenização: {mensagem} | Detalhe: {erro_detalhe}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f"{mensagem} - {erro_detalhe}" if erro_detalhe else mensagem
                }

            # Extrair token (ambos gateways retornam 'cartao_id')
            cartao_id = resultado.get('cartao_id')

            if not cartao_id:
                raise ValidationError(f'Token não retornado pelo gateway {gateway}')

            # Gerar máscara do cartão (primeiros 6 + últimos 4 dígitos)
            cartao_mascarado = f"{numero[:6]}******{numero[-4:]}"

            # Detectar bandeira pelos primeiros dígitos
            primeiro_digito = numero[0]
            if primeiro_digito == '4':
                bandeira = 'VISA'
            elif primeiro_digito == '5':
                bandeira = 'MASTERCARD'
            elif primeiro_digito == '3':
                bandeira = 'AMEX'
            elif primeiro_digito == '6':
                bandeira = 'ELO'
            else:
                bandeira = 'VISA'  # default

            # Salvar cartão tokenizado com informação do gateway
            cartao = CheckoutCartaoTokenizado.objects.create(
                cliente=cliente,
                id_token=cartao_id,
                cartao_mascarado=cartao_mascarado,
                bandeira=bandeira,
                tokenizadora=gateway,
                validade=validade,
                nome_cliente=nome_titular,
                valido=True
            )

            registrar_log('checkout', f"Cartão tokenizado com sucesso - Cliente: {cliente.id}, CartaoId: {cartao_id}")

            return {
                'sucesso': True,
                'cartao_id': cartao.id,
                'cartao_mascarado': cartao_mascarado,
                'mensagem': 'Cartão tokenizado com sucesso'
            }

        except CheckoutCliente.DoesNotExist:
            registrar_log('checkout', f"Cliente {cliente_id} não encontrado", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Cliente não encontrado'
            }
        except ValidationError as e:
            registrar_log('checkout', f"Validação falhou: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': str(e)
            }
        except Exception as e:
            registrar_log('checkout', f"Erro inesperado ao tokenizar cartão: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao tokenizar: {str(e)}'
            }

    @staticmethod
    def listar_cartoes_cliente(cliente_id: int, apenas_validos: bool = True):
        """
        Lista cartões do cliente filtrando pelo gateway da loja
        Retorna apenas cartões tokenizados pelo gateway ativo da loja
        """
        from checkout.services_gateway_router import GatewayRouter

        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            gateway = GatewayRouter.obter_gateway_loja(cliente.loja_id)

            filtros = {
                'cliente_id': cliente_id,
                'tokenizadora': gateway  # Filtrar pelo gateway ativo da loja
            }
            if apenas_validos:
                filtros['valido'] = True

            registrar_log('checkout', f"Listando cartões do cliente {cliente_id} - Gateway: {gateway}")
            return CheckoutCartaoTokenizado.objects.filter(**filtros).order_by('-created_at')

        except CheckoutCliente.DoesNotExist:
            registrar_log('checkout', f"Cliente {cliente_id} não encontrado", nivel='WARNING')
            return CheckoutCartaoTokenizado.objects.none()

    @staticmethod
    def invalidar_cartao(cartao_id: int, motivo: str = None, usuario_id: int = None):
        """
        Invalida cartão (soft delete)

        Args:
            cartao_id: ID do cartão
            motivo: Motivo da invalidação (ex: "Múltiplas falhas", "Solicitação do cliente")
            usuario_id: ID do usuário que invalidou (null se automático)
        """
        from django.utils import timezone

        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
            cartao.valido = False
            cartao.motivo_invalidacao = motivo or "Invalidação manual"
            cartao.invalidado_por = usuario_id
            cartao.invalidado_em = timezone.now()
            cartao.save()

            registrar_log('checkout',
                         f"Cartão invalidado: {cartao_id} - Motivo: {motivo} - Usuário: {usuario_id}",
                         nivel='INFO')

        except CheckoutCartaoTokenizado.DoesNotExist:
            raise ValidationError('Cartão não encontrado')

    @staticmethod
    def excluir_cartao_pinbank(cartao_id: int) -> Dict[str, Any]:
        """
        Exclui cartão do gateway (Pinbank ou OWN) e invalida localmente

        Args:
            cartao_id: ID do cartão local

        Returns:
            Dict com sucesso e mensagem
        """
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)

            # Obter gateway correto via router
            gateway = GatewayRouter.obter_gateway_loja(cartao.cliente.loja_id)
            service = GatewayRouter.obter_service_transacao(cartao.cliente.loja_id)

            # Chamar API do gateway para excluir
            if gateway == GatewayRouter.GATEWAY_OWN:
                resultado = service.delete_registration(
                    registration_id=cartao.id_token,
                    loja_id=cartao.cliente.loja_id
                )
                registrar_log('checkout', f"Cartão excluído da OWN: {cartao_id}")
            else:
                resultado = service.excluir_cartao_tokenizado(cartao.id_token)
                registrar_log('checkout', f"Cartão excluído do Pinbank: {cartao_id}")

            # Invalidar localmente independente do resultado
            cartao.valido = False
            cartao.save()

            if not resultado.get('sucesso'):
                registrar_log('checkout', f"Erro ao excluir do {gateway}: {resultado.get('mensagem')}", nivel='WARNING')

            return resultado

        except CheckoutCartaoTokenizado.DoesNotExist:
            raise ValidationError('Cartão não encontrado')


class CheckoutService:
    """Serviço para processar pagamentos de checkout"""

    @staticmethod
    @transaction.atomic
    def processar_pagamento_cartao_tokenizado(
        cliente_id: int,
        cartao_id: str,
        valor: Decimal,
        parcelas: int,
        bandeira: str,
        descricao: str,
        ip_address: str,
        user_agent: str,
        pedido_origem_loja: str = None,
        cod_item_origem_loja: str = None,
        portais_usuarios_id: int = None,
        valor_transacao_original: Decimal = None,
        valor_transacao_final: Decimal = None
    ) -> Dict[str, Any]:
        """
        Processa pagamento com cartão tokenizado.

        Args:
            cliente_id: ID do cliente checkout
            cartao_id: ID do cartão tokenizado
            valor: Valor da transação
            parcelas: Quantidade de parcelas
            bandeira: Bandeira do cartão (VISA, MASTERCARD, etc)
            descricao: Descrição da transação
            ip_address: IP do comprador
            user_agent: User agent do comprador
            pedido_origem_loja: Número do pedido na loja
            cod_item_origem_loja: Código do item na loja
            portais_usuarios_id: ID do vendedor (se origem portal)
            valor_transacao_original: Valor original sem desconto/juros
            valor_transacao_final: Valor final com desconto/juros aplicados

        Returns:
            Dict com sucesso, transacao_id, nsu, codigo_autorizacao, status, mensagem
        """
        # Variáveis para captura de erro
        cliente = None
        cartao = None
        bandeira_cartao = bandeira or 'MASTERCARD'

        try:
            # Buscar cliente e cartão
            cliente = CheckoutCliente.objects.get(id=cliente_id, ativo=True)
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id, cliente=cliente, valido=True)

            # Determinar bandeira do cartão
            bandeira_cartao = bandeira or cartao.bandeira or 'MASTERCARD'

            # Garantir que valor seja Decimal
            if not isinstance(valor, Decimal):
                valor = Decimal(str(valor))

            # Usar valor_transacao_final se fornecido (valor com desconto das parcelas)
            valor_para_transacao = valor_transacao_final if valor_transacao_final is not None else valor

            # Obter gateway correto via router
            gateway = GatewayRouter.obter_gateway_loja(cliente.loja_id)
            service = GatewayRouter.obter_service_transacao(cliente.loja_id)

            registrar_log('checkout', f"Processando pagamento cliente {cliente_id} - R$ {valor} via {gateway}")

            # Processar conforme gateway
            if gateway == GatewayRouter.GATEWAY_OWN:
                # OWN Financial - pagamento com registration_id
                resultado = service.create_payment_with_registration(
                    registration_id=cartao.id_token,
                    amount=valor_para_transacao,
                    parcelas=parcelas,
                    loja_id=cliente.loja_id
                )
                registrar_log('checkout', f"Resultado OWN: sucesso={resultado.get('sucesso')}, mensagem={resultado.get('mensagem')}")
            else:
                # Pinbank - pagamento com cartão tokenizado
                cpf_cnpj = cliente.cpf or cliente.cnpj
                cpf_cnpj_int = int(cpf_cnpj) if cpf_cnpj else 0

                payload_transacao = {
                    'cartao_id': cartao.id_token,
                    'valor': valor_para_transacao,
                    'quantidade_parcelas': parcelas,
                    'forma_pagamento': '1',
                    'descricao_pedido': descricao,
                    'ip_address_comprador': ip_address,
                    'cpf_comprador': cpf_cnpj_int,
                    'nome_comprador': cliente.nome
                }

                registrar_log('checkout', f"Payload Pinbank: {payload_transacao}")
                resultado = service.efetuar_transacao_cartao_tokenizado(payload_transacao)
                registrar_log('checkout', f"Resultado Pinbank: sucesso={resultado.get('sucesso')}, mensagem={resultado.get('mensagem')}")

            # Determinar status
            if resultado.get('sucesso'):
                status = 'APROVADA'
                # NSU e código_autorização estão dentro de 'dados'
                dados = resultado.get('dados', {})
                nsu = dados.get('nsu') or resultado.get('nsu')
                codigo_autorizacao = dados.get('codigo_autorizacao') or resultado.get('codigo_autorizacao')
                erro_pinbank = None
            else:
                status = 'NEGADA'
                nsu = None
                codigo_autorizacao = None
                erro_pinbank = resultado.get('mensagem', 'Transação negada')

            # Salvar transação
            # Usar valores fornecidos ou usar 'valor' para ambos se não fornecidos
            from datetime import datetime

            valor_original = valor_transacao_original if valor_transacao_original is not None else valor
            valor_final = valor_transacao_final if valor_transacao_final is not None else valor

            transacao = CheckoutTransaction.objects.create(
                cliente=cliente,
                cartao_tokenizado=cartao,
                origem='CHECKOUT',
                loja_id=cliente.loja_id,
                gateway='OWN' if gateway == GatewayRouter.GATEWAY_OWN else 'PINBANK',
                nsu=nsu,
                codigo_autorizacao=codigo_autorizacao,
                card_bin=resultado.get('card_bin'),
                card_last4=resultado.get('card_last4'),
                payment_brand_response=resultado.get('payment_brand'),
                result_code=resultado.get('result_code'),
                tx_transaction_id=resultado.get('tx_transaction_id'),
                valor_transacao_original=valor_original,
                valor_transacao_final=valor_final,
                status=status,
                forma_pagamento=f"{bandeira_cartao}_{parcelas}x",
                parcelas=parcelas,
                pedido_origem_loja=pedido_origem_loja,
                cod_item_origem_loja=cod_item_origem_loja,
                vendedor_id=portais_usuarios_id,
                gateway_response=resultado.get('resposta_completa'),
                erro_gateway=erro_pinbank,
                processed_at=datetime.now()
            )

            registrar_log('checkout', f"Transação salva: {transacao.id} - Status: {status}")

            return {
                'sucesso': resultado.get('sucesso'),
                'transacao_id': transacao.id,
                'nsu': nsu,
                'codigo_autorizacao': codigo_autorizacao,
                'status': status,
                'mensagem': resultado.get('mensagem', 'Transação processada')
            }

        except CheckoutCliente.DoesNotExist:
            raise ValidationError('Cliente não encontrado')
        except CheckoutCartaoTokenizado.DoesNotExist:
            raise ValidationError('Cartão não encontrado ou inválido')
        except Exception as e:
            import traceback
            erro_completo = traceback.format_exc()
            registrar_log('checkout', f"Erro ao processar pagamento: {str(e)}\n{erro_completo}", nivel='ERROR')

            # Salvar transação com erro para auditoria
            try:
                from datetime import datetime
                gateway_erro = GatewayRouter.obter_gateway_loja(cliente.loja_id) if cliente else 'PINBANK'
                CheckoutTransaction.objects.create(
                    cliente_id=cliente_id,
                    cartao_tokenizado_id=cartao_id,
                    origem='CHECKOUT',
                    loja_id=cliente.loja_id if cliente else None,
                    gateway=gateway_erro,
                    valor_transacao_original=valor_transacao_original or valor,
                    valor_transacao_final=valor_transacao_final or valor,
                    status='NEGADA',
                    forma_pagamento=f"{bandeira_cartao}_{parcelas}x",
                    parcelas=parcelas,
                    pedido_origem_loja=pedido_origem_loja,
                    cod_item_origem_loja=cod_item_origem_loja,
                    vendedor_id=portais_usuarios_id,
                    erro_gateway=f"Erro interno: {str(e)}",
                    processed_at=datetime.now()
                )
            except Exception as save_error:
                registrar_log('checkout', f"Erro ao salvar transação com erro: {str(save_error)}", nivel='ERROR')

            raise

    @staticmethod
    @transaction.atomic
    def processar_pagamento_cartao_direto(
        cliente_id: int,
        numero_cartao: str,
        validade: str,
        cvv: str,
        nome_titular: str,
        valor: Decimal,
        parcelas: int,
        bandeira: str,
        descricao: str,
        ip_address: str,
        user_agent: str,
        pedido_origem_loja: str = None,
        cod_item_origem_loja: str = None,
        portais_usuarios_id: int = None
    ) -> Dict[str, Any]:
        """
        Processa pagamento usando cartão digitado diretamente (não tokenizado)
        Usa efetuar_transacao ao invés de efetuar_transacao_cartao_tokenizado
        """
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)

            if valor <= 0:
                raise ValidationError('Valor deve ser maior que zero')

            if not all([numero_cartao, validade, cvv, nome_titular, bandeira]):
                raise ValidationError('Dados do cartão incompletos')

            # Obter gateway correto via router
            gateway = GatewayRouter.obter_gateway_loja(cliente.loja_id)
            service = GatewayRouter.obter_service_transacao(cliente.loja_id)

            registrar_log('checkout', f"Processando pagamento DIRETO cliente {cliente_id} - R$ {valor}")

            # ========== INTERCEPTAÇÃO ANTIFRAUDE ==========
            from django.conf import settings
            from checkout.services_antifraude import CheckoutAntifraudeService

            if settings.ANTIFRAUDE_ENABLED and cliente.cpf:
                try:
                    # Determinar modalidade
                    modalidade = 'CREDITO' if parcelas > 1 else 'DEBITO'

                    # Obter canal_id da loja
                    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
                    loja = HierarquiaOrganizacionalService.get_loja(cliente.loja_id)
                    canal_id = loja.canal_id if loja else None

                    # Analisar transação
                    permitir, resultado_antifraude = CheckoutAntifraudeService.analisar_transacao(
                        cpf=cliente.cpf,
                        valor=valor,
                        modalidade=modalidade,
                        parcelas=parcelas,
                        loja_id=cliente.loja_id,
                        canal_id=canal_id,
                        numero_cartao=numero_cartao,
                        bandeira=bandeira,
                        ip_address=ip_address,
                        user_agent=user_agent,
                        device_fingerprint=None,
                        cliente_nome=cliente.nome,
                        cliente_email=cliente.email,
                        transaction_id=f'CHECKOUT-{cliente_id}-{int(datetime.now().timestamp())}'
                    )

                    # Verificar decisão
                    if not permitir:
                        # Transação REPROVADA pelo antifraude
                        registrar_log(
                            'checkout',
                            f'🚫 Transação BLOQUEADA pelo antifraude - Score: {resultado_antifraude.get("score_risco")}',
                            nivel='WARNING'
                        )

                        return {
                            'sucesso': False,
                            'mensagem': 'Transação bloqueada por segurança',
                            'motivo_antifraude': resultado_antifraude.get('motivo'),
                            'score_risco': resultado_antifraude.get('score_risco')
                        }

                    # APROVADO ou REVISAR: continua processamento
                    registrar_log(
                        'checkout',
                        f'✅ Antifraude: {resultado_antifraude.get("decisao")} - Score: {resultado_antifraude.get("score_risco")}'
                    )

                except Exception as e:
                    # Fail-open: erro no antifraude não bloqueia transação
                    registrar_log(
                        'checkout',
                        f'⚠️ Erro no antifraude (fail-open): {str(e)}',
                        nivel='WARNING'
                    )
            # ========== FIM INTERCEPTAÇÃO ANTIFRAUDE ==========

            # Processar conforme gateway
            registrar_log('checkout', f"Processando pagamento DIRETO via {gateway}")

            if gateway == GatewayRouter.GATEWAY_OWN:
                # OWN Financial - pagamento direto com cartão
                card_data = {
                    'number': numero_cartao,
                    'holder': nome_titular.upper(),
                    'expiry_month': validade.split('/')[0],
                    'expiry_year': validade.split('/')[1],
                    'cvv': cvv,
                    'brand': bandeira.upper()
                }

                # Preparar dados do cliente (obrigatório para Own)
                customer_data = {
                    'nome_completo': cliente.nome,
                    'email': cliente.email,
                    'cpf': cliente.cpf,
                    'data_nascimento': cliente.data_nascimento.strftime('%Y-%m-%d') if cliente.data_nascimento else None
                }

                resultado = service.create_payment_debit(
                    card_data=card_data,
                    amount=valor,
                    parcelas=parcelas,
                    loja_id=cliente.loja_id,
                    customer_data=customer_data,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            else:
                # Pinbank - pagamento direto com cartão
                cpf_cnpj = cliente.cpf or cliente.cnpj
                cpf_cnpj_int = int(cpf_cnpj) if cpf_cnpj else 0

                payload_transacao = {
                    'numero_cartao': numero_cartao,
                    'data_validade': validade,
                    'codigo_seguranca': cvv,
                    'nome_impresso': nome_titular,
                    'bandeira': bandeira,
                    'valor': valor,
                    'quantidade_parcelas': parcelas,
                    'forma_pagamento': '1',
                    'descricao_pedido': descricao,
                    'ip_address_comprador': ip_address,
                    'cpf_comprador': cpf_cnpj_int,
                    'nome_comprador': cliente.nome
                }
                resultado = service.efetuar_transacao_cartao(payload_transacao)

            if resultado.get('sucesso'):
                status = 'APROVADA'
                nsu = resultado.get('nsu')
                codigo_autorizacao = resultado.get('codigo_autorizacao')
                erro_pinbank = None
            else:
                status = 'NEGADA'
                nsu = None
                codigo_autorizacao = None
                erro_pinbank = resultado.get('mensagem', 'Transação negada')

            # Salvar transação
            # Cartão direto: valor_transacao_original e valor_transacao_final são iguais
            transacao = CheckoutTransaction.objects.create(
                cliente=cliente,
                cartao_tokenizado=None,  # Cartão NÃO tokenizado
                origem='CHECKOUT',
                loja_id=cliente.loja_id,
                gateway='OWN' if gateway == GatewayRouter.GATEWAY_OWN else 'PINBANK',
                nsu=nsu,
                codigo_autorizacao=codigo_autorizacao,
                card_bin=resultado.get('card_bin'),
                card_last4=resultado.get('card_last4'),
                payment_brand_response=resultado.get('payment_brand'),
                result_code=resultado.get('result', {}).get('code') if isinstance(resultado.get('result'), dict) else None,
                tx_transaction_id=resultado.get('nsu'),
                valor_transacao_original=valor,
                valor_transacao_final=valor,
                status=status,
                forma_pagamento=f"{bandeira}_{parcelas}x",
                parcelas=parcelas,
                pedido_origem_loja=pedido_origem_loja,
                cod_item_origem_loja=cod_item_origem_loja,
                vendedor_id=portais_usuarios_id,
                gateway_response=resultado.get('resposta_completa'),
                erro_gateway=erro_pinbank,
                processed_at=timezone.now()
            )

            registrar_log('checkout', f"Transação DIRETA salva: {transacao.id} - Status: {status}")

            return {
                'sucesso': resultado.get('sucesso'),
                'transacao_id': transacao.id,
                'nsu': nsu,
                'codigo_autorizacao': codigo_autorizacao,
                'status': status,
                'mensagem': resultado.get('mensagem', 'Transação processada')
            }

        except CheckoutCliente.DoesNotExist:
            raise ValidationError('Cliente não encontrado')
        except Exception as e:
            registrar_log('checkout', f"Erro ao processar pagamento direto: {str(e)}", nivel='ERROR')
            raise

    @staticmethod
    def simular_parcelas(
        valor: Decimal,
        loja_id: int,
        bandeira: str,
        wall: str = 'S'
    ) -> Dict[str, Any]:
        """
        Simula opções de parcelamento usando calculadora do sistema
        Suporta cálculo diferente por bandeira (ao contrário do POS que é fixo em Mastercard)

        Args:
            valor: Valor da compra
            loja_id: ID da loja
            bandeira: Bandeira do cartão (MASTERCARD, VISA, ELO, etc)
            wall: Modalidade (S=Com Wall, N=Sem Wall)

        Returns:
            Dict com parcelas calculadas incluindo desconto e cashback
        """
        from parametros_wallclub.services import CalculadoraDesconto
        from datetime import datetime

        try:
            # Garantir que valor seja Decimal
            if not isinstance(valor, Decimal):
                valor = Decimal(str(valor))

            registrar_log('checkout', f"Simulando parcelas - Loja: {loja_id}, Valor: {valor}, Bandeira: {bandeira}")

            calculadora = CalculadoraDesconto()
            data_atual = datetime.now().strftime('%Y-%m-%d')

            parcelas_resultado = {}

            # # PIX (0 parcelas)
            # try:
            #     valor_pix = calculadora.calcular_desconto(
            #         valor_original=valor,
            #         data=data_atual,
            #         forma='PIX',
            #         parcelas=0,
            #         id_loja=loja_id,
            #         wall=wall
            #     )
            #
            #     if valor_pix > 0:
            #         parcelas_resultado['PIX'] = {
            #             'num_parcelas': 0,
            #             'valor_parcela': float(valor_pix),
            #             'valor_desconto': float(valor_pix),
            #             'descricao': '(c/desconto PIX)',
            #             'cashback': 0
            #         }
            # except Exception as e:
            #     registrar_log('checkout', f"Erro ao calcular PIX: {str(e)}", nivel='WARNING')

            # # DÉBITO (0 parcelas)
            # try:
            #     valor_debito = calculadora.calcular_desconto(
            #         valor_original=valor,
            #         data=data_atual,
            #         forma='DEBITO',
            #         parcelas=0,
            #         id_loja=loja_id,
            #         wall=wall
            #     )
            #
            #     if valor_debito > 0:
            #         parcelas_resultado['DEBITO'] = {
            #             'num_parcelas': 0,
            #             'valor_parcela': float(valor_debito),
            #             'valor_desconto': float(valor_debito),
            #             'descricao': '(c/desconto)',
            #             'cashback': 0
            #         }
            # except Exception as e:
            #     registrar_log('checkout', f"Erro ao calcular DÉBITO: {str(e)}", nivel='WARNING')

            # CRÉDITO À VISTA (1 parcela)
            try:
                valor_avista = calculadora.calcular_desconto(
                    valor_original=valor,
                    data=data_atual,
                    forma='A VISTA',
                    parcelas=1,
                    id_loja=loja_id,
                    wall=wall
                )

                if valor_avista > 0:
                    # Definir descrição baseada na comparação com valor original
                    if valor_avista > valor:
                        descricao = '(c/encargos)'
                    elif valor_avista < valor:
                        descricao = '(c/desconto)'
                    else:
                        descricao = '(s/juros)'

                    # Calcular cashback Wall
                    cashback_wall_valor = Decimal('0')
                    cashback_wall_percentual = Decimal('0')
                    if wall.upper() == 'S':
                        try:
                            valor_com_cashback = calculadora.calcular_desconto(
                                valor_original=valor_avista,
                                data=data_atual,
                                forma='A VISTA',
                                parcelas=1,
                                id_loja=loja_id,
                                wall='C'
                            )
                            cashback_wall_valor = valor_avista - valor_com_cashback if valor_com_cashback else Decimal('0')
                            cashback_wall_percentual = (cashback_wall_valor / valor_avista * 100) if valor_avista > 0 else Decimal('0')
                        except Exception as e:
                            registrar_log('checkout', f'Erro ao calcular cashback Wall: {str(e)}', nivel='WARNING')

                    # Simular cashback loja
                    cashback_loja_info = {"aplicavel": False, "valor": "0.00"}
                    cashback_loja_valor = Decimal('0')
                    try:
                        from apps.cashback.services import CashbackService
                        resultado_loja = CashbackService.simular_cashback_loja(
                            loja_id=loja_id,
                            cliente_id=0,
                            canal_id=1,
                            valor_transacao=valor_avista,
                            forma_pagamento='CREDITO'
                        )
                        if resultado_loja and resultado_loja.get('aplicavel'):
                            cashback_loja_valor = Decimal(str(resultado_loja['valor']))
                            cashback_loja_info = {
                                'aplicavel': True,
                                'valor': f"{cashback_loja_valor:.2f}",
                                'regra_id': resultado_loja['regra_id'],
                                'regra_nome': resultado_loja['regra_nome'],
                                'tipo_concessao': resultado_loja['tipo_concessao'],
                                'valor_concessao': f"{resultado_loja['valor_concessao']:.2f}"
                            }
                    except Exception as e:
                        registrar_log('checkout', f'Erro ao simular cashback loja: {str(e)}', nivel='WARNING')

                    cashback_total = cashback_wall_valor + cashback_loja_valor

                    parcelas_resultado['CREDITO_1X'] = {
                        'num_parcelas': 1,
                        'valor_original': float(valor),
                        'valor_total': float(valor_avista),
                        'valor_parcela': float(valor_avista),
                        'valor_desconto': float(valor_avista),  # Alias para compatibilidade
                        'descricao': descricao,
                        'desconto_wall': float(valor - valor_avista),
                        'cashback_wall': {
                            'valor': float(cashback_wall_valor),
                            'percentual': float(cashback_wall_percentual)
                        },
                        'cashback_loja': cashback_loja_info,
                        'cashback': float(cashback_total),  # Alias para compatibilidade
                        'cashback_total': float(cashback_total)
                    }
            except Exception as e:
                registrar_log('checkout', f"Erro ao calcular CRÉDITO 1x: {str(e)}", nivel='WARNING')

            # PARCELADO (2 a 12 parcelas)
            for num_parcelas in range(2, 13):
                try:
                    valor_parcelado = calculadora.calcular_desconto(
                        valor_original=valor,
                        data=data_atual,
                        forma='PARCELADO SEM JUROS',
                        parcelas=num_parcelas,
                        id_loja=loja_id,
                        wall=wall
                    )

                    if valor_parcelado > 0:
                        valor_parcela = valor_parcelado / num_parcelas

                        # Definir descrição baseada na comparação com valor original
                        if valor_parcelado > valor:
                            descricao = '(c/encargos)'
                        elif valor_parcelado < valor:
                            descricao = '(c/desconto)'
                        else:
                            descricao = '(s/juros)'

                        # Calcular cashback Wall
                        cashback_wall_valor = Decimal('0')
                        cashback_wall_percentual = Decimal('0')
                        if wall.upper() == 'S':
                            try:
                                valor_com_cashback = calculadora.calcular_desconto(
                                    valor_original=valor_parcelado,
                                    data=data_atual,
                                    forma='PARCELADO SEM JUROS',
                                    parcelas=num_parcelas,
                                    id_loja=loja_id,
                                    wall='C'
                                )
                                cashback_wall_valor = valor_parcelado - valor_com_cashback if valor_com_cashback else Decimal('0')
                                cashback_wall_percentual = (cashback_wall_valor / valor_parcelado * 100) if valor_parcelado > 0 else Decimal('0')
                            except Exception as e:
                                registrar_log('checkout', f'Erro ao calcular cashback Wall: {str(e)}', nivel='WARNING')

                        # Simular cashback loja
                        cashback_loja_info = {"aplicavel": False, "valor": "0.00"}
                        cashback_loja_valor = Decimal('0')
                        try:
                            from apps.cashback.services import CashbackService
                            resultado_loja = CashbackService.simular_cashback_loja(
                                loja_id=loja_id,
                                cliente_id=0,
                                canal_id=1,
                                valor_transacao=valor_parcelado,
                                forma_pagamento='CREDITO'
                            )
                            if resultado_loja and resultado_loja.get('aplicavel'):
                                cashback_loja_valor = Decimal(str(resultado_loja['valor']))
                                cashback_loja_info = {
                                    'aplicavel': True,
                                    'valor': f"{cashback_loja_valor:.2f}",
                                    'regra_id': resultado_loja['regra_id'],
                                    'regra_nome': resultado_loja['regra_nome'],
                                    'tipo_concessao': resultado_loja['tipo_concessao'],
                                    'valor_concessao': f"{resultado_loja['valor_concessao']:.2f}"
                                }
                        except Exception as e:
                            registrar_log('checkout', f'Erro ao simular cashback loja: {str(e)}', nivel='WARNING')

                        cashback_total = cashback_wall_valor + cashback_loja_valor

                        parcelas_resultado[f'CREDITO_{num_parcelas}X'] = {
                            'num_parcelas': num_parcelas,
                            'valor_original': float(valor),
                            'valor_total': float(valor_parcelado),
                            'valor_parcela': float(valor_parcela),
                            'valor_desconto': float(valor_parcelado),  # Alias para compatibilidade
                            'descricao': descricao,
                            'desconto_wall': float(valor - valor_parcelado),
                            'cashback_wall': {
                                'valor': float(cashback_wall_valor),
                                'percentual': float(cashback_wall_percentual)
                            },
                            'cashback_loja': cashback_loja_info,
                            'cashback': float(cashback_total),  # Alias para compatibilidade
                            'cashback_total': float(cashback_total)
                        }
                except Exception as e:
                    registrar_log('checkout', f"Erro ao calcular {num_parcelas}x: {str(e)}", nivel='WARNING')

            if not parcelas_resultado:
                return {
                    'sucesso': False,
                    'mensagem': 'Nenhuma opção de parcelamento disponível'
                }

            registrar_log('checkout', f"Simulação concluída - {len(parcelas_resultado)} opções")

            return {
                'sucesso': True,
                'parcelas': parcelas_resultado,
                'mensagem': 'Parcelas calculadas com sucesso'
            }

        except Exception as e:
            registrar_log('checkout', f"Erro ao simular parcelas: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao calcular parcelas: {str(e)}'
            }


class LinkPagamentoService:
    """Serviço para envio de link de pagamento por email"""

    @staticmethod
    def enviar_link_pagamento_email(
        token,
        cliente_email: str,
        cliente_nome: str,
        loja_nome: str,
        valor: Decimal,
        item_nome: str
    ) -> Dict[str, Any]:
        """
        Envia email com link de pagamento para o cliente

        Args:
            token: Objeto CheckoutToken gerado
            cliente_email: Email do cliente
            cliente_nome: Nome do cliente
            loja_nome: Nome da loja
            valor: Valor da transação
            item_nome: Descrição do item/venda

        Returns:
            Dict com sucesso e mensagem
        """
        from django.conf import settings
        from wallclub_core.integracoes.email_service import EmailService

        try:
            # URL do checkout com token - obrigatório via settings
            checkout_url = f"{settings.CHECKOUT_BASE_URL}/api/v1/checkout/?token={token.token}"

            context = {
                'cliente_nome': cliente_nome,
                'loja_nome': loja_nome,
                'valor': valor,
                'item_nome': item_nome,
                'checkout_url': checkout_url,
                'validade_minutos': 30
            }

            # Enviar via EmailService centralizado
            resultado = EmailService.enviar_email(
                destinatarios=[cliente_email],
                assunto=f'{loja_nome} - Link de Pagamento Seguro',
                template_html='checkout/emails/link_pagamento.html',  # Caminho correto
                template_context=context,
                fail_silently=False
            )

            if resultado['sucesso']:
                registrar_log('checkout', f"Link de pagamento enviado para {cliente_email}")

            return resultado

        except Exception as e:
            registrar_log('checkout', f"Erro ao enviar email: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao enviar email: {str(e)}'
            }


class LinkPagamentoTransactionService:
    """Serviço para gerenciar transações de link de pagamento"""

    @staticmethod
    def criar_transacao_inicial(
        token: str,
        loja_id: int,
        valor: Decimal,
        cliente_id: int = None,
        vendedor_id: int = None,
        pedido_origem_loja: str = None
    ) -> CheckoutTransaction:
        """
        Cria transação inicial quando vendedor gera link de pagamento.
        Status inicial: PENDENTE (aguardando cliente pagar)

        Args:
            token: Token do link de pagamento
            loja_id: ID da loja
            valor: Valor da transação
            cliente_id: ID do cliente (opcional)
            vendedor_id: ID do vendedor que criou
            pedido_origem_loja: Pedido de origem da loja

        Returns:
            CheckoutTransaction criada
        """
        transacao = CheckoutTransaction.objects.create(
            token=token,
            loja_id=loja_id,
            cliente_id=cliente_id,
            valor_transacao_original=valor,
            valor_transacao_final=None,  # Cliente ainda não escolheu
            status='PENDENTE',
            origem='CHECKOUT',
            vendedor_id=vendedor_id,
            pedido_origem_loja=pedido_origem_loja,
            created_at=timezone.now()
        )

        registrar_log('checkout', f"Transação inicial criada - Token: {token[:8]}... - Valor: {valor}")

        return transacao
