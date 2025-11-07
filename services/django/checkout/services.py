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
            dados: Dict com campos a atualizar (nome, email, endereco, cep)
            
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
            # celular removido - gerenciado por checkout_cliente_telefone (2FA)
            if 'endereco' in dados:
                cliente.endereco = dados['endereco']
            if 'cep' in dados:
                cliente.cep = dados['cep']
            
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


class CartaoTokenizadoService:
    """Serviço para tokenização e gerenciamento de cartões via Pinbank"""
    
    @staticmethod
    def tokenizar_cartao(cliente_id: int, dados_cartao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tokeniza cartão via API Pinbank e salva no banco
        
        Args:
            cliente_id: ID do cliente
            dados_cartao: Dict com numero, validade, cvv, nome_titular, bandeira
            
        Returns:
            Dict com sucesso, cartao_id, mensagem
            
        Raises:
            ValidationError: Se cliente não existe ou dados inválidos
        """
        from pinbank.services_transacoes_pagamento import TransacoesPinbankService
        
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            
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
            
            # Chamar API Pinbank para tokenizar
            # USANDO EXATAMENTE O MESMO PAYLOAD DO LINK DE PAGAMENTO (testado)
            pinbank_service = TransacoesPinbankService(loja_id=cliente.loja_id)
            
            cpf_limpo = cliente.cpf.replace('.', '').replace('-', '')
            
            payload_tokenizacao = {
                'numero_cartao': numero,
                'data_validade': validade,  # MM/YY
                'codigo_seguranca': cvv,
                'nome_impresso': nome_titular.upper(),
                'cpf_comprador': int(cpf_limpo)
            }
            
            registrar_log('checkout', f"Iniciando tokenização para cliente {cliente_id}")
            
            resultado = pinbank_service.incluir_cartao_tokenizado(payload_tokenizacao)
            
            # Logar resposta completa do Pinbank
            registrar_log('checkout', f"Resposta Pinbank: {resultado}")
            
            if not resultado.get('sucesso'):
                mensagem = resultado.get('mensagem', 'Erro ao tokenizar cartão')
                erro_detalhe = resultado.get('erro', '')
                registrar_log('checkout', f"Erro tokenização: {mensagem} | Detalhe: {erro_detalhe}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': f"{mensagem} - {erro_detalhe}" if erro_detalhe else mensagem
                }
            
            # Extrair token (Pinbank retorna 'cartao_id')
            cartao_id = resultado.get('cartao_id')
            
            if not cartao_id:
                raise ValidationError('Token não retornado pelo Pinbank')
            
            # Gerar máscara do cartão (primeiros 6 + últimos 4 dígitos)
            # MESMO PADRÃO DO LINK DE PAGAMENTO
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
            
            # Salvar cartão tokenizado
            # USANDO EXATAMENTE OS MESMOS CAMPOS DO LINK DE PAGAMENTO (testado)
            cartao = CheckoutCartaoTokenizado.objects.create(
                cliente=cliente,
                id_token=cartao_id,
                cartao_mascarado=cartao_mascarado,
                bandeira=bandeira,
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
        """Lista cartões do cliente"""
        filtros = {'cliente_id': cliente_id}
        if apenas_validos:
            filtros['valido'] = True
        
        return CheckoutCartaoTokenizado.objects.filter(**filtros).order_by('-created_at')
    
    @staticmethod
    def invalidar_cartao(cartao_id: int):
        """Invalida cartão (soft delete)"""
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
            cartao.valido = False
            cartao.save()
            
            registrar_log('checkout', f"Cartão invalidado: {cartao_id}")
            
        except CheckoutCartaoTokenizado.DoesNotExist:
            raise ValidationError('Cartão não encontrado')
    
    @staticmethod
    def excluir_cartao_pinbank(cartao_id: int) -> Dict[str, Any]:
        """
        Exclui cartão do Pinbank e invalida localmente
        
        Args:
            cartao_id: ID do cartão local
            
        Returns:
            Dict com sucesso e mensagem
        """
        from pinbank.services_transacoes_pagamento import TransacoesPinbankService
        
        try:
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id)
            
            # Chamar API Pinbank para excluir
            pinbank_service = TransacoesPinbankService(loja_id=cartao.cliente.loja_id)
            resultado = pinbank_service.excluir_cartao_tokenizado(cartao.id_token)
            
            # Invalidar localmente independente do resultado
            cartao.valido = False
            cartao.save()
            
            if resultado.get('sucesso'):
                registrar_log('checkout', f"Cartão excluído do Pinbank: {cartao_id}")
            else:
                registrar_log('checkout', f"Erro ao excluir do Pinbank: {resultado.get('mensagem')}", nivel='WARNING')
            
            return resultado
            
        except CheckoutCartaoTokenizado.DoesNotExist:
            raise ValidationError('Cartão não encontrado')


class CheckoutService:
    """Serviço para processar pagamentos de checkout"""
    
    @staticmethod
    @transaction.atomic
    def processar_pagamento_cartao_tokenizado(
        cliente_id: int,
        cartao_id: int,
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
        Processa pagamento usando cartão tokenizado
        
        Args:
            cliente_id: ID do cliente
            cartao_id: ID do cartão tokenizado
            valor: Valor da transação
            parcelas: Número de parcelas
            bandeira: Bandeira do cartão
            descricao: Descrição da compra
            ip_address: IP do cliente
            user_agent: User agent
            pedido_origem_loja: ID do pedido no sistema da loja
            
        Returns:
            Dict com sucesso, nsu, codigo_autorizacao, mensagem
        """
        from pinbank.services_transacoes_pagamento import TransacoesPinbankService
        
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            cartao = CheckoutCartaoTokenizado.objects.get(id=cartao_id, cliente=cliente, valido=True)
            
            # Validar valor
            if valor <= 0:
                raise ValidationError('Valor deve ser maior que zero')
            
            # Buscar bandeira do cartão tokenizado (ignora parâmetro bandeira)
            bandeira_cartao = cartao.bandeira
            
            # Preparar dados da transação
            pinbank_service = TransacoesPinbankService(loja_id=cliente.loja_id)
            
            # Garantir que valor seja Decimal
            if not isinstance(valor, Decimal):
                valor = Decimal(str(valor))
            
            # Usar valor_transacao_final se fornecido (valor com desconto das parcelas)
            valor_para_transacao = valor_transacao_final if valor_transacao_final is not None else valor
            
            # CPF/CNPJ como int (remover zeros à esquerda)
            cpf_cnpj = cliente.cpf or cliente.cnpj
            cpf_cnpj_int = int(cpf_cnpj) if cpf_cnpj else 0
            
            payload_transacao = {
                'cartao_id': cartao.id_token,  # snake_case
                'valor': valor_para_transacao,  # Valor em reais (Decimal) - conversão para centavos feita no Pinbank
                'quantidade_parcelas': parcelas,
                'forma_pagamento': '1',  # Cartão de crédito
                'descricao_pedido': descricao,
                'ip_address_comprador': ip_address,
                'cpf_comprador': cpf_cnpj_int,  # CPF como int
                'nome_comprador': cliente.nome
            }
            
            registrar_log('checkout', f"Processando pagamento cliente {cliente_id} - R$ {valor}")
            
            # Processar via Pinbank
            resultado = pinbank_service.efetuar_transacao_cartao_tokenizado(payload_transacao)
            
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
                nsu=nsu,
                codigo_autorizacao=codigo_autorizacao,
                valor_transacao_original=valor_original,
                valor_transacao_final=valor_final,
                status=status,
                forma_pagamento=f"{bandeira_cartao}_{parcelas}x",
                parcelas=parcelas,
                pedido_origem_loja=pedido_origem_loja,
                cod_item_origem_loja=cod_item_origem_loja,
                vendedor_id=portais_usuarios_id,
                pinbank_response=resultado.get('resposta_completa'),
                erro_pinbank=erro_pinbank,
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
            registrar_log('checkout', f"Erro ao processar pagamento: {str(e)}", nivel='ERROR')
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
        from pinbank.services_transacoes_pagamento import TransacoesPinbankService
        
        try:
            cliente = CheckoutCliente.objects.get(id=cliente_id)
            
            if valor <= 0:
                raise ValidationError('Valor deve ser maior que zero')
            
            if not all([numero_cartao, validade, cvv, nome_titular, bandeira]):
                raise ValidationError('Dados do cartão incompletos')
            
            pinbank_service = TransacoesPinbankService(loja_id=cliente.loja_id)
            
            # CPF/CNPJ como int (remover zeros à esquerda)
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
                'forma_pagamento': '1',  # Cartão de crédito
                'descricao_pedido': descricao,
                'ip_address_comprador': ip_address,
                'cpf_comprador': cpf_cnpj_int,  # CPF como int
                'nome_comprador': cliente.nome
            }
            
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
            
            # Processar via Pinbank (cartão direto - não tokenizado)
            resultado = pinbank_service.efetuar_transacao_cartao(payload_transacao)
            
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
                nsu=nsu,
                codigo_autorizacao=codigo_autorizacao,
                valor_transacao_original=valor,
                valor_transacao_final=valor,
                status=status,
                forma_pagamento=f"{bandeira}_{parcelas}x",
                parcelas=parcelas,
                pedido_origem_loja=pedido_origem_loja,
                cod_item_origem_loja=cod_item_origem_loja,
                vendedor_id=portais_usuarios_id,
                pinbank_response=resultado.get('resposta_completa'),
                erro_pinbank=erro_pinbank,
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
                    
                    parcelas_resultado['CREDITO_1X'] = {
                        'num_parcelas': 1,
                        'valor_parcela': float(valor_avista),
                        'valor_desconto': float(valor_avista),
                        'descricao': descricao,
                        'cashback': 0
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
                        
                        parcelas_resultado[f'CREDITO_{num_parcelas}X'] = {
                            'num_parcelas': num_parcelas,
                            'valor_parcela': float(valor_parcela),
                            'valor_desconto': float(valor_parcelado),
                            'descricao': descricao,
                            'cashback': 0
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
            # URL do checkout com token
            checkout_url = f"{settings.BASE_URL}/api/v1/checkout/?token={token.token}"
            
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
