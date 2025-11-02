#!/usr/bin/env python3
"""
SCRIPT DE VALIDAÇÃO PÓS-MIGRAÇÃO
WallClub - Parâmetros Financeiros

VERSÃO: 1.0.0
DATA: 2025-08-14

FUNCIONALIDADES:
- Validação completa da estrutura migrada
- Verificação de integridade dos dados
- Comparação com métricas esperadas
- Testes funcionais básicos
- Relatório detalhado de validação

USO:
python validar_migracao.py [--verbose]
"""

import os
import sys
import django
import pymysql
from datetime import datetime
from decimal import Decimal

# Configurar Django para PRODUÇÃO
sys.path.append('/var/www/wallclub_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.models import (
    Plano, ConfiguracaoVigente, ConfiguracaoFutura, 
    ConfiguracaoHistorico, ImportacaoConfiguracoes
)
from parametros_wallclub.services import CalculadoraDesconto
from django.db import connection


class ValidadorMigracao:
    """Validador completo da migração."""
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.resultados = {
            'inicio': datetime.now(),
            'testes_executados': 0,
            'testes_passou': 0,
            'testes_falhou': 0,
            'erros': [],
            'warnings': [],
            'metricas': {}
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
            self.resultados['erros'].append(mensagem)
        elif tipo == 'WARNING':
            self.resultados['warnings'].append(mensagem)
    
    def executar_teste(self, nome_teste, funcao_teste):
        """Executa um teste e registra resultado."""
        self.resultados['testes_executados'] += 1
        
        try:
            resultado = funcao_teste()
            if resultado:
                self.resultados['testes_passou'] += 1
                self.log(f"PASSOU: {nome_teste}", 'SUCCESS')
            else:
                self.resultados['testes_falhou'] += 1
                self.log(f"FALHOU: {nome_teste}", 'ERROR')
            return resultado
        except Exception as e:
            self.resultados['testes_falhou'] += 1
            self.log(f"ERRO: {nome_teste} - {e}", 'ERROR')
            return False
    
    def validar_estrutura_tabelas(self):
        """Valida se todas as tabelas foram criadas."""
        self.log("Validando estrutura das tabelas...")
        
        tabelas_esperadas = [
            'parametros_wallclub_planos',
            'parametros_wallclub',
            'parametros_wallclub_futuro',
            'parametros_wallclub_historico',
            'parametros_wallclub_importacoes'
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES LIKE 'parametros_wallclub%'")
            tabelas_existentes = [row[0] for row in cursor.fetchall()]
        
        for tabela in tabelas_esperadas:
            if tabela not in tabelas_existentes:
                self.log(f"Tabela {tabela} não encontrada", 'ERROR')
                return False
        
        return True
    
    def validar_campos_decimal(self):
        """Valida se campos foram convertidos para DECIMAL."""
        self.log("Validando campos DECIMAL...")
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE, NUMERIC_PRECISION, NUMERIC_SCALE
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'wallclub'
                AND TABLE_NAME = 'parametros_wallclub'
                AND COLUMN_NAME LIKE 'parametro_%'
                AND COLUMN_NAME != 'parametro_loja_16'
            """)
            
            campos_numericos = cursor.fetchall()
        
        for campo, tipo, precisao, escala in campos_numericos:
            if tipo != 'decimal' or precisao != 10 or escala != 6:
                self.log(f"Campo {campo} não é DECIMAL(10,6): {tipo}({precisao},{escala})", 'ERROR')
                return False
        
        # Verificar parametro_loja_16 como VARCHAR
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_SCHEMA = 'wallclub'
                AND TABLE_NAME = 'parametros_wallclub'
                AND COLUMN_NAME = 'parametro_loja_16'
            """)
            
            resultado = cursor.fetchone()
            if not resultado or resultado[0] != 'varchar' or resultado[1] != 50:
                self.log("Campo parametro_loja_16 não é VARCHAR(50)", 'ERROR')
                return False
        
        return True
    
    def validar_indices(self):
        """Valida se índices foram criados."""
        self.log("Validando índices...")
        
        indices_esperados = [
            'uk_parametros_loja_plano_wall',
            'idx_parametros_loja',
            'idx_parametros_plano',
            'idx_parametros_wall',
            'idx_parametros_vigencia'
        ]
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT INDEX_NAME
                FROM INFORMATION_SCHEMA.STATISTICS
                WHERE TABLE_SCHEMA = 'wallclub'
                AND TABLE_NAME = 'parametros_wallclub'
            """)
            
            indices_existentes = [row[0] for row in cursor.fetchall()]
        
        for indice in indices_esperados:
            if indice not in indices_existentes:
                self.log(f"Índice {indice} não encontrado", 'WARNING')
        
        return True
    
    def validar_contagem_dados(self):
        """Valida contagem de dados migrados."""
        self.log("Validando contagem de dados...")
        
        # Contar planos
        count_planos = Plano.objects.count()
        self.resultados['metricas']['planos'] = count_planos
        
        if count_planos == 0:
            self.log("Nenhum plano encontrado", 'ERROR')
            return False
        
        # Contar configurações
        count_configs = ConfiguracaoVigente.objects.count()
        self.resultados['metricas']['configuracoes'] = count_configs
        
        if count_configs == 0:
            self.log("Nenhuma configuração encontrada", 'ERROR')
            return False
        
        # Métricas esperadas baseadas em testes
        if count_configs < 5000:
            self.log(f"Poucas configurações migradas: {count_configs} (esperado: ~5200)", 'WARNING')
        
        if self.verbose:
            self.log(f"Planos: {count_planos}, Configurações: {count_configs}")
        
        return True
    
    def validar_parametros_uptal_wall(self):
        """Valida se parâmetros uptal e wall foram migrados."""
        self.log("Validando parâmetros uptal e wall...")
        
        # Contar configurações com parâmetros uptal
        count_uptal = ConfiguracaoVigente.objects.exclude(parametro_uptal_1__isnull=True).count()
        self.resultados['metricas']['configs_com_uptal'] = count_uptal
        
        # Contar configurações com parâmetros wall
        count_wall = ConfiguracaoVigente.objects.exclude(parametro_wall_1__isnull=True).count()
        self.resultados['metricas']['configs_com_wall'] = count_wall
        
        if count_uptal == 0:
            self.log("Nenhuma configuração com parâmetros uptal encontrada", 'ERROR')
            return False
        
        if count_wall == 0:
            self.log("Nenhuma configuração com parâmetros wall encontrada", 'ERROR')
            return False
        
        # Verificar se as contagens são similares (devem ser iguais na maioria dos casos)
        if abs(count_uptal - count_wall) > 100:
            self.log(f"Diferença significativa entre uptal ({count_uptal}) e wall ({count_wall})", 'WARNING')
        
        if self.verbose:
            self.log(f"Configurações com uptal: {count_uptal}, com wall: {count_wall}")
        
        return True
    
    def validar_valores_decimais(self):
        """Valida se valores decimais foram convertidos corretamente."""
        self.log("Validando valores decimais...")
        
        # Buscar uma amostra de configurações com valores decimais
        configs_amostra = ConfiguracaoVigente.objects.exclude(
            parametro_loja_1__isnull=True
        )[:10]
        
        if not configs_amostra:
            self.log("Nenhuma configuração com parâmetros para validar", 'ERROR')
            return False
        
        for config in configs_amostra:
            if config.parametro_loja_1 is not None:
                if not isinstance(config.parametro_loja_1, Decimal):
                    self.log(f"Valor não é Decimal: {type(config.parametro_loja_1)}", 'ERROR')
                    return False
        
        return True
    
    def validar_integridade_referencial(self):
        """Valida integridade referencial."""
        self.log("Validando integridade referencial...")
        
        # Verificar se todas as configurações têm planos válidos
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM parametros_wallclub p
                LEFT JOIN parametros_wallclub_planos pl ON p.id_plano = pl.id
                WHERE pl.id IS NULL
            """)
            
            configs_sem_plano = cursor.fetchone()[0]
        
        if configs_sem_plano > 0:
            self.log(f"{configs_sem_plano} configurações sem plano válido", 'ERROR')
            return False
        
        return True
    
    def validar_constraints_unique(self):
        """Valida constraints de unicidade."""
        self.log("Validando constraints de unicidade...")
        
        # Verificar duplicatas na chave única (loja_id, id_plano, wall)
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT loja_id, id_plano, wall, COUNT(*)
                FROM parametros_wallclub
                GROUP BY loja_id, id_plano, wall
                HAVING COUNT(*) > 1
            """)
            
            duplicatas = cursor.fetchall()
        
        if duplicatas:
            self.log(f"{len(duplicatas)} duplicatas encontradas na chave única", 'ERROR')
            return False
        
        return True
    
    def teste_funcional_basico(self):
        """Teste funcional básico dos modelos Django."""
        self.log("Executando teste funcional básico...")
        
        try:
            # Buscar uma configuração
            config = ConfiguracaoVigente.objects.first()
            if not config:
                self.log("Nenhuma configuração para testar", 'ERROR')
                return False
            
            # Testar métodos do modelo
            parametros_dict = config.get_parametros_dict()
            if not isinstance(parametros_dict, dict):
                self.log("Método get_parametros_dict() falhou", 'ERROR')
                return False
            
            # Testar busca de parâmetro específico
            param_1 = config.get_parametro(1)
            if param_1 is not None and not isinstance(param_1, (Decimal, type(None))):
                self.log("Método get_parametro() retornou tipo incorreto", 'ERROR')
                return False
            
            return True
            
        except Exception as e:
            self.log(f"Erro no teste funcional: {e}", 'ERROR')
            return False
    
    def testar_calculadora_desconto(self):
        """Testa se a CalculadoraDesconto consegue ser instanciada e executar cálculo básico."""
        self.log("Testando CalculadoraDesconto...")
        
        try:
            # Instanciar calculadora
            calculadora = CalculadoraDesconto()
            
            # Buscar uma configuração para teste
            config = ConfiguracaoVigente.objects.first()
            if not config:
                self.log("Nenhuma configuração para testar calculadora", 'WARNING')
                return True  # Não é erro crítico se não há dados ainda
            
            # Tentar um cálculo básico (pode retornar None se não houver dados suficientes)
            resultado = calculadora.calcular_desconto(
                valor_original=100.0,
                data="2024-01-01",
                forma="PIX",
                parcelas=1,
                terminal="123456789",
                wall="s"
            )
            
            # Se chegou até aqui sem erro, a calculadora está funcional
            self.log(f"CalculadoraDesconto instanciada com sucesso. Resultado teste: {resultado}")
            return True
            
        except ImportError as e:
            self.log(f"Erro ao importar CalculadoraDesconto: {e}", 'ERROR')
            return False
        except Exception as e:
            self.log(f"Erro ao testar CalculadoraDesconto: {e}", 'ERROR')
            return False
    
    def executar_validacao_completa(self):
        """Executa validação completa."""
        self.log("=== INICIANDO VALIDAÇÃO PÓS-MIGRAÇÃO ===")
        
        # Lista de testes a executar
        testes = [
            ("Estrutura das Tabelas", self.validar_estrutura_tabelas),
            ("Campos DECIMAL", self.validar_campos_decimal),
            ("Índices", self.validar_indices),
            ("Contagem de Dados", self.validar_contagem_dados),
            ("Parâmetros Uptal/Wall", self.validar_parametros_uptal_wall),
            ("Valores Decimais", self.validar_valores_decimais),
            ("Integridade Referencial", self.validar_integridade_referencial),
            ("Constraints Unique", self.validar_constraints_unique),
            ("Teste Funcional Básico", self.teste_funcional_basico),
            ("CalculadoraDesconto", self.testar_calculadora_desconto),
        ]
        
        # Executar todos os testes
        for nome, funcao in testes:
            self.executar_teste(nome, funcao)
        
        # Gerar relatório final
        self.gerar_relatorio_final()
    
    def gerar_relatorio_final(self):
        """Gera relatório final da validação."""
        fim = datetime.now()
        duracao = fim - self.resultados['inicio']
        
        print("\n" + "=" * 60)
        print("📊 RELATÓRIO FINAL DA VALIDAÇÃO")
        print("=" * 60)
        print(f"⏱️  Duração: {duracao}")
        print(f"🧪 Testes executados: {self.resultados['testes_executados']}")
        print(f"✅ Testes passou: {self.resultados['testes_passou']}")
        print(f"❌ Testes falhou: {self.resultados['testes_falhou']}")
        
        # Métricas
        if self.resultados['metricas']:
            print("\n📈 MÉTRICAS:")
            for chave, valor in self.resultados['metricas'].items():
                print(f"   {chave}: {valor}")
        
        # Erros
        if self.resultados['erros']:
            print(f"\n❌ ERROS ({len(self.resultados['erros'])}):")
            for erro in self.resultados['erros']:
                print(f"   - {erro}")
        
        # Warnings
        if self.resultados['warnings']:
            print(f"\n⚠️  WARNINGS ({len(self.resultados['warnings'])}):")
            for warning in self.resultados['warnings']:
                print(f"   - {warning}")
        
        # Status final
        taxa_sucesso = (self.resultados['testes_passou'] / 
                       max(self.resultados['testes_executados'], 1)) * 100
        
        print(f"\n📊 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        if self.resultados['testes_falhou'] == 0:
            print("🎉 VALIDAÇÃO CONCLUÍDA COM SUCESSO!")
            status = "SUCESSO"
        else:
            print("⚠️  VALIDAÇÃO CONCLUÍDA COM PROBLEMAS!")
            status = "PROBLEMAS"
        
        print("=" * 60)
        
        return status


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validação pós-migração')
    parser.add_argument('--verbose', action='store_true', help='Logs detalhados')
    
    args = parser.parse_args()
    
    validador = ValidadorMigracao(verbose=args.verbose)
    status = validador.executar_validacao_completa()
    
    # Exit code baseado no resultado
    sys.exit(0 if status == "SUCESSO" else 1)


if __name__ == '__main__':
    main()
