"""Dados sintéticos para os testes (nada de rede)."""
from datetime import date, timedelta

import pandas as pd

DIAS = [date(2026, 10, 9) + timedelta(days=i) for i in range(6)]  # sex 09 ... qua 14 (12/10 = feriado)
PTAX = {date(2026, 10, 9): (5.00, 5.01), date(2026, 10, 13): (5.10, 5.11), date(2026, 10, 14): (5.20, 5.21)}
CDI = {date(2026, 10, 9): 0.05, date(2026, 10, 13): 0.05, date(2026, 10, 14): 0.05}  # sem taxa: sáb, dom, feriado


def cambio_df() -> pd.DataFrame:
    linhas, ult = [], None
    for d in DIAS:
        if d in PTAX:
            ult = (d, *PTAX[d])
        linhas.append(dict(data=d, cotacao_compra=ult[1], cotacao_venda=ult[2], data_ptax=ult[0],
                           cdi_taxa_dia=CDI.get(d, 0.0)))
    return pd.DataFrame(linhas)


def fato_df(group_id=1, remover=()) -> pd.DataFrame:
    """1 booster box (US$110), 12 cartas de US$ 50 a 5 (+1 Code Card cara) e 1 carta barata."""
    prods = [(1000, "selado", "booster box", "Booster Box", None, 110.0)]
    prods += [(i, "carta", None, f"Carta {i}", "Ultra Rare", 50.0 - 4 * i) for i in range(1, 13)]
    prods += [(900, "carta", None, "Code Card", "Code Card", 999.0)]
    linhas = []
    for k, d in enumerate(DIAS):
        for pid, tipo, cat, nome, rar, p0 in prods:
            if (pid, d) in remover:
                continue
            linhas.append(dict(data=d, group_id=group_id, sigla="TST", product_id=pid, acabamento="Normal",
                               market_price=round(p0 * (1 + 0.01 * k), 4), tipo_produto=tipo,
                               categoria_selado=cat, raridade=rar, nome=nome, numero=None,
                               image_url="http://img", url="http://url"))
    return pd.DataFrame(linhas)
