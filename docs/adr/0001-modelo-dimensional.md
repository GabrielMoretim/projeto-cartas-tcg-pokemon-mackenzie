# ADR 0001 — Esquema estrela com fato de preço diário
**Status:** aceito
**Contexto:** as cinco perguntas agregam o preço de um produto, num acabamento, num dia, por coleção, raridade e tipo.
**Decisão:** `fato_preco_diario` (grão: produto × acabamento × dia) e `fato_cambio_diario` (grão: dia de calendário), com `dim_produto`, `dim_colecao`, `dim_data`, `dim_acabamento`.
**Por quê:** P1/P2 agregam por produto/tipo; P3/P4/P5 por coleção e raridade; todas sobre o mesmo fato. Dias desde o lançamento são calculados na consulta (não ficam em dimensão).
**Consequências:** a gold é construída sobre a silver de **todas** as coleções (curinga em `s3://tcg/silver/...`), reconstruível por `make rebuild`.
**Alternativa descartada:** tabela larga única — repete texto de produto em cada linha de preço e dificulta o filtro de Code Card.
