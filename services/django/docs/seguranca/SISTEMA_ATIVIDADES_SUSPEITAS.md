# SISTEMA DE ATIVIDADES SUSPEITAS E BLOQUEIOS
## Risk Engine + Portal Admin

**Versão:** 1.0  
**Data:** 18/10/2025  
**Fase:** 4 - Semana 23

---

## 📋 VISÃO GERAL

Sistema centralizado no Risk Engine que:
- Detecta automaticamente comportamentos suspeitos de login
- Permite bloqueios manuais de IP/CPF
- Integra com Portal Admin para gestão visual

---

## 🏗️ ARQUITETURA

```
PORTAIS (8003)          RISK ENGINE (8004)
┌─────────────┐         ┌──────────────────────┐
│ Middleware  │───────→ │ validate-login API   │
│   Login     │ POST    │ Verifica bloqueios   │
└─────────────┘         └──────────────────────┘
                                 │
┌─────────────┐         ┌───────▼──────────────┐
│Portal Admin │←────────│ suspicious API       │
│   Views     │ GET     │ Lista atividades     │
└─────────────┘         └──────────────────────┘
                                 │
                        ┌────────▼─────────────┐
                        │ Detector Automático  │
                        │ (Celery - 5 em 5 min)│
                        │ Analisa logs         │
                        └──────────────────────┘
```

---

## 📦 MODELS (Risk Engine)

### BloqueioSeguranca
```python
class BloqueioSeguranca(models.Model):
    tipo = CharField(choices=['ip', 'cpf'])
    valor = CharField(max_length=50, db_index=True)
    motivo = TextField()
    bloqueado_por = CharField(max_length=100)
    bloqueado_em = DateTimeField()
    ativo = BooleanField(default=True)
```

### AtividadeSuspeita
```python
class AtividadeSuspeita(models.Model):
    TIPO_CHOICES = [
        ('login_multiplo', 'Múltiplos Logins'),
        ('tentativas_falhas', 'Tentativas Falhas'),
        ('ip_novo', 'IP Novo'),
        ('horario_suspeito', 'Horário Suspeito'),
    ]
    
    tipo = CharField(max_length=30)
    cpf = CharField(max_length=11)
    ip = CharField(max_length=45)
    portal = CharField(max_length=50)
    detalhes = JSONField()  # {"ips": [...], "intervalo_segundos": 120}
    detectado_em = DateTimeField()
    status = CharField(default='pendente')  # pendente/investigado/bloqueado
```

---

## 🔌 APIs (Risk Engine)

### 1. POST /api/antifraude/validate-login/
**Request:**
```json
{"ip": "192.168.1.100", "cpf": "12345678901", "portal": "vendas"}
```

**Response (Bloqueado):**
```json
{"permitido": false, "bloqueado": true, "tipo": "ip", "motivo": "..."}
```

### 2. GET /api/antifraude/suspicious/
Lista atividades com filtros (status, tipo, portal, período)

### 3. POST /api/antifraude/block/
Cria bloqueio manual

### 4. POST /api/antifraude/investigate/
Ações: marcar_investigado, bloquear_ip, bloquear_cpf, falso_positivo

---

## 🤖 DETECTOR AUTOMÁTICO

**Celery task (5 em 5 min):**
1. Lê `/app/logs/auditoria.login.log`
2. Analisa últimos 5 minutos
3. Aplica regras de detecção:

**REGRA 1:** Tentativas falhas > 5x em 5min → cria alerta
**REGRA 2:** Login de múltiplos IPs < 5min → cria alerta
**REGRA 3:** Login 00h-06h → cria alerta

---

## 🔒 MIDDLEWARE (Django)

```python
# comum/middleware/security_middleware.py

def process_request(request):
    if 'login' in request.path and request.method == 'POST':
        ip = get_client_ip(request)
        cpf = request.POST.get('cpf')
        
        # Consultar Risk Engine
        response = requests.post(
            'http://wallclub-riskengine:8004/api/antifraude/validate-login/',
            json={'ip': ip, 'cpf': cpf, 'portal': get_portal(request)}
        )
        
        if not response.json().get('permitido'):
            return HttpResponseForbidden("Acesso bloqueado")
```

---

## 🖥️ PORTAL ADMIN - TELAS

### 1. `/admin/seguranca/atividades-suspeitas/`

```
┌─────────────────────────────────────────────┐
│ ATIVIDADES SUSPEITAS                        │
├─────────────────────────────────────────────┤
│ Cards:  [12 Pendentes] [45 Total (24h)]    │
│         [8 Investigados] [3 Bloqueados]     │
│                                             │
│ Filtros: [Status▼] [Tipo▼] [Portal▼]       │
│                                             │
│ Tabela:                                     │
│ ┌────────┬──────────┬────────┬────────┐   │
│ │Data    │Tipo      │CPF     │Ações   │   │
│ ├────────┼──────────┼────────┼────────┤   │
│ │18/10   │Login     │123...  │[Ver]   │   │
│ │08:45   │Múltiplo  │        │        │   │
│ └────────┴──────────┴────────┴────────┘   │
└─────────────────────────────────────────────┘
```

**Modal [Ver]:**
```
┌─────────────────────────────────┐
│ Detalhes                        │
├─────────────────────────────────┤
│ Tipo: Login Múltiplos IPs       │
│ CPF: 123.456.789-01             │
│ IPs: 192.168.1.100, 10.0.0.50   │
│ Intervalo: 2 minutos            │
│                                 │
│ Ações:                          │
│ [Investigado] [Bloquear IP]     │
│ [Bloquear CPF] [Falso Positivo] │
└─────────────────────────────────┘
```

### 2. `/admin/seguranca/bloqueios/`

```
┌─────────────────────────────────────────┐
│ BLOQUEIOS ATIVOS                        │
├─────────────────────────────────────────┤
│ [+ Novo Bloqueio]                       │
│                                         │
│ Tabela:                                 │
│ ┌──────┬──────────────┬────────────┐   │
│ │Tipo  │Valor         │Bloqueado   │   │
│ ├──────┼──────────────┼────────────┤   │
│ │IP    │192.168.1.100 │18/10 09:00 │   │
│ │CPF   │12345678901   │18/10 08:30 │   │
│ └──────┴──────────────┴────────────┘   │
└─────────────────────────────────────────┘
```

---

## 📁 ESTRUTURA DE ARQUIVOS

### Risk Engine (8004):
```
antifraude/
├── models.py               # +BloqueioSeguranca, +AtividadeSuspeita
├── views_api.py            # +4 APIs
├── tasks.py                # Detector automático (Celery)
└── migrations/             # Nova migration
```

### Django (8003):
```
comum/middleware/
└── security_middleware.py  # Middleware validação login

portais/admin/
├── views_seguranca.py      # Views atividades + bloqueios
├── templates/admin/seguranca/
│   ├── atividades_suspeitas.html
│   └── bloqueios.html
└── urls.py                 # Rotas /admin/seguranca/
```

---

## ⏱️ ESTIMATIVA

| Item | Tempo |
|------|-------|
| Risk Engine: Models + APIs | 4h |
| Risk Engine: Detector Celery | 3h |
| Django: Middleware | 2h |
| Django: Views + Templates | 3h |
| **TOTAL** | **12h** |

---

## 🚀 DEPLOY

1. Risk Engine: Aplicar migrations
2. Django: Ativar middleware
3. Configurar Celery Beat
4. Testar fluxo completo

---

## 📊 MÉTRICAS DE SUCESSO

- ✅ Bloqueios automáticos funcionando
- ✅ Detecção < 5 minutos após evento
- ✅ Interface admin funcional
- ✅ 0 falsos positivos em 1 semana
