# SEGURANÇA, RISCO E ANTIFRAUDE - WALLCLUB

**Versão:** 1.0  
**Data:** 2025-10-15  
**Status:** 🟡 EM ANÁLISE  
**Prioridade:** P0 - CRÍTICA (pré-requisito para operação)

---

## VISÃO GERAL

Sistema antifraude leve e evolutivo para gateway de pagamentos com:
- **Volume:** ~2.000 transações/mês (~R$ 1 milhão)
- **Custo-alvo:** R$ 70-120/mês (Fase 1) → R$ 200-600/mês (Fase 2 opcional)
- **Taxa de fraude:** < 0,2%
- **Taxa de aprovação:** 95-98%
- **Latência:** < 200ms por decisão

---

## ARQUITETURA DO SISTEMA

```
┌─────────────────────────────────────────────────────────┐
│  TRANSAÇÃO (POS, App Mobile, Checkout Web)             │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  MÓDULO ANTIFRAUDE (Container Separado)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Coleta     │→ │   Score      │→ │   Engine     │  │
│  │   de Dados   │  │  (MaxMind)   │  │  de Decisão  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                            ▼                            │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Decisão: APROVAR | NEGAR | REVISAR | 3DS      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│  PAINEL DE REVISÃO MANUAL (casos suspeitos)            │
└─────────────────────────────────────────────────────────┘
```

---

## FASE 1: SISTEMA BASE (6-8 semanas)

### Objetivo:
Implementar sistema antifraude mínimo viável para iniciar operação segura.

---

### 1.1. Coleta e Normalização de Dados (1 semana)

**Implementar:**

#### Model: `TransacaoRisco`
```python
# antifraude/models.py
class TransacaoRisco(models.Model):
    # Identificação
    transacao_id = models.CharField(max_length=100, unique=True)
    tipo_transacao = models.CharField(max_length=20)  # POS, APP, WEB
    
    # Dados financeiros
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    metodo_pagamento = models.CharField(max_length=20)
    parcelas = models.IntegerField(default=1)
    
    # Identificação cliente/terminal
    cpf_cnpj = models.CharField(max_length=14, db_index=True)
    terminal_id = models.CharField(max_length=50, null=True)
    device_id = models.CharField(max_length=100, null=True)
    
    # Dados de contexto
    ip_address = models.GenericIPAddressField(null=True)
    user_agent = models.TextField(null=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True)
    
    # BIN do cartão (primeiros 6 dígitos)
    card_bin = models.CharField(max_length=6, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'antifraude_transacao_risco'
        indexes = [
            models.Index(fields=['cpf_cnpj', 'created_at']),
            models.Index(fields=['ip_address', 'created_at']),
            models.Index(fields=['card_bin']),
        ]
```

#### Service: Normalização
```python
# antifraude/services/coleta_service.py
class ColetaDadosService:
    @staticmethod
    def normalizar_transacao(dados_brutos):
        """Normaliza dados de diferentes origens (POS/APP/WEB)"""
        return {
            'transacao_id': dados_brutos.get('nsu') or dados_brutos.get('transaction_id'),
            'valor': Decimal(dados_brutos['valor']),
            'cpf_cnpj': re.sub(r'\D', '', dados_brutos['cpf_cnpj']),
            'ip_address': dados_brutos.get('ip') or request.META.get('REMOTE_ADDR'),
            'device_id': dados_brutos.get('device_fingerprint'),
            'terminal_id': dados_brutos.get('terminal'),
            # ... outros campos
        }
    
    @staticmethod
    def extrair_card_bin(numero_cartao):
        """Extrai BIN (primeiros 6 dígitos) do cartão"""
        return numero_cartao[:6] if numero_cartao else None
```

**Entregável:** Dados normalizados e armazenados

---

### 1.2. Integração MaxMind minFraud Score (1 semana)

**API:** MaxMind minFraud Score  
**Custo:** US$ 0,005/consulta (~R$ 55/mês para 2k transações)

#### Service: MaxMind
```python
# antifraude/services/maxmind_service.py
import minfraud
from django.core.cache import cache

class MaxMindService:
    def __init__(self):
        self.client = minfraud.Client(
            account_id=settings.MAXMIND_ACCOUNT_ID,
            license_key=settings.MAXMIND_LICENSE_KEY
        )
    
    def calcular_score(self, transacao_data):
        """Consulta score de risco no MaxMind"""
        cache_key = f"maxmind_score_{transacao_data['ip_address']}_{transacao_data['cpf_cnpj']}"
        
        # Cache de 1 hora para mesmo IP+CPF
        score_cached = cache.get(cache_key)
        if score_cached:
            return score_cached
        
        try:
            request = {
                'device': {
                    'ip_address': transacao_data['ip_address'],
                    'user_agent': transacao_data.get('user_agent'),
                },
                'billing': {
                    'address': transacao_data.get('address'),
                    'postal': transacao_data.get('postal_code'),
                },
                'payment': {
                    'processor': 'wallclub',
                },
                'order': {
                    'amount': float(transacao_data['valor']),
                    'currency': 'BRL',
                }
            }
            
            response = self.client.score(request)
            score_data = {
                'risk_score': response.risk_score,  # 0-100
                'ip_risk': response.ip_address.risk,
                'country': response.ip_address.country.iso_code,
                'warnings': [w.code for w in response.warnings],
            }
            
            cache.set(cache_key, score_data, timeout=3600)
            return score_data
            
        except Exception as e:
            logger.error(f"Erro MaxMind: {e}")
            return {'risk_score': 50, 'error': str(e)}  # Score neutro em caso de erro
```

**Entregável:** Score de risco funcional com cache

---

### 1.3. Engine de Decisão Parametrizado (2 semanas)

#### Model: Regras Parametrizadas
```python
# antifraude/models.py
class RegraAntifraude(models.Model):
    TIPO_REGRA = [
        ('limite_valor', 'Limite de Valor'),
        ('velocidade', 'Velocidade de Transações'),
        ('blacklist', 'Blacklist'),
        ('whitelist', 'Whitelist'),
        ('score_threshold', 'Limiar de Score'),
        ('geo_bloqueio', 'Bloqueio Geográfico'),
    ]
    
    ACAO = [
        ('aprovar', 'Aprovar'),
        ('negar', 'Negar'),
        ('revisar', 'Revisar Manualmente'),
        ('3ds', 'Solicitar 3D Secure'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_REGRA)
    descricao = models.TextField()
    parametros = models.JSONField()  # Configuração flexível
    acao = models.CharField(max_length=20, choices=ACAO)
    prioridade = models.IntegerField(default=50)  # 0-100, maior = mais prioritário
    ativo = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'antifraude_regra'
        ordering = ['-prioridade', 'id']

# Exemplos de regras no banco:
REGRAS_INICIAIS = [
    {
        'nome': 'Valor Alto com Score Alto',
        'tipo': 'score_threshold',
        'parametros': {'valor_min': 2000, 'score_min': 70},
        'acao': 'revisar',
        'prioridade': 90,
    },
    {
        'nome': 'Velocidade Suspeita - Mesmo CPF',
        'tipo': 'velocidade',
        'parametros': {'max_transacoes': 3, 'janela_minutos': 60},
        'acao': 'negar',
        'prioridade': 95,
    },
    {
        'nome': 'Whitelist Clientes Confiáveis',
        'tipo': 'whitelist',
        'parametros': {'min_transacoes_ok': 10, 'max_chargebacks': 0},
        'acao': 'aprovar',
        'prioridade': 100,
    },
]
```

#### Model: Decisão
```python
class DecisaoAntifraude(models.Model):
    transacao_risco = models.OneToOneField(TransacaoRisco, on_delete=models.CASCADE)
    
    # Score e contexto
    score_maxmind = models.FloatField()
    score_ajustado = models.FloatField()  # Score final após regras locais
    
    # Decisão
    decisao = models.CharField(max_length=20, choices=[
        ('aprovado', 'Aprovado'),
        ('negado', 'Negado'),
        ('revisar', 'Revisar'),
        ('3ds_required', '3DS Obrigatório'),
    ])
    
    # Rastreabilidade
    regras_aplicadas = models.JSONField()  # Lista de regras que dispararam
    motivo = models.TextField()
    
    # Review manual
    revisado_por = models.ForeignKey('auth.User', null=True, on_delete=models.SET_NULL)
    revisado_em = models.DateTimeField(null=True)
    decisao_final = models.CharField(max_length=20, null=True)
    comentario_revisor = models.TextField(null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    latencia_ms = models.IntegerField()  # Tempo de processamento
    
    class Meta:
        db_table = 'antifraude_decisao'
```

#### Service: Engine de Decisão
```python
# antifraude/services/engine_service.py
class EngineAntifraude:
    def __init__(self):
        self.maxmind_service = MaxMindService()
    
    def analisar_transacao(self, transacao_data):
        """Pipeline completo de análise"""
        inicio = time.time()
        
        # 1. Criar registro de risco
        transacao_risco = TransacaoRisco.objects.create(**transacao_data)
        
        # 2. Calcular score MaxMind
        score_maxmind = self.maxmind_service.calcular_score(transacao_data)
        
        # 3. Aplicar regras locais
        decisao_info = self._aplicar_regras(transacao_risco, score_maxmind)
        
        # 4. Registrar decisão
        latencia = int((time.time() - inicio) * 1000)
        decisao = DecisaoAntifraude.objects.create(
            transacao_risco=transacao_risco,
            score_maxmind=score_maxmind['risk_score'],
            score_ajustado=decisao_info['score_ajustado'],
            decisao=decisao_info['decisao'],
            regras_aplicadas=decisao_info['regras'],
            motivo=decisao_info['motivo'],
            latencia_ms=latencia,
        )
        
        logger.info(f"Transação {transacao_risco.transacao_id}: {decisao.decisao} ({latencia}ms)")
        
        return {
            'decisao': decisao.decisao,
            'score': decisao.score_ajustado,
            'motivo': decisao.motivo,
            'latencia_ms': latencia,
        }
    
    def _aplicar_regras(self, transacao, score_maxmind):
        """Aplica regras ordenadas por prioridade"""
        regras = RegraAntifraude.objects.filter(ativo=True)
        score_ajustado = score_maxmind['risk_score']
        regras_disparadas = []
        
        for regra in regras:
            disparou, ajuste_score = self._avaliar_regra(regra, transacao, score_ajustado)
            
            if disparou:
                regras_disparadas.append({
                    'regra_id': regra.id,
                    'nome': regra.nome,
                    'acao': regra.acao,
                })
                
                score_ajustado += ajuste_score
                
                # Regra de prioridade alta encerra análise
                if regra.prioridade >= 90:
                    return {
                        'decisao': regra.acao,
                        'score_ajustado': score_ajustado,
                        'regras': regras_disparadas,
                        'motivo': f"Regra prioritária: {regra.nome}",
                    }
        
        # Decisão baseada em score final
        decisao_final = self._decisao_por_score(score_ajustado)
        
        return {
            'decisao': decisao_final,
            'score_ajustado': score_ajustado,
            'regras': regras_disparadas,
            'motivo': f"Score ajustado: {score_ajustado:.1f}",
        }
    
    def _avaliar_regra(self, regra, transacao, score_atual):
        """Avalia uma regra específica"""
        params = regra.parametros
        
        if regra.tipo == 'limite_valor':
            if transacao.valor > params['valor_min'] and score_atual > params.get('score_min', 0):
                return True, 10  # Aumenta score em 10
        
        elif regra.tipo == 'velocidade':
            count = self._contar_transacoes_recentes(
                transacao.cpf_cnpj, 
                params['janela_minutos']
            )
            if count >= params['max_transacoes']:
                return True, 30  # Aumenta muito o score
        
        elif regra.tipo == 'whitelist':
            if self._cliente_confiavel(transacao.cpf_cnpj, params):
                return True, -20  # REDUZ score (confiável)
        
        elif regra.tipo == 'blacklist':
            if self._cliente_bloqueado(transacao.cpf_cnpj):
                return True, 50  # Aumenta muito o score
        
        return False, 0
    
    def _decisao_por_score(self, score):
        """Mapeia score em decisão"""
        if score <= 30:
            return 'aprovado'
        elif score <= 60:
            return '3ds_required'
        elif score <= 85:
            return 'revisar'
        else:
            return 'negado'
    
    def _contar_transacoes_recentes(self, cpf_cnpj, minutos):
        """Conta transações do CPF nos últimos X minutos"""
        limite = timezone.now() - timedelta(minutes=minutos)
        return TransacaoRisco.objects.filter(
            cpf_cnpj=cpf_cnpj,
            created_at__gte=limite
        ).count()
    
    def _cliente_confiavel(self, cpf_cnpj, params):
        """Verifica se cliente está em whitelist automática"""
        # Cliente com 10+ transações OK e 0 chargebacks
        stats = self._obter_estatisticas_cliente(cpf_cnpj)
        return (
            stats['total_aprovado'] >= params['min_transacoes_ok'] and
            stats['total_chargeback'] <= params['max_chargebacks']
        )
    
    def _cliente_bloqueado(self, cpf_cnpj):
        """Verifica blacklist"""
        return Blacklist.objects.filter(cpf_cnpj=cpf_cnpj, ativo=True).exists()
```

**Entregável:** Engine funcional com regras parametrizadas

---

### 1.4. Blacklist e Whitelist (3 dias)

```python
# antifraude/models.py
class Blacklist(models.Model):
    cpf_cnpj = models.CharField(max_length=14, unique=True)
    motivo = models.TextField()
    adicionado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'antifraude_blacklist'

class WhitelistManual(models.Model):
    """Whitelist manual para casos especiais"""
    cpf_cnpj = models.CharField(max_length=14, unique=True)
    motivo = models.TextField()
    valido_ate = models.DateTimeField(null=True)
    adicionado_por = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'antifraude_whitelist_manual'
```

---

### 1.5. Painel de Revisão Manual (1 semana)

#### View Django Admin Customizado
```python
# antifraude/admin.py
@admin.register(DecisaoAntifraude)
class DecisaoAntifraudeAdmin(admin.ModelAdmin):
    list_display = ['transacao_id', 'cpf_cnpj', 'valor', 'decisao', 'score_ajustado', 'created_at']
    list_filter = ['decisao', 'created_at']
    search_fields = ['transacao_risco__cpf_cnpj', 'transacao_risco__transacao_id']
    
    def transacao_id(self, obj):
        return obj.transacao_risco.transacao_id
    
    def cpf_cnpj(self, obj):
        return obj.transacao_risco.cpf_cnpj
    
    def valor(self, obj):
        return f"R$ {obj.transacao_risco.valor:,.2f}"
    
    # Ações em lote
    actions = ['aprovar_selecionadas', 'negar_selecionadas', 'adicionar_blacklist']
    
    def aprovar_selecionadas(self, request, queryset):
        queryset.update(
            decisao_final='aprovado',
            revisado_por=request.user,
            revisado_em=timezone.now()
        )
    
    def adicionar_blacklist(self, request, queryset):
        for decisao in queryset:
            Blacklist.objects.get_or_create(
                cpf_cnpj=decisao.transacao_risco.cpf_cnpj,
                defaults={'motivo': 'Adicionado via revisão manual', 'adicionado_por': request.user}
            )
```

**Entregável:** Painel funcional para revisão

---

### 1.6. Integração 3D Secure (1 semana)

**Implementação via gateway existente (Getnet, Adyen, etc)**

```python
# antifraude/services/auth3ds_service.py
class Auth3DSService:
    def solicitar_3ds(self, transacao_data):
        """Solicita autenticação 3D Secure"""
        # Integração específica com seu gateway
        # Getnet/Adyen já incluem 3DS nativo
        
        return {
            'requires_3ds': True,
            'redirect_url': gateway_response['authentication_url'],
            'session_id': gateway_response['session_id'],
        }
    
    def validar_3ds(self, session_id, authentication_result):
        """Valida resultado do 3DS"""
        # Processa retorno do gateway
        if authentication_result == 'success':
            return {'approved': True}
        return {'approved': False, 'reason': 'Falha na autenticação'}
```

---

### 1.7. API de Antifraude (3 dias)

```python
# antifraude/urls.py
urlpatterns = [
    path('api/analyze/', AnalisarTransacaoView.as_view()),
    path('api/decision/<transacao_id>/', ConsultarDecisaoView.as_view()),
]

# antifraude/views.py
class AnalisarTransacaoView(APIView):
    """
    POST /api/antifraude/analyze/
    
    Request:
    {
        "transacao_id": "NSU123456",
        "valor": 1500.00,
        "cpf_cnpj": "12345678901",
        "terminal_id": "POS001",
        "ip_address": "192.168.1.1",
        ...
    }
    
    Response:
    {
        "decisao": "aprovado|negado|revisar|3ds_required",
        "score": 45.5,
        "motivo": "Score ajustado: 45.5",
        "latencia_ms": 150
    }
    """
    def post(self, request):
        try:
            dados = ColetaDadosService.normalizar_transacao(request.data)
            engine = EngineAntifraude()
            resultado = engine.analisar_transacao(dados)
            
            return Response(resultado, status=200)
            
        except Exception as e:
            logger.error(f"Erro na análise: {e}")
            return Response({
                'decisao': 'revisar',
                'motivo': 'Erro no processamento',
                'error': str(e)
            }, status=500)
```

**Entregável:** API REST funcional

---

## FASE 2: KYC E VALIDAÇÕES (2 semanas - OPCIONAL)

### 2.1. Validação CPF Forte (já planejado no plano mestre)
- API Serpro
- ValidadorCPFService

### 2.2. KYC Sob Demanda (1 semana)
- Integração Idwall/Acesso Digital
- Apenas para transações > R$ 2.000
- Custo: ~R$ 2/validação

---

## FASE 3: MACHINE LEARNING (6+ meses - FUTURO)

### Quando considerar:
- ✅ Após 6 meses de histórico (mínimo 10k transações)
- ✅ Se taxa de fraude > 0,5%
- ✅ Se review manual consome > 10h/semana

### Opções:
1. **Konduto** (R$ 200-600/mês) - ML automático
2. **ClearSale** (1-3% transação) - ML + analistas humanos
3. **ML Próprio** - Scikit-learn/TensorFlow com histórico

---

## CRONOGRAMA FASE 1

| Semana | Atividade | Entregável |
|--------|-----------|------------|
| 1 | Coleta de dados + Models | TransacaoRisco criada |
| 2 | Integração MaxMind | Score funcional |
| 3-4 | Engine de decisão | Regras parametrizadas |
| 5 | Blacklist/Whitelist | Listas funcionais |
| 6 | Painel de revisão | Admin customizado |
| 7 | Integração 3DS | 3DS via gateway |
| 8 | API + Testes | Sistema completo |

**Total:** 6-8 semanas

---

## CUSTOS MENSAIS

### Fase 1 (Básico):
- MaxMind minFraud Score: R$ 55/mês
- FingerprintJS (grátis): R$ 0
- 3DS via gateway (incluso): R$ 0
- KYC esporádico: R$ 10-20/mês
- **TOTAL: R$ 70-120/mês**

### Fase 2 (Com KYC):
- Mesmos custos Fase 1
- KYC frequente: R$ 100-200/mês
- **TOTAL: R$ 170-320/mês**

### Fase 3 (Com ML):
- Konduto: R$ 200-600/mês
- OU ClearSale: R$ 10-30k/mês (não recomendado)
- **TOTAL: R$ 200-600/mês**

---

## MÉTRICAS DE SUCESSO

### KPIs Principais:
- ✅ **Taxa de fraude:** < 0,2%
- ✅ **Taxa de aprovação:** 95-98%
- ✅ **Latência:** < 200ms (p95)
- ✅ **Falsos positivos:** < 5%

### KPIs Secundários:
- Tempo médio de revisão manual: < 2 min/caso
- Chargebacks: < 0,1% do volume
- Cobertura de regras: 100% das transações analisadas

---

## INTEGRAÇÃO COM OUTROS MÓDULOS

### Com APIs Mobile:
```python
# modulos/apis_mobile/checkout/views.py
resultado_fraude = requests.post(
    'http://wallclub-riskengine:8004/api/analyze/',
    json=dados_transacao
).json()

if resultado_fraude['decisao'] == 'negado':
    return Response({'error': 'Transação negada por segurança'}, status=403)
```

### Com POS Terminal:
```python
# modulos/pos_terminal/posp2/views.py
# Análise síncrona (tempo real)
engine = EngineAntifraude()
resultado = engine.analisar_transacao(dados_pos)
```

---

## RISCOS E MITIGAÇÕES

| Risco | Probabilidade | Mitigação |
|-------|---------------|-----------|
| Falsos positivos altos | Média | Ajuste semanal de regras, whitelist automática |
| MaxMind indisponível | Baixa | Fallback para score neutro (50), aprovar com log |
| Latência > 200ms | Média | Cache agressivo, timeout de 5s |
| Review manual lento | Alta | Alertas automáticos, priorização por valor |

---

## DECISÕES PENDENTES

- [ ] Contratar MaxMind minFraud? (R$ 55/mês)
- [ ] Implementar KYC desde o início ou sob demanda?
- [ ] Limiar inicial de score (30/60/85)?
- [ ] Ativar 3DS para todos ou só risco médio?
- [ ] Integração com Konduto em 6 meses?

---

**Próximo passo:** Revisar e aprovar este plano antes de iniciar implementação.
