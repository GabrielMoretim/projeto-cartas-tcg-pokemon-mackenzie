# Cartas Pokémon como ativo de coleção

Projeto do módulo *Data Collection and Storage* (MBA Engenharia de Dados, Mackenzie).
Pipeline diário **TCGplayer (TCGCSV) + PTAX + CDI → RustFS (bruto) → silver Parquet/Pydantic → gold DuckDB → dashboard Streamlit**,
com as cinco perguntas de investimento em reais e o desafio da carteira de R$ 1.000.

- **Aluno:** `<SEU NOME>`
- **Coleção escolhida:** `<SIGLA — nome> (groupId <ID>)`  ← preencha depois de rodar `make check`
- **Início da coleta:** `<DD/MM/AAAA>`
- **Lacunas na série:** `<liste cada dia sem coleta e o motivo; "nenhuma" se não houve>`

## Arquitetura

```
TCGCSV ─┐                  raw/ (imutável)          silver/ (contrato da turma)        gold/ (estrela, DuckDB)
BCB PTAX ┼─► collect.py ─► tcg/raw/<fonte>/group_id=X/data=D/ ─► silver.py (Pydantic) ─► gold.py ─► dashboard/app.py
BCB CDI ─┘   (idempotente)                                  └► quarentena/                └► carteira.py ─► gold_turma/carteira/
```

| Camada | Código | Onde grava |
|---|---|---|
| Coleta | `src/tcg/collect.py` | `raw/tcgplayer`, `raw/bcb_ptax`, `raw/bcb_cdi` |
| Silver | `src/tcg/models.py`, `silver.py` | `silver/*`, `quarentena/` |
| Gold | `src/tcg/gold.py` | `gold/group_id=X/` + `data/gold.duckdb` |
| Perguntas | `src/tcg/analytics.py` | — |
| Carteira | `src/tcg/carteira.py` | `gold_turma/carteira/group_id=X/carteira.parquet` |
| Dashboard | `dashboard/app.py` | — |

## Como rodar

```bash
python -m venv .venv && source .venv/bin/activate
make install
cp .env.example .env        # preencha S3_SECRET_KEY (página do projeto), GROUP_ID e RESPONSAVEL
make check                  # lista as coleções já ocupadas no lake — faça ANTES da 1ª gravação
make daily                  # coleta + silver + gold + carteira
make dash                   # abre o Streamlit
make rebuild                # reconstrói silver + gold + carteira SÓ a partir do bruto
make test
```

Para desenvolver sem tocar no lake: `STORE=local` no `.env` (grava em `data/lake/`).

## Agendamento

`.github/workflows/coleta_diaria.yml` roda todo dia às 21h30 UTC (o TCGCSV atualiza ~20h UTC).
Cadastre em *Settings → Secrets and variables → Actions*: secrets `S3_ENDPOINT`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`; variables `GROUP_ID`, `RESPONSAVEL`.
Alternativa: serviço *cron* no Railway rodando `python -m tcg daily`.

## Decisões e rastreabilidade

ADRs em `docs/adr/`, ATAM em `docs/atam.md`, rastreabilidade pergunta → tabela → teste → painel em `docs/rastreabilidade.md`,
artefatos SDD em `specs/`, histórico de prompts em `docs/prompts/`.

## Limites do dado

`market_price` vem de vendas recentes nos EUA, em dólar, sem separar condição; não inclui frete, taxas nem preço no Brasil.
PTAX é taxa de referência (cartão paga outra cotação + IOF). CDI sem IR. A série tem poucas semanas: descreve, não prevê.
