/**
 * Script para cadastro de loja com integração Own Financial
 */

class CadastroLojaOwn {
    constructor() {
        this.apiBaseUrl = '/api/own';
        this.cnaeData = [];
        this.cestasData = [];
        this.tarifasData = [];
        this.tarifaCounter = 0;
        this.cestasCarregadas = false;
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

        // Botão consultar protocolo
        const btnConsultarProtocolo = document.getElementById('btn-consultar-protocolo');
        if (btnConsultarProtocolo) {
            btnConsultarProtocolo.addEventListener('click', () => this.consultarProtocolo());
        }

        // Formatação de moeda
        const moneyInputs = document.querySelectorAll('.money-input');
        moneyInputs.forEach(input => {
            // Formatar valor inicial
            if (input.value) {
                input.value = this.formatMoney(input.value);
            }

            input.addEventListener('input', (e) => {
                let value = e.target.value.replace(/\D/g, '');
                e.target.value = this.formatMoney(value);
            });

            input.addEventListener('blur', (e) => {
                if (!e.target.value) {
                    e.target.value = '0,00';
                }
            });
        });

        // Busca CNAE
        const inputCnae = document.getElementById('busca_cnae');
        if (inputCnae) {
            inputCnae.addEventListener('input', (e) => this.buscarCNAE(e.target.value));
        }

        // Radio buttons modelo de tarifação - alternar entre FLEX e MDR
        const radioFlex = document.getElementById('modelo_flex');
        const radioMdr = document.getElementById('modelo_mdr');
        if (radioFlex && radioMdr) {
            const toggleModelo = () => {
                const isFlex = radioFlex.checked;
                const aceitaEcommerce = document.getElementById('aceita_ecommerce')?.checked || false;

                // Cestas FLEX
                const cestaFlexPos = document.getElementById('cesta_parcela_pos');
                const cestaFlexEcommerce = document.getElementById('cesta_parcela_ecommerce');

                // Cestas MDR
                const cestaMdrPos = document.getElementById('cesta_bandeira_mdr');
                const cestaMdrEcommerce = document.getElementById('cesta_ecommerce_mdr');

                // Campos de antecipação
                const camposAntecipacao = document.getElementById('antecipacao_automatica')?.closest('.col-md-3');
                const campoTaxaAntecipacao = document.getElementById('taxa_antecipacao')?.closest('.col-md-3');

                if (isFlex) {
                    // FLEX: Mostrar cesta 333 (POS) + 1655 (E-commerce se marcado)
                    if (cestaFlexPos) cestaFlexPos.style.display = 'block';
                    if (cestaFlexEcommerce) cestaFlexEcommerce.style.display = aceitaEcommerce ? 'block' : 'none';

                    // Ocultar cestas MDR
                    if (cestaMdrPos) cestaMdrPos.style.display = 'none';
                    if (cestaMdrEcommerce) cestaMdrEcommerce.style.display = 'none';

                    // Ocultar antecipação no FLEX
                    if (camposAntecipacao) camposAntecipacao.style.display = 'none';
                    if (campoTaxaAntecipacao) campoTaxaAntecipacao.style.display = 'none';
                } else {
                    // MDR: Mostrar cesta 117 (POS) + 1608 (E-commerce se marcado)
                    if (cestaMdrPos) cestaMdrPos.style.display = 'block';
                    if (cestaMdrEcommerce) cestaMdrEcommerce.style.display = aceitaEcommerce ? 'block' : 'none';

                    // Ocultar cestas FLEX
                    if (cestaFlexPos) cestaFlexPos.style.display = 'none';
                    if (cestaFlexEcommerce) cestaFlexEcommerce.style.display = 'none';

                    // Mostrar antecipação no MDR
                    if (camposAntecipacao) camposAntecipacao.style.display = 'block';
                    if (campoTaxaAntecipacao) campoTaxaAntecipacao.style.display = 'block';
                }
            };

            radioFlex.addEventListener('change', toggleModelo);
            radioMdr.addEventListener('change', toggleModelo);

            // Executar toggle inicial
            toggleModelo();
        }

        // Checkbox e-commerce - mostrar/ocultar cestas de e-commerce baseado no modelo
        const checkboxEcommerce = document.getElementById('aceita_ecommerce');
        if (checkboxEcommerce) {
            checkboxEcommerce.addEventListener('change', (e) => {
                const isFlex = document.getElementById('modelo_flex')?.checked || false;
                const aceitaEcommerce = e.target.checked;

                if (isFlex) {
                    // FLEX: Mostrar/ocultar cesta 1655
                    const cestaFlexEcommerce = document.getElementById('cesta_parcela_ecommerce');
                    if (cestaFlexEcommerce) {
                        cestaFlexEcommerce.style.display = aceitaEcommerce ? 'block' : 'none';
                    }
                } else {
                    // MDR: Mostrar/ocultar cesta 1608
                    const cestaMdrEcommerce = document.getElementById('cesta_ecommerce_mdr');
                    if (cestaMdrEcommerce) {
                        cestaMdrEcommerce.style.display = aceitaEcommerce ? 'block' : 'none';
                    }
                }
            });
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

            // Marcar apenas campos específicos como obrigatórios (excluir campos de busca e readonly)
            const camposObrigatorios = ['cnae', 'mcc', 'faturamento_previsto', 'faturamento_contratado',
                'responsavel_assinatura'];

            camposObrigatorios.forEach(id => {
                const campo = document.getElementById(id);
                if (campo) {
                    campo.required = mostrar;
                }
            });

            // Remover required de campos que não devem ser obrigatórios
            const camposNaoObrigatorios = ['busca_cnae', 'ramo_atividade', 'quantidade_pos',
                'antecipacao_automatica', 'taxa_antecipacao', 'aceita_ecommerce'];
            camposNaoObrigatorios.forEach(id => {
                const campo = document.getElementById(id);
                if (campo) {
                    campo.required = false;
                }
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
            this.carregarTodasAsCestas();
        } catch (error) {
            console.error('Erro ao carregar cestas:', error);
            this.mostrarErro('Erro ao carregar cestas de tarifas');
        }
    }

    async carregarTodasAsCestas() {
        // Cestas por ID (conforme conversas com backend):
        // 117: Bandeira POS (MDR)
        // 333: Parcela POS (FLEX)
        // 1608: Bandeira E-commerce (MDR)
        // 1655: Parcela E-commerce (FLEX)

        const cestas = {
            117: null,    // Bandeira para MDR
            333: null,    // Parcela POS para FLEX
            1608: null,   // E-commerce para MDR
            1655: null    // E-commerce para FLEX
        };

        this.cestasData.forEach(cesta => {
            const cestaId = parseInt(cesta.cestaId);
            if (cestas.hasOwnProperty(cestaId)) {
                cestas[cestaId] = cesta.cestaId;
            }
        });

        // Carrega todas as 4 cestas, mas mostra/oculta conforme modelo
        // FLEX: 333 (parcela POS) + 1655 (parcela e-commerce)
        if (cestas[333]) {
            await this.carregarTarifasCesta(cestas[333], 'cesta_parcela_pos');
        }
        if (cestas[1655]) {
            await this.carregarTarifasCesta(cestas[1655], 'cesta_parcela_ecommerce');
        }

        // MDR: 117 (bandeira POS) + 1608 (bandeira e-commerce)
        if (cestas[117]) {
            await this.carregarTarifasCesta(cestas[117], 'cesta_bandeira_mdr');
        }
        if (cestas[1608]) {
            await this.carregarTarifasCesta(cestas[1608], 'cesta_ecommerce_mdr');
        }

        // Adicionar campo hidden com total de tarifas no formulário
        const form = document.getElementById('form_cadastro_loja');
        if (form) {
            let totalInput = form.querySelector('input[name="total_tarifas"]');
            if (!totalInput) {
                totalInput = document.createElement('input');
                totalInput.type = 'hidden';
                totalInput.name = 'total_tarifas';
                form.appendChild(totalInput);
            }
            totalInput.value = this.tarifaCounter;
        }

        // Marcar cestas como carregadas
        this.cestasCarregadas = true;
        console.log(`✅ Cestas carregadas: ${this.tarifaCounter} tarifas`);
    }

    async carregarTarifasCesta(cestaId, containerId, isMDR = false) {
        if (!cestaId) return;

        const container = document.getElementById(containerId);
        if (!container) return;

        try {
            const response = await fetch(`${this.apiBaseUrl}/cestas/${cestaId}/tarifas/`, {
                credentials: 'same-origin',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            if (!response.ok) throw new Error('Erro ao carregar tarifas');

            const data = await response.json();

            if (!data.tarifas || data.tarifas.length === 0) {
                container.innerHTML = '<p class="text-muted">Nenhuma tarifa encontrada</p>';
                return;
            }

            // Mapa de IDs de cesta para seus nomes descritivos
            const cestaNames = {
                '117': 'Bandeira',
                '333': 'Parcela POS',
                '1608': 'E-commerce',
                '1655': 'Parcela E-commerce'
            };

            const cestaNome = cestaNames[cestaId] || `Cesta ${cestaId}`;
            const totalTarifas = data.tarifas.length;

            let html = `
                <div class="alert alert-light border mb-3">
                    <strong>${cestaNome}</strong> <span class="badge bg-secondary">${totalTarifas} tarifa(s)</span>
                </div>
                <table class="table table-sm table-bordered">
                    <thead>
                        <tr>
                            <th>Descrição</th>
                            <th class="text-end" style="width: 200px;">Valor</th>
                            <th class="text-end" style="width: 150px;">Mínimo</th>
                        </tr>
                    </thead>
                    <tbody>
        `;

            data.tarifas.forEach((tarifa) => {
                const valorMinimo = parseFloat(tarifa.valor_minimo || 0);
                const valorAtual = parseFloat(tarifa.valor || valorMinimo);
                const currentIndex = this.tarifaCounter++;

                html += `
                <tr>
                    <td>
                        ${tarifa.descricao || 'Tarifa'}
                        <input type="hidden" name="tarifa_id_${currentIndex}" value="${tarifa.cesta_valor_id}">
                        <input type="hidden" name="tarifa_cesta_id_${currentIndex}" value="${cestaId}">
                    </td>
                    <td class="text-end">
                        <input type="number"
                               class="form-control form-control-sm text-end tarifa-valor"
                               name="tarifa_valor_${currentIndex}"
                               data-tarifa-id="${tarifa.cesta_valor_id}"
                               data-valor-minimo="${valorMinimo}"
                               value="${valorAtual.toFixed(2)}"
                               min="${valorMinimo}"
                               step="0.01"
                               style="width: 100%;">
                    </td>
                    <td class="text-end text-muted">
                        ${valorMinimo.toFixed(2)}
                    </td>
                </tr>
            `;
            });

            html += `
                    </tbody>
                </table>
        `;

            container.innerHTML = html;

            // Adicionar validação de valor mínimo
            this.adicionarValidacaoTarifas();
        } catch (error) {
            console.error('Erro ao carregar tarifas:', error);
            this.mostrarErro('Erro ao carregar tarifas da cesta');
        }
    }

    adicionarValidacaoTarifas() {
        const inputs = document.querySelectorAll('.tarifa-valor');
        inputs.forEach(input => {
            input.addEventListener('change', function () {
                const valorMinimo = parseFloat(this.dataset.valorMinimo);
                const valorAtual = parseFloat(this.value);

                if (valorAtual < valorMinimo) {
                    alert(`O valor não pode ser menor que o mínimo: R$ ${valorMinimo.toFixed(2)}`);
                    this.value = valorMinimo.toFixed(2);
                }
            });
        });
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

        // Validar que as cestas foram carregadas
        if (!this.cestasCarregadas) {
            erros.push('Aguarde o carregamento das cestas de tarifas antes de salvar.');
        }

        // Validar que existem tarifas
        const totalTarifas = parseInt(document.querySelector('input[name="total_tarifas"]')?.value || '0');
        if (totalTarifas === 0) {
            erros.push('Nenhuma tarifa carregada. Aguarde o carregamento das cestas.');
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

    async consultarProtocolo() {
        const btn = document.getElementById('btn-consultar-protocolo');
        const resultadoDiv = document.getElementById('resultado-protocolo');

        // Pegar loja_id da URL
        const urlParts = window.location.pathname.split('/');
        const lojaId = urlParts[urlParts.indexOf('loja') + 1];

        if (!lojaId) {
            alert('Erro ao identificar loja');
            return;
        }

        // Desabilitar botão e mostrar loading
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Consultando...';
        resultadoDiv.innerHTML = '';

        try {
            const response = await fetch(`${this.apiBaseUrl}/protocolo/?loja_id=${lojaId}`);
            const data = await response.json();

            if (response.ok && data.sucesso) {
                // Montar HTML com resultado
                const statusClass = this.getStatusClass(data.status);
                const podeReenviar = data.podeReenviar ?
                    '<span class="badge bg-warning">Pode reenviar</span>' :
                    '<span class="badge bg-info">Aguardando processamento</span>';

                resultadoDiv.innerHTML = `
                    <div class="alert alert-${statusClass} mb-0">
                        <h6 class="mb-2"><strong>Status do Protocolo ${data.protocolo}</strong></h6>
                        <p class="mb-1"><strong>Status:</strong> ${data.status} ${podeReenviar}</p>
                        <p class="mb-1"><strong>Data Recebimento:</strong> ${data.dataRecebimento}</p>
                        <p class="mb-1"><strong>Tipo:</strong> ${data.tipo}</p>
                        <p class="mb-1"><strong>Reenvio:</strong> ${data.reenvio === 'S' ? '<span class="badge bg-warning">Sim</span>' : '<span class="badge bg-secondary">Não</span>'}</p>
                        ${data.contrato && data.contrato.trim() && data.contrato !== ' ' ? `<p class="mb-1"><strong>Contrato:</strong> ${data.contrato}</p>` : ''}
                        ${data.identificadorCliente ? `<p class="mb-1"><strong>Identificador Cliente:</strong> ${data.identificadorCliente}</p>` : ''}
                        ${data.cnpjWL ? `<p class="mb-1"><strong>CNPJ White Label:</strong> ${data.cnpjWL}</p>` : ''}
                        ${data.cnpjEstabelecimento ? `<p class="mb-1"><strong>CNPJ Estabelecimento:</strong> ${data.cnpjEstabelecimento}</p>` : ''}
                        ${data.motivo && data.motivo.trim() && data.motivo !== ' ' ? `<p class="mb-0"><strong>Motivo:</strong> ${data.motivo}</p>` : ''}
                    </div>
                `;

            } else {
                resultadoDiv.innerHTML = `
                    <div class="alert alert-warning mb-0">
                        <i class="fas fa-exclamation-triangle"></i> ${data.erro || 'Protocolo não encontrado'}
                    </div>
                `;
            }
        } catch (error) {
            console.error('Erro ao consultar protocolo:', error);
            resultadoDiv.innerHTML = `
                <div class="alert alert-danger mb-0">
                    <i class="fas fa-times-circle"></i> Erro ao consultar protocolo: ${error.message}
                </div>
            `;
        } finally {
            // Reabilitar botão
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-search"></i> Consultar Status do Protocolo';
        }
    }

    getStatusClass(status) {
        const statusMap = {
            'EM ANALISE': 'info',
            'PENDENTE': 'info',
            'SUCESSO': 'success',
            'APPROVED': 'success',
            'ERRO': 'danger',
            'REPROVED': 'danger'
        };
        return statusMap[status] || 'secondary';
    }

    formatMoney(value) {
        // Remove tudo que não é dígito
        value = value.toString().replace(/\D/g, '');

        // Se vazio, retorna 0,00
        if (!value || value === '0') {
            return '0,00';
        }

        // Converte para número e divide por 100 para ter centavos
        const numValue = parseInt(value) / 100;

        // Formata com separador de milhar e decimal
        return numValue.toLocaleString('pt-BR', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        });
    }
}

// Inicializar quando o DOM estiver pronto
document.addEventListener('DOMContentLoaded', () => {
    new CadastroLojaOwn();
});
