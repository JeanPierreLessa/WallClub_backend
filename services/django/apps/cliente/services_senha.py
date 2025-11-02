"""
Service para gerenciamento e validação de senhas de clientes.
Implementa regras de senha forte, histórico e migração gradual.
"""

from datetime import datetime, timedelta
from django.contrib.auth.hashers import make_password, check_password
from django.conf import settings
from wallclub_core.utilitarios.log_control import registrar_log


class SenhaService:
    """
    Service centralizado para gerenciamento de senhas de clientes.
    """
    
    # Configurações de senha forte
    MIN_LENGTH = getattr(settings, 'PASSWORD_MIN_LENGTH', 8)
    REQUIRE_LETTER = getattr(settings, 'PASSWORD_REQUIRE_LETTER', True)
    REQUIRE_NUMBER = getattr(settings, 'PASSWORD_REQUIRE_NUMBER', True)
    HISTORY_COUNT = getattr(settings, 'PASSWORD_HISTORY_COUNT', 3)
    
    # Data de corte para migração gradual
    DATA_CORTE_SENHA_FORTE = datetime.strptime(
        getattr(settings, 'SENHA_FORTE_DATA_CORTE', '2025-10-20'),
        '%Y-%m-%d'
    )
    
    @staticmethod
    def validar_senha_forte(senha):
        """
        Valida se a senha cumpre os requisitos de senha forte.
        
        Args:
            senha (str): Senha a ser validada
            
        Returns:
            dict: {'valida': bool, 'erros': list}
        """
        erros = []
        
        # Verificar tamanho mínimo
        if len(senha) < SenhaService.MIN_LENGTH:
            erros.append(f'Senha deve ter pelo menos {SenhaService.MIN_LENGTH} caracteres')
        
        # Verificar se contém letra
        if SenhaService.REQUIRE_LETTER and not any(c.isalpha() for c in senha):
            erros.append('Senha deve conter pelo menos uma letra')
        
        # Verificar se contém número
        if SenhaService.REQUIRE_NUMBER and not any(c.isdigit() for c in senha):
            erros.append('Senha deve conter pelo menos um número')
        
        return {
            'valida': len(erros) == 0,
            'erros': erros
        }
    
    @staticmethod
    def gerar_senha_temporaria():
        """
        Gera senha temporária de 4 dígitos.
        
        Returns:
            str: Senha de 4 dígitos
        """
        import random
        return ''.join([str(random.randint(0, 9)) for _ in range(4)])
    
    @staticmethod
    def cliente_requer_senha_forte(cliente_auth):
        """
        Verifica se cliente é obrigado a ter senha forte baseado na data de criação.
        
        Estratégia de migração gradual:
        - Usuários criados APÓS data de corte: senha forte obrigatória
        - Usuários criados ANTES: aceita senha antiga (compatibilidade)
        
        Args:
            cliente_auth (ClienteAuth): Objeto ClienteAuth
            
        Returns:
            bool: True se requer senha forte
        """
        # Se cliente foi criado após data de corte, exige senha forte
        if hasattr(cliente_auth.cliente, 'created_at'):
            return cliente_auth.cliente.created_at >= SenhaService.DATA_CORTE_SENHA_FORTE
        
        # Fallback: não exigir para clientes antigos sem data
        return False
    
    @staticmethod
    def trocar_senha(cliente, senha_atual, nova_senha):
        """
        Troca senha do cliente validando a senha atual.
        
        Args:
            cliente (Cliente): Objeto Cliente
            senha_atual (str): Senha atual do cliente
            nova_senha (str): Nova senha
            
        Returns:
            dict: {'sucesso': bool, 'mensagem': str}
        """
        from apps.cliente.models import ClienteAuth
        
        # Validar senha atual
        if not cliente.check_password(senha_atual):
            return {
                'sucesso': False,
                'mensagem': 'Senha atual incorreta'
            }
        
        # Validar nova senha
        validacao = SenhaService.validar_senha_forte(nova_senha)
        if not validacao['valida']:
            return {
                'sucesso': False,
                'mensagem': ' | '.join(validacao['erros'])
            }
        
        # Verificar histórico (não repetir últimas 3)
        if SenhaService.senha_no_historico(cliente, nova_senha):
            return {
                'sucesso': False,
                'mensagem': f'Não é permitido reutilizar as últimas {SenhaService.HISTORY_COUNT} senhas'
            }
        
        try:
            # Adicionar senha atual ao histórico
            SenhaService.adicionar_ao_historico(cliente, cliente.hash_senha)
            
            # Atualizar senha
            cliente.set_password(nova_senha)
            cliente.save(update_fields=['hash_senha'])
            
            # Atualizar data da última troca
            cliente_auth = ClienteAuth.objects.get(cliente=cliente)
            cliente_auth.last_password_change = datetime.now()
            cliente_auth.save(update_fields=['last_password_change'])
            
            # Invalidar todos dispositivos confiáveis (troca de senha = risco de segurança)
            SenhaService.invalidar_dispositivos_confiaveis(cliente)
            
            registrar_log('apps.cliente',
                f"Senha trocada para cliente_id={cliente.id}", nivel='INFO')
            
            return {
                'sucesso': True,
                'mensagem': 'Senha alterada com sucesso. Todos dispositivos foram desconectados.'
            }
            
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao trocar senha: {str(e)}", nivel='ERROR')
            return {
                'sucesso': False,
                'mensagem': 'Erro ao alterar senha'
            }
    
    @staticmethod
    def adicionar_ao_historico(cliente, password_hash):
        """
        Adiciona senha ao histórico do cliente.
        
        Args:
            cliente (Cliente): Objeto Cliente
            password_hash (str): Hash da senha
        """
        from apps.cliente.models import SenhaHistorico
        
        SenhaHistorico.objects.create(
            cliente=cliente,
            password_hash=password_hash,
            criado_em=datetime.now()
        )
        
        # Manter apenas as últimas N senhas
        senhas_antigas = SenhaHistorico.objects.filter(
            cliente=cliente
        ).order_by('-criado_em')[SenhaService.HISTORY_COUNT:]
        
        for senha in senhas_antigas:
            senha.delete()
    
    @staticmethod
    def senha_no_historico(cliente, nova_senha):
        """
        Verifica se senha já foi usada recentemente.
        
        Args:
            cliente (Cliente): Objeto Cliente
            nova_senha (str): Senha a verificar
            
        Returns:
            bool: True se senha está no histórico
        """
        from apps.cliente.models import SenhaHistorico
        
        historico = SenhaHistorico.objects.filter(
            cliente=cliente
        ).order_by('-criado_em')[:SenhaService.HISTORY_COUNT]
        
        for registro in historico:
            if check_password(nova_senha, registro.password_hash):
                return True
        
        return False
    
    @staticmethod
    def invalidar_dispositivos_confiaveis(cliente):
        """
        Invalida todos dispositivos confiáveis do cliente.
        Chamado após troca de senha por segurança.
        
        Args:
            cliente (Cliente): Objeto Cliente
        """
        from wallclub_core.seguranca.services_device import DeviceManagementService
        
        try:
            DeviceManagementService.revogar_todos_dispositivos(
                user_id=cliente.id,
                tipo_usuario='cliente'
            )
            registrar_log('apps.cliente',
                f"Dispositivos invalidados após troca de senha (cliente_id={cliente.id})",
                nivel='INFO')
        except Exception as e:
            registrar_log('apps.cliente',
                f"Erro ao invalidar dispositivos: {str(e)}", nivel='ERROR')
