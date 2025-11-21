"""
Serviços para integração com Pinbank
Funções relacionadas a transações e dados do Pinbank
"""

from typing import Dict, Any
import requests
import json
from datetime import datetime, timedelta
from django.db import connection
from django.conf import settings
from django.core.cache import cache
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import base64
import urllib3
from wallclub_core.utilitarios.log_control import registrar_log

# Desabilitar warnings SSL para Pinbank
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class PinbankService:
    """Serviço centralizado para operações relacionadas a NSU, transactiondata e terminais"""
    
    def __init__(self):
        # Configurações da API Pinbank
        self.base_url = getattr(settings, 'PINBANK_URL', None)
        self.username = getattr(settings, 'PINBANK_WALL_USERNAME', None)
        self.password = getattr(settings, 'PINBANK_WALL_PASSWD', None)
        self.timeout = getattr(settings, 'PINBANK_TIMEOUT', 30)
        
        if not self.username or not self.password:
            registrar_log('pinbank', "Pinbank: Credenciais não configuradas", nivel='ERROR')
    
    def pega_info_loja(self, identificador, tabela: str) -> Dict[str, Any]:
        """
        Busca informações da loja baseado no identificador e tabela de origem.
        
        Args:
            identificador: NSU (int) para Pinbank OU CNPJ (str) para Own
            tabela: 'transactiondata' ou 'transactiondata_own' (OBRIGATÓRIO)
        
        Returns:
            Dict com informações da loja (id, loja_id, loja, cnpj, canal_id)
        
        Raises:
            Exception: Se loja não for encontrada
        """
        if tabela == 'transactiondata_own':
            return self._buscar_loja_por_cnpj(identificador)
        elif tabela == 'transactiondata':
            return self._buscar_loja_por_nsu(identificador)
        else:
            raise ValueError(f"Tabela inválida: {tabela}. Use 'transactiondata' ou 'transactiondata_own'")
    
    def _buscar_loja_por_nsu(self, nsu_operacao: int) -> Dict[str, Any]:
        """Busca loja pelo NSU (Pinbank) - método interno"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT  l.id, l.razao_social, l.cnpj, l.canal_id
                FROM    wallclub.loja l,
                        wallclub.terminais as t, 
                        wallclub.transactiondata as td
                WHERE   td.nsuPinbank = %s
                        AND (t.inicio <= UNIX_TIMESTAMP(CAST(td.datahora AS DATETIME(6))))
                        AND td.terminal = t.terminal 
                        AND t.loja_id = l.id
                ORDER BY t.id DESC LIMIT 1
            """, [nsu_operacao])
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0], 
                    'loja_id': row[0],
                    'loja': row[1], 
                    'cnpj': row[2],
                    'canal_id': row[3]
                }
            else:
                raise Exception(f"Loja não encontrada para NSU {nsu_operacao}")
    
    def _buscar_loja_por_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """Busca loja pelo CNPJ (Own) - método interno"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, razao_social, cnpj, canal_id
                FROM wallclub.loja
                WHERE cnpj = %s
                LIMIT 1
            """, [cnpj])
            
            row = cursor.fetchone()
            if row:
                return {
                    'id': row[0],
                    'loja_id': row[0],
                    'loja': row[1],
                    'cnpj': row[2],
                    'canal_id': row[3]
                }
            else:
                raise Exception(f"Loja não encontrada para CNPJ {cnpj}")
    
    def pega_info_canal_por_id(self, canal_id: int) -> Dict[str, Any]:
        """Busca informações do canal pelo ID"""
        from wallclub_core.estr_organizacional.canal import Canal
        # Usar método centralizado get_canal
        canal = Canal.get_canal(canal_id)
        if canal:
            return {
                'id': canal.id,
                'codigo_canal': int(canal.canal) if canal.canal and canal.canal.isdigit() else 0,
                'codigo_cliente': int(canal.codigo_cliente) if canal.codigo_cliente and canal.codigo_cliente.isdigit() else 0,
                'key_loja': canal.keyvalue or '',
                'canal': canal.canal or '',
                'nome': canal.nome or ''
            }
        else:
            # Retornar valores padrão se canal não existir
            return {
                'id': canal_id,
                'codigo_canal': 0,
                'codigo_cliente': 0,
                'key_loja': '',
                'canal': '',
                'nome': ''
            }

    def pega_info_canal(self, identificador, tabela: str) -> Dict[str, Any]:
        """
        Busca informações do canal baseado no identificador e tabela de origem.
        
        Args:
            identificador: NSU (int) para Pinbank OU CNPJ (str) para Own
            tabela: 'transactiondata' ou 'transactiondata_own' (OBRIGATÓRIO)
        
        Returns:
            Dict com informações do canal (id, canal)
        
        Raises:
            Exception: Se canal não for encontrado
        """
        if tabela == 'transactiondata_own':
            return self._buscar_canal_por_cnpj(identificador)
        elif tabela == 'transactiondata':
            return self._buscar_canal_por_nsu(identificador)
        else:
            raise ValueError(f"Tabela inválida: {tabela}. Use 'transactiondata' ou 'transactiondata_own'")
    
    def _buscar_canal_por_nsu(self, nsu_operacao: int) -> Dict[str, Any]:
        """Busca canal pelo NSU (Pinbank) - método interno"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT   canal.id, canal.nome 
                FROM     wallclub.canal as canal,
                         wallclub.loja  as loja,  
                         wallclub.terminais as terminais, 
                         wallclub.transactiondata as td
                WHERE    td.nsuPinbank = %s
                         AND td.terminal= terminais.terminal 
                         AND ( terminais.inicio <=  UNIX_TIMESTAMP(DATE_ADD(td.datahora, INTERVAL 3 HOUR))  ) 
                         AND terminais.loja_id = loja.id 
                         AND loja.canal_id = canal.id 
                ORDER BY terminais.id DESC LIMIT 1
            """, [nsu_operacao])
            
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'canal': row[1]}
            else:
                raise Exception(f"Canal não encontrado para NSU {nsu_operacao}")
    
    def _buscar_canal_por_cnpj(self, cnpj: str) -> Dict[str, Any]:
        """Busca canal pelo CNPJ da loja (Own) - método interno"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT c.id, c.nome
                FROM wallclub.canal c
                INNER JOIN wallclub.loja l ON l.canal_id = c.id
                WHERE l.cnpj = %s
                LIMIT 1
            """, [cnpj])
            
            row = cursor.fetchone()
            if row:
                return {'id': row[0], 'canal': row[1]}
            else:
                raise Exception(f"Canal não encontrado para CNPJ {cnpj}")
    
    def obter_token(self) -> Dict[str, Any]:
        """
        Obtém token de acesso da API Pinbank.
        
        Returns:
            Dict com token e dados de expiração
            
        Raises:
            Exception: Em caso de erro na obtenção do token
        """
        cache_key = "pinbank_token"
        
        # Verifica se já temos um token válido em cache
        cached_token = cache.get(cache_key)
        if cached_token:
            registrar_log('pinbank', "Pinbank: Token obtido do cache")
            return cached_token
        
        registrar_log('pinbank', "Pinbank: Gerando novo token")
        
        try:
            # URL para obtenção do token
            token_url = f"{self.base_url}token"
            
            # Dados para requisição do token
            token_data = {
                'username': self.username,
                'password': self.password,
                'grant_type': 'password'
            }
            
            # Headers da requisição
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json',
                'User-Agent': 'WallClub-Django/1.0'
            }
            
            # Log da tentativa (sem credenciais sensíveis)
            registrar_log('pinbank', f"Pinbank: Solicitando token em {token_url}")
            
            # Fazer requisição para obter token
            response = requests.post(
                token_url,
                data=token_data,
                headers=headers,
                timeout=self.timeout,
                verify=False  # Desabilita verificação SSL
            )
            
            # Log da resposta
            registrar_log('pinbank', f"Pinbank: Resposta HTTP {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Erro HTTP {response.status_code}: {response.text}"
                registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
                raise Exception(f"Erro ao obter token Pinbank: {error_msg}")
            
            # Parse da resposta
            token_response = response.json()
            
            if 'access_token' not in token_response:
                registrar_log('pinbank', f"Pinbank: Resposta inválida - {token_response}", nivel='ERROR')
                raise Exception("Token não encontrado na resposta da API")
            
            # Preparar dados do token
            access_token = token_response['access_token']
            expires_in = token_response.get('expires_in', 3600)  # Padrão: 1 hora
            token_type = token_response.get('token_type', 'Bearer')
            
            # Calcular tempo de expiração
            expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            token_data = {
                'access_token': access_token,
                'token_type': token_type,
                'expires_in': expires_in,
                'expires_at': expires_at.isoformat(),
                'generated_at': datetime.now().isoformat()
            }
            
            # Salvar no cache (com margem de segurança de 5 minutos)
            cache_timeout = max(expires_in - 300, 60)  # Mínimo 1 minuto
            cache.set(cache_key, token_data, timeout=cache_timeout)
            
            registrar_log('pinbank', f"Pinbank: Token gerado com sucesso, expira em {expires_in}s")
            
            return {
                'access_token': access_token,
                'token_type': token_type,
                'expires_in': expires_in,
                'expires_at': expires_at.isoformat()
            }
            
        except requests.exceptions.Timeout:
            error_msg = "Timeout na requisição para Pinbank"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
            
        except requests.exceptions.ConnectionError:
            error_msg = "Erro de conexão com a API Pinbank"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição HTTP: {str(e)}"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
            
        except json.JSONDecodeError:
            error_msg = "Resposta inválida da API Pinbank (não é JSON válido)"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
            
        except Exception as e:
            error_msg = f"Erro inesperado ao obter token: {str(e)}"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
    
    def criptografar_payload(self, dados: Any) -> str:
        """
        Criptografa payload para envio à API Pinbank usando AES-128-CBC.
        
        Args:
            dados: Dados a serem criptografados (dict ou string)
            
        Returns:
            String JSON com payload criptografado
            
        Raises:
            Exception: Em caso de erro na criptografia
        """
        try:
            # Usar a senha configurada para criptografia
            key = self.password.encode('utf-8')
            
            # Garantir que a chave tenha 16 bytes (AES-128)
            if len(key) > 16:
                key = key[:16]
            elif len(key) < 16:
                key = key.ljust(16, b'\x00')
            
            # IV fixo com zeros
            iv = b'\x00' * 16
            
            # Converter dados para JSON se necessário
            if isinstance(dados, dict) or isinstance(dados, list):
                dados_json = json.dumps(dados, separators=(',', ':'))
            else:
                dados_json = str(dados)
            
            # Criptografar usando AES-128-CBC
            cipher = AES.new(key, AES.MODE_CBC, iv)
            dados_padded = pad(dados_json.encode('utf-8'), AES.block_size)
            criptografado = cipher.encrypt(dados_padded)
            
            # Codificar em base64
            base64_encoded = base64.b64encode(criptografado).decode('utf-8')
            
            # Retornar no formato esperado pela API Pinbank
            return json.dumps({
                'Data': {
                    'Json': base64_encoded
                }
            }, separators=(',', ':'))
            
        except Exception as e:
            registrar_log('pinbank', f"Pinbank: Erro ao criptografar payload - {e}", nivel='ERROR')
            raise Exception(f"Erro ao criptografar payload: {e}")
    
    def descriptografar_payload(self, resposta_criptografada: str) -> Any:
        """
        Descriptografa resposta da API Pinbank usando AES-128-CBC.
        
        Args:
            resposta_criptografada: String JSON com resposta criptografada
            
        Returns:
            Dados descriptografados
            
        Raises:
            Exception: Em caso de erro na descriptografia
        """
        try:
            # Verificar se a resposta é uma string válida
            if not isinstance(resposta_criptografada, str):
                raise Exception(f"Resposta não é uma string válida. Tipo: {type(resposta_criptografada)}")
            
            # Verificar se a resposta está vazia ou None
            if resposta_criptografada is None or not resposta_criptografada.strip():
                raise Exception("Resposta vazia ou None recebida para descriptografia")
            
            # Decodificar JSON da resposta
            try:
                objeto_resposta = json.loads(resposta_criptografada)
            except json.JSONDecodeError as e:
                raise Exception(f"Erro ao decodificar JSON: {e}")
            
            # Verificar estrutura esperada
            if 'Data' not in objeto_resposta:
                estrutura = json.dumps(objeto_resposta, indent=2)[:500]
                raise Exception(f"Estrutura JSON inesperada. Estrutura recebida: {estrutura}")
            
            # Verificar se Data não é None
            if objeto_resposta['Data'] is None:
                estrutura = json.dumps(objeto_resposta, indent=2)[:500]
                raise Exception(f"Campo Data é None. Estrutura completa: {estrutura}")
            
            # Obter conteúdo base64 (compatibilidade com diferentes chaves)
            if 'Json' in objeto_resposta['Data']:
                conteudo_base64 = objeto_resposta['Data']['Json']
            elif 'DataCriptografada' in objeto_resposta['Data']:
                conteudo_base64 = objeto_resposta['Data']['DataCriptografada']
            else:
                estrutura = json.dumps(objeto_resposta, indent=2)[:500]
                raise Exception(f"Estrutura JSON não contém chave Json ou DataCriptografada. Estrutura: {estrutura}")
            
            # Decodificar Base64
            try:
                conteudo = base64.b64decode(conteudo_base64)
            except Exception as e:
                raise Exception(f"Falha ao decodificar Base64: {e}")
            
            # Preparar chave para descriptografia
            key = self.password.encode('utf-8')
            if len(key) > 16:
                key = key[:16]
            elif len(key) < 16:
                key = key.ljust(16, b'\x00')
            
            # IV fixo com zeros
            iv = b'\x00' * 16
            
            # Descriptografar
            try:
                cipher = AES.new(key, AES.MODE_CBC, iv)
                texto_decifrado = cipher.decrypt(conteudo)
                texto_decifrado = unpad(texto_decifrado, AES.block_size)
                texto_decifrado = texto_decifrado.decode('utf-8')
            except Exception as e:
                raise Exception(f"Falha ao descriptografar o conteúdo: {e}")
            
            # Decodificar JSON resultante
            try:
                dados_json = json.loads(texto_decifrado)
            except json.JSONDecodeError as e:
                raise Exception(f"Erro ao decodificar JSON descriptografado: {e}")
            
            # Adaptar estrutura conforme necessário
            if isinstance(dados_json, dict):
                if 'Data' in dados_json:
                    return dados_json['Data']
                elif 'data' in dados_json:
                    return dados_json['data']
                elif not dados_json:  # Array vazio
                    return dados_json
                elif 'error' in dados_json or 'Error' in dados_json:
                    # Objeto de erro da API
                    return dados_json
            
            return dados_json
            
        except Exception as e:
            registrar_log('pinbank', f"Pinbank: Erro ao descriptografar payload - {e}", nivel='ERROR')
            raise e
    
    def consultar_extrato_pos_encrypted(self, username: str, password: str, dados: Dict[str, Any]) -> Any:
        """
        Consulta extrato POS com criptografia usando credenciais específicas.
        
        Args:
            username: Username específico do estabelecimento
            password: Password específico do estabelecimento  
            dados: Dados da consulta (período, quantidade, etc.)
            
        Returns:
            Lista de transações ou objeto de resposta da API
            
        Raises:
            Exception: Em caso de erro na consulta
        """
        try:
            registrar_log('pinbank', f"Pinbank: Consultando extrato POS para username={username}")
            
            # 1. Obter token de acesso usando credenciais globais
            token_data = self.obter_token()
            access_token = token_data['access_token']
            token_type = token_data['token_type']
            
            # 2. Criar instância temporária com credenciais específicas para criptografia
            temp_service = PinbankService()
            temp_service.username = username
            temp_service.password = password
            
            # 3. Criptografar payload usando credenciais específicas
            payload_criptografado = temp_service.criptografar_payload(dados)
            
            # 4. Fazer requisição para endpoint de extrato
            url = f"{self.base_url}ContaDigital/ExtratoPosEncrypted"
            
            headers = {
                'Authorization': f'{token_type} {access_token}',
                'UserName': username,
                'RequestOrigin': '5',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.post(
                url,
                data=payload_criptografado,
                headers=headers,
                timeout=30,
                verify=False
            )
            
            registrar_log('pinbank', f"Pinbank: Resposta HTTP {response.status_code}")
            
            if response.status_code != 200:
                error_msg = f"Erro HTTP {response.status_code}: {response.text}"
                registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
                raise Exception(f"Erro ao consultar extrato: {error_msg}")
            
            # 5. Descriptografar resposta usando credenciais específicas
            resposta_descriptografada = temp_service.descriptografar_payload(response.text)
            
            # 6. Verificar se é resposta "Sem resultado" da API
            if (isinstance(resposta_descriptografada, dict) and 
                resposta_descriptografada.get('ResultCode') == 1 and 
                resposta_descriptografada.get('Message') == 'Sem resultado.'):
                
                registrar_log('pinbank', f"Pinbank: Sem resultado para este período/estabelecimento")
                return []  # Retorna array vazio em vez de erro
            
            # 7. Verificar outros códigos de erro
            if (isinstance(resposta_descriptografada, dict) and 
                resposta_descriptografada.get('ResultCode') != 0):
                
                error_msg = resposta_descriptografada.get('Message', 'Erro desconhecido')
                registrar_log('pinbank', f"Pinbank: API retornou erro - {error_msg}")
                raise Exception(f"Erro da API Pinbank: {error_msg}")
            
            registrar_log('pinbank', f"Pinbank: Extrato consultado com sucesso")
            return resposta_descriptografada
            
        except Exception as e:
            error_msg = f"Erro ao consultar extrato POS: {str(e)}"
            registrar_log('pinbank', f"Pinbank: {error_msg}", nivel='ERROR')
            raise Exception(error_msg)
      
