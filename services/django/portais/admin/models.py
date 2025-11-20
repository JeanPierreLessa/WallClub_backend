from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# MODELOS REMOVIDOS - DUPLICAÇÕES ELIMINADAS
#
# BaseTransacoesGestao: Movido para gestao_financeira.models
# - Use: from gestao_financeira.models import BaseTransacoesGestao
#
# Terminal: Movido para posp2.models  
# - Use: from posp2.models import Terminal
#
# Pagamento: Removido - usar gestao_financeira.models.PagamentoEfetuado
# - Use: from gestao_financeira.models import PagamentoEfetuado
