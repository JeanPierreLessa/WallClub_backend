"""Service para Sistema de Controle de Acesso - Opção 2: Apenas Permissões
Usa tabelas existentes, gerencia permissões sem campo tipo_usuario
"""
from typing import List, Optional, Dict, Any
from django.db.models import Q
from django.contrib.sessions.models import Session
from datetime import datetime
import hashlib
from .models import PortalUsuario, PortalPermissao, PortalUsuarioAcesso


class ControleAcessoService:
    """
    Service principal para gerenciar controle de acesso
    Implementa Opção 2: sistema baseado apenas em permissões
    """

    # Hierarquia de níveis (do menor para o maior)
    HIERARQUIA_NIVEIS = ['negado', 'leitura', 'escrita', 'admin']

    # Níveis granulares por portal
    NIVEIS_ADMIN = [
        'admin_total',         # Acesso completo sem filtros
        'admin_superusuario',  # Super usuário (quase total, sem parâmetros)
        'admin_canal',         # Admin com filtro por canal
        'leitura_canal'        # Leitura com filtro por canal
        #'leitura_regional',   # Leitura com filtro regional
        #'leitura_vendedor'    # Leitura com filtro vendedor
    ]

    NIVEIS_LOJISTA = [
        'lojista_admin',    # Acesso completo lojista
        'grupo_economico',  # Filtro por grupo econômico
        'lojista'          # Filtro por loja específica
    ]

    # Seções disponíveis por nível de acesso
    SECOES_POR_NIVEL = {
        # Portal Admin
        'admin_total': ['dashboard', 'usuarios', 'transacoes', 'parametros', 'relatorios', 'hierarquia', 'pagamentos', 'gestao_admin', 'terminais', 'rpr'],
        'admin_superusuario': ['dashboard', 'usuarios', 'transacoes', 'relatorios', 'hierarquia', 'gestao_admin', 'terminais', 'rpr'],
        'admin_canal': ['dashboard', 'transacoes', 'relatorios', 'hierarquia', 'terminais', 'rpr', 'usuarios_canal'],

        # Portal Lojista
        'lojista_admin': ['dashboard', 'vendas', 'terminais', 'relatorios', 'conciliacao', 'recebimentos'],
        'grupo_economico': ['dashboard', 'vendas', 'relatorios', 'recebimentos'],
        'lojista': ['dashboard', 'vendas', 'terminais'],
    }

    @classmethod
    def usuario_tem_acesso_portal(cls, usuario: PortalUsuario, portal: str) -> bool:
        """
        Verifica se usuário tem acesso a um portal

        Args:
            usuario: Usuário Portal
            portal: Nome do portal ('admin', 'lojista', 'corporativo')

        Returns:
            bool: True se tem acesso, False caso contrário
        """
        try:
            permissao = PortalPermissao.objects.get(
                usuario=usuario,
                portal=portal
            )
            return permissao.nivel_acesso != 'negado'
        except PortalPermissao.DoesNotExist:
            return False

    @classmethod
    def obter_nivel_portal(cls, usuario: PortalUsuario, portal: str) -> str:
        """
        Obtém nível de acesso do usuário ao portal

        Args:
            usuario: Usuário Portal
            portal: Nome do portal

        Returns:
            str: Nível de acesso ('negado', 'leitura', 'escrita', 'admin')
        """
        try:
            permissao = PortalPermissao.objects.get(
                usuario=usuario,
                portal=portal
            )
            return permissao.nivel_acesso
        except PortalPermissao.DoesNotExist:
            return 'negado'

    @classmethod
    def usuario_tem_nivel_minimo(cls, usuario: PortalUsuario, portal: str, nivel_minimo: str) -> bool:
        """
        Verifica se usuário tem nível mínimo no portal

        Args:
            usuario: Usuário Portal
            portal: Nome do portal
            nivel_minimo: Nível mínimo necessário

        Returns:
            bool: True se tem nível suficiente, False caso contrário
        """
        nivel_usuario = cls.obter_nivel_portal(usuario, portal)

        try:
            idx_usuario = cls.HIERARQUIA_NIVEIS.index(nivel_usuario)
            idx_minimo = cls.HIERARQUIA_NIVEIS.index(nivel_minimo)
            return idx_usuario >= idx_minimo
        except ValueError:
            return False

    @classmethod
    def obter_vinculos_usuario(cls, usuario: PortalUsuario, entidade_tipo: Optional[str] = None, portal: Optional[str] = None) -> List[PortalUsuarioAcesso]:
        """
        Obtém vínculos de acesso do usuário

        Args:
            usuario: Usuário Portal
            entidade_tipo: Filtrar por tipo específico (opcional)
            portal: Filtrar por portal específico (opcional)

        Returns:
            List[PortalUsuarioAcesso]: Lista de vínculos
        """
        query = PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True)

        if entidade_tipo:
            query = query.filter(entidade_tipo=entidade_tipo)

        if portal:
            query = query.filter(portal=portal)

        return list(query)

    @classmethod
    def usuario_tem_acesso_canal(cls, usuario: PortalUsuario, canal_id: int) -> bool:
        """
        Verifica se usuário tem acesso a um canal específico

        Args:
            usuario: Usuário Portal
            canal_id: ID do canal

        Returns:
            bool: True se tem acesso, False caso contrário
        """
        # Se não tem vínculos definidos, assume acesso global (para admins)
        if not PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True).exists():
            return True

        # Verificar acesso específico ao canal
        return PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='canal',
            entidade_id=canal_id,
            ativo=True
        ).exists()

    @classmethod
    def usuario_tem_acesso_loja(cls, usuario: PortalUsuario, loja_id: int) -> bool:
        """
        Verifica se usuário tem acesso a uma loja específica

        Args:
            usuario: Usuário Portal
            loja_id: ID da loja

        Returns:
            bool: True se tem acesso, False caso contrário
        """
        # Se não tem vínculos definidos, assume acesso global (para admins)
        if not PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True).exists():
            return True

        # Verificar acesso específico à loja
        if PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='loja',
            entidade_id=loja_id,
            ativo=True
        ).exists():
            return True

        # TODO: Verificar se loja pertence a canal/regional que usuário tem acesso
        # Implementar lógica de hierarquia quando necessário

        return False

    @classmethod
    def usuario_tem_permissao_funcionalidade(cls, usuario: PortalUsuario, funcionalidade: str,
                                           canal_id: Optional[int] = None,
                                           loja_id: Optional[int] = None) -> bool:
        """
        Verifica permissão específica de funcionalidade baseada em recursos_permitidos JSON

        Args:
            usuario: Usuário Portal
            funcionalidade: Nome da funcionalidade
            canal_id: ID do canal (opcional)
            loja_id: ID da loja (opcional)

        Returns:
            bool: True se tem permissão, False caso contrário
        """
        # Buscar permissões do usuário
        permissoes = PortalPermissao.objects.filter(usuario=usuario)

        for permissao in permissoes:
            recursos = permissao.recursos_permitidos or {}
            if funcionalidade in recursos:
                return recursos[funcionalidade]

        # Se não há permissão específica, usar lógica padrão
        return True  # Por enquanto, permitir se não há restrição explícita

    @classmethod
    def obter_canais_usuario(cls, usuario: PortalUsuario) -> List[int]:
        """
        Obtém lista de IDs de canais que o usuário tem acesso

        Args:
            usuario: Usuário Portal

        Returns:
            List[int]: Lista de IDs de canais (vazia = acesso a todos)
        """
        # Se não tem vínculos definidos, retorna lista vazia (acesso global)
        if not PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True).exists():
            return []  # Lista vazia = acesso a todos os canais

        # Obter canais específicos
        vinculos = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='canal',
            ativo=True
        ).values_list('entidade_id', flat=True)

        return list(vinculos)

    @classmethod
    def obter_canal_principal_usuario(cls, usuario: PortalUsuario) -> int:
        """
        Obtém o canal principal de um usuário baseado em suas permissões

        Args:
            usuario: Usuário Portal

        Returns:
            int: ID do canal principal (1 se admin total)
        """
        # Se não tem acesso, é admin total
        acessos_count = PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True).count()

        if acessos_count == 0:
            return 1

        # Verificar acesso direto a canal
        canal_id = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='canal',
            ativo=True
        ).values_list('entidade_id', flat=True).first()

        if canal_id:
            return canal_id

        from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService

        # Verificar acesso via grupo econômico
        grupo_economico_id = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='grupo_economico',
            ativo=True
        ).values_list('entidade_id', flat=True).first()

        if grupo_economico_id:
            grupo = HierarquiaOrganizacionalService.get_grupo_economico(grupo_economico_id)
            if grupo:
                vendedor = HierarquiaOrganizacionalService.get_vendedor(grupo.vendedorId)
                if vendedor:
                    regional = HierarquiaOrganizacionalService.get_regional(vendedor.regionalId)
                    if regional:
                        return regional.canalId

        # Verificar acesso via loja
        loja_id = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='loja',
            ativo=True
        ).values_list('entidade_id', flat=True).first()

        if loja_id:
            hierarquia = HierarquiaOrganizacionalService.get_loja_hierarquia_completa(loja_id)
            if hierarquia and 'canal' in hierarquia:
                return hierarquia['canal']['id']

        # Verificar acesso via regional
        regional_id = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='regional',
            ativo=True
        ).values_list('entidade_id', flat=True).first()

        if regional_id:
            regional = HierarquiaOrganizacionalService.get_regional(regional_id)
            if regional:
                return regional.canalId

        # Verificar acesso via vendedor
        vendedor_id = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='vendedor',
            ativo=True
        ).values_list('entidade_id', flat=True).first()

        if vendedor_id:
            vendedor = HierarquiaOrganizacionalService.get_vendedor(vendedor_id)
            if vendedor:
                regional = HierarquiaOrganizacionalService.get_regional(vendedor.regionalId)
                if regional:
                    return regional.canalId

        # Se não encontrou canal específico, usa padrão 1
        return 1

    @classmethod
    def obter_lojas_usuario(cls, usuario: PortalUsuario) -> List[int]:
        """
        Obtém lista de IDs de lojas que o usuário tem acesso

        Args:
            usuario: Usuário Portal

        Returns:
            List[int]: Lista de IDs de lojas (vazia = acesso a todas)
        """
        # Se não tem vínculos definidos, retorna lista vazia (acesso global)
        if not PortalUsuarioAcesso.objects.filter(usuario=usuario, ativo=True).exists():
            return []  # Lista vazia = acesso a todas as lojas

        # Obter lojas específicas
        vinculos = PortalUsuarioAcesso.objects.filter(
            usuario=usuario,
            entidade_tipo='loja',
            ativo=True
        ).values_list('entidade_id', flat=True)

        return list(vinculos)

    @classmethod
    def criar_permissao_portal(cls, usuario: PortalUsuario, portal: str, nivel_acesso: str,
                              recursos_permitidos: Dict = None) -> PortalPermissao:
        """
        Cria ou atualiza permissão de portal para usuário

        Args:
            usuario: Usuário Portal
            portal: Nome do portal
            nivel_acesso: Nível de acesso
            recursos_permitidos: Dict com recursos permitidos

        Returns:
            PortalPermissao: Permissão criada/atualizada
        """
        if recursos_permitidos is None:
            recursos_permitidos = {}

        permissao, created = PortalPermissao.objects.update_or_create(
            usuario=usuario,
            portal=portal,
            defaults={
                'nivel_acesso': nivel_acesso,
                'recursos_permitidos': recursos_permitidos
            }
        )
        return permissao

    @classmethod
    def criar_vinculo_acesso(cls, usuario: PortalUsuario, entidade_tipo: str,
                           entidade_id: int) -> PortalUsuarioAcesso:
        """
        Cria vínculo de acesso para usuário

        Args:
            usuario: Usuário Portal
            entidade_tipo: Tipo da entidade ('loja', 'canal', etc.)
            entidade_id: ID da entidade

        Returns:
            PortalUsuarioAcesso: Vínculo criado
        """
        return PortalUsuarioAcesso.objects.create(
            usuario=usuario,
            entidade_tipo=entidade_tipo,
            entidade_id=entidade_id
        )

    @classmethod
    def obter_secoes_permitidas(cls, usuario: PortalUsuario, portal: str) -> List[str]:
        """
        Obtém lista de seções que o usuário pode acessar no portal

        Args:
            usuario: Usuário Portal
            portal: Nome do portal ('admin', 'lojista')

        Returns:
            List[str]: Lista de seções permitidas
        """
        nivel_acesso = cls.obter_nivel_portal(usuario, portal)
        return cls.SECOES_POR_NIVEL.get(nivel_acesso, [])

    @classmethod
    def usuario_pode_acessar_secao(cls, usuario: PortalUsuario, portal: str, secao: str) -> bool:
        """
        Verifica se usuário pode acessar uma seção específica

        Args:
            usuario: Usuário Portal
            portal: Nome do portal
            secao: Nome da seção

        Returns:
            bool: True se pode acessar, False caso contrário
        """
        secoes_permitidas = cls.obter_secoes_permitidas(usuario, portal)
        return secao in secoes_permitidas

    @classmethod
    def obter_resumo_permissoes(cls, usuario: PortalUsuario) -> Dict[str, Any]:
        """
        Obtém resumo completo das permissões do usuário

        Args:
            usuario: Usuário Portal

        Returns:
            Dict: Resumo das permissões
        """
        # Permissões de portais
        permissoes_portais = {}
        for permissao in PortalPermissao.objects.filter(usuario=usuario):
            secoes_permitidas = cls.obter_secoes_permitidas(usuario, permissao.portal)
            permissoes_portais[permissao.portal] = {
                'nivel_acesso': permissao.nivel_acesso,
                'recursos_permitidos': permissao.recursos_permitidos,
                'secoes_permitidas': secoes_permitidas
            }

        # Vínculos de acesso
        vinculos = cls.obter_vinculos_usuario(usuario)
        vinculos_por_tipo = {}
        for vinculo in vinculos:
            if vinculo.entidade_tipo not in vinculos_por_tipo:
                vinculos_por_tipo[vinculo.entidade_tipo] = []
            vinculos_por_tipo[vinculo.entidade_tipo].append(vinculo.entidade_id)

        return {
            'usuario': usuario.nome,
            'email': usuario.email,
            'portais': permissoes_portais,
            'vinculos': vinculos_por_tipo,
            'ativo': usuario.ativo,
            'acesso_global': not bool(vinculos)  # True se não tem vínculos (acesso total)
        }


class AutenticacaoService:
    """Service para autenticação centralizada dos portais"""

    @staticmethod
    def autenticar_usuario(email, senha, portal):
        """
        Autentica usuário para um portal específico

        Args:
            email: Email do usuário
            senha: Senha em texto plano
            portal: Portal de destino ('admin', 'lojista', 'corporativo')

        Returns:
            tuple: (usuario, sucesso, mensagem)
        """
        try:
            # Busca usuário ativo
            usuario = PortalUsuario.objects.get(
                email=email,
                ativo=True
            )

            # Verifica senha
            if not usuario.verificar_senha(senha):
                return None, False, "Credenciais inválidas"

            # Verifica se pode acessar o portal
            if not usuario.pode_acessar_portal(portal):
                return None, False, f"Usuário não tem permissão para acessar o portal {portal}"

            # Atualiza último login
            usuario.ultimo_login = datetime.now()
            usuario.save(update_fields=['ultimo_login'])

            return usuario, True, "Autenticação realizada com sucesso"

        except PortalUsuario.DoesNotExist:
            return None, False, "Usuário não encontrado"
        except Exception as e:
            return None, False, f"Erro na autenticação: {str(e)}"

    @staticmethod
    def criar_sessao_portal(request, usuario, portal):
        """Cria sessão específica do portal com chaves padronizadas"""
        if portal == 'lojista':
            # Portal lojista usa chaves específicas
            request.session['lojista_authenticated'] = True
            request.session['lojista_usuario_id'] = usuario.id
            request.session['lojista_usuario_nome'] = usuario.nome
            request.session['lojista_usuario_email'] = usuario.email
            request.session['lojista_aceite'] = usuario.aceite
        else:
            # Portais admin e recorrência usam chaves padronizadas
            request.session['portal_usuario_id'] = usuario.id
            request.session['portal_usuario_nome'] = usuario.nome
            request.session['portal_usuario_email'] = usuario.email
            request.session['portal_tipo'] = portal

        # Adiciona informações do perfil se existir
        if hasattr(usuario, 'perfil'):
            perfil = usuario.perfil
            request.session['portal_loja_id'] = perfil.loja_id
            request.session['portal_canal_id'] = perfil.canal_id
            request.session['portal_regional_id'] = perfil.regional_id

    @staticmethod
    def obter_usuario_sessao(request):
        """Obtém usuário da sessão atual baseado no portal"""
        path = request.path

        if path.startswith('/portal_lojista/'):
            # Portal lojista
            usuario_id = request.session.get('lojista_usuario_id')
        else:
            # Portal admin/recorrência
            usuario_id = request.session.get('portal_usuario_id')

        if usuario_id:
            try:
                return PortalUsuario.objects.get(id=usuario_id, ativo=True)
            except PortalUsuario.DoesNotExist:
                pass
        return None

    @staticmethod
    def limpar_sessao_portal(request):
        """Limpa sessão do portal baseado no tipo"""
        # Identificar tipo de portal pela URL ou sessão
        path = request.path

        if path.startswith('/portal_lojista/'):
            # Limpar sessão do lojista
            keys_to_remove = [
                'lojista_authenticated', 'lojista_usuario_id', 'lojista_usuario_nome',
                'lojista_usuario_email', 'lojista_aceite'
            ]
        else:
            # Limpar sessão admin/recorrência
            keys_to_remove = [
                'portal_usuario_id', 'portal_usuario_nome', 'portal_usuario_email',
                'portal_tipo', 'portal_loja_id', 'portal_canal_id', 'portal_regional_id'
            ]

        for key in keys_to_remove:
            if key in request.session:
                del request.session[key]


class PermissaoService:
    """Service para gerenciamento de permissões"""

    @staticmethod
    def usuario_tem_permissao(usuario, portal, recurso=None, nivel_minimo='leitura'):
        """
        Verifica se usuário tem permissão para acessar recurso

        Args:
            usuario: Instância do PortalUsuario
            portal: Portal ('admin', 'lojista', 'corporativo')
            recurso: Recurso específico (opcional)
            nivel_minimo: Nível mínimo necessário

        Returns:
            bool: True se tem permissão
        """
        try:
            permissao = PortalPermissao.objects.get(
                usuario=usuario,
                portal=portal
            )

            # Verifica nível de acesso
            niveis = ['leitura', 'escrita', 'admin']
            nivel_usuario = niveis.index(permissao.nivel_acesso)
            nivel_necessario = niveis.index(nivel_minimo)

            if nivel_usuario < nivel_necessario:
                return False

            # Verifica recurso específico se informado
            if recurso and permissao.recursos_permitidos:
                return recurso in permissao.recursos_permitidos

            return True

        except PortalPermissao.DoesNotExist:
            # Fallback para tipos de usuário básicos
            return usuario.pode_acessar_portal(portal)

    @staticmethod
    def criar_permissao_padrao(usuario, portal):
        """Cria permissão padrão baseada no tipo de usuário"""
        niveis_padrao = {
            'admin': 'admin',
            'admin_canal': 'admin',
            'canal': 'escrita',
            'lojista': 'escrita',
            'regional': 'leitura',
            'vendedor': 'leitura',
            'corporativo': 'leitura',
            'grupo_economico': 'escrita'
        }

        nivel = 'leitura'  # nível padrão

        permissao, created = PortalPermissao.objects.get_or_create(
            usuario=usuario,
            portal=portal,
            defaults={'nivel_acesso': nivel}
        )

        return permissao


class UsuarioService:
    """Service para gestão completa de usuários dos portais"""

    @staticmethod
    def criar_usuario(
        nome: str,
        email: str,
        acessos_selecionados: List[str],
        usuario_criador: PortalUsuario,
        tipo_portal: Optional[str] = None,
        tipo_lojista: Optional[str] = None,
        tipo_recorrencia: Optional[str] = None,
        tipo_vendas: Optional[str] = None,
        referencia_portal: Optional[str] = None,
        referencia_lojista: Optional[str] = None,
        referencia_recorrencia: Optional[str] = None,
        referencia_vendas: Optional[str] = None,
        recurso_checkout: bool = False,
        recurso_recorrencia: bool = False
    ) -> Dict[str, Any]:
        """Cria novo usuário com permissões e acessos"""
        import secrets
        import string
        from datetime import datetime, timedelta
        from wallclub_core.utilitarios.log_control import registrar_log
        from .email_service import EmailService

        try:
            # Validar se email já existe
            if PortalUsuario.objects.filter(email=email).exists():
                return {'sucesso': False, 'mensagem': 'Email já cadastrado'}

            # Validar ao menos um acesso selecionado
            if not acessos_selecionados:
                return {'sucesso': False, 'mensagem': 'Selecione ao menos um portal de acesso'}

            # Gerar senha e token
            senha_temp_string = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            token_primeiro_acesso = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

            # Criar usuário
            usuario = PortalUsuario.objects.create(
                nome=nome,
                email=email,
                senha_temporaria=True,
                email_verificado=False,
                ativo=True,
                token_primeiro_acesso=token_primeiro_acesso,
                primeiro_acesso_expira=datetime.now() + timedelta(days=7)
            )
            usuario.set_password(senha_temp_string)
            usuario.save()

            # Criar permissões de portais
            portal_destino = 'admin'
            canal_id_email = None

            # Mapear nomes do formulário para nomes do banco
            mapa_portal_db = {
                'portal': 'admin',
                'lojista': 'lojista',
                'recorrencia': 'recorrencia',
                'vendas': 'vendas'
            }

            mapa_tipos = {
                'portal': (tipo_portal, referencia_portal),
                'lojista': (tipo_lojista, referencia_lojista),
                'recorrencia': (tipo_recorrencia, referencia_recorrencia),
                'vendas': (tipo_vendas, referencia_vendas)
            }
            
            # Validar tipos que EXIGEM referência
            tipos_exigem_referencia = ['admin_canal', 'grupo_economico', 'lojista', 'vendedor', 'operador']
            
            for portal in acessos_selecionados:
                if portal in mapa_tipos:
                    tipo_acesso, referencia = mapa_tipos[portal]
                    if tipo_acesso in tipos_exigem_referencia and not referencia:
                        erros = {
                            'admin_canal': 'Admin Canal exige seleção do canal',
                            'grupo_economico': 'Grupo Econômico exige seleção do grupo',
                            'lojista': 'Lojista exige seleção da loja',
                            'vendedor': 'Vendedor exige seleção da loja',
                            'operador': 'Operador exige seleção da loja'
                        }
                        return {'sucesso': False, 'mensagem': erros.get(tipo_acesso, f'{tipo_acesso} exige referência')}

            for portal in acessos_selecionados:
                if portal in mapa_tipos:
                    tipo_acesso, referencia = mapa_tipos[portal]
                    portal_db = mapa_portal_db.get(portal, portal)

                    # Montar recursos_permitidos para portal vendas
                    recursos = {}
                    if portal == 'vendas':
                        recursos = {
                            'checkout': recurso_checkout,
                            'recorrencia': recurso_recorrencia
                        }

                    PortalPermissao.objects.create(
                        usuario=usuario,
                        portal=portal_db,
                        nivel_acesso=tipo_acesso or 'admin',
                        recursos_permitidos=recursos
                    )

                    # Criar vínculo de acesso se houver referência
                    if referencia:
                        entidade_tipo_map = {
                            'admin_total': None,
                            'admin_superusuario': None,
                            'admin_canal': 'canal',
                            'lojista_admin': None,
                            'grupo_economico': 'grupo_economico',
                            'lojista': 'loja',
                            'vendedor': 'loja',
                            'operador': 'loja'  # Portal Vendas - operador vinculado a loja
                        }

                        entidade_tipo = entidade_tipo_map.get(tipo_acesso)
                        if entidade_tipo:
                            PortalUsuarioAcesso.objects.create(
                                usuario=usuario,
                                portal=portal_db,
                                entidade_tipo=entidade_tipo,
                                entidade_id=int(referencia),
                                ativo=True
                            )

                    # Definir portal destino e canal para email
                    if portal == 'lojista':
                        portal_destino = 'lojista'

                    # Capturar canal_id de admin_canal (tanto admin quanto lojista)
                    if tipo_acesso == 'admin_canal' and referencia:
                        canal_id_email = int(referencia)

            # Se lojista sem canal definido, usar canal do criador
            if portal_destino == 'lojista' and not canal_id_email:
                canal_id_email = ControleAcessoService.obter_canal_principal_usuario(usuario_criador)

            # Enviar email de primeiro acesso
            email_enviado, mensagem_email = EmailService.enviar_email_primeiro_acesso(
                usuario, senha_temp_string, token_primeiro_acesso, canal_id_email, portal_destino
            )

            registrar_log('portais.controle_acesso', f"Usuário criado: {email} por {usuario_criador.email}")

            if email_enviado:
                return {
                    'sucesso': True,
                    'mensagem': f'Usuário criado! Email enviado para {email}',
                    'usuario': usuario
                }
            else:
                return {
                    'sucesso': True,
                    'mensagem': f'Usuário criado, mas erro no email: {mensagem_email}',
                    'usuario': usuario,
                    'senha_temporaria': senha_temp_string
                }

        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro criar usuário: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def atualizar_usuario(
        usuario_id: int,
        nome: str,
        email: str,
        acessos_selecionados: List[str],
        tipo_portal: Optional[str] = None,
        tipo_lojista: Optional[str] = None,
        tipo_recorrencia: Optional[str] = None,
        tipo_vendas: Optional[str] = None,
        referencia_portal: Optional[str] = None,
        referencia_lojista: Optional[str] = None,
        referencia_recorrencia: Optional[str] = None,
        referencia_vendas: Optional[str] = None,
        recurso_checkout: bool = False,
        recurso_recorrencia: bool = False
    ) -> Dict[str, Any]:
        """Atualiza dados e permissões do usuário"""
        from wallclub_core.utilitarios.log_control import registrar_log

        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)

            # Verificar email duplicado
            if PortalUsuario.objects.filter(email=email).exclude(id=usuario_id).exists():
                return {'sucesso': False, 'mensagem': 'Email já usado por outro usuário'}

            # Atualizar dados básicos
            usuario.nome = nome
            usuario.email = email
            usuario.save()

            # Remover permissões e acessos atuais
            PortalPermissao.objects.filter(usuario=usuario).delete()
            PortalUsuarioAcesso.objects.filter(usuario=usuario).delete()

            # Recriar permissões
            # Mapear nomes do formulário para nomes do banco
            mapa_portal_db = {
                'portal': 'admin',
                'lojista': 'lojista',
                'recorrencia': 'recorrencia',
                'vendas': 'vendas'
            }

            mapa_tipos = {
                'portal': (tipo_portal, referencia_portal),
                'lojista': (tipo_lojista, referencia_lojista),
                'recorrencia': (tipo_recorrencia, referencia_recorrencia),
                'vendas': (tipo_vendas, referencia_vendas)
            }
            
            # Validar tipos que EXIGEM referência
            tipos_exigem_referencia = ['admin_canal', 'grupo_economico', 'lojista', 'vendedor', 'operador']
            
            for portal in acessos_selecionados:
                if portal in mapa_tipos:
                    tipo_acesso, referencia = mapa_tipos[portal]
                    if tipo_acesso in tipos_exigem_referencia and not referencia:
                        erros = {
                            'admin_canal': 'Admin Canal exige seleção do canal',
                            'grupo_economico': 'Grupo Econômico exige seleção do grupo',
                            'lojista': 'Lojista exige seleção da loja',
                            'vendedor': 'Vendedor exige seleção da loja',
                            'operador': 'Operador exige seleção da loja'
                        }
                        return {'sucesso': False, 'mensagem': erros.get(tipo_acesso, f'{tipo_acesso} exige referência')}

            for portal in acessos_selecionados:
                if portal in mapa_tipos:
                    tipo_acesso, referencia = mapa_tipos[portal]
                    portal_db = mapa_portal_db.get(portal, portal)

                    # Montar recursos_permitidos para portal vendas
                    recursos = {}
                    if portal == 'vendas':
                        recursos = {
                            'checkout': recurso_checkout,
                            'recorrencia': recurso_recorrencia
                        }

                    PortalPermissao.objects.create(
                        usuario=usuario,
                        portal=portal_db,
                        nivel_acesso=tipo_acesso or 'admin',
                        recursos_permitidos=recursos
                    )

                    # Criar vínculo se houver referência
                    if referencia:
                        entidade_tipo_map = {
                            'admin_canal': 'canal',
                            'grupo_economico': 'grupo_economico',
                            'lojista': 'loja',
                            'vendedor': 'loja',
                            'operador': 'loja'  # Portal Vendas - operador vinculado a loja
                        }

                        entidade_tipo = entidade_tipo_map.get(tipo_acesso)
                        if entidade_tipo:
                            PortalUsuarioAcesso.objects.create(
                                usuario=usuario,
                                portal=portal_db,
                                entidade_tipo=entidade_tipo,
                                entidade_id=int(referencia),
                                ativo=True
                            )

            registrar_log('portais.controle_acesso', f"Usuário atualizado: ID={usuario_id} - {email}")
            return {'sucesso': True, 'mensagem': 'Usuário atualizado!', 'usuario': usuario}

        except PortalUsuario.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Usuário não encontrado'}
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro atualizar usuário: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def resetar_senha(usuario_id: int) -> Dict[str, Any]:
        """Gera nova senha temporária e envia por email"""
        import secrets
        import string
        from datetime import datetime, timedelta
        from wallclub_core.utilitarios.log_control import registrar_log
        from .email_service import EmailService

        try:
            usuario = PortalUsuario.objects.get(id=usuario_id)

            # Gerar nova senha e token
            senha_temp_string = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
            token_reset = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

            usuario.senha_temporaria = True
            usuario.token_reset_senha = token_reset
            usuario.reset_senha_expira = datetime.now() + timedelta(days=7)
            usuario.set_password(senha_temp_string)
            usuario.save()

            # Enviar email
            sucesso, mensagem = EmailService.enviar_email_reset_senha(usuario, token_reset)

            registrar_log('portais.controle_acesso', f"Reset senha: {usuario.email}")

            if sucesso:
                return {'sucesso': True, 'mensagem': f'Nova senha enviada para {usuario.email}'}
            else:
                return {'sucesso': False, 'mensagem': f'Erro ao enviar email: {mensagem}'}

        except PortalUsuario.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Usuário não encontrado'}
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro reset senha: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def remover_usuario(usuario_id: int, usuario_logado_id: int) -> Dict[str, Any]:
        """Remove usuário (não permite auto-remoção)"""
        from wallclub_core.utilitarios.log_control import registrar_log

        try:
            if usuario_id == usuario_logado_id:
                return {'sucesso': False, 'mensagem': 'Não pode remover seu próprio usuário'}

            usuario = PortalUsuario.objects.get(id=usuario_id)
            usuario.delete()

            registrar_log('portais.controle_acesso', f"Usuário removido: ID={usuario_id}")
            return {'sucesso': True, 'mensagem': 'Usuário removido!'}

        except PortalUsuario.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Usuário não encontrado'}
        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro remover usuário: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}

    @staticmethod
    def buscar_usuarios(
        usuario_logado: PortalUsuario,
        filtro_status: Optional[str] = None,
        filtro_busca: Optional[str] = None
    ) -> List[PortalUsuario]:
        """Busca usuários com filtros baseados no nível de acesso"""
        from wallclub_core.utilitarios.log_control import registrar_log

        try:
            nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')

            # Filtrar baseado no nível
            if nivel_usuario == 'admin_canal':
                # Admin canal vê apenas usuários lojistas do seu canal
                canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)

                if canais_usuario:
                    usuarios_ids = set()
                    # Usuários com acesso direto ao canal
                    usuarios_canal = PortalUsuarioAcesso.objects.filter(
                        entidade_tipo='canal',
                        entidade_id__in=canais_usuario,
                        ativo=True
                    ).values_list('usuario_id', flat=True)
                    usuarios_ids.update(usuarios_canal)

                    # Usuários com acesso a lojas do canal
                    from wallclub_core.estr_organizacional.services import HierarquiaOrganizacionalService
                    lojas_canal = HierarquiaOrganizacionalService.filtrar_lojas_por_canais(canais_usuario)
                    lojas_ids = [loja.id for loja in lojas_canal]

                    usuarios_lojas = PortalUsuarioAcesso.objects.filter(
                        entidade_tipo='loja',
                        entidade_id__in=lojas_ids,
                        ativo=True
                    ).values_list('usuario_id', flat=True)
                    usuarios_ids.update(usuarios_lojas)

                    usuarios = PortalUsuario.objects.filter(id__in=list(usuarios_ids))
                else:
                    usuarios = PortalUsuario.objects.none()

            elif nivel_usuario == 'admin_superusuario':
                # Super usuário vê apenas usuários SEM acesso ao portal admin
                usuarios_com_admin = PortalPermissao.objects.filter(
                    portal='admin'
                ).values_list('usuario_id', flat=True)
                usuarios = PortalUsuario.objects.exclude(id__in=usuarios_com_admin)

            else:
                # Admin total vê todos
                usuarios = PortalUsuario.objects.all()

            # Aplicar filtros adicionais
            if filtro_status:
                if filtro_status == 'validados':
                    usuarios = usuarios.filter(email_verificado=True, ativo=True)
                elif filtro_status == 'pendentes':
                    usuarios = usuarios.filter(email_verificado=False, ativo=True)
                elif filtro_status == 'inativos':
                    usuarios = usuarios.filter(ativo=False)

            if filtro_busca:
                usuarios = usuarios.filter(
                    Q(nome__icontains=filtro_busca) | Q(email__icontains=filtro_busca)
                )

            return list(usuarios.order_by('nome'))

        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro buscar usuários: {str(e)}", nivel='ERROR')
            return []

    @staticmethod
    def validar_token_primeiro_acesso(token: str) -> Dict[str, Any]:
        """Valida token de primeiro acesso"""
        from datetime import datetime

        try:
            usuario = PortalUsuario.objects.get(
                token_primeiro_acesso=token,
                primeiro_acesso_expira__gt=datetime.now()
            )
            return {'sucesso': True, 'usuario': usuario}
        except PortalUsuario.DoesNotExist:
            return {'sucesso': False, 'mensagem': 'Token inválido ou expirado'}

    @staticmethod
    def processar_definicao_senha(token: str, nova_senha: str, confirmacao_senha: str) -> Dict[str, Any]:
        """Processa definição de senha no primeiro acesso"""
        from wallclub_core.utilitarios.log_control import registrar_log

        try:
            # Validar senhas
            if nova_senha != confirmacao_senha:
                return {'sucesso': False, 'mensagem': 'Senhas não conferem'}

            if len(nova_senha) < 6:
                return {'sucesso': False, 'mensagem': 'Senha deve ter no mínimo 6 caracteres'}

            # Validar token
            resultado = UsuarioService.validar_token_primeiro_acesso(token)
            if not resultado['sucesso']:
                return resultado

            usuario = resultado['usuario']

            # Atualizar senha
            usuario.set_password(nova_senha)
            usuario.senha_temporaria = False
            usuario.email_verificado = True
            usuario.token_primeiro_acesso = None
            usuario.primeiro_acesso_expira = None
            usuario.save()

            registrar_log('portais.controle_acesso', f"Primeiro acesso concluído: {usuario.email}")
            return {'sucesso': True, 'mensagem': 'Senha definida com sucesso!', 'usuario': usuario}

        except Exception as e:
            registrar_log('portais.controle_acesso', f"Erro definir senha: {str(e)}", nivel='ERROR')
            return {'sucesso': False, 'mensagem': f'Erro: {str(e)}'}
