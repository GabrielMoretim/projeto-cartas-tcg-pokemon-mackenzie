# ADR 0006 — Preço ausente: último preço observado
**Status:** aceito
**Decisão:** na silver, preço ausente fica **nulo** (nulo ≠ zero, não entra em média nem variação). Só na *avaliação* (carteira e índices das perguntas 2–5) o último preço observado é carregado para a frente. Nada inventado é gravado; a coluna `preco_carregado` marca os dias e vira a métrica "dias com preço carregado".
