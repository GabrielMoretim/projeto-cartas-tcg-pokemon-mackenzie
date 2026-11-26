"""Integração: bruto -> silver -> gold, com a regra de câmbio da última cotação conhecida."""
from datetime import date

import duckdb
import pyarrow.parquet as pq

from helpers import DIAS
from raw_fixture import popular_raw
from tcg.gold import construir, fontes_silver
from tcg.silver import build_silver
from tcg.store import LocalStore

GID = 24269


def _gold(tmp_path, **kw):
    store = LocalStore(tmp_path)
    popular_raw(store, GID, **kw)
    cont = build_silver(store, GID)
    con = duckdb.connect()
    construir(con, fontes_silver(store))
    return store, cont, con


def test_ptax_fim_de_semana_e_feriado_usam_a_sexta(tmp_path):
    """Semana 09/10 a 13/10/2026: sáb 10, dom 11 e feriado 12 usam a PTAX de 09/10; terça 13 usa a própria."""
    _, _, con = _gold(tmp_path)
    q = dict(con.execute("SELECT data, data_ptax FROM fato_cambio_diario").fetchall())
    for d in DIAS[:4]:
        assert q[d] == date(2026, 10, 9), d
    assert q[date(2026, 10, 13)] == date(2026, 10, 13)
    # nunca uma cotação posterior ao dia do preço
    assert con.execute("SELECT count(*) FROM fato_preco_diario WHERE data_ptax > data").fetchone()[0] == 0


def test_market_price_brl_pode_ser_refeito_a_mao(tmp_path):
    _, _, con = _gold(tmp_path)
    p, brl, venda = con.execute("""SELECT market_price, market_price_brl, cotacao_venda FROM fato_preco_diario
                                   WHERE data = DATE '2026-10-11' AND product_id = 1""").fetchone()
    assert venda == 5.01 and abs(brl - p * 5.01) < 1e-9


def test_cdi_zero_em_dia_sem_taxa(tmp_path):
    _, _, con = _gold(tmp_path)
    q = dict(con.execute("SELECT data, cdi_taxa_dia FROM fato_cambio_diario").fetchall())
    assert q[date(2026, 10, 10)] == q[date(2026, 10, 12)] == 0.0 and q[date(2026, 10, 9)] > 0


def test_silver_nulo_nao_vira_zero_e_quarentena_conta(tmp_path):
    store, cont, con = _gold(tmp_path, preco_ruim=True)
    assert cont["preco_diario_quarentena"] == 1
    assert store.exists(f"quarentena/preco_diario/group_id={GID}/data=2026-10-11/erros.json")
    nulos = con.execute("SELECT count(*) FROM fato_preco_diario WHERE product_id = 2 AND market_price IS NULL").fetchone()[0]
    zeros = con.execute("SELECT count(*) FROM fato_preco_diario WHERE market_price = 0").fetchone()[0]
    assert nulos == len(DIAS) and zeros == 0


def test_tipos_da_silver_seguem_o_contrato(tmp_path):
    store, _, _ = _gold(tmp_path)
    t = pq.read_table(store.uri(f"silver/preco_diario/group_id={GID}/data=2026-10-09/preco.parquet"))
    assert str(t.schema.field("market_price").type) == "double" and str(t.schema.field("data").type).startswith("date32")


def test_reconstrucao_e_deterministica(tmp_path):
    store, _, con = _gold(tmp_path)
    antes = con.execute("SELECT * FROM fato_preco_diario ORDER BY ALL").fetchall()
    build_silver(store, GID)  # segundo `rebuild` sobre o mesmo bruto
    con2 = duckdb.connect()
    construir(con2, fontes_silver(store))
    assert con2.execute("SELECT * FROM fato_preco_diario ORDER BY ALL").fetchall() == antes


def test_classificacao_carta_e_selado(tmp_path):
    _, _, con = _gold(tmp_path)
    r = dict(con.execute("SELECT product_id, tipo_produto || ':' || coalesce(categoria_selado, '') FROM dim_produto").fetchall())
    assert r[1] == "carta:" and r[3] == "selado:booster box"
