# ADR 0007 — Bruto imutável, data de referência e idempotência
**Status:** aceito
**Decisão:** (1) `raw/` só recebe `put` se a chave não existir; (2) a data da chave é a **data de referência** do preço: antes de 20h30 UTC é o dia anterior, porque o TCGCSV só atualiza ~20h UTC — gravar o preço velho como "hoje" corromperia um bruto que não pode ser regravado; (3) resposta com `success=false` ou sem resultados não é gravada; (4) a cada execução a PTAX dos últimos 7 dias é garantida (fim de semana/feriado gravam lista vazia), o que também cobre o 1º dia em fim de semana e dias perdidos; (5) o CDI é buscado numa janela de 10 dias porque a taxa só sai na manhã seguinte.
**Testes:** `tests/test_collect.py`.
