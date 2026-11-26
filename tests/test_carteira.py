import pandas as pd

from helpers import DIAS, cambio_df, fato_df
from tcg import carteira


def _calc(**kw):
    return carteira.calcular(fato_df(**kw), cambio_df(), group_id=1, taxa_venda=0.15)


def test_unidades_inteiras_e_caixa_nao_negativo():
    _, comp = _calc()
    for nome, c in comp.items():
        assert c["caixa_inicial"] >= -1e-9, nome
        assert all(isinstance(i["unidades"], int) for i in c["itens"]), nome
    sel = comp["selado"]["itens"][0]
    assert sel["unidades"] == 1  # R$ 551,10 por caixa: 1 unidade, a sobra fica em caixa
    assert abs(comp["selado"]["caixa_inicial"] - (1000 - 110 * 5.01)) < 1e-6


def test_cesta_escolhe_top10_sem_code_card():
    _, comp = _calc()
    nomes = [i["nome"] for i in comp["cesta_raras"]["itens"]]
    assert len(nomes) == 10 and "Code Card" not in nomes
    assert nomes[0] == "Carta 1"  # a de maior preço


def test_sem_informacao_do_futuro():
    f, c = fato_df(), cambio_df()
    _, comp_full = carteira.calcular(f, c, 1)
    so_d0 = f[f.data == DIAS[0]]
    _, comp_d0 = carteira.calcular(so_d0, c[c.data == DIAS[0]], 1)
    for k in ("selado", "cesta_raras", "propria"):
        assert comp_full[k]["itens"] == comp_d0[k]["itens"], k


def test_cdi_nao_rende_fim_de_semana_nem_feriado():
    out, _ = _calc()
    cdi = out[(out.carteira == "cdi") & (out.taxa_venda == 0.15)].set_index("data").valor_brl
    sex, sab, dom, seg_feriado, ter = (cdi[pd.Timestamp(d)] for d in DIAS[:5])
    assert sex == 1000.0 and sab == sex and dom == sex and seg_feriado == sex
    assert abs(ter - 1000 * 1.0005) < 1e-9  # só o CDI de terça (13/10) entra


def test_dolar_usa_venda_na_compra_e_compra_na_venda():
    out, _ = _calc()
    d = out[(out.carteira == "dolar") & (out.taxa_venda == 0.15)].set_index("data").valor_brl
    assert abs(d[pd.Timestamp(DIAS[0])] - 1000 * 5.00 / 5.01) < 1e-9  # spread já no 1º dia
    # fim de semana e feriado usam a PTAX de 09/10
    assert d[pd.Timestamp(DIAS[1])] == d[pd.Timestamp(DIAS[0])] == d[pd.Timestamp(DIAS[3])]


def test_preco_ausente_usa_ultimo_observado_e_marca_o_dia():
    ausente = {(1000, DIAS[2])}
    out, _ = carteira.calcular(fato_df(remover=ausente), cambio_df(), 1)
    s = out[(out.carteira == "selado") & (out.taxa_venda == 0.0)].set_index("data")
    assert bool(s.loc[pd.Timestamp(DIAS[2]), "preco_carregado"]) is True
    assert bool(s.loc[pd.Timestamp(DIAS[1]), "preco_carregado"]) is False
    m = carteira.metricas(out, taxa=0.0).set_index("carteira")
    assert m.loc["selado", "dias_preco_carregado"] == 1


def test_taxa_de_venda_reduz_o_valor():
    out, _ = _calc()
    u = out[(out.carteira == "selado") & (out.data == pd.Timestamp(DIAS[-1]))].set_index("taxa_venda").valor_brl
    assert u[0.0] > u[0.15]


def test_contrato_de_saida():
    out, _ = _calc()
    assert set(carteira.CONTRATO) <= set(out.columns)
    assert set(out.carteira) == set(carteira.CARTEIRAS)
