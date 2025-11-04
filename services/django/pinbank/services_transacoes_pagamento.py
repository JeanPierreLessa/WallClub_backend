"""
Serviço para processamento de transações via API Pinbank
"""
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal
import requests
from datetime import datetime
from django.conf import settings
from pinbank.services import PinbankService
from wallclub_core.utilitarios.log_control import registrar_log

# Mapeamento de tipos de compra para a API Pinbank
TIPO_COMPRA_MAP = {
    'CREDIT_IN_INSTALLMENTS_WITHOUT_INTEREST': '2',
    'CREDIT_ONE_INSTALLMENT': '1',
}


class TransacoesPinbankService:
    """Serviço para processamento de transações via API Pinbank"""

    def __init__(self, loja_id: int = None):
        self.pinbank_service = PinbankService()
        self.loja_id = loja_id

    def _obter_credenciais_loja(self, loja_id: int = None) -> Dict[str, Any]:
        """Obtém credenciais da loja para autenticação na API Pinbank"""
        from wallclub_core.estr_organizacional.loja import Loja

        # Usar loja_id passado como parâmetro ou do construtor
        id_loja = loja_id or self.loja_id

        if not id_loja:
            raise ValueError("loja_id não fornecido. Informe no construtor ou como parâmetro.")

        try:
            from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
            loja = HierarquiaOrganizacionalService.get_loja(id_loja)

            if not loja:
                raise ValueError(f"Loja {id_loja} não encontrada")

            # Validar se loja tem credenciais Pinbank configuradas
            if not all([loja.pinbank_CodigoCanal, loja.pinbank_CodigoCliente, loja.pinbank_KeyValueLoja]):
                raise ValueError(f"Loja {id_loja} não possui credenciais Pinbank configuradas")

            return {
                'codigo_canal': loja.pinbank_CodigoCanal,
                'codigo_cliente': loja.pinbank_CodigoCliente,
                'key_loja': loja.pinbank_KeyValueLoja
            }
        except Loja.DoesNotExist:
            raise ValueError(f"Loja {id_loja} não encontrada")

    def _fazer_requisicao_criptografada(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Método genérico para fazer requisições criptografadas à API Pinbank

        Args:
            endpoint: Endpoint da API (ex: "Transacoes/EfetuarTransacaoEncrypted")
            payload: Dados a serem enviados

        Returns:
            Dict com resposta descriptografada ou erro
        """
        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento', f"=== INICIANDO REQUISIÇÃO CRIPTOGRAFADA ===")
            registrar_log('pinbank.transacoes_pagamento', f"Endpoint: {endpoint}")
            registrar_log('pinbank.transacoes_pagamento', f"Payload original: {payload}")

            # 1. Obter token de autenticação
            registrar_log('pinbank.transacoes_pagamento', f"PASSO 1: Obtendo token de autenticação...")
            token_data = self.pinbank_service.obter_token()

            if not token_data or not token_data.get('access_token'):
                registrar_log('pinbank.transacoes_pagamento', f"ERRO: Token de autenticação vazio - obter_token() retornou: {token_data}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro de autenticação com Pinbank'
                }

            access_token = token_data['access_token']
            token_type = token_data.get('token_type', 'Bearer')
            registrar_log('pinbank.transacoes_pagamento', f"✅ Token obtido com sucesso: {str(access_token)[:20]}... (tipo: {token_type})")

            # 2. Criptografar payload
            registrar_log('pinbank.transacoes_pagamento', f"PASSO 2: Criptografando payload...")
            payload_criptografado = self.pinbank_service.criptografar_payload(payload)

            if not payload_criptografado:
                registrar_log('pinbank.transacoes_pagamento', f"ERRO: Payload criptografado vazio - criptografar_payload() retornou: {payload_criptografado}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar dados da requisição'
                }

            registrar_log('pinbank.transacoes_pagamento', f"✅ Payload criptografado: {str(payload_criptografado)[:100]}...")

            # 3. Fazer requisição para API
            url_endpoint = f"{settings.PINBANK_URL}{endpoint}"
            headers = {
                'Authorization': f'{token_type} {access_token}',
                'UserName': self.pinbank_service.username,
                'RequestOrigin': '5',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }

            registrar_log('pinbank.transacoes_pagamento', f"PASSO 3: Fazendo requisição HTTP...")
            registrar_log('pinbank.transacoes_pagamento', f"URL: {url_endpoint}")
            registrar_log('pinbank.transacoes_pagamento', f"Headers: {headers}")

            import requests
            import json

            try:
                payload_json = json.loads(payload_criptografado)
                registrar_log('pinbank.transacoes_pagamento', f"Payload JSON válido: {str(payload_json)[:200]}...")
            except json.JSONDecodeError as je:
                registrar_log('pinbank.transacoes_pagamento', f"ERRO: Payload não é JSON válido: {str(je)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro no formato do payload criptografado'
                }

            response = requests.post(
                url_endpoint,
                json=payload_json,
                headers=headers,
                timeout=30,
                verify=False
            )

            registrar_log('pinbank.transacoes_pagamento', f"✅ Requisição enviada")
            registrar_log('pinbank.transacoes_pagamento', f"Status Code: {response.status_code}")
            registrar_log('pinbank.transacoes_pagamento', f"Response Headers: {dict(response.headers)}")
            registrar_log('pinbank.transacoes_pagamento', f"Response Text: {response.text}")

            if response.status_code != 200:
                registrar_log('pinbank.transacoes_pagamento', f"ERRO HTTP {response.status_code}: {response.text}", nivel='ERROR')
                registrar_log('pinbank.transacoes_pagamento', f"Response completa: {response.text}")
                return {
                    'sucesso': False,
                    'mensagem': f'Erro na comunicação com Pinbank: {response.status_code}'
                }

            # 4. Descriptografando resposta
            registrar_log('pinbank.transacoes_pagamento', f"PASSO 4: Descriptografando resposta...")

            try:
                resposta_json = response.json()
                registrar_log('pinbank.transacoes_pagamento', f"Resposta JSON: {resposta_json}")
            except json.JSONDecodeError as je:
                registrar_log('pinbank.transacoes_pagamento', f"ERRO: Resposta não é JSON válido: {str(je)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro no formato da resposta da API'
                }

            # Verificar se há dados criptografados para descriptografar
            if resposta_json.get('Data') and resposta_json.get('Data', {}).get('Json'):
                # Resposta com dados criptografados - mas pode ter erro no ResultCode
                result_code = resposta_json.get('ResultCode', -1)
                message = resposta_json.get('Message', '')

                registrar_log('pinbank.transacoes_pagamento', f"Resposta com dados criptografados - ResultCode: {result_code}")

                # Se há erro no ResultCode, retornar erro sem tentar descriptografar
                if result_code != 0:
                    registrar_log('pinbank.transacoes_pagamento', f"❌ Erro na API - ResultCode: {result_code}, Message: {message}", nivel='ERROR')
                    return {
                        'sucesso': False,
                        'mensagem': message or 'Erro na API Pinbank',
                        'result_code': result_code,
                        'resposta_completa': resposta_json
                    }

                # ResultCode 0 - tentar descriptografar
                registrar_log('pinbank.transacoes_pagamento', f"Descriptografando dados...")
                try:
                    resposta_para_descriptografar = json.dumps({
                        "Data": {
                            "Json": resposta_json['Data']['Json']
                        }
                    })
                    resposta_descriptografada = self.pinbank_service.descriptografar_payload(resposta_para_descriptografar)

                    registrar_log('pinbank.transacoes_pagamento', f"✅ Resposta descriptografada: {resposta_descriptografada}")
                    return {
                        'sucesso': True,
                        'dados': resposta_descriptografada,
                        'resposta_completa': resposta_json
                    }
                except Exception as desc_error:
                    registrar_log('pinbank.transacoes_pagamento', f"❌ ERRO na descriptografia: {str(desc_error)}", nivel='ERROR')
                    return {
                        'sucesso': False,
                        'mensagem': f'Erro ao descriptografar resposta: {str(desc_error)}'
                    }
            else:
                # Resposta não criptografada - verificar ResultCode
                result_code = resposta_json.get('ResultCode', -1)
                message = resposta_json.get('Message', '')

                registrar_log('pinbank.transacoes_pagamento', f"Resposta não criptografada - ResultCode: {result_code}, Message: {message}")

                if result_code == 0:
                    # Sucesso sem dados criptografados (ex: exclusão)
                    return {
                        'sucesso': True,
                        'mensagem': message or 'Operação realizada com sucesso',
                        'dados': {},
                        'resposta_completa': resposta_json
                    }
                else:
                    return {
                        'sucesso': False,
                        'mensagem': message or 'Erro ao processar resposta da API',
                        'result_code': result_code,
                        'resposta_completa': resposta_json
                    }

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"EXCEÇÃO na requisição criptografada: {str(e)}", nivel='ERROR')
            import traceback
            registrar_log('pinbank.transacoes_pagamento', f"Traceback: {traceback.format_exc()}")
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar requisição'
            }

    def efetuar_transacao_cartao(self, dados_transacao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Efetua transação via API Pinbank usando endpoint /Transacoes/EfetuarTransacaoEncrypted

        Args:
            dados_transacao: Dicionário com dados da transação do checkout

        Returns:
            Dict com resultado da transação
        """
        # Log detalhado de TODOS os dados recebidos do checkout
        from wallclub_core.utilitarios.log_control import registrar_log
        registrar_log("pinbank.transacoes_pagamento", "=== DADOS RECEBIDOS DO CHECKOUT (efetuar_transacao_cartao) ===")
        for chave, valor in dados_transacao.items():
            registrar_log("pinbank.transacoes_pagamento", f"{chave}: {valor} (tipo: {type(valor).__name__})")
        registrar_log("pinbank.transacoes_pagamento", "=== FIM DADOS CHECKOUT ===")

        # Log específico da data de validade
        data_validade_original = dados_transacao.get('data_validade')
        registrar_log("pinbank.transacoes_pagamento", f"Data validade ORIGINAL recebida: '{data_validade_original}' (tipo: {type(data_validade_original).__name__})")

        def _converter_data_validade(data_validade: str) -> str:
            """Converte data de validade de MM/YYYY para YYYYMM"""
            if '/' in data_validade:
                mes, ano = data_validade.split('/')
                return f"{ano}{mes.zfill(2)}"
            return data_validade

        def _montar_payload_transacao(dados: Dict[str, Any]) -> Dict[str, Any]:
            """Monta payload específico da transação"""
            # Validar campos obrigatórios
            campos_obrigatorios = [
                'nome_impresso', 'data_validade', 'numero_cartao',
                'codigo_seguranca', 'valor', 'descricao_pedido',
                'ip_address_comprador', 'cpf_comprador', 'nome_comprador'
            ]

            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    raise ValueError(f"Campo obrigatório '{campo}' não fornecido")

            # Obter credenciais dinâmicas
            credenciais = self._obter_credenciais_loja()

            # Converter data de validade para formato YYYYMM
            data_validade = _converter_data_validade(dados.get('data_validade'))

            # Determinar FormaPagamento baseado em parcelas
            qtd_parcelas = dados.get('quantidade_parcelas', 1)
            # Converter para int se vier como string
            if isinstance(qtd_parcelas, str):
                qtd_parcelas = int(qtd_parcelas)
            forma_pagamento = '1' if qtd_parcelas == 1 else '2'

            # Converter valor de reais para centavos (exemplo: 10.50 -> 1050)
            valor = dados.get('valor')
            if isinstance(valor, (Decimal, float)):
                valor = int(valor * 100)
            else:
                valor = int(valor * 100)

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "KeyLoja": credenciais['key_loja'],
                    "NomeImpresso": dados.get('nome_impresso'),
                    "DataValidade": data_validade,
                    "NumeroCartao": dados.get('numero_cartao'),
                    "CodigoSeguranca": dados.get('codigo_seguranca'),
                    "Valor": valor,
                    "FormaPagamento": forma_pagamento,
                    "QuantidadeParcelas": qtd_parcelas,
                    "DescricaoPedido": dados.get('descricao_pedido'),
                    "IpAddressComprador": dados.get('ip_address_comprador'),
                    "CpfComprador": dados.get('cpf_comprador'),
                    "NomeComprador": dados.get('nome_comprador'),
                    "TransacaoPreAutorizada": dados.get('transacao_pre_autorizada', False)
                }
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload montado: {payload}")
            return payload

        def _processar_resposta_transacao(resposta: Dict[str, Any], dados_originais: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da transação"""
            try:
                registrar_log('pinbank.transacoes_pagamento', f"Processando resposta: {resposta}")
                registrar_log('pinbank.transacoes_pagamento', f"Dados originais: {dados_originais}")

                # Verificar se a resposta tem NSU e Código de Autorização (transação aprovada)
                if 'NsuOperacao' in resposta and 'CodigoAutorizacao' in resposta:
                    nsu_operacao = resposta.get('NsuOperacao', '')
                    codigo_autorizacao = resposta.get('CodigoAutorizacao', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação APROVADA - NSU: {nsu_operacao}, Autorização: {codigo_autorizacao}")

                    return {
                        'sucesso': True,
                        'mensagem': 'Transação aprovada com sucesso',
                        'dados': {
                            'nsu': nsu_operacao,
                            'codigo_autorizacao': codigo_autorizacao,
                            'result_code': 0,
                            'valor': dados_originais.get('valor', 0),
                            'forma_pagamento': dados_originais.get('forma_pagamento', ''),
                            'cpf_comprador': dados_originais.get('cpf_comprador', ''),
                            'nome_comprador': dados_originais.get('nome_comprador', '')
                        }
                    }

                # Fallback para formato com ResultCode
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                # ResultCode 0 = sucesso
                if result_code == 0:
                    # Para transação com cartão direto, os dados podem estar no wrapper "Data"
                    dados_resposta = data if data else resposta
                    codigo_autorizacao = dados_resposta.get('CodigoAutorizacao', '')
                    nsu_operacao = dados_resposta.get('NsuOperacao', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação APROVADA - NSU: {nsu_operacao}, Autorização: {codigo_autorizacao}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Transação aprovada com sucesso',
                        'dados': {
                            'nsu': nsu_operacao,
                            'codigo_autorizacao': codigo_autorizacao,
                            'result_code': result_code,
                            'valor': dados_originais.get('valor', 0),
                            'forma_pagamento': dados_originais.get('forma_pagamento', ''),
                            'cpf_comprador': dados_originais.get('cpf_comprador', ''),
                            'nome_comprador': dados_originais.get('nome_comprador', '')
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    validation_result_code = validation_data.get('ResultCode', result_code)
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Transação não autorizada'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação NEGADA - ResultCode: {result_code}, ValidationCode: {validation_result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'validation_result_code': validation_result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da transação: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da transação'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando efetuar_transacao_encrypted - CPF: {dados_transacao.get('cpf_comprador')}")

            # 1. Montar payload da transação
            payload_transacao = _montar_payload_transacao(dados_transacao)

            registrar_log('pinbank.transacoes_pagamento',
                         f"Payload montado - Valor: {payload_transacao['Data']['Valor']}, "
                         f"Forma: {payload_transacao['Data']['FormaPagamento']}")

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/EfetuarTransacaoEncrypted",
                payload_transacao
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da transação
            resposta_descriptografada = resultado['dados']

            registrar_log('pinbank.transacoes_pagamento',
                         f"Transação processada - Sucesso: {resposta_descriptografada.get('sucesso', False)}")

            return _processar_resposta_transacao(resposta_descriptografada, dados_transacao)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao efetuar transação: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar transação'
            }

    def incluir_cartao_tokenizado(self, dados_cartao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inclui cartão tokenizado via API Pinbank usando endpoint /Transacoes/IncluirCartaoEncrypted

        Args:
            dados_cartao: Dicionário com dados do cartão

        Returns:
            Dict com resultado da inclusão (CartaoId)
        """

        def _converter_data_validade(data_validade: str) -> str:
            """Converte data de validade de MM/YYYY para YYYYMM"""
            if '/' in data_validade:
                mes, ano = data_validade.split('/')
                return f"{ano}{mes.zfill(2)}"
            return data_validade

        def _montar_payload_cartao(dados: Dict[str, Any]) -> Dict[str, Any]:
            """Monta payload específico para inclusão de cartão"""
            # Obter credenciais dinâmicas
            credenciais = self._obter_credenciais_loja()

            # Converter data de validade para formato YYYYMM
            data_validade = _converter_data_validade(dados.get('data_validade'))

            # Gerar Apelido único: codigo_cliente-cpf_cliente-ultimos_4_digitos
            # Permite mesmo cartão em clientes diferentes
            numero_cartao = dados.get('numero_cartao').replace(' ', '')
            ultimos_4_digitos = numero_cartao[-4:]
            cpf_comprador = str(dados.get('cpf_comprador', '')).replace('.', '').replace('-', '')
            apelido = f"{credenciais['codigo_cliente']}-{cpf_comprador[-4:]}-{ultimos_4_digitos}"

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "KeyLoja": credenciais['key_loja'],  # ← FALTAVA
                    "Apelido": apelido,
                    "NomeImpresso": dados.get('nome_impresso'),
                    "NumeroCartao": numero_cartao,
                    "DataValidade": data_validade,
                    "CodigoSeguranca": dados.get('codigo_seguranca'),
                    "ValidarCartao": False
                }
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload cartão montado: {payload}")
            return payload

        def _processar_resposta_cartao(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da inclusão de cartão"""
            try:
                # Verificar se resposta é válida
                if resposta is None:
                    registrar_log('pinbank.transacoes_pagamento', "❌ Resposta é None")
                    return {
                        'sucesso': False,
                        'mensagem': 'Resposta vazia da API'
                    }

                if not isinstance(resposta, dict):
                    registrar_log('pinbank.transacoes_pagamento', f"❌ Resposta não é dict: {type(resposta)}")
                    return {
                        'sucesso': False,
                        'mensagem': 'Formato de resposta inválido'
                    }

                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    cartao_id = data.get('CartaoId', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Cartão INCLUÍDO com sucesso - CartaoId: {cartao_id}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Cartão tokenizado com sucesso',
                        'dados': {
                            'cartao_id': cartao_id,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao tokenizar cartão'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao incluir cartão - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta do cartão: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da tokenização'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando incluir_cartao_tokenizado - Apelido: {dados_cartao.get('apelido')}")

            # 1. Montar payload do cartão
            payload_cartao = _montar_payload_cartao(dados_cartao)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/IncluirCartaoEncrypted",
                payload_cartao
            )

            # 3. Processar resposta específica do cartão
            if not resultado['sucesso']:
                # Erro já tratado pelo método genérico - repassar com detalhes específicos
                return {
                    'sucesso': False,
                    'mensagem': resultado.get('mensagem', 'Erro na tokenização'),
                    'result_code': resultado.get('result_code', -1)
                }

            # Sucesso - dados descriptografados já contêm CartaoId
            dados_descriptografados = resultado.get('dados', {})
            cartao_id = dados_descriptografados.get('CartaoId', '')

            if not cartao_id:
                registrar_log('pinbank.transacoes_pagamento', f"Erro: CartaoId não encontrado na resposta: {dados_descriptografados}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Token não retornado pelo Pinbank'
                }

            registrar_log('pinbank.transacoes_pagamento', f"Cartão INCLUÍDO com sucesso - CartaoId: {cartao_id}")

            return {
                'sucesso': True,
                'mensagem': 'Cartão tokenizado com sucesso',
                'cartao_id': cartao_id
            }

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao incluir cartão tokenizado: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar cartão'
            }

    def excluir_cartao_tokenizado(self, cartao_id: str) -> Dict[str, Any]:
        """
        Exclui cartão tokenizado via API Pinbank usando endpoint /Cartoes/ExcluirCartaoEncrypted

        Args:
            cartao_id: ID do cartão tokenizado

        Returns:
            Dict com resultado da exclusão
        """

        def _montar_payload_exclusao(cartao_id: str) -> Dict[str, Any]:
            """Monta payload específico para exclusão de cartão"""
            # Usar credenciais corretas como na inclusão e consulta
            payload = {
                "Data": {
                    "CodigoCanal": 47,
                    "CodigoCliente": 3510,
                    "CartaoId": cartao_id
                }
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload exclusão montado: {payload}")
            return payload

        def _processar_resposta_exclusao(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da exclusão de cartão"""
            try:
                # A resposta da exclusão vem vazia {}, então consideramos sucesso
                # se chegou até aqui sem erro
                if not resposta or resposta == {}:
                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Cartão EXCLUÍDO com sucesso - CartaoId: {cartao_id}")

                    return {
                        'sucesso': True,
                        'mensagem': 'Cartão excluído com sucesso',
                        'dados': {
                            'cartao_id': cartao_id
                        }
                    }

                # Fallback para formato com ResultCode
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Cartão EXCLUÍDO com sucesso - CartaoId: {cartao_id}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Cartão excluído com sucesso',
                        'dados': {
                            'cartao_id': cartao_id,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao excluir cartão'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao excluir cartão - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da exclusão: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da exclusão'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando excluir_cartao_tokenizado - CartaoId: {cartao_id}")

            # 1. Montar payload da exclusão
            payload_exclusao = _montar_payload_exclusao(cartao_id)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/ExcluirCartaoEncrypted",
                payload_exclusao
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da exclusão
            resposta_descriptografada = resultado['dados']

            return _processar_resposta_exclusao(resposta_descriptografada)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao excluir cartão tokenizado: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao excluir cartão'
            }

    def consulta_dados_cartao_tokenizado(self, cartao_id: str) -> Dict[str, Any]:
        """
        Consulta dados do cartão tokenizado via API Pinbank usando endpoint /Transacoes/ConsultarDadosCartaoEncrypted

        Args:
            cartao_id: ID do cartão tokenizado

        Returns:
            Dict com dados do cartão
        """

        def _montar_payload_consulta(cartao_id: str) -> Dict[str, Any]:
            """Monta payload específico para consulta de cartão"""
            # Usar credenciais corretas como na inclusão
            payload = {
                "Data": {
                    "CodigoCanal": 47,
                    "CodigoCliente": 3510,
                    "CartaoId": cartao_id
                }
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload consulta montado: {payload}")
            return payload

        def _processar_resposta_consulta(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da consulta de cartão"""
            try:
                # A resposta da consulta vem diretamente com os dados do cartão
                # não tem ResultCode como nas outras operações
                if 'Apelido' in resposta:
                    dados_cartao = {
                        'apelido': resposta.get('Apelido', ''),
                        'data_validade': resposta.get('DataValidade', ''),
                        'bandeira': resposta.get('Bandeira', ''),
                        'status': resposta.get('Status', ''),
                        'cartao_id': resposta.get('CartaoId', ''),
                        'nome_impresso': resposta.get('NomeImpresso', ''),
                        'numero_cartao': resposta.get('NumeroCartao', '')
                    }

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Dados do cartão consultados - CartaoId: {cartao_id}, Status: {dados_cartao['status']}")

                    return {
                        'sucesso': True,
                        'mensagem': 'Dados do cartão consultados com sucesso',
                        'dados': dados_cartao
                    }
                else:
                    # Fallback para formato com ResultCode
                    result_code = resposta.get('ResultCode', -1)
                    message = resposta.get('Message', '')
                    data = resposta.get('Data', {})
                    validation_data = resposta.get('ValidationData', {})

                    if result_code == 0:
                        dados_cartao = {
                            'apelido': data.get('Apelido', ''),
                            'data_validade': data.get('DataValidade', ''),
                            'bandeira': data.get('Bandeira', ''),
                            'status': data.get('Status', ''),
                            'cartao_id': data.get('CartaoId', ''),
                            'nome_impresso': data.get('NomeImpresso', ''),
                            'numero_cartao': data.get('NumeroCartao', '')
                        }

                        return {
                            'sucesso': True,
                            'mensagem': message or 'Dados do cartão consultados com sucesso',
                            'dados': dados_cartao
                        }
                    else:
                        validation_message = validation_data.get('Message', '')
                        errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao consultar dados do cartão'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao consultar cartão - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da consulta: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da consulta'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando consulta_dados_cartao_tokenizado - CartaoId: {cartao_id}")

            # 1. Montar payload da consulta
            payload_consulta = _montar_payload_consulta(cartao_id)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/ConsultarDadosCartaoEncrypted",
                payload_consulta
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da consulta
            resposta_descriptografada = resultado['dados']

            return _processar_resposta_consulta(resposta_descriptografada)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao consultar dados do cartão: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao consultar cartão'
            }

    def ativar_cartao_tokenizado(self, cartao_id: str, protocolo_ativacao: int = 1) -> Dict[str, Any]:
        """
        Ativa cartão tokenizado via API Pinbank usando endpoint /Cartoes/AtivarCartaoEncrypted

        Args:
            cartao_id: ID do cartão tokenizado
            protocolo_ativacao: Protocolo de ativação (default: 1)

        Returns:
            Dict com resultado da ativação
        """

        def _montar_payload_ativacao(cartao_id: str, protocolo: int) -> Dict[str, Any]:
            """Monta payload específico para ativação de cartão"""
            # Obter credenciais dinâmicas
            credenciais = self._obter_credenciais_loja()

            payload = {
                "CodigoCanal": credenciais['codigo_canal'],
                "CodigoCliente": credenciais['codigo_cliente'],
                "CartaoId": cartao_id,
                "ProtocoloAtivacao": protocolo
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload ativação montado: {payload}")
            return payload

        def _processar_resposta_ativacao(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da ativação de cartão"""
            try:
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Cartão ATIVADO com sucesso - CartaoId: {cartao_id}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Cartão ativado com sucesso',
                        'dados': {
                            'cartao_id': cartao_id,
                            'protocolo_ativacao': protocolo_ativacao,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao ativar cartão'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao ativar cartão - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da ativação: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da ativação'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando ativar_cartao_tokenizado - CartaoId: {cartao_id}, Protocolo: {protocolo_ativacao}")

            # 1. Montar payload da ativação
            payload_ativacao = _montar_payload_ativacao(cartao_id, protocolo_ativacao)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/AtivarCartaoEncrypted",
                payload_ativacao
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da ativação
            resposta_descriptografada = resultado['dados']

            return _processar_resposta_ativacao(resposta_descriptografada)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao ativar cartão tokenizado: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao ativar cartão'
            }

    def consultar_cartoes(self, status_cartao: str = "Todos", numero_truncado: str = "") -> Dict[str, Any]:
        """
        Consulta cartões tokenizados via API Pinbank usando endpoint /Transacoes/ConsultarCartoes

        Args:
            status_cartao: Status dos cartões a consultar (Todos, Ativo, Inativo, etc)
            numero_truncado: Número truncado do cartão para filtro (opcional)

        Returns:
            Dict com lista de cartões
        """

        def _montar_payload_consulta_cartoes(status: str, numero: str) -> Dict[str, Any]:
            """Monta payload específico para consulta de cartões"""
            # Obter credenciais dinâmicas
            credenciais = self._obter_credenciais_loja()

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "StatusCartao": status,
                    "NumeroTruncado": numero
                }
            }
            registrar_log('pinbank.transacoes_pagamento', f"Payload consulta cartões montado: {payload}")
            return payload

        def _processar_resposta_consulta_cartoes(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da consulta de cartões"""
            try:
                registrar_log('pinbank.transacoes_pagamento', f"Processando resposta consulta cartões: {resposta}")

                # Verificar se há lista de cartões diretamente
                if isinstance(resposta, list):
                    # Resposta é direto a lista de cartões
                    cartoes = []
                    for cartao in resposta:
                        cartoes.append({
                            'apelido': cartao.get('Apelido', ''),
                            'data_validade': cartao.get('DataValidade', ''),
                            'bandeira': cartao.get('Bandeira', ''),
                            'status': cartao.get('Status', ''),
                            'cartao_id': cartao.get('CartaoId', ''),
                            'nome_impresso': cartao.get('NomeImpresso', ''),
                            'numero_cartao': cartao.get('NumeroCartao', '')
                        })

                    registrar_log('pinbank.transacoes_pagamento',
                                f"Consulta de cartões realizada - {len(cartoes)} cartão(ões) encontrado(s)")

                    return {
                        'sucesso': True,
                        'mensagem': f'{len(cartoes)} cartão(ões) encontrado(s)',
                        'dados': {
                            'cartoes': cartoes,
                            'total': len(cartoes)
                        }
                    }

                # Verificar formato com ResultCode
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', [])
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    # Sucesso - processar lista de cartões
                    cartoes = []

                    # Data pode ser lista ou dict
                    lista_cartoes = data if isinstance(data, list) else []

                    for cartao in lista_cartoes:
                        cartoes.append({
                            'apelido': cartao.get('Apelido', ''),
                            'data_validade': cartao.get('DataValidade', ''),
                            'bandeira': cartao.get('Bandeira', ''),
                            'status': cartao.get('Status', ''),
                            'cartao_id': cartao.get('CartaoId', ''),
                            'nome_impresso': cartao.get('NomeImpresso', ''),
                            'numero_cartao': cartao.get('NumeroCartao', '')
                        })

                    registrar_log('pinbank.transacoes_pagamento',
                                f"Consulta de cartões realizada - {len(cartoes)} cartão(ões) encontrado(s)")

                    return {
                        'sucesso': True,
                        'mensagem': message or f'{len(cartoes)} cartão(ões) encontrado(s)',
                        'dados': {
                            'cartoes': cartoes,
                            'total': len(cartoes)
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao consultar cartões'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                f"Erro ao consultar cartões - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da consulta de cartões: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da consulta'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                        f"Iniciando consultar_cartoes - Status: {status_cartao}, NumeroTruncado: {numero_truncado}")

            # 1. Montar payload da consulta
            payload_consulta = _montar_payload_consulta_cartoes(status_cartao, numero_truncado)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/ConsultarCartoesEncrypted",
                payload_consulta
            )

            # Logar resposta completa
            registrar_log('pinbank.transacoes_pagamento', f"Resposta consulta cartões: {resultado}")

            # 3. Verificar se houve erro na requisição
            if not resultado['sucesso']:
                # Logar erro detalhado
                erro_msg = resultado.get('mensagem', 'Erro ao consultar cartões')
                erro_code = resultado.get('result_code', -1)
                registrar_log('pinbank.transacoes_pagamento', f"Erro na consulta: {erro_msg} (code: {erro_code})", nivel='ERROR')

                return {
                    'sucesso': False,
                    'mensagem': erro_msg,
                    'result_code': erro_code
                }

            # 4. Processar resposta descriptografada
            resposta_para_processar = resultado.get('dados', {})
            return _processar_resposta_consulta_cartoes(resposta_para_processar)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao consultar cartões: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao consultar cartões'
            }

    def efetuar_transacao_cartao_tokenizado(self, dados_transacao: Dict[str, Any]) -> Dict[str, Any]:
        """
        Efetua transação com cartão tokenizado via API Pinbank usando endpoint /Transacoes/EfetuarTransacaoCartaoIdEncrypted

        Args:
            dados_transacao: Dicionário com dados da transação

        Returns:
            Dict com resultado da transação
        """

        def _montar_payload_transacao_token(dados: Dict[str, Any]) -> Dict[str, Any]:
            """Monta payload específico para transação com cartão tokenizado"""
            # Validar campos obrigatórios
            campos_obrigatorios = [
                'cartao_id', 'valor', 'descricao_pedido',
                'ip_address_comprador', 'cpf_comprador', 'nome_comprador'
            ]

            for campo in campos_obrigatorios:
                if not dados.get(campo):
                    raise ValueError(f"Campo obrigatório '{campo}' não fornecido")

            # Obter credenciais dinâmicas
            credenciais = self._obter_credenciais_loja()

            # Determinar FormaPagamento baseado em parcelas
            qtd_parcelas = dados.get('quantidade_parcelas', 1)
            # Converter para int se vier como string
            if isinstance(qtd_parcelas, str):
                qtd_parcelas = int(qtd_parcelas)
            forma_pagamento = '1' if qtd_parcelas == 1 else '2'

            # Converter valor de reais para centavos (exemplo: 10.50 -> 1050)
            valor = dados.get('valor')
            if isinstance(valor, (Decimal, float)):
                valor = int(valor * 100)
            else:
                valor = int(valor * 100)

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "KeyLoja": credenciais['key_loja'],
                    "CartaoId": dados.get('cartao_id'),
                    "Valor": valor,
                    "FormaPagamento": forma_pagamento,
                    "QuantidadeParcelas": qtd_parcelas,
                    "DescricaoPedido": dados.get('descricao_pedido'),
                    "IpAddressComprador": dados.get('ip_address_comprador'),
                    "CpfComprador": dados.get('cpf_comprador'),
                    "NomeComprador": dados.get('nome_comprador'),
                    "TransacaoPreAutorizada": dados.get('transacao_pre_autorizada', False)
                }
            }

            # Log detalhado de tipos para debug
            registrar_log('pinbank.transacoes_pagamento', "=== DEBUG TIPOS DO PAYLOAD ===")
            for campo, valor in payload['Data'].items():
                registrar_log('pinbank.transacoes_pagamento', f"{campo}: {valor} (tipo: {type(valor).__name__})")
            registrar_log('pinbank.transacoes_pagamento', "=== FIM DEBUG TIPOS ===")

            registrar_log('pinbank.transacoes_pagamento', f"Payload transação token montado: {payload}")
            return payload

        def _processar_resposta_transacao_token(resposta: Dict[str, Any], dados_originais: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da transação com cartão tokenizado"""
            try:
                registrar_log('pinbank.transacoes_pagamento', f"Processando resposta token: {resposta}")
                registrar_log('pinbank.transacoes_pagamento', f"Dados originais token: {dados_originais}")

                # Verificar se a resposta tem NSU e Código de Autorização (transação aprovada)
                if 'NsuOperacao' in resposta and 'CodigoAutorizacao' in resposta:
                    nsu_operacao = resposta.get('NsuOperacao', '')
                    codigo_autorizacao = resposta.get('CodigoAutorizacao', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação com token APROVADA - NSU: {nsu_operacao}, Autorização: {codigo_autorizacao}")

                    return {
                        'sucesso': True,
                        'mensagem': 'Transação com cartão tokenizado aprovada com sucesso',
                        'dados': {
                            'nsu': nsu_operacao,
                            'codigo_autorizacao': codigo_autorizacao,
                            'result_code': 0,
                            'cartao_id': dados_originais.get('cartao_id', ''),
                            'valor': dados_originais.get('valor', 0),
                            'forma_pagamento': dados_originais.get('forma_pagamento', ''),
                            'cpf_comprador': dados_originais.get('cpf_comprador', ''),
                            'nome_comprador': dados_originais.get('nome_comprador', '')
                        }
                    }

                # Fallback para formato com ResultCode
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    codigo_autorizacao = data.get('CodigoAutorizacao', '')
                    nsu_operacao = data.get('NsuOperacao', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação com token APROVADA - NSU: {nsu_operacao}, Autorização: {codigo_autorizacao}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Transação com cartão tokenizado aprovada com sucesso',
                        'dados': {
                            'nsu': nsu_operacao,
                            'codigo_autorizacao': codigo_autorizacao,
                            'result_code': result_code,
                            'cartao_id': dados_originais.get('cartao_id', ''),
                            'valor': dados_originais.get('valor', 0),
                            'forma_pagamento': dados_originais.get('forma_pagamento', ''),
                            'cpf_comprador': dados_originais.get('cpf_comprador', ''),
                            'nome_comprador': dados_originais.get('nome_comprador', '')
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    validation_result_code = validation_data.get('ResultCode', result_code)
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Transação com cartão tokenizado não autorizada'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação com token NEGADA - ResultCode: {result_code}, ValidationCode: {validation_result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'validation_result_code': validation_result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da transação com token: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da transação'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando efetuar_transacao_cartao_tokenizado - CartaoId: {dados_transacao.get('cartao_id')}")

            # 1. Montar payload da transação com token
            payload_transacao = _montar_payload_transacao_token(dados_transacao)

            registrar_log('pinbank.transacoes_pagamento',
                         f"Payload montado - CartaoId: {payload_transacao['Data']['CartaoId']}, "
                         f"Valor: {payload_transacao['Data']['Valor']}, Forma: {payload_transacao['Data']['FormaPagamento']}")

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/EfetuarTransacaoCartaoIdEncrypted",
                payload_transacao
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da transação
            resposta_descriptografada = resultado['dados']

            registrar_log('pinbank.transacoes_pagamento',
                         f"Transação com token processada - Sucesso: {resposta_descriptografada.get('sucesso', False)}")

            return _processar_resposta_transacao_token(resposta_descriptografada, dados_transacao)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao efetuar transação com cartão tokenizado: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar transação'
            }

    def capturar_transacao(self, nsu_operacao: str, valor: Decimal) -> Dict[str, Any]:
        """
        Captura uma transação pré-autorizada via API Pinbank usando endpoint /Transacoes/CapturarTransacaoEncrypted

        Fluxo:
        1. EfetuarTransacao(TransacaoPreAutorizada=true) → Reserva valor (pré-autorização)
        2. CapturarTransacao(NSU) → Efetiva a cobrança
        3. CancelarTransacao(NSU) → Cancela pré-autorização ou estorna

        Args:
            nsu_operacao: NSU da operação pré-autorizada
            valor: Valor da transação em reais

        Returns:
            Dict com resultado da captura
        """

        def _montar_payload_captura(nsu: str, valor_reais: Decimal) -> Dict[str, Any]:
            """Monta payload específico para captura de transação"""
            credenciais = self._obter_credenciais_loja()

            # Garantir que valor seja Decimal e converter para centavos
            if not isinstance(valor_reais, Decimal):
                valor_reais = Decimal(str(valor_reais))

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "KeyLoja": credenciais['key_loja'],
                    "Valor": int(valor_reais * 100),  # Converter para centavos
                    "NsuOperacao": nsu
                }
            }
            return payload

        def _processar_resposta_captura(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da captura"""
            try:
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    codigo_autorizacao_captura = data.get('CodigoAutorizacaoCaptura', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação CAPTURADA com sucesso - Código: {codigo_autorizacao_captura}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Transação capturada com sucesso',
                        'dados': {
                            'codigo_autorizacao_captura': codigo_autorizacao_captura,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao capturar transação'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao capturar transação - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da captura: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da captura'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando captura - NSU: {nsu_operacao}, Valor: R$ {valor:.2f}")

            # 1. Montar payload da captura
            payload_captura = _montar_payload_captura(nsu_operacao, valor)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/CapturarTransacaoEncrypted",
                payload_captura
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da captura
            resposta_descriptografada = resultado['dados']
            resposta_completa = resultado.get('resposta_completa', {})
            
            # Adicionar ResultCode e Message da resposta original aos dados descriptografados
            resposta_para_processar = {
                'ResultCode': resposta_completa.get('ResultCode', 0),
                'Message': resposta_completa.get('Message', ''),
                'Data': resposta_descriptografada,
                'ValidationData': resposta_completa.get('ValidationData')
            }

            return _processar_resposta_captura(resposta_para_processar)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao capturar transação: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar captura'
            }

    def cancelar_transacao(self, nsu_operacao: str, valor: Decimal) -> Dict[str, Any]:
        """
        Cancela uma transação via API Pinbank usando endpoint /Transacoes/CancelarTransacaoEncrypted

        Cancela pré-autorização (antes da captura) ou estorna transação (depois da captura)

        Args:
            nsu_operacao: NSU da operação a cancelar
            valor: Valor da transação em reais

        Returns:
            Dict com resultado do cancelamento
        """

        def _montar_payload_cancelamento(nsu: str, valor_reais: Decimal) -> Dict[str, Any]:
            """Monta payload específico para cancelamento de transação"""
            credenciais = self._obter_credenciais_loja()

            # Garantir que valor seja Decimal e converter para centavos
            if not isinstance(valor_reais, Decimal):
                valor_reais = Decimal(str(valor_reais))

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "KeyLoja": credenciais['key_loja'],
                    "Valor": int(valor_reais * 100),  # Converter para centavos
                    "NsuOperacao": nsu
                }
            }
            return payload

        def _processar_resposta_cancelamento(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica do cancelamento"""
            try:
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    codigo_autorizacao_cancelamento = data.get('CodigoAutorizacaoCancelamento', '')

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Transação CANCELADA com sucesso - Código: {codigo_autorizacao_cancelamento}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Transação cancelada com sucesso',
                        'dados': {
                            'codigo_autorizacao_cancelamento': codigo_autorizacao_cancelamento,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao cancelar transação'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao cancelar transação - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta do cancelamento: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado do cancelamento'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando cancelamento - NSU: {nsu_operacao}, Valor: R$ {valor:.2f}")

            # 1. Montar payload do cancelamento
            payload_cancelamento = _montar_payload_cancelamento(nsu_operacao, valor)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/CancelarTransacaoEncrypted",
                payload_cancelamento
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica do cancelamento
            resposta_descriptografada = resultado['dados']
            resposta_completa = resultado.get('resposta_completa', {})
            
            # Adicionar ResultCode e Message da resposta original aos dados descriptografados
            resposta_para_processar = {
                'ResultCode': resposta_completa.get('ResultCode', 0),
                'Message': resposta_completa.get('Message', ''),
                'Data': resposta_descriptografada,
                'ValidationData': resposta_completa.get('ValidationData')
            }

            return _processar_resposta_cancelamento(resposta_para_processar)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao cancelar transação: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar cancelamento'
            }

    def ativar_cartao_tokenizado(self, cartao_id: str, protocolo_ativacao: int) -> Dict[str, Any]:
        """
        Ativa um cartão tokenizado via API Pinbank usando endpoint /Transacoes/AtivarCartaoEncrypted

        Args:
            cartao_id: ID do cartão a ativar
            protocolo_ativacao: Protocolo de ativação (código numérico)

        Returns:
            Dict com resultado da ativação
        """

        def _montar_payload_ativacao(cartao_id: str, protocolo: int) -> Dict[str, Any]:
            """Monta payload específico para ativação de cartão"""
            credenciais = self._obter_credenciais_loja()

            payload = {
                "Data": {
                    "CodigoCanal": credenciais['codigo_canal'],
                    "CodigoCliente": credenciais['codigo_cliente'],
                    "CartaoId": cartao_id,
                    "ProtocoloAtivacao": protocolo
                }
            }
            return payload

        def _processar_resposta_ativacao(resposta: Dict[str, Any]) -> Dict[str, Any]:
            """Processa resposta específica da ativação"""
            try:
                result_code = resposta.get('ResultCode', -1)
                message = resposta.get('Message', '')
                data = resposta.get('Data', {})
                validation_data = resposta.get('ValidationData', {})

                if result_code == 0:
                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Cartão ATIVADO com sucesso - CartaoId: {cartao_id}")

                    return {
                        'sucesso': True,
                        'mensagem': message or 'Cartão ativado com sucesso',
                        'dados': {
                            'cartao_id': cartao_id,
                            'result_code': result_code
                        }
                    }
                else:
                    validation_message = validation_data.get('Message', '')
                    errors = validation_data.get('Errors', [])

                    mensagem_erro = message or validation_message or 'Erro ao ativar cartão'
                    if errors:
                        detalhes_erro = ', '.join([error.get('ErrorMessage', '') for error in errors if error.get('ErrorMessage')])
                        if detalhes_erro:
                            mensagem_erro += f" - {detalhes_erro}"

                    registrar_log('pinbank.transacoes_pagamento',
                                 f"Erro ao ativar cartão - ResultCode: {result_code}, Mensagem: {mensagem_erro}")

                    return {
                        'sucesso': False,
                        'mensagem': mensagem_erro,
                        'result_code': result_code,
                        'errors': errors
                    }

            except Exception as e:
                registrar_log('pinbank.transacoes_pagamento', f"Erro ao processar resposta da ativação: {str(e)}", nivel='ERROR')
                return {
                    'sucesso': False,
                    'mensagem': 'Erro ao processar resultado da ativação'
                }

        try:
            from wallclub_core.utilitarios.log_control import registrar_log

            registrar_log('pinbank.transacoes_pagamento',
                         f"Iniciando ativação - CartaoId: {cartao_id}, Protocolo: {protocolo_ativacao}")

            # 1. Montar payload da ativação
            payload_ativacao = _montar_payload_ativacao(cartao_id, protocolo_ativacao)

            # 2. Fazer requisição criptografada genérica
            resultado = self._fazer_requisicao_criptografada(
                "Transacoes/AtivarCartaoEncrypted",
                payload_ativacao
            )

            if not resultado['sucesso']:
                return resultado

            # 3. Processar resposta específica da ativação
            resposta_descriptografada = resultado['dados']

            return _processar_resposta_ativacao(resposta_descriptografada)

        except Exception as e:
            registrar_log('pinbank.transacoes_pagamento', f"Erro ao ativar cartão: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro interno ao processar ativação'
            }
