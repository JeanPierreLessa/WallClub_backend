"""
Views para terminais no portal lojista.
"""

from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.views import View
from django.http import JsonResponse, HttpResponse
from django.db import connection
from django.contrib import messages
from datetime import datetime, timedelta, date
import json
import csv
import io
from decimal import Decimal

from .mixins import LojistaAccessMixin, LojistaDataMixin


class LojistaTerminaisView(LojistaAccessMixin, LojistaDataMixin, TemplateView):
    """View para página de terminais do lojista"""
    
    template_name = 'portais/lojista/terminais.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obter lojas acessíveis usando mixin
        lojas_acessiveis = self.get_lojas_acessiveis()
        
        context.update({
            'current_page': 'terminais',
            'lojas_acessiveis': lojas_acessiveis,
            'mostrar_filtro_loja': len(lojas_acessiveis) > 1
        })
        
        # Extrair apenas os IDs das lojas para compatibilidade
        if lojas_acessiveis and isinstance(lojas_acessiveis[0], dict):
            ids_lojas = [loja['id'] for loja in lojas_acessiveis]
        else:
            ids_lojas = lojas_acessiveis
        
        # Determinar quais lojas consultar
        # Lógica simplificada - permitir acesso a todas as lojas disponíveis
        # if tipo_usuario in ['vendedor', 'lojista']:
        #     lojas_para_consulta = [ids_lojas[0]] if ids_lojas else []
        # else:
        if True:
            # Usuários com acesso múltiplo: todas as lojas
            lojas_para_consulta = ids_lojas
        
        if not lojas_para_consulta:
            context.update({
                'terminais': [],
                'error': 'Acesso negado'
            })
            return context
        
        # Query para buscar terminais
        sql = """
        SELECT  l.razao_social AS `Lojista`,
                t.terminal AS `Nr_Serie_Terminal`,
                l.complemento AS `Endereco`
        FROM    terminais t
        INNER JOIN loja l ON t.loja_id = l.id
        WHERE   l.id IN %s
        ORDER BY t.inicio
        """
        
        # Executar query
        with connection.cursor() as cursor:
            cursor.execute(sql, [tuple(lojas_para_consulta)])
            columns = [col[0] for col in cursor.description]
            terminais = []
            
            for row in cursor.fetchall():
                terminal_dict = dict(zip(columns, row))
                terminais.append(terminal_dict)
        
        # registrar_log('portais.lojista', f"TERMINAIS - Consulta realizada - {len(terminais)} registros encontrados")
        
        context.update({
            'terminais': terminais,
            'total_terminais': len(terminais)
        })
        
        return context
