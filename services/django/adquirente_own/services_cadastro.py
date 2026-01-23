"""
Serviço para cadastro de estabelecimentos na Own Financial
Endpoint: POST /parceiro/v2/cadastrarConveniada
"""

import base64
import json
import hashlib
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
            "identificadorCliente": self._formatar_identificador_cliente(loja_data),
            "urlCallback": loja_data.get('url_callback', 'https://wcapi.wallclub.com.br/webhook/own/credenciamento/'),

            # Razão social e nome fantasia
            "razaoSocial": loja_data['razao_social'],
            "nomeFantasia": loja_data['nome_fantasia'],

            # Atividade econômica
            "cnae": loja_data['cnae'],
            "ramoAtividade": loja_data['ramo_atividade'],
            "mcc": loja_data['mcc'],

            # Dados financeiros (converter formato brasileiro para float)
            "faturamentoPrevisto": self._converter_valor_br(loja_data['faturamento_previsto']),
            "faturamentoContratado": self._converter_valor_br(loja_data['faturamento_contratado']),

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

            # Protocolo, contrato e hash
            "protocoloCore": loja_data.get('protocolo', ''),  # Protocolo - apenas para reenvio após recusa
            "numeroContrato": loja_data.get('contrato', ''),  # Número do contrato - para aditivos (alterações)
            "hashAceite": self._gerar_hash_aceite(loja_data),

            # Terminais - sempre vazio
            "terminais": [],

            # Documentos
            "documentosSocios": loja_data.get('documentos_socios', []),
            "anexos": loja_data.get('anexos', []),

            # Outros meios de captura
            "outrosMeiosCaptura": [{"meioCaptura": "ECOMMERCE"}] if loja_data.get('aceita_ecommerce') else []
        }

        return payload

    def _converter_valor_br(self, valor_str: str) -> float:
        """
        Converte valor no formato brasileiro (ex: 40.000,00) para float.

        Args:
            valor_str: String com valor no formato brasileiro

        Returns:
            Float com o valor convertido
        """
        if not valor_str:
            return 0.0
        # Remove pontos (separador de milhar) e substitui vírgula por ponto
        return float(str(valor_str).replace('.', '').replace(',', '.'))

    def _formatar_identificador_cliente(self, loja_data: Dict[str, Any]) -> str:
        """
        Formata o identificadorCliente no padrão exigido pela Own Financial.

        Formato: CNPJ_CPF/EXTERNAL_ID/NOME_OPERACAO/EMAIL/CPF/NOME_PESSOA

        Exemplo: 00000000000/123/99999999999999/emailresponsavel@teste.com.br/11111111111/NOME_PESSOA

        Componentes:
        - CNPJ_CPF: CNPJ ou CPF do estabelecimento (apenas números)
        - EXTERNAL_ID: ID do estabelecimento no sistema (loja.id)
        - NOME_OPERACAO: CNPJ do Parceiro WL (WallClub) se não houver separação por operação
        - EMAIL: Email da pessoa responsável pelo contrato
        - CPF: CPF da pessoa responsável pelo contrato (apenas números)
        - NOME_PESSOA: Nome da pessoa responsável pelo contrato

        Args:
            loja_data: Dados da loja contendo CNPJ, ID, responsável, etc.

        Returns:
            String formatada no padrão Own Financial
        """
        # CNPJ_CPF: CNPJ do estabelecimento (apenas números)
        cnpj_cpf = ''.join(filter(str.isdigit, loja_data.get('cnpj', '')))

        # EXTERNAL_ID: ID da loja no sistema WallClub
        external_id = str(loja_data.get('loja_id', ''))

        # NOME_OPERACAO: CNPJ do Parceiro WL (WallClub)
        nome_operacao = '54430621000134'  # CNPJ WallClub

        # EMAIL: Email do responsável pelo contrato
        email = loja_data.get('responsavel_assinatura_email', '')

        # CPF: CPF do responsável (apenas números)
        cpf = ''.join(filter(str.isdigit, loja_data.get('responsavel_assinatura_cpf', '')))

        # NOME_PESSOA: Nome do responsável
        nome_pessoa = loja_data.get('responsavel_assinatura', '')

        # Montar identificador no formato: CNPJ_CPF/EXTERNAL_ID/NOME_OPERACAO/EMAIL/CPF/NOME_PESSOA
        identificador = f"{cnpj_cpf}/{external_id}/{nome_operacao}/{email}/{cpf}/{nome_pessoa}"

        return identificador

    def _formatar_cpf(self, cpf: str) -> str:
        """
        Formata CPF com pontos e traço (XXX.XXX.XXX-XX)

        Args:
            cpf: CPF apenas com números

        Returns:
            CPF formatado
        """
        if not cpf:
            return ''

        # Remove qualquer formatação existente
        cpf_numeros = ''.join(filter(str.isdigit, cpf))

        # Formata: XXX.XXX.XXX-XX
        if len(cpf_numeros) == 11:
            return f'{cpf_numeros[:3]}.{cpf_numeros[3:6]}.{cpf_numeros[6:9]}-{cpf_numeros[9:]}'

        return cpf_numeros

    def _gerar_hash_aceite(self, loja_data: Dict[str, Any]) -> str:
        """
        Gera hash SHA256 do termo de aceite

        Args:
            loja_data: Dados da loja

        Returns:
            Hash SHA256 em hexadecimal
        """
        # Termo de aceite padrão WallClub para Own Financial
        termo_aceite = f"""
        TERMO DE ACEITE - CREDENCIAMENTO OWN FINANCIAL

        Eu, {loja_data.get('responsavel_assinatura', '')}, na qualidade de representante legal da empresa
        {loja_data.get('razao_social', '')}, inscrita no CNPJ {loja_data.get('cnpj', '')},
        declaro estar ciente e de acordo com os termos e condições do credenciamento junto à Own Financial
        para utilização dos serviços de adquirência e meios de pagamento.

        Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
        """

        # Gerar hash SHA256
        hash_obj = hashlib.sha256(termo_aceite.encode('utf-8'))
        return hash_obj.hexdigest()

    def converter_arquivo_base64(self, caminho_arquivo: str) -> Optional[str]:
        """
        Converte arquivo para base64

        Args:
            caminho_arquivo: Caminho do arquivo no storage

        Returns:
            String base64 ou None
        """
        try:
            from django.core.files.storage import default_storage

            # Ler arquivo do storage (funciona com S3 ou filesystem)
            if default_storage.exists(caminho_arquivo):
                with default_storage.open(caminho_arquivo, 'rb') as f:
                    conteudo = f.read()
                    return base64.b64encode(conteudo).decode('utf-8')
            else:
                registrar_log('adquirente_own', f'⚠️ Arquivo não encontrado: {caminho_arquivo}', nivel='WARNING')
                return None
        except Exception as e:
            registrar_log('adquirente_own', f'❌ Erro ao converter arquivo para base64: {str(e)}', nivel='ERROR')
            return None

    def preparar_documentos_socios(self, loja_id: int, cpf_responsavel: str = None) -> List[Dict[str, Any]]:
        """
        Prepara documentos dos sócios para envio

        Args:
            loja_id: ID da loja
            cpf_responsavel: CPF do responsável pela assinatura (obrigatório para API Own)

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
                        'identificacao': self._formatar_cpf(cpf),
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

            # Retornar lista vazia se não houver documentos reais
            # API Own em produção não aceita anexos em branco
            return list(socios_dict.values())

        except Exception as e:
            registrar_log('adquirente_own', f'❌ Erro ao preparar documentos de sócios: {str(e)}', nivel='ERROR')
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
            registrar_log('adquirente_own', f'❌ Erro ao preparar anexos da empresa: {str(e)}', nivel='ERROR')
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
            registrar_log('adquirente_own', f'🏪 Iniciando cadastro da loja {loja_id} na Own')

            # Obter credenciais
            credenciais = self.own_service.obter_credenciais_white_label(self.environment)
            if not credenciais:
                return {
                    'sucesso': False,
                    'mensagem': 'Credenciais não encontradas'
                }

            # Preparar documentos
            loja_data['documentos_socios'] = self.preparar_documentos_socios(loja_id, loja_data.get('responsavel_assinatura_cpf'))
            loja_data['anexos'] = self.preparar_anexos_empresa(loja_id)

            # Preparar payload
            payload = self.preparar_payload_cadastro(loja_data)

            registrar_log('adquirente_own', f'📦 Payload preparado: CNPJ={payload["cnpj"]}, Cesta={payload["idCesta"]}')
            registrar_log('adquirente_own', f'📋 Payload completo: {json.dumps(payload, indent=2, ensure_ascii=False)}', nivel='DEBUG')

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
                registrar_log('adquirente_own', f'❌ Falha no cadastro: {resultado.get("mensagem")}', nivel='ERROR')
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

            registrar_log('adquirente_own', f'✅ Cadastro enviado: protocolo={protocolo}, conveniada_id={conveniada_id}')

            return {
                'sucesso': True,
                'protocolo': protocolo,
                'conveniada_id': conveniada_id,
                'mensagem': 'Cadastro enviado com sucesso. Aguardando processamento da Own.'
            }

        except Exception as e:
            registrar_log('adquirente_own', f'❌ Erro ao cadastrar estabelecimento: {str(e)}', nivel='ERROR')
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
