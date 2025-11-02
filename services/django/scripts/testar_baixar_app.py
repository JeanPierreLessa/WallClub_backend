#!/usr/bin/env python
"""
Script para testar envio de mensagem baixar_app (WhatsApp + SMS)
"""

import os
import sys
import django

# Configurar Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wallclub.settings')
django.setup()

from wallclub_core.integracoes.whatsapp_service import WhatsAppService
from wallclub_core.integracoes.sms_service import enviar_sms
from wallclub_core.integracoes.messages_template_service import MessagesTemplateService
from wallclub_core.utilitarios.log_control import registrar_log


def testar_whatsapp_baixar_app(celular, canal_id=1):
    """
    Testa envio de WhatsApp com template baixar_app
    """
    print("\n" + "="*60)
    print("TESTE: WhatsApp - Template baixar_app")
    print("="*60)
    
    try:
        # Preparar template
        print(f"\n1. Preparando template para canal_id={canal_id}...")
        tpl = MessagesTemplateService.preparar_whatsapp(
            canal_id=canal_id,
            id_template='baixar_app'
        )
        
        if not tpl:
            print("❌ ERRO: Template não encontrado no banco de dados")
            print("   Verifique se existe registro em templates_envio_msg:")
            print("   - canal_id = 1")
            print("   - tipo = 'WHATSAPP'")
            print("   - id_template = 'baixar_app'")
            print("   - ativo = 1")
            return False
        
        print("✅ Template preparado com sucesso:")
        print(f"   - Nome template: {tpl['nome_template']}")
        print(f"   - Idioma: {tpl['idioma']}")
        print(f"   - Parâmetros corpo: {tpl['parametros_corpo']}")
        print(f"   - Parâmetros botão: {tpl['parametros_botao']}")
        
        # Enviar WhatsApp
        print(f"\n2. Enviando WhatsApp para {celular}...")
        resultado = WhatsAppService.envia_whatsapp(
            numero_telefone=celular,
            canal_id=canal_id,
            nome_template=tpl['nome_template'],
            idioma_template=tpl['idioma'],
            parametros_corpo=tpl['parametros_corpo'],
            parametros_botao=tpl['parametros_botao']
        )
        
        if resultado:
            print("✅ WhatsApp enviado com sucesso!")
            print("   Verifique o celular se a mensagem chegou.")
            print("   Se não chegou, verifique no Facebook Business Manager:")
            print("   - Status do template 'baixar_app_wallclub'")
            print("   - Qualidade do template (deve estar alta/média)")
            print("   - Se não está pausado ou rejeitado")
            return True
        else:
            print("❌ Falha ao enviar WhatsApp")
            print("   Verifique os logs em comum.integracoes.log")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def testar_sms_baixar_app(celular, canal_id=1):
    """
    Testa envio de SMS com template baixar_app
    """
    print("\n" + "="*60)
    print("TESTE: SMS - Template baixar_app")
    print("="*60)
    
    try:
        # Preparar template
        print(f"\n1. Preparando template SMS para canal_id={canal_id}...")
        tpl = MessagesTemplateService.preparar_sms(
            canal_id=canal_id,
            id_template='baixar_app'
        )
        
        if not tpl:
            print("❌ ERRO: Template SMS não encontrado no banco de dados")
            print("   Verifique se existe registro em templates_envio_msg:")
            print("   - canal_id = 1")
            print("   - tipo = 'SMS'")
            print("   - id_template = 'baixar_app'")
            print("   - ativo = 1")
            return False
        
        print("✅ Template SMS preparado:")
        print(f"   - Assunto: {tpl['assunto']}")
        print(f"   - Mensagem: {tpl['mensagem'][:50]}...")
        
        # Enviar SMS
        print(f"\n2. Enviando SMS para {celular}...")
        resultado = enviar_sms(
            telefone=celular,
            mensagem=tpl['mensagem'],
            assunto=tpl['assunto']
        )
        
        print(f"\n3. Resultado do envio:")
        print(f"   - Status: {resultado.get('status')}")
        print(f"   - Data: {resultado.get('data')}")
        print(f"   - Message: {resultado.get('message')}")
        
        if resultado.get('status') == 'success':
            print("✅ SMS enviado com sucesso!")
            return True
        else:
            print("❌ Falha ao enviar SMS")
            print("   Verifique os logs em comum.integracoes.log")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """
    Função principal
    """
    print("\n" + "="*60)
    print("SCRIPT DE TESTE - MENSAGEM BAIXAR_APP")
    print("="*60)
    
    # Obter número de celular
    celular = input("\nDigite o número do celular (apenas números): ").strip()
    
    if not celular:
        print("❌ Número de celular é obrigatório!")
        return
    
    # Testar WhatsApp
    whatsapp_ok = testar_whatsapp_baixar_app(celular)
    
    # Testar SMS
    sms_ok = testar_sms_baixar_app(celular)
    
    # Resumo
    print("\n" + "="*60)
    print("RESUMO DOS TESTES")
    print("="*60)
    print(f"WhatsApp: {'✅ OK' if whatsapp_ok else '❌ FALHOU'}")
    print(f"SMS:      {'✅ OK' if sms_ok else '❌ FALHOU'}")
    print("="*60)
    
    if whatsapp_ok or sms_ok:
        print("\n✅ Pelo menos um canal funcionou!")
    else:
        print("\n❌ Nenhum canal funcionou. Verifique os logs.")
    
    print("\nPara ver logs detalhados, execute:")
    print("  tail -f logs/comum.integracoes.log")
    print("  tail -f logs/posp2.log")


if __name__ == '__main__':
    main()
