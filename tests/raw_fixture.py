"""Gera um bruto sintético (formato real do TCGCSV/BCB) para os testes de integração."""
import json

from helpers import CDI, DIAS, PTAX


def _ptax(d):
    if d not in PTAX:
        return {"value": []}  # sábado, domingo, feriado
    c, v = PTAX[d]
    return {"value": [
        {"cotacaoCompra": c - 0.01, "cotacaoVenda": v - 0.01, "dataHoraCotacao": f"{d} 10:08:00.000", "tipoBoletim": "Abertura"},
        {"cotacaoCompra": c, "cotacaoVenda": v, "dataHoraCotacao": f"{d} 13:09:12.123", "tipoBoletim": "Fechamento PTAX"}]}


def popular_raw(store, gid, preco_ruim=False):
    produtos = [
        {"productId": 1, "name": "Carta A", "imageUrl": "http://i/1.jpg", "url": "http://u/1", "groupId": gid,
         "extendedData": [{"name": "Number", "value": "001/100"}, {"name": "Rarity", "value": "Ultra Rare"}]},
        {"productId": 2, "name": "Carta B", "imageUrl": "http://i/2.jpg", "url": "http://u/2", "groupId": gid,
         "extendedData": [{"name": "Number", "value": "002/100"}, {"name": "Rarity", "value": "Common"}]},
        {"productId": 3, "name": "Destined Rivals Booster Box", "imageUrl": "http://i/3.jpg", "url": "http://u/3",
         "groupId": gid, "extendedData": []},
    ]
    for k, d in enumerate(DIAS):
        base = f"raw/tcgplayer/group_id={gid}/data={d}"
        store.put(f"{base}/products.json", json.dumps({"success": True, "results": produtos}).encode())
        precos = [
            {"productId": 1, "subTypeName": "Holofoil", "marketPrice": 50.0 + k, "lowPrice": 40.0, "midPrice": 50.0, "highPrice": 60.0},
            {"productId": 2, "subTypeName": "Normal", "marketPrice": None, "lowPrice": None, "midPrice": None, "highPrice": None},
            {"productId": 3, "subTypeName": "Normal", "marketPrice": 110.0, "lowPrice": 100.0, "midPrice": 110.0, "highPrice": 120.0},
        ]
        if preco_ruim and k == 2:
            precos.append({"productId": 1, "subTypeName": "Normal", "marketPrice": -5.0})
        store.put(f"{base}/prices.json", json.dumps({"success": True, "results": precos}).encode())
        store.put(f"raw/bcb_ptax/group_id={gid}/data={d}/cotacao.json", json.dumps(_ptax(d)).encode())
    ultimo = DIAS[-1]
    cdi = [{"data": f"{d:%d/%m/%Y}", "valor": f"{v:.6f}"} for d, v in sorted(CDI.items())]
    store.put(f"raw/bcb_cdi/group_id={gid}/data={ultimo}/cdi.json", json.dumps(cdi).encode())
