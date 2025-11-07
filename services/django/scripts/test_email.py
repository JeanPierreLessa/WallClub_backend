#!/usr/bin/env python
"""
Script para testar envio de email
Uso: python scripts/test_email.py
"""
import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings.portais')
django.setup()

from django.conf import settings
from wallclub_core.integracoes.email_service import EmailService
from wallclub_core.utilitarios.log_control import registrar_log


def test_email_simples():
    """Teste 1: Email simples sem template"""
    print("\n" + "="*60)
    print("TESTE 1: Email Simples (sem template)")
    print("="*60)
    
    try:
        resultado = EmailService.enviar_email_simples(
            destinatario='jeanpierre.lessa@gmail.com',
            assunto='Teste WallClub - Email Simples',
            mensagem='Este é um email de teste do sistema WallClub.'
        )
        
        print(f"✅ Resultado: {resultado}")
        return resultado.get('sucesso', False)
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_email_template():
    """Teste 2: Email com template HTML"""
    print("\n" + "="*60)
    print("TESTE 2: Email com Template HTML")
    print("="*60)
    
    try:
        # Criar token fake para teste
        from checkout.link_pagamento_web.models import CheckoutToken
        from decimal import Decimal
        from django.utils import timezone
        from datetime import timedelta
        
        token_obj = CheckoutToken.objects.create(
            token='TEST_TOKEN_123456',
            loja_id=1,
            item_nome='Teste de Pagamento',
            item_valor=Decimal('100.00'),
            nome_completo='Jean Pierre Teste',
            cpf='12345678901',
            celular='21999999999',
            endereco_completo='Rua Teste, 123',
            expires_at=timezone.now() + timedelta(minutes=30),
            created_by='Script Teste'
        )
        
        context = {
            'cliente_nome': 'Jean Pierre',
            'loja_nome': 'Loja Teste',
            'valor': Decimal('100.00'),
            'item_nome': 'Teste de Pagamento',
            'checkout_url': f'https://checkout.wallclub.com.br/checkout/{token_obj.token}/',
            'validade_minutos': 30
        }
        
        resultado = EmailService.enviar_email(
            destinatarios=['jeanpierre.lessa@gmail.com'],
            assunto='Teste WallClub - Link de Pagamento',
            template_html='checkout/emails/link_pagamento.html',  # Caminho correto
            template_context=context,
            fail_silently=False
        )
        
        print(f"✅ Resultado: {resultado}")
        
        # Limpar token de teste
        token_obj.delete()
        
        return resultado.get('sucesso', False)
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_configuracao_email():
    """Teste 3: Verificar configurações de email"""
    print("\n" + "="*60)
    print("TESTE 3: Configurações de Email")
    print("="*60)
    
    configs = {
        'EMAIL_BACKEND': getattr(settings, 'EMAIL_BACKEND', 'NÃO CONFIGURADO'),
        'EMAIL_HOST': getattr(settings, 'EMAIL_HOST', 'NÃO CONFIGURADO'),
        'EMAIL_PORT': getattr(settings, 'EMAIL_PORT', 'NÃO CONFIGURADO'),
        'EMAIL_USE_TLS': getattr(settings, 'EMAIL_USE_TLS', 'NÃO CONFIGURADO'),
        'EMAIL_USE_SSL': getattr(settings, 'EMAIL_USE_SSL', 'NÃO CONFIGURADO'),
        'EMAIL_HOST_USER': getattr(settings, 'EMAIL_HOST_USER', 'NÃO CONFIGURADO'),
        'EMAIL_HOST_PASSWORD': '***' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else 'NÃO CONFIGURADO',
        'DEFAULT_FROM_EMAIL': getattr(settings, 'DEFAULT_FROM_EMAIL', 'NÃO CONFIGURADO'),
    }
    
    for key, value in configs.items():
        print(f"{key}: {value}")
    
    # Verificar se está usando AWS SES
    if 'ses' in str(configs['EMAIL_BACKEND']).lower():
        print("\n⚠️  Usando AWS SES")
        print("Verifique:")
        print("1. Conta AWS SES está em modo PRODUÇÃO (não sandbox)")
        print("2. Email remetente está verificado")
        print("3. Email destinatário está verificado (se em sandbox)")
        print("4. Credenciais AWS estão corretas")
    
    return True


def test_template_existe():
    """Teste 4: Verificar se template existe"""
    print("\n" + "="*60)
    print("TESTE 4: Verificar Template")
    print("="*60)
    
    from django.template.loader import get_template
    
    templates = [
        'emails/checkout/link_pagamento.html',
        'checkout/emails/link_pagamento.html',
    ]
    
    for template_path in templates:
        try:
            template = get_template(template_path)
            print(f"✅ Template encontrado: {template_path}")
            print(f"   Origem: {template.origin.name if hasattr(template, 'origin') else 'N/A'}")
            return True
        except Exception as e:
            print(f"❌ Template não encontrado: {template_path}")
            print(f"   Erro: {str(e)}")
    
    return False


def test_usuario_cadastro():
    """Teste 5: Criar usuário e enviar email de boas-vindas"""
    print("\n" + "="*60)
    print("TESTE 5: Email de Cadastro de Usuário")
    print("="*60)
    
    try:
        from apps.cliente.models import Cliente
        from django.utils import timezone
        
        # Verificar se já existe
        cpf_teste = '12345678901'
        cliente = Cliente.objects.filter(cpf=cpf_teste).first()
        
        if not cliente:
            # Criar cliente de teste
            cliente = Cliente.objects.create(
                cpf=cpf_teste,
                nome='Usuario Teste Email',
                email='jeanpierre.lessa@gmail.com',
                celular='21999999999',
                canal_id=1,
                ativo=True
            )
            print(f"✅ Cliente criado: {cliente.id}")
        else:
            print(f"ℹ️  Cliente já existe: {cliente.id}")
        
        # Enviar email de boas-vindas
        resultado = EmailService.enviar_email_simples(
            destinatario=cliente.email,
            assunto='Bem-vindo ao WallClub!',
            mensagem=f'Olá {cliente.nome}!\n\nSeu cadastro foi realizado com sucesso.\n\nEquipe WallClub'
        )
        
        print(f"✅ Resultado: {resultado}")
        return resultado.get('sucesso', False)
        
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes"""
    print("\n" + "="*60)
    print("SCRIPT DE TESTE DE EMAIL - WALLCLUB")
    print("="*60)
    
    resultados = {
        'Configuração': test_configuracao_email(),
        'Template': test_template_existe(),
        'Email Simples': test_email_simples(),
        'Email Template': test_email_template(),
        'Email Usuário': test_usuario_cadastro(),
    }
    
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    
    for teste, sucesso in resultados.items():
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        print(f"{teste}: {status}")
    
    total = len(resultados)
    passou = sum(1 for s in resultados.values() if s)
    
    print(f"\nTotal: {passou}/{total} testes passaram")
    
    if passou == total:
        print("\n🎉 Todos os testes passaram!")
        return 0
    else:
        print("\n⚠️  Alguns testes falharam. Verifique os logs acima.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
