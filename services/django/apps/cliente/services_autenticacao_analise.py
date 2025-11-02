"""
Service para análise de dados de autenticação
Usado pelo engine de fraude para enriquecer análise de risco
"""
from datetime import datetime, timedelta
from django.db.models import Count, Q
from .models import Cliente
from .models_autenticacao import ClienteAutenticacao, TentativaLogin, Bloqueio
from wallclub_core.utilitarios.log_control import registrar_log


class ClienteAutenticacaoAnaliseService:
    """
    Agrega dados de autenticação do cliente para análise de risco
    """
    
    @staticmethod
    def analisar_historico_cliente(cpf, canal_id=None):
        """
        Retorna análise completa do histórico de autenticação do cliente
        
        Args:
            cpf: CPF do cliente
            canal_id: Canal (opcional, se None busca todos)
        
        Returns:
            dict: Dados estruturados para análise de risco
        """
        try:
            # Buscar cliente
            query = {'cpf': cpf}
            if canal_id:
                query['canal_id'] = canal_id
            
            try:
                cliente = Cliente.objects.get(**query)
            except Cliente.DoesNotExist:
                return {
                    'encontrado': False,
                    'cpf': cpf,
                    'mensagem': 'Cliente não encontrado'
                }
            
            # Buscar dados de autenticação
            try:
                auth = ClienteAutenticacao.objects.get(cliente=cliente)
            except ClienteAutenticacao.DoesNotExist:
                auth = None
            
            # Janelas de tempo
            agora = datetime.now()
            janela_24h = agora - timedelta(hours=24)
            janela_7d = agora - timedelta(days=7)
            janela_30d = agora - timedelta(days=30)
            
            # Análise de tentativas recentes
            historico_24h = ClienteAutenticacaoAnaliseService._analisar_tentativas_periodo(
                cliente, janela_24h, agora
            )
            
            # Análise de bloqueios
            bloqueios_recentes = ClienteAutenticacaoAnaliseService._analisar_bloqueios(
                cliente, janela_30d, agora
            )
            
            # Análise de dispositivos
            dispositivos = ClienteAutenticacaoAnaliseService._analisar_dispositivos(
                cliente, janela_7d, agora
            )
            
            # Flags de risco
            flags_risco = ClienteAutenticacaoAnaliseService._calcular_flags_risco(
                auth, historico_24h, bloqueios_recentes, dispositivos
            )
            
            resultado = {
                'encontrado': True,
                'cpf': cpf,
                'cliente_id': cliente.id,
                'canal_id': cliente.canal_id,
                'status_autenticacao': {
                    'bloqueado': auth.bloqueado if auth else False,
                    'bloqueado_ate': auth.bloqueado_ate.isoformat() if auth and auth.bloqueado_ate else None,
                    'bloqueio_motivo': auth.bloqueio_motivo if auth else None,
                    'tentativas_15min': auth.tentativas_15min if auth else 0,
                    'tentativas_1h': auth.tentativas_1h if auth else 0,
                    'tentativas_24h': auth.tentativas_24h if auth else 0,
                    'ultimo_ip': auth.ultimo_ip if auth else None,
                    'ultimo_sucesso_em': auth.ultimo_sucesso_em.isoformat() if auth and auth.ultimo_sucesso_em else None,
                    'ultima_tentativa_em': auth.ultima_tentativa_em.isoformat() if auth and auth.ultima_tentativa_em else None,
                },
                'historico_recente': historico_24h,
                'dispositivos_conhecidos': dispositivos,
                'bloqueios_historico': bloqueios_recentes,
                'flags_risco': flags_risco,
                'timestamp_consulta': agora.isoformat()
            }
            
            registrar_log(
                'apps.cliente.autenticacao_analise',
                f"Análise gerada para CPF {cpf[:3]}*** - Flags: {len(flags_risco)}",
                nivel='DEBUG'
            )
            
            return resultado
            
        except Exception as e:
            registrar_log(
                'apps.cliente.autenticacao_analise',
                f"Erro ao analisar histórico: {str(e)}",
                nivel='ERROR'
            )
            return {
                'encontrado': False,
                'cpf': cpf,
                'erro': str(e)
            }
    
    @staticmethod
    def _analisar_tentativas_periodo(cliente, data_inicio, data_fim):
        """Analisa tentativas de login em um período"""
        tentativas = TentativaLogin.objects.filter(
            cliente=cliente,
            timestamp__gte=data_inicio,
            timestamp__lte=data_fim
        )
        
        total = tentativas.count()
        sucessos = tentativas.filter(sucesso=True).count()
        falhas = tentativas.filter(sucesso=False).count()
        
        # IPs distintos
        ips_distintos = tentativas.values('ip_address').distinct().count()
        
        # Dispositivos distintos
        devices_distintos = tentativas.filter(
            device_fingerprint__isnull=False
        ).values('device_fingerprint').distinct().count()
        
        # Taxa de falha
        taxa_falha = (falhas / total) if total > 0 else 0.0
        
        return {
            'total_tentativas': total,
            'tentativas_sucesso': sucessos,
            'tentativas_falhas': falhas,
            'taxa_falha': round(taxa_falha, 3),
            'ips_distintos': ips_distintos,
            'devices_distintos': devices_distintos
        }
    
    @staticmethod
    def _analisar_bloqueios(cliente, data_inicio, data_fim):
        """Analisa histórico de bloqueios"""
        bloqueios = Bloqueio.objects.filter(
            cliente=cliente,
            bloqueado_em__gte=data_inicio,
            bloqueado_em__lte=data_fim
        ).order_by('-bloqueado_em')[:10]  # Últimos 10
        
        resultado = []
        for bloqueio in bloqueios:
            resultado.append({
                'motivo': bloqueio.motivo,
                'bloqueado_em': bloqueio.bloqueado_em.isoformat(),
                'bloqueado_ate': bloqueio.bloqueado_ate.isoformat(),
                'desbloqueado_em': bloqueio.desbloqueado_em.isoformat() if bloqueio.desbloqueado_em else None,
                'desbloqueado_por': bloqueio.desbloqueado_por,
                'ativo': bloqueio.ativo,
                'tentativas_antes': bloqueio.tentativas_antes_bloqueio
            })
        
        return resultado
    
    @staticmethod
    def _analisar_dispositivos(cliente, data_inicio, data_fim):
        """Analisa dispositivos usados"""
        # Buscar tentativas com device_fingerprint
        dispositivos_data = TentativaLogin.objects.filter(
            cliente=cliente,
            device_fingerprint__isnull=False,
            timestamp__gte=data_inicio,
            timestamp__lte=data_fim
        ).values('device_fingerprint').annotate(
            total_logins=Count('id'),
            total_sucesso=Count('id', filter=Q(sucesso=True)),
            total_falhas=Count('id', filter=Q(sucesso=False))
        )
        
        resultado = []
        for device in dispositivos_data:
            # Buscar último uso
            ultima_tentativa = TentativaLogin.objects.filter(
                cliente=cliente,
                device_fingerprint=device['device_fingerprint']
            ).order_by('-timestamp').first()
            
            # Buscar primeiro uso
            primeira_tentativa = TentativaLogin.objects.filter(
                cliente=cliente,
                device_fingerprint=device['device_fingerprint']
            ).order_by('timestamp').first()
            
            # Calcular idade do dispositivo
            if primeira_tentativa:
                dias_desde_primeiro_uso = (datetime.now() - primeira_tentativa.timestamp).days
            else:
                dias_desde_primeiro_uso = 0
            
            # Considerar confiável se: 10+ logins bem-sucedidos e idade > 7 dias
            confiavel = (
                device['total_sucesso'] >= 10 and 
                dias_desde_primeiro_uso > 7
            )
            
            resultado.append({
                'device_fingerprint': device['device_fingerprint'],
                'total_logins': device['total_logins'],
                'total_sucesso': device['total_sucesso'],
                'total_falhas': device['total_falhas'],
                'ultimo_uso': ultima_tentativa.timestamp.isoformat() if ultima_tentativa else None,
                'primeiro_uso': primeira_tentativa.timestamp.isoformat() if primeira_tentativa else None,
                'dias_desde_primeiro_uso': dias_desde_primeiro_uso,
                'confiavel': confiavel
            })
        
        return resultado
    
    @staticmethod
    def _calcular_flags_risco(auth, historico_24h, bloqueios_recentes, dispositivos):
        """Calcula flags de risco baseado nos dados"""
        flags = []
        
        # Flag: Conta bloqueada agora
        if auth and auth.bloqueado:
            flags.append('conta_bloqueada')
        
        # Flag: Bloqueio recente (últimos 7 dias)
        bloqueios_ativos = [b for b in bloqueios_recentes if b['ativo']]
        if bloqueios_ativos:
            flags.append('bloqueio_recente')
        
        # Flag: Múltiplos bloqueios (2+ em 30 dias)
        if len(bloqueios_recentes) >= 2:
            flags.append('multiplos_bloqueios')
        
        # Flag: Alta taxa de falha
        if historico_24h['taxa_falha'] >= 0.3:
            flags.append('alta_taxa_falha')
        
        # Flag: Múltiplas tentativas falhas
        if historico_24h['tentativas_falhas'] >= 5:
            flags.append('multiplas_tentativas_falhas')
        
        # Flag: Múltiplos IPs
        if historico_24h['ips_distintos'] >= 3:
            flags.append('multiplos_ips_recentes')
        
        # Flag: Múltiplos dispositivos
        if historico_24h['devices_distintos'] >= 2:
            flags.append('multiplos_devices_recentes')
        
        # Flag: Todos dispositivos são novos
        if dispositivos:
            todos_novos = all(d['dias_desde_primeiro_uso'] <= 7 for d in dispositivos)
            if todos_novos:
                flags.append('todos_devices_novos')
        
        # Flag: Nenhum dispositivo confiável
        if dispositivos:
            nenhum_confiavel = not any(d['confiavel'] for d in dispositivos)
            if nenhum_confiavel:
                flags.append('nenhum_device_confiavel')
        
        return flags
