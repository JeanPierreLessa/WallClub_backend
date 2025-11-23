#!/usr/bin/env python3
"""
MIGRAÇÃO SIMPLIFICADA - APENAS VERSÕES ATUAIS
WallClub - Parâmetros Financeiros

Baseado nas queries fornecidas pelo usuário que retornam apenas id_desc_ativo.
"""

import os
import sys
import django
import pymysql
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from datetime import datetime

# Configurar Django para PRODUÇÃO
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.models import ParametrosWall


class MigradorAtual:
    def __init__(self):
        self.conn_legado = None
        self.conn_wallclub = None
        
    def conectar_bancos(self):
        """Conecta aos bancos legado (wclub) e novo (wallclub)."""
        try:
            # Banco legado
            self.conn_legado = pymysql.connect(
                host='10.0.1.107',
                user='user_python',
                password='sblYcQ(@p.9',
                database='wclub',
                charset='utf8mb4'
            )
            
            # Banco wallclub
            self.conn_wallclub = pymysql.connect(
                host='10.0.1.107',
                user='user_python',
                password='sblYcQ(@p.9',
                database='wallclub',
                charset='utf8mb4'
            )
            
            print("✅ Conectado aos bancos wclub e wallclub")
        except Exception as e:
            print(f"❌ Erro ao conectar aos bancos: {e}")
            sys.exit(1)
    
    def buscar_lojas_ativas(self):
        """Busca lojas ativas do sistema wallclub."""
        cursor = self.conn_wallclub.cursor()
        
        sql = """
        SELECT id, razao_social
        FROM loja 
        ORDER BY id
        """
        
        cursor.execute(sql)
        lojas = cursor.fetchall()
        cursor.close()
        
        print(f"📊 Encontradas {len(lojas)} lojas ativas")
        return lojas
    
    def buscar_combinacoes_vigencia(self, loja_id, wall_type='S'):
        """
        Busca todas as combinações de vigência para uma loja específica.
        Retorna matriz com todas as datas de mudança e os id_desc ativos em cada período.
        """
        cursor = self.conn_legado.cursor()
        
        # Primeiro buscar o id_estab da loja
        cursor.execute("SELECT id_estab FROM wclub.clientes WHERE id = %s", (loja_id,))
        resultado_estab = cursor.fetchone()
        if not resultado_estab:
            print(f"    ❌ Loja {loja_id} não encontrada na tabela clientes")
            cursor.close()
            return []
        
        id_estab = resultado_estab[0]
        
        # Buscar todas as vigências de cada tipo para a loja
        sql = """
        WITH vigencias AS (
          -- Vigências de parâmetros loja
          SELECT 
            'loja' as tipo,
            r.id_desc,
            r.inicio,
            LEAD(r.inicio, 1, 9999999999) OVER (ORDER BY r.inicio) as fim
          FROM wclub.rel_loja_param r 
          WHERE r.id_cliente = %s
          
          UNION ALL
          
          -- Vigências de parâmetros wall
          SELECT 
            'wall' as tipo,
            r.id_desc,
            r.inicio,
            LEAD(r.inicio, 1, 9999999999) OVER (ORDER BY r.inicio) as fim
          FROM wclub.rel_wall_param r 
          WHERE r.id_estab = %s
          
          UNION ALL
          
          -- Vigências de parâmetros clientef (global)
          SELECT 
            'clientef' as tipo,
            r.id_desc,
            r.inicio,
            LEAD(r.inicio, 1, 9999999999) OVER (ORDER BY r.inicio) as fim
          FROM wclub.rel_clientef_param r
        ),
        periodos AS (
          SELECT DISTINCT inicio as data_mudanca FROM vigencias
          UNION 
          SELECT DISTINCT fim as data_mudanca FROM vigencias WHERE fim < 9999999999
        )
        SELECT 
          p.data_mudanca,
          -- ID_DESC ativo para loja nesta data
          (SELECT v1.id_desc FROM vigencias v1 
           WHERE v1.tipo = 'loja' AND v1.inicio <= p.data_mudanca AND v1.fim > p.data_mudanca
           ORDER BY v1.inicio DESC LIMIT 1) as id_desc_loja,
          -- ID_DESC ativo para wall nesta data  
          (SELECT v2.id_desc FROM vigencias v2 
           WHERE v2.tipo = 'wall' AND v2.inicio <= p.data_mudanca AND v2.fim > p.data_mudanca
           ORDER BY v2.inicio DESC LIMIT 1) as id_desc_wall,
          -- ID_DESC ativo para clientef nesta data
          (SELECT v3.id_desc FROM vigencias v3 
           WHERE v3.tipo = 'clientef' AND v3.inicio <= p.data_mudanca AND v3.fim > p.data_mudanca
           ORDER BY v3.inicio DESC LIMIT 1) as id_desc_clientef
        FROM periodos p
        ORDER BY p.data_mudanca
        """
        
        cursor.execute(sql, (loja_id, id_estab))
        combinacoes = cursor.fetchall()
        cursor.close()
        
        return combinacoes
    
    def buscar_parametros_por_combinacao(self, id_desc_loja, id_desc_wall, id_desc_clientef, wall_type='S'):
        """
        Busca parâmetros para uma combinação específica de id_desc.
        """
        cursor = self.conn_legado.cursor()
        
        plano_filter = "< 1000" if wall_type == 'S' else ">= 1000"
        
        sql = f"""
        SELECT
          -- Parâmetros loja
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', p.id_plano,
                'parametro', p.parametro, 
                'valor', p.valor
              )
            )
            FROM wclub.parametros_loja p
            WHERE p.id_desc = %s AND p.id_plano {plano_filter}
          ) AS parametros_loja_json,
          -- Parâmetros wall
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', pw.id_plano,
                'parametro', pw.parametro, 
                'valor', pw.valor
              )
            )
            FROM wclub.parametros_wall pw
            WHERE pw.id_desc = %s AND pw.id_plano {plano_filter}
          ) AS parametros_wall_json,
          -- Parâmetros clientef
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', pc.id_plano,
                'parametro', pc.parametro, 
                'valor', pc.valor
              )
            )
            FROM wclub.parametros_clientesf pc
            WHERE pc.id_desc = %s AND pc.id_plano {plano_filter}
          ) AS parametros_clientesf_json
        """
        
        cursor.execute(sql, (id_desc_loja, id_desc_wall, id_desc_clientef))
        resultado = cursor.fetchone()
        cursor.close()
        
        return resultado
    
    def buscar_parametros_wall_n_DEPRECATED(self, loja_id):
        """
        Busca parâmetros Wall N (Sem Club) usando query fornecida.
        Adaptada para buscar todos os planos, não apenas plano 1001.
        """
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT
          c.id AS loja_id,
          c.razao_social,
          /* id_desc ativo (mais recente) do cliente */
          (
            SELECT r1.id_desc
            FROM wclub.rel_loja_param r1
            WHERE r1.id_cliente = c.id
            ORDER BY r1.inicio DESC, r1.id DESC
            LIMIT 1
          ) AS id_desc_ativo,
          /* parâmetros desse id_desc para todos os planos Wall N */
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', p.id_plano,
                'parametro', p.parametro, 
                'valor', p.valor
              )
            )
            FROM wclub.parametros_loja p
            WHERE p.id_desc = (
              SELECT r2.id_desc
              FROM wclub.rel_loja_param r2
              WHERE r2.id_cliente = c.id
              ORDER BY r2.inicio DESC, r2.id DESC
              LIMIT 1
            )
            AND p.id_plano >= 1000  -- Wall N
          ) AS parametros_loja_json,
          /* parâmetros wall (antigo parametros_wall) */
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', pw.id_plano,
                'parametro', pw.parametro, 
                'valor', pw.valor
              )
            )
            FROM wclub.parametros_wall pw
            WHERE pw.id_desc = (
              SELECT r3.id_desc
              FROM wclub.rel_wall_param r3
              WHERE r3.id_estab = c.id
              ORDER BY r3.inicio DESC, r3.id DESC
              LIMIT 1
            )
            AND pw.id_plano >= 1000  -- Wall N
          ) AS parametros_wall_json,
          /* parâmetros clientesf (antigo parametros_clientesf) */
          (
            SELECT JSON_ARRAYAGG(
              JSON_OBJECT(
                'id_plano', pc.id_plano,
                'parametro', pc.parametro, 
                'valor', pc.valor
              )
            )
            FROM wclub.parametros_clientesf pc
            WHERE pc.id_desc = (
              SELECT r4.id_desc
              FROM wclub.rel_clientef_param r4
              ORDER BY r4.inicio DESC, r4.id DESC
              LIMIT 1
            )
            AND pc.id_plano >= 1000  -- Wall N
          ) AS parametros_clientesf_json
        FROM wallclub.loja c
        WHERE c.id = %s
        """
        
        cursor.execute(sql, (loja_id,))
        resultado = cursor.fetchone()
        cursor.close()
        
        return resultado
    
    def mapear_plano_legado_para_novo(self, id_plano_legado):
        """
        Mapeia plano do sistema legado para novo sistema.
        
        LÓGICA:
        - Wall S: plano 1 → plano 1, wall='S'
        - Wall N: plano 1001 → plano 1, wall='N'
        """
        if id_plano_legado >= 1000:
            # Sem Wall: 1000 → plano 1, 1001 → plano 2, etc.
            id_plano_novo = id_plano_legado - 999
            wall = 'N'
        else:
            # Com Wall: 1 → plano 1, 2 → plano 2, etc.
            id_plano_novo = id_plano_legado
            wall = 'S'
        
        return id_plano_novo, wall
    
    def limpar_valor(self, valor):
        """Limpa e valida valores dos parâmetros."""
        if valor is None or valor == '':
            return None
        
        valor_str = str(valor).strip()
        
        # Valores inválidos
        valores_invalidos = ['#N/D', 'ND', 'Crédito a Vista', '\\', '-', '', '#VALOR!']
        if valor_str in valores_invalidos:
            return None
        
        try:
            return Decimal(valor_str)
        except (InvalidOperation, ValueError):
            # Para parametro_loja_16 que é texto
            return valor_str if valor_str else None
    
    def processar_parametros_json(self, parametros_json, tipo_parametro):
        """
        Processa JSON de parâmetros e retorna dicionário organizado por plano.
        
        Args:
            parametros_json: JSON string dos parâmetros
            tipo_parametro: 'loja', 'wall', 'clientesf'
            
        Returns:
            dict: {id_plano: {parametro: valor}}
        """
        import json
        
        if not parametros_json:
            return {}
        
        try:
            parametros_list = json.loads(parametros_json)
            if not parametros_list:
                return {}
        except (json.JSONDecodeError, TypeError):
            return {}
        
        # Organizar por plano
        parametros_por_plano = {}
        
        for item in parametros_list:
            id_plano = item['id_plano']
            parametro = item['parametro']
            valor = item['valor']
            
            if id_plano not in parametros_por_plano:
                parametros_por_plano[id_plano] = {}
            
            # Mapear códigos para campos Django
            if tipo_parametro == 'loja':
                # parametros_loja: 1-30 → parametro_loja_X
                if 1 <= parametro <= 30:
                    campo = f'parametro_loja_{parametro}'
                    parametros_por_plano[id_plano][campo] = self.limpar_valor(valor)
            
            elif tipo_parametro == 'wall':
                # parametros_wall: 1-6 → parametro_uptal_X (31-36)
                if 1 <= parametro <= 6:
                    campo = f'parametro_uptal_{parametro}'
                    parametros_por_plano[id_plano][campo] = self.limpar_valor(valor)
            
            elif tipo_parametro == 'clientesf':
                # parametros_clientesf: 1-4 → parametro_wall_X (37-40)
                if 1 <= parametro <= 4:
                    campo = f'parametro_wall_{parametro}'
                    parametros_por_plano[id_plano][campo] = self.limpar_valor(valor)
        
        return parametros_por_plano
    
    def criar_configuracao_parametros(self, loja_id, id_desc_combinado, id_plano_legado, parametros_consolidados, vigencia_inicio, vigencia_fim=None, verbose=False):
        """Cria configuração de parâmetros no novo sistema com múltiplos id_desc."""
        
        # Mapear plano legado para novo sistema
        id_plano_novo, wall = self.mapear_plano_legado_para_novo(id_plano_legado)
        
        if verbose:
            print(f"  🔄 Loja {loja_id}, plano {id_plano_legado}→{id_plano_novo}, wall {wall}")
            print(f"      id_desc: {id_desc_combinado}")
        
        # Verificar se já existe configuração idêntica
        if ParametrosWall.objects.filter(
            loja_id=loja_id, 
            id_plano=id_plano_novo, 
            wall=wall,
            id_desc=id_desc_combinado,
            vigencia_inicio=vigencia_inicio
        ).exists():
            if verbose:
                print(f"    ⚠️  Já existe: Loja {loja_id}, plano {id_plano_novo}, wall {wall}, vigência {vigencia_inicio}")
            return False
        
        # Preparar dados da configuração
        config_data = {
            'loja_id': loja_id,
            'id_desc': id_desc_combinado,  # Formato: [loja_id,wall_id,clientef_id]
            'id_plano': id_plano_novo,
            'wall': wall,
            'vigencia_inicio': vigencia_inicio,
            'vigencia_fim': vigencia_fim,
        }
        
        # Adicionar parâmetros
        config_data.update(parametros_consolidados)
        
        # Criar configuração
        try:
            ParametrosWall.objects.create(**config_data)
            return True
        except Exception as e:
            print(f"    ❌ Erro ao criar configuração: {e}")
            print(f"    🔍 Dados: loja_id={loja_id}, id_plano={id_plano_novo}, wall={wall}")
            print(f"    🔍 id_desc={id_desc_combinado}")
            return False
    
    def migrar_loja(self, loja_id, razao_social, verbose=False):
        """Migra parâmetros de uma loja específica usando matriz de vigências."""
        
        from django.utils import timezone
        
        print(f"\n📋 Migrando Loja {loja_id}: {razao_social}")
        
        configuracoes_criadas = 0
        
        # Migrar Wall S e Wall N
        for wall_type in ['S', 'N']:
            print(f"  🔄 Processando Wall {wall_type}")
            
            # Buscar todas as combinações de vigência para esta loja
            combinacoes = self.buscar_combinacoes_vigencia(loja_id, wall_type)
            
            if not combinacoes:
                print(f"    ⚠️  Nenhuma combinação de vigência encontrada para Wall {wall_type}")
                continue
            
            # Processar cada combinação de vigência
            for i, combinacao in enumerate(combinacoes):
                data_inicio, id_desc_loja, id_desc_wall, id_desc_clientef = combinacao
                
                # Calcular data fim (próxima combinação ou None)
                data_fim = None
                if i + 1 < len(combinacoes):
                    data_fim = timezone.make_aware(datetime.fromtimestamp(combinacoes[i + 1][0]))
                
                # Converter timestamp para datetime timezone-aware
                vigencia_inicio = timezone.make_aware(datetime.fromtimestamp(data_inicio))
                
                # Criar string combinada de id_desc no formato [loja,wall,clientef]
                id_desc_combinado = f"[{id_desc_loja or 0},{id_desc_wall or 0},{id_desc_clientef or 0}]"
                
                if verbose:
                    print(f"    📅 Vigência: {vigencia_inicio} → {data_fim or 'atual'}")
                    print(f"    🆔 ID_DESC: {id_desc_combinado}")
                
                # Buscar parâmetros para esta combinação
                resultado = self.buscar_parametros_por_combinacao(
                    id_desc_loja, id_desc_wall, id_desc_clientef, wall_type
                )
                
                if not resultado:
                    continue
                
                # Processar parâmetros
                parametros_loja = self.processar_parametros_json(resultado[0], 'loja')
                parametros_wall = self.processar_parametros_json(resultado[1], 'wall') 
                parametros_clientesf = self.processar_parametros_json(resultado[2], 'clientesf')
                
                # Obter todos os planos únicos
                todos_planos = set()
                todos_planos.update(parametros_loja.keys())
                todos_planos.update(parametros_wall.keys())
                todos_planos.update(parametros_clientesf.keys())
                
                # Criar configurações para cada plano
                for id_plano_legado in todos_planos:
                    # Consolidar parâmetros deste plano
                    parametros_consolidados = {}
                    parametros_consolidados.update(parametros_loja.get(id_plano_legado, {}))
                    parametros_consolidados.update(parametros_wall.get(id_plano_legado, {}))
                    parametros_consolidados.update(parametros_clientesf.get(id_plano_legado, {}))
                    
                    if parametros_consolidados:
                        if self.criar_configuracao_parametros(
                            loja_id, id_desc_combinado, id_plano_legado, 
                            parametros_consolidados, vigencia_inicio, data_fim, verbose
                        ):
                            configuracoes_criadas += 1
        
        print(f"  ✅ {configuracoes_criadas} configurações criadas para loja {loja_id}")
        return configuracoes_criadas
    
    def executar_migracao(self, verbose=False):
        """Executa a migração completa."""
        
        print("🚀 Iniciando migração de parâmetros atuais...")
        
        # Conectar aos bancos
        self.conectar_bancos()
        
        # Buscar lojas ativas
        lojas = self.buscar_lojas_ativas()
        
        total_configuracoes = 0
        
        # Migrar cada loja
        for loja_id, razao_social in lojas:
            configuracoes_loja = self.migrar_loja(loja_id, razao_social, verbose)
            total_configuracoes += configuracoes_loja
        
        print(f"\n🎉 Migração concluída!")
        print(f"📊 Total de lojas processadas: {len(lojas)}")
        print(f"📊 Total de configurações migradas: {total_configuracoes}")
        
        # Fechar conexões
        if self.conn_legado:
            self.conn_legado.close()
        if self.conn_wallclub:
            self.conn_wallclub.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração de parâmetros atuais')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verboso')
    parser.add_argument('--loja', type=int, help='Migrar apenas uma loja específica')
    
    args = parser.parse_args()
    
    migrador = MigradorAtual()
    
    if args.loja:
        # Migrar apenas uma loja
        migrador.conectar_bancos()
        cursor = migrador.conn_wallclub.cursor()
        cursor.execute("SELECT id, razao_social FROM loja WHERE id = %s", (args.loja,))
        loja = cursor.fetchone()
        cursor.close()
        
        if loja:
            migrador.migrar_loja(loja[0], loja[1], args.verbose)
        else:
            print(f"❌ Loja {args.loja} não encontrada")
        
        migrador.conn_legado.close()
        migrador.conn_wallclub.close()
    else:
        # Migração completa
        migrador.executar_migracao(verbose=args.verbose)


if __name__ == '__main__':
    main()
