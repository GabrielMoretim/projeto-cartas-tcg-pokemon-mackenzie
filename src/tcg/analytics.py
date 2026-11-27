"""As cinco perguntas de investimento (pandas sobre a fato do gold) e o placar da turma."""
from __future__ import annotations

import pandas as pd

from . import config

ORDEM_ACABAMENTO = ["Normal", "Holofoil", "Reverse Holofoil"]


def _col(brl: bool) -> str:
    return "market_price_brl" if brl else "market_price"


def so_cartas(df: pd.DataFrame) -> pd.DataFrame:
    return df[(df.tipo_produto == "carta") & (df.raridade != config.RARIDADE_FORA)]


def um_acabamento_por_produto(df: pd.DataFrame) -> pd.DataFrame:
    """Um exemplar de cada produto: acabamento fixo por produto (Normal > Holofoil > Reverse > resto)."""
    ordem = {a: i for i, a in enumerate(ORDEM_ACABAMENTO)}
    prefer = (df[["group_id", "product_id", "acabamento"]].drop_duplicates()
              .assign(r=lambda x: x.acabamento.map(ordem).fillna(99), a=lambda x: x.acabamento)
              .sort_values(["group_id", "product_id", "r", "a"])
              .drop_duplicates(["group_id", "product_id"])[["group_id", "product_id", "acabamento"]])
    return df.merge(prefer, on=["group_id", "product_id", "acabamento"])


def _largo(d: pd.DataFrame, valor: str) -> pd.DataFrame:
    """Matriz data x produto, com o último preço observado carregado (nulo vira o preço anterior)."""
    w = d.pivot_table(index="data", columns="product_id", values=valor, aggfunc="last")
    w = w.reindex(pd.date_range(w.index.min(), w.index.max(), freq="D"))
    return w.ffill()


# ---------------------------------------------------------------- pergunta 1
def pergunta1(df, group_id, brl=True, min_usd=1.0, n=10):
    """Variação em reais entre o 1º e o último dia, decomposta em carta, câmbio e cruzado."""
    d = so_cartas(df[df.group_id == group_id])
    d0, d1 = d.data.min(), d.data.max()
    cols = ["product_id", "acabamento", "market_price", "cotacao_venda"]
    a = d[d.data == d0][cols].rename(columns={"market_price": "p0", "cotacao_venda": "c0"})
    b = d[d.data == d1][cols].rename(columns={"market_price": "p1", "cotacao_venda": "c1"})
    m = a.merge(b, on=["product_id", "acabamento"]).dropna(subset=["p0", "p1", "c0", "c1"])
    m = m[m.p0 > min_usd]  # filtro em dólar: a lista não muda quando o câmbio muda
    m["efeito_carta"] = m.p1 / m.p0 - 1
    m["efeito_cambio"] = m.c1 / m.c0 - 1
    m["efeito_cruzado"] = m.efeito_carta * m.efeito_cambio
    m["variacao_brl"] = (1 + m.efeito_carta) * (1 + m.efeito_cambio) - 1
    m["preco_ini_brl"], m["preco_fim_brl"] = m.p0 * m.c0, m.p1 * m.c1
    info = d[["product_id", "nome", "raridade", "image_url", "url"]].drop_duplicates("product_id")
    m = m.merge(info, on="product_id")
    chave = "variacao_brl" if brl else "efeito_carta"
    return m.nlargest(n, chave), m.nsmallest(n, chave)


# ---------------------------------------------------------------- pergunta 2
def pergunta2(df, group_id, brl=True):
    """Índice base 100: média dos selados x soma das cartas de raridade alta."""
    col = _col(brl)
    d = um_acabamento_por_produto(df[df.group_id == group_id])
    d0 = d.data.min()
    saida = {}
    grupos = {
                "Selados (média)": (d[(d.tipo_produto == "selado") & (d.categoria_selado != "booster box case")
                              & ~d.nome.str.contains("Display", case=False, na=False)], "mean"),
        "Cartas Double Rare+ (soma)": (d[(d.tipo_produto == "carta") & d.raridade.isin(config.RARIDADES_ALTAS)], "sum"),
    }
    for nome, (g, agg) in grupos.items():
        if g.empty:
            continue
        w = _largo(g, col)
        w = w.loc[:, w.loc[d0].notna()] if d0 in w.index else w
        serie = getattr(w, agg)(axis=1)
        saida[nome] = serie / serie.iloc[0] * 100
    return pd.DataFrame(saida).rename_axis("data").reset_index()


# ---------------------------------------------------------------- pergunta 3
def _valor_colecao(df, brl):
    col = _col(brl)
    d = um_acabamento_por_produto(so_cartas(df))
    out = []
    for g, dg in d.groupby("group_id"):
        w = _largo(dg, col)
        w = w.loc[:, w.iloc[0].notna()]
        s = w.sum(axis=1).rename("valor").rename_axis("data").reset_index()
        s["group_id"], s["sigla"] = g, dg.sigla.iloc[0]
        out.append(s)
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame()


def pergunta3(df, brl=True):
    """Valor da coleção (1 exemplar de cada carta) em índice base 100 na janela comum, com a PTAX."""
    v = _valor_colecao(df, brl)
    base = v.groupby("group_id").data.min().max()  # 1º dia em que todas já tinham coleta
    v = v[v.data >= base].copy()
    v["indice"] = v.groupby("group_id").valor.transform(lambda s: s / s.iloc[0] * 100)
    ptax = (df.groupby("data").cotacao_venda.first().reset_index().query("data >= @base").sort_values("data"))
    ptax["indice"] = ptax.cotacao_venda / ptax.cotacao_venda.iloc[0] * 100
    return v[["data", "group_id", "sigla", "valor", "indice"]], ptax[["data", "indice"]]


# ---------------------------------------------------------------- pergunta 4
def pergunta4(df, brl=True, corte=0.8):
    """Concentração por raridade no último dia e nº de cartas que somam 80% do valor."""
    col = _col(brl)
    d = um_acabamento_por_produto(so_cartas(df))
    partes, n80 = [], []
    for g, dg in d.groupby("group_id"):
        w = _largo(dg, col).iloc[-1].dropna()
        info = dg.drop_duplicates("product_id").set_index("product_id")
        v = pd.DataFrame({"valor": w, "raridade": info.reindex(w.index).raridade.fillna("(sem raridade)")})
        share = v.groupby("raridade").valor.sum().pipe(lambda s: s / s.sum()).reset_index(name="participacao")
        share["sigla"] = dg.sigla.iloc[0]
        partes.append(share)
        acum = v.valor.sort_values(ascending=False).cumsum() / v.valor.sum()
        n80.append({"sigla": dg.sigla.iloc[0], "cartas_para_80pct": int((acum < corte).sum() + 1),
                    "total_cartas": len(v)})
    return pd.concat(partes, ignore_index=True), pd.DataFrame(n80)


# ---------------------------------------------------------------- pergunta 5
def pergunta5(df, brl=True, min_usd=5.0):
    """Retorno no período x volatilidade diária, para cartas acima de US$ 5 no 1º dia da janela comum."""
    col = _col(brl)
    d = um_acabamento_por_produto(so_cartas(df))
    base = d.groupby("group_id").data.min().max()
    linhas = []
    for g, dg in d.groupby("group_id"):
        usd = _largo(dg[dg.data >= base], "market_price")
        w = _largo(dg[dg.data >= base], col)
        if len(w) < 3:
            continue
        ok = usd.iloc[0] > min_usd
        w = w.loc[:, ok[ok].index.intersection(w.columns)].dropna(axis=1, how="all")
        ret = w.iloc[-1] / w.iloc[0] - 1
        vol = w.pct_change().std()
        res = pd.DataFrame({"retorno": ret, "volatilidade": vol}).dropna().reset_index()
        res["group_id"], res["sigla"] = g, dg.sigla.iloc[0]
        linhas.append(res)
    if not linhas:
        return pd.DataFrame()
    r = pd.concat(linhas, ignore_index=True)
    info = d[["group_id", "product_id", "nome", "raridade", "image_url", "url"]].drop_duplicates(["group_id", "product_id"])
    return r.merge(info, on=["group_id", "product_id"])


# ---------------------------------------------------------------- placar da turma
def placar(cart: pd.DataFrame, taxa: float = config.TAXA_VENDA) -> dict:
    """cart: contrato gold_turma/carteira (todas as coleções)."""
    c = cart[cart.taxa_venda.isin([taxa])].copy()
    ult = c[c.data == c.groupby("group_id").data.transform("max")]
    p = ult.pivot_table(index="group_id", columns="carteira", values="retorno_acumulado")
    c = c.sort_values("data")
    c["dd"] = c.groupby(["group_id", "carteira"]).valor_brl.transform(lambda s: s / s.cummax() - 1)
    dd = c.groupby(["group_id", "carteira"]).dd.min().unstack()
    return {
        "colecoes": int(len(p)),
        "selado_ganhou_do_cdi": int((p["selado"] > p["cdi"]).sum()) if {"selado", "cdi"} <= set(p) else None,
        "cesta_ganhou_do_dolar": int((p["cesta_raras"] > p["dolar"]).sum()) if {"cesta_raras", "dolar"} <= set(p) else None,
        "menor_perda_maxima": (dd.drop(columns=["dolar", "cdi"], errors="ignore").stack().idxmax() if len(dd) else None),  # (group_id, carteira)
        "retornos": p, "perda_maxima": dd,
    }
