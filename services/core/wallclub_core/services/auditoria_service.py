"""
Serviço centralizado de auditoria para todas as ações críticas do sistema
Unifica auditoria de autenticação, transações, usuários, configurações e dados sensíveis
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from django.core.cache import cache
from django.db import models
from wallclub_core.utilitarios.log_control import registrar_log


class AuditoriaService:
    """
    Service centralizado para auditoria de todas ações críticas do sistema
    
    Responsabilidades:
    - Autenticação (login, logout, senha)
    - Transações financeiras (criação, cancelamento, estorno)
    - Usuários e permissões (criação, edição, remoção, mudança perfil)
    - Configurações (parâmetros, regras antifraude)
    - Dados sensíveis (CPF, email, telefone, senha)
    """
    
    # Configurações de detecção de ataques
    MAX_TENTATIVAS_FALHAS = 5
    JANELA_TEMPO_MINUTOS = 15
    TEMPO_BLOQUEIO_MINUTOS = 30
    
    # ================================================================================
    # AUTENTICAÇÃO
    # ================================================================================
    
    @classmethod
    def registrar_tentativa_login(cls, cpf: str, sucesso: bool, ip_address: str, 
                                  canal_id: int, endpoint: str,
                                  cliente_id: Optional[int] = None,
                                  user_agent: Optional[str] = None,
                                  motivo_falha: Optional[str] = None) -> Optional[object]:
        """
        Registra tentativa de login/validação de senha
        
        Args:
            cpf: CPF do cliente
            sucesso: Se a tentativa foi bem-sucedida
            ip_address: IP da requisição
            canal_id: ID do canal
            endpoint: Endpoint acessado
            cliente_id: ID do cliente se encontrado
            user_agent: User agent do navegador
            motivo_falha: Motivo da falha se houver
        
        Returns:
            Registro de auditoria criado
        """
        try:
            from wallclub_core.models import AuditoriaValidacaoSenha
            
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            
            auditoria = AuditoriaValidacaoSenha.objects.create(
                cliente_id=cliente_id,
                cpf=cpf_limpo,
                sucesso=sucesso,
                ip_address=ip_address,
                user_agent=user_agent or '',
                canal_id=canal_id,
                endpoint=endpoint,
                motivo_falha=motivo_falha
            )
            
            # NOTA: Incremento de failed_attempts removido daqui para evitar duplicação
            # O código de login já chama cliente_auth.record_failed_attempt() explicitamente
            
            # Verificar bloqueio
            if not sucesso:
                cls._verificar_e_bloquear(cpf_limpo, ip_address, cliente_id)
            
            return auditoria
            
        except Exception as e:
            registrar_log('auditoria.login', f"Erro ao registrar auditoria login: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def _verificar_e_bloquear(cls, cpf: str, ip_address: str, cliente_id: Optional[int] = None):
        """Verifica se deve bloquear CPF ou IP por excesso de tentativas"""
        try:
            from wallclub_core.models import AuditoriaValidacaoSenha
            
            janela_inicio = datetime.now() - timedelta(minutes=cls.JANELA_TEMPO_MINUTOS)
            
            # Contar falhas por CPF
            tentativas_cpf = AuditoriaValidacaoSenha.objects.filter(
                cpf=cpf,
                sucesso=False,
                timestamp__gte=janela_inicio
            ).count()
            
            # Contar falhas por IP
            tentativas_ip = AuditoriaValidacaoSenha.objects.filter(
                ip_address=ip_address,
                sucesso=False,
                timestamp__gte=janela_inicio
            ).count()
            
            # Bloquear CPF
            if tentativas_cpf >= cls.MAX_TENTATIVAS_FALHAS:
                cache_key = f"blocked_cpf:{cpf}"
                cache.set(cache_key, True, timeout=cls.TEMPO_BLOQUEIO_MINUTOS * 60)
                registrar_log('auditoria.login', 
                             f"CPF bloqueado: {cpf} ({tentativas_cpf} tentativas)",
                             nivel='WARNING')
            
            # Bloquear IP
            if tentativas_ip >= cls.MAX_TENTATIVAS_FALHAS:
                cache_key = f"blocked_ip:{ip_address}"
                cache.set(cache_key, True, timeout=cls.TEMPO_BLOQUEIO_MINUTOS * 60)
                registrar_log('auditoria.login', 
                             f"IP bloqueado: {ip_address} ({tentativas_ip} tentativas)",
                             nivel='WARNING')
                
        except Exception as e:
            registrar_log('auditoria.login', f"Erro ao verificar bloqueio: {str(e)}", nivel='ERROR')
    
    @classmethod
    def verificar_bloqueio(cls, cpf: Optional[str] = None, 
                          ip_address: Optional[str] = None) -> tuple:
        """
        Verifica se CPF ou IP está bloqueado
        
        Returns:
            (bloqueado: bool, motivo: str, tempo_restante: int)
        """
        try:
            if cpf:
                cpf_limpo = ''.join(filter(str.isdigit, cpf))
                cache_key = f"blocked_cpf:{cpf_limpo}"
                if cache.get(cache_key):
                    ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else cls.TEMPO_BLOQUEIO_MINUTOS * 60
                    return True, "CPF bloqueado temporariamente", ttl
            
            if ip_address:
                cache_key = f"blocked_ip:{ip_address}"
                if cache.get(cache_key):
                    ttl = cache.ttl(cache_key) if hasattr(cache, 'ttl') else cls.TEMPO_BLOQUEIO_MINUTOS * 60
                    return True, "IP bloqueado temporariamente", ttl
            
            return False, None, 0
            
        except Exception as e:
            registrar_log('auditoria.login', f"Erro ao verificar bloqueio: {str(e)}", nivel='ERROR')
            return False, None, 0
    
    # ================================================================================
    # TRANSAÇÕES FINANCEIRAS
    # ================================================================================
    
    @classmethod
    def registrar_transacao(cls, acao: str, transacao_id: int, usuario_id: int,
                           valor_anterior: Optional[float] = None,
                           valor_novo: Optional[float] = None,
                           status_anterior: Optional[str] = None,
                           status_novo: Optional[str] = None,
                           motivo: Optional[str] = None,
                           ip_address: Optional[str] = None) -> bool:
        """
        Registra ação em transação financeira
        
        Args:
            acao: Tipo de ação (criacao, cancelamento, estorno, alteracao_valor, alteracao_status)
            transacao_id: ID da transação
            usuario_id: ID do usuário que executou
            valor_anterior: Valor antes da alteração
            valor_novo: Valor depois da alteração
            status_anterior: Status antes da alteração
            status_novo: Status depois da alteração
            motivo: Motivo da ação
            ip_address: IP da requisição
        
        Returns:
            bool: Sucesso do registro
        """
        try:
            dados = {
                'acao': acao,
                'transacao_id': transacao_id,
                'usuario_id': usuario_id,
                'valor_anterior': valor_anterior,
                'valor_novo': valor_novo,
                'status_anterior': status_anterior,
                'status_novo': status_novo,
                'motivo': motivo,
                'ip_address': ip_address
            }
            
            registrar_log('auditoria.transacao',
                         f"[{acao.upper()}] Transação {transacao_id} por usuário {usuario_id} - {motivo or 'Sem motivo'}",
                         nivel='INFO')
            
            return True
            
        except Exception as e:
            registrar_log('auditoria.transacao', f"Erro ao registrar auditoria transação: {str(e)}", nivel='ERROR')
            return False
    
    # ================================================================================
    # USUÁRIOS E PERMISSÕES
    # ================================================================================
    
    @classmethod
    def registrar_usuario(cls, acao: str, usuario_id: int, executado_por: int,
                         dados_alterados: Optional[Dict] = None,
                         ip_address: Optional[str] = None) -> bool:
        """
        Registra ação em usuário (criação, edição, remoção, mudança perfil)
        
        Args:
            acao: Tipo de ação (criacao, edicao, remocao, mudanca_perfil, mudanca_permissao)
            usuario_id: ID do usuário afetado
            executado_por: ID do usuário que executou
            dados_alterados: Dict com dados alterados (antes/depois)
            ip_address: IP da requisição
        
        Returns:
            bool: Sucesso do registro
        """
        try:
            dados = {
                'acao': acao,
                'usuario_id': usuario_id,
                'executado_por': executado_por,
                'dados_alterados': dados_alterados or {},
                'ip_address': ip_address
            }
            
            registrar_log('auditoria.usuario',
                         f"[{acao.upper()}] Usuário {usuario_id} por {executado_por}",
                         nivel='INFO',
                         extra=dados)
            
            return True
            
        except Exception as e:
            registrar_log('auditoria.usuario', f"Erro ao registrar auditoria usuário: {str(e)}", nivel='ERROR')
            return False
    
    # ================================================================================
    # CONFIGURAÇÕES
    # ================================================================================
    
    @classmethod
    def registrar_configuracao(cls, tipo: str, config_id: int, usuario_id: int,
                              valor_anterior: Optional[Any] = None,
                              valor_novo: Optional[Any] = None,
                              descricao: Optional[str] = None) -> bool:
        """
        Registra alteração em configuração do sistema
        
        Args:
            tipo: Tipo de configuração (parametros_wall, regra_antifraude, blacklist, whitelist)
            config_id: ID da configuração
            usuario_id: ID do usuário que alterou
            valor_anterior: Valor antes da alteração
            valor_novo: Valor depois da alteração
            descricao: Descrição da alteração
        
        Returns:
            bool: Sucesso do registro
        """
        try:
            dados = {
                'tipo': tipo,
                'config_id': config_id,
                'usuario_id': usuario_id,
                'valor_anterior': str(valor_anterior),
                'valor_novo': str(valor_novo),
                'descricao': descricao
            }
            
            registrar_log('auditoria.configuracao',
                         f"[{tipo.upper()}] Config {config_id} alterada por usuário {usuario_id} - {descricao}",
                         nivel='INFO',
                         extra=dados)
            
            return True
            
        except Exception as e:
            registrar_log('auditoria.configuracao', f"Erro ao registrar auditoria configuração: {str(e)}", nivel='ERROR')
            return False
    
    # ================================================================================
    # DADOS SENSÍVEIS
    # ================================================================================
    
    @classmethod
    def registrar_dados_sensiveis(cls, tipo: str, cliente_id: int, campo: str,
                                  valor_anterior: Optional[str] = None,
                                  valor_novo: Optional[str] = None,
                                  executado_por: Optional[int] = None,
                                  ip_address: Optional[str] = None) -> bool:
        """
        Registra alteração de dados sensíveis
        
        Args:
            tipo: Tipo de alteração (cpf, email, telefone, senha)
            cliente_id: ID do cliente
            campo: Campo alterado
            valor_anterior: Valor antes (mascarado se sensível)
            valor_novo: Valor depois (mascarado se sensível)
            executado_por: ID do usuário que executou
            ip_address: IP da requisição
        
        Returns:
            bool: Sucesso do registro
        """
        try:
            # Mascarar valores sensíveis no log
            valor_anterior_log = cls._mascarar_valor(tipo, valor_anterior) if valor_anterior else None
            valor_novo_log = cls._mascarar_valor(tipo, valor_novo) if valor_novo else None
            
            dados = {
                'tipo': tipo,
                'cliente_id': cliente_id,
                'campo': campo,
                'valor_anterior': valor_anterior_log,
                'valor_novo': valor_novo_log,
                'executado_por': executado_por,
                'ip_address': ip_address
            }
            
            registrar_log('auditoria.dados_sensiveis',
                         f"[{tipo.upper()}] Cliente {cliente_id} - Campo {campo} alterado",
                         nivel='WARNING',
                         extra=dados)
            
            return True
            
        except Exception as e:
            registrar_log('auditoria.dados_sensiveis', f"Erro ao registrar auditoria dados sensíveis: {str(e)}", nivel='ERROR')
            return False
    
    @staticmethod
    def _mascarar_valor(tipo: str, valor: str) -> str:
        """Mascara valores sensíveis"""
        if not valor:
            return None
        
        if tipo == 'cpf':
            return f"{valor[:3]}.***.**{valor[-2:]}" if len(valor) >= 5 else "***"
        elif tipo == 'email':
            partes = valor.split('@')
            if len(partes) == 2:
                return f"{partes[0][:2]}***@{partes[1]}"
            return "***@***"
        elif tipo == 'telefone':
            return f"({valor[:2]}) ****-{valor[-4:]}" if len(valor) >= 6 else "****-****"
        elif tipo == 'senha':
            return "********"
        else:
            return "***"
    
    # ================================================================================
    # ESTATÍSTICAS E RELATÓRIOS
    # ================================================================================
    
    @classmethod
    def obter_estatisticas_cpf(cls, cpf: str, dias: int = 7) -> Optional[Dict]:
        """
        Obtém estatísticas de tentativas para um CPF
        
        Args:
            cpf: CPF a consultar
            dias: Número de dias para análise
        
        Returns:
            Dict com estatísticas do CPF
        """
        try:
            from wallclub_core.models import AuditoriaValidacaoSenha
            
            cpf_limpo = ''.join(filter(str.isdigit, cpf))
            data_inicio = datetime.now() - timedelta(days=dias)
            
            tentativas = AuditoriaValidacaoSenha.objects.filter(
                cpf=cpf_limpo,
                timestamp__gte=data_inicio
            )
            
            total = tentativas.count()
            sucessos = tentativas.filter(sucesso=True).count()
            falhas = tentativas.filter(sucesso=False).count()
            ips_diferentes = tentativas.values('ip_address').distinct().count()
            ultima = tentativas.order_by('-timestamp').first()
            
            return {
                'cpf': cpf_limpo,
                'total_tentativas': total,
                'sucessos': sucessos,
                'falhas': falhas,
                'taxa_sucesso': round((sucessos / total * 100) if total > 0 else 0, 2),
                'ips_diferentes': ips_diferentes,
                'ultima_tentativa': ultima.timestamp if ultima else None,
                'ultima_sucesso': ultima.sucesso if ultima else None
            }
            
        except Exception as e:
            registrar_log('auditoria.login', f"Erro ao obter estatísticas: {str(e)}", nivel='ERROR')
            return None
    
    @classmethod
    def obter_tentativas_suspeitas(cls, horas: int = 24, limite: int = 10) -> Optional[Dict]:
        """
        Obtém CPFs/IPs com padrão suspeito de tentativas
        
        Args:
            horas: Janela de tempo em horas
            limite: Número máximo de resultados
        
        Returns:
            Dict com CPFs e IPs suspeitos
        """
        try:
            from wallclub_core.models import AuditoriaValidacaoSenha
            from django.db.models import Count
            
            data_inicio = datetime.now() - timedelta(hours=horas)
            
            # CPFs com mais falhas
            cpfs_suspeitos = AuditoriaValidacaoSenha.objects.filter(
                timestamp__gte=data_inicio,
                sucesso=False
            ).values('cpf').annotate(
                total=Count('id')
            ).filter(
                total__gte=cls.MAX_TENTATIVAS_FALHAS
            ).order_by('-total')[:limite]
            
            # IPs com mais falhas
            ips_suspeitos = AuditoriaValidacaoSenha.objects.filter(
                timestamp__gte=data_inicio,
                sucesso=False
            ).values('ip_address').annotate(
                total=Count('id')
            ).filter(
                total__gte=cls.MAX_TENTATIVAS_FALHAS
            ).order_by('-total')[:limite]
            
            return {
                'cpfs_suspeitos': list(cpfs_suspeitos),
                'ips_suspeitos': list(ips_suspeitos),
                'periodo_horas': horas
            }
            
        except Exception as e:
            registrar_log('auditoria.login', f"Erro ao obter tentativas suspeitas: {str(e)}", nivel='ERROR')
            return None
