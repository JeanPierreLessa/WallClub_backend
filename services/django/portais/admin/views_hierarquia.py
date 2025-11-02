from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection
from ..controle_acesso.decorators import require_admin_access
from portais.controle_acesso import require_funcionalidade


@require_funcionalidade('hierarquia_list')
def hierarquia_geral(request):
    """Visão geral da hierarquia organizacional"""
    from portais.controle_acesso.services import ControleAcessoService
    
    # Aplicar filtro por canal se necessário
    usuario_logado = getattr(request, 'portal_usuario', None)
    if usuario_logado:
        nivel_usuario = ControleAcessoService.obter_nivel_portal(usuario_logado, 'admin')
        if nivel_usuario == 'admin_canal':
            canais_usuario = ControleAcessoService.obter_canais_usuario(usuario_logado)
            if canais_usuario:
                canal_filter = f"AND c.id IN ({','.join(map(str, canais_usuario))})"
            else:
                canal_filter = "AND 1=0"  # Nenhum canal se não tem canais
        else:
            canal_filter = ""
    else:
        canal_filter = ""
    
    # Query para buscar toda a hierarquia de uma vez - com filtro por canal se necessário
    base_query = f"""
        SELECT 
            c.id as canal_id,
            c.nome as canal_nome,
            c.marca as canal_marca,
            r.id as regional_id,
            r.nome as regional_nome,
            v.id as vendedor_id,
            v.nome as vendedor_nome,
            g.id as grupo_id,
            g.nome as grupo_nome,
            COUNT(l.id) as total_lojas
        FROM canal c
        LEFT JOIN regionais r ON c.id = r.canalId
        LEFT JOIN vendedores v ON r.id = v.regionalId
        LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
        LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
        WHERE c.id IS NOT NULL {canal_filter}
        GROUP BY c.id, r.id, v.id, g.id
        ORDER BY c.nome, r.nome, v.nome, g.nome
    """
    
    with connection.cursor() as cursor:
        cursor.execute(base_query)
    
    rows = cursor.fetchall()
    
    # Organizar dados em estrutura hierárquica
    hierarquia = {}
    
    for row in rows:
        canal_id, canal_nome, canal_marca, regional_id, regional_nome, \
        vendedor_id, vendedor_nome, grupo_id, grupo_nome, total_lojas = row
        
        # Inicializar canal se não existe
        if canal_id not in hierarquia:
            hierarquia[canal_id] = {
                'id': canal_id,
                'nome': canal_nome,
                'marca': canal_marca,
                'regionais': {},
                'total_lojas': 0
            }
        
        # Adicionar regional se existe
        if regional_id:
            if regional_id not in hierarquia[canal_id]['regionais']:
                hierarquia[canal_id]['regionais'][regional_id] = {
                    'id': regional_id,
                    'nome': regional_nome,
                    'vendedores': {},
                    'total_lojas': 0
                }
            
            # Adicionar vendedor se existe
            if vendedor_id:
                if vendedor_id not in hierarquia[canal_id]['regionais'][regional_id]['vendedores']:
                    hierarquia[canal_id]['regionais'][regional_id]['vendedores'][vendedor_id] = {
                        'id': vendedor_id,
                        'nome': vendedor_nome,
                        'grupos': {},
                        'total_lojas': 0
                    }
                
                # Adicionar grupo se existe
                if grupo_id:
                    hierarquia[canal_id]['regionais'][regional_id]['vendedores'][vendedor_id]['grupos'][grupo_id] = {
                        'id': grupo_id,
                        'nome': grupo_nome,
                        'total_lojas': total_lojas or 0
                    }
                    
                    # Somar totais
                    hierarquia[canal_id]['regionais'][regional_id]['vendedores'][vendedor_id]['total_lojas'] += (total_lojas or 0)
                    hierarquia[canal_id]['regionais'][regional_id]['total_lojas'] += (total_lojas or 0)
                    hierarquia[canal_id]['total_lojas'] += (total_lojas or 0)
    
    # Estatísticas gerais
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM canal")
        total_canais = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM regionais")
        total_regionais = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM vendedores")
        total_vendedores = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM gruposeconomicos")
        total_grupos = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM loja")
        total_lojas = cursor.fetchone()[0]
    
    estatisticas = {
        'canais': total_canais,
        'regionais': total_regionais,
        'vendedores': total_vendedores,
        'grupos': total_grupos,
        'lojas': total_lojas
    }
    
    context = {
        'hierarquia': hierarquia,
        'estatisticas': estatisticas
    }
    
    return render(request, 'portais/admin/hierarquia_geral.html', context)


@require_admin_access
def canal_detail(request, canal_id):
    """Detalhes de um canal específico"""
    
    with connection.cursor() as cursor:
        # Buscar dados do canal
        cursor.execute("""
            SELECT id, nome, marca
            FROM canal 
            WHERE id = %s
        """, [canal_id])
        
        canal_data = cursor.fetchone()
        if not canal_data:
            return render(request, 'portais/admin/hierarquia_not_found.html', {
                'tipo': 'Canal',
                'id': canal_id
            })
        
        # Buscar comissão vigente do canal
        cursor.execute("""
            SELECT comissao, vigencia_inicio, vigencia_fim
            FROM canal_comissao 
            WHERE canal_id = %s 
            AND (vigencia_fim IS NULL OR vigencia_fim >= CURDATE())
            AND vigencia_inicio <= CURDATE()
            ORDER BY vigencia_inicio DESC
            LIMIT 1
        """, [canal_id])
        
        comissao_data = cursor.fetchone()
        from decimal import Decimal
        comissao_vigente = Decimal(str(comissao_data[0])) * 100 if comissao_data else None
        
        canal = {
            'id': canal_data[0],
            'nome': canal_data[1],
            'marca': canal_data[2],
            'comissao_vigente': comissao_vigente
        }
        
        # Buscar regionais do canal
        cursor.execute("""
            SELECT r.id, r.nome, COUNT(DISTINCT l.id) as total_lojas
            FROM regionais r
            LEFT JOIN vendedores v ON r.id = v.regionalId
            LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE r.canalId = %s
            GROUP BY r.id, r.nome
            ORDER BY r.nome
        """, [canal_id])
        
        regionais = []
        for row in cursor.fetchall():
            regionais.append({
                'id': row[0],
                'nome': row[1],
                'total_lojas': row[2] or 0
            })
        
        # Estatísticas do canal
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT r.id) as total_regionais,
                COUNT(DISTINCT v.id) as total_vendedores,
                COUNT(DISTINCT g.id) as total_grupos,
                COUNT(DISTINCT l.id) as total_lojas
            FROM canal c
            LEFT JOIN regionais r ON c.id = r.canalId
            LEFT JOIN vendedores v ON r.id = v.regionalId
            LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE c.id = %s
        """, [canal_id])
        
        stats = cursor.fetchone()
        estatisticas = {
            'regionais': stats[0] or 0,
            'vendedores': stats[1] or 0,
            'grupos': stats[2] or 0,
            'lojas': stats[3] or 0
        }
    
    context = {
        'canal': canal,
        'regionais': regionais,
        'estatisticas': estatisticas,
    }
    
    return render(request, 'portais/admin/canal_detail.html', context)


@require_admin_access
def canal_edit_comissao(request, canal_id):
    """Editar comissão do canal com controle de vigência"""
    
    if request.method == 'POST':
        nova_comissao = request.POST.get('comissao', '').strip()
        
        if not nova_comissao:
            messages.error(request, 'Comissão é obrigatória.')
        else:
            try:
                from decimal import Decimal, ROUND_HALF_UP
                nova_comissao = Decimal(nova_comissao.replace(',', '.')) / Decimal('100')
                nova_comissao = nova_comissao.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)
                
                with connection.cursor() as cursor:
                    # Buscar comissão vigente atual
                    cursor.execute("""
                        SELECT id, comissao
                        FROM canal_comissao 
                        WHERE canal_id = %s 
                        AND (vigencia_fim IS NULL OR vigencia_fim >= CURDATE())
                        AND vigencia_inicio <= CURDATE()
                        ORDER BY vigencia_inicio DESC
                        LIMIT 1
                    """, [canal_id])
                    
                    comissao_atual = cursor.fetchone()
                    
                    if comissao_atual and Decimal(str(comissao_atual[1])) == nova_comissao:
                        messages.warning(request, 'A comissão informada é igual à vigente atual.')
                    else:
                        # Encerrar vigência atual se existir
                        if comissao_atual:
                            cursor.execute("""
                                UPDATE canal_comissao 
                                SET vigencia_fim = CURDATE() - INTERVAL 1 DAY
                                WHERE id = %s
                            """, [comissao_atual[0]])
                        
                        # Criar nova vigência
                        cursor.execute("""
                            INSERT INTO canal_comissao (canal_id, comissao, vigencia_inicio, vigencia_fim)
                            VALUES (%s, %s, CURDATE(), NULL)
                        """, [canal_id, nova_comissao])
                        
                        messages.success(request, f'Comissão alterada para {nova_comissao * 100:.2f}% com sucesso!')
                        
            except (ValueError, TypeError) as e:
                messages.error(request, 'Valor de comissão inválido.')
            except Exception as e:
                messages.error(request, f'Erro ao alterar comissão: {str(e)}')
    
    return redirect('portais_admin:canal_detail', canal_id=canal_id)


@require_admin_access
def regional_detail(request, regional_id):
    """Detalhes de uma regional específica"""
    
    with connection.cursor() as cursor:
        # Buscar dados da regional e canal
        cursor.execute("""
            SELECT r.id, r.nome, c.id, c.nome, c.marca
            FROM regionais r
            JOIN canal c ON r.canalId = c.id
            WHERE r.id = %s
        """, [regional_id])
        
        regional_data = cursor.fetchone()
        if not regional_data:
            return render(request, 'portais/admin/hierarquia_not_found.html', {
                'tipo': 'Regional',
                'id': regional_id
            })
        
        regional = {
            'id': regional_data[0],
            'nome': regional_data[1],
            'canal': {
                'id': regional_data[2],
                'nome': regional_data[3],
                'marca': regional_data[4]
            }
        }
        
        # Buscar vendedores da regional
        cursor.execute("""
            SELECT v.id, v.nome, COUNT(DISTINCT l.id) as total_lojas
            FROM vendedores v
            LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE v.regionalId = %s
            GROUP BY v.id, v.nome
            ORDER BY v.nome
        """, [regional_id])
        
        vendedores = []
        for row in cursor.fetchall():
            vendedores.append({
                'id': row[0],
                'nome': row[1],
                'total_lojas': row[2] or 0
            })
        
        # Estatísticas da regional
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT v.id) as total_vendedores,
                COUNT(DISTINCT g.id) as total_grupos,
                COUNT(DISTINCT l.id) as total_lojas
            FROM regionais r
            LEFT JOIN vendedores v ON r.id = v.regionalId
            LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE r.id = %s
        """, [regional_id])
        
        stats = cursor.fetchone()
        estatisticas = {
            'vendedores': stats[0] or 0,
            'grupos': stats[1] or 0,
            'lojas': stats[2] or 0
        }
    
    context = {
        'regional': regional,
        'vendedores': vendedores,
        'estatisticas': estatisticas,
    }
    
    return render(request, 'portais/admin/regional_detail.html', context)


@require_admin_access
def vendedor_detail(request, vendedor_id):
    """Detalhes de um vendedor específico"""
    
    with connection.cursor() as cursor:
        # Buscar dados do vendedor, regional e canal
        cursor.execute("""
            SELECT v.id, v.nome, r.id, r.nome, c.id, c.nome, c.marca
            FROM vendedores v
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            WHERE v.id = %s
        """, [vendedor_id])
        
        vendedor_data = cursor.fetchone()
        if not vendedor_data:
            return render(request, 'portais/admin/hierarquia_not_found.html', {
                'tipo': 'Vendedor',
                'id': vendedor_id
            })
        
        vendedor = {
            'id': vendedor_data[0],
            'nome': vendedor_data[1],
            'regional': {
                'id': vendedor_data[2],
                'nome': vendedor_data[3],
                'canal': {
                    'id': vendedor_data[4],
                    'nome': vendedor_data[5],
                    'marca': vendedor_data[6]
                }
            }
        }
        
        # Buscar grupos do vendedor
        cursor.execute("""
            SELECT g.id, g.nome, COUNT(DISTINCT l.id) as total_lojas
            FROM gruposeconomicos g
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE g.vendedorId = %s
            GROUP BY g.id, g.nome
            ORDER BY g.nome
        """, [vendedor_id])
        
        grupos = []
        for row in cursor.fetchall():
            grupos.append({
                'id': row[0],
                'nome': row[1],
                'total_lojas': row[2] or 0
            })
        
        # Estatísticas do vendedor
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT g.id) as total_grupos,
                COUNT(DISTINCT l.id) as total_lojas
            FROM vendedores v
            LEFT JOIN gruposeconomicos g ON v.id = g.vendedorId
            LEFT JOIN loja l ON g.id = l.GrupoEconomicoId
            WHERE v.id = %s
        """, [vendedor_id])
        
        stats = cursor.fetchone()
        estatisticas = {
            'grupos': stats[0] or 0,
            'lojas': stats[1] or 0
        }
    
    context = {
        'vendedor': vendedor,
        'grupos': grupos,
        'estatisticas': estatisticas,
    }
    
    return render(request, 'portais/admin/vendedor_detail.html', context)


@require_admin_access
def grupo_detail(request, grupo_id):
    """Detalhes de um grupo econômico específico"""
    
    with connection.cursor() as cursor:
        # Buscar dados do grupo, vendedor, regional e canal
        cursor.execute("""
            SELECT g.id, g.nome, v.id, v.nome, r.id, r.nome, c.id, c.nome, c.marca
            FROM gruposeconomicos g
            JOIN vendedores v ON g.vendedorId = v.id
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            WHERE g.id = %s
        """, [grupo_id])
        
        grupo_data = cursor.fetchone()
        if not grupo_data:
            return render(request, 'portais/admin/hierarquia_not_found.html', {
                'tipo': 'Grupo Econômico',
                'id': grupo_id
            })
        
        grupo = {
            'id': grupo_data[0],
            'nome': grupo_data[1],
            'vendedor': {
                'id': grupo_data[2],
                'nome': grupo_data[3],
                'regional': {
                    'id': grupo_data[4],
                    'nome': grupo_data[5],
                    'canal': {
                        'id': grupo_data[6],
                        'nome': grupo_data[7],
                        'marca': grupo_data[8]
                    }
                }
            }
        }
        
        # Buscar lojas do grupo
        cursor.execute("""
            SELECT l.id, l.razao_social, l.cnpj
            FROM loja l
            WHERE l.GrupoEconomicoId = %s
            ORDER BY l.razao_social
        """, [grupo_id])
        
        lojas = []
        for row in cursor.fetchall():
            lojas.append({
                'id': row[0],
                'razao_social': row[1],
                'cnpj': row[2]
            })
        
        # Estatísticas do grupo
        cursor.execute("""
            SELECT COUNT(*) as total_lojas
            FROM loja l
            WHERE l.GrupoEconomicoId = %s
        """, [grupo_id])
        
        stats = cursor.fetchone()
        estatisticas = {
            'lojas': stats[0] or 0
        }
    
    context = {
        'grupo': grupo,
        'lojas': lojas,
        'estatisticas': estatisticas,
    }
    
    return render(request, 'portais/admin/grupo_detail.html', context)


@require_admin_access
def loja_detail(request, loja_id):
    """Detalhes de uma loja específica"""
    
    # Validar acesso à loja
    from portais.controle_acesso.filtros import FiltrosAcessoService
    FiltrosAcessoService.validar_acesso_loja_ou_403(request.portal_usuario, loja_id)
    
    with connection.cursor() as cursor:
        # Buscar dados da loja e hierarquia completa
        cursor.execute("""
            SELECT l.id, l.razao_social, l.cnpj,
                   g.id, g.nome, v.id, v.nome, r.id, r.nome, c.id, c.nome, c.marca
            FROM loja l
            JOIN gruposeconomicos g ON l.GrupoEconomicoId = g.id
            JOIN vendedores v ON g.vendedorId = v.id
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            WHERE l.id = %s
        """, [loja_id])
        
        loja_data = cursor.fetchone()
        if not loja_data:
            return render(request, 'portais/admin/hierarquia_not_found.html', {
                'tipo': 'Loja',
                'id': loja_id
            })
        
        loja = {
            'id': loja_data[0],
            'razao_social': loja_data[1],
            'cnpj': loja_data[2],
            'grupo': {
                'id': loja_data[3],
                'nome': loja_data[4],
                'vendedor': {
                    'id': loja_data[5],
                    'nome': loja_data[6],
                    'regional': {
                        'id': loja_data[7],
                        'nome': loja_data[8],
                        'canal': {
                            'id': loja_data[9],
                            'nome': loja_data[10],
                            'marca': loja_data[11]
                        }
                    }
                }
            }
        }
    
    context = {
        'loja': loja,
    }
    
    return render(request, 'portais/admin/loja_detail.html', context)


@require_funcionalidade('hierarquia_create')
def canal_create(request):
    """Criar novo canal"""
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        descricao = request.POST.get('descricao', '').strip()
        username = request.POST.get('username', '').strip()
        keyvalue = request.POST.get('keyvalue', '').strip()
        canal = request.POST.get('canal', '').strip()
        codigo_cliente = request.POST.get('codigo_cliente', '').strip()
        marca = request.POST.get('marca', '').strip()
        json_firebase = request.POST.get('json_firebase', '').strip()
        facebook_url = request.POST.get('facebook_url', '').strip()
        facebook_token = request.POST.get('facebook_token', '').strip()
        logo_pos = request.POST.get('logo_pos', '').strip()
        
        if not nome:
            messages.error(request, 'Nome é obrigatório.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO canal (nome, cnpj, descricao, username, keyvalue, canal, 
                                         codigo_cliente, marca, json_firebase, facebook_url, 
                                         facebook_token, logo_pos)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [nome, cnpj or None, descricao or None, username or None, 
                          keyvalue or None, canal or None, codigo_cliente or None, 
                          marca or None, json_firebase or None, facebook_url or None, 
                          facebook_token or None, logo_pos or None])
                
                messages.success(request, f'Canal "{nome}" criado com sucesso!')
                return redirect('portais_admin:hierarquia_geral')
            except Exception as e:
                messages.error(request, f'Erro ao criar canal: {str(e)}')
    
    return render(request, 'portais/admin/canal_create.html')


@require_funcionalidade('hierarquia_create')
def regional_create(request):
    """Criar nova regional"""
    
    # Buscar canais disponíveis
    with connection.cursor() as cursor:
        cursor.execute("SELECT id, nome, marca FROM canal ORDER BY nome")
        canais = [{'id': row[0], 'nome': row[1], 'marca': row[2]} for row in cursor.fetchall()]
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        canal_id = request.POST.get('canal_id')
        
        if not nome or not canal_id:
            messages.error(request, 'Nome e canal são obrigatórios.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO regionais (nome, canalId)
                        VALUES (%s, %s)
                    """, [nome, canal_id])
                
                messages.success(request, f'Regional "{nome}" criada com sucesso!')
                return redirect('portais_admin:hierarquia_geral')
            except Exception as e:
                messages.error(request, f'Erro ao criar regional: {str(e)}')
    
    context = {
        'canais': canais
    }
    
    return render(request, 'portais/admin/regional_create.html', context)


@require_funcionalidade('hierarquia_create')
def vendedor_create(request):
    """Criar novo vendedor"""
    
    # Buscar regionais disponíveis
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.id, r.nome, c.nome as canal_nome
            FROM regionais r
            JOIN canal c ON r.canalId = c.id
            ORDER BY c.nome, r.nome
        """)
        regionais = [{'id': row[0], 'nome': row[1], 'canal_nome': row[2]} for row in cursor.fetchall()]
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        regional_id = request.POST.get('regional_id')
        
        if not nome or not regional_id:
            messages.error(request, 'Nome e regional são obrigatórios.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO vendedores (nome, regionalId)
                        VALUES (%s, %s)
                    """, [nome, regional_id])
                
                messages.success(request, f'Vendedor "{nome}" criado com sucesso!')
                return redirect('portais_admin:hierarquia_geral')
            except Exception as e:
                messages.error(request, f'Erro ao criar vendedor: {str(e)}')
    
    context = {
        'regionais': regionais
    }
    
    return render(request, 'portais/admin/vendedor_create.html', context)


@require_funcionalidade('hierarquia_create')
def grupo_create(request):
    """Criar novo grupo econômico"""
    
    # Buscar vendedores disponíveis
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT v.id, v.nome, r.nome as regional_nome, c.nome as canal_nome
            FROM vendedores v
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            ORDER BY c.nome, r.nome, v.nome
        """)
        vendedores = [{
            'id': row[0], 
            'nome': row[1], 
            'regional_nome': row[2], 
            'canal_nome': row[3]
        } for row in cursor.fetchall()]
    
    if request.method == 'POST':
        nome = request.POST.get('nome', '').strip()
        vendedor_id = request.POST.get('vendedor_id')
        
        if not nome or not vendedor_id:
            messages.error(request, 'Nome e vendedor são obrigatórios.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO gruposeconomicos (nome, vendedorId)
                        VALUES (%s, %s)
                    """, [nome, vendedor_id])
                
                messages.success(request, f'Grupo Econômico "{nome}" criado com sucesso!')
                return redirect('portais_admin:hierarquia_geral')
            except Exception as e:
                messages.error(request, f'Erro ao criar grupo: {str(e)}')
    
    context = {
        'vendedores': vendedores
    }
    
    return render(request, 'portais/admin/grupo_create.html', context)


@require_funcionalidade('hierarquia_create')
def loja_create(request):
    """Criar nova loja"""
    
    # Buscar grupos econômicos disponíveis
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT g.id, g.nome, v.nome as vendedor_nome, 
                   r.nome as regional_nome, c.nome as canal_nome
            FROM gruposeconomicos g
            JOIN vendedores v ON g.vendedorId = v.id
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            ORDER BY c.nome, r.nome, v.nome, g.nome
        """)
        grupos = [{
            'id': row[0], 
            'nome': row[1], 
            'vendedor_nome': row[2],
            'regional_nome': row[3], 
            'canal_nome': row[4]
        } for row in cursor.fetchall()]
    
    if request.method == 'POST':
        razao_social = request.POST.get('razao_social', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        complemento = request.POST.get('complemento', '').strip()
        canal_id = request.POST.get('canal_id', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '').strip()
        cod_cliente = request.POST.get('cod_cliente', '').strip()
        celular = request.POST.get('celular', '').strip()
        aceite = 0  # Sempre criado com 0
        nomebanco = request.POST.get('nomebanco', '').strip()
        numerobanco = request.POST.get('numerobanco', '').strip()
        agencia = request.POST.get('agencia', '').strip()
        conta = request.POST.get('conta', '').strip()
        pix = request.POST.get('pix', '').strip()
        grupo_id = request.POST.get('GrupoEconomicoId')
        
        if not grupo_id:
            messages.error(request, 'Grupo econômico é obrigatório.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO loja (razao_social, cnpj, complemento, canal_id, email, senha, 
                                        cod_cliente, celular, aceite, nomebanco, numerobanco, 
                                        agencia, conta, pix, GrupoEconomicoId)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, [razao_social or None, cnpj or None, complemento or None, 
                          int(canal_id) if canal_id else None, email or None, senha or None, 
                          cod_cliente or None, celular or None, int(aceite), 
                          nomebanco or None, numerobanco or None, agencia or None, 
                          conta or None, pix or None, grupo_id])
                
                messages.success(request, f'Loja "{razao_social or "Nova Loja"}" criada com sucesso!')
                return redirect('portais_admin:hierarquia_geral')
            except Exception as e:
                messages.error(request, f'Erro ao criar loja: {str(e)}')
    
    context = {
        'grupos': grupos
    }
    
    return render(request, 'portais/admin/loja_create.html', context)


@require_funcionalidade('hierarquia_edit')
def loja_edit(request, loja_id):
    """Editar loja existente"""
    
    # Buscar dados da loja
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, razao_social, cnpj, complemento, canal_id, email, senha,
                   cod_cliente, celular, aceite, nomebanco, numerobanco,
                   agencia, conta, pix, GrupoEconomicoId
            FROM loja
            WHERE id = %s
        """, [loja_id])
        
        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Loja não encontrada.')
            return redirect('portais_admin:hierarquia_geral')
        
        loja = {
            'id': row[0], 'razao_social': row[1], 'cnpj': row[2],
            'complemento': row[3], 'canal_id': row[4], 'email': row[5],
            'senha': row[6], 'cod_cliente': row[7], 'celular': row[8],
            'aceite': row[9], 'nomebanco': row[10], 'numerobanco': row[11],
            'agencia': row[12], 'conta': row[13], 'pix': row[14],
            'GrupoEconomicoId': row[15]
        }
    
    # Buscar grupos econômicos disponíveis
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT g.id, g.nome, v.nome as vendedor_nome, 
                   r.nome as regional_nome, c.nome as canal_nome
            FROM gruposeconomicos g
            JOIN vendedores v ON g.vendedorId = v.id
            JOIN regionais r ON v.regionalId = r.id
            JOIN canal c ON r.canalId = c.id
            ORDER BY c.nome, r.nome, v.nome, g.nome
        """)
        grupos = [{
            'id': row[0], 
            'nome': row[1], 
            'vendedor_nome': row[2],
            'regional_nome': row[3], 
            'canal_nome': row[4]
        } for row in cursor.fetchall()]
    
    if request.method == 'POST':
        razao_social = request.POST.get('razao_social', '').strip()
        cnpj = request.POST.get('cnpj', '').strip()
        complemento = request.POST.get('complemento', '').strip()
        canal_id = request.POST.get('canal_id', '').strip()
        email = request.POST.get('email', '').strip()
        senha = request.POST.get('senha', '').strip()
        cod_cliente = request.POST.get('cod_cliente', '').strip()
        celular = request.POST.get('celular', '').strip()
        aceite = 0  # Sempre mantém 0
        nomebanco = request.POST.get('nomebanco', '').strip()
        numerobanco = request.POST.get('numerobanco', '').strip()
        agencia = request.POST.get('agencia', '').strip()
        conta = request.POST.get('conta', '').strip()
        pix = request.POST.get('pix', '').strip()
        grupo_id = request.POST.get('GrupoEconomicoId')
        
        if not grupo_id:
            messages.error(request, 'Grupo econômico é obrigatório.')
        else:
            try:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE loja SET
                            razao_social = %s, cnpj = %s, complemento = %s, canal_id = %s,
                            email = %s, senha = %s, cod_cliente = %s, celular = %s,
                            aceite = %s, nomebanco = %s, numerobanco = %s, agencia = %s,
                            conta = %s, pix = %s, GrupoEconomicoId = %s
                        WHERE id = %s
                    """, [razao_social or None, cnpj or None, complemento or None,
                          int(canal_id) if canal_id else None, email or None, senha or None,
                          cod_cliente or None, celular or None, int(aceite),
                          nomebanco or None, numerobanco or None, agencia or None,
                          conta or None, pix or None, grupo_id, loja_id])
                
                messages.success(request, f'Loja "{razao_social or "Loja"}" atualizada com sucesso!')
                return redirect('portais_admin:loja_detail', loja_id=loja_id)
            except Exception as e:
                messages.error(request, f'Erro ao atualizar loja: {str(e)}')
    
    context = {
        'grupos': grupos,
        'loja': loja,
        'edit_mode': True
    }
    
    return render(request, 'portais/admin/loja_edit.html', context)
