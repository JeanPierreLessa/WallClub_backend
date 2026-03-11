"""
Comando management para sincronizar tarifas do banco com a API Own
Chamado raramente para verificar/corrigir discrepâncias

Uso:
    # Sincronizar uma loja específica
    python manage.py sincronizar_tarifas_own --loja-id 15

    # Sincronizar TODAS as lojas com cadastro Own
    python manage.py sincronizar_tarifas_own --todas
"""

from django.core.management.base import BaseCommand, CommandError
from adquirente_own.models_cadastro import LojaOwn
from adquirente_own.services_cadastro import CadastroOwnService
from wallclub_core.utilitarios.log_control import registrar_log


class Command(BaseCommand):
    help = 'Sincroniza tarifas do banco com a API Own Financial'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loja-id',
            type=int,
            help='ID da loja a sincronizar'
        )
        parser.add_argument(
            '--todas',
            action='store_true',
            help='Sincronizar TODAS as lojas com cadastro Own'
        )

    def handle(self, *args, **options):
        loja_id = options.get('loja_id')
        todas = options.get('todas', False)

        if not loja_id and not todas:
            raise CommandError('Especifique --loja-id <id> ou use --todas')

        service = CadastroOwnService()
        lojas_processadas = 0
        lojas_com_discrepancias = 0

        # Determinar quais lojas processar
        if loja_id:
            lojas = LojaOwn.objects.filter(loja_id=loja_id)
            if not lojas.exists():
                raise CommandError(f'Loja {loja_id} não encontrada no cadastro Own')
        else:
            lojas = LojaOwn.objects.all()

        total_lojas = lojas.count()
        self.stdout.write(f'\n🔄 Iniciando sincronização de {total_lojas} loja(s)...\n')

        for loja_own in lojas:
            try:
                resultado = service.sincronizar_tarifas_com_api(loja_id=loja_own.loja_id)

                lojas_processadas += 1

                if resultado['sucesso']:
                    discrepancias = resultado.get('discrepancias_encontradas', 0)

                    if discrepancias > 0:
                        lojas_com_discrepancias += 1
                        self.stdout.write(
                            self.style.WARNING(
                                f"⚠️  Loja {loja_own.loja_id}: {discrepancias} discrepâncias sincronizadas"
                            )
                        )
                        # Listar discrepâncias
                        for disc in resultado.get('discrepancias', []):
                            if 'situacao' in disc:
                                self.stdout.write(
                                    f"    - Tarifa {disc['cesta_valor_id']}: {disc['situacao']}"
                                )
                            else:
                                self.stdout.write(
                                    f"    - Tarifa {disc['cesta_valor_id']}: "
                                    f"R$ {disc['valor_banco']:.3f} (banco) → R$ {disc['valor_api']:.3f} (API)"
                                )
                    else:
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Loja {loja_own.loja_id}: Sincronizada (sem discrepâncias)")
                        )
                else:
                    self.stdout.write(
                        self.style.ERROR(f"❌ Loja {loja_own.loja_id}: {resultado['mensagem']}")
                    )

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Loja {loja_own.loja_id}: Erro - {str(e)}")
                )
                registrar_log('adquirente_own',
                    f'Erro ao sincronizar tarifas da loja {loja_own.loja_id}: {str(e)}',
                    nivel='ERROR')

        # Resumo final
        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS(
            f'✅ Sincronização concluída!\n'
            f'   Lojas processadas: {lojas_processadas}\n'
            f'   Lojas com discrepâncias: {lojas_com_discrepancias}'
        ))
        self.stdout.write('='*60 + '\n')
