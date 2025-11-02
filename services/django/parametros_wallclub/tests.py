from django.test import TestCase
from decimal import Decimal
from django.utils import timezone
from .models import ConfiguracaoLoja
from .services import (
    ConfiguracaoLojaService, 
    CalculadoraDesconto, 
    CalculadoraComissao, 
    CalculadoraFinanceira
)


class ConfiguracaoLojaServiceTest(TestCase):
    """Testes para o serviço de configuração de loja"""
    
    def setUp(self):
        """Criar configuração de teste"""
        self.config = ConfiguracaoLoja.objects.create(
            loja_id=123,
            wall='S',
            id_desc=1001,
            # Parâmetros de teste - simulando dados reais
            loja_param_1=Decimal('30'),  # Prazo limite
            loja_param_2=Decimal('0.0123'),  # MDR
            loja_param_7=Decimal('0.0713'),  # Desconto cliente
            loja_param_10=Decimal('0.0215'),  # Cashback
            wall_param_10=Decimal('0.0150'),  # Comissão wall
            clientesf_param_2=Decimal('0.0050'),  # Repasse cliente
            ativo=True
        )
        self.service = ConfiguracaoLojaService()
    
    def test_get_configuracao_existente(self):
        """Testa busca de configuração existente"""
        config = self.service.get_configuracao(123, 'S')
        self.assertIsNotNone(config)
        self.assertEqual(config.loja_id, 123)
        self.assertEqual(config.wall, 'S')
    
    def test_get_configuracao_inexistente(self):
        """Testa busca de configuração inexistente"""
        config = self.service.get_configuracao(999, 'S')
        self.assertIsNone(config)
    
    def test_get_parametro_por_codigo_loja(self):
        """Testa busca de parâmetro da tabela loja"""
        valor = self.service.get_parametro_por_codigo(self.config, 7, 'loja')
        self.assertEqual(valor, Decimal('0.0713'))
    
    def test_get_parametro_por_codigo_wall(self):
        """Testa busca de parâmetro da tabela wall"""
        valor = self.service.get_parametro_por_codigo(self.config, 10, 'wall')
        self.assertEqual(valor, Decimal('0.0150'))
    
    def test_get_parametro_por_codigo_clientesf(self):
        """Testa busca de parâmetro da tabela clientesf"""
        valor = self.service.get_parametro_por_codigo(self.config, 2, 'clientesf')
        self.assertEqual(valor, Decimal('0.0050'))
    
    def test_get_parametro_inexistente(self):
        """Testa busca de parâmetro inexistente"""
        valor = self.service.get_parametro_por_codigo(self.config, 999, 'loja')
        self.assertIsNone(valor)


class CalculadoraDescontoTest(TestCase):
    """Testes para a calculadora de desconto"""
    
    def setUp(self):
        """Criar configuração e calculadora de teste"""
        self.config = ConfiguracaoLoja.objects.create(
            loja_id=123,
            wall='S',
            id_desc=1001,
            # Parâmetros baseados em dados reais do sistema
            loja_param_1=Decimal('30'),  # Prazo limite parcelas
            loja_param_7=Decimal('0.0713'),  # Desconto cliente 7.13%
            loja_param_10=Decimal('0.0215'),  # Cashback 2.15%
            ativo=True
        )
        self.calculadora = CalculadoraDesconto()
    
    def test_calcular_pix(self):
        """Testa cálculo para PIX"""
        resultado = self.calculadora.calcular(
            valor=Decimal('100.00'),
            forma_pagamento='PIX',
            parcelas=0,
            loja_id=123,
            wall='S'
        )
        
        # PIX deve aplicar desconto de 7.13%
        self.assertEqual(resultado['forma_pagamento'], 'PIX')
        self.assertEqual(resultado['parcelas'], 0)
        self.assertEqual(resultado['valor_original'], Decimal('100.00'))
        self.assertEqual(resultado['desconto_percentual'], Decimal('7.13'))
        self.assertEqual(resultado['valor_liquido'], Decimal('92.87'))
        self.assertEqual(resultado['desconto_valor'], Decimal('7.13'))
    
    def test_calcular_debito(self):
        """Testa cálculo para débito"""
        resultado = self.calculadora.calcular(
            valor=Decimal('100.00'),
            forma_pagamento='DEBITO',
            parcelas=0,
            loja_id=123,
            wall='S'
        )
        
        # Débito normalmente não tem desconto
        self.assertEqual(resultado['forma_pagamento'], 'DEBITO')
        self.assertEqual(resultado['parcelas'], 0)
        self.assertEqual(resultado['valor_original'], Decimal('100.00'))
        self.assertEqual(resultado['valor_liquido'], Decimal('100.00'))
        self.assertEqual(resultado['desconto_percentual'], Decimal('0'))
    
    def test_calcular_credito_vista(self):
        """Testa cálculo para crédito à vista"""
        resultado = self.calculadora.calcular(
            valor=Decimal('100.00'),
            forma_pagamento='A VISTA',
            parcelas=1,
            loja_id=123,
            wall='S'
        )
        
        # Crédito à vista deve aplicar desconto
        self.assertEqual(resultado['forma_pagamento'], 'CREDITO_VISTA')
        self.assertEqual(resultado['parcelas'], 1)
        self.assertEqual(resultado['desconto_percentual'], Decimal('7.13'))
        self.assertEqual(resultado['valor_liquido'], Decimal('92.87'))
    
    def test_calcular_parcelado_dentro_prazo(self):
        """Testa cálculo parcelado dentro do prazo limite"""
        resultado = self.calculadora.calcular(
            valor=Decimal('100.00'),
            forma_pagamento='PARCELADO',
            parcelas=12,  # Dentro do prazo limite (30)
            loja_id=123,
            wall='S'
        )
        
        # Dentro do prazo: aplica desconto cliente
        self.assertEqual(resultado['forma_pagamento'], 'PARCELADO')
        self.assertEqual(resultado['parcelas'], 12)
        self.assertEqual(resultado['prazo_limite'], 30)
        self.assertEqual(resultado['desconto_percentual'], Decimal('7.13'))
        self.assertEqual(resultado['valor_liquido'], Decimal('92.87'))
    
    def test_calcular_parcelado_fora_prazo(self):
        """Testa cálculo parcelado fora do prazo limite"""
        resultado = self.calculadora.calcular(
            valor=Decimal('100.00'),
            forma_pagamento='PARCELADO',
            parcelas=36,  # Fora do prazo limite (30)
            loja_id=123,
            wall='S'
        )
        
        # Fora do prazo: sem desconto cliente
        self.assertEqual(resultado['forma_pagamento'], 'PARCELADO')
        self.assertEqual(resultado['parcelas'], 36)
        self.assertEqual(resultado['prazo_limite'], 30)
        self.assertEqual(resultado['desconto_percentual'], Decimal('0'))
        self.assertEqual(resultado['valor_liquido'], Decimal('100.00'))
    
    def test_normalizar_forma_pagamento(self):
        """Testa normalização das formas de pagamento"""
        calc = self.calculadora
        
        # PIX
        self.assertEqual(calc._normalizar_forma_pagamento('pix', 0), 'PIX')
        
        # Débito
        self.assertEqual(calc._normalizar_forma_pagamento('debito', 0), 'DEBITO')
        
        # Crédito à vista
        self.assertEqual(calc._normalizar_forma_pagamento('credito', 1), 'CREDITO_VISTA')
        self.assertEqual(calc._normalizar_forma_pagamento('a vista', 1), 'CREDITO_VISTA')
        
        # Parcelado
        self.assertEqual(calc._normalizar_forma_pagamento('credito', 6), 'PARCELADO')
        self.assertEqual(calc._normalizar_forma_pagamento('parcelado', 12), 'PARCELADO')
    
    def test_configuracao_inexistente(self):
        """Testa erro quando configuração não existe"""
        with self.assertRaises(ValueError) as context:
            self.calculadora.calcular(
                valor=Decimal('100.00'),
                forma_pagamento='PIX',
                parcelas=0,
                loja_id=999,  # Loja inexistente
                wall='S'
            )
        
        self.assertIn('Configuração não encontrada', str(context.exception))


class CalculadoraComissaoTest(TestCase):
    """Testes para a calculadora de comissão"""
    
    def setUp(self):
        """Criar configuração de teste"""
        self.config = ConfiguracaoLoja.objects.create(
            loja_id=123,
            wall='S',
            id_desc=1001,
            wall_param_10=Decimal('0.0150'),  # Comissão wall 1.5%
            clientesf_param_2=Decimal('0.0050'),  # Repasse cliente 0.5%
            ativo=True
        )
        self.calculadora = CalculadoraComissao()
    
    def test_calcular_comissao_wall(self):
        """Testa cálculo de comissão wall"""
        resultado = self.calculadora.calcular_comissao_wall(
            valor=Decimal('100.00'),
            loja_id=123
        )
        
        self.assertEqual(resultado['comissao'], Decimal('1.50'))
        self.assertEqual(resultado['percentual'], Decimal('1.50'))
        self.assertEqual(resultado['valor_base'], Decimal('100.00'))
    
    def test_calcular_repasse_cliente(self):
        """Testa cálculo de repasse cliente"""
        resultado = self.calculadora.calcular_repasse_cliente(
            valor=Decimal('100.00'),
            loja_id=123
        )
        
        self.assertEqual(resultado['repasse'], Decimal('0.50'))
        self.assertEqual(resultado['percentual'], Decimal('0.50'))
        self.assertEqual(resultado['valor_base'], Decimal('100.00'))
    
    def test_configuracao_inexistente(self):
        """Testa comportamento com configuração inexistente"""
        resultado_wall = self.calculadora.calcular_comissao_wall(
            valor=Decimal('100.00'),
            loja_id=999
        )
        
        resultado_cliente = self.calculadora.calcular_repasse_cliente(
            valor=Decimal('100.00'),
            loja_id=999
        )
        
        # Deve retornar zero quando não há configuração
        self.assertEqual(resultado_wall['comissao'], Decimal('0'))
        self.assertEqual(resultado_cliente['repasse'], Decimal('0'))


class CalculadoraFinanceiraTest(TestCase):
    """Testes para a calculadora financeira integrada"""
    
    def setUp(self):
        """Criar configuração completa de teste"""
        self.config = ConfiguracaoLoja.objects.create(
            loja_id=123,
            wall='S',
            id_desc=1001,
            loja_param_1=Decimal('30'),
            loja_param_7=Decimal('0.0713'),
            loja_param_10=Decimal('0.0215'),
            wall_param_10=Decimal('0.0150'),
            clientesf_param_2=Decimal('0.0050'),
            ativo=True
        )
        self.calculadora = CalculadoraFinanceira()
    
    def test_calcular_transacao_completa_pix(self):
        """Testa cálculo completo para PIX"""
        resultado = self.calculadora.calcular_transacao_completa(
            valor=Decimal('100.00'),
            forma_pagamento='PIX',
            parcelas=0,
            loja_id=123,
            wall='S'
        )
        
        # Verificar dados básicos
        self.assertEqual(resultado['forma_pagamento'], 'PIX')
        self.assertEqual(resultado['valor_original'], Decimal('100.00'))
        self.assertEqual(resultado['valor_liquido'], Decimal('92.87'))
        
        # Verificar comissões (wall = 'S')
        self.assertEqual(resultado['comissao'], Decimal('1.50'))
        self.assertEqual(resultado['repasse'], Decimal('0.50'))
        
        # Verificar metadados
        self.assertEqual(resultado['wall'], 'S')
        self.assertEqual(resultado['loja_id'], 123)
        self.assertIsNotNone(resultado['calculado_em'])
    
    def test_calcular_transacao_completa_sem_wall(self):
        """Testa cálculo completo sem wall"""
        resultado = self.calculadora.calcular_transacao_completa(
            valor=Decimal('100.00'),
            forma_pagamento='PIX',
            parcelas=0,
            loja_id=123,
            wall='N'  # Sem wall
        )
        
        # Verificar que não há comissões wall
        self.assertNotIn('comissao', resultado)
        self.assertNotIn('repasse', resultado)
        self.assertEqual(resultado['wall'], 'N')


class IntegracaoTest(TestCase):
    """Testes de integração simulando cenários reais"""
    
    def setUp(self):
        """Criar múltiplas configurações de teste"""
        # Loja com wall
        self.loja_wall = ConfiguracaoLoja.objects.create(
            loja_id=100,
            wall='S',
            id_desc=1001,
            loja_param_1=Decimal('24'),  # Prazo 24 parcelas
            loja_param_7=Decimal('0.0713'),  # Desconto 7.13%
            loja_param_10=Decimal('0.0215'),
            wall_param_10=Decimal('0.0150'),
            clientesf_param_2=Decimal('0.0050'),
            ativo=True
        )
        
        # Loja sem wall
        self.loja_sem_wall = ConfiguracaoLoja.objects.create(
            loja_id=200,
            wall='N',
            id_desc=2001,
            loja_param_1=Decimal('12'),  # Prazo 12 parcelas
            loja_param_7=Decimal('0.0500'),  # Desconto 5%
            ativo=True
        )
        
        self.calc_financeira = CalculadoraFinanceira()
    
    def test_cenario_real_mastercard_12x(self):
        """Simula transação real: Mastercard 12x parcelado"""
        resultado = self.calc_financeira.calcular_transacao_completa(
            valor=Decimal('1200.00'),
            forma_pagamento='PARCELADO',
            parcelas=12,
            loja_id=100,  # Com wall
            wall='S'
        )
        
        # 12 parcelas <= 24 (prazo limite): aplica desconto
        self.assertEqual(resultado['parcelas'], 12)
        self.assertEqual(resultado['prazo_limite'], 24)
        self.assertEqual(resultado['desconto_percentual'], Decimal('7.13'))
        
        # Valor líquido: 1200 - (1200 * 0.0713)
        valor_esperado = Decimal('1114.44')
        self.assertEqual(resultado['valor_liquido'], valor_esperado)
        
        # Comissões
        self.assertEqual(resultado['comissao'], Decimal('18.00'))  # 1200 * 1.5%
        self.assertEqual(resultado['repasse'], Decimal('6.00'))   # 1200 * 0.5%
    
    def test_cenario_real_pix_sem_wall(self):
        """Simula transação PIX sem wall"""
        resultado = self.calc_financeira.calcular_transacao_completa(
            valor=Decimal('500.00'),
            forma_pagamento='PIX',
            parcelas=0,
            loja_id=200,  # Sem wall
            wall='N'
        )
        
        # Verificar cálculo básico
        self.assertEqual(resultado['forma_pagamento'], 'PIX')
        self.assertEqual(resultado['desconto_percentual'], Decimal('5.00'))
        self.assertEqual(resultado['valor_liquido'], Decimal('475.00'))
        
        # Sem comissões wall
        self.assertNotIn('comissao', resultado)
        self.assertEqual(resultado['wall'], 'N')
    
    def test_performance_multiplas_transacoes(self):
        """Testa performance com múltiplas transações"""
        import time
        
        start_time = time.time()
        
        # Simular 100 transações
        for i in range(100):
            self.calc_financeira.calcular_transacao_completa(
                valor=Decimal('100.00'),
                forma_pagamento='PIX',
                parcelas=0,
                loja_id=100,
                wall='S'
            )
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Deve processar 100 transações em menos de 1 segundo
        self.assertLess(duration, 1.0, "Performance inadequada para múltiplas transações")
