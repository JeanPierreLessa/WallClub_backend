TRUNCATE TABLE wallclub.pinbankExtratoPOS;
TRUNCATE TABLE wallclub.pinbankExtratoPOS_audit;
TRUNCATE TABLE wallclub.baseTransacoesGestao;
TRUNCATE TABLE wallclub.baseTransacoesGestaoErroCarga;
TRUNCATE TABLE wallclub.baseTransacoesGestao_audit;

-- ------------------------------------------------------------
-- Migração wclub -> wallclub com remapeamento de IDs
-- Mantém vínculo pinbankExtratoPOS.id <-> baseTransacoesGestao.idFilaExtrato
-- ------------------------------------------------------------
START TRANSACTION;

-- 1) Staging dos dados de extrato com o old_id
DROP TEMPORARY TABLE IF EXISTS tmp_extrato;
CREATE TEMPORARY TABLE tmp_extrato AS
SELECT
  e.*,
  e.id AS old_id
FROM wclub.pinbankExtratoPOS e;

-- 2) Inserir no wallclub.pinbankExtratoPOS gerando novos IDs sequenciais
INSERT INTO wallclub.pinbankExtratoPOS (
  created_at,
  updated_at,
  Lido,
  codigo_cliente,
  IdTerminal,
  SerialNumber,
  Terminal,
  Bandeira,
  TipoCompra,
  DadosExtra,
  CpfCnpjComprador,
  NomeRazaoSocialComprador,
  NumeroParcela,
  NumeroTotalParcelas,
  DataTransacao,
  DataFuturaPagamento,
  CodAutorizAdquirente,
  NsuOperacao,
  NsuOperacaoLoja,
  ValorBruto,
  ValorBrutoParcela,
  ValorLiquidoRepasse,
  ValorSplit,
  IdStatus,
  DescricaoStatus,
  IdStatusPagamento,
  DescricaoStatusPagamento,
  ValorTaxaAdm,
  ValorTaxaMes,
  NumeroCartao,
  DataCancelamento,
  Submerchant
)
SELECT
  x.dataInsercao            AS created_at,
  NULL                      AS updated_at,
  x.Lido,
  x.codigo_cliente,
  x.IdTerminal,
  x.SerialNumber,
  x.Terminal,
  x.Bandeira,
  x.TipoCompra,
  x.DadosExtra,
  x.CpfCnpjComprador,
  x.NomeRazaoSocialComprador,
  x.NumeroParcela,
  x.NumeroTotalParcelas,
  x.DataTransacao,
  x.DataFuturaPagamento,
  x.CodAutorizAdquirente,
  x.NsuOperacao,
  x.NsuOperacaoLoja,
  x.ValorBruto,
  x.ValorBrutoParcela,
  x.ValorLiquidoRepasse,
  x.ValorSplit,
  x.IdStatus,
  x.DescricaoStatus,
  x.IdStatusPagamento,
  x.DescricaoStatusPagamento,
  x.ValorTaxaAdm,
  x.ValorTaxaMes,
  x.NumeroCartao,
  x.DataCancelamento,
  x.Submerchant
FROM tmp_extrato x;

-- 3) Construir o mapa old_id -> new_id usando (NsuOperacao, NumeroParcela)
DROP TEMPORARY TABLE IF EXISTS tmp_map_extrato;
CREATE TEMPORARY TABLE tmp_map_extrato AS
SELECT
  t.old_id,
  w.id AS new_id
FROM tmp_extrato t
JOIN wallclub.pinbankExtratoPOS w
  ON w.NsuOperacao   = t.NsuOperacao
 AND w.NumeroParcela = t.NumeroParcela;

-- 4) Staging de baseTransacoesGestao com old_idFila
DROP TEMPORARY TABLE IF EXISTS tmp_base;
CREATE TEMPORARY TABLE tmp_base AS
SELECT
  b.*,
  b.idFilaExtrato AS old_idFila
FROM wclub.baseTransacoesGestao b;

-- 5) Inserir no destino remapeando idFilaExtrato e montando data_transacao de var0+var1
INSERT INTO wallclub.baseTransacoesGestao (
  idFilaExtrato,
  banco,
  data_transacao,
  var0, var1, var2, var3, var4, var5, var6, var7, var8, var9, var10,
  var11, var12, var13, var14, var15, var16, var17, var18, var19, var20,
  var21, var22, var23, var24, var25, var26, var27, var28, var29, var30,
  var31, var32, var33, var34, var35, var36, var37, var38, var39, var40,
  var41, var42, var43, var44, var45, var46, var47, var48, var49, var50,
  var51, var52, var53, var54, var55, var56, var57, var58, var59, var60,
  var60_A, var61, var61_A, var62, var63, var64, var65, var66, var67, var68,
  var69, var70, var71, var72, var73, var74, var75, var76, var77, var78,
  var79, var80, var81, var82, var83, var84, var85, var86, var87, var88,
  var89, var90, var91, var92, var93, var93_A, var94, var94_A, var94_B, var95,
  var96, var97, var98, var99, var100, var101, var102, var103, var103_A, var104,
  var105, var106, var107, var107_A, var108, var109, var109_A, var110, var111, var111_A,
  var111_B, var112, var112_A, var112_B, var113, var113_A, var114, var114_A, var115, var115_A,
  var116, var116_A, var117, var117_A, var118, var118_A, var119, var120, var121, var122,
  var123, var124, var125, var126, var127, var128, var129, var130
)
SELECT
  m.new_id AS idFilaExtrato,
  b.banco,
  COALESCE(
    STR_TO_DATE(CONCAT(b.var0, ' ', b.var1), '%d/%m/%Y %H:%i:%s'),
    STR_TO_DATE(CONCAT(b.var0, ' ', b.var1), '%d/%m/%Y %H:%i')
  ) AS data_transacao,
  b.var0, b.var1, b.var2, b.var3, b.var4, b.var5, b.var6, b.var7, b.var8, b.var9, b.var10,
  b.var11, b.var12, b.var13, b.var14, b.var15, b.var16, b.var17, b.var18, b.var19, b.var20,
  b.var21, b.var22, b.var23, b.var24, b.var25, b.var26, b.var27, b.var28, b.var29, b.var30,
  b.var31, b.var32, b.var33, b.var34, b.var35, b.var36, b.var37, b.var38, b.var39, b.var40,
  b.var41, b.var42, b.var43, b.var44, b.var45, b.var46, b.var47, b.var48, b.var49, b.var50,
  b.var51, b.var52, b.var53, b.var54, b.var55, b.var56, b.var57, b.var58, b.var59, b.var60,
  b.var60_A, b.var61, b.var61_A, b.var62, b.var63, b.var64, b.var65, b.var66, b.var67, b.var68,
  b.var69, b.var70, b.var71, b.var72, b.var73, b.var74, b.var75, b.var76, b.var77, b.var78,
  b.var79, b.var80, b.var81, b.var82, b.var83, b.var84, b.var85, b.var86, b.var87, b.var88,
  b.var89, b.var90, b.var91, b.var92, b.var93, b.var93_A, b.var94, b.var94_A, b.var94_B, b.var95,
  b.var96, b.var97, b.var98, b.var99, b.var100, b.var101, b.var102, b.var103, b.var103_A, b.var104,
  b.var105, b.var106, b.var107, b.var107_A, b.var108, b.var109, b.var109_A, b.var110, b.var111, b.var111_A,
  b.var111_B, b.var112, b.var112_A, b.var112_B, b.var113, b.var113_A, b.var114, b.var114_A, b.var115, b.var115_A,
  b.var116, b.var116_A, b.var117, b.var117_A, b.var118, b.var118_A, b.var119, b.var120, b.var121, b.var122,
  b.var123, b.var124, b.var125, b.var126, b.var127, b.var128, b.var129, b.var130
FROM tmp_base b
JOIN tmp_map_extrato m
  ON m.old_id = b.old_idFila
WHERE m.new_id IS NOT NULL;

COMMIT;


DROP TEMPORARY TABLE IF EXISTS tmp_extrato;
DROP TEMPORARY TABLE IF EXISTS tmp_map_extrato;
DROP TEMPORARY TABLE IF EXISTS tmp_base;

-- Checagens rápidas
SELECT * FROM wallclub.baseTransacoesGestao WHERE var130 = 'TEF' LIMIT 100;
SELECT * FROM wallclub.pinbankExtratoPOS WHERE NsuOperacao = 142631637;