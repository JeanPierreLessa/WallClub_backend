"""
Middleware para capturar marca do canal na URL do portal lojista
"""
from wallclub_core.estr_organizacional.canal import Canal


class MarcaCanalMiddleware:
    """Middleware para processar marca do canal na URL"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Processar marca antes da view
        self.process_marca(request)
        
        response = self.get_response(request)
        return response

    def process_marca(self, request):
        """Processa a marca do canal baseada na URL"""
        # Verificar se é uma URL do portal lojista
        if not request.path.startswith('/portal_lojista/'):
            return
            
        # Extrair marca da URL
        path_parts = request.path.strip('/').split('/')
        
        # Se tem marca na URL: /portal_lojista/aclub/...
        if len(path_parts) >= 2 and path_parts[1] not in ['', 'home', 'login', 'logout']:
            marca_url = path_parts[1]
            
            # Verificar se a marca existe no banco
            canal = Canal.objects.filter(marca=marca_url).first()
            if canal:
                request.marca_canal = marca_url
                request.canal_id = canal.id
                request.canal_info = {
                    'id': canal.id,
                    'nome': canal.nome,
                    'marca': canal.marca,
                    'logo_id': str(canal.id)  # Para usar como nome do arquivo (1.png, 6.png)
                }
            else:
                # Marca não encontrada, usar padrão
                request.marca_canal = 'wallclub'
                request.canal_id = 1  # ID padrão do wallclub
                request.canal_info = {
                    'id': 1,
                    'nome': 'WallClub',
                    'marca': 'wallclub',
                    'logo_id': '1'
                }
        else:
            # URL padrão sem marca: /portal_lojista/
            request.marca_canal = 'wallclub'
            request.canal_id = 1
            request.canal_info = {
                'id': 1,
                'nome': 'WallClub', 
                'marca': 'wallclub',
                'logo_id': '1'
            }
