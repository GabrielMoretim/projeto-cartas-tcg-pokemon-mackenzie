# \# ADR 0005 — Carteira `propria`

# 

# \*\*Status:\*\* aceito. Este commit é anterior ao primeiro cálculo oficial da carteira no data lake.

# 

# \*\*Regra (implementada em `montar\_propria`):\*\*

# \- 50% (R$ 500) em uma Elite Trainer Box: a mais barata com preço no 1º dia; se não houver, o selado mais barato com preço.

# \- 50% (R$ 500) repartidos igualmente (R$ 100 cada) entre as 5 cartas de raridade alta com preço mais próximo de US$ 10 no 1º dia.

# \- Unidades inteiras; a sobra fica em caixa e rende CDI.

# \- Só preços do 1º dia entram na escolha (sem informação do futuro).

# 

# \*\*Hipótese:\*\* cartas de raridade alta com preço de entrada baixo tendem a ter mais liquidez que as mais caras, e a ETB diversifica com um selado. É uma hipótese a testar, não uma recomendação.

# 

# \*\*Limitação:\*\* série curta (poucas semanas) e preço de venda dos EUA; o resultado descreve o período, não prevê.

