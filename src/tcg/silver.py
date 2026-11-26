"""Bruto -> silver (Parquet tipado, validado com Pydantic). Reconstruível a partir de raw/."""
from __future__ import annotations

import io
import json
import logging
import re
from datetime import date, datetime

import pyarrow.parquet as pq

from . import config
from .models import para_tabela, validar

log = logging.getLogger("tcg.silver")
_RE_DATA = re.compile(r"data=(\d{4}-\d{2}-\d{2})/")


def _parquet(tabela) -> bytes:
    buf = io.BytesIO()
    pq.write_table(tabela, buf)
    return buf.getvalue()


def _datas_raw(store, fonte: str, group_id: int) -> list[tuple[date, str]]:
    """[(data, chave)] de todos os arquivos do bruto de uma fonte, em ordem de data."""
    saida = []
    for k in store.list(f"raw/{fonte}/group_id={group_id}/"):
        m = _RE_DATA.search(k)
        if m:
            saida.append((date.fromisoformat(m.group(1)), k))
    return sorted(saida)


def _quarentena(store, tabela: str, group_id: int, ruins: list[dict], d: date | None = None):
    if not ruins:
        return
    sufixo = f"/data={d.isoformat()}" if d else ""
    store.put(f"quarentena/{tabela}/group_id={group_id}{sufixo}/erros.json",
              json.dumps(ruins, ensure_ascii=False, default=str).encode())
    log.warning("quarentena %s: %d registros rejeitados", tabela, len(ruins))


def _ext(p: dict) -> dict:
    return {e.get("name"): e.get("value") for e in (p.get("extendedData") or [])}


def classificar(p: dict) -> tuple[str, str | None, str | None]:
    """(tipo_produto, raridade, numero). Carta tem número ou raridade; o resto é selado."""
    ext = _ext(p)
    raridade, numero = ext.get("Rarity"), ext.get("Number")
    return ("carta" if (numero or raridade) else "selado"), raridade, numero


def _produtos(store, group_id: int) -> list[dict]:
    arqs = [x for x in _datas_raw(store, "tcgplayer", group_id) if x[1].endswith("products.json")]
    if not arqs:
        return []
    corpo = json.loads(store.get(arqs[-1][1]))  # catálogo do dia mais recente
    linhas = []
    for p in corpo["results"]:
        tipo, rar, num = classificar(p)
        linhas.append(dict(product_id=p["productId"], group_id=group_id, nome=p["name"],
                           tipo_produto=tipo, raridade=rar, numero=num,
                           image_url=p.get("imageUrl"), url=p.get("url")))
    return linhas


def _precos(store, group_id: int):
    for d, k in _datas_raw(store, "tcgplayer", group_id):
        if not k.endswith("prices.json"):
            continue
        linhas = [dict(data=d, product_id=r["productId"], group_id=group_id,
                       acabamento=r.get("subTypeName"), market_price=r.get("marketPrice"),
                       low_price=r.get("lowPrice"), mid_price=r.get("midPrice"),
                       high_price=r.get("highPrice"), chave_raw=k)
                  for r in json.loads(store.get(k))["results"]]
        yield d, linhas


def _cambio(store, group_id: int) -> list[dict]:
    linhas = []
    for _, k in _datas_raw(store, "bcb_ptax", group_id):
        for b in json.loads(store.get(k)).get("value", []):
            if b.get("tipoBoletim") != "Fechamento":
                continue
            quando = datetime.fromisoformat(b["dataHoraCotacao"])
            linhas.append(dict(data=quando.date(), cotacao_compra=b["cotacaoCompra"],
                               cotacao_venda=b["cotacaoVenda"], data_hora_cotacao=quando,
                               boletim="Fechamento", chave_raw=k))
    return linhas


def _cdi(store, group_id: int) -> list[dict]:
    vistos: dict[date, dict] = {}
    for _, k in _datas_raw(store, "bcb_cdi", group_id):
        for r in json.loads(store.get(k)):
            d = datetime.strptime(r["data"], "%d/%m/%Y").date()
            vistos.setdefault(d, dict(data=d, taxa_dia=float(r["valor"]), chave_raw=k))
    return [vistos[d] for d in sorted(vistos)]


def build_silver(store, group_id: int) -> dict[str, int]:
    nome, sigla, lanc = config.COLECOES[group_id]
    cont: dict[str, int] = {}

    def gravar(tabela, linhas, chave, d=None):
        ok, ruins = validar(tabela, linhas)
        store.put(chave, _parquet(para_tabela(tabela, ok)))
        _quarentena(store, tabela, group_id, ruins, d)
        cont[tabela] = cont.get(tabela, 0) + len(ok)
        cont[f"{tabela}_quarentena"] = cont.get(f"{tabela}_quarentena", 0) + len(ruins)

    gravar("colecao", [dict(group_id=group_id, nome=nome, sigla=sigla, data_lancamento=lanc,
                            responsavel=config.RESPONSAVEL)],
           f"silver/colecao/group_id={group_id}/colecao.parquet")
    gravar("produto", _produtos(store, group_id), f"silver/produto/group_id={group_id}/produto.parquet")
    for d, linhas in _precos(store, group_id):
        gravar("preco_diario", linhas,
               f"silver/preco_diario/group_id={group_id}/data={d.isoformat()}/preco.parquet", d)
    gravar("cambio_diario", _cambio(store, group_id), f"silver/cambio_diario/group_id={group_id}/cambio.parquet")
    gravar("cdi_diario", _cdi(store, group_id), f"silver/cdi_diario/group_id={group_id}/cdi.parquet")
    log.info("silver: %s", cont)
    return cont
