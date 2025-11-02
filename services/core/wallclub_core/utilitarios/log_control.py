"""
Utilitário para controle dinâmico de logs por processo.
Inspirado no log_control.php do sistema PHP legado.
Permite ativar/desativar logs específicos via banco de dados.
VERSÃO SIMPLIFICADA - Acesso direto ao MySQL sem depender de modelo Django.
"""
import os
import logging
from datetime import datetime
from typing import Optional
from django.conf import settings
from django.core.cache import cache
from django.db import connection


logger = logging.getLogger(__name__)


def log_esta_habilitado(processo: str) -> bool:
    """
    Verifica se o log está habilitado para um processo específico.
    
    Args:
        processo (str): Nome do processo/módulo (ex: 'autenticacao', 'reset_senha')
        
    Returns:
        bool: True se o log está habilitado, False caso contrário
    """
    # Cache key para evitar consultas repetitivas ao banco
    cache_key = f"log_habilitado_{processo}"
    
    # Tentar buscar do cache primeiro (cache por 5 minutos)
    resultado = cache.get(cache_key)
    if resultado is not None:
        return resultado
    
    try:
        # Importar aqui para evitar circular import
        from wallclub_core.models import LogParametro
        
        # Buscar no banco
        try:
            log_param = LogParametro.objects.get(processo=processo)
            habilitado = log_param.ligado
        except LogParametro.DoesNotExist:
            # Se não encontrou o processo, assumir que está habilitado por padrão
            habilitado = True
            logger.warning(f"Processo '{processo}' não encontrado na tabela log_parametros. Assumindo habilitado.")
        
        # Cachear resultado por 5 minutos
        cache.set(cache_key, habilitado, 300)
        return habilitado
        
    except Exception as e:
        logger.error(f"Erro ao verificar se log está habilitado para '{processo}': {e}")
        # Em caso de erro, assumir que está habilitado
        return True


def obter_nivel_log(processo: str) -> str:
    """
    Obtém o nível de log configurado para um processo.
    
    Args:
        processo (str): Nome do processo/módulo
        
    Returns:
        str: Nível do log ('DEBUG' ou 'ERROR')
    """
    cache_key = f"nivel_log_{processo}"
    resultado = cache.get(cache_key)
    if resultado is not None:
        return resultado
    
    try:
        from wallclub_core.models import LogParametro
        try:
            log_param = LogParametro.objects.get(processo=processo)
            nivel = log_param.nivel or 'DEBUG'
        except LogParametro.DoesNotExist:
            nivel = 'DEBUG'
        
        cache.set(cache_key, nivel, 600)
        return nivel
    except Exception as e:
        logger.error(f"Erro ao obter nível de log para '{processo}': {e}")
        return 'DEBUG'


def obter_arquivo_log(processo: str) -> str:
    """
    Obtém o nome do arquivo de log específico para um processo.
    
    Args:
        processo (str): Nome do processo/módulo
        
    Returns:
        str: Nome do arquivo de log (ex: 'autenticacao.log')
    """
    # Cache key para evitar consultas repetitivas ao banco
    cache_key = f"arquivo_log_{processo}"
    
    # Tentar buscar do cache primeiro (cache por 10 minutos)
    resultado = cache.get(cache_key)
    if resultado is not None:
        return resultado
    
    try:
        # Importar aqui para evitar circular import
        from wallclub_core.models import LogParametro
        
        # Buscar no banco
        try:
            log_param = LogParametro.objects.get(processo=processo)
            arquivo_log = log_param.arquivo_log
        except LogParametro.DoesNotExist:
            # Se não encontrou o processo, usar nome padrão
            arquivo_log = f"{processo}.log"
            logger.warning(f"Processo '{processo}' não encontrado na tabela log_parametros. Usando arquivo padrão: {arquivo_log}")
        
        # Cachear resultado por 10 minutos
        cache.set(cache_key, arquivo_log, 600)
        return arquivo_log
        
    except Exception as e:
        logger.error(f"Erro ao obter arquivo de log para '{processo}': {e}")
        # Em caso de erro, usar nome padrão
        return f"{processo}.log"


def registrar_log(processo: str, mensagem: str, nivel: str = 'INFO') -> None:
    """
    Registra uma mensagem de log apenas se o processo estiver habilitado.
    
    Args:
        processo (str): Nome do processo/módulo
        mensagem (str): Mensagem a ser registrada
        nivel (str): Nível da mensagem ('INFO' ou 'ERROR'). Default: 'INFO'
        
    Filtro hierárquico:
        - Se processo configurado como 'ERROR': só loga mensagens 'ERROR'
        - Se processo configurado como 'DEBUG': loga tudo ('INFO' e 'ERROR')
    """
    # Verificar se o log está habilitado para este processo
    if not log_esta_habilitado(processo):
        return
    
    try:
        # Obter nível configurado do processo
        nivel_config = obter_nivel_log(processo)
        
        # Filtro hierárquico:
        # - ERROR: só loga ERROR
        # - DEBUG: loga tudo (INFO e ERROR)
        if nivel_config == 'ERROR' and nivel != 'ERROR':
            return  # Não loga INFO se config é ERROR
        
        # Obter nome do arquivo de log
        nome_arquivo = obter_arquivo_log(processo)
        
        # Garantir que o diretório de logs existe
        logs_dir = os.path.join(settings.BASE_DIR, 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # Caminho completo do arquivo
        caminho_arquivo = os.path.join(logs_dir, nome_arquivo)
        
        # Formatar mensagem com timestamp e nível
        timestamp = datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')
        mensagem_formatada = f"{timestamp} [{nivel}] {mensagem}\n"
        
        # Escrever no arquivo
        with open(caminho_arquivo, 'a', encoding='utf-8') as arquivo:
            arquivo.write(mensagem_formatada)
            
    except Exception as e:
        logger.error(f"Erro ao registrar log para processo '{processo}': {e}")


def limpar_cache_log(processo: Optional[str] = None) -> None:
    """
    Limpa o cache de configurações de log.
    
    Args:
        processo (str, optional): Se especificado, limpa apenas o cache deste processo.
                                 Se None, limpa todo o cache de log.
    """
    if processo:
        # Limpar cache específico
        cache.delete(f"log_habilitado_{processo}")
        cache.delete(f"arquivo_log_{processo}")
        cache.delete(f"nivel_log_{processo}")
    else:
        # Limpar todo o cache de log (pattern matching)
        try:
            # Tentar buscar todas as chaves que começam com log_
            keys_to_delete = []
            for key in cache._cache.keys():
                if key.startswith('log_habilitado_') or key.startswith('arquivo_log_') or key.startswith('nivel_log_'):
                    keys_to_delete.append(key)
            
            for key in keys_to_delete:
                cache.delete(key)
                
        except Exception as e:
            logger.warning(f"Não foi possível limpar todo o cache de log: {e}")


def criar_processo_log(processo: str, arquivo_log: str, descricao: str = "", ligado: bool = True, nivel: str = 'DEBUG') -> bool:
    """
    Cria ou atualiza um processo de log na tabela log_parametros.
    
    Args:
        processo (str): Nome do processo
        arquivo_log (str): Nome do arquivo de log
        descricao (str): Descrição do processo
        ligado (bool): Se o log deve estar ativo
        nivel (str): Nível do log ('DEBUG' ou 'ERROR'). Default: 'DEBUG'
        
    Returns:
        bool: True se criou/atualizou com sucesso
    """
    try:
        from wallclub_core.models import LogParametro
        
        log_param, created = LogParametro.objects.get_or_create(
            processo=processo,
            defaults={
                'arquivo_log': arquivo_log,
                'descricao': descricao,
                'ligado': ligado,
                'nivel': nivel
            }
        )
        
        if not created:
            # Atualizar se já existia
            log_param.arquivo_log = arquivo_log
            log_param.descricao = descricao
            log_param.ligado = ligado
            log_param.nivel = nivel
            log_param.save()
        
        # Limpar cache para este processo
        limpar_cache_log(processo)
        
        action = "criado" if created else "atualizado"
        logger.info(f"Processo de log '{processo}' {action} com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar/atualizar processo de log '{processo}': {e}")
        return False
