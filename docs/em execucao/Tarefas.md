## Tarefas Pendentes

- Email Aclub nao esta indo com layout correto (portal lojista)
- nao envia mensagem de baixar app no checkout
- Alteracao em loja (alterar, mudar vendedor, todas as lojas)
- checkout esta ok e tokenizando cartao; precisa validar recorrencia (debitar 1 pra validar cartao)

Contabilizar
- cupom
- cashback loja
- cashback wall


Cupom
- ver se engine esta obedecendo a todas as regras
- contabilizar
- POS nao esta mostrando no SLIP



select  valor_original       'valor original da transacao: R$10,00',
		amount               'valor cobrado do cliente R$ 5,03',
		originalAmount		 'valor cobrado do cliente R$ 5,03',
		valor_desconto		 'valor do desconto/acrescimo WALL',
		autorizacao_id		 'id de autorizacao do cliente para uso de cashback',
		valor_cashback		 'valor usado de cashback',
		cupom_id             'id do cupom usado',
		cupom_valor_desconto 'valor do cupom usado - desconto',
		desconto_wall_parametro_id 'id da regra wall de desconto/acrescimo',
		cashback_concedido         'valor do cashback concedido',
		cashback_wall_parametro_id 'id do parametro wall q concedeu cashback',
		cashback_loja_regra_id 'id da regra do lojista q concedeu cashback'
from    transactiondata_pos
where   terminal in ('PB59237K70569','5202172510000286' )
		and nsu_gateway = '2119516'


