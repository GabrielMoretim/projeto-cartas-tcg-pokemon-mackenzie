from datetime import date

from tcg.models import SCHEMAS, validar


def _preco(**kw):
    base = dict(data=date(2026, 10, 9), product_id=1, group_id=1, acabamento="Normal", chave_raw="k")
    return base | kw


def test_preco_nulo_continua_nulo():
    ok, ruins = validar("preco_diario", [_preco(market_price=None)])
    assert ok[0].market_price is None and not ruins


def test_preco_negativo_vai_para_quarentena_com_motivo():
    ok, ruins = validar("preco_diario", [_preco(market_price=-1.0), _preco(market_price=2.0)])
    assert len(ok) == 1 and len(ruins) == 1 and "negativo" in ruins[0]["motivo"]


def test_acabamento_ausente_e_rejeitado():
    ok, ruins = validar("preco_diario", [_preco(acabamento=None)])
    assert not ok and ruins


def test_cambio_so_aceita_boletim_de_fechamento():
    from datetime import datetime
    linha = dict(data=date(2026, 10, 9), cotacao_compra=5.0, cotacao_venda=5.01,
                 data_hora_cotacao=datetime(2026, 10, 9, 13, 9), boletim="Abertura", chave_raw="k")
    ok, ruins = validar("cambio_diario", [linha])
    assert not ok and ruins


def test_schema_segue_o_contrato_da_turma():
    nomes = [f.name for f in SCHEMAS["preco_diario"]]
    assert nomes == ["data", "product_id", "group_id", "acabamento", "market_price", "low_price",
                     "mid_price", "high_price", "moeda", "fonte", "chave_raw"]
    assert str(SCHEMAS["preco_diario"].field("market_price").type) == "double"
    assert str(SCHEMAS["cdi_diario"].field("data").type) == "date32[day]"
