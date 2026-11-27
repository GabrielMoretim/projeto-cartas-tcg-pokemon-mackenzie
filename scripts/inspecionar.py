"""Inspeciona coleções no TCGCSV antes de escolher (só leitura)."""
import sys
import time

import requests

from tcg.silver import classificar

H = {"User-Agent": "inspecao-colecao/1.0"}


def get(url):
    time.sleep(0.3)
    r = requests.get(url, headers=H, timeout=60)
    r.raise_for_status()
    return r.json()["results"]


for g in sys.argv[1:]:
    base = f"https://tcgcsv.com/tcgplayer/3/{g}"
    prods = get(f"{base}/products")
    precos = get(f"{base}/prices")
    maior = {}
    for p in precos:
        v = p.get("marketPrice")
        if v is not None:
            maior[p["productId"]] = max(v, maior.get(p["productId"], 0))
    cartas = [p for p in prods if classificar(p)[0] == "carta"]
    selados = [p for p in prods if classificar(p)[0] == "selado"]
    box = [p for p in selados if "booster box" in p["name"].lower()
           and " case" not in p["name"].lower() and p["productId"] in maior]
    etb = [p for p in selados if "elite trainer box" in p["name"].lower() and p["productId"] in maior]
    top = sorted((maior.get(p["productId"], 0) for p in cartas), reverse=True)
    print(f"\n=== {g} ===")
    print(f"produtos: {len(prods)} | cartas: {len(cartas)} | selados: {len(selados)}")
    print(f"booster box com preco: {[(p['name'], maior[p['productId']]) for p in box] or 'NENHUMA'}")
    print(f"elite trainer box com preco: {len(etb)}")
    print(f"cartas > US$1: {sum(v > 1 for v in top)} | > US$5: {sum(v > 5 for v in top)}")
    print(f"5 cartas mais caras (US$): {top[:5]}")