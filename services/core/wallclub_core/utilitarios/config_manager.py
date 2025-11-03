"""
ConfigManager - Gerenciador de configurações híbridas para WallClub Django

Gerencia configurações usando AWS Secrets Manager para desenvolvimento e produção.
- Desenvolvimento: usa secret 'wall/dev/db'
- Produção: usa secret 'wall/prod/db'
"""
import json
import os
import boto3
from typing import Any, Dict
from wallclub_core.utilitarios.log_control import registrar_log

class ConfigManager:
    """
    Gerenciador de configurações que usa AWS Secrets Manager
    """
    
    def __init__(self):
        self.is_production = self._detect_production_environment()
        self._aws_session = None
        self._secrets_client = None
        
        # Inicializar cliente AWS sempre (desenvolvimento e produção usam AWS Secrets)
        self._initialize_aws_clients()
    
    def _detect_production_environment(self) -> bool:
        """
        Detecta se está em ambiente de produção
        """
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        return environment == 'production'
    
    def _get_secret_name(self) -> str:
        """
        Retorna o nome do secret baseado no ambiente - configurável via .env
        """
        if self.is_production:
            return os.getenv('AWS_SECRET_NAME_PROD', 'wall/prod/db')
        else:
            return os.getenv('AWS_SECRET_NAME_DEV', 'wall/dev/db')
    
    def _initialize_aws_clients(self):
        """
        Inicializa clientes AWS
        """
        try:
            # Usar região us-east-1 como padrão
            region = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
            
            self._aws_session = boto3.Session()
            self._secrets_client = boto3.client('secretsmanager', region_name=region)
            # Log removido - causava dependência circular durante inicialização Django
            
        except Exception as e:
            # Log removido - causava dependência circular durante inicialização Django
            self._secrets_client = None
    
    def get_secret(self, secret_name: str, default: Any = None) -> Any:
        """
        Busca um secret do AWS Secrets Manager
        
        Args:
            secret_name: Nome do secret (ex: 'wall/dev/db' ou 'wall/prod/db')
            default: Valor padrão se não encontrar
            
        Returns:
            Valor do secret ou default
        """
        try:
            if not self._secrets_client:
                # Log removido - pode ocorrer durante inicialização Django
                return default
                
            response = self._secrets_client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
            
        except Exception as e:
            # Log removido - pode ocorrer durante inicialização Django
            return default
    
    def get_database_config(self) -> Dict[str, Any]:
        """
        Obtém configurações do banco de dados do AWS Secret ou ENV vars (fallback)
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            
            if secret_string:
                secrets = json.loads(secret_string)
                
                # Configuração do Django para MySQL usando chaves do secret
                config = {
                    'ENGINE': 'django.db.backends.mysql',
                    'NAME': secrets.get('DB_DATABASE_PYTHON'),  
                    'USER': secrets.get('DB_USER_PYTHON'),
                    'PASSWORD': secrets.get('DB_PASS_PYTHON'),
                    'HOST': secrets.get('DB_HOST'),
                    'PORT': '3306',  
                    'OPTIONS': {
                        'charset': 'utf8mb4',
                        'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
                    },
                }
                
                # Validar se configurações críticas estão presentes
                critical_fields = ['USER', 'PASSWORD', 'HOST']
                missing_fields = [field for field in critical_fields if not config.get(field)]
                
                if not missing_fields:
                    return config
        
        except Exception:
            pass
        
        # Fallback para variáveis de ambiente (desenvolvimento local)
        return {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.getenv('DB_NAME', 'wallclub'),
            'USER': os.getenv('DB_USER', 'root'),
            'PASSWORD': os.getenv('DB_PASSWORD', ''),
            'HOST': os.getenv('DB_HOST', 'localhost'),
            'PORT': os.getenv('DB_PORT', '3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    
    def get_bureau_config(self) -> Dict[str, Any]:
        """
        Obtém configurações do Bureau de Crédito do AWS Secret
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            if not secret_string:
                return {}
                
            secrets = json.loads(secret_string)
            
            config = {
                'url': secrets.get('BUREAU_URL'),
                'access_token': secrets.get('BUREAU_ACCESS_TOKEN'),
                'token_id': secrets.get('BUREAU_TOKEN_ID'),
            }
            
            return config
            
        except Exception as e:
            pass
            return {}
    
    def get_pinbank_config(self) -> Dict[str, Any]:
        """
        Obtém configurações do Pinbank do AWS Secret
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            if not secret_string:
                return {}
                
            secrets = json.loads(secret_string)
            
            config = {
                'url': secrets.get('PINBANK_URL'),
                'username': secrets.get('PINBANK_WALL_USERNAME'),
                'password': secrets.get('PINBANK_WALL_PASSWD'),
            }
            
            return config
            
        except Exception as e:
            pass
            return {}
    
    def get_email_config(self) -> Dict[str, Any]:
        """
        Obtém configurações de email do AWS Secret
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            if not secret_string:
                return {}
                
            secrets = json.loads(secret_string)
            
            config = {
                'host': secrets.get('WEBSERVER_HOST'),
                'user': secrets.get('WEBSERVER_USER'),
                'password': secrets.get('WEBSERVER_PASSWD'),
            }
            
            return config
            
        except Exception as e:
            pass
            return {}
    
    def get_maxmind_config(self) -> Dict[str, Any]:
        """
        Obtém configurações do MaxMind minFraud do AWS Secret
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            if not secret_string:
                return {}
                
            secrets = json.loads(secret_string)
            
            config = {
                'account_id': secrets.get('MAXMIND_ACCOUNT_ID'),
                'license_key': secrets.get('MAXMIND_LICENSE_KEY'),
            }
            
            return config
            
        except Exception as e:
            pass
            return {}
    
    def get_riskengine_credentials(self) -> Dict[str, str]:
        """
        Obtém credenciais OAuth do Risk Engine do AWS Secret
        Retorna 3 pares de credenciais separadas:
        - admin: Portal Admin (wallclub-django)
        - pos: POSP2 + Checkout (wallclub-pos-checkout)
        - internal: Uso interno geral (wallclub_django_internal)
        """
        try:
            secret_string = self.get_secret(self._get_secret_name())
            if not secret_string:
                return {}
                
            secrets = json.loads(secret_string)
            
            return {
                'admin_client_id': secrets.get('RISK_ENGINE_ADMIN_CLIENT_ID', 'wallclub-django'),
                'admin_client_secret': secrets.get('RISK_ENGINE_ADMIN_CLIENT_SECRET', ''),
                'pos_client_id': secrets.get('RISK_ENGINE_POS_CLIENT_ID', 'wallclub-pos-checkout'),
                'pos_client_secret': secrets.get('RISK_ENGINE_POS_CLIENT_SECRET', ''),
                'internal_client_id': secrets.get('RISK_ENGINE_INTERNAL_CLIENT_ID', 'wallclub_django_internal'),
                'internal_client_secret': secrets.get('RISK_ENGINE_INTERNAL_CLIENT_SECRET', ''),
            }
            
        except Exception as e:
            pass
            return {}


# Instância global do gerenciador (lazy loading)
_config_manager_instance = None

def get_config_manager():
    """
    Retorna a instância do ConfigManager (lazy loading)
    """
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
