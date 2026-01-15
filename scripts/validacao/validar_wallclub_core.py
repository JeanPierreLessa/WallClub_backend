#!/usr/bin/env python3
"""
scripts/validacao/validar_wallclub_core.py
Valida estrutura do wallclub_core conforme documentação
"""

import os

# Documentado em README.md e ARQUITETURA.md
ESTRUTURA_DOCUMENTADA = {
    'database': ['queries.py'],
    'decorators': ['api_decorators.py'],
    'estr_organizacional': [],  # Vários arquivos, verificar existência do diretório
    'integracoes': [
        'apn_service.py',
        'bureau_service.py',
        'email_service.py',
        'firebase_service.py',
        'sms_service.py',
        'whatsapp_service.py',
        'config_manager.py',
        'notification_service.py',
        'api_interna_service.py',
    ],
    'middleware': [
        'security_middleware.py',
        'security_validation.py',
        'session_timeout.py',
        'subdomain_router.py',
    ],
    'oauth': ['decorators.py', 'jwt_utils.py', 'models.py', 'services.py'],
    'seguranca': [
        'services_2fa.py',
        'services_device.py',
        'rate_limiter_2fa.py',
        'validador_cpf.py',
    ],
    'services': ['auditoria_service.py'],
    'templatetags': ['formatacao_tags.py'],
    'utilitarios': [
        'config_manager.py',
        'export_utils.py',
        'formatacao.py',
        'log_control.py',
    ],
}

def validar_wallclub_core():
    print("=== VALIDAÇÃO: Estrutura wallclub_core ===\n")

    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    core_path = os.path.join(base_path, 'services', 'core', 'wallclub_core')

    if not os.path.exists(core_path):
        core_path = '/Users/jeanlessa/wall_projects/WallClub_backend/services/core/wallclub_core'

    if not os.path.exists(core_path):
        print(f"❌ ERRO: Diretório não encontrado: {core_path}")
        return

    print(f"📁 Verificando: {core_path}\n")

    divergencias = []
    total_arquivos_doc = 0
    total_arquivos_encontrados = 0

    for diretorio, arquivos_doc in sorted(ESTRUTURA_DOCUMENTADA.items()):
        dir_path = os.path.join(core_path, diretorio)

        print(f"📁 {diretorio}/")

        if not os.path.exists(dir_path):
            print(f"  ❌ Diretório não existe")
            divergencias.append(f"Diretório ausente: {diretorio}")
            continue

        arquivos_reais = [f for f in os.listdir(dir_path) if f.endswith('.py') and f != '__init__.py']

        # Se não há arquivos específicos documentados, apenas verificar existência
        if not arquivos_doc:
            print(f"  ✅ Diretório existe ({len(arquivos_reais)} arquivos)")
            continue

        # Verificar arquivos documentados
        for arquivo in arquivos_doc:
            total_arquivos_doc += 1
            existe = arquivo in arquivos_reais
            status = "✅" if existe else "❌"
            print(f"  {status} {arquivo}")
            if existe:
                total_arquivos_encontrados += 1
            else:
                divergencias.append(f"Arquivo ausente: {diretorio}/{arquivo}")

        # Arquivos não documentados (informativo)
        nao_documentados = set(arquivos_reais) - set(arquivos_doc)
        if nao_documentados and len(nao_documentados) <= 5:
            for arquivo in sorted(nao_documentados):
                print(f"  📝 {arquivo} (não documentado)")
        elif nao_documentados:
            print(f"  📝 +{len(nao_documentados)} arquivos não documentados")

    print("\n=== Resultado ===")
    if not divergencias:
        print(f"✅ VALIDADO: Estrutura conforme documentação ({total_arquivos_encontrados}/{total_arquivos_doc} arquivos)")
    else:
        print(f"⚠️  DIVERGÊNCIAS ENCONTRADAS: {len(divergencias)}")
        for div in divergencias[:10]:  # Limitar a 10
            print(f"  - {div}")
        if len(divergencias) > 10:
            print(f"  ... e mais {len(divergencias) - 10} divergências")

if __name__ == '__main__':
    validar_wallclub_core()
