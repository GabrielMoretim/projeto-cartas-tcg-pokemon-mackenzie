# ADR 0005 — Carteira `propria`
**Status:** RASCUNHO — o aluno deve revisar a regra e **commitar este ADR antes do primeiro cálculo da carteira** (exigência da página do projeto).
**Regra proposta (implementada em `montar_propria`):** 50% (R$ 500) em Elite Trainer Box (a mais barata com preço; fallback: selado mais barato) + 50% repartidos igualmente entre as 5 cartas de raridade alta com preço mais próximo de US$ 10 no 1º dia. Unidades inteiras, sobra em caixa.
**Hipótese:** cartas de entrada em raridade alta têm mais liquidez que as mais caras, e o selado diversifica. É uma hipótese, não uma recomendação.
**Evidência de ordem dos commits:** `git log --follow docs/adr/0005-carteira-propria.md` deve preceder a 1ª execução de `python -m tcg carteira`.
