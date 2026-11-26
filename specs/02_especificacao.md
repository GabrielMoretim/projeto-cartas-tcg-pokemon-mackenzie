# Especificação (resumo)
- **Entradas:** TCGCSV `/3/{groupId}/products|prices`; PTAX Olinda (`CotacaoMoedaDia`); CDI SGS 12.
- **Regras de coleta:** User-Agent próprio, ≥ 100 ms entre chamadas, 1 coleta/dia, bruto imutável por `group_id` e `data`.
- **Silver (contrato da turma):** `colecao`, `produto`, `preco_diario`, `cambio_diario`, `cdi_diario` — nomes e tipos da página do projeto; nulo ≠ zero; inválidos em `quarentena/`.
- **Gold:** estrela (ADR 0001). **Câmbio:** ADR 0002. **Carteiras:** ADRs 0003–0006, 0008.
- **Saída da turma:** `gold_turma/carteira/group_id=X/carteira.parquet` com `data, group_id, carteira, valor_brl, retorno_acumulado, taxa_venda`.
- **Critérios de aceite:** reconstrução por um comando; coleta idempotente; teste de câmbio 09–13/10; teste de composição sem informação do futuro.
