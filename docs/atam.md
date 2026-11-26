# Validação ATAM

| Atributo de qualidade | Cenário | Abordagem | Ponto de sensibilidade | Trade-off | Risco |
|---|---|---|---|---|---|
| Idempotência | Job roda 2× no mesmo dia | `put_raw` só se a chave não existe; teste de coleta repetida | data de referência (ADR 0007) | checagem de existência a cada objeto | rodar antes das 20h UTC grava dia anterior — tratado |
| Reprodutibilidade | Perda da silver/gold | `make rebuild` a partir do `raw/` | ordem de listagem do S3 | custo de reprocessar tudo | bruto corrompido não se corrige (imutável) |
| Consistência entre alunos | Colega grava tipo diferente | Pydantic + schema Arrow fixo; gold com `TRY_CAST` e `union_by_name` | contrato comum | rejeita dado fora do contrato (quarentena) | coluna de colega quebrada vira NULL |
| Correção financeira | Preço em dia sem PTAX | `ASOF JOIN` com última cotação; teste 09–13/10 | regra de câmbio (ADR 0002) | ignora cotação futura mesmo que mais "justa" | 1º dia sem PTAX anterior |
| Sensibilidade a custo | Taxa de venda muda 15%→0% | carteiras gravadas com ambas | `TAXA_VENDA` (ADR 0004) | dobra linhas do contrato | conclusão pode inverter conforme a taxa |
| Observabilidade | Registros inválidos | `quarentena/` + contagem no log | — | custo extra de armazenamento | — |
| Disponibilidade da coleta | GitHub Actions atrasa/falha | cron 21h30 UTC, retries HTTP, PTAX/CDI auto-recuperáveis; preço do dia **não** é recuperável | janela do TCGCSV | — | dia perdido vira lacuna documentada |

**Conclusão a preencher ao final:** resultado do desafio, sensibilidade à taxa e limitações (série curta, preço dos EUA, PTAX ≠ cartão).
