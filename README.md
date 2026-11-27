# Cartas Pokémon como ativo de coleção

Projeto do módulo *Data Collection and Storage* (MBA Engenharia de Dados, Mackenzie).
Pipeline diário **TCGplayer (TCGCSV) + PTAX + CDI → RustFS (bruto) → silver Parquet/Pydantic → gold DuckDB → dashboard Streamlit**,
com as cinco perguntas de investimento em reais e o desafio da carteira de R$ 1.000.

**- \*\*Aluno:\*\* Gabriel Moretim**

**- \*\*Repositório:\*\* https://github.com/GabrielMoretim/projeto-cartas-tcg-pokemon-mackenzie**

**- \*\*Coleção escolhida:\*\* ME05: Pitch Black (PBL, groupId 24688)**

**- \*\*Início da coleta:\*\* 26/11/2026**

**- \*\*Lacunas na série:\*\* nenhuma até o momento.**

## Arquitetura

```
TCGCSV ─┐                  raw/ (imutável)          silver/ (contrato da turma)        gold/ (estrela, DuckDB)
BCB PTAX ┼─► collect.py ─► tcg/raw/<fonte>/group\_id=X/data=D/ ─► silver.py (Pydantic) ─► gold.py ─► dashboard/app.py
BCB CDI ─┘   (idempotente)                                  └► quarentena/                └► carteira.py ─► gold\_turma/carteira/
```

|Camada|Código|Onde grava|
|-|-|-|
|Coleta|`src/tcg/collect.py`|`raw/tcgplayer`, `raw/bcb\_ptax`, `raw/bcb\_cdi`|
|Silver|`src/tcg/models.py`, `silver.py`|`silver/\*`, `quarentena/`|
|Gold|`src/tcg/gold.py`|`gold/group\_id=X/` + `data/gold.duckdb`|
|Perguntas|`src/tcg/analytics.py`|—|
|Carteira|`src/tcg/carteira.py`|`gold\_turma/carteira/group\_id=X/carteira.parquet`|
|Dashboard|`dashboard/app.py`|—|

## Como rodar

```bash
python -m venv .venv \&\& source .venv/bin/activate
make install
cp .env.example .env        # preencha S3\_SECRET\_KEY (página do projeto), GROUP\_ID e RESPONSAVEL
make check                  # lista as coleções já ocupadas no lake — faça ANTES da 1ª gravação
make daily                  # coleta + silver + gold + carteira
make dash                   # abre o Streamlit
make rebuild                # reconstrói silver + gold + carteira SÓ a partir do bruto
make test
```

Para desenvolver sem tocar no lake: `STORE=local` no `.env` (grava em `data/lake/`).

## Agendamento

`.github/workflows/coleta\_diaria.yml` roda todo dia às 21h30 UTC (o TCGCSV atualiza \~20h UTC).
Cadastre em *Settings → Secrets and variables → Actions*: secrets `S3\_ENDPOINT`, `S3\_ACCESS\_KEY`, `S3\_SECRET\_KEY`; variables `GROUP\_ID`, `RESPONSAVEL`.
Alternativa: serviço *cron* no Railway rodando `python -m tcg daily`.

## Decisões e rastreabilidade

ADRs em `docs/adr/`, ATAM em `docs/atam.md`, rastreabilidade pergunta → tabela → teste → painel em `docs/rastreabilidade.md`,
artefatos SDD em `specs/`, histórico de prompts em `docs/prompts/`.

## Limites do dado

`market\_price` vem de vendas recentes nos EUA, em dólar, sem separar condição; não inclui frete, taxas nem preço no Brasil.
PTAX é taxa de referência (cartão paga outra cotação + IOF). CDI sem IR. A série tem poucas semanas: descreve, não prevê.



\## Por que a PBL



A coleção foi escolhida depois de comparar os preços reais do TCGCSV em 27/11/2026. A booster box da PBL custava US$ 167,73 (cerca de R$ 964 pela PTAX de venda do dia 1), então cabe nos R$ 1.000 do desafio e a carteira `selado` compra 1 unidade. Em PRE, WHT, SFA e 30C não há booster box com preço; em JTG, PFL, POR, SCR e DRI a caixa custa mais de R$ 1.000. A PBL também tem 11 cartas acima de US$ 5 (pergunta 5) e Elite Trainer Box (carteira própria).



\## No Windows (sem make)



&#x20;   python -m venv .venv

&#x20;   .venv\\Scripts\\activate

&#x20;   pip install -r requirements.txt

&#x20;   copy .env.example .env

&#x20;   set PYTHONPATH=src

&#x20;   python -m tcg check-colecao

&#x20;   python -m tcg daily

&#x20;   python -m tcg rebuild

&#x20;   python -m pytest -q

&#x20;   streamlit run dashboard\\app.py



Para gravar só em disco (sem tocar no lake da turma), use `set STORE=local` antes de rodar.



\## Observações sobre o resultado



\- A carteira de cada coleção é contada a partir do primeiro dia de coleta dela, então os retornos de coleções que começaram em dias diferentes não são comparáveis entre si. A comparação entre coleções usa a janela comum (pergunta 3).

\- Na regra literal da cesta de raras (R$ 100 por carta, unidades inteiras), as cartas mais caras não são compradas e o valor fica em caixa; ver ADR 0003.

