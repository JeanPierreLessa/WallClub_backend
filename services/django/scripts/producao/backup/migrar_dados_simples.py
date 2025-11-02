#!/usr/bin/env python3
"""
SCRIPT SIMPLIFICADO DE MIGRAÇÃO DE DADOS PARA PRODUÇÃO
WallClub - Parâmetros Financeiros

Baseado no script migrar_parametros_corrigido.py que já funcionava.
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

from parametros_wallclub.models import (
    Plano, 
    ParametrosWall
)


class MigradorSimples:
    def __init__(self):
        self.conn_legado = None
        
    def conectar_banco_legado(self):
        """Conecta ao banco legado wclub."""
        try:
            self.conn_legado = pymysql.connect(
                host='10.0.1.107',
                user='user_python',
                password='sblYcQ(@p.9',
                database='wclub',
                charset='utf8mb4'
            )
            print("✅ Conectado ao banco legado (wclub)")
        except Exception as e:
            print(f"❌ Erro ao conectar ao banco legado: {e}")
            sys.exit(1)
    
    def buscar_configuracoes_legado(self):
        """Busca todas as configurações do sistema legado."""
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT DISTINCT 
            r.id_cliente as loja_id,
            r.id_desc,
            r.inicio as vigencia_inicio
        FROM rel_loja_param r
        ORDER BY r.id_cliente, r.id_desc, r.inicio
        """
        
        cursor.execute(sql)
        configuracoes = cursor.fetchall()
        cursor.close()
        
        print(f"📊 Encontradas {len(configuracoes)} configurações no legado")
        return configuracoes
    
    def popular_tabela_planos(self):
        """Popula a tabela de planos consolidando Wall e Sem Wall."""
        print("📋 Populando tabela de planos (consolidando Wall + Sem Wall)...")
        
        cursor_legado = self.conn_legado.cursor()
        
        # Buscar planos Wall
        print("  📋 Buscando planos Wall...")
        cursor_legado.execute("""
            SELECT DISTINCT id, nome, prazo, bandeira
            FROM planos 
            ORDER BY id
        """)
        planos_wall = cursor_legado.fetchall()
        
        # Buscar planos Sem Wall  
        print("  📋 Buscando planos Sem Wall...")
        cursor_legado.execute("""
            SELECT DISTINCT id, nome, prazo, bandeira
            FROM planos_sem_club 
            ORDER BY id
        """)
        planos_sem_wall = cursor_legado.fetchall()
        
        cursor_legado.close()
        
        # Conectar ao banco wallclub
        import pymysql
        conn_wallclub = pymysql.connect(
            host='10.0.1.107',
            user='user_python',
            password='sblYcQ(@p.9',
            database='wallclub',
            charset='utf8mb4'
        )
        
        cursor_wallclub = conn_wallclub.cursor()
        
        # Criar mapeamento de planos únicos
        planos_unicos = {}
        id_sequencial = 1
        
        # Processar planos Wall
        for id_original, nome, prazo, bandeira in planos_wall:
            chave = (nome, prazo, bandeira or '')
            
            if chave not in planos_unicos:
                planos_unicos[chave] = {
                    'id': id_sequencial,
                    'nome': nome,
                    'prazo': prazo,
                    'bandeira': bandeira,
                    'id_original_wall': None,
                    'id_original_sem_wall': None
                }
                id_sequencial += 1
            
            planos_unicos[chave]['id_original_wall'] = id_original
        
        # Processar planos Sem Wall
        for id_original, nome, prazo, bandeira in planos_sem_wall:
            chave = (nome, prazo, bandeira or '')
            
            if chave not in planos_unicos:
                planos_unicos[chave] = {
                    'id': id_sequencial,
                    'nome': nome,
                    'prazo': prazo,
                    'bandeira': bandeira,
                    'id_original_wall': None,
                    'id_original_sem_wall': None
                }
                id_sequencial += 1
            
            planos_unicos[chave]['id_original_sem_wall'] = id_original
        
        # Inserir planos únicos
        planos_criados = 0
        
        for dados_plano in planos_unicos.values():
            # Verificar se já existe
            cursor_wallclub.execute("SELECT COUNT(*) FROM parametros_wallclub_planos WHERE id = %s", (dados_plano['id'],))
            existe = cursor_wallclub.fetchone()[0] > 0
            
            if not existe:
                cursor_wallclub.execute("""
                    INSERT INTO parametros_wallclub_planos 
                    (id, id_original_wall, id_original_sem_wall, nome, prazo_dias, bandeira, ativo) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    dados_plano['id'],
                    dados_plano['id_original_wall'],
                    dados_plano['id_original_sem_wall'],
                    dados_plano['nome'] or f'Plano {dados_plano["id"]}',
                    dados_plano['prazo'] or 0,
                    dados_plano['bandeira'] or '',
                    True
                ))
                planos_criados += 1
        
        conn_wallclub.commit()
        cursor_wallclub.close()
        conn_wallclub.close()
        
        print(f"✅ {planos_criados} planos únicos criados")
        print(f"📊 Total Wall: {len(planos_wall)}, Sem Wall: {len(planos_sem_wall)}, Únicos: {len(planos_unicos)}")
        return planos_criados

    def buscar_planos_por_id_desc(self, id_desc):
        """Busca todos os planos que têm parâmetros para um id_desc."""
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT DISTINCT id_plano 
        FROM parametros_loja 
        WHERE id_desc = %s
        ORDER BY id_plano
        """
        
        cursor.execute(sql, (id_desc,))
        planos = [row[0] for row in cursor.fetchall()]
        cursor.close()
        
        return planos
    
    def buscar_parametros_loja(self, id_desc, id_plano):
        """Busca parâmetros da tabela parametros_loja."""
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT parametro, valor 
        FROM parametros_loja 
        WHERE id_desc = %s AND id_plano = %s
        ORDER BY parametro
        """
        
        cursor.execute(sql, (id_desc, id_plano))
        parametros = cursor.fetchall()
        cursor.close()
        
        return {int(param): valor for param, valor in parametros}
    
    def buscar_parametros_wall(self, id_desc, id_plano):
        """Busca parâmetros da tabela parametros_wall."""
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT parametro, valor 
        FROM parametros_wall 
        WHERE id_desc = %s AND id_plano = %s
        ORDER BY parametro
        """
        
        cursor.execute(sql, (id_desc, id_plano))
        parametros = cursor.fetchall()
        cursor.close()
        
        # Mapear códigos 1-6 para parâmetros 31-36
        return {int(param) + 30: valor for param, valor in parametros}
    
    def buscar_parametros_clientesf(self, id_desc, id_plano):
        """Busca parâmetros da tabela parametros_clientesf."""
        cursor = self.conn_legado.cursor()
        
        sql = """
        SELECT parametro, valor 
        FROM parametros_clientesf 
        WHERE id_desc = %s AND id_plano = %s
        ORDER BY parametro
        """
        
        cursor.execute(sql, (id_desc, id_plano))
        parametros = cursor.fetchall()
        cursor.close()
        
        # Mapear códigos 1-4 para parâmetros 37-40
        return {int(param) + 36: valor for param, valor in parametros}
    
    def determinar_modalidade_wall(self, id_plano):
        """Determina se o plano é Com Wall (S) ou Sem Wall (N)."""
        return 'S' if id_plano < 1000 else 'N'
    
    def mapear_plano_legado_para_novo(self, id_plano_legado):
        """
        Mapeia plano do sistema legado para novo sistema.
        
        LÓGICA NOVA:
        - Wall S: plano 1 → plano 1, wall='S'
        - Wall N: plano 1001 → plano 1, wall='N'
        - Wall S: plano 2 → plano 2, wall='S'  
        - Wall N: plano 1002 → plano 2, wall='N'
        
        Returns:
            tuple: (id_plano_novo, wall)
        """
        if id_plano_legado >= 1000:
            # Sem Wall: 1001 → plano 1, 1002 → plano 2, etc.
            id_plano_novo = id_plano_legado - 1000
            wall = 'N'
        else:
            # Com Wall: 1 → plano 1, 2 → plano 2, etc.
            id_plano_novo = id_plano_legado
            wall = 'S'
        
        return id_plano_novo, wall
    
    def converter_data_vigencia(self, data_str):
        """Converte string de data para datetime com timezone."""
        if not data_str:
            return timezone.now()
        
        try:
            # Tentar formato completo
            dt = datetime.strptime(str(data_str), '%Y-%m-%d %H:%M:%S')
        except ValueError:
            try:
                # Tentar formato só data
                dt = datetime.strptime(str(data_str), '%Y-%m-%d')
            except ValueError:
                return timezone.now()
        
        # Usar timezone do Django (já configurado)
        return timezone.make_aware(dt)
    
    def eh_configuracao_futura(self, vigencia_inicio):
        """Verifica se a configuração é futura."""
        return vigencia_inicio > timezone.now()
    
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
    
    def consolidar_parametros(self, parametros_loja, parametros_wall, parametros_clientesf):
        """Consolida todos os parâmetros em um dicionário único."""
        parametros_consolidados = {}
        
        # Parâmetros da loja (1-30) -> parametro_loja_X
        for codigo, valor in parametros_loja.items():
            if 1 <= codigo <= 30:
                campo = f'parametro_loja_{codigo}'
                parametros_consolidados[campo] = self.limpar_valor(valor)
        
        # Parâmetros uptal (31-36) -> parametro_uptal_X  
        for codigo, valor in parametros_wall.items():
            if 31 <= codigo <= 36:
                campo = f'parametro_uptal_{codigo - 30}'
                parametros_consolidados[campo] = self.limpar_valor(valor)
        
        # Parâmetros wall (37-40) -> parametro_wall_X
        for codigo, valor in parametros_clientesf.items():
            if 37 <= codigo <= 40:
                campo = f'parametro_wall_{codigo - 36}'
                parametros_consolidados[campo] = self.limpar_valor(valor)
        
        return parametros_consolidados
    
    def buscar_id_plano_consolidado(self, id_plano_legado):
        """
        Mapeia plano legado para novo sistema (sem consulta ao banco).
        
        LÓGICA SIMPLIFICADA:
        - Wall S: 1 → 1, 2 → 2, etc.
        - Wall N: 1001 → 1, 1002 → 2, etc.
        """
        id_plano_novo, _ = self.mapear_plano_legado_para_novo(id_plano_legado)
        return id_plano_novo

    def criar_configuracao(self, loja_id, id_desc, id_plano_legado, vigencia_inicio, parametros_consolidados, eh_historica=False, verbose=False):
        """Cria uma configuração na nova estrutura."""
        
        # Mapear plano legado para novo sistema
        id_plano_novo, wall = self.mapear_plano_legado_para_novo(id_plano_legado)
        
        # Converter vigência
        vigencia_inicio_dt = self.converter_data_vigencia(vigencia_inicio)
        
        # TODAS as configurações vão para ParametrosWall
        # Diferença: versões históricas têm vigencia_fim preenchida
        eh_futura = self.eh_configuracao_futura(vigencia_inicio_dt)
        modelo = ConfiguracaoFutura if eh_futura else ParametrosWall
        
        if eh_historica:
            tipo_config = "histórica"
            # Para versões históricas, definir vigencia_fim como a data atual
            # (indicando que não está mais ativa)
            from django.utils import timezone
            vigencia_fim = timezone.now()
        else:
            tipo_config = "futura" if eh_futura else "vigente"
            vigencia_fim = None
        
        if verbose:
            print(f"🔄 Criando configuração {tipo_config}: Loja {loja_id}, id_desc {id_desc}, plano {id_plano_legado}→{id_plano_novo}, wall {wall}")
        
        # Verificar se já existe (incluir id_desc para permitir múltiplas versões)
        filtro_existencia = {
            'loja_id': loja_id, 
            'id_desc': id_desc,
            'id_plano': id_plano_novo,
            'wall': wall
        }
        
        if modelo.objects.filter(**filtro_existencia).exists():
            if verbose:
                print(f"⚠️  Já existe: Loja {loja_id}, id_desc {id_desc}, plano {id_plano_novo}, wall {wall}")
            return False
        
        # Preparar dados da configuração
        config_data = {
            'loja_id': loja_id,
            'id_desc': id_desc,
            'id_plano': id_plano_novo,
            'wall': wall,
            'vigencia_inicio': vigencia_inicio_dt,
            'vigencia_fim': vigencia_fim,
        }
        
        # Adicionar parâmetros
        config_data.update(parametros_consolidados)
        
        # Criar configuração
        try:
            modelo.objects.create(**config_data)
            return True
        except Exception as e:
            print(f"❌ Erro ao criar configuração: {e}")
            return False
    
    def migrar_configuracao(self, loja_id, id_desc, vigencia_inicio, verbose=False):
        """Migra uma configuração completa (todos os planos)."""
        
        # Buscar todos os planos para este id_desc
        planos = self.buscar_planos_por_id_desc(id_desc)
        
        if not planos:
            if verbose:
                print(f"⚠️  Nenhum plano encontrado para id_desc {id_desc}")
            return 0
        
        configuracoes_criadas = 0
        
        for id_plano in planos:
            # Buscar parâmetros de todas as tabelas
            parametros_loja = self.buscar_parametros_loja(id_desc, id_plano)
            parametros_wall = self.buscar_parametros_wall(id_desc, id_plano)
            parametros_clientesf = self.buscar_parametros_clientesf(id_desc, id_plano)
            
            # Consolidar parâmetros
            parametros_consolidados = self.consolidar_parametros(
                parametros_loja, parametros_wall, parametros_clientesf
            )
            
            # Criar configuração
            if self.criar_configuracao(
                loja_id, id_desc, id_plano, vigencia_inicio, 
                parametros_consolidados, verbose
            ):
                configuracoes_criadas += 1
        
        return configuracoes_criadas
    
    def identificar_versoes_atuais_e_historicas(self, configuracoes):
        """Separa versões atuais das históricas por loja/plano/wall."""
        print("🔍 Identificando versões atuais vs históricas...")
        
        # Agrupar por loja/plano/wall
        grupos = {}
        
        for loja_id, id_desc, vigencia_inicio in configuracoes:
            # Buscar planos para este id_desc
            planos = self.buscar_planos_por_id_desc(id_desc)
            
            for id_plano in planos:
                wall = self.determinar_modalidade_wall(id_plano)
                chave = (loja_id, id_plano, wall)
                
                if chave not in grupos:
                    grupos[chave] = []
                
                grupos[chave].append((loja_id, id_desc, id_plano, vigencia_inicio))
        
        # Separar versões atuais das históricas
        configuracoes_atuais = []
        configuracoes_historicas = []
        
        for chave, versoes in grupos.items():
            # Ordenar por vigência (mais recente primeiro)
            versoes_ordenadas = sorted(versoes, key=lambda x: x[3], reverse=True)
            
            # A primeira é a atual
            configuracoes_atuais.append(versoes_ordenadas[0])
            
            # As demais são históricas
            configuracoes_historicas.extend(versoes_ordenadas[1:])
        
        print(f"📊 Versões atuais: {len(configuracoes_atuais)}, Históricas: {len(configuracoes_historicas)}")
        return configuracoes_atuais, configuracoes_historicas

    def executar_migracao(self, verbose=False):
        """Executa a migração completa."""
        
        print("🚀 Iniciando migração simplificada...")
        
        # Conectar ao banco
        self.conectar_banco_legado()
        
        # Popular tabela de planos primeiro (COMENTADO - tabela já existe)
        # self.popular_tabela_planos()
        
        # Buscar configurações
        configuracoes = self.buscar_configuracoes_legado()
        
        # Separar versões atuais das históricas
        configuracoes_atuais, configuracoes_historicas = self.identificar_versoes_atuais_e_historicas(configuracoes)
        
        total_configuracoes = 0
        
        # Migrar versões atuais primeiro
        print("\n📋 Migrando versões atuais...")
        for loja_id, id_desc, id_plano, vigencia_inicio in configuracoes_atuais:
            # Buscar parâmetros de todas as tabelas
            parametros_loja = self.buscar_parametros_loja(id_desc, id_plano)
            parametros_wall = self.buscar_parametros_wall(id_desc, id_plano)
            parametros_clientesf = self.buscar_parametros_clientesf(id_desc, id_plano)
            
            # Consolidar parâmetros
            parametros_consolidados = self.consolidar_parametros(
                parametros_loja, parametros_wall, parametros_clientesf
            )
            
            if parametros_consolidados:
                if self.criar_configuracao(
                    loja_id, id_desc, id_plano, vigencia_inicio, 
                    parametros_consolidados, eh_historica=False, verbose=verbose
                ):
                    total_configuracoes += 1
        
        # Migrar versões históricas
        print("\n📚 Migrando versões históricas...")
        for loja_id, id_desc, id_plano, vigencia_inicio in configuracoes_historicas:
            # Buscar parâmetros de todas as tabelas
            parametros_loja = self.buscar_parametros_loja(id_desc, id_plano)
            parametros_wall = self.buscar_parametros_wall(id_desc, id_plano)
            parametros_clientesf = self.buscar_parametros_clientesf(id_desc, id_plano)
            
            # Consolidar parâmetros
            parametros_consolidados = self.consolidar_parametros(
                parametros_loja, parametros_wall, parametros_clientesf
            )
            
            if parametros_consolidados:
                if self.criar_configuracao(
                    loja_id, id_desc, id_plano, vigencia_inicio, 
                    parametros_consolidados, eh_historica=True, verbose=verbose
                ):
                    total_configuracoes += 1
        
        # Log da importação (sem salvar em tabela removida)
        print(f"📝 Importação registrada: {total_configuracoes} configurações processadas")
        
        print(f"\n🎉 Migração concluída!")
        print(f"📊 Total de configurações migradas: {total_configuracoes}")
        print(f"📊 Atuais: {len(configuracoes_atuais)}, Históricas: {len(configuracoes_historicas)}")
        
        # Fechar conexão
        if self.conn_legado:
            self.conn_legado.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração simplificada de dados para produção')
    parser.add_argument('--verbose', '-v', action='store_true', help='Modo verboso')
    
    args = parser.parse_args()
    
    migrador = MigradorSimples()
    migrador.executar_migracao(verbose=args.verbose)


if __name__ == '__main__':
    main()
