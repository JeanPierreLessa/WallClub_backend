#!/usr/bin/env python3
"""
Script de Validação de Cálculos Pós-Migração
Baseado em comparar_django_vs_php.py, adaptado para produção

Valida se os cálculos da CalculadoraDesconto migrada mantêm paridade com PHP.
"""

import os
import sys
import django
import requests
import json
from datetime import datetime
from decimal import Decimal

# Configurar Django para PRODUÇÃO
sys.path.append('/var/www/wallclub_django')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.production')
django.setup()

from parametros_wallclub.services import CalculadoraDesconto


class ValidadorCalculos:
    """Validador de cálculos Django vs PHP."""
    
    def __init__(self, endpoint_php=None, verbose=False):
        self.endpoint_php = endpoint_php or "https://wallclub.com.br/apps/calcula_desconto_parcela_para_teste.php"
        self.verbose = verbose
        self.calculadora = CalculadoraDesconto()
        self.resultados = {
            'inicio': datetime.now(),
            'total_testes': 0,
            'sucessos': 0,
            'divergencias': 0,
            'erros_django': 0,
            'erros_php': 0,
            'detalhes_divergencias': [],
            'detalhes_erros': []
        }
    
    def log(self, mensagem, tipo='INFO'):
        """Log com timestamp."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        prefixo = {
            'INFO': '📋',
            'SUCCESS': '✅',
            'ERROR': '❌',
            'WARNING': '⚠️',
            'DIVERGENCIA': '🔍'
        }.get(tipo, '📋')
        
        print(f"[{timestamp}] {prefixo} {mensagem}")
    
    def chamar_django(self, valor, data, forma, parcelas, terminal, wall):
        """Chama a CalculadoraDesconto Django."""
        try:
            resultado = self.calculadora.calcular_desconto(
                valor_original=float(valor),
                data=data,
                forma=forma,
                parcelas=int(parcelas),
                terminal=terminal,
                wall=wall
            )
            
            if resultado is None:
                return None, "Nenhum resultado (dados insuficientes)"
            
            # Extrair valor final baseado na forma de pagamento
            if isinstance(resultado, dict):
                if forma.upper() in ['PIX', 'DÉBITO', 'DEBITO']:
                    valor_final = resultado.get('valor_pix_debito')
                else:
                    valor_final = resultado.get('valor_cartao_credito')
                
                if valor_final is not None:
                    return float(valor_final), None
            
            # Se resultado é um número direto
            if isinstance(resultado, (int, float, Decimal)):
                return float(resultado), None
            
            return None, f"Formato de resultado inesperado: {type(resultado)}"
            
        except Exception as e:
            return None, str(e)
    
    def chamar_php(self, valor, data, forma, parcelas, terminal, wall):
        """Chama o endpoint PHP."""
        try:
            payload = {
                'valoro': valor,
                'data': data,
                'forma': forma,
                'parcelas': parcelas,
                'terminal': terminal,
                'wall': wall
            }
            
            response = requests.post(self.endpoint_php, data=payload, timeout=10)
            
            if response.status_code != 200:
                return None, f"HTTP {response.status_code}"
            
            try:
                data_response = response.json()
            except json.JSONDecodeError:
                return None, "Resposta não é JSON válido"
            
            if not data_response.get('sucesso'):
                erro = data_response.get('erro', 'Erro desconhecido')
                return None, f"PHP retornou erro: {erro}"
            
            resultado = data_response.get('resultado')
            if resultado is None:
                return None, "PHP retornou resultado nulo"
            
            return float(resultado), None
            
        except requests.exceptions.Timeout:
            return None, "Timeout na requisição"
        except requests.exceptions.RequestException as e:
            return None, f"Erro de requisição: {e}"
        except Exception as e:
            return None, f"Erro inesperado: {e}"
    
    def comparar_resultado(self, django_valor, php_valor, tolerancia=0.01):
        """Compara resultados Django vs PHP."""
        if django_valor is None and php_valor is None:
            return True, 0.0
        
        if django_valor is None or php_valor is None:
            return False, float('inf')
        
        diferenca_abs = abs(django_valor - php_valor)
        diferenca_perc = (diferenca_abs / max(abs(php_valor), 0.01)) * 100
        
        return diferenca_abs <= tolerancia, diferenca_perc
    
    def testar_caso(self, valor, data, forma, parcelas, terminal, wall, loja_id=None):
        """Testa um caso específico."""
        self.resultados['total_testes'] += 1
        
        # Chamar Django
        django_valor, django_erro = self.chamar_django(valor, data, forma, parcelas, terminal, wall)
        
        # Chamar PHP
        php_valor, php_erro = self.chamar_php(valor, data, forma, parcelas, terminal, wall)
        
        # Analisar resultados
        if django_erro:
            self.resultados['erros_django'] += 1
            self.resultados['detalhes_erros'].append({
                'tipo': 'django',
                'caso': f"{forma} {parcelas}x R${valor} (terminal {terminal}, wall {wall})",
                'erro': django_erro
            })
        
        if php_erro:
            self.resultados['erros_php'] += 1
            self.resultados['detalhes_erros'].append({
                'tipo': 'php',
                'caso': f"{forma} {parcelas}x R${valor} (terminal {terminal}, wall {wall})",
                'erro': php_erro
            })
        
        # Se ambos falharam ou ambos deram certo, comparar
        if django_valor is not None and php_valor is not None:
            igual, diferenca_perc = self.comparar_resultado(django_valor, php_valor)
            
            if igual:
                self.resultados['sucessos'] += 1
                if self.verbose:
                    self.log(f"✅ {forma} {parcelas}x: Django R${django_valor:.2f} = PHP R${php_valor:.2f}")
            else:
                self.resultados['divergencias'] += 1
                self.resultados['detalhes_divergencias'].append({
                    'caso': f"{forma} {parcelas}x R${valor} (terminal {terminal}, wall {wall})",
                    'django': django_valor,
                    'php': php_valor,
                    'diferenca_perc': diferenca_perc,
                    'loja_id': loja_id
                })
                
                self.log(f"🔍 DIVERGÊNCIA {forma} {parcelas}x: Django R${django_valor:.2f} vs PHP R${php_valor:.2f} ({diferenca_perc:.1f}%)", 'DIVERGENCIA')
        
        elif django_valor is not None and php_valor is None:
            # Django funcionou, PHP falhou
            if self.verbose:
                self.log(f"⚠️ {forma} {parcelas}x: Django R${django_valor:.2f}, PHP falhou: {php_erro}", 'WARNING')
        
        elif django_valor is None and php_valor is not None:
            # PHP funcionou, Django falhou  
            if self.verbose:
                self.log(f"⚠️ {forma} {parcelas}x: PHP R${php_valor:.2f}, Django falhou: {django_erro}", 'WARNING')
    
    def executar_testes_basicos(self):
        """Executa testes básicos de validação."""
        self.log("Executando testes básicos de validação...")
        
        # Casos de teste básicos
        casos_teste = [
            # PIX/Débito
            (100.0, "2024-01-15", "PIX", 1, "123456789", "s"),
            (500.0, "2024-01-15", "DÉBITO", 1, "123456789", "s"),
            
            # Crédito à vista
            (100.0, "2024-01-15", "CRÉDITO", 1, "123456789", "s"),
            (500.0, "2024-01-15", "CRÉDITO", 1, "123456789", "n"),
            
            # Parcelado
            (300.0, "2024-01-15", "PARCELADO", 2, "123456789", "s"),
            (600.0, "2024-01-15", "PARCELADO", 3, "123456789", "s"),
            (1000.0, "2024-01-15", "PARCELADO", 6, "123456789", "n"),
            (2000.0, "2024-01-15", "PARCELADO", 12, "123456789", "n"),
        ]
        
        for valor, data, forma, parcelas, terminal, wall in casos_teste:
            self.testar_caso(valor, data, forma, parcelas, terminal, wall)
    
    def executar_testes_terminais_reais(self):
        """Executa testes com terminais reais do banco."""
        self.log("Executando testes com terminais reais...")
        
        # Buscar alguns terminais reais do banco
        try:
            from django.db import connections
            
            # Conectar ao banco legado para buscar terminais
            cursor = connections['default'].cursor()
            cursor.execute("""
                SELECT DISTINCT terminal, loja_id 
                FROM parametros_wallclub 
                WHERE terminal IS NOT NULL 
                LIMIT 5
            """)
            
            terminais_reais = cursor.fetchall()
            
            if not terminais_reais:
                self.log("Nenhum terminal real encontrado, usando terminais de teste", 'WARNING')
                terminais_reais = [("123456789", 1), ("987654321", 7)]
            
        except Exception as e:
            self.log(f"Erro ao buscar terminais reais: {e}", 'WARNING')
            terminais_reais = [("123456789", 1), ("987654321", 7)]
        
        # Testar com terminais reais
        for terminal, loja_id in terminais_reais[:3]:  # Limitar a 3 terminais
            for forma, parcelas in [("PIX", 1), ("CRÉDITO", 1), ("PARCELADO", 3)]:
                for wall in ["s", "n"]:
                    self.testar_caso(100.0, "2024-01-15", forma, parcelas, terminal, wall, loja_id)
    
    def gerar_relatorio_final(self):
        """Gera relatório final da validação."""
        fim = datetime.now()
        duracao = fim - self.resultados['inicio']
        
        print("\n" + "=" * 70)
        print("📊 RELATÓRIO FINAL - VALIDAÇÃO DE CÁLCULOS")
        print("=" * 70)
        print(f"⏱️  Duração: {duracao}")
        print(f"🧪 Total de testes: {self.resultados['total_testes']}")
        print(f"✅ Sucessos: {self.resultados['sucessos']}")
        print(f"🔍 Divergências: {self.resultados['divergencias']}")
        print(f"❌ Erros Django: {self.resultados['erros_django']}")
        print(f"❌ Erros PHP: {self.resultados['erros_php']}")
        
        # Taxa de paridade
        if self.resultados['total_testes'] > 0:
            taxa_sucesso = (self.resultados['sucessos'] / self.resultados['total_testes']) * 100
            print(f"📈 Taxa de paridade: {taxa_sucesso:.1f}%")
            
            # Verificar se está dentro do esperado (94.5%)
            if taxa_sucesso >= 94.0:
                print("🎉 PARIDADE DENTRO DO ESPERADO (≥94%)")
                status = "SUCESSO"
            elif taxa_sucesso >= 90.0:
                print("⚠️  PARIDADE ACEITÁVEL (≥90%)")
                status = "ACEITAVEL"
            else:
                print("❌ PARIDADE BAIXA (<90%)")
                status = "PROBLEMAS"
        else:
            print("❌ NENHUM TESTE EXECUTADO")
            status = "ERRO"
        
        # Detalhes das divergências
        if self.resultados['detalhes_divergencias']:
            print(f"\n🔍 DIVERGÊNCIAS DETALHADAS ({len(self.resultados['detalhes_divergencias'])}):")
            for i, div in enumerate(self.resultados['detalhes_divergencias'][:10], 1):  # Mostrar só as 10 primeiras
                print(f"   {i}. {div['caso']}")
                print(f"      Django: R${div['django']:.2f} | PHP: R${div['php']:.2f} | Diff: {div['diferenca_perc']:.1f}%")
            
            if len(self.resultados['detalhes_divergencias']) > 10:
                print(f"   ... e mais {len(self.resultados['detalhes_divergencias']) - 10} divergências")
        
        # Detalhes dos erros
        if self.resultados['detalhes_erros']:
            print(f"\n❌ ERROS DETALHADOS ({len(self.resultados['detalhes_erros'])}):")
            for i, erro in enumerate(self.resultados['detalhes_erros'][:5], 1):  # Mostrar só os 5 primeiros
                print(f"   {i}. [{erro['tipo'].upper()}] {erro['caso']}")
                print(f"      Erro: {erro['erro']}")
            
            if len(self.resultados['detalhes_erros']) > 5:
                print(f"   ... e mais {len(self.resultados['detalhes_erros']) - 5} erros")
        
        print("=" * 70)
        return status
    
    def executar_validacao_completa(self):
        """Executa validação completa dos cálculos."""
        self.log("=== INICIANDO VALIDAÇÃO DE CÁLCULOS ===")
        
        # Testar se a calculadora pode ser instanciada
        try:
            self.calculadora = CalculadoraDesconto()
            self.log("CalculadoraDesconto instanciada com sucesso")
        except Exception as e:
            self.log(f"ERRO CRÍTICO: Não foi possível instanciar CalculadoraDesconto: {e}", 'ERROR')
            return "ERRO"
        
        # Executar testes
        self.executar_testes_basicos()
        self.executar_testes_terminais_reais()
        
        # Gerar relatório
        status = self.gerar_relatorio_final()
        return status


def main():
    """Função principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validação de cálculos pós-migração')
    parser.add_argument('--endpoint', help='Endpoint PHP para comparação')
    parser.add_argument('--verbose', action='store_true', help='Logs detalhados')
    
    args = parser.parse_args()
    
    validador = ValidadorCalculos(
        endpoint_php=args.endpoint,
        verbose=args.verbose
    )
    
    status = validador.executar_validacao_completa()
    
    # Exit code baseado no resultado
    if status == "SUCESSO":
        sys.exit(0)
    elif status == "ACEITAVEL":
        sys.exit(1)  # Warning
    else:
        sys.exit(2)  # Error


if __name__ == '__main__':
    main()
