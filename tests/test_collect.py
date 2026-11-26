from datetime import date, datetime, timezone

from tcg import collect, config
from tcg.store import LocalStore, put_raw


def _falso(chamadas):
    def get(url, tentativas=4):
        chamadas.append(url)
        if "tcgcsv" in url:
            return b'{"success":true,"errors":[],"results":[{"productId":1}]}'
        if "bcdata" in url:
            return b"[]"
        return b'{"value":[]}'
    return get


def test_coleta_repetida_nao_duplica_nem_regrava(tmp_path, monkeypatch):
    chamadas = []
    monkeypatch.setattr(collect, "_get", _falso(chamadas))
    monkeypatch.setattr(collect, "PAUSA_S", 0)
    store = LocalStore(tmp_path)
    r1 = collect.coletar(store, 24269, date(2026, 10, 24))
    n = len(chamadas)
    assert set(r1.values()) == {"gravado"}
    r2 = collect.coletar(store, 24269, date(2026, 10, 24))
    assert set(r2.values()) == {"ja_existia"} and len(chamadas) == n  # nenhuma chamada nova


def test_ptax_dos_ultimos_dias_e_gravada(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "_get", _falso([]))
    store = LocalStore(tmp_path)
    collect.coletar(store, 24269, date(2026, 10, 10))  # sábado: 1º dia pode cair em fim de semana
    assert store.exists("raw/bcb_ptax/group_id=24269/data=2026-10-09/cotacao.json")


def test_bruto_nao_e_sobrescrito(tmp_path):
    store = LocalStore(tmp_path)
    assert put_raw(store, "raw/x.json", b"original") is True
    assert put_raw(store, "raw/x.json", b"outro") is False
    assert store.get("raw/x.json") == b"original"


def test_resposta_invalida_nao_vai_para_o_bruto(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "_get", lambda url, tentativas=4: b'{"success":false,"errors":["x"],"results":[]}')
    store = LocalStore(tmp_path)
    try:
        collect.coletar(store, 24269, date(2026, 10, 24))
        assert False, "deveria falhar"
    except RuntimeError:
        pass
    assert store.list("raw/tcgplayer/") == []


def test_data_referencia_respeita_a_atualizacao_das_20h_utc():
    antes = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)
    depois = datetime(2026, 10, 24, 21, 30, tzinfo=timezone.utc)
    assert config.data_referencia(antes) == date(2026, 10, 23)
    assert config.data_referencia(depois) == date(2026, 10, 24)
