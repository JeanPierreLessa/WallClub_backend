/**
 * JavaScript para listagem de lançamentos manuais
 * Segue diretrizes técnicas: arquivo separado, nomenclatura snake_case, modais Bootstrap
 */

document.addEventListener('DOMContentLoaded', function() {
    inicializar_eventos_modais();
});

/**
 * Inicializa eventos dos modais de confirmação
 */
function inicializar_eventos_modais() {
    const modal_processar = document.getElementById('modalProcessar');
    const modal_cancelar = document.getElementById('modalCancelar');
    
    if (modal_processar) {
        modal_processar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const lancamento_id = button.getAttribute('data-lancamento-id');
            
            const btn_confirmar = modal_processar.querySelector('#btnConfirmarProcessar');
            btn_confirmar.onclick = function() {
                processar_lancamento(lancamento_id);
            };
        });
    }
    
    if (modal_cancelar) {
        modal_cancelar.addEventListener('show.bs.modal', function(event) {
            const button = event.relatedTarget;
            const lancamento_id = button.getAttribute('data-lancamento-id');
            
            const btn_confirmar = modal_cancelar.querySelector('#btnConfirmarCancelar');
            btn_confirmar.onclick = function() {
                cancelar_lancamento(lancamento_id);
            };
        });
    }
}

/**
 * Processa um lançamento manual
 * @param {string} lancamento_id - ID do lançamento
 */
function processar_lancamento(lancamento_id) {
    const csrf_token = obter_csrf_token();
    
    fetch(`/portal_admin/lancamentos-manuais/${lancamento_id}/processar/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
        }
    })
    .then(response => response.json())
    .then(data => {
        fechar_modal('modalProcessar');
        
        if (data.success) {
            mostrar_mensagem_sucesso(data.message);
            setTimeout(() => location.reload(), 1500);
        } else {
            mostrar_mensagem_erro('Erro: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erro ao processar lançamento:', error);
        fechar_modal('modalProcessar');
        mostrar_mensagem_erro('Erro interno. Verifique o console para mais detalhes.');
    });
}

/**
 * Cancela um lançamento manual
 * @param {string} lancamento_id - ID do lançamento
 */
function cancelar_lancamento(lancamento_id) {
    const motivo_textarea = document.getElementById('motivoCancelamento');
    const motivo = motivo_textarea.value.trim();
    
    if (!motivo) {
        mostrar_mensagem_erro('Motivo do cancelamento é obrigatório');
        motivo_textarea.focus();
        return;
    }
    
    const csrf_token = obter_csrf_token();
    
    fetch(`/portal_admin/lancamentos-manuais/${lancamento_id}/cancelar/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
        },
        body: JSON.stringify({ motivo: motivo })
    })
    .then(response => response.json())
    .then(data => {
        fechar_modal('modalCancelar');
        
        if (data.success) {
            mostrar_mensagem_sucesso(data.message);
            setTimeout(() => location.reload(), 1500);
        } else {
            mostrar_mensagem_erro('Erro: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erro ao cancelar lançamento:', error);
        fechar_modal('modalCancelar');
        mostrar_mensagem_erro('Erro interno. Verifique o console para mais detalhes.');
    });
}

/**
 * Obtém o token CSRF
 * @returns {string} - Token CSRF
 */
function obter_csrf_token() {
    const csrf_input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrf_input) {
        return csrf_input.value;
    }
    
    // Fallback: buscar no cookie
    const cookies = document.cookie.split(';');
    for (let cookie of cookies) {
        const [name, value] = cookie.trim().split('=');
        if (name === 'csrftoken') {
            return value;
        }
    }
    
    return '';
}

/**
 * Fecha um modal específico
 * @param {string} modal_id - ID do modal
 */
function fechar_modal(modal_id) {
    const modal_element = document.getElementById(modal_id);
    if (modal_element) {
        const modal_instance = bootstrap.Modal.getInstance(modal_element);
        if (modal_instance) {
            modal_instance.hide();
        }
    }
}

/**
 * Mostra mensagem de sucesso
 * @param {string} mensagem - Mensagem a ser exibida
 */
function mostrar_mensagem_sucesso(mensagem) {
    criar_alerta(mensagem, 'success');
}

/**
 * Mostra mensagem de erro
 * @param {string} mensagem - Mensagem a ser exibida
 */
function mostrar_mensagem_erro(mensagem) {
    criar_alerta(mensagem, 'danger');
}

/**
 * Cria um alerta Bootstrap
 * @param {string} mensagem - Mensagem do alerta
 * @param {string} tipo - Tipo do alerta (success, danger, warning, info)
 */
function criar_alerta(mensagem, tipo) {
    const container = document.querySelector('.container-fluid .row .col-12');
    if (!container) return;
    
    const alerta = document.createElement('div');
    alerta.className = `alert alert-${tipo} alert-dismissible fade show`;
    alerta.setAttribute('role', 'alert');
    alerta.innerHTML = `
        ${mensagem}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    // Inserir após o breadcrumb
    const breadcrumb = container.querySelector('nav[aria-label="breadcrumb"]');
    if (breadcrumb) {
        breadcrumb.insertAdjacentElement('afterend', alerta);
    } else {
        container.insertBefore(alerta, container.firstChild);
    }
    
    // Auto-remover após 5 segundos
    setTimeout(() => {
        if (alerta.parentNode) {
            alerta.remove();
        }
    }, 5000);
}
