// Script para listagem de ofertas e disparo de push
document.addEventListener('DOMContentLoaded', function() {
    const modalDisparar = new bootstrap.Modal(document.getElementById('modalDisparar'));
    const btnDisparar = document.querySelectorAll('.btn-disparar');
    const btnConfirmar = document.getElementById('btn-confirmar-disparo');
    const modalTitulo = document.getElementById('modal-oferta-titulo');
    const disparoLoading = document.getElementById('disparo-loading');
    
    let ofertaIdSelecionada = null;
    
    // Abrir modal de confirmação
    btnDisparar.forEach(btn => {
        btn.addEventListener('click', function() {
            ofertaIdSelecionada = this.getAttribute('data-oferta-id');
            const ofertaTitulo = this.getAttribute('data-oferta-titulo');
            
            modalTitulo.textContent = ofertaTitulo;
            disparoLoading.style.display = 'none';
            btnConfirmar.disabled = false;
            
            modalDisparar.show();
        });
    });
    
    // Confirmar disparo
    btnConfirmar.addEventListener('click', function() {
        if (!ofertaIdSelecionada) return;
        
        // Mostrar loading
        disparoLoading.style.display = 'block';
        btnConfirmar.disabled = true;
        
        // Enviar requisição
        fetch(`/portal_lojista/ofertas/${ofertaIdSelecionada}/disparar/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCookie('csrftoken')
            },
            body: JSON.stringify({})
        })
        .then(response => response.json())
        .then(data => {
            disparoLoading.style.display = 'none';
            
            if (data.sucesso) {
                modalDisparar.hide();
                
                // Mostrar mensagem de sucesso
                const alert = document.createElement('div');
                alert.className = 'alert alert-success alert-dismissible fade show';
                alert.innerHTML = `
                    <i class="fas fa-check-circle me-2"></i>
                    ${data.mensagem}
                    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                `;
                
                document.querySelector('.container-fluid').insertBefore(
                    alert, 
                    document.querySelector('.container-fluid').firstChild
                );
                
                // Auto-fechar após 5 segundos
                setTimeout(() => {
                    alert.remove();
                }, 5000);
                
                // Recarregar após 2 segundos
                setTimeout(() => {
                    window.location.reload();
                }, 2000);
            } else {
                // Mostrar erro
                alert('Erro: ' + data.mensagem);
                btnConfirmar.disabled = false;
            }
        })
        .catch(error => {
            disparoLoading.style.display = 'none';
            btnConfirmar.disabled = false;
            alert('Erro ao processar requisição: ' + error.message);
        });
    });
    
    // Função para pegar CSRF token
    function getCookie(name) {
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
});
