from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import connection, transaction
from ..controle_acesso.decorators import require_admin_access
from portais.controle_acesso import require_funcionalidade
from wallclub_core.utilitarios.log_control import registrar_log


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
            SELECT l.id, l.razao_social, l.cnpj, l.canal_id,
                   g.id, g.nome, v.id, v.nome, r.id, r.nome, c.id, c.nome, c.marca
            FROM loja l
            LEFT JOIN gruposeconomicos g ON l.GrupoEconomicoId = g.id
            LEFT JOIN vendedores v ON g.vendedorId = v.id
            LEFT JOIN regionais r ON v.regionalId = r.id
            LEFT JOIN canal c ON r.canalId = c.id
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
            'canal_id': loja_data[3],
            'grupo': {
                'id': loja_data[4],
                'nome': loja_data[5],
                'vendedor': {
                    'id': loja_data[6],
                    'nome': loja_data[7],
                    'regional': {
                        'id': loja_data[8],
                        'nome': loja_data[9],
                        'canal': {
                            'id': loja_data[10],
                            'nome': loja_data[11],
                            'marca': loja_data[12]
                        }
                    }
                }
            } if loja_data[4] else None
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
    """Criar nova loja com integração Own Financial"""
    from adquirente_own.services_cadastro import CadastroOwnService
    from adquirente_own.models_cadastro import LojaOwn
    from wallclub_core.utilitarios.log_control import registrar_log

    if request.method == 'GET':
        # Buscar canais disponíveis
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, nome
                FROM canal
                ORDER BY nome
            """)
            canais = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

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

        context = {
            'canais': canais,
            'grupos': grupos
        }
        return render(request, 'portais/admin/loja_create.html', context)

    # POST - processar cadastro
    try:
        with transaction.atomic():
            # Extrair dados do formulário
            razao_social = request.POST.get('razao_social', '').strip()
            cnpj = request.POST.get('cnpj', '').strip()
            nome_fantasia = request.POST.get('nome_fantasia', '').strip()
            complemento = request.POST.get('complemento', '').strip()
            canal_id = request.POST.get('canal_id', '').strip()
            gateway_ativo = request.POST.get('gateway_ativo', 'PINBANK').strip()
            email = request.POST.get('email', '').strip()
            url_loja = request.POST.get('url_loja', '').strip()

            # Contato
            ddd_telefone_comercial = request.POST.get('ddd_telefone_comercial', '').strip()
            telefone_comercial = request.POST.get('telefone_comercial', '').strip()
            ddd_celular = request.POST.get('ddd_celular', '').strip()
            celular = request.POST.get('celular', '').strip()

            # Endereço
            cep = request.POST.get('cep', '').strip()
            logradouro = request.POST.get('logradouro', '').strip()
            numero_endereco = request.POST.get('numero_endereco', '').strip()
            bairro = request.POST.get('bairro', '').strip()
            municipio = request.POST.get('municipio', '').strip()
            uf = request.POST.get('uf', '').strip()

            # Dados bancários
            codigo_banco = request.POST.get('codigo_banco', '').strip()
            agencia = request.POST.get('agencia', '').strip()
            digito_agencia = request.POST.get('digito_agencia', '').strip()
            numero_conta = request.POST.get('numero_conta', '').strip()
            digito_conta = request.POST.get('digito_conta', '').strip()
            pix = request.POST.get('pix', '').strip()

            # Hierarquia
            grupo_id = request.POST.get('GrupoEconomicoId')

            # Dados Own (opcionais)
            cnae = request.POST.get('cnae', '').strip()
            mcc = request.POST.get('mcc', '').strip()
            ramo_atividade = request.POST.get('ramo_atividade', '').strip()
            faturamento_previsto = request.POST.get('faturamento_previsto', '').strip()
            faturamento_contratado = request.POST.get('faturamento_contratado', '').strip()
            quantidade_pos = request.POST.get('quantidade_pos', '1').strip()
            antecipacao_automatica = request.POST.get('antecipacao_automatica', 'N').strip()
            taxa_antecipacao = request.POST.get('taxa_antecipacao', '0').strip()
            responsavel_assinatura = request.POST.get('responsavel_assinatura', '').strip()
            responsavel_assinatura_cpf = request.POST.get('responsavel_assinatura_cpf', '').strip()
            responsavel_assinatura_email = request.POST.get('responsavel_assinatura_email', '').strip()
            aceita_ecommerce = request.POST.get('aceita_ecommerce') == '1'

            if not grupo_id:
                messages.error(request, 'Grupo econômico é obrigatório.')
                return redirect('portais_admin:loja_create')
            elif not canal_id:
                messages.error(request, 'Canal é obrigatório.')
                return redirect('portais_admin:loja_create')

            # Inserir loja na tabela principal (sem campos Own)
            with connection.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO loja (
                        razao_social, nome_fantasia, cnpj, complemento, canal_id, gateway_ativo,
                        email, url_loja, ddd_telefone_comercial, telefone_comercial,
                        ddd_celular, celular, cep, logradouro, numero_endereco,
                        bairro, municipio, uf, codigo_banco, agencia, digito_agencia,
                        numero_conta, digito_conta, pix, GrupoEconomicoId
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, [
                    razao_social or None, nome_fantasia or None, cnpj or None, complemento or None,
                    int(canal_id), gateway_ativo,
                    email or None, url_loja or None, ddd_telefone_comercial or None, telefone_comercial or None,
                    ddd_celular or None, celular or None, cep or None, logradouro or None, numero_endereco or None,
                    bairro or None, municipio or None, uf or None, codigo_banco or None, agencia or None, digito_agencia or None,
                    numero_conta or None, digito_conta or None, pix or None, int(grupo_id)
                ])

                # Obter ID da loja criada
                cursor.execute("SELECT LAST_INSERT_ID()")
                loja_id = cursor.fetchone()[0]

            # Criar/atualizar registro loja_own com campos Own
            from adquirente_own.models_cadastro import LojaOwn

            # Função para converter formato brasileiro para float
            def converter_valor_br(valor_str):
                if not valor_str or valor_str == 'N/A':
                    return None
                # Remove pontos (separador de milhar) e substitui vírgula por ponto
                return float(valor_str.replace('.', '').replace(',', '.'))

            loja_own, created = LojaOwn.objects.get_or_create(loja_id=loja_id)
            loja_own.cnae = cnae or None
            loja_own.ramo_atividade = ramo_atividade or None
            loja_own.mcc = mcc or None
            loja_own.faturamento_previsto = converter_valor_br(faturamento_previsto)
            loja_own.faturamento_contratado = converter_valor_br(faturamento_contratado)
            loja_own.quantidade_pos = int(quantidade_pos) if quantidade_pos else 0
            loja_own.antecipacao_automatica = antecipacao_automatica or 'N'
            loja_own.taxa_antecipacao = converter_valor_br(taxa_antecipacao) or 0.00
            loja_own.tipo_antecipacao = 'ROTATIVO'
            loja_own.responsavel_assinatura = responsavel_assinatura or None
            loja_own.responsavel_assinatura_cpf = responsavel_assinatura_cpf or None
            loja_own.responsavel_assinatura_email = responsavel_assinatura_email or None
            loja_own.aceita_ecommerce = aceita_ecommerce
            loja_own.save()

            # Processar upload de documentos do responsável e da empresa
            from adquirente_own.models_cadastro import LojaDocumentos
            import os
            from django.core.files.storage import default_storage

            if responsavel_assinatura_cpf:
                # RG ou CNH - Frente
                if 'doc_rg_frente' in request.FILES:
                    arquivo = request.FILES['doc_rg_frente']
                    caminho = f'documentos/loja_{loja_id}/rg_frente_{arquivo.name}'
                    caminho_salvo = default_storage.save(caminho, arquivo)

                    LojaDocumentos.objects.create(
                        loja_id=loja_id,
                        tipo_documento='RGFRENTE',
                        nome_arquivo=arquivo.name,
                        caminho_arquivo=caminho_salvo,
                        tamanho_bytes=arquivo.size,
                        mime_type=arquivo.content_type,
                        cpf_socio=responsavel_assinatura_cpf,
                        nome_socio=responsavel_assinatura,
                        ativo=True
                    )

                # RG ou CNH - Verso
                if 'doc_rg_verso' in request.FILES:
                    arquivo = request.FILES['doc_rg_verso']
                    caminho = f'documentos/loja_{loja_id}/rg_verso_{arquivo.name}'
                    caminho_salvo = default_storage.save(caminho, arquivo)

                    LojaDocumentos.objects.create(
                        loja_id=loja_id,
                        tipo_documento='RGVERSO',
                        nome_arquivo=arquivo.name,
                        caminho_arquivo=caminho_salvo,
                        tamanho_bytes=arquivo.size,
                        mime_type=arquivo.content_type,
                        cpf_socio=responsavel_assinatura_cpf,
                        nome_socio=responsavel_assinatura,
                        ativo=True
                    )

                # Comprovante de Residência do Sócio
                if 'doc_comprovante_residencia_socio' in request.FILES:
                    arquivo = request.FILES['doc_comprovante_residencia_socio']
                    caminho = f'documentos/loja_{loja_id}/comprovante_residencia_socio_{arquivo.name}'
                    caminho_salvo = default_storage.save(caminho, arquivo)

                    LojaDocumentos.objects.create(
                        loja_id=loja_id,
                        tipo_documento='COMPROVANTE_ENDERECO',
                        nome_arquivo=arquivo.name,
                        caminho_arquivo=caminho_salvo,
                        tamanho_bytes=arquivo.size,
                        mime_type=arquivo.content_type,
                        cpf_socio=responsavel_assinatura_cpf,
                        nome_socio=responsavel_assinatura,
                        ativo=True
                    )

            # Documentos da Empresa
            # Contrato Social
            if 'doc_contrato_social' in request.FILES:
                arquivo = request.FILES['doc_contrato_social']
                caminho = f'documentos/loja_{loja_id}/contrato_social_{arquivo.name}'
                caminho_salvo = default_storage.save(caminho, arquivo)

                LojaDocumentos.objects.create(
                    loja_id=loja_id,
                    tipo_documento='CONTRATO_SOCIAL',
                    nome_arquivo=arquivo.name,
                    caminho_arquivo=caminho_salvo,
                    tamanho_bytes=arquivo.size,
                    mime_type=arquivo.content_type,
                    ativo=True
                )

            # Comprovante de Endereço da Empresa
            if 'doc_comprovante_endereco_empresa' in request.FILES:
                arquivo = request.FILES['doc_comprovante_endereco_empresa']
                caminho = f'documentos/loja_{loja_id}/comprovante_endereco_empresa_{arquivo.name}'
                caminho_salvo = default_storage.save(caminho, arquivo)

                LojaDocumentos.objects.create(
                    loja_id=loja_id,
                    tipo_documento='COMPROVANTE_ENDERECO',
                    nome_arquivo=arquivo.name,
                    caminho_arquivo=caminho_salvo,
                    tamanho_bytes=arquivo.size,
                    mime_type=arquivo.content_type,
                    ativo=True
                )

            # Verificar se deve cadastrar na Own
            cadastrar_own = request.POST.get('cadastrar_own') == '1'

            registrar_log('admin.hierarquia', f'📋 Checkbox cadastrar_own: {cadastrar_own} (valor POST: {request.POST.get("cadastrar_own")})')

            if cadastrar_own:
                # Verificar se aceita e-commerce
                aceita_ecommerce = request.POST.get('aceita_ecommerce') == '1'

                # Verificar modelo de tarifação
                modelo_tarifacao = request.POST.get('modelo_tarifacao', 'FLEX')

                if modelo_tarifacao == 'FLEX':
                    # Coletar tarifas editadas do formulário
                    total_tarifas = int(request.POST.get('total_tarifas', 0))
                    tarifacao = []
                    cestas_ids_set = set()

                    for i in range(total_tarifas):
                        tarifa_id = request.POST.get(f'tarifa_id_{i}')
                        tarifa_valor = request.POST.get(f'tarifa_valor_{i}')
                        tarifa_cesta_id = request.POST.get(f'tarifa_cesta_id_{i}')

                        if tarifa_id and tarifa_valor:
                            tarifacao.append({
                                'id': int(tarifa_id),
                                'valor': float(tarifa_valor)
                            })
                            if tarifa_cesta_id:
                                cestas_ids_set.add(int(tarifa_cesta_id))

                    cestas_ids = list(cestas_ids_set)
                    antecipacao_automatica = 'N'
                    taxa_antecipacao = 0

                    registrar_log('admin.hierarquia',
                        f'📊 Modelo FLEX: {len(tarifacao)} tarifas de {len(cestas_ids)} cestas '
                        f'(E-commerce: {"SIM" if aceita_ecommerce else "NÃO"})')
                else:
                    # Modelo MDR - coletar tarifas editadas do formulário (cestas 117 e 1608)
                    total_tarifas = int(request.POST.get('total_tarifas', 0))
                    tarifacao = []
                    cestas_ids_set = set()

                    for i in range(total_tarifas):
                        tarifa_id = request.POST.get(f'tarifa_id_{i}')
                        tarifa_valor = request.POST.get(f'tarifa_valor_{i}')
                        tarifa_cesta_id = request.POST.get(f'tarifa_cesta_id_{i}')

                        if tarifa_id and tarifa_valor:
                            tarifacao.append({
                                'id': int(tarifa_id),
                                'valor': float(tarifa_valor)
                            })
                            if tarifa_cesta_id:
                                cestas_ids_set.add(int(tarifa_cesta_id))

                    cestas_ids = list(cestas_ids_set)
                    antecipacao_automatica = request.POST.get('antecipacao_automatica', 'N')
                    taxa_antecipacao = 1.1 if antecipacao_automatica == 'S' else 0

                    registrar_log('admin.hierarquia',
                        f'📊 Modelo MDR: {len(tarifacao)} tarifas de {len(cestas_ids)} cestas '
                        f'(E-commerce: {"SIM" if aceita_ecommerce else "NÃO"})')

                # Montar dados para Own
                loja_data = {
                    'loja_id': loja_id,
                    'cnpj': cnpj,
                    'razao_social': razao_social,
                    'nome_fantasia': nome_fantasia,
                    'email': email,
                    'ddd_telefone_comercial': ddd_telefone_comercial,
                    'telefone_comercial': telefone_comercial,
                    'ddd_celular': ddd_celular,
                    'celular': celular,
                    'cep': cep,
                    'logradouro': logradouro,
                    'numero_endereco': numero_endereco,
                    'complemento': complemento,
                    'bairro': bairro,
                    'municipio': municipio,
                    'uf': uf,
                    'codigo_banco': codigo_banco,
                    'agencia': agencia,
                    'digito_agencia': digito_agencia,
                    'numero_conta': numero_conta,
                    'digito_conta': digito_conta,
                    'cnae': cnae,
                    'mcc': mcc,
                    'ramo_atividade': ramo_atividade,
                    'faturamento_previsto': faturamento_previsto,
                    'faturamento_contratado': faturamento_contratado,
                    'responsavel_assinatura': responsavel_assinatura,
                    'responsavel_assinatura_cpf': responsavel_assinatura_cpf,
                    'responsavel_assinatura_email': responsavel_assinatura_email,
                    'quantidade_pos': quantidade_pos,
                    'antecipacao_automatica': antecipacao_automatica,
                    'taxa_antecipacao': taxa_antecipacao,
                    'tipo_antecipacao': 'ROTATIVO',
                    'aceita_ecommerce': aceita_ecommerce,
                    'tarifacao': tarifacao,
                    'cestas_ids': cestas_ids
                }

                registrar_log('admin.hierarquia', f'🔄 Iniciando cadastro Own para loja {loja_id} - {razao_social}')
                registrar_log('admin.hierarquia', f'📋 Dados: CNPJ={cnpj}, Responsável={responsavel_assinatura}, CPF={responsavel_assinatura_cpf}, Email={responsavel_assinatura_email}')

                # Cadastrar na Own
                service = CadastroOwnService(environment='LIVE')
                resultado = service.cadastrar_estabelecimento(loja_id, loja_data)

                registrar_log('admin.hierarquia', f'📊 Resultado do cadastro Own: {resultado}')

                if resultado.get('sucesso'):
                    messages.success(
                        request,
                        f'✅ Loja "{razao_social}" criada e cadastrada na Own Financial! Protocolo: {resultado.get("protocolo")}'
                    )
                else:
                    messages.error(
                        request,
                        f'⚠️ Loja "{razao_social}" criada, mas houve ERRO ao cadastrar na Own Financial: {resultado.get("mensagem")}'
                    )
            else:
                # Checkbox não marcado - avisar que não foi enviado para Own
                messages.warning(
                    request,
                    f'⚠️ Loja "{razao_social}" criada com sucesso, mas NÃO foi enviada para cadastro na Own Financial. '
                    f'Para cadastrar na Own, edite a loja e marque o checkbox "Cadastrar esta loja na Own Financial".'
                )

            return redirect('portais_admin:hierarquia_geral')

    except Exception as e:
        registrar_log('admin.hierarquia', f'❌ Erro ao criar loja: {str(e)}', nivel='ERROR')
        messages.error(request, f'Erro ao criar loja: {str(e)}')
        return redirect('portais_admin:loja_create')


@require_funcionalidade('hierarquia_edit')
def loja_edit(request, loja_id):
    """Editar loja existente com integração Own Financial"""
    from adquirente_own.models_cadastro import LojaOwn
    from adquirente_own.services_cadastro import CadastroOwnService
    from wallclub_core.utilitarios.log_control import registrar_log

    # Buscar dados completos da loja (sem campos Own)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, razao_social, nome_fantasia, cnpj, complemento, canal_id, gateway_ativo,
                   email, url_loja, ddd_telefone_comercial, telefone_comercial,
                   ddd_celular, celular, cep, logradouro, numero_endereco,
                   bairro, municipio, uf, codigo_banco, agencia, digito_agencia,
                   numero_conta, digito_conta, pix, GrupoEconomicoId,
                   nomebanco, numerobanco, conta
            FROM loja
            WHERE id = %s
        """, [loja_id])

        row = cursor.fetchone()
        if not row:
            messages.error(request, 'Loja não encontrada.')
            return redirect('portais_admin:hierarquia_geral')

        loja = {
            'id': row[0], 'razao_social': row[1], 'nome_fantasia': row[2], 'cnpj': row[3],
            'complemento': row[4], 'canal_id': row[5], 'gateway_ativo': row[6],
            'email': row[7], 'url_loja': row[8], 'ddd_telefone_comercial': row[9], 'telefone_comercial': row[10],
            'ddd_celular': row[11], 'celular': row[12], 'cep': row[13], 'logradouro': row[14], 'numero_endereco': row[15],
            'bairro': row[16], 'municipio': row[17], 'uf': row[18], 'codigo_banco': row[19], 'agencia': row[20], 'digito_agencia': row[21],
            'numero_conta': row[22], 'digito_conta': row[23], 'pix': row[24], 'GrupoEconomicoId': row[25],
            'nomebanco': row[26], 'numerobanco': row[27], 'conta': row[28]
        }

    # Buscar dados Own da loja
    try:
        loja_own = LojaOwn.objects.get(loja_id=loja_id)

        # Sincronizar dados cadastrais da Own (se loja tem credenciamento)
        if loja_own and loja_own.protocolo:
            from adquirente_own.services_consultas import ConsultasOwnService
            service = ConsultasOwnService(environment='LIVE')
            resultado_sync = service.sincronizar_dados_cadastrais(loja_id=loja_id)

            if resultado_sync.get('sucesso'):
                registrar_log('portais_admin', f'✅ Dados Own sincronizados para loja {loja_id}')
                # Recarregar loja_own após sincronização
                loja_own = LojaOwn.objects.get(loja_id=loja_id)
            else:
                registrar_log('portais_admin', f'⚠️ Falha ao sincronizar dados Own: {resultado_sync.get("mensagem")}', nivel='WARNING')

    except LojaOwn.DoesNotExist:
        loja_own = None

    # Buscar canais disponíveis
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT id, nome
            FROM canal
            ORDER BY nome
        """)
        canais = [{'id': row[0], 'nome': row[1]} for row in cursor.fetchall()]

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

    if request.method == 'GET':
        context = {
            'loja': loja,
            'loja_own': loja_own,
            'canais': canais,
            'grupos': grupos
        }
        return render(request, 'portais/admin/loja_edit.html', context)

    # POST - processar edição
    if request.method == 'POST':
        # Dados básicos
        razao_social = request.POST.get('razao_social', '').strip()
        nome_fantasia = request.POST.get('nome_fantasia', '').strip()
        cnpj_raw = request.POST.get('cnpj', '').strip()
        cnpj = ''.join(filter(str.isdigit, cnpj_raw)) if cnpj_raw else ''
        complemento = request.POST.get('complemento', '').strip()
        canal_id = request.POST.get('canal_id', '').strip()
        gateway_ativo = request.POST.get('gateway_ativo', 'PINBANK').strip()

        # Contato
        email = request.POST.get('email', '').strip()
        url_loja = request.POST.get('url_loja', '').strip()
        ddd_telefone_comercial = request.POST.get('ddd_telefone_comercial', '').strip()
        telefone_comercial = request.POST.get('telefone_comercial', '').strip()
        ddd_celular = request.POST.get('ddd_celular', '').strip()
        celular = request.POST.get('celular', '').strip()

        # Endereço
        cep = request.POST.get('cep', '').strip()
        logradouro = request.POST.get('logradouro', '').strip()
        numero_endereco = request.POST.get('numero_endereco', '').strip()
        bairro = request.POST.get('bairro', '').strip()
        municipio = request.POST.get('municipio', '').strip()
        uf = request.POST.get('uf', '').strip()

        # Dados bancários
        codigo_banco = request.POST.get('codigo_banco', '').strip()
        agencia = request.POST.get('agencia', '').strip()
        digito_agencia = request.POST.get('digito_agencia', '').strip()
        numero_conta = request.POST.get('numero_conta', '').strip()
        digito_conta = request.POST.get('digito_conta', '').strip()
        pix = request.POST.get('pix', '').strip()

        # Hierarquia
        grupo_id = request.POST.get('GrupoEconomicoId')

        # Campos Own Financial
        cnae = request.POST.get('cnae', '').strip()
        mcc = request.POST.get('mcc', '').strip()
        ramo_atividade = request.POST.get('ramo_atividade', '').strip()
        faturamento_previsto = request.POST.get('faturamento_previsto', '').strip()
        faturamento_contratado = request.POST.get('faturamento_contratado', '').strip()
        antecipacao_automatica = request.POST.get('antecipacao_automatica', 'N').strip()
        tipo_antecipacao = request.POST.get('tipo_antecipacao', 'ROTATIVO').strip()
        responsavel_assinatura = request.POST.get('responsavel_assinatura', '').strip()
        responsavel_assinatura_cpf = request.POST.get('responsavel_assinatura_cpf', '').strip()
        responsavel_assinatura_email = request.POST.get('responsavel_assinatura_email', '').strip()
        aceita_ecommerce = request.POST.get('aceita_ecommerce') == '1'
        cadastrar_own = request.POST.get('cadastrar_own') == '1'

        # Validações
        if not cnpj:
            messages.error(request, 'CNPJ/CPF é obrigatório.')
        elif len(cnpj) not in [11, 14]:
            messages.error(request, 'CNPJ/CPF inválido. Deve ter 11 (CPF) ou 14 (CNPJ) dígitos.')
        elif not grupo_id:
            messages.error(request, 'Grupo econômico é obrigatório.')
        else:
            try:
                # Verificar se CNPJ já existe em outra loja
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT id FROM loja WHERE cnpj = %s AND id != %s
                    """, [cnpj, loja_id])
                    if cursor.fetchone():
                        messages.error(request, f'CNPJ/CPF {cnpj_raw} já está cadastrado em outra loja.')
                        return render(request, 'portais/admin/loja_edit.html', {
                            'grupos': grupos,
                            'loja': loja,
                            'edit_mode': True
                        })

                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            UPDATE loja SET
                                razao_social = %s, nome_fantasia = %s, cnpj = %s, complemento = %s,
                                canal_id = %s, gateway_ativo = %s,
                                email = %s, url_loja = %s,
                                ddd_telefone_comercial = %s, telefone_comercial = %s,
                                ddd_celular = %s, celular = %s,
                                cep = %s, logradouro = %s, numero_endereco = %s,
                                bairro = %s, municipio = %s, uf = %s,
                                codigo_banco = %s, agencia = %s, digito_agencia = %s,
                                numero_conta = %s, digito_conta = %s, pix = %s,
                                GrupoEconomicoId = %s
                            WHERE id = %s
                        """, [
                            razao_social or None, nome_fantasia or None, cnpj, complemento or None,
                            int(canal_id) if canal_id else None, gateway_ativo,
                            email or None, url_loja or None,
                            ddd_telefone_comercial or None, telefone_comercial or None,
                            ddd_celular or None, celular or None,
                            cep or None, logradouro or None, int(numero_endereco) if numero_endereco else None,
                            bairro or None, municipio or None, uf or None,
                            codigo_banco or None, agencia or None, digito_agencia or None,
                            numero_conta or None, digito_conta or None, pix or None,
                            grupo_id,
                            loja_id
                        ])

                    # Atualizar registro loja_own com campos Own
                    from adquirente_own.models_cadastro import LojaOwn

                    # Função para converter formato brasileiro para float
                    def converter_valor_br(valor_str):
                        if not valor_str or valor_str == 'N/A':
                            return None
                        # Remove pontos (separador de milhar) e substitui vírgula por ponto
                        return float(valor_str.replace('.', '').replace(',', '.'))

                    loja_own, created = LojaOwn.objects.get_or_create(loja_id=loja_id)
                    loja_own.cnae = cnae or None
                    loja_own.ramo_atividade = ramo_atividade or None
                    loja_own.mcc = mcc or None
                    loja_own.faturamento_previsto = converter_valor_br(faturamento_previsto)
                    loja_own.faturamento_contratado = converter_valor_br(faturamento_contratado)
                    loja_own.quantidade_pos = 0  # POS cadastrado via API específica (configuraEquipamento)
                    loja_own.antecipacao_automatica = antecipacao_automatica or 'N'
                    loja_own.tipo_antecipacao = tipo_antecipacao or 'ROTATIVO'
                    loja_own.responsavel_assinatura = responsavel_assinatura or None
                    loja_own.responsavel_assinatura_cpf = responsavel_assinatura_cpf or None
                    loja_own.responsavel_assinatura_email = responsavel_assinatura_email or None
                    loja_own.aceita_ecommerce = aceita_ecommerce
                    loja_own.save()

                    # Processar upload de documentos do responsável e da empresa
                    from adquirente_own.models_cadastro import LojaDocumentos
                    from django.core.files.storage import default_storage

                    if responsavel_assinatura_cpf:
                        # RG ou CNH - Frente
                        if 'doc_rg_frente' in request.FILES:
                            LojaDocumentos.objects.filter(
                                loja_id=loja_id,
                                tipo_documento='RGFRENTE',
                                cpf_socio=responsavel_assinatura_cpf
                            ).update(ativo=False)

                            arquivo = request.FILES['doc_rg_frente']
                            caminho = f'documentos/loja_{loja_id}/rg_frente_{arquivo.name}'
                            caminho_salvo = default_storage.save(caminho, arquivo)

                            LojaDocumentos.objects.create(
                                loja_id=loja_id,
                                tipo_documento='RGFRENTE',
                                nome_arquivo=arquivo.name,
                                caminho_arquivo=caminho_salvo,
                                tamanho_bytes=arquivo.size,
                                mime_type=arquivo.content_type,
                                cpf_socio=responsavel_assinatura_cpf,
                                nome_socio=responsavel_assinatura,
                                ativo=True
                            )

                        # RG ou CNH - Verso
                        if 'doc_rg_verso' in request.FILES:
                            LojaDocumentos.objects.filter(
                                loja_id=loja_id,
                                tipo_documento='RGVERSO',
                                cpf_socio=responsavel_assinatura_cpf
                            ).update(ativo=False)

                            arquivo = request.FILES['doc_rg_verso']
                            caminho = f'documentos/loja_{loja_id}/rg_verso_{arquivo.name}'
                            caminho_salvo = default_storage.save(caminho, arquivo)

                            LojaDocumentos.objects.create(
                                loja_id=loja_id,
                                tipo_documento='RGVERSO',
                                nome_arquivo=arquivo.name,
                                caminho_arquivo=caminho_salvo,
                                tamanho_bytes=arquivo.size,
                                mime_type=arquivo.content_type,
                                cpf_socio=responsavel_assinatura_cpf,
                                nome_socio=responsavel_assinatura,
                                ativo=True
                            )

                        # Comprovante de Residência do Sócio
                        if 'doc_comprovante_residencia_socio' in request.FILES:
                            LojaDocumentos.objects.filter(
                                loja_id=loja_id,
                                tipo_documento='COMPROVANTE_ENDERECO',
                                cpf_socio=responsavel_assinatura_cpf
                            ).update(ativo=False)

                            arquivo = request.FILES['doc_comprovante_residencia_socio']
                            caminho = f'documentos/loja_{loja_id}/comprovante_residencia_socio_{arquivo.name}'
                            caminho_salvo = default_storage.save(caminho, arquivo)

                            LojaDocumentos.objects.create(
                                loja_id=loja_id,
                                tipo_documento='COMPROVANTE_ENDERECO',
                                nome_arquivo=arquivo.name,
                                caminho_arquivo=caminho_salvo,
                                tamanho_bytes=arquivo.size,
                                mime_type=arquivo.content_type,
                                cpf_socio=responsavel_assinatura_cpf,
                                nome_socio=responsavel_assinatura,
                                ativo=True
                            )

                    # Documentos da Empresa
                    # Contrato Social
                    if 'doc_contrato_social' in request.FILES:
                        LojaDocumentos.objects.filter(
                            loja_id=loja_id,
                            tipo_documento='CONTRATO_SOCIAL',
                            cpf_socio__isnull=True
                        ).update(ativo=False)

                        arquivo = request.FILES['doc_contrato_social']
                        caminho = f'documentos/loja_{loja_id}/contrato_social_{arquivo.name}'
                        caminho_salvo = default_storage.save(caminho, arquivo)

                        LojaDocumentos.objects.create(
                            loja_id=loja_id,
                            tipo_documento='CONTRATO_SOCIAL',
                            nome_arquivo=arquivo.name,
                            caminho_arquivo=caminho_salvo,
                            tamanho_bytes=arquivo.size,
                            mime_type=arquivo.content_type,
                            ativo=True
                        )

                    # Comprovante de Endereço da Empresa
                    if 'doc_comprovante_endereco_empresa' in request.FILES:
                        LojaDocumentos.objects.filter(
                            loja_id=loja_id,
                            tipo_documento='COMPROVANTE_ENDERECO',
                            cpf_socio__isnull=True
                        ).update(ativo=False)

                        arquivo = request.FILES['doc_comprovante_endereco_empresa']
                        caminho = f'documentos/loja_{loja_id}/comprovante_endereco_empresa_{arquivo.name}'
                        caminho_salvo = default_storage.save(caminho, arquivo)

                        LojaDocumentos.objects.create(
                            loja_id=loja_id,
                            tipo_documento='COMPROVANTE_ENDERECO',
                            nome_arquivo=arquivo.name,
                            caminho_arquivo=caminho_salvo,
                            tamanho_bytes=arquivo.size,
                            mime_type=arquivo.content_type,
                            ativo=True
                        )

                    # Se checkbox Own marcado, cadastrar ou recadastrar
                    registrar_log('admin.hierarquia', f'📋 Checkbox cadastrar_own: {cadastrar_own} (valor POST: {request.POST.get("cadastrar_own")})')

                    if cadastrar_own:
                        try:
                            # Validar campos obrigatórios para Own

                            if not cnae or not mcc or not ramo_atividade:
                                messages.warning(request, 'Loja atualizada, mas é necessário selecionar um CNAE para cadastrar na Own.')
                                return redirect('portais_admin:loja_detail', loja_id=loja_id)

                            if not faturamento_previsto or not faturamento_contratado:
                                messages.warning(request, 'Loja atualizada, mas é necessário informar os faturamentos para cadastrar na Own.')
                                return redirect('portais_admin:loja_detail', loja_id=loja_id)

                            if not responsavel_assinatura:
                                messages.warning(request, 'Loja atualizada, mas é necessário informar o Responsável pela Assinatura para cadastrar na Own.')
                                return redirect('portais_admin:loja_detail', loja_id=loja_id)

                            # Verificar se aceita e-commerce
                            aceita_ecommerce = request.POST.get('aceita_ecommerce') == '1'

                            # Verificar modelo de tarifação
                            modelo_tarifacao = request.POST.get('modelo_tarifacao', 'FLEX')

                            if modelo_tarifacao == 'FLEX':
                                # Coletar tarifas editadas do formulário
                                total_tarifas = int(request.POST.get('total_tarifas', 0))
                                tarifacao = []
                                cestas_ids_set = set()

                                for i in range(total_tarifas):
                                    tarifa_id = request.POST.get(f'tarifa_id_{i}')
                                    tarifa_valor = request.POST.get(f'tarifa_valor_{i}')
                                    tarifa_cesta_id = request.POST.get(f'tarifa_cesta_id_{i}')

                                    if tarifa_id and tarifa_valor:
                                        tarifacao.append({
                                            'id': int(tarifa_id),
                                            'valor': float(tarifa_valor)
                                        })
                                        if tarifa_cesta_id:
                                            cestas_ids_set.add(int(tarifa_cesta_id))

                                cestas_ids = list(cestas_ids_set)
                                antecipacao_automatica = 'N'

                                registrar_log('admin.hierarquia',
                                    f'📊 Modelo FLEX (edição): {len(tarifacao)} tarifas de {len(cestas_ids)} cestas '
                                    f'(E-commerce: {"SIM" if aceita_ecommerce else "NÃO"})')
                            else:
                                # Modelo MDR - coletar tarifas editadas do formulário (cestas 117 e 1608)
                                total_tarifas = int(request.POST.get('total_tarifas', 0))
                                tarifacao = []
                                cestas_ids_set = set()

                                for i in range(total_tarifas):
                                    tarifa_id = request.POST.get(f'tarifa_id_{i}')
                                    tarifa_valor = request.POST.get(f'tarifa_valor_{i}')
                                    tarifa_cesta_id = request.POST.get(f'tarifa_cesta_id_{i}')

                                    if tarifa_id and tarifa_valor:
                                        tarifacao.append({
                                            'id': int(tarifa_id),
                                            'valor': float(tarifa_valor)
                                        })
                                        if tarifa_cesta_id:
                                            cestas_ids_set.add(int(tarifa_cesta_id))

                                cestas_ids = list(cestas_ids_set)
                                antecipacao_automatica = request.POST.get('antecipacao_automatica', 'N')
                                taxa_antecipacao = 1.1 if antecipacao_automatica == 'S' else 0

                                registrar_log('admin.hierarquia',
                                    f'📊 Modelo MDR (edição): {len(tarifacao)} tarifas de {len(cestas_ids)} cestas '
                                    f'(E-commerce: {"SIM" if aceita_ecommerce else "NÃO"})')

                            loja_data = {
                                'loja_id': loja_id,
                                'razao_social': razao_social,
                                'nome_fantasia': nome_fantasia,
                                'cnpj': cnpj,
                                'email': email,
                                'ddd_telefone_comercial': ddd_telefone_comercial,
                                'telefone_comercial': telefone_comercial,
                                'ddd_celular': ddd_celular,
                                'celular': celular,
                                'cep': cep,
                                'logradouro': logradouro,
                                'numero_endereco': numero_endereco,
                                'complemento': complemento,
                                'bairro': bairro,
                                'municipio': municipio,
                                'uf': uf,
                                'codigo_banco': codigo_banco,
                                'agencia': agencia,
                                'digito_agencia': digito_agencia,
                                'numero_conta': numero_conta,
                                'digito_conta': digito_conta,
                                'cnae': cnae,
                                'mcc': mcc,
                                'ramo_atividade': ramo_atividade,
                                'faturamento_previsto': faturamento_previsto,
                                'faturamento_contratado': faturamento_contratado,
                                'responsavel_assinatura': responsavel_assinatura,
                                'responsavel_assinatura_cpf': responsavel_assinatura_cpf,
                                'responsavel_assinatura_email': responsavel_assinatura_email,
                                'quantidade_pos': 0,
                                'antecipacao_automatica': antecipacao_automatica,
                                'tipo_antecipacao': tipo_antecipacao,
                                'tarifacao': tarifacao,
                                'cestas_ids': cestas_ids,
                                'aceita_ecommerce': aceita_ecommerce,
                                'protocolo': loja_own.protocolo if loja_own else '',
                                'contrato': loja_own.contrato if loja_own else ''
                            }

                            registrar_log('admin.hierarquia', f'🔄 Iniciando cadastro Own para loja {loja_id} - {razao_social}')

                            service = CadastroOwnService()
                            resultado = service.cadastrar_estabelecimento(loja_id, loja_data)

                            registrar_log('admin.hierarquia', f'📊 Resultado do cadastro Own: {resultado}')

                            if resultado.get('sucesso'):
                                messages.success(request, f'✅ Loja "{razao_social}" atualizada e cadastrada na Own Financial! Protocolo: {resultado.get("protocolo")}')
                            else:
                                messages.error(request, f'⚠️ Loja "{razao_social}" atualizada, mas houve ERRO ao cadastrar na Own Financial: {resultado.get("mensagem")}')
                        except Exception as e:
                            registrar_log('admin.hierarquia', f'❌ Erro ao cadastrar loja na Own: {str(e)}', nivel='ERROR')
                            messages.error(request, f'⚠️ Loja atualizada, mas houve ERRO ao cadastrar na Own: {str(e)}')
                    else:
                        # Checkbox não marcado - avisar que não foi enviado para Own
                        messages.warning(
                            request,
                            f'⚠️ Loja "{razao_social}" atualizada com sucesso, mas NÃO foi enviada para cadastro na Own Financial. '
                            f'Para cadastrar na Own, marque o checkbox "Cadastrar esta loja na Own Financial".'
                        )

                return redirect('portais_admin:loja_detail', loja_id=loja_id)
            except Exception as e:
                registrar_log('admin.hierarquia', f'❌ Erro ao atualizar loja: {str(e)}', nivel='ERROR')
                messages.error(request, f'Erro ao atualizar loja: {str(e)}')

    context = {
        'loja': loja,
        'loja_own': loja_own,
        'canais': canais,
        'grupos': grupos
    }

    return render(request, 'portais/admin/loja_edit.html', context)
