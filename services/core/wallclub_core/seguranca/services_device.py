"""
Service para gerenciamento de dispositivos confiáveis
Controla registro, validação, revogação e notificações de dispositivos
"""
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from django.db import transaction
from django.core.cache import cache
from wallclub_core.seguranca.models import DispositivoConfiavel
from wallclub_core.utilitarios.log_control import registrar_log


class DeviceManagementService:
    """Serviço para gerenciamento de dispositivos confiáveis"""

    # Limites de dispositivos por tipo de usuário
    LIMITES_DISPOSITIVOS = {
        'cliente': 2,      # Até 2 dispositivos por cliente
        'vendedor': 2,     # Até 2 dispositivos por vendedor
        'lojista': 2,      # Até 2 dispositivos por lojista
        'admin': None      # Sem limite para admin
    }

    # Validade padrão de dispositivo confiável (30 dias)
    VALIDADE_DIAS = 30

    @classmethod
    def calcular_fingerprint(cls, dados_dispositivo: Dict) -> str:
        """
        Calcula fingerprint único do dispositivo usando MD5
        Normaliza user_agent para ignorar versão do app (WallClub/311 → WallClub)

        Args:
            dados_dispositivo: Dict com user_agent, screen_resolution, timezone, etc

        Returns:
            str: Hash MD5 do fingerprint
        """
        try:
            # Normalizar user_agent removendo versão do app
            user_agent = dados_dispositivo.get('user_agent', '')
            import re
            # WallClub/311 → WallClub, WallClub/312 → WallClub
            user_agent_normalizado = re.sub(r'(WallClub|AClub)/\d+', r'\1', user_agent)
            
            # Concatenar dados relevantes do dispositivo
            componentes = [
                user_agent_normalizado,  # User-agent sem versão
                dados_dispositivo.get('screen_resolution', ''),
                dados_dispositivo.get('timezone', ''),
                dados_dispositivo.get('platform', ''),
                dados_dispositivo.get('language', ''),
            ]

            # Gerar string única
            fingerprint_str = '|'.join(filter(None, componentes))

            # Calcular MD5
            fingerprint_hash = hashlib.md5(fingerprint_str.encode('utf-8')).hexdigest()

            registrar_log('comum.seguranca', f"Fingerprint calculado: {fingerprint_hash[:8]}... (user_agent: {user_agent} → {user_agent_normalizado})", nivel='DEBUG')

            return fingerprint_hash

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao calcular fingerprint: {str(e)}", nivel='ERROR')
            # Fallback: usar apenas user-agent
            return hashlib.md5(dados_dispositivo.get('user_agent', 'unknown').encode('utf-8')).hexdigest()

    @classmethod
    def registrar_dispositivo(
        cls,
        user_id: int,
        tipo_usuario: str,
        dados_dispositivo: Dict,
        ip_registro: str,
        marcar_confiavel: bool = True
    ) -> Tuple[DispositivoConfiavel, bool, str]:
        """
        Registra ou atualiza dispositivo do usuário

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo (cliente, vendedor, admin, lojista)
            dados_dispositivo: Dict com user_agent, screen, timezone, etc
            ip_registro: IP de origem
            marcar_confiavel: Se deve marcar como confiável (30 dias)

        Returns:
            Tuple[DispositivoConfiavel, bool, str]: (dispositivo, criado, mensagem)
        """
        try:
            # CRÍTICO: NUNCA sobrescrever fingerprint fornecido pelo app
            # App já calcula o fingerprint corretamente no lado do cliente
            fingerprint = dados_dispositivo.get('device_fingerprint')
            
            if not fingerprint or fingerprint.strip() == '':
                # Apenas calcular se app NÃO enviou fingerprint
                registrar_log('comum.seguranca',
                    f"Device fingerprint NÃO fornecido pelo app, calculando no backend...", nivel='DEBUG')
                fingerprint = cls.calcular_fingerprint(dados_dispositivo)
                registrar_log('comum.seguranca',
                    f"Fingerprint calculado no backend: {fingerprint[:8]}...", nivel='DEBUG')
            else:
                # USAR o fingerprint do app sem modificação
                registrar_log('comum.seguranca',
                    f"✅ Device fingerprint FORNECIDO pelo app (usando sem modificação): {fingerprint[:8]}...", nivel='INFO')
                # NÃO recalcular, NÃO validar, apenas USAR o que o app enviou

            # Verificar se dispositivo já existe (apenas ativos)
            dispositivo_existente = DispositivoConfiavel.objects.filter(
                device_fingerprint=fingerprint,
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                ativo=True
            ).first()

            if dispositivo_existente:
                # Dispositivo ativo encontrado: renovar validade
                dispositivo_existente.ultimo_acesso = datetime.now()
                if marcar_confiavel:
                    dispositivo_existente.confiavel_ate = datetime.now() + timedelta(days=cls.VALIDADE_DIAS)
                dispositivo_existente.save()

                registrar_log(
                    'comum.seguranca',
                    f"Dispositivo existente renovado: {tipo_usuario} ID:{user_id} - {fingerprint[:8]}",
                    nivel='INFO'
                )

                return dispositivo_existente, False, "Dispositivo renovado com sucesso"

            # Se chegou aqui: dispositivo não existe ou foi revogado
            # Criar NOVO registro para manter histórico completo de auditoria

            # Verificar limite de dispositivos para o tipo de usuário
            limite = cls.LIMITES_DISPOSITIVOS.get(tipo_usuario)

            if limite is not None:
                dispositivos_ativos = DispositivoConfiavel.objects.filter(
                    user_id=user_id,
                    tipo_usuario=tipo_usuario,
                    ativo=True
                ).count()

                if dispositivos_ativos >= limite:
                    registrar_log(
                        'comum.seguranca',
                        f"Limite de dispositivos atingido: {tipo_usuario} ID:{user_id} - {dispositivos_ativos}/{limite}",
                        nivel='WARNING'
                    )

                    # Para clientes (limite 1), bloquear automaticamente
                    if tipo_usuario == 'cliente':
                        return None, False, f"Limite de {limite} dispositivo atingido. Revogue o dispositivo atual para adicionar um novo."

                    return None, False, f"Limite de {limite} dispositivos atingido. Revogue um dispositivo para adicionar novo."

            # Calcular validade (30 dias se confiável)
            confiavel_ate = None
            if marcar_confiavel:
                confiavel_ate = datetime.now() + timedelta(days=cls.VALIDADE_DIAS)

            # Usar nome fornecido ou extrair do user-agent como fallback
            nome_dispositivo = dados_dispositivo.get('nome_dispositivo')
            if not nome_dispositivo:
                user_agent = dados_dispositivo.get('user_agent', '')
                nome_dispositivo = cls._extrair_nome_dispositivo(user_agent)

            user_agent = dados_dispositivo.get('user_agent', '')

            # Criar novo dispositivo
            with transaction.atomic():
                dispositivo = DispositivoConfiavel.objects.create(
                    user_id=user_id,
                    tipo_usuario=tipo_usuario,
                    device_fingerprint=fingerprint,
                    nome_dispositivo=nome_dispositivo,
                    user_agent=user_agent,
                    ip_registro=ip_registro,
                    ultimo_acesso=datetime.now(),
                    ativo=True,
                    confiavel_ate=confiavel_ate
                )

                registrar_log(
                    'comum.seguranca',
                    f"Novo dispositivo registrado: {tipo_usuario} ID:{user_id} - {nome_dispositivo} - {fingerprint[:8]}",
                    nivel='INFO'
                )

                # Notificar usuário sobre novo dispositivo
                cls.notificar_novo_dispositivo(user_id, tipo_usuario, nome_dispositivo, ip_registro)

                return dispositivo, True, "Dispositivo registrado com sucesso"

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao registrar dispositivo: {str(e)}", nivel='ERROR')
            return None, False, f"Erro ao registrar dispositivo: {str(e)}"

    @classmethod
    def validar_dispositivo(
        cls,
        user_id: int,
        tipo_usuario: str,
        fingerprint: str
    ) -> Tuple[bool, Optional[DispositivoConfiavel], str]:
        """
        Valida se dispositivo é confiável e está ativo

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            fingerprint: Hash do fingerprint

        Returns:
            Tuple[bool, DispositivoConfiavel, str]: (válido, dispositivo, mensagem)
        """
        try:
            # Buscar dispositivo
            dispositivo = DispositivoConfiavel.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                device_fingerprint=fingerprint,
                ativo=True
            ).first()

            if not dispositivo:
                registrar_log(
                    'comum.seguranca',
                    f"Dispositivo não encontrado ou inativo: {tipo_usuario} ID:{user_id} - {fingerprint[:8]}",
                    nivel='WARNING'
                )
                return False, None, "Dispositivo não reconhecido"

            # Verificar se ainda está dentro da validade (30 dias)
            if dispositivo.confiavel_ate:
                if datetime.now() > dispositivo.confiavel_ate:
                    registrar_log(
                        'comum.seguranca',
                        f"Dispositivo expirado: {tipo_usuario} ID:{user_id} - {dispositivo.nome_dispositivo}",
                        nivel='WARNING'
                    )
                    return False, dispositivo, "Dispositivo expirado. Necessário revalidar com 2FA."

            # Atualizar último acesso
            dispositivo.ultimo_acesso = datetime.now()
            dispositivo.save()

            registrar_log(
                'comum.seguranca',
                f"Dispositivo validado: {tipo_usuario} ID:{user_id} - {dispositivo.nome_dispositivo}",
                nivel='DEBUG'
            )

            return True, dispositivo, "Dispositivo confiável"

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao validar dispositivo: {str(e)}", nivel='ERROR')
            return False, None, f"Erro ao validar dispositivo: {str(e)}"

    @classmethod
    def verificar_limite(
        cls,
        user_id: int,
        tipo_usuario: str,
        device_fingerprint: str
    ) -> Dict:
        """
        Verifica se usuário atingiu limite de dispositivos.
        Retorna info do device existente se limite atingido.

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            device_fingerprint: Fingerprint do novo device tentando entrar

        Returns:
            Dict: {
                'limite_atingido': bool,
                'device_atual': Dict ou None,
                'limite_maximo': int
            }
        """
        try:
            # Verificar se device é o mesmo já cadastrado
            device_existente = DispositivoConfiavel.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                device_fingerprint=device_fingerprint,
                ativo=True
            ).first()

            if device_existente:
                # É o mesmo device, não atingiu limite
                return {
                    'limite_atingido': False,
                    'device_atual': None,
                    'limite_maximo': cls.LIMITES_DISPOSITIVOS.get(tipo_usuario)
                }

            # Buscar limite do tipo de usuário
            limite = cls.LIMITES_DISPOSITIVOS.get(tipo_usuario)

            if limite is None:
                # Sem limite (admin)
                return {
                    'limite_atingido': False,
                    'device_atual': None,
                    'limite_maximo': None
                }

            # Contar dispositivos ativos
            dispositivos_ativos = DispositivoConfiavel.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                ativo=True
            )

            quantidade_ativos = dispositivos_ativos.count()

            if quantidade_ativos >= limite:
                # Limite atingido, pegar info do device atual
                device_atual = dispositivos_ativos.first()

                return {
                    'limite_atingido': True,
                    'device_atual': {
                        'id': device_atual.id,
                        'nome_dispositivo': device_atual.nome_dispositivo,
                        'ultimo_acesso': device_atual.ultimo_acesso.isoformat(),
                        'criado_em': device_atual.criado_em.isoformat(),
                        'dias_desde_acesso': (datetime.now() - device_atual.ultimo_acesso).days
                    },
                    'limite_maximo': limite
                }

            # Não atingiu limite
            return {
                'limite_atingido': False,
                'device_atual': None,
                'limite_maximo': limite
            }

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao verificar limite: {str(e)}", nivel='ERROR')
            # Em caso de erro, assumir que não atingiu limite (fail-open)
            return {
                'limite_atingido': False,
                'device_atual': None,
                'limite_maximo': None
            }

    @classmethod
    def listar_dispositivos(
        cls,
        user_id: int,
        tipo_usuario: str,
        apenas_ativos: bool = True
    ) -> List[Dict]:
        """
        Lista dispositivos do usuário

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            apenas_ativos: Se deve listar apenas ativos

        Returns:
            List[Dict]: Lista de dispositivos
        """
        try:
            query = DispositivoConfiavel.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario
            )

            if apenas_ativos:
                query = query.filter(ativo=True)

            dispositivos = query.order_by('-ultimo_acesso')

            resultado = []
            for disp in dispositivos:
                # Verificar se está expirado
                expirado = False
                dias_restantes = None

                if disp.confiavel_ate:
                    dias_restantes = (disp.confiavel_ate - datetime.now()).days
                    expirado = dias_restantes < 0

                resultado.append({
                    'id': disp.id,
                    'nome_dispositivo': disp.nome_dispositivo,
                    'fingerprint': disp.device_fingerprint[:16] + '...',
                    'ip_registro': disp.ip_registro,
                    'ultimo_acesso': disp.ultimo_acesso.strftime('%d/%m/%Y %H:%M'),
                    'ativo': disp.ativo,
                    'confiavel': disp.esta_confiavel(),
                    'expirado': expirado,
                    'dias_restantes': dias_restantes if dias_restantes and dias_restantes > 0 else 0,
                    'criado_em': disp.criado_em.strftime('%d/%m/%Y %H:%M'),
                    'revogado_em': disp.revogado_em.strftime('%d/%m/%Y %H:%M') if disp.revogado_em else None,
                    'revogado_por': disp.revogado_por
                })

            registrar_log(
                'comum.seguranca',
                f"Listados {len(resultado)} dispositivos: {tipo_usuario} ID:{user_id}",
                nivel='DEBUG'
            )

            return resultado

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao listar dispositivos: {str(e)}", nivel='ERROR')
            return []

    @classmethod
    def revogar_dispositivo(
        cls,
        user_id: int = None,
        tipo_usuario: str = None,
        device_fingerprint: str = None,
        dispositivo_id: int = None,
        revogado_por: str = 'usuario'
    ) -> Dict[str, any]:
        """
        Revoga dispositivo (marca como inativo)
        Aceita busca por fingerprint+user_id OU dispositivo_id

        Args:
            user_id: ID do usuário (usado com fingerprint)
            tipo_usuario: Tipo do usuário (usado com fingerprint)
            device_fingerprint: Fingerprint do dispositivo
            dispositivo_id: ID direto do dispositivo
            revogado_por: Quem revogou (usuario, sistema, admin)

        Returns:
            Dict: {'sucesso': bool, 'mensagem': str}
        """
        try:
            # LOG DETALHADO: Parâmetros recebidos
            registrar_log('comum.seguranca',
                f"🔍 [REVOGAR] Parâmetros recebidos:",
                nivel='INFO')
            registrar_log('comum.seguranca',
                f"  - user_id: {user_id}",
                nivel='INFO')
            registrar_log('comum.seguranca',
                f"  - tipo_usuario: {tipo_usuario}",
                nivel='INFO')
            registrar_log('comum.seguranca',
                f"  - device_fingerprint: {device_fingerprint}",
                nivel='INFO')
            registrar_log('comum.seguranca',
                f"  - dispositivo_id: {dispositivo_id}",
                nivel='INFO')
            
            # Buscar dispositivo por fingerprint ou ID
            if device_fingerprint and user_id and tipo_usuario:
                # LOG: Listar TODOS os dispositivos ativos do usuário antes de revogar
                dispositivos_ativos = DispositivoConfiavel.objects.filter(
                    user_id=user_id,
                    tipo_usuario=tipo_usuario,
                    ativo=True
                )
                
                registrar_log('comum.seguranca',
                    f"📱 [REVOGAR] Dispositivos ativos encontrados para user_id={user_id}: {dispositivos_ativos.count()}",
                    nivel='INFO')
                
                for idx, disp in enumerate(dispositivos_ativos, 1):
                    registrar_log('comum.seguranca',
                        f"  [{idx}] ID={disp.id}, fingerprint={disp.device_fingerprint}, "
                        f"nome={disp.nome_dispositivo}, user_agent={disp.user_agent}",
                        nivel='INFO')
                
                # Buscar dispositivo específico pelo fingerprint
                dispositivo = DispositivoConfiavel.objects.filter(
                    device_fingerprint=device_fingerprint,
                    user_id=user_id,
                    tipo_usuario=tipo_usuario,
                    ativo=True
                ).first()
                
                # LOG: Resultado da busca
                if dispositivo:
                    registrar_log('comum.seguranca',
                        f"✅ [REVOGAR] Dispositivo encontrado pelo fingerprint:",
                        nivel='INFO')
                    registrar_log('comum.seguranca',
                        f"  - ID: {dispositivo.id}",
                        nivel='INFO')
                    registrar_log('comum.seguranca',
                        f"  - fingerprint: {dispositivo.device_fingerprint}",
                        nivel='INFO')
                    registrar_log('comum.seguranca',
                        f"  - nome: {dispositivo.nome_dispositivo}",
                        nivel='INFO')
                    registrar_log('comum.seguranca',
                        f"  - user_agent: {dispositivo.user_agent}",
                        nivel='INFO')
                else:
                    registrar_log('comum.seguranca',
                        f"❌ [REVOGAR] NENHUM dispositivo encontrado com fingerprint={device_fingerprint}",
                        nivel='WARNING')
            elif dispositivo_id:
                dispositivo = DispositivoConfiavel.objects.filter(id=dispositivo_id).first()
            else:
                return {'sucesso': False, 'mensagem': 'Parâmetros insuficientes para localizar dispositivo'}

            if not dispositivo:
                registrar_log('comum.seguranca',
                    f"❌ [REVOGAR] Dispositivo não encontrado para revogação",
                    nivel='WARNING')
                return {'sucesso': False, 'mensagem': 'Dispositivo não encontrado'}

            # LOG: Antes de revogar
            registrar_log('comum.seguranca',
                f"🗑️ [REVOGAR] Revogando dispositivo ID={dispositivo.id}, fingerprint={dispositivo.device_fingerprint}",
                nivel='INFO')
            
            # Usar update() para evitar violação de constraint unique_user_device_ativo
            DispositivoConfiavel.objects.filter(id=dispositivo.id).update(
                ativo=False,
                revogado_em=datetime.now(),
                revogado_por=revogado_por
            )
            
            # Recarregar objeto para notificação
            dispositivo.refresh_from_db()

            registrar_log(
                'comum.seguranca',
                f"✅ [REVOGAR] Dispositivo revogado com sucesso: {dispositivo.tipo_usuario} ID:{dispositivo.user_id} - "
                f"{dispositivo.nome_dispositivo} (fingerprint={dispositivo.device_fingerprint}) - por {revogado_por}",
                nivel='INFO'
            )

            # Notificar usuário sobre revogação
            try:
                cls.notificar_dispositivo_removido(
                    dispositivo.user_id,
                    dispositivo.tipo_usuario,
                    dispositivo.nome_dispositivo,
                    revogado_por
                )
            except Exception as e:
                # Não falhar se notificação falhar
                registrar_log('comum.seguranca', f"Erro ao notificar revogação: {str(e)}", nivel='WARNING')

            return {'sucesso': True, 'mensagem': 'Dispositivo removido com sucesso'}

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao revogar dispositivo: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro ao revogar dispositivo: {str(e)}'}

    @classmethod
    def revogar_todos_dispositivos(
        cls,
        user_id: int,
        tipo_usuario: str,
        revogado_por: str = 'sistema'
    ) -> Tuple[int, str]:
        """
        Revoga TODOS os dispositivos de um usuário
        Usado quando troca senha ou detecta atividade suspeita

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            revogado_por: Quem revogou

        Returns:
            Tuple[int, str]: (quantidade revogada, mensagem)
        """
        try:
            dispositivos = DispositivoConfiavel.objects.filter(
                user_id=user_id,
                tipo_usuario=tipo_usuario,
                ativo=True
            )

            quantidade = dispositivos.count()

            if quantidade == 0:
                return 0, "Nenhum dispositivo ativo encontrado"

            # Revogar todos
            dispositivos.update(
                ativo=False,
                revogado_em=datetime.now(),
                revogado_por=revogado_por
            )

            registrar_log(
                'comum.seguranca',
                f"Todos os dispositivos revogados: {tipo_usuario} ID:{user_id} - {quantidade} dispositivos - por {revogado_por}",
                nivel='WARNING'
            )

            return quantidade, f"{quantidade} dispositivo(s) revogado(s) com sucesso"

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao revogar todos dispositivos: {str(e)}", nivel='ERROR')
            return 0, f"Erro ao revogar dispositivos: {str(e)}"

    @classmethod
    def notificar_novo_dispositivo(
        cls,
        user_id: int,
        tipo_usuario: str,
        nome_dispositivo: str,
        ip_origem: str
    ):
        """
        Notifica usuário sobre novo dispositivo detectado

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            nome_dispositivo: Nome do dispositivo
            ip_origem: IP de origem
        """
        try:
            registrar_log(
                'comum.seguranca',
                f"NOTIFICAÇÃO: Novo dispositivo - {tipo_usuario} ID:{user_id} - {nome_dispositivo} - IP:{ip_origem}",
                nivel='INFO'
            )

            # Notificação deve ser disparada pelo caller (quem chamou registrar_dispositivo)
            # que já tem acesso aos dados do usuário
            # CORE não deve buscar dados de apps específicos

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao notificar novo dispositivo: {str(e)}", nivel='ERROR')

    @classmethod
    def notificar_dispositivo_removido(
        cls,
        user_id: int,
        tipo_usuario: str,
        nome_dispositivo: str,
        removido_por: str
    ):
        """
        Notifica usuário sobre dispositivo removido

        Args:
            user_id: ID do usuário
            tipo_usuario: Tipo do usuário
            nome_dispositivo: Nome do dispositivo
            removido_por: Quem removeu (usuário, admin, sistema)
        """
        try:
            registrar_log(
                'comum.seguranca',
                f"NOTIFICAÇÃO: Dispositivo removido - {tipo_usuario} ID:{user_id} - {nome_dispositivo} - por {removido_por}",
                nivel='INFO'
            )

            # Notificação deve ser disparada pelo caller (quem chamou remover_dispositivo)
            # que já tem acesso aos dados do usuário
            # CORE não deve buscar dados de apps específicos

        except Exception as e:
            registrar_log('comum.seguranca', f"Erro ao notificar dispositivo removido: {str(e)}", nivel='ERROR')

    @staticmethod
    def _extrair_nome_dispositivo(user_agent: str) -> str:
        """
        Extrai nome amigável do dispositivo a partir do User-Agent

        Args:
            user_agent: String do User-Agent

        Returns:
            str: Nome amigável do dispositivo
        """
        user_agent_lower = user_agent.lower()

        # Detectar SO
        if 'iphone' in user_agent_lower:
            return 'iPhone'
        elif 'ipad' in user_agent_lower:
            return 'iPad'
        elif 'android' in user_agent_lower:
            if 'mobile' in user_agent_lower:
                return 'Android Phone'
            else:
                return 'Android Tablet'
        elif 'windows' in user_agent_lower:
            if 'chrome' in user_agent_lower:
                return 'Chrome Desktop (Windows)'
            elif 'firefox' in user_agent_lower:
                return 'Firefox Desktop (Windows)'
            else:
                return 'Windows Desktop'
        elif 'macintosh' in user_agent_lower or 'mac os' in user_agent_lower:
            if 'safari' in user_agent_lower and 'chrome' not in user_agent_lower:
                return 'Safari Desktop (Mac)'
            elif 'chrome' in user_agent_lower:
                return 'Chrome Desktop (Mac)'
            else:
                return 'Mac Desktop'
        elif 'linux' in user_agent_lower:
            return 'Linux Desktop'

        return 'Dispositivo Desconhecido'
