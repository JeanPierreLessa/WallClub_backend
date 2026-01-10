# ROTEIRO: GESTÃO DE OPERADORES DE TERMINAIS

**Data:** 09/01/2026  
**Objetivo:** Criar funcionalidade de gestão de operadores no Portal Lojista  
**Responsável:** Jean Lessa

---

## 📋 CONTEXTO

### Tabelas Atuais

**1. `terminais_operadores` (73 registros)**
- Cadastro de operadores (dados pessoais)
- Campos: id, loja_id, operador, nome, cpf, identificacao_loja, matricula, telefone, email, endereco_loja

**2. `terminais_operadores_pos` (89 registros)**
- Vínculo operador-terminal (N:N)
- Campos: id, terminal_id, operador, **valido** (será renomeado para **ativo**), created_at, updated_at

**3. `terminais_operadores_log` (nova tabela)**
- Log de ativação/desativação de vínculos
- Campos: id, vinculo_id, acao (ATIVADO/DESATIVADO), usuario_id, motivo, created_at

**3. `transactiondata_pos`**
- Campo `operador_pos` registra quem fez a venda
- **NÃO MEXER NESTA TABELA**

### Melhorias Propostas

**Simplificação:**
- Remover `data_inicio` e `data_fim` de `terminais_operadores` (desnecessário)
- Renomear campo `valido` para `ativo` em `terminais_operadores_pos` (mais claro)
- Criar tabela `terminais_operadores_log` para auditoria de ativações/desativações

**Benefícios:**
- Modelagem mais simples e direta
- Histórico completo de mudanças de status
- Facilita troubleshooting e auditoria

---

## 🎯 OBJETIVO FINAL

### Funcionalidades

**Tela 1: Gestão de Operadores** (`/operadores/`)
- Listar operadores da loja
- Criar novo operador
- Editar dados do operador
- Visualizar histórico de vínculos

**Tela 2: Vínculo Operadores-Terminais** (`/operadores/vinculos/`)
- Listar terminais da loja
- Para cada terminal: mostrar operadores ativos
- Adicionar vínculo (operador → terminal)
- Ativar/Desativar vínculo (toggle ativo) - **gera log automaticamente**
- Visualizar log de ativações/desativações

---

## 📝 ROTEIRO DE EXECUÇÃO

### FASE 1: Ajustes no Banco de Dados

#### 1.1 Criar tabela de log

```sql
CREATE TABLE terminais_operadores_log (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  vinculo_id BIGINT UNSIGNED NOT NULL,
  acao ENUM('ATIVADO', 'DESATIVADO') NOT NULL,
  usuario_id INT UNSIGNED NULL,
  motivo VARCHAR(255) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  
  KEY idx_vinculo (vinculo_id),
  KEY idx_created_at (created_at),
  
  CONSTRAINT fk_log_vinculo 
    FOREIGN KEY (vinculo_id) 
    REFERENCES terminais_operadores_pos(id) 
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Validação:**
```sql
DESC terminais_operadores_log;
SHOW CREATE TABLE terminais_operadores_log;
```

---

#### 1.2 Inserir registros inativos no log

```sql
-- Inserir log para vínculos que estão inativos (valido=0)
INSERT INTO terminais_operadores_log (vinculo_id, acao, motivo, created_at)
SELECT 
  id,
  'DESATIVADO',
  'Migração: vínculo estava inativo',
  updated_at
FROM terminais_operadores_pos
WHERE valido = 0;
```

**Validação:**
```sql
-- Verificar quantos logs foram inseridos
SELECT COUNT(*) FROM terminais_operadores_log;
-- Esperado: quantidade de vínculos com valido=0

-- Verificar dados
SELECT * FROM terminais_operadores_log ORDER BY created_at DESC LIMIT 10;
```

---

#### 1.3 Renomear campo `valido` para `ativo`

```sql
-- Renomear coluna
ALTER TABLE terminais_operadores_pos
CHANGE COLUMN valido ativo TINYINT(1) NOT NULL DEFAULT 1;
```

**Validação:**
```sql
DESC terminais_operadores_pos;
-- Campo 'ativo' deve aparecer, 'valido' não

-- Verificar dados
SELECT ativo, COUNT(*) FROM terminais_operadores_pos GROUP BY ativo;
```

---

#### 1.4 Remover `data_inicio` e `data_fim` de `terminais_operadores`

```sql
-- Backup antes de dropar
CREATE TABLE terminais_operadores_backup_20260110 AS
SELECT * FROM terminais_operadores;

-- Dropar colunas
ALTER TABLE terminais_operadores
DROP COLUMN data_inicio,
DROP COLUMN data_fim;
```

**Validação:**
```sql
DESC terminais_operadores;
-- data_inicio e data_fim não devem aparecer

-- Verificar backup
SELECT COUNT(*) FROM terminais_operadores_backup_20260110;
-- Esperado: 73
```

---

#### 1.5 Adicionar Foreign Keys

```sql
-- FK para terminais
ALTER TABLE terminais_operadores_pos
ADD CONSTRAINT fk_terminal_id 
  FOREIGN KEY (terminal_id) 
  REFERENCES terminais(id) 
  ON DELETE CASCADE 
  ON UPDATE CASCADE;

-- FK para operadores
ALTER TABLE terminais_operadores_pos
ADD CONSTRAINT fk_operador_codigo 
  FOREIGN KEY (operador) 
  REFERENCES terminais_operadores(operador) 
  ON DELETE RESTRICT 
  ON UPDATE CASCADE;
```

**Validação:**
```sql
-- Verificar constraints
SELECT 
  CONSTRAINT_NAME,
  TABLE_NAME,
  COLUMN_NAME,
  REFERENCED_TABLE_NAME,
  REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'wallclub' 
  AND TABLE_NAME = 'terminais_operadores_pos'
  AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

#### 1.6 Adicionar Índices

```sql
-- Índice para queries de vínculos ativos
ALTER TABLE terminais_operadores_pos
ADD KEY idx_terminal_ativo (terminal_id, ativo);

-- Índice para busca por operador
ALTER TABLE terminais_operadores_pos
ADD KEY idx_operador_ativo (operador, ativo);
```

**Validação:**
```sql
SHOW INDEX FROM terminais_operadores_pos;
```

---

### FASE 2: Ajustar Código POS

#### 2.1 Atualizar `posp2/services.py` - método `listar_operadores_pos`

**Arquivo:** `/services/django/posp2/services.py`  
**Linha:** 814-819

**Código Atual:**
```python
cursor.execute("""
    SELECT id, operador
    FROM terminais_operadores_pos
    WHERE terminal_id = %s AND valido = 1
    ORDER BY operador
""", [terminal_id])
```

**Código Novo:**
```python
cursor.execute("""
    SELECT id, operador
    FROM terminais_operadores_pos
    WHERE terminal_id = %s AND ativo = 1
    ORDER BY operador
""", [terminal_id])
```

**Validação:**
- Testar endpoint `/api/v1/posp2/listar_operadores_pos/` em QA
- Verificar que retorna apenas operadores ativos hoje

---

### FASE 3: Criar Models Django

#### 3.1 Criar arquivo `posp2/models.py` (ou adicionar em arquivo existente)

```python
from django.db import models
from django.core.exceptions import ValidationError
from datetime import date

class TerminalOperador(models.Model):
    """
    Cadastro de operadores (dados pessoais)
    """
    loja = models.ForeignKey('cliente.Loja', on_delete=models.PROTECT, db_column='loja_id')
    operador = models.CharField(max_length=10, unique=True, help_text='Código único do operador')
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=11, db_index=True)
    identificacao_loja = models.CharField(max_length=50, blank=True, null=True)
    matricula = models.CharField(max_length=50, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=256, blank=True, null=True)
    endereco_loja = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'terminais_operadores'
        verbose_name = 'Operador de Terminal'
        verbose_name_plural = 'Operadores de Terminais'
        unique_together = [['loja', 'cpf']]
        indexes = [
            models.Index(fields=['loja']),
            models.Index(fields=['operador']),
        ]

    def __str__(self):
        return f'{self.operador} - {self.nome}'

    def vinculos_ativos(self):
        """Retorna vínculos ativos"""
        return self.vinculos.filter(ativo=True)

    def vinculos_inativos(self):
        """Retorna vínculos inativos"""
        return self.vinculos.filter(ativo=False)


class TerminalOperadorPos(models.Model):
    """
    Vínculo operador-terminal
    """
    terminal = models.ForeignKey('cliente.Terminal', on_delete=models.CASCADE, db_column='terminal_id', related_name='operadores_vinculados')
    operador = models.ForeignKey(TerminalOperador, on_delete=models.PROTECT, to_field='operador', db_column='operador', related_name='vinculos')
    ativo = models.BooleanField(default=True, help_text='Vínculo ativo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'terminais_operadores_pos'
        verbose_name = 'Vínculo Operador-Terminal'
        verbose_name_plural = 'Vínculos Operadores-Terminais'
        unique_together = [['terminal', 'operador']]
        indexes = [
            models.Index(fields=['terminal', 'ativo']),
            models.Index(fields=['operador', 'ativo']),
        ]

    def __str__(self):
        status = 'Ativo' if self.ativo else 'Inativo'
        return f'{self.operador.operador} → Terminal {self.terminal.terminal} ({status})'

    def ativar(self, usuario=None, motivo=None):
        """Ativa vínculo e registra log automaticamente"""
        if not self.ativo:
            self.ativo = True
            self.save()
            # Log gerado automaticamente pela tela de gestão
            TerminalOperadorLog.objects.create(
                vinculo=self,
                acao='ATIVADO',
                usuario_id=usuario.id if usuario else None,
                motivo=motivo or 'Ativado via portal'
            )

    def desativar(self, usuario=None, motivo=None):
        """Desativa vínculo e registra log automaticamente"""
        if self.ativo:
            self.ativo = False
            self.save()
            # Log gerado automaticamente pela tela de gestão
            TerminalOperadorLog.objects.create(
                vinculo=self,
                acao='DESATIVADO',
                usuario_id=usuario.id if usuario else None,
                motivo=motivo or 'Desativado via portal'
            )


class TerminalOperadorLog(models.Model):
    """
    Log de ativações/desativações de vínculos
    """
    vinculo = models.ForeignKey(TerminalOperadorPos, on_delete=models.CASCADE, db_column='vinculo_id', related_name='logs')
    acao = models.CharField(max_length=20, choices=[('ATIVADO', 'Ativado'), ('DESATIVADO', 'Desativado')])
    usuario_id = models.IntegerField(null=True, blank=True)
    motivo = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'terminais_operadores_log'
        verbose_name = 'Log Operador-Terminal'
        verbose_name_plural = 'Logs Operadores-Terminais'
        indexes = [
            models.Index(fields=['vinculo', 'created_at']),
        ]

    def __str__(self):
        return f'{self.acao} - {self.vinculo} em {self.created_at.strftime("%d/%m/%Y %H:%M")}'
```

**Validação:**
```python
# Testar no shell Django
python manage.py shell

from posp2.models import TerminalOperador, TerminalOperadorPos

# Listar operadores
TerminalOperador.objects.filter(loja_id=14).count()  # Esperado: 73

# Listar vínculos ativos
TerminalOperadorPos.objects.filter(ativo=True).count()
```

---

### FASE 4: Criar Views e Templates (Portal Lojista)

#### 4.1 Criar `portais/lojista/views_operadores.py`

```python
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from datetime import date
from posp2.models import TerminalOperador, TerminalOperadorPos
from cliente.models import Terminal

@login_required
def listar_operadores(request):
    """
    Tela 1: Lista operadores da loja
    """
    loja = request.user.loja
    
    # Filtros
    busca = request.GET.get('busca', '')
    status = request.GET.get('status', 'todos')  # todos, ativos, inativos
    
    operadores = TerminalOperador.objects.filter(loja=loja)
    
    if busca:
        operadores = operadores.filter(
            Q(operador__icontains=busca) |
            Q(nome__icontains=busca) |
            Q(cpf__icontains=busca)
        )
    
    # Anotar quantidade de vínculos ativos
    operadores = operadores.annotate(
        total_vinculos_ativos=Count(
            'vinculos',
            filter=Q(vinculos__ativo=True)
        )
    )
    
    if status == 'ativos':
        operadores = operadores.filter(total_vinculos_ativos__gt=0)
    elif status == 'inativos':
        operadores = operadores.filter(total_vinculos_ativos=0)
    
    operadores = operadores.order_by('nome')
    
    context = {
        'operadores': operadores,
        'busca': busca,
        'status': status,
    }
    
    return render(request, 'lojista/operadores/listar.html', context)


@login_required
def criar_operador(request):
    """
    Cria novo operador
    """
    if request.method == 'POST':
        loja = request.user.loja
        
        # Validar campos obrigatórios
        operador = request.POST.get('operador', '').strip()
        nome = request.POST.get('nome', '').strip()
        cpf = request.POST.get('cpf', '').replace('.', '').replace('-', '')
        
        if not operador or not nome or not cpf:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return redirect('lojista:criar_operador')
        
        # Verificar se operador já existe
        if TerminalOperador.objects.filter(operador=operador).exists():
            messages.error(request, f'Código de operador {operador} já existe')
            return redirect('lojista:criar_operador')
        
        # Verificar se CPF já existe na loja
        if TerminalOperador.objects.filter(loja=loja, cpf=cpf).exists():
            messages.error(request, f'CPF {cpf} já cadastrado nesta loja')
            return redirect('lojista:criar_operador')
        
        # Criar operador
        novo_operador = TerminalOperador.objects.create(
            loja=loja,
            operador=operador,
            nome=nome,
            cpf=cpf,
            identificacao_loja=request.POST.get('identificacao_loja', ''),
            matricula=request.POST.get('matricula', ''),
            telefone=request.POST.get('telefone', ''),
            email=request.POST.get('email', ''),
            endereco_loja=request.POST.get('endereco_loja', ''),
        )
        
        messages.success(request, f'Operador {novo_operador.nome} criado com sucesso')
        return redirect('lojista:listar_operadores')
    
    return render(request, 'lojista/operadores/criar.html')


@login_required
def editar_operador(request, operador_id):
    """
    Edita dados do operador
    """
    operador = get_object_or_404(TerminalOperador, id=operador_id, loja=request.user.loja)
    
    if request.method == 'POST':
        operador.nome = request.POST.get('nome', '').strip()
        operador.identificacao_loja = request.POST.get('identificacao_loja', '')
        operador.matricula = request.POST.get('matricula', '')
        operador.telefone = request.POST.get('telefone', '')
        operador.email = request.POST.get('email', '')
        operador.endereco_loja = request.POST.get('endereco_loja', '')
        operador.save()
        
        messages.success(request, f'Operador {operador.nome} atualizado com sucesso')
        return redirect('lojista:listar_operadores')
    
    context = {
        'operador': operador,
    }
    
    return render(request, 'lojista/operadores/editar.html', context)


@login_required
def visualizar_operador(request, operador_id):
    """
    Visualiza detalhes e histórico de vínculos do operador
    """
    operador = get_object_or_404(TerminalOperador, id=operador_id, loja=request.user.loja)
    
    vinculos_ativos = operador.vinculos_ativos()
    vinculos_inativos = operador.vinculos_inativos()
    
    context = {
        'operador': operador,
        'vinculos_ativos': vinculos_ativos,
        'vinculos_inativos': vinculos_inativos,
    }
    
    return render(request, 'lojista/operadores/visualizar.html', context)


@login_required
def listar_vinculos(request):
    """
    Tela 2: Lista terminais e seus operadores vinculados
    """
    loja = request.user.loja
    
    terminais = Terminal.objects.filter(loja=loja).prefetch_related(
        'operadores_vinculados__operador'
    ).order_by('terminal')
    
    # Para cada terminal, separar vínculos ativos e inativos
    terminais_data = []
    for terminal in terminais:
        vinculos_ativos = terminal.operadores_vinculados.filter(
            ativo=True
        ).select_related('operador')
        
        terminais_data.append({
            'terminal': terminal,
            'vinculos_ativos': vinculos_ativos,
        })
    
    # Operadores disponíveis para vincular (sem vínculo ativo)
    operadores_disponiveis = TerminalOperador.objects.filter(loja=loja).order_by('nome')
    
    context = {
        'terminais_data': terminais_data,
        'operadores_disponiveis': operadores_disponiveis,
    }
    
    return render(request, 'lojista/operadores/vinculos.html', context)


@login_required
def criar_vinculo(request):
    """
    Cria novo vínculo operador-terminal
    """
    if request.method == 'POST':
        loja = request.user.loja
        
        terminal_id = request.POST.get('terminal_id')
        operador_id = request.POST.get('operador_id')
        
        if not terminal_id or not operador_id:
            messages.error(request, 'Preencha todos os campos obrigatórios')
            return redirect('lojista:listar_vinculos')
        
        terminal = get_object_or_404(Terminal, id=terminal_id, loja=loja)
        operador = get_object_or_404(TerminalOperador, id=operador_id, loja=loja)
        
        # Verificar se já existe vínculo
        vinculo_existente = TerminalOperadorPos.objects.filter(
            terminal=terminal,
            operador=operador
        ).first()
        
        if vinculo_existente:
            if vinculo_existente.ativo:
                messages.error(request, f'Operador {operador.nome} já está vinculado ao terminal {terminal.terminal}')
            else:
                # Reativar vínculo existente
                vinculo_existente.ativar(usuario=request.user)
                messages.success(request, f'Vínculo reativado: {operador.nome} → Terminal {terminal.terminal}')
            return redirect('lojista:listar_vinculos')
        
        # Criar novo vínculo
        vinculo = TerminalOperadorPos.objects.create(
            terminal=terminal,
            operador=operador,
            ativo=True
        )
        
        # Log gerado automaticamente pelo método create (ativo=True por padrão)
        TerminalOperadorLog.objects.create(
            vinculo=vinculo,
            acao='ATIVADO',
            usuario_id=request.user.id,
            motivo='Vínculo criado via portal'
        )
        
        messages.success(request, f'Operador {operador.nome} vinculado ao terminal {terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    return redirect('lojista:listar_vinculos')


@login_required
def desativar_vinculo(request, vinculo_id):
    """
    Desativa vínculo
    """
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja=request.user.loja)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        vinculo.desativar(usuario=request.user, motivo=motivo)
        
        messages.success(request, f'Vínculo desativado: {vinculo.operador.nome} → Terminal {vinculo.terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    context = {
        'vinculo': vinculo,
    }
    
    return render(request, 'lojista/operadores/desativar_vinculo.html', context)


@login_required
def ativar_vinculo(request, vinculo_id):
    """
    Ativa vínculo
    """
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja=request.user.loja)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        vinculo.ativar(usuario=request.user, motivo=motivo)
        
        messages.success(request, f'Vínculo ativado: {vinculo.operador.nome} → Terminal {vinculo.terminal.terminal}')
        return redirect('lojista:listar_vinculos')
    
    return redirect('lojista:listar_vinculos')


@login_required
def visualizar_log_vinculo(request, vinculo_id):
    """
    Visualiza log de ativações/desativações do vínculo
    """
    vinculo = get_object_or_404(TerminalOperadorPos, id=vinculo_id, terminal__loja=request.user.loja)
    logs = vinculo.logs.all().order_by('-created_at')
    
    context = {
        'vinculo': vinculo,
        'logs': logs,
    }
    
    return render(request, 'lojista/operadores/log_vinculo.html', context)
```

---

#### 4.2 Adicionar URLs em `portais/lojista/urls.py`

```python
from django.urls import path
from . import views_operadores

app_name = 'lojista'

urlpatterns = [
    # ... URLs existentes ...
    
    # Operadores
    path('operadores/', views_operadores.listar_operadores, name='listar_operadores'),
    path('operadores/criar/', views_operadores.criar_operador, name='criar_operador'),
    path('operadores/<int:operador_id>/editar/', views_operadores.editar_operador, name='editar_operador'),
    path('operadores/<int:operador_id>/', views_operadores.visualizar_operador, name='visualizar_operador'),
    
    # Vínculos
    path('operadores/vinculos/', views_operadores.listar_vinculos, name='listar_vinculos'),
    path('operadores/vinculos/criar/', views_operadores.criar_vinculo, name='criar_vinculo'),
    path('operadores/vinculos/<int:vinculo_id>/desativar/', views_operadores.desativar_vinculo, name='desativar_vinculo'),
    path('operadores/vinculos/<int:vinculo_id>/ativar/', views_operadores.ativar_vinculo, name='ativar_vinculo'),
    path('operadores/vinculos/<int:vinculo_id>/log/', views_operadores.visualizar_log_vinculo, name='visualizar_log_vinculo'),
]
```

---

#### 4.3 Criar Templates

**Estrutura:**
```
portais/lojista/templates/lojista/operadores/
├── listar.html
├── criar.html
├── editar.html
├── visualizar.html
├── vinculos.html
├── desativar_vinculo.html
└── log_vinculo.html
```

*(Templates serão criados na próxima fase)*

---

### FASE 5: Testes

#### 5.1 Testes Unitários

```python
# tests/test_operadores.py
from django.test import TestCase
from datetime import date, timedelta
from posp2.models import TerminalOperador, TerminalOperadorPos
from cliente.models import Loja, Terminal

class TerminalOperadorTestCase(TestCase):
    def setUp(self):
        self.loja = Loja.objects.create(nome='Loja Teste')
        self.terminal = Terminal.objects.create(loja=self.loja, terminal='12345')
        self.operador = TerminalOperador.objects.create(
            loja=self.loja,
            operador='OP001',
            nome='João Silva',
            cpf='12345678900'
        )
    
    def test_vinculo_ativo(self):
        """Testa vínculo ativo"""
        vinculo = TerminalOperadorPos.objects.create(
            terminal=self.terminal,
            operador=self.operador,
            ativo=True
        )
        self.assertTrue(vinculo.ativo)
    
    def test_vinculo_inativo(self):
        """Testa vínculo inativo"""
        vinculo = TerminalOperadorPos.objects.create(
            terminal=self.terminal,
            operador=self.operador,
            ativo=False
        )
        self.assertFalse(vinculo.ativo)
    
    def test_desativar_vinculo(self):
        """Testa desativação de vínculo"""
        vinculo = TerminalOperadorPos.objects.create(
            terminal=self.terminal,
            operador=self.operador,
            ativo=True
        )
        vinculo.desativar(motivo='Teste')
        self.assertFalse(vinculo.ativo)
        
        # Verificar log
        log = vinculo.logs.first()
        self.assertEqual(log.acao, 'DESATIVADO')
        self.assertEqual(log.motivo, 'Teste')
    
    def test_ativar_vinculo(self):
        """Testa ativação de vínculo"""
        vinculo = TerminalOperadorPos.objects.create(
            terminal=self.terminal,
            operador=self.operador,
            ativo=False
        )
        vinculo.ativar(motivo='Reativação')
        self.assertTrue(vinculo.ativo)
        
        # Verificar log
        log = vinculo.logs.first()
        self.assertEqual(log.acao, 'ATIVADO')
        self.assertEqual(log.motivo, 'Reativação')
```

---

#### 5.2 Testes Manuais (QA)

**Checklist:**

- [ ] Listar operadores da loja
- [ ] Criar novo operador
- [ ] Editar operador existente
- [ ] Visualizar histórico de vínculos
- [ ] Listar terminais e operadores vinculados
- [ ] Criar vínculo operador-terminal
- [ ] Desativar vínculo
- [ ] Reativar vínculo
- [ ] Visualizar log de ativações/desativações
- [ ] Validar que POS lista apenas operadores ativos (ativo=1)
- [ ] Validar que transações continuam gravando `operador_pos` corretamente

---

## 📊 CRONOGRAMA ESTIMADO

| Fase | Descrição | Esforço | Responsável |
|------|-----------|---------|-------------|
| 1 | Ajustes no Banco de Dados | 1h | Jean |
| 2 | Ajustar Código POS | 0.5h | Jean |
| 3 | Criar Models Django | 2h | Jean |
| 4 | Criar Views e Templates | 6h | Jean |
| 5 | Testes | 2h | Jean |
| **TOTAL** | | **11.5h** | |

---

## ⚠️ PONTOS DE ATENÇÃO

1. **Backup obrigatório** antes de qualquer ALTER TABLE
2. **Testar em QA** antes de produção
3. **Deploy em horário de baixo movimento** (madrugada)
4. **Monitorar logs** do POS após deploy
5. **Não mexer** em `transactiondata_pos`

---

## 📝 CHECKLIST DE EXECUÇÃO

### Banco de Dados
- [ ] Backup completo do banco
- [ ] Executar FASE 1.1 (criar tabela de log)
- [ ] Executar FASE 1.2 (inserir registros inativos no log)
- [ ] Executar FASE 1.3 (renomear valido para ativo)
- [ ] Executar FASE 1.4 (remover data_inicio/data_fim de terminais_operadores)
- [ ] Executar FASE 1.5 (adicionar FKs)
- [ ] Executar FASE 1.6 (adicionar índices)

### Código
- [ ] Ajustar `listar_operadores_pos` (FASE 2)
- [ ] Criar models (FASE 3)
- [ ] Criar views (FASE 4.1)
- [ ] Adicionar URLs (FASE 4.2)
- [ ] Criar templates (FASE 4.3)

### Testes
- [ ] Testes unitários (FASE 5.1)
- [ ] Testes manuais em QA (FASE 5.2)
- [ ] Validar POS em QA
- [ ] Deploy em produção
- [ ] Monitorar logs (24h)

---

**Status:** 📋 Planejamento  
**Próximo Passo:** Executar FASE 1 (Ajustes no Banco de Dados)  
**Data Prevista Início:** A definir
