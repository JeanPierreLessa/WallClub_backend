/**
 * Script para cadastro de loja com integração Own Financial
 */

class CadastroLojaOwn {
    constructor() {
        this.apiBaseUrl = '/api/own';
        this.cnaeData = [];
        this.cestasData = [];
        this.tarifasData = [];
        this.csrfToken = this.getCsrfToken();
        this.init();
    }

    getCsrfToken() {
        const name = 'csrftoken';
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    init() {
        this.setupEventListeners();
        this.carregarCNAE();
        this.carregarCestas();
    }

    setupEventListeners() {
        // Checkbox "Cadastrar na Own"
        const checkboxOwn = document.getElementById('cadastrar_own');
        if (checkboxOwn) {
            checkboxOwn.addEventListener('change', (e) => this.toggleCamposOwn(e.target.checked));
        }

        // Busca CNAE
        const inputCnae = document.getElementById('busca_cnae');
        if (inputCnae) {
            inputCnae.addEventListener('input', (e) => this.buscarCNAE(e.target.value));
        }

        // Seleção de cesta
        const selectCesta = document.getElementById('id_cesta');
        if (selectCesta) {
            selectCesta.addEventListener('change', (e) => this.carregarTarifasCesta(e.target.value));
        }

        // Busca CEP
        const inputCep = document.getElementById('cep');
        if (inputCep) {
            inputCep.addEventListener('blur', (e) => this.buscarCEP(e.target.value));
        }

        // Validação do formulário
        const form = document.getElementById('form_cadastro_loja');
        if (form) {
            form.addEventListener('submit', (e) => this.validarFormulario(e));
        }
    }

    toggleCamposOwn(mostrar) {
        const camposOwn = document.getElementById('campos_own');
        if (camposOwn) {
            camposOwn.style.display = mostrar ? 'block' : 'none';

            // Marcar campos como obrigatórios
            const inputs = camposOwn.querySelectorAll('input, select');
            inputs.forEach(input => {
                input.required = mostrar;
            });
        }
    }

    async carregarCNAE() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/cnae/`, {
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            if (!response.ok) throw new Error('Erro ao carregar CNAE');

            this.cnaeData = await response.json();
            this.renderizarCNAE(this.cnaeData);
        } catch (error) {
            console.error('Erro ao carregar CNAE:', error);
            this.mostrarErro('Erro ao carregar lista de atividades CNAE');
        }
    }

    buscarCNAE(termo) {
        if (!termo || termo.length < 3) {
            this.renderizarCNAE(this.cnaeData);
            return;
        }

        const filtrados = this.cnaeData.filter(cnae =>
            cnae.descCnae.toLowerCase().includes(termo.toLowerCase()) ||
            cnae.codCnae.includes(termo)
        );

        this.renderizarCNAE(filtrados);
    }

    renderizarCNAE(dados) {
        const select = document.getElementById('cnae');
        if (!select) return;

        select.innerHTML = '<option value="">Selecione uma atividade</option>';

        dados.forEach(cnae => {
            const option = document.createElement('option');
            option.value = cnae.codCnae;
            option.dataset.mcc = cnae.codMcc;
            option.dataset.descricao = cnae.descCnae;
            option.textContent = `${cnae.codCnae} - ${cnae.descCnae}`;
            select.appendChild(option);
        });

        // Atualizar MCC quando CNAE for selecionado
        select.addEventListener('change', (e) => {
            const selectedOption = e.target.selectedOptions[0];
            if (selectedOption) {
                document.getElementById('mcc').value = selectedOption.dataset.mcc || '';
                document.getElementById('ramo_atividade').value = selectedOption.dataset.descricao || '';
            }
        });
    }

    async carregarCestas() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/cestas/`, {
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            if (!response.ok) throw new Error('Erro ao carregar cestas');

            this.cestasData = await response.json();
            this.renderizarCestas(this.cestasData);
        } catch (error) {
            console.error('Erro ao carregar cestas:', error);
            this.mostrarErro('Erro ao carregar cestas de tarifas');
        }
    }

    renderizarCestas(dados) {
        const select = document.getElementById('id_cesta');
        if (!select) return;

        select.innerHTML = '<option value="">Selecione uma cesta</option>';

        dados.forEach(cesta => {
            const option = document.createElement('option');
            option.value = cesta.cestaId;
            option.textContent = cesta.nomeCesta;
            select.appendChild(option);
        });
    }

    async carregarTarifasCesta(cestaId) {
        if (!cestaId) {
            document.getElementById('tarifas_preview').innerHTML = '';
            return;
        }

        try {
            const response = await fetch(`${this.apiBaseUrl}/cestas/${cestaId}/tarifas/`, {
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            if (!response.ok) throw new Error('Erro ao carregar tarifas');

            const data = await response.json();
            this.tarifasData = data.tarifas || [];
            this.renderizarTarifas(data);
        } catch (error) {
            console.error('Erro ao carregar tarifas:', error);
            this.mostrarErro('Erro ao carregar tarifas da cesta');
        }
    }

    renderizarTarifas(data) {
        const container = document.getElementById('tarifas_preview');
        if (!container) return;

        if (!data.tarifas || data.tarifas.length === 0) {
            container.innerHTML = '<p class="text-muted">Nenhuma tarifa encontrada</p>';
            return;
        }

        let html = `
            <div class="card">
                <div class="card-header">
                    <h6 class="mb-0">Tarifas da Cesta: ${data.nome_cesta}</h6>
                </div>
                <div class="card-body">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Descrição</th>
                                <th class="text-end">Valor</th>
                            </tr>
                        </thead>
                        <tbody>
        `;

        data.tarifas.forEach(tarifa => {
            html += `
                <tr>
                    <td>${tarifa.descricao || 'Tarifa'}</td>
                    <td class="text-end">R$ ${parseFloat(tarifa.valor).toFixed(2)}</td>
                </tr>
            `;
        });

        html += `
                        </tbody>
                    </table>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    async buscarCEP(cep) {
        cep = cep.replace(/\D/g, '');

        if (cep.length !== 8) return;

        try {
            const response = await fetch(`https://viacep.com.br/ws/${cep}/json/`);
            if (!response.ok) throw new Error('CEP não encontrado');

            const data = await response.json();

            if (data.erro) {
                this.mostrarErro('CEP não encontrado');
                return;
            }

            // Preencher campos
            document.getElementById('logradouro').value = data.logradouro || '';
            document.getElementById('bairro').value = data.bairro || '';
            document.getElementById('municipio').value = data.localidade || '';
            document.getElementById('uf').value = data.uf || '';

            // Focar no número
            document.getElementById('numero_endereco').focus();
        } catch (error) {
            console.error('Erro ao buscar CEP:', error);
            this.mostrarErro('Erro ao buscar CEP');
        }
    }

    validarFormulario(event) {
        const cadastrarOwn = document.getElementById('cadastrar_own').checked;

        if (!cadastrarOwn) {
            return true; // Validação normal do HTML5
        }

        // Validações específicas para Own
        const erros = [];

        // Validar CNAE
        if (!document.getElementById('cnae').value) {
            erros.push('CNAE é obrigatório para cadastro na Own');
        }

        // Validar cesta
        if (!document.getElementById('id_cesta').value) {
            erros.push('Cesta de tarifas é obrigatória para cadastro na Own');
        }

        // Validar dados bancários
        if (!document.getElementById('codigo_banco').value) {
            erros.push('Código do banco é obrigatório');
        }

        if (!document.getElementById('agencia').value) {
            erros.push('Agência é obrigatória');
        }

        if (!document.getElementById('numero_conta').value) {
            erros.push('Número da conta é obrigatório');
        }

        if (!document.getElementById('digito_conta').value) {
            erros.push('Dígito da conta é obrigatório');
        }

        if (erros.length > 0) {
            event.preventDefault();
            this.mostrarErro(erros.join('<br>'));
            return false;
        }

        return true;
    }

    mostrarErro(mensagem) {
        // Criar toast de erro
        const toast = document.createElement('div');
        toast.className = 'alert alert-danger alert-dismissible fade show position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }

    mostrarSucesso(mensagem) {
        const toast = document.createElement('div');
        toast.className = 'alert alert-success alert-dismissible fade show position-fixed';
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${mensagem}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.remove();
        }, 5000);
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    new CadastroLojaOwn();
});
