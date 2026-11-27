import pandas as pd

from helpers import fato_df
from tcg import analytics


def test_decomposicao_carta_cambio_cruzado():
    """Exemplo da página: carta +10%, dólar +5% => +15,5% em reais (10% + 5% + 0,5%)."""
    df = pd.DataFrame([
        dict(data=pd.Timestamp("2026-10-01"), group_id=1, sigla="T", product_id=1, acabamento="Normal",
             market_price=100.0, cotacao_venda=5.00, tipo_produto="carta", raridade="Ultra Rare",
             nome="X", image_url="", url=""),
        dict(data=pd.Timestamp("2026-10-02"), group_id=1, sigla="T", product_id=1, acabamento="Normal",
             market_price=110.0, cotacao_venda=5.25, tipo_produto="carta", raridade="Ultra Rare",
             nome="X", image_url="", url=""),
    ])
    top, _ = analytics.pergunta1(df, 1)
    r = top.iloc[0]
    assert abs(r.efeito_carta - 0.10) < 1e-12 and abs(r.efeito_cambio - 0.05) < 1e-12
    assert abs(r.efeito_cruzado - 0.005) < 1e-12
    assert abs(r.variacao_brl - 0.155) < 1e-12
    assert abs(r.preco_ini_brl - 500) < 1e-9 and abs(r.preco_fim_brl - 577.5) < 1e-9


def test_pergunta1_filtro_de_preco_minimo_em_dolar():
    df = fato_df()
    df["cotacao_venda"] = 5.0
    top, bottom = analytics.pergunta1(df, 1, min_usd=1.0)
    assert 900 not in set(top.product_id) | set(bottom.product_id)  # Code Card fora
    assert (top.p0 > 1.0).all()


def test_nulo_nao_vira_zero():
    df = fato_df()
    df["cotacao_venda"] = 5.0
    df.loc[(df.product_id == 1) & (df.data == df.data.max()), "market_price"] = None
    top, bottom = analytics.pergunta1(df, 1)
    assert 1 not in set(top.product_id) | set(bottom.product_id)


def _cart(group_id, selado_fim, taxa_dolar_cdi):
    """Duas datas: 1.000 no dia 1 e o valor final no dia 2, para cada carteira."""
    linhas = []
    for nome, fim, taxa in (("selado", selado_fim, 0.15), ("cdi", 1001.0, taxa_dolar_cdi), ("dolar", 990.0, taxa_dolar_cdi),
                            ("cesta_raras", 995.0, 0.15)):
        for d, v in ((pd.Timestamp("2026-11-26"), 1000.0), (pd.Timestamp("2026-11-27"), fim)):
            linhas.append(dict(data=d, group_id=group_id, carteira=nome, valor_brl=v,
                               retorno_acumulado=v / 1000 - 1, taxa_venda=taxa))
    return pd.DataFrame(linhas)


def test_placar_aceita_dolar_e_cdi_com_qualquer_taxa():
    """Colega que gravou dolar/cdi com taxa 0 não pode ser descartado do placar."""
    cart = pd.concat([_cart(1, 1010.0, 0.15), _cart(2, 1000.5, 0.0), _cart(3, 990.0, 0.0)])
    p = analytics.placar(cart, taxa=0.15)
    assert p["selado_comparaveis"] == 3 and p["selado_ganhou_do_cdi"] == 1  # só a coleção 1 (1010 > 1001)
    assert p["cesta_comparaveis"] == 3 and p["cesta_ganhou_do_dolar"] == 3  # 995 > 990 em todas


def test_placar_ignora_colecao_sem_a_carteira_comparada():
    cart = pd.concat([_cart(1, 1010.0, 0.15), _cart(2, 1010.0, 0.15)])
    cart = cart[~((cart.group_id == 2) & (cart.carteira == "cdi"))]
    p = analytics.placar(cart, taxa=0.15)
    assert p["selado_comparaveis"] == 1 and p["colecoes"] == 2
