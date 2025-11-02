/**
 * Portal Lojista - Funções JavaScript Comuns
 * Centraliza funções utilizadas em múltiplos templates
 */

// Função para voltar à tela anterior
function voltarTela() {
    window.history.back();
}

// Função para navegação de páginas (paginação)
function navegarPagina(pagina) {
    const form = document.getElementById('filtroForm');
    if (!form) return;
    
    // Criar input hidden para página se não existir
    let paginaInput = form.querySelector('input[name="pagina"]');
    if (!paginaInput) {
        paginaInput = document.createElement('input');
        paginaInput.type = 'hidden';
        paginaInput.name = 'pagina';
        form.appendChild(paginaInput);
    }
    
    paginaInput.value = pagina;
    
    // Submeter formulário via AJAX
    buscarDados();
}

// Função para mostrar loading
function mostrarLoading(containerId = 'resultados') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="loading">
                <i class="fas fa-spinner fa-spin"></i>
                <p>Carregando dados...</p>
            </div>
        `;
    }
}

// Função para mostrar erro
function mostrarErro(mensagem, containerId = 'resultados') {
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML = `
            <div class="alert alert-danger">
                <i class="fas fa-exclamation-triangle me-2"></i>
                ${mensagem}
            </div>
        `;
    }
}

// Função para formatar moeda brasileira
function formatarMoeda(valor) {
    if (!valor || valor === '') return '0,00';
    return parseFloat(valor).toFixed(2).replace('.', ',');
}

// Função para obter badge de status de pagamento
function getStatusBadge(status) {
    if (!status) return 'bg-secondary';
    const s = status.toLowerCase();
    if (s.includes('pago') || s.includes('aprovado')) return 'bg-success';
    if (s.includes('pendente') || s.includes('aguardando')) return 'bg-warning';
    if (s.includes('cancelado') || s.includes('negado')) return 'bg-danger';
    return 'bg-info';
}

// Função para obter badge de status de transação
function getTransBadge(status) {
    if (!status) return 'bg-secondary';
    const s = status.toLowerCase();
    if (s.includes('aprovado') || s.includes('confirmado')) return 'bg-success';
    if (s.includes('pendente')) return 'bg-warning';
    if (s.includes('negado') || s.includes('cancelado')) return 'bg-danger';
    return 'bg-info';
}

// Função para validar datas
function validarDatas() {
    const dataInicial = document.getElementById('data_inicio');
    const dataFinal = document.getElementById('data_fim');
    
    if (dataInicial && dataFinal && dataInicial.value && dataFinal.value) {
        const inicio = new Date(dataInicial.value);
        const fim = new Date(dataFinal.value);
        
        if (inicio > fim) {
            alert('A data inicial não pode ser maior que a data final.');
            dataInicial.focus();
            return false;
        }
        
        // Verificar se o período não é muito longo (mais de 1 ano)
        const diffTime = Math.abs(fim - inicio);
        const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays > 365) {
            alert('O período selecionado não pode ser maior que 1 ano.');
            dataInicial.focus();
            return false;
        }
    }
    
    return true;
}

// Função para exportar dados com AJAX (padrão para todos os templates)
function exportarDadosComum(formato, exportUrl) {
    const form = document.getElementById('filtroForm');
    const formData = new FormData(form);
    formData.append('formato', formato);
    
    // Mostrar loading
    const loadingMsg = document.createElement('div');
    loadingMsg.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processando export...';
    loadingMsg.style.cssText = 'position: fixed; top: 20px; right: 20px; background: #007bff; color: white; padding: 10px 15px; border-radius: 5px; z-index: 9999;';
    document.body.appendChild(loadingMsg);
    
    // Fazer requisição AJAX
    fetch(exportUrl, {
        method: 'POST',
        body: formData,
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
        }
    })
    .then(response => {
        console.log('Response headers:', response.headers);
        console.log('Content-Type:', response.headers.get('content-type'));
        
        if (response.headers.get('content-type')?.includes('application/json')) {
            console.log('Detectado JSON - processamento em background');
            return response.json();
        } else {
            console.log('Detectado arquivo - fazendo download direto');
            // Download direto
            return response.blob().then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = response.headers.get('content-disposition')?.split('filename=')[1]?.replace(/"/g, '') || `export.${formato}`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                document.body.removeChild(a);
                return { status: 'download' };
            });
        }
    })
    .then(data => {
        console.log('Data recebida:', data);
        if (data && data.success && data.message) {
            // Mostrar mensagem de processamento em background
            alert(`Export iniciado!\n\n${data.message}`);
        } else if (data && data.error) {
            // Mostrar mensagem de erro
            alert(`Erro no export:\n\n${data.error}`);
        }
    })
    .catch(error => {
        console.error('Erro no export:', error);
        alert('Erro ao processar export. Tente novamente.');
    })
    .finally(() => {
        // Remover loading
        document.body.removeChild(loadingMsg);
    });
}

// Função para inicializar validações de data
function inicializarValidacoesDatas() {
    const dataInicial = document.getElementById('data_inicio');
    const dataFinal = document.getElementById('data_fim');
    
    if (dataInicial && dataFinal) {
        dataInicial.addEventListener('change', validarDatas);
        dataFinal.addEventListener('change', validarDatas);
    }
}

// Função para inicializar eventos de exportação
function inicializarEventosExportacao(exportUrl) {
    document.querySelectorAll('[data-formato]').forEach(btn => {
        btn.addEventListener('click', function(e) {
            e.preventDefault();
            const formato = this.dataset.formato;
            exportarDadosComum(formato, exportUrl);
        });
    });
}

// Inicialização automática quando DOM estiver carregado
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar validações de data em todos os templates
    inicializarValidacoesDatas();
    
    // Aguardar um pouco para garantir que os elementos estejam carregados
    setTimeout(() => {
        // Os eventos de exportação serão inicializados individualmente em cada template
        // pois cada um tem uma URL diferente
    }, 1000);
});
