#!/usr/bin/env python3
"""
Script Principal de Migração de Dados para Produção
Migra dados do sistema legado para o novo sistema Django parametros_wallclub

Baseado em migrar_dados_simples.py com melhorias para produção:
- Rollback automático em caso de erro
- Validação completa dos dados
- Logs detalhados
- Backup automático antes da migração
"""

import os
import sys
import django
import pymysql
from datetime import datetime
from decimal import Decimal, InvalidOperation

# Configurar Django para PRODUÇÃO
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.models import ConfiguracaoVigente, ConfiguracaoFutura, ImportacaoConfiguracoes, Plano
from django.utils import timezone
from django.db import transaction, connection


class MigradorProducao:
    """Migrador completo para produção com rollback e validação."""
    
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.conn_legado = None
        self.stats = {
            'inicio': datetime.now(),
            'planos_migrados': 0,
            'configuracoes_migradas': 0,
            'erros': [],
            'warnings': []
        }
        
    def log(self, mensagem, tipo='INFO'):
        """Log com timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefixo = {
            'INFO': '📋',
            'SUCCESS': '✅',
            'ERROR': '❌',
            'WARNING': '⚠️'
        }.get(tipo, '📋')
        
        print(f"[{timestamp}] {prefixo} {mensagem}")
        
        if tipo == 'ERROR':
            self.stats['erros'].append(mensagem)
        elif tipo == 'WARNING':
            self.stats['warnings'].append(mensagem)
    
    def conectar_banco_legado(self):
        """Conecta ao banco legado."""
        try:
            self.conn_legado = pymysql.connect(
                host='10.0.1.107',  # IP do MySQL em produção
                user='user_python', # Usuário Python
                password='sblYcQ(@p.9',  # Senha do user_python
                database='wclub',
                charset='utf8mb4'
            )
            self.log("Conectado ao banco legado")
            return True
        except Exception as e:
            self.log(f"Erro ao conectar banco legado: {e}", 'ERROR')
            return False
    
    def criar_backup_tabelas(self):
        """Cria backup das tabelas antes da migração."""
        if self.dry_run:
            self.log("DRY RUN: Backup seria criado aqui")
            return True
            
        try:
            with connection.cursor() as cursor:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Backup da tabela principal
                cursor.execute(f"""
                    CREATE TABLE parametros_wallclub_backup_{timestamp} 
                    AS SELECT * FROM parametros_wallclub
                """)
                
                # Backup da tabela de planos
                cursor.execute(f"""
                    CREATE TABLE parametros_wallclub_planos_backup_{timestamp} 
                    AS SELECT * FROM parametros_wallclub_planos
                """)
                
                self.log(f"Backup criado com timestamp {timestamp}")
                return True
                
        except Exception as e:
            self.log(f"Erro ao criar backup: {e}", 'ERROR')
            return False
    
    def limpar_tabelas_destino(self):
        """Limpa tabelas de destino antes da migração."""
        if self.dry_run:
            self.log("DRY RUN: Tabelas seriam limpas aqui")
            return True
            
        try:
            with transaction.atomic():
                ConfiguracaoVigente.objects.all().delete()
                Plano.objects.all().delete()
                
                self.log("Tabelas de destino limpas")
                return True
                
        except Exception as e:
            self.log(f"Erro ao limpar tabelas: {e}", 'ERROR')
            return False
    
    def migrar_planos(self):
        """Migra planos do sistema legado."""
        try:
            cursor = self.conn_legado.cursor()
            
            # Buscar planos únicos
            cursor.execute("""
                SELECT DISTINCT 
                    id,
                    COALESCE(nome, CONCAT('Plano ', id)) as nome,
                    prazo
                FROM planos 
                WHERE id IS NOT NULL
                ORDER BY id
            """)
            
            planos = cursor.fetchall()
            
            for id_plano, nome, prazo in planos:
                if not self.dry_run:
                    plano, created = Plano.objects.get_or_create(
                        id=id_plano,
                        defaults={
                            'nome': nome,
                            'prazo_dias': prazo or 0,
                            'bandeira': ''
                        }
                    )
                    
                    if created:
                        self.stats['planos_migrados'] += 1
                else:
                    self.log(f"DRY RUN: Criaria plano {id_plano} - {nome}")
                    self.stats['planos_migrados'] += 1
            
            self.log(f"Planos migrados: {self.stats['planos_migrados']}")
            return True
            
        except Exception as e:
            self.log(f"Erro ao migrar planos: {e}", 'ERROR')
            return False
    
    def migrar_configuracoes(self):
        """Migra configurações do sistema legado."""
        try:
            cursor = self.conn_legado.cursor()
            
            # Query principal baseada no script que funciona
            cursor.execute("""
                SELECT DISTINCT
                    p.loja_id,
                    p.id_plano,
                    p.wall,
                    p.parametro_1, p.parametro_2, p.parametro_3, p.parametro_4, p.parametro_5,
                    p.parametro_6, p.parametro_7, p.parametro_8, p.parametro_9, p.parametro_10,
                    p.parametro_11, p.parametro_12, p.parametro_13, p.parametro_14, p.parametro_15,
                    p.parametro_16, p.parametro_17, p.parametro_18, p.parametro_19, p.parametro_20,
                    p.parametro_21, p.parametro_22, p.parametro_23, p.parametro_24, p.parametro_25,
                    p.parametro_26, p.parametro_27, p.parametro_28, p.parametro_29, p.parametro_30,
                    p.uptal_1, p.uptal_2, p.uptal_3, p.uptal_4, p.uptal_5,
                    p.uptal_6, p.uptal_7, p.uptal_8, p.uptal_9, p.uptal_10,
                    p.uptal_11, p.uptal_12, p.uptal_13, p.uptal_14, p.uptal_15,
                    p.uptal_16, p.uptal_17, p.uptal_18, p.uptal_19, p.uptal_20,
                    p.uptal_21, p.uptal_22, p.uptal_23, p.uptal_24, p.uptal_25,
                    p.uptal_26, p.uptal_27, p.uptal_28, p.uptal_29, p.uptal_30,
                    p.wall_1, p.wall_2, p.wall_3, p.wall_4, p.wall_5,
                    p.wall_6, p.wall_7, p.wall_8, p.wall_9, p.wall_10,
                    p.wall_11, p.wall_12, p.wall_13, p.wall_14, p.wall_15,
                    p.wall_16, p.wall_17, p.wall_18, p.wall_19, p.wall_20,
                    p.wall_21, p.wall_22, p.wall_23, p.wall_24, p.wall_25,
                    p.wall_26, p.wall_27, p.wall_28, p.wall_29, p.wall_30,
                    p.clientesf2,
                    p.data_vigencia,
                    p.terminal
                FROM parametros_clientesf p
                WHERE p.loja_id IS NOT NULL 
                AND p.id_plano IS NOT NULL
                ORDER BY p.loja_id, p.id_plano, p.wall
            """)
            
            configuracoes = cursor.fetchall()
            
            for config in configuracoes:
                try:
                    if not self.dry_run:
                        self._criar_configuracao(config)
                    else:
                        self.log(f"DRY RUN: Criaria config loja {config[0]}, plano {config[1]}, wall {config[2]}")
                    
                    self.stats['configuracoes_migradas'] += 1
                    
                    if self.stats['configuracoes_migradas'] % 100 == 0:
                        self.log(f"Migradas {self.stats['configuracoes_migradas']} configurações...")
                        
                except Exception as e:
                    self.log(f"Erro ao migrar configuração loja {config[0]}: {e}", 'ERROR')
                    continue
            
            self.log(f"Configurações migradas: {self.stats['configuracoes_migradas']}")
            return True
            
        except Exception as e:
            self.log(f"Erro ao migrar configurações: {e}", 'ERROR')
            return False
    
    def _criar_configuracao(self, config):
        """Cria uma configuração individual."""
        # Desempacotar dados
        (loja_id, id_plano, wall, 
         param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8, param_9, param_10,
         param_11, param_12, param_13, param_14, param_15, param_16, param_17, param_18, param_19, param_20,
         param_21, param_22, param_23, param_24, param_25, param_26, param_27, param_28, param_29, param_30,
         uptal_1, uptal_2, uptal_3, uptal_4, uptal_5, uptal_6, uptal_7, uptal_8, uptal_9, uptal_10,
         uptal_11, uptal_12, uptal_13, uptal_14, uptal_15, uptal_16, uptal_17, uptal_18, uptal_19, uptal_20,
         uptal_21, uptal_22, uptal_23, uptal_24, uptal_25, uptal_26, uptal_27, uptal_28, uptal_29, uptal_30,
         wall_1, wall_2, wall_3, wall_4, wall_5, wall_6, wall_7, wall_8, wall_9, wall_10,
         wall_11, wall_12, wall_13, wall_14, wall_15, wall_16, wall_17, wall_18, wall_19, wall_20,
         wall_21, wall_22, wall_23, wall_24, wall_25, wall_26, wall_27, wall_28, wall_29, wall_30,
         clientesf2, data_vigencia, terminal) = config
        
        # Converter valores para Decimal
        def safe_decimal(value):
            if value is None:
                return None
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError):
                return None
        
        # Buscar plano
        try:
            plano = Plano.objects.get(id=id_plano)
        except Plano.DoesNotExist:
            raise Exception(f"Plano {id_plano} não encontrado")
        
        # Criar configuração
        configuracao = ConfiguracaoVigente.objects.create(
            loja_id=loja_id,
            plano=plano,
            wall=wall or 'n',
            terminal=terminal,
            
            # Parâmetros loja
            parametro_loja_1=safe_decimal(param_1),
            parametro_loja_2=safe_decimal(param_2),
            parametro_loja_3=safe_decimal(param_3),
            parametro_loja_4=safe_decimal(param_4),
            parametro_loja_5=safe_decimal(param_5),
            parametro_loja_6=safe_decimal(param_6),
            parametro_loja_7=safe_decimal(param_7),
            parametro_loja_8=safe_decimal(param_8),
            parametro_loja_9=safe_decimal(param_9),
            parametro_loja_10=safe_decimal(param_10),
            parametro_loja_11=safe_decimal(param_11),
            parametro_loja_12=safe_decimal(param_12),
            parametro_loja_13=safe_decimal(param_13),
            parametro_loja_14=safe_decimal(param_14),
            parametro_loja_15=safe_decimal(param_15),
            parametro_loja_16=param_16,  # VARCHAR
            parametro_loja_17=safe_decimal(param_17),
            parametro_loja_18=safe_decimal(param_18),
            parametro_loja_19=safe_decimal(param_19),
            parametro_loja_20=safe_decimal(param_20),
            parametro_loja_21=safe_decimal(param_21),
            parametro_loja_22=safe_decimal(param_22),
            parametro_loja_23=safe_decimal(param_23),
            parametro_loja_24=safe_decimal(param_24),
            parametro_loja_25=safe_decimal(param_25),
            parametro_loja_26=safe_decimal(param_26),
            parametro_loja_27=safe_decimal(param_27),
            parametro_loja_28=safe_decimal(param_28),
            parametro_loja_29=safe_decimal(param_29),
            parametro_loja_30=safe_decimal(param_30),
            
            # Parâmetros uptal
            parametro_uptal_1=safe_decimal(uptal_1),
            parametro_uptal_2=safe_decimal(uptal_2),
            parametro_uptal_3=safe_decimal(uptal_3),
            parametro_uptal_4=safe_decimal(uptal_4),
            parametro_uptal_5=safe_decimal(uptal_5),
            parametro_uptal_6=safe_decimal(uptal_6),
            parametro_uptal_7=safe_decimal(uptal_7),
            parametro_uptal_8=safe_decimal(uptal_8),
            parametro_uptal_9=safe_decimal(uptal_9),
            parametro_uptal_10=safe_decimal(uptal_10),
            parametro_uptal_11=safe_decimal(uptal_11),
            parametro_uptal_12=safe_decimal(uptal_12),
            parametro_uptal_13=safe_decimal(uptal_13),
            parametro_uptal_14=safe_decimal(uptal_14),
            parametro_uptal_15=safe_decimal(uptal_15),
            parametro_uptal_16=safe_decimal(uptal_16),
            parametro_uptal_17=safe_decimal(uptal_17),
            parametro_uptal_18=safe_decimal(uptal_18),
            parametro_uptal_19=safe_decimal(uptal_19),
            parametro_uptal_20=safe_decimal(uptal_20),
            parametro_uptal_21=safe_decimal(uptal_21),
            parametro_uptal_22=safe_decimal(uptal_22),
            parametro_uptal_23=safe_decimal(uptal_23),
            parametro_uptal_24=safe_decimal(uptal_24),
            parametro_uptal_25=safe_decimal(uptal_25),
            parametro_uptal_26=safe_decimal(uptal_26),
            parametro_uptal_27=safe_decimal(uptal_27),
            parametro_uptal_28=safe_decimal(uptal_28),
            parametro_uptal_29=safe_decimal(uptal_29),
            parametro_uptal_30=safe_decimal(uptal_30),
            
            # Parâmetros wall
            parametro_wall_1=safe_decimal(wall_1),
            parametro_wall_2=safe_decimal(wall_2),
            parametro_wall_3=safe_decimal(wall_3),
            parametro_wall_4=safe_decimal(wall_4),
            parametro_wall_5=safe_decimal(wall_5),
            parametro_wall_6=safe_decimal(wall_6),
            parametro_wall_7=safe_decimal(wall_7),
            parametro_wall_8=safe_decimal(wall_8),
            parametro_wall_9=safe_decimal(wall_9),
            parametro_wall_10=safe_decimal(wall_10),
            parametro_wall_11=safe_decimal(wall_11),
            parametro_wall_12=safe_decimal(wall_12),
            parametro_wall_13=safe_decimal(wall_13),
            parametro_wall_14=safe_decimal(wall_14),
            parametro_wall_15=safe_decimal(wall_15),
            parametro_wall_16=safe_decimal(wall_16),
            parametro_wall_17=safe_decimal(wall_17),
            parametro_wall_18=safe_decimal(wall_18),
            parametro_wall_19=safe_decimal(wall_19),
            parametro_wall_20=safe_decimal(wall_20),
            parametro_wall_21=safe_decimal(wall_21),
            parametro_wall_22=safe_decimal(wall_22),
            parametro_wall_23=safe_decimal(wall_23),
            parametro_wall_24=safe_decimal(wall_24),
            parametro_wall_25=safe_decimal(wall_25),
            parametro_wall_26=safe_decimal(wall_26),
            parametro_wall_27=safe_decimal(wall_27),
            parametro_wall_28=safe_decimal(wall_28),
            parametro_wall_29=safe_decimal(wall_29),
            parametro_wall_30=safe_decimal(wall_30),
            
            # Outros campos
            parametro_clientesf2=safe_decimal(clientesf2),
            data_vigencia=data_vigencia or timezone.now().date(),
            criado_em=timezone.now(),
            atualizado_em=timezone.now()
        )
        
        return configuracao
    
    def validar_migracao(self):
        """Validação básica pós-migração."""
        try:
            count_planos = Plano.objects.count()
            count_configs = ConfiguracaoVigente.objects.count()
            
            self.log(f"Validação: {count_planos} planos, {count_configs} configurações")
            
            if count_planos == 0:
                self.log("ERRO: Nenhum plano migrado", 'ERROR')
                return False
            
            if count_configs == 0:
                self.log("ERRO: Nenhuma configuração migrada", 'ERROR')
                return False
            
            # Verificar integridade referencial
            configs_sem_plano = ConfiguracaoVigente.objects.filter(plano__isnull=True).count()
            if configs_sem_plano > 0:
                self.log(f"ERRO: {configs_sem_plano} configurações sem plano", 'ERROR')
                return False
            
            self.log("Validação básica passou")
            return True
            
        except Exception as e:
            self.log(f"Erro na validação: {e}", 'ERROR')
            return False
    
    def executar_migracao_completa(self):
        """Executa migração completa com rollback automático."""
        self.log("=== INICIANDO MIGRAÇÃO PARA PRODUÇÃO ===")
        
        if self.dry_run:
            self.log("MODO DRY RUN - Nenhuma alteração será feita")
        
        # Conectar ao banco legado
        if not self.conectar_banco_legado():
            return False
        
        try:
            with transaction.atomic():
                # Criar backup
                if not self.criar_backup_tabelas():
                    raise Exception("Falha ao criar backup")
                
                # Limpar tabelas
                if not self.limpar_tabelas_destino():
                    raise Exception("Falha ao limpar tabelas")
                
                # Migrar planos
                if not self.migrar_planos():
                    raise Exception("Falha ao migrar planos")
                
                # Migrar configurações
                if not self.migrar_configuracoes():
                    raise Exception("Falha ao migrar configurações")
                
                # Validar migração
                if not self.validar_migracao():
                    raise Exception("Falha na validação")
                
                if self.dry_run:
                    self.log("DRY RUN: Rollback automático")
                    raise Exception("Dry run - rollback intencional")
                
                self.log("MIGRAÇÃO CONCLUÍDA COM SUCESSO!", 'SUCCESS')
                return True
                
        except Exception as e:
            self.log(f"ERRO NA MIGRAÇÃO: {e}", 'ERROR')
            self.log("Rollback automático executado", 'WARNING')
            return False
        
        finally:
            if self.conn_legado:
                self.conn_legado.close()
    
    def gerar_relatorio_final(self):
        """Gera relatório final da migração."""
        fim = datetime.now()
        duracao = fim - self.stats['inicio']
        
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL DA MIGRAÇÃO")
        print("=" * 60)
        print(f"⏱️  Duração: {duracao}")
        print(f"📦 Planos migrados: {self.stats['planos_migrados']}")
        print(f"⚙️  Configurações migradas: {self.stats['configuracoes_migradas']}")
        print(f"❌ Erros: {len(self.stats['erros'])}")
        print(f"⚠️  Warnings: {len(self.stats['warnings'])}")
        
        if self.stats['erros']:
            print(f"\n❌ ERROS ({len(self.stats['erros'])}):")
            for erro in self.stats['erros'][:5]:  # Mostrar só os 5 primeiros
                print(f"   - {erro}")
            if len(self.stats['erros']) > 5:
                print(f"   ... e mais {len(self.stats['erros']) - 5} erros")
        
        print("=" * 60)


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Migração de dados para produção')
    parser.add_argument('--dry-run', action='store_true', help='Simular migração sem alterar dados')
    
    args = parser.parse_args()
    
    migrador = MigradorProducao(dry_run=args.dry_run)
    sucesso = migrador.executar_migracao_completa()
    migrador.gerar_relatorio_final()
    
    # Exit code baseado no resultado
    sys.exit(0 if sucesso else 1)


if __name__ == '__main__':
    main()