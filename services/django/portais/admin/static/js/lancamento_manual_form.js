/**
 * JavaScript para formulário de lançamento manual
 * Segue diretrizes técnicas: arquivo separado, nomenclatura snake_case
 */

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('formLancamentoManual');
    const valorInput = document.getElementById('valor');
    
    if (form) {
        form.addEventListener('submit', processar_formulario_lancamento);
    }
    
    if (valorInput) {
        valorInput.addEventListener('input', formatar_campo_valor);
    }
});

/**
 * Processa o envio do formulário de lançamento manual
 * @param {Event} e - Evento de submit
 */
function processar_formulario_lancamento(e) {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    
    // Validar campos obrigatórios
    if (!validar_campos_obrigatorios(formData)) {
        return;
    }
    
    // Converter FormData para objeto JSON
    const dados = converter_form_data_para_json(formData);
    
    // Fazer requisição AJAX
    enviar_dados_lancamento(dados);
}

/**
 * Valida campos obrigatórios do formulário
 * @param {FormData} formData - Dados do formulário
 * @returns {boolean} - True se válido
 */
function validar_campos_obrigatorios(formData) {
    const campos_obrigatorios = ['loja_id', 'tipo_lancamento', 'valor', 'descricao'];
    
    for (const campo of campos_obrigatorios) {
        if (!formData.get(campo)) {
            mostrar_modal_erro(`Campo ${campo.replace('_', ' ')} é obrigatório`);
            return false;
        }
    }
    return true;
}

/**
 * Converte FormData para objeto JSON
 * @param {FormData} formData - Dados do formulário
 * @returns {Object} - Objeto JSON
 */
function converter_form_data_para_json(formData) {
    const dados = {};
    for (const [key, value] of formData.entries()) {
        dados[key] = value;
    }
    return dados;
}

/**
 * Envia dados do lançamento via AJAX
 * @param {Object} dados - Dados para envio
 */
function enviar_dados_lancamento(dados) {
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    
    fetch(window.location.pathname.replace('/novo/', '/criar/'), {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify(dados)
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            mostrar_modal_sucesso(data.message, function() {
                window.location.href = '/lancamentos_manuais/';
            });
        } else {
            mostrar_modal_erro('Erro: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Erro:', error);
        mostrar_modal_erro('Erro interno. Verifique o console para mais detalhes.');
    });
}

/**
 * Formata campo valor - apenas números e vírgula/ponto
 * @param {Event} e - Evento de input
 */
function formatar_campo_valor(e) {
    let value = e.target.value.replace(/[^\d,\.]/g, '');
    
    // Permite apenas uma vírgula ou ponto
    let parts = value.split(/[,\.]/);
    if (parts.length > 2) {
        value = parts[0] + ',' + parts[1];
    }
    
    // Limita a 2 casas decimais
    if (parts[1] && parts[1].length > 2) {
        value = parts[0] + ',' + parts[1].substring(0, 2);
    }
    
    e.target.value = value;
}

/**
 * Mostra modal de erro (substitui alert)
 * @param {string} mensagem - Mensagem de erro
 */
function mostrar_modal_erro(mensagem) {
    // TODO: Implementar modal Bootstrap em vez de alert
    alert(mensagem);
}

/**
 * Mostra modal de sucesso (substitui alert)
 * @param {string} mensagem - Mensagem de sucesso
 * @param {Function} callback - Função a executar após fechar modal
 */
function mostrar_modal_sucesso(mensagem, callback) {
    // TODO: Implementar modal Bootstrap em vez de alert
    alert(mensagem);
    if (callback) callback();
}
