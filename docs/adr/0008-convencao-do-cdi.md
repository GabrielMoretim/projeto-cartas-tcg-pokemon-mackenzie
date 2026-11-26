# ADR 0008 — Convenção de rendimento do CDI
**Status:** aceito
**Decisão:** o valor do dia da compra é R$ 1.000 sem rendimento; a partir do dia seguinte, `valor_t = valor_(t-1) × (1 + taxa_t/100)`, com taxa 0 em dia sem publicação (sábado, domingo, feriado). Vale para a carteira `cdi` e para o caixa das demais.
**Consequência:** a taxa do último dia só entra após a publicação (manhã seguinte); o `rebuild` seguinte a corrige.
