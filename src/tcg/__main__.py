"""CLI:  python -m tcg {check-colecao|collect|silver|gold|carteira|rebuild|daily}"""
from __future__ import annotations

import argparse
import io
import json
import logging
import re
import sys

import pyarrow as pa
import pyarrow.parquet as pq

from . import carteira, config
from .collect import coletar
from .gold import abrir_gold, build_gold, carregar_cambio, carregar_fato
from .silver import build_silver
from .store import get_store

log = logging.getLogger("tcg")

_SCHEMA_CARTEIRA = pa.schema([("data", pa.date32()), ("group_id", pa.int32()), ("carteira", pa.string()),
                              ("valor_brl", pa.float64()), ("retorno_acumulado", pa.float64()),
                              ("taxa_venda", pa.float64())])


def cmd_check(store, gid):
    ocupados = {int(m.group(1)) for k in store.list("raw/tcgplayer/")
                if (m := re.search(r"group_id=(\d+)/", k))}
    print("Coleções com coleta no lake:", sorted(ocupados) or "nenhuma")
    livres = [f"{s} ({g})" for g, (_, s, _) in config.COLECOES.items() if g not in ocupados]
    print("Livres:", ", ".join(livres))
    nome = config.COLECOES[gid][0]
    print(f"\nSua coleção ({nome}, {gid}):", "JÁ TEM DADOS — confira se é sua ou escolha outra."
          if gid in ocupados else "livre.")


def cmd_carteira(store, gid):
    con = abrir_gold()
    try:
        fato, cambio = carregar_fato(con), carregar_cambio(con)
    finally:
        con.close()
    out, comp = carteira.calcular(fato[fato.group_id == gid], cambio, gid)
    df = out[carteira.CONTRATO].copy()
    df["data"] = df["data"].dt.date
    tabela = pa.Table.from_pandas(df, schema=_SCHEMA_CARTEIRA, preserve_index=False)
    buf = io.BytesIO()
    pq.write_table(tabela, buf)
    store.put(f"gold_turma/carteira/group_id={gid}/carteira.parquet", buf.getvalue())
    store.put(f"gold/group_id={gid}/carteira_composicao.json",
              json.dumps(comp, ensure_ascii=False, indent=2, default=str).encode())
    print(carteira.metricas(out).round(4).to_string(index=False))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="tcg")
    ap.add_argument("comando", choices=["check-colecao", "collect", "silver", "gold", "carteira", "rebuild", "daily"])
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    gid, store = config.group_id(), get_store()

    if a.comando == "check-colecao":
        return cmd_check(store, gid)
    if a.comando in ("collect", "daily"):
        coletar(store, gid)
    if a.comando in ("silver", "rebuild", "daily"):
        build_silver(store, gid)
    if a.comando in ("gold", "rebuild", "daily"):
        build_gold(store, gid)
    if a.comando in ("carteira", "rebuild", "daily"):
        cmd_carteira(store, gid)


if __name__ == "__main__":
    sys.exit(main())
