# ADR 0003 — Montagem das carteiras `selado` e `cesta_raras`
**Status:** aceito, com ponto em aberto (ver abaixo)
**Decisão:** compra no 1º dia de coleta pela PTAX de **venda**, em **unidades inteiras**, sobra em caixa rendendo CDI. Composição usa só preços do 1º dia (teste `test_sem_informacao_do_futuro`).
- `selado`: booster box da coleção (o de maior preço se houver mais de um, excluindo *case*); se não tiver preço no 1º dia, o selado de maior preço com preço.
- `cesta_raras`: R$ 100 em cada uma das 10 cartas de maior `market_price` (sem Code Card, um acabamento por produto).
**Ponto em aberto:** as 10 cartas mais caras de uma coleção costumam custar mais que R$ 100 por unidade. Lido ao pé da letra (unidade inteira), unidades = 0 para elas e o valor fica em caixa (= CDI). A implementação segue a leitura literal e o painel lista "cartas não compradas". **Levar à mentoria de 05/12** e, se o professor aceitar outra leitura (ex.: comprar 1 unidade enquanto houver caixa), registrar aqui e trocar `montar_cesta`.
