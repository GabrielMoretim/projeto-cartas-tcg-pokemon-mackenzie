# Rastreabilidade

| # | Pergunta | Tabelas gold | Função | Teste | Painel |
|---|---|---|---|---|---|
| 1 | Cartas que mais valorizaram/desvalorizaram (carta × câmbio × cruzado) | `fato_preco_diario`, `dim_produto` | `analytics.pergunta1` | `test_analytics.py` (decomposição 10%/5%/15,5%, filtro US$ 1, nulo) | Aba 1 |
| 2 | Selado × cartas Double Rare+ (base 100) | `fato_preco_diario`, `dim_produto` | `pergunta2` | verificar com dados reais | Aba 2 |
| 3 | Coleção da turma que mais valorizou (+ PTAX) | `fato_preco_diario`, `dim_colecao`, `fato_cambio_diario` | `pergunta3` | verificar com dados reais | Aba 3 |
| 4 | Concentração por raridade e cartas que somam 80% | `fato_preco_diario`, `dim_produto` | `pergunta4` | verificar com dados reais | Aba 4 |
| 5 | Retorno × volatilidade (> US$ 5) | `fato_preco_diario`, `dim_produto` | `pergunta5` | verificar com dados reais | Aba 5 |
| Desafio | 5 carteiras vs dólar e CDI | `fato_preco_diario`, `fato_cambio_diario` | `carteira.calcular` | `test_carteira.py` | Aba "Desafio" |
