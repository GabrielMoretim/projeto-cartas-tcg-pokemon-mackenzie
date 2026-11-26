# ADR 0002 — Câmbio: última cotação conhecida (nunca posterior)
**Status:** aceito
**Contexto:** TCGplayer publica todo dia; a PTAX só em dia útil.
**Decisão:** preço do dia D usa o boletim `Fechamento` de D ou, se não houver, o do dia útil anterior mais próximo (`ASOF JOIN ... p.data >= c.data`). `fato_preco_diario` guarda `cotacao_venda`, `cotacao_compra` e `data_ptax`.
**Uso das pontas:** série de preços e rankings em reais usam a **venda** (custo de quem compra dólar); a liquidação de carteira usa a **compra** (quem vende dólar recebe a compra).
**Teste:** `tests/test_pipeline.py::test_ptax_fim_de_semana_e_feriado_usam_a_sexta` (09/10 a 13/10/2026).
**Risco:** 1º dia de coleta num fim de semana — mitigado pela coleta da PTAX dos últimos 7 dias (ADR 0007).
