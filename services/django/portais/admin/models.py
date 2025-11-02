from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

# MODELOS REMOVIDOS - DUPLICAÇÕES ELIMINADAS
#
# BaseTransacoesGestao: Movido para pinbank.cargas_pinbank.models
# - Use: from pinbank.models import BaseTransacoesGestao
#
# Terminal: Movido para posp2.models  
# - Use: from posp2.models import Terminal
#
# Pagamento: Removido - usar sistema_bancario.models.PagamentoEfetuado
# - Use: from sistema_bancario.models import PagamentoEfetuado
