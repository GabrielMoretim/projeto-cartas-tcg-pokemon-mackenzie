"""Coletor diário: TCGplayer (via TCGCSV), PTAX e CDI. Grava o bruto, imutável e idempotente."""
from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta

import requests

from . import config
from .store import put_raw

log = logging.getLogger("tcg.collect")

TCGCSV = "https://tcgcsv.com/tcgplayer/3"
OLINDA = "https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata"
SGS_CDI = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados"
PAUSA_S = 0.15  # o TCGCSV pede >= 100 ms entre chamadas
DIAS_PTAX = 7  # garante PTAX dos últimos dias (cobre o 1º dia em fim de semana e dias perdidos)
JANELA_CDI = 10  # a taxa de um dia útil só sai na manhã seguinte


def _get(url: str, tentativas: int = 4) -> bytes:
    ultimo = None
    for i in range(tentativas):
        time.sleep(PAUSA_S)
        try:
            r = requests.get(url, headers={"User-Agent": config.user_agent()}, timeout=60)
            r.raise_for_status()
            return r.content
        except requests.RequestException as e:
            ultimo = e
            espera = 2 ** (i + 1)
            log.warning("falha em %s (%s); nova tentativa em %ss", url, e, espera)
            time.sleep(espera)
    raise RuntimeError(f"esgotadas as tentativas para {url}") from ultimo


def chave(fonte: str, group_id: int, d: date, arquivo: str) -> str:
    return f"raw/{fonte}/group_id={group_id}/data={d.isoformat()}/{arquivo}"


def url_ptax(d: date) -> str:
    return (f"{OLINDA}/CotacaoMoedaDia(moeda=@moeda,dataCotacao=@dataCotacao)"
            f"?@moeda='USD'&@dataCotacao='{d:%m-%d-%Y}'&$format=json")


def url_cdi(ini: date, fim: date) -> str:
    return f"{SGS_CDI}?formato=json&dataInicial={ini:%d/%m/%Y}&dataFinal={fim:%d/%m/%Y}"


def _tcgcsv_valido(conteudo: bytes, nome: str) -> bytes:
    """Não grava lixo num bruto imutável: exige success=true e resultados."""
    corpo = json.loads(conteudo)
    if not corpo.get("success") or not corpo.get("results"):
        raise RuntimeError(f"resposta do TCGCSV inválida em {nome}: {str(corpo)[:200]}")
    return conteudo


def coletar(store, group_id: int, d: date | None = None) -> dict[str, str]:
    """Roda a coleta do dia. Devolve {chave: 'gravado' | 'ja_existia'}."""
    d = d or config.data_referencia()
    resultado: dict[str, str] = {}

    def gravar(k: str, obter):
        if store.exists(k):
            resultado[k] = "ja_existia"
            return
        put_raw(store, k, obter())
        resultado[k] = "gravado"

    for nome in ("products", "prices"):
        gravar(chave("tcgplayer", group_id, d, f"{nome}.json"),
               lambda n=nome: _tcgcsv_valido(_get(f"{TCGCSV}/{group_id}/{n}"), n))

    # PTAX: fim de semana e feriado devolvem lista vazia; gravamos assim mesmo (é o fato do dia)
    for i in range(DIAS_PTAX):
        dd = d - timedelta(days=i)
        gravar(chave("bcb_ptax", group_id, dd, "cotacao.json"), lambda x=dd: _get(url_ptax(x)))

    gravar(chave("bcb_cdi", group_id, d, "cdi.json"),
           lambda: _get(url_cdi(d - timedelta(days=JANELA_CDI), d)))

    novos = sum(v == "gravado" for v in resultado.values())
    log.info("coleta %s: %d objetos gravados, %d já existiam", d, novos, len(resultado) - novos)
    return resultado
