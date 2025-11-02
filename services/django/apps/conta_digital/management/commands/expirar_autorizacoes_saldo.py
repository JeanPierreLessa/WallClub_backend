"""
Django management command para expirar autorizações de uso de saldo.
Executa via cron a cada 1 minuto.

Uso:
    python manage.py expirar_autorizacoes_saldo
    
Crontab:
    * * * * * cd /app && python manage.py expirar_autorizacoes_saldo >> /app/logs/cron_autorizacoes.log 2>&1
"""
from django.core.management.base import BaseCommand
from apps.conta_digital.services_autorizacao import AutorizacaoService
from wallclub_core.utilitarios.log_control import registrar_log


class Command(BaseCommand):
    help = 'Expira autorizações de uso de saldo pendentes/aprovadas e libera bloqueios'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Exibe informações detalhadas',
        )
    
    def handle(self, *args, **options):
        verbose = options.get('verbose', False)
        
        if verbose:
            self.stdout.write('Iniciando expiração de autorizações...')
        
        try:
            # Chama serviço
            resultado = AutorizacaoService.expirar_autorizacoes_pendentes()
            
            if resultado['sucesso']:
                from decimal import Decimal
                
                total = resultado['total_expiradas']
                liberado = resultado['saldo_liberado']
                
                # Garantir que liberado é Decimal para formatação correta
                if isinstance(liberado, str):
                    liberado = Decimal(liberado)
                
                if total > 0:
                    mensagem = (
                        f'✅ Expiradas: {total} autorizações, '
                        f'Saldo liberado: R$ {float(liberado):.2f}'
                    )
                    self.stdout.write(self.style.SUCCESS(mensagem))
                    registrar_log('apps.conta_digital', mensagem)
                else:
                    if verbose:
                        self.stdout.write('Nenhuma autorização expirada encontrada')
            else:
                mensagem = f'❌ Erro: {resultado.get("mensagem")}'
                self.stdout.write(self.style.ERROR(mensagem))
                registrar_log('apps.conta_digital', mensagem, nivel='ERROR')
                
        except Exception as e:
            mensagem = f'❌ Exceção ao expirar autorizações: {str(e)}'
            self.stdout.write(self.style.ERROR(mensagem))
            registrar_log('apps.conta_digital', mensagem, nivel='ERROR')
