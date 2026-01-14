"""
Serviço para cadastro de estabelecimentos na Own Financial
Endpoint: POST /parceiro/v2/cadastrarConveniada
"""

import base64
from typing import Dict, Any, List, Optional
from datetime import datetime
from adquirente_own.services import OwnService
from adquirente_own.models_cadastro import LojaOwn, LojaOwnTarifacao, LojaDocumentos
from wallclub_core.utilitarios.log_control import registrar_log


class CadastroOwnService:
    """Serviço para cadastro de estabelecimentos na Own Financial"""

    def __init__(self, environment: str = 'LIVE'):
        """
        Inicializa serviço de cadastro

        Args:
            environment: 'LIVE' ou 'TEST'
        """
        self.own_service = OwnService(environment=environment)
        self.environment = environment

    def preparar_payload_cadastro(self, loja_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepara payload completo para cadastro na Own

        Args:
            loja_data: Dados da loja (dict com todos os campos necessários)

        Returns:
            Payload formatado para API Own
        """
        payload = {
            # Dados do estabelecimento
            "cnpj": loja_data['cnpj'],
            "cnpjCanalWL": loja_data.get('cnpj_canal_wl', ''),
            "cnpjOrigem": loja_data.get('cnpj_origem', ''),
            "identificadorCliente": loja_data.get('identificador_cliente', loja_data['cnpj']),
            "urlCallback": loja_data.get('url_callback', 'https://wcapi.wallclub.com.br/webhook/own/credenciamento/'),

            # Razão social e nome fantasia
            "razaoSocial": loja_data['razao_social'],
            "nomeFantasia": loja_data['nome_fantasia'],

            # Atividade econômica
            "cnae": loja_data['cnae'],
            "ramoAtividade": loja_data['ramo_atividade'],
            "mcc": loja_data['mcc'],

            # Dados financeiros
            "faturamentoPrevisto": float(loja_data['faturamento_previsto']),
            "faturamentoContratado": float(loja_data['faturamento_contratado']),

            # Contato
            "email": loja_data['email'],
            "dddComercial": loja_data['ddd_telefone_comercial'],
            "telefoneComercial": loja_data['telefone_comercial'],
            "dddCel": loja_data['ddd_celular'],
            "telefoneCelular": loja_data['celular'],

            # Endereço
            "cep": loja_data['cep'],
            "logradouro": loja_data['logradouro'],
            "numeroEndereco": int(loja_data['numero_endereco']),
            "complemento": loja_data.get('complemento', ''),
            "bairro": loja_data['bairro'],
            "municipio": loja_data['municipio'],
            "uf": loja_data['uf'],

            # Responsável
            "responsavelAssinatura": loja_data['responsavel_assinatura'],

            # Configurações de pagamento
            "quantidadePos": int(loja_data.get('quantidade_pos', 1)),
            "antecipacaoAutomatica": loja_data.get('antecipacao_automatica', 'N'),
            "taxaAntecipacao": float(loja_data.get('taxa_antecipacao', 0)),
            "tipoAntecipacao": loja_data.get('tipo_antecipacao', 'ROTATIVO'),

            # Dados bancários
            "codBanco": loja_data['codigo_banco'],
            "agencia": loja_data['agencia'],
            "digAgencia": loja_data.get('digito_agencia', ''),
            "numConta": loja_data['numero_conta'],
            "digConta": loja_data['digito_conta'],

            # Configurações Own
            "tipoContrato": "W",  # White Label
            "codConfiguracao": "",
            "cnpjParceiro": "54430621000134",  # CNPJ WallClub
            "idCesta": int(loja_data['id_cesta']),
            "tarifacao": loja_data['tarifacao'],  # Lista de tarifas

            # Protocolo e hash
            "protocoloCore": "",
            "hashAceite": "",

            # Terminais
            "terminais": loja_data.get('terminais', []),

            # Documentos
            "documentosSocios": loja_data.get('documentos_socios', []),
            "anexos": loja_data.get('anexos', []),

            # Outros meios de captura
            "outrosMeiosCaptura": loja_data.get('outros_meios_captura', [])
        }

        return payload

    def converter_arquivo_base64(self, caminho_arquivo: str) -> Optional[str]:
        """
        Converte arquivo para base64

        Args:
            caminho_arquivo: Caminho do arquivo (S3 ou local)

        Returns:
            String base64 ou None
        """
        try:
            # TODO: Implementar leitura do S3 se necessário
            # Por enquanto, assumindo arquivo local
            with open(caminho_arquivo, 'rb') as f:
                conteudo = f.read()
                return base64.b64encode(conteudo).decode('utf-8')
        except Exception as e:
            registrar_log('own.cadastro', f'❌ Erro ao converter arquivo para base64: {str(e)}', nivel='ERROR')
            return None

    def preparar_documentos_socios(self, loja_id: int) -> List[Dict[str, Any]]:
        """
        Prepara documentos dos sócios para envio

        Args:
            loja_id: ID da loja

        Returns:
            Lista de documentos formatados
        """
        try:
            # Buscar documentos de sócios
            docs_socios = LojaDocumentos.objects.filter(
                loja_id=loja_id,
                cpf_socio__isnull=False,
                ativo=True
            ).order_by('cpf_socio')

            # Agrupar por CPF do sócio
            socios_dict = {}
            for doc in docs_socios:
                cpf = doc.cpf_socio
                if cpf not in socios_dict:
                    socios_dict[cpf] = {
                        'identificacao': cpf,
                        'anexos': []
                    }

                # Converter arquivo para base64
                conteudo_base64 = self.converter_arquivo_base64(doc.caminho_arquivo)
                if conteudo_base64:
                    socios_dict[cpf]['anexos'].append({
                        'nomeArquivo': doc.nome_arquivo,
                        'conteudo': conteudo_base64,
                        'tipo': doc.tipo_documento
                    })

            return list(socios_dict.values())

        except Exception as e:
            registrar_log('own.cadastro', f'❌ Erro ao preparar documentos de sócios: {str(e)}', nivel='ERROR')
            return []

    def preparar_anexos_empresa(self, loja_id: int) -> List[Dict[str, Any]]:
        """
        Prepara anexos da empresa para envio

        Args:
            loja_id: ID da loja

        Returns:
            Lista de anexos formatados
        """
        try:
            # Buscar documentos da empresa (sem CPF de sócio)
            docs_empresa = LojaDocumentos.objects.filter(
                loja_id=loja_id,
                cpf_socio__isnull=True,
                ativo=True
            )

            anexos = []
            for doc in docs_empresa:
                # Converter arquivo para base64
                conteudo_base64 = self.converter_arquivo_base64(doc.caminho_arquivo)
                if conteudo_base64:
                    anexos.append({
                        'nomeArquivo': doc.nome_arquivo,
                        'conteudo': conteudo_base64,
                        'tipo': doc.tipo_documento
                    })

            return anexos

        except Exception as e:
            registrar_log('own.cadastro', f'❌ Erro ao preparar anexos da empresa: {str(e)}', nivel='ERROR')
            return []

    def cadastrar_estabelecimento(self, loja_id: int, loja_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Cadastra estabelecimento na Own Financial

        Args:
            loja_id: ID da loja
            loja_data: Dados da loja

        Returns:
            {
                'sucesso': bool,
                'protocolo': str,
                'mensagem': str
            }
        """
        try:
            registrar_log('own.cadastro', f'🏪 Iniciando cadastro da loja {loja_id} na Own')

            # Obter credenciais
            credenciais = self.own_service.obter_credenciais_white_label(self.environment)
            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais não encontradas'
                }

            # Preparar documentos
            loja_data['documentos_socios'] = self.preparar_documentos_socios(loja_id)
            loja_data['anexos'] = self.preparar_anexos_empresa(loja_id)

            # Preparar payload
            payload = self.preparar_payload_cadastro(loja_data)

            registrar_log('own.cadastro', f'📦 Payload preparado: CNPJ={payload["cnpj"]}, Cesta={payload["idCesta"]}')

            # Fazer requisição
            resultado = self.own_service.fazer_requisicao_autenticada(
                method='POST',
                endpoint='/parceiro/v2/cadastrarConveniada',
                client_id=credenciais['client_id'],
                client_secret=credenciais['client_secret'],
                scope=credenciais['scope'],
                data=payload
            )

            if not resultado.get('sucesso'):
                registrar_log('own.cadastro', f'❌ Falha no cadastro: {resultado.get("mensagem")}', nivel='ERROR')
                return resultado

            # Processar resposta
            dados_resposta = resultado.get('dados', {})
            protocolo = dados_resposta.get('protocolo', '')
            conveniada_id = dados_resposta.get('conveniadaId', '')

            # Atualizar ou criar registro LojaOwn
            loja_own, created = LojaOwn.objects.update_or_create(
                loja_id=loja_id,
                defaults={
                    'cadastrar': True,
                    'protocolo': protocolo,
                    'conveniada_id': conveniada_id,
                    'status_credenciamento': 'PENDENTE',
                    'data_credenciamento': datetime.now(),
                    'mensagem_status': 'Cadastro enviado com sucesso'
                }
            )

            registrar_log('own.cadastro', f'✅ Cadastro enviado: protocolo={protocolo}, conveniada_id={conveniada_id}')

            return {
                'sucesso': True,
                'protocolo': protocolo,
                'conveniada_id': conveniada_id,
                'mensagem': 'Cadastro enviado com sucesso. Aguardando processamento da Own.'
            }

        except Exception as e:
            registrar_log('own.cadastro', f'❌ Erro ao cadastrar estabelecimento: {str(e)}', nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': f'Erro ao cadastrar: {str(e)}'
            }

    def validar_dados_cadastro(self, loja_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Valida dados obrigatórios para cadastro

        Args:
            loja_data: Dados da loja

        Returns:
            {
                'valido': bool,
                'erros': List[str]
            }
        """
        erros = []

        # Campos obrigatórios
        campos_obrigatorios = [
            'cnpj', 'razao_social', 'nome_fantasia', 'email',
            'cnae', 'ramo_atividade', 'mcc',
            'faturamento_previsto', 'faturamento_contratado',
            'ddd_telefone_comercial', 'telefone_comercial',
            'ddd_celular', 'celular',
            'cep', 'logradouro', 'numero_endereco', 'bairro', 'municipio', 'uf',
            'responsavel_assinatura',
            'codigo_banco', 'agencia', 'numero_conta', 'digito_conta',
            'id_cesta', 'tarifacao'
        ]

        for campo in campos_obrigatorios:
            if not loja_data.get(campo):
                erros.append(f'Campo obrigatório ausente: {campo}')

        # Validar tarifação
        if loja_data.get('tarifacao') and not isinstance(loja_data['tarifacao'], list):
            erros.append('Tarifação deve ser uma lista')

        if loja_data.get('tarifacao') and len(loja_data['tarifacao']) == 0:
            erros.append('Tarifação não pode estar vazia')

        return {
            'valido': len(erros) == 0,
            'erros': erros
        }
