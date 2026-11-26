"""Desafio: R$ 1.000 em cartas e selados contra dólar parado e CDI (pandas puro, testável)."""
from __future__ import annotations

import math

import pandas as pd

from . import config

CARTEIRAS = ["selado", "cesta_raras", "propria", "dolar", "cdi"]


def _unidades(preco_brl: float, orcamento: float) -> int:
    """Unidades inteiras: ninguém compra 0,37 booster box."""
    return int(math.floor(orcamento / preco_brl + 1e-9)) if preco_brl and preco_brl > 0 else 0


def _info(d0df: pd.DataFrame, venda: float, linha, orcamento: float) -> dict:
    return dict(product_id=int(linha.product_id), acabamento=linha.acabamento,
                unidades=_unidades(linha.market_price * venda, orcamento),
                preco_brl=float(linha.market_price * venda), nome=linha.nome)


# ------------------------------------------------------------------ montagem (só dados do 1º dia)
def montar_selado(d0df, venda, capital):
    s = d0df[(d0df.tipo_produto == "selado") & d0df.market_price.notna()]
    cand = s[s.categoria_selado == "booster box"]
    regra = "booster box"
    if cand.empty:  # ADR 0003: fallback = selado de maior preço com preço
        cand, regra = s, "selado de maior preço (sem booster box com preço)"
    if cand.empty:
        raise ValueError("nenhum selado com preço no 1º dia")
    linha = cand.sort_values(["market_price", "product_id"], ascending=[False, True]).iloc[0]
    h = _info(d0df, venda, linha, capital)
    return [h], capital - h["unidades"] * h["preco_brl"], {"regra": regra, "itens": [h]}


def montar_cesta(d0df, venda, capital, aloc=100.0, n=10):
    c = d0df[(d0df.tipo_produto == "carta") & (d0df.raridade != config.RARIDADE_FORA) & d0df.market_price.notna()]
    c = (c.sort_values(["market_price", "product_id"], ascending=[False, True])
         .drop_duplicates("product_id").head(n))
    hs = [_info(d0df, venda, l, aloc) for l in c.itertuples()]
    caixa = capital - sum(h["unidades"] * h["preco_brl"] for h in hs)
    return hs, caixa, {"regra": f"R$ {aloc:.0f} em cada uma das {n} cartas de maior preço", "itens": hs,
                       "cartas_nao_compradas": [h["nome"] for h in hs if h["unidades"] == 0]}


def montar_propria(d0df, venda, capital):
    """RASCUNHO do ADR 0005 — substitua pela sua regra e commite o ADR antes do 1º cálculo.

    50% em Elite Trainer Box (a mais barata) + 50% repartidos entre as 5 cartas de raridade alta
    com preço mais próximo de US$ 10 no 1º dia.
    """
    metade, hs = capital / 2, []
    etb = d0df[(d0df.categoria_selado == "elite trainer box") & d0df.market_price.notna()]
    if etb.empty:
        etb = d0df[(d0df.tipo_produto == "selado") & d0df.market_price.notna()]
    if not etb.empty:
        hs.append(_info(d0df, venda, etb.sort_values(["market_price", "product_id"]).iloc[0], metade))
    c = d0df[d0df.raridade.isin(config.RARIDADES_ALTAS) & d0df.market_price.notna()].copy()
    c["dist"] = (c.market_price - 10).abs()
    c = c.sort_values(["dist", "product_id"]).drop_duplicates("product_id").head(5)
    hs += [_info(d0df, venda, l, metade / 5) for l in c.itertuples()]
    caixa = capital - sum(h["unidades"] * h["preco_brl"] for h in hs)
    return hs, caixa, {"regra": "50% ETB + 50% em 5 cartas altas próximas de US$ 10", "itens": hs}


# ------------------------------------------------------------------ avaliação diária
def avaliar(fato, cambio, holdings, caixa0, taxa_venda):
    """Valor de liquidação por dia + flag de preço carregado. Caixa rende CDI só em dia útil."""
    cal = cambio.sort_values("data").set_index("data")
    cal = cal[cal.index >= fato.data.min()]
    if not holdings:
        cartas, carregado = pd.Series(0.0, index=cal.index), pd.Series(False, index=cal.index)
    else:
        w = fato.set_index(["data", "product_id", "acabamento"]).market_price.unstack(["product_id", "acabamento"])
        cols = [(h["product_id"], h["acabamento"]) for h in holdings]
        w = w.reindex(cal.index)[cols]
        carregado = (w.isna() & w.ffill().notna()).any(axis=1)  # dia em que algum item usou preço antigo
        unidades = pd.Series([h["unidades"] for h in holdings], index=pd.MultiIndex.from_tuples(cols))
        cartas = (w.ffill() * unidades).sum(axis=1) * (1 - taxa_venda) * cal.cotacao_compra
    fator = 1 + cal.cdi_taxa_dia.fillna(0.0) / 100
    fator.iloc[0] = 1.0  # o rendimento começa no dia seguinte à compra
    caixa = caixa0 * fator.cumprod()
    return cartas + caixa, carregado


def _quadro(idx, valor, nome, taxa, group_id, capital, carregado=None):
    return pd.DataFrame({
        "data": idx, "group_id": group_id, "carteira": nome, "valor_brl": valor.values,
        "retorno_acumulado": valor.values / capital - 1, "taxa_venda": taxa,
        "preco_carregado": carregado.values if carregado is not None else False})


def calcular(fato: pd.DataFrame, cambio: pd.DataFrame, group_id: int,
             taxa_venda: float = config.TAXA_VENDA, capital: float = config.CAPITAL):
    """Devolve (tabela no contrato gold_turma, composição das carteiras).

    `fato`: um grupo, colunas data, product_id, acabamento, market_price, tipo_produto,
    categoria_selado, raridade, nome. `cambio`: fato_cambio_diario.
    """
    fato, cambio = fato.copy(), cambio.copy()
    fato["data"], cambio["data"] = pd.to_datetime(fato["data"]), pd.to_datetime(cambio["data"])
    d0 = fato.data.min()
    linha0 = cambio[cambio.data == d0]
    if linha0.empty or pd.isna(linha0.iloc[0].cotacao_venda):
        raise ValueError("sem PTAX conhecida no 1º dia de coleta")
    venda0 = float(linha0.iloc[0].cotacao_venda)
    d0df = fato[fato.data == d0]  # a composição usa SÓ o 1º dia: sem informação do futuro

    montagens = {"selado": montar_selado(d0df, venda0, capital),
                 "cesta_raras": montar_cesta(d0df, venda0, capital),
                 "propria": montar_propria(d0df, venda0, capital)}
    cal = cambio[cambio.data >= d0].sort_values("data")
    idx = cal.data
    quadros = []
    for taxa in sorted({taxa_venda, 0.0}, reverse=True):
        for nome, (hs, caixa0, _) in montagens.items():
            v, carr = avaliar(fato, cambio, hs, caixa0, taxa)
            quadros.append(_quadro(v.index, v, nome, taxa, group_id, capital, carr))
        usd0 = capital / venda0
        dolar = pd.Series(usd0 * cal.cotacao_compra.values, index=idx.values)
        quadros.append(_quadro(idx.values, dolar, "dolar", taxa, group_id, capital))
        fator = 1 + cal.cdi_taxa_dia.fillna(0.0).values / 100
        fator[0] = 1.0
        cdi = pd.Series(capital * fator.cumprod(), index=idx.values)
        quadros.append(_quadro(idx.values, cdi, "cdi", taxa, group_id, capital))
    out = pd.concat(quadros, ignore_index=True)
    return out, {k: v[2] | {"caixa_inicial": v[1]} for k, v in montagens.items()}


def metricas(cart: pd.DataFrame, taxa: float = config.TAXA_VENDA) -> pd.DataFrame:
    c = cart[cart.taxa_venda == taxa].sort_values("data")
    linhas = []
    for nome, g in c.groupby("carteira"):
        linhas.append(dict(carteira=nome, retorno_acumulado=g.valor_brl.iloc[-1] / config.CAPITAL - 1,
                           perda_maxima=float((g.valor_brl / g.valor_brl.cummax() - 1).min()),
                           dias_preco_carregado=int(g.preco_carregado.sum()) if "preco_carregado" in g else 0))
    m = pd.DataFrame(linhas).set_index("carteira")
    m["excesso_sobre_cdi"] = m.retorno_acumulado - m.loc["cdi", "retorno_acumulado"]
    return m.reindex(CARTEIRAS).reset_index()


CONTRATO = ["data", "group_id", "carteira", "valor_brl", "retorno_acumulado", "taxa_venda"]
