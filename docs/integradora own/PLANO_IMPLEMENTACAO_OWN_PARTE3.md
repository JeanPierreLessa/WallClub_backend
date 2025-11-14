# PLANO DE IMPLEMENTAÇÃO - PARTE 3

## 🔧 ESPECIFICAÇÃO TÉCNICA (Continuação)

### Services - Tokenização e Recorrência

```python
# own/services_tokenizacao.py

from .services_transacoes import OwnTransacaoService
from .models import OwnRegistration
from wallclub_core.utilitarios.log_control import registrar_log

class OwnTokenizacaoService:
    """Service de tokenização e pagamentos recorrentes"""
    
    def __init__(self, loja):
        self.loja = loja
        self.transacao_service = OwnTransacaoService(loja)
    
    def create_registration_standalone(self, card_data):
        """
        Cria registration sem pagamento
        Endpoint: POST /v1/registrations
        """
        data = {
            'entityId': self.transacao_service.entity_id,
            'paymentBrand': card_data['brand'].upper(),
            'card.number': card_data['number'],
            'card.holder': card_data['holder'],
            'card.expiryMonth': card_data['expiry_month'],
            'card.expiryYear': card_data['expiry_year'],
            'card.cvv': card_data['cvv'],
        }
        
        registrar_log('own.tokenizacao', '🔐 Criando registration standalone')
        
        response = self.transacao_service._make_request('POST', '/v1/registrations', data)
        
        if response['result']['code'] in self.transacao_service.SUCCESS_CODES:
            # Salvar registration
            registration = OwnRegistration.objects.create(
                loja=self.loja,
                registration_id=response['id'],
                initial_transaction_id='',  # Não há transação inicial
                card_bin=response.get('card', {}).get('bin', ''),
                card_last4=response.get('card', {}).get('last4Digits', ''),
                card_brand=response.get('paymentBrand', ''),
                card_holder=response.get('card', {}).get('holder', ''),
                ativo=True
            )
            
            registrar_log('own.tokenizacao', f'✅ Registration criado: {response["id"]}')
            
            return {
                'sucesso': True,
                'registration_id': response['id'],
                'card_last4': response.get('card', {}).get('last4Digits')
            }
        else:
            return {
                'sucesso': False,
                'mensagem': response['result']['description']
            }
    
    def payment_with_registration(self, registration_id, amount, initial_transaction_id=None):
        """
        Pagamento usando registration (recorrência)
        Endpoint: POST /v1/registrations/{registrationId}/payments
        """
        data = {
            'entityId': self.transacao_service.entity_id,
            'amount': f'{amount:.2f}',
            'currency': 'BRL',
            'paymentType': 'DB',
            'standingInstruction.mode': 'REPEATED',
            'standingInstruction.type': 'UNSCHEDULED',
            'standingInstruction.source': 'MIT'
        }
        
        if initial_transaction_id:
            data['standingInstruction.initialTransactionId'] = initial_transaction_id
        
        registrar_log('own.tokenizacao', f'💳 Cobrança recorrente: {registration_id} - R$ {amount:.2f}')
        
        response = self.transacao_service._make_request(
            'POST',
            f'/v1/registrations/{registration_id}/payments',
            data
        )
        
        if response['result']['code'] in self.transacao_service.SUCCESS_CODES:
            registrar_log('own.tokenizacao', f'✅ Cobrança aprovada: {response["id"]}')
            return {
                'sucesso': True,
                'own_payment_id': response['id'],
                'nsu': response['id']
            }
        else:
            registrar_log('own.tokenizacao', f'❌ Cobrança reprovada: {response["result"]["code"]}')
            return {
                'sucesso': False,
                'mensagem': response['result']['description']
            }
    
    def delete_registration(self, registration_id):
        """
        Deleta registration (desativa token)
        Endpoint: DELETE /v1/registrations/{registrationId}
        """
        registrar_log('own.tokenizacao', f'🗑️ Deletando registration: {registration_id}')
        
        try:
            url = f'{self.transacao_service.base_url}/v1/registrations/{registration_id}'
            headers = {
                'Authorization': f'Bearer {self.transacao_service.access_token}'
            }
            
            response = requests.delete(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Marcar como inativo no banco
            registration = OwnRegistration.objects.get(registration_id=registration_id)
            registration.ativo = False
            registration.deleted_at = datetime.now()
            registration.save()
            
            registrar_log('own.tokenizacao', f'✅ Registration deletado: {registration_id}')
            return {'sucesso': True}
            
        except Exception as e:
            registrar_log('own.tokenizacao', f'❌ Erro ao deletar: {str(e)}', level='ERROR')
            return {'sucesso': False, 'mensagem': str(e)}
```

---

### Services - Consultas (APIs Own Adquirência)

```python
# own/services_consultas.py

import requests
from datetime import datetime
from .services_autenticacao import OwnAuthService
from wallclub_core.utilitarios.log_control import registrar_log

class OwnConsultaService:
    """Service de consultas via APIs Own Adquirência"""
    
    BASE_URL_TEST = 'https://acquirer-qa.own.financial/agilli'
    BASE_URL_LIVE = 'https://acquirer.own.financial/agilli'
    
    def __init__(self, environment='LIVE'):
        self.environment = environment
        self.base_url = self.BASE_URL_LIVE if environment == 'LIVE' else self.BASE_URL_TEST
        self.auth_service = OwnAuthService(environment)
    
    def _get_headers(self, client_id, client_secret, scope):
        """Headers com autenticação OAuth"""
        token = self.auth_service.get_access_token(client_id, client_secret, scope)
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def buscar_transacoes_gerais(self, cnpj_cliente, data_inicial, data_final, 
                                  doc_parceiro=None, identificador_transacao=None):
        """
        Consulta transações gerais
        Endpoint: POST /transacoes/v2/buscaTransacoesGerais
        """
        url = f'{self.base_url}/transacoes/v2/buscaTransacoesGerais'
        
        payload = {
            'cnpjCliente': cnpj_cliente,
            'dataInicial': data_inicial.strftime('%Y-%m-%d %H:%M'),
            'dataFinal': data_final.strftime('%Y-%m-%d %H:%M')
        }
        
        if doc_parceiro:
            payload['docParceiro'] = doc_parceiro
        if identificador_transacao:
            payload['identificadorTransacao'] = identificador_transacao
        
        registrar_log('own.consulta', f'🔍 Buscando transações: {data_inicial} a {data_final}')
        
        try:
            # Obter credenciais (do AWS Secrets ou config)
            client_id = 'SEU_CLIENT_ID'
            client_secret = 'SEU_CLIENT_SECRET'
            scope = 'SEU_SCOPE'
            
            headers = self._get_headers(client_id, client_secret, scope)
            
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            response.raise_for_status()
            
            transacoes = response.json()
            registrar_log('own.consulta', f'✅ {len(transacoes)} transações encontradas')
            
            return transacoes
            
        except requests.exceptions.RequestException as e:
            registrar_log('own.consulta', f'❌ Erro na consulta: {str(e)}', level='ERROR')
            return []
    
    def consultar_liquidacoes(self, cnpj_cliente, data_pagamento_real):
        """
        Consulta liquidações
        Endpoint: GET /parceiro/v2/consultaLiquidacoes
        """
        url = f'{self.base_url}/parceiro/v2/consultaLiquidacoes'
        
        params = {
            'dataPagamentoReal': data_pagamento_real.strftime('%Y-%m-%d'),
            'cnpjCliente': cnpj_cliente
        }
        
        registrar_log('own.consulta', f'💰 Consultando liquidações: {data_pagamento_real}')
        
        try:
            client_id = 'SEU_CLIENT_ID'
            client_secret = 'SEU_CLIENT_SECRET'
            scope = 'SEU_SCOPE'
            
            headers = self._get_headers(client_id, client_secret, scope)
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            liquidacoes = response.json()
            registrar_log('own.consulta', f'✅ {len(liquidacoes)} liquidações encontradas')
            
            return liquidacoes
            
        except requests.exceptions.RequestException as e:
            registrar_log('own.consulta', f'❌ Erro na consulta: {str(e)}', level='ERROR')
            return []
```

---

### Services - Credenciamento

```python
# own/services_credenciamento.py

import requests
from datetime import datetime
from .services_autenticacao import OwnAuthService
from .models import OwnCredenciamento
from wallclub_core.utilitarios.log_control import registrar_log

class OwnCredenciamentoService:
    """Service de credenciamento de estabelecimentos"""
    
    BASE_URL_TEST = 'https://acquirer-qa.own.financial/agilli'
    BASE_URL_LIVE = 'https://acquirer.own.financial/agilli'
    
    def __init__(self, environment='LIVE'):
        self.environment = environment
        self.base_url = self.BASE_URL_LIVE if environment == 'LIVE' else self.BASE_URL_TEST
        self.auth_service = OwnAuthService(environment)
    
    def cadastrar_conveniada(self, loja, dados_cadastrais, documentos, tarifacao):
        """
        Cadastra estabelecimento via API
        Endpoint: POST /parceiro/v2/cadastrarConveniada
        """
        url = f'{self.base_url}/parceiro/v2/cadastrarConveniada'
        
        payload = {
            'cnpj': dados_cadastrais['cnpj'],
            'cnpjCanalWL': dados_cadastrais.get('cnpj_canal_wl', ''),
            'cnpjOrigem': '',
            'identificadorCliente': str(loja.id),
            'urlCallback': dados_cadastrais.get('url_callback', ''),
            'razaoSocial': dados_cadastrais['razao_social'],
            'nomeFantasia': dados_cadastrais['nome_fantasia'],
            'cnae': dados_cadastrais['cnae'],
            'ramoAtividade': dados_cadastrais['ramo_atividade'],
            'faturamentoPrevisto': dados_cadastrais['faturamento_previsto'],
            'email': dados_cadastrais['email'],
            'dddComercial': dados_cadastrais['ddd_comercial'],
            'telefoneComercial': dados_cadastrais['telefone_comercial'],
            'cep': dados_cadastrais['cep'],
            'logradouro': dados_cadastrais['logradouro'],
            'numeroEndereco': dados_cadastrais['numero_endereco'],
            'complemento': dados_cadastrais.get('complemento', ''),
            'bairro': dados_cadastrais['bairro'],
            'municipio': dados_cadastrais['municipio'],
            'uf': dados_cadastrais['uf'],
            'dddCel': dados_cadastrais['ddd_celular'],
            'telefoneCelular': dados_cadastrais['telefone_celular'],
            'responsavelAssinatura': dados_cadastrais['responsavel_assinatura'],
            'quantidadePos': dados_cadastrais.get('quantidade_pos', 1),
            'faturamentoContratado': dados_cadastrais['faturamento_contratado'],
            'antecipacaoAutomatica': dados_cadastrais.get('antecipacao_automatica', 'N'),
            'taxaAntecipacao': dados_cadastrais.get('taxa_antecipacao', 0),
            'tipoAntecipacao': dados_cadastrais.get('tipo_antecipacao', 'ROTATIVO'),
            'mcc': dados_cadastrais['mcc'],
            'tipoContrato': 'W',
            'codConfiguracao': '',
            'cnpjParceiro': dados_cadastrais['cnpj_parceiro'],
            'idCesta': dados_cadastrais['id_cesta'],
            'tarifacao': tarifacao,
            'codBanco': dados_cadastrais['cod_banco'],
            'agencia': dados_cadastrais['agencia'],
            'digAgencia': dados_cadastrais.get('dig_agencia', ''),
            'numConta': dados_cadastrais['num_conta'],
            'digConta': dados_cadastrais['dig_conta'],
            'protocoloCore': dados_cadastrais.get('protocolo_core', ' '),
            'hashAceite': ' ',
            'terminais': [],
            'documentosSocios': documentos['socios'],
            'anexos': documentos['estabelecimento'],
            'outrosMeiosCaptura': dados_cadastrais.get('outros_meios_captura', [])
        }
        
        registrar_log('own.credenciamento', f'📝 Enviando credenciamento: {dados_cadastrais["cnpj"]}')
        
        try:
            client_id = 'SEU_CLIENT_ID'
            client_secret = 'SEU_CLIENT_SECRET'
            scope = 'SEU_SCOPE'
            
            token = self.auth_service.get_access_token(client_id, client_secret, scope)
            headers = {
                'Authorization': f'Bearer {token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            
            # Salvar credenciamento
            credenciamento = OwnCredenciamento.objects.create(
                loja=loja,
                protocolo_core=result['protocolo'],
                status='EM_ANALISE',
                dados_cadastrais=dados_cadastrais,
                documentos=documentos,
                enviado_em=datetime.now()
            )
            
            registrar_log('own.credenciamento', f'✅ Protocolo: {result["protocolo"]}')
            
            return {
                'sucesso': True,
                'protocolo': result['protocolo'],
                'status': result['status']
            }
            
        except requests.exceptions.RequestException as e:
            registrar_log('own.credenciamento', f'❌ Erro: {str(e)}', level='ERROR')
            return {
                'sucesso': False,
                'mensagem': str(e)
            }
    
    def consultar_protocolos(self, cnpj_estabelecimento=None, data_inicial=None, data_final=None):
        """
        Consulta status de protocolos
        Endpoint: GET /parceiro/consultarProtocolos
        """
        url = f'{self.base_url}/parceiro/consultarProtocolos'
        
        params = {}
        if cnpj_estabelecimento:
            params['cnpjEstabelecimento'] = cnpj_estabelecimento
        if data_inicial and data_final:
            params['dataInicial'] = data_inicial.strftime('%Y-%m-%d')
            params['dataFinal'] = data_final.strftime('%Y-%m-%d')
        
        registrar_log('own.credenciamento', '🔍 Consultando protocolos')
        
        try:
            client_id = 'SEU_CLIENT_ID'
            client_secret = 'SEU_CLIENT_SECRET'
            scope = 'SEU_SCOPE'
            
            token = self.auth_service.get_access_token(client_id, client_secret, scope)
            headers = {'Authorization': f'Bearer {token}'}
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            
            protocolos = response.json()
            registrar_log('own.credenciamento', f'✅ {len(protocolos)} protocolos encontrados')
            
            # Atualizar status no banco
            for protocolo in protocolos:
                try:
                    cred = OwnCredenciamento.objects.get(protocolo_core=protocolo['protocoloCore'])
                    
                    if protocolo['status'] == 'SUCESSO':
                        cred.status = 'APROVADO'
                        cred.numero_contrato = protocolo.get('contrato', '')
                    elif protocolo['status'] in ['ERRO', 'REPROVED']:
                        cred.status = 'REPROVADO'
                        cred.motivo_reprovacao = protocolo.get('motivo', '')
                    
                    cred.respondido_em = datetime.now()
                    cred.save()
                except OwnCredenciamento.DoesNotExist:
                    pass
            
            return protocolos
            
        except requests.exceptions.RequestException as e:
            registrar_log('own.credenciamento', f'❌ Erro: {str(e)}', level='ERROR')
            return []
```

---

## 📅 CRONOGRAMA DE IMPLEMENTAÇÃO

### Fase 1: Infraestrutura Base (Semana 1-2)

**Objetivos:**
- Criar módulo `own/`
- Implementar autenticação OAuth 2.0
- Configurar ambientes (test/live)

**Tarefas:**
1. ✅ Criar estrutura de diretórios
2. ✅ Implementar `OwnAuthService`
3. ✅ Criar models base
4. ✅ Configurar AWS Secrets Manager para credenciais
5. ✅ Testes de conectividade

**Entregáveis:**
- Módulo `own/` funcional
- Autenticação OAuth testada
- Documentação de configuração

---

### Fase 2: Transações e-SiTef (Semana 3-4)

**Objetivos:**
- Implementar pagamentos síncronos (DB)
- Implementar tokenização (PA + Registration)
- Integrar com checkout web

**Tarefas:**
1. ✅ Implementar `OwnTransacaoService`
2. ✅ Implementar `OwnTokenizacaoService`
3. ✅ Criar `GatewayRouter`
4. ✅ Adaptar `CheckoutService` para usar roteador
5. ✅ Testes em ambiente sandbox

**Entregáveis:**
- Pagamentos DB funcionando
- Tokenização PA funcionando
- Checkout web com Own

---

### Fase 3: Recorrências (Semana 5)

**Objetivos:**
- Implementar cobranças recorrentes
- Migrar tasks Celery

**Tarefas:**
1. ✅ Adaptar `RecorrenciaAgendada` model
2. ✅ Implementar cobrança com registration
3. ✅ Atualizar Celery tasks
4. ✅ Testes de recorrência

**Entregáveis:**
- Recorrências Own funcionando
- Tasks Celery atualizadas

---

### Fase 4: Consultas e Cargas (Semana 6)

**Objetivos:**
- Implementar consultas de transações
- Implementar consultas de liquidações
- Criar cargas automáticas

**Tarefas:**
1. ✅ Implementar `OwnConsultaService`
2. ✅ Criar `services_carga_transacoes.py`
3. ✅ Criar `services_carga_liquidacoes.py`
4. ✅ Integrar com `BaseTransacoesGestao`
5. ✅ Configurar Celery Beat

**Entregáveis:**
- Consultas funcionando
- Cargas automáticas rodando
- Dados no portal

---

### Fase 5: Credenciamento (Semana 7-8)

**Objetivos:**
- Implementar processo de credenciamento
- Criar formulários e upload de documentos
- Portal admin

**Tarefas:**
1. ✅ Implementar `OwnCredenciamentoService`
2. ✅ Criar formulário credenciamento
3. ✅ Implementar upload documentos
4. ✅ Criar views admin
5. ✅ Consulta de protocolos

**Entregáveis:**
- Credenciamento via portal
- Acompanhamento de protocolos

---

### Fase 6: Portal e UX (Semana 9)

**Objetivos:**
- Seleção de gateway no cadastro
- Dashboards comparativos
- Documentação usuário

**Tarefas:**
1. ✅ Campo `gateway_ativo` em Loja
2. ✅ Seletor de gateway no cadastro
3. ✅ Dashboard comparativo
4. ✅ Documentação para lojistas

**Entregáveis:**
- Portal completo
- Documentação

---

### Fase 7: Testes e Homologação (Semana 10-11)

**Objetivos:**
- Testes integrados
- Homologação com usuários
- Correções

**Tarefas:**
1. ✅ Testes E2E checkout
2. ✅ Testes E2E recorrência
3. ✅ Testes cargas
4. ✅ Homologação com 3 lojas piloto
5. ✅ Correções e ajustes

**Entregáveis:**
- Sistema testado
- Bugs corrigidos

---

### Fase 8: Deploy Produção (Semana 12)

**Objetivos:**
- Deploy gradual
- Monitoramento
- Suporte

**Tarefas:**
1. ✅ Deploy em produção
2. ✅ Migrar 5 lojas piloto
3. ✅ Monitoramento 24/7
4. ✅ Suporte dedicado
5. ✅ Documentação final

**Entregáveis:**
- Sistema em produção
- Lojas operando

---

Continua na PARTE 4...
