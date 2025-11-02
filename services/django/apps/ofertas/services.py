"""
Services para ofertas - lógica de negócio
"""
import json
import time
from datetime import datetime
from django.db import connection, transaction
from django.db.models import Q
import threading

from typing import List, Optional

from apps.ofertas.models import Oferta, OfertaDisparo, OfertaEnvio
from apps.cliente.models import Cliente
from wallclub_core.integracoes.notification_service import NotificationService
from wallclub_core.utilitarios.log_control import registrar_log


class OfertaService:
    """Service para gestão de ofertas e disparos de push"""

    @staticmethod
    def criar_oferta(titulo, texto_push, descricao, imagem_url, vigencia_inicio, vigencia_fim,
                    canal_id, tipo_segmentacao, grupo_id, usuario_criador_id, ativo=True):
        """Cria uma nova oferta

        Args:
            titulo (str): Título da oferta
            texto_push (str): Texto curto do push notification
            descricao (str): Descrição detalhada para página do app
            imagem_url (str): URL da imagem
            vigencia_inicio (datetime): Data início vigência
            vigencia_fim (datetime): Data fim vigência
            canal_id (int): ID do canal
            tipo_segmentacao (str): 'todos_canal' ou 'grupo_customizado'
            grupo_id (int): ID do grupo (obrigatório se tipo=grupo_customizado)
            usuario_criador_id (int): ID do usuário criador
            ativo (bool): Oferta ativa

        Returns:
            tuple: (sucesso: bool, mensagem: str, oferta_id: int)
        """
        try:
            # Validações
            if not titulo or not texto_push or not vigencia_inicio or not vigencia_fim:
                return False, 'Título, texto push e datas de vigência são obrigatórios', None

            if vigencia_fim <= vigencia_inicio:
                return False, 'Data fim deve ser posterior à data início', None

            if tipo_segmentacao not in ['todos_canal', 'grupo_customizado']:
                return False, 'Tipo de segmentação inválido', None

            if tipo_segmentacao == 'grupo_customizado' and not grupo_id:
                return False, 'Grupo é obrigatório para segmentação customizada', None

            # Criar oferta
            oferta = Oferta(
                titulo=titulo,
                texto_push=texto_push,
                descricao=descricao,
                imagem_url=imagem_url,
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=vigencia_fim,
                canal_id=canal_id,
                tipo_segmentacao=tipo_segmentacao,
                grupo_id=grupo_id,
                usuario_criador_id=usuario_criador_id,
                ativo=ativo,
                created_at=datetime.now()
            )
            oferta.save()

            registrar_log('apps.ofertas', f'Oferta criada: {oferta.id} - {titulo} (canal={canal_id}, tipo={tipo_segmentacao})')
            return True, 'Oferta criada com sucesso', oferta.id

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao criar oferta: {str(e)}', nivel='ERROR')
            return False, f'Erro ao criar oferta: {str(e)}', None

    @staticmethod
    def listar_ofertas_vigentes(cliente_id):
        """Lista ofertas vigentes disponíveis para um cliente

        Busca ofertas baseado nas lojas, canais e grupos econômicos do cliente

        Args:
            cliente_id (int): ID do cliente

        Returns:
            list: Lista de dicionários com dados das ofertas
        """
        try:
            # Buscar cliente e canal
            cliente = Cliente.objects.filter(id=cliente_id).first()
            if not cliente:
                return []
            
            canal_id = cliente.canal_id

            # Buscar ofertas vigentes do canal
            agora = datetime.now()
            ofertas = Oferta.objects.filter(
                canal_id=canal_id,
                vigencia_inicio__lte=agora,
                vigencia_fim__gte=agora,
                ativo=True
            ).order_by('-created_at')

            # Filtrar por segmentação
            resultado = []
            for oferta in ofertas:
                # Se é 'todos_canal', cliente sempre recebe
                if oferta.tipo_segmentacao == 'todos_canal':
                    incluir = True
                # Se é 'grupo_customizado', verificar se cliente está no grupo
                elif oferta.tipo_segmentacao == 'grupo_customizado':
                    if oferta.grupo_id:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "SELECT 1 FROM ofertas_grupos_clientes WHERE grupo_id = %s AND cliente_id = %s",
                                [oferta.grupo_id, cliente_id]
                            )
                            incluir = cursor.fetchone() is not None
                    else:
                        incluir = False
                else:
                    incluir = False
                
                if incluir:
                    resultado.append({
                        'id': oferta.id,
                        'titulo': oferta.titulo,
                        'descricao': oferta.descricao,
                        'imagem_url': oferta.imagem_url,
                        'vigencia_inicio': oferta.vigencia_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                        'vigencia_fim': oferta.vigencia_fim.strftime('%Y-%m-%d %H:%M:%S'),
                        'tipo_segmentacao': oferta.tipo_segmentacao,
                        'canal_id': oferta.canal_id
                    })

            registrar_log('apps.ofertas', f'Ofertas listadas para cliente {cliente_id}: {len(resultado)} ofertas')
            return resultado

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao listar ofertas: {str(e)}', nivel='ERROR')
            return []

    @staticmethod
    def obter_oferta_cliente(oferta_id, cliente_id):
        """Busca uma oferta específica por ID com validação de acesso do cliente

        Valida se oferta está vigente e se cliente tem acesso
        (baseado em canal e segmentação)

        Args:
            oferta_id (int): ID da oferta
            cliente_id (int): ID do cliente

        Returns:
            dict: Dados da oferta ou None se não encontrada/sem acesso
        """
        try:
            # Buscar cliente e canal
            cliente = Cliente.objects.filter(id=cliente_id).first()
            if not cliente:
                return None
            
            canal_id = cliente.canal_id

            # Buscar oferta vigente do canal
            agora = datetime.now()
            oferta = Oferta.objects.filter(
                id=oferta_id,
                canal_id=canal_id,
                vigencia_inicio__lte=agora,
                vigencia_fim__gte=agora,
                ativo=True
            ).first()

            if not oferta:
                return None

            # Verificar segmentação
            if oferta.tipo_segmentacao == 'todos_canal':
                incluir = True
            elif oferta.tipo_segmentacao == 'grupo_customizado':
                if oferta.grupo_id:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT 1 FROM ofertas_grupos_clientes WHERE grupo_id = %s AND cliente_id = %s",
                            [oferta.grupo_id, cliente_id]
                        )
                        incluir = cursor.fetchone() is not None
                else:
                    incluir = False
            else:
                incluir = False
            
            if not incluir:
                return None

            # Retornar dados da oferta
            return {
                'id': oferta.id,
                'titulo': oferta.titulo,
                'descricao': oferta.descricao,
                'imagem_url': oferta.imagem_url,
                'vigencia_inicio': oferta.vigencia_inicio.strftime('%Y-%m-%d %H:%M:%S'),
                'vigencia_fim': oferta.vigencia_fim.strftime('%Y-%m-%d %H:%M:%S'),
                'tipo_segmentacao': oferta.tipo_segmentacao,
                'canal_id': oferta.canal_id
            }

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao buscar oferta por ID: {str(e)}', nivel='ERROR')
            return None

    @staticmethod
    def buscar_clientes_elegiveis(canal_id, tipo_segmentacao, grupo_id=None):
        """Busca clientes elegíveis para receber a oferta

        Baseado no tipo de segmentação:
        - todos_canal: todos os clientes ativos do canal com token
        - grupo_customizado: apenas clientes do grupo específico

        Args:
            canal_id (int): ID do canal
            tipo_segmentacao (str): 'todos_canal' ou 'grupo_customizado'
            grupo_id (int): ID do grupo (obrigatório se tipo=grupo_customizado)

        Returns:
            list: Lista de cliente_ids
        """
        try:
            with connection.cursor() as cursor:
                if tipo_segmentacao == 'todos_canal':
                    # Todos os clientes ativos do canal com token
                    cursor.execute(
                        """
                        SELECT id FROM cliente 
                        WHERE canal_id = %s 
                        AND is_active = 1
                        AND firebase_token IS NOT NULL 
                        AND firebase_token != ''
                        """,
                        [canal_id]
                    )
                    
                elif tipo_segmentacao == 'grupo_customizado':
                    if not grupo_id:
                        registrar_log('apps.ofertas', 'grupo_id obrigatório para segmentação customizada', nivel='ERROR')
                        return []
                    
                    # Clientes do grupo específico (com token)
                    cursor.execute(
                        """
                        SELECT c.id 
                        FROM cliente c
                        INNER JOIN ofertas_grupos_clientes gc ON c.id = gc.cliente_id
                        WHERE gc.grupo_id = %s 
                        AND c.canal_id = %s
                        AND c.is_active = 1
                        AND c.firebase_token IS NOT NULL 
                        AND c.firebase_token != ''
                        """,
                        [grupo_id, canal_id]
                    )
                    
                else:
                    registrar_log('apps.ofertas', f'Tipo de segmentação inválido: {tipo_segmentacao}', nivel='ERROR')
                    return []

                clientes = [row[0] for row in cursor.fetchall()]
                registrar_log('apps.ofertas', f'Clientes encontrados: {len(clientes)} (canal={canal_id}, tipo={tipo_segmentacao}, grupo={grupo_id})')
                return clientes

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao buscar clientes elegíveis: {str(e)}', nivel='ERROR')
            return []

    @staticmethod
    def disparar_push(oferta_id, usuario_disparador_id):
        """Dispara push notification para todos os clientes elegíveis

        Args:
            oferta_id (int): ID da oferta
            usuario_disparador_id (int): ID do usuário que solicitou

        Returns:
            tuple: (sucesso: bool, mensagem: str, disparo_id: int)
        """
        try:
            # Buscar oferta
            oferta = Oferta.objects.filter(id=oferta_id).first()
            if not oferta:
                return False, 'Oferta não encontrada', None

            if not oferta.ativo:
                return False, 'Oferta inativa', None

            # Criar registro de disparo
            disparo = OfertaDisparo(
                oferta_id=oferta_id,
                data_disparo=datetime.now(),
                usuario_disparador_id=usuario_disparador_id,
                status='processando',
                created_at=datetime.now()
            )
            disparo.save()

            # Buscar clientes elegíveis
            clientes = OfertaService.buscar_clientes_elegiveis(
                oferta.canal_id,
                oferta.tipo_segmentacao,
                oferta.grupo_id
            )

            disparo.total_clientes = len(clientes)
            disparo.save()

            registrar_log('apps.ofertas', f'Disparo {disparo.id} iniciado: {len(clientes)} clientes')

            # Processar envios em background
            thread = threading.Thread(
                target=OfertaService._processar_envios_background,
                args=(disparo.id, oferta_id, clientes)
            )
            thread.daemon = True
            thread.start()

            return True, f'Disparo iniciado para {len(clientes)} clientes', disparo.id

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao disparar push: {str(e)}', nivel='ERROR')
            return False, f'Erro ao disparar push: {str(e)}', None

    @staticmethod
    def _processar_envios_background(disparo_id, oferta_id, clientes):
        """Processa envios de push em background

        Args:
            disparo_id (int): ID do disparo
            oferta_id (int): ID da oferta
            clientes (list): Lista de IDs dos clientes
        """
        try:
            total_enviados = 0
            total_falhas = 0

            # Buscar oferta
            oferta = Oferta.objects.filter(id=oferta_id).first()
            if not oferta:
                registrar_log('apps.ofertas', f'Oferta {oferta_id} não encontrada', nivel='ERROR')
                return

            for cliente_id in clientes:
                try:
                    # Criar registro de envio
                    envio = OfertaEnvio(
                        oferta_disparo_id=disparo_id,
                        cliente_id=cliente_id,
                        created_at=datetime.now()
                    )
                    envio.save()

                    # Enviar push via NotificationService unificado
                    notification_service = NotificationService.get_instance(oferta.canal_id)
                    
                    resultado = notification_service.send_push(
                        cliente_id=cliente_id,
                        id_template='oferta_disponivel',
                        titulo_oferta=oferta.titulo,
                        texto_oferta=oferta.texto_push,
                        oferta_id=str(oferta_id)
                    )

                    if resultado.get('sucesso'):
                        envio.enviado = True
                        envio.data_envio = datetime.now()
                        total_enviados += 1
                    else:
                        envio.erro = resultado.get('mensagem', 'Erro desconhecido')
                        total_falhas += 1

                    envio.save()

                except Exception as e:
                    registrar_log('apps.ofertas', f'Erro ao enviar para cliente {cliente_id}: {str(e)}', nivel='ERROR')
                    total_falhas += 1

            # Atualizar disparo
            disparo = OfertaDisparo.objects.filter(id=disparo_id).first()
            if disparo:
                disparo.total_enviados = total_enviados
                disparo.total_falhas = total_falhas
                disparo.status = 'concluido' if total_falhas == 0 else 'erro'
                disparo.save()

            registrar_log('apps.ofertas', f'Disparo {disparo_id} finalizado: {total_enviados} enviados, {total_falhas} falhas')

        except Exception as e:
            registrar_log('apps.ofertas', f'Erro no processamento em background: {str(e)}', nivel='ERROR')
            # Atualizar disparo como erro
            disparo = OfertaDisparo.objects.filter(id=disparo_id).first()
            if disparo:
                disparo.status = 'erro'
                disparo.save()
    
    @staticmethod
    def listar_todas_ofertas() -> List[Oferta]:
        """
        Lista todas as ofertas do sistema ordenadas por data de criação
        
        Returns:
            Lista de ofertas
        """
        return list(Oferta.objects.all().order_by('-created_at'))
    
    @staticmethod
    def obter_oferta_por_id(oferta_id: int) -> Optional[Oferta]:
        """
        Busca oferta por ID
        
        Args:
            oferta_id: ID da oferta
            
        Returns:
            Oferta ou None
        """
        return Oferta.objects.filter(id=oferta_id).first()
    
    @staticmethod
    def atualizar_oferta(oferta_id: int, dados: dict) -> tuple:
        """
        Atualiza dados de uma oferta existente
        
        Args:
            oferta_id: ID da oferta
            dados: Dict com campos a atualizar
            
        Returns:
            tuple: (sucesso: bool, mensagem: str)
        """
        try:
            oferta = Oferta.objects.filter(id=oferta_id).first()
            if not oferta:
                return False, 'Oferta não encontrada'
            
            # Atualizar campos permitidos
            campos_permitidos = ['titulo', 'texto_push', 'descricao', 'imagem_url', 
                               'vigencia_inicio', 'vigencia_fim', 'ativo']
            
            for campo, valor in dados.items():
                if campo in campos_permitidos and valor is not None:
                    setattr(oferta, campo, valor)
            
            oferta.save()
            
            registrar_log('apps.ofertas', f'Oferta {oferta_id} atualizada')
            return True, 'Oferta atualizada com sucesso'
            
        except Exception as e:
            registrar_log('apps.ofertas', f'Erro ao atualizar oferta {oferta_id}: {str(e)}', nivel='ERROR')
            return False, f'Erro ao atualizar oferta: {str(e)}'
    
    @staticmethod
    def listar_disparos_oferta(oferta_id: int) -> List[OfertaDisparo]:
        """
        Lista todos os disparos de uma oferta ordenados por data
        
        Args:
            oferta_id: ID da oferta
            
        Returns:
            Lista de disparos
        """
        return list(OfertaDisparo.objects.filter(oferta_id=oferta_id).order_by('-data_disparo'))
    
    @staticmethod
    def listar_grupos_segmentacao(canal_id: Optional[int] = None, apenas_ativos: bool = True) -> list:
        """
        Lista grupos de segmentação, opcionalmente filtrados por canal
        
        Args:
            canal_id: ID do canal (opcional)
            apenas_ativos: Se True, retorna apenas grupos ativos
            
        Returns:
            Lista de grupos de segmentação
        """
        from apps.ofertas.models import GrupoSegmentacao
        
        queryset = GrupoSegmentacao.objects.all()
        
        if apenas_ativos:
            queryset = queryset.filter(ativo=True)
        
        if canal_id:
            queryset = queryset.filter(canal_id=canal_id)
        
        return list(queryset.order_by('canal_id', 'nome'))
