"""Silver da turma -> gold dimensional no DuckDB (esquema estrela)."""
from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import duckdb
import pandas as pd

from . import config

log = logging.getLogger("tcg.gold")

GOLD_TABELAS = ["fato_preco_diario", "fato_cambio_diario", "dim_produto", "dim_colecao",
                "dim_data", "dim_acabamento"]

_PARQ = "union_by_name=true, hive_partitioning=false"  # tolera colunas extras dos colegas


def fontes_silver(store) -> dict[str, str]:
    u = store.uri
    return {
        "colecao": u("silver/colecao/*/colecao.parquet"),
        "produto": u("silver/produto/*/produto.parquet"),
        "preco": u("silver/preco_diario/*/*/*.parquet"),
        "cambio": u("silver/cambio_diario/*/cambio.parquet"),
        "cdi": u("silver/cdi_diario/*/cdi.parquet"),
    }


def construir(con: duckdb.DuckDBPyConnection, src: dict[str, str]) -> None:
    """Cria as tabelas gold a partir de globs de Parquet da silver (de todas as coleções)."""
    q = lambda k: f"read_parquet('{src[k]}', {_PARQ})"  # noqa: E731

    con.execute(f"""
        CREATE OR REPLACE TABLE stg_preco AS
        SELECT CAST(data AS DATE) AS data, CAST(product_id AS INTEGER) AS product_id,
               CAST(group_id AS INTEGER) AS group_id, CAST(acabamento AS VARCHAR) AS acabamento,
               TRY_CAST(market_price AS DOUBLE) AS market_price, TRY_CAST(low_price AS DOUBLE) AS low_price,
               TRY_CAST(mid_price AS DOUBLE) AS mid_price, TRY_CAST(high_price AS DOUBLE) AS high_price
        FROM {q('preco')}
        WHERE data IS NOT NULL AND acabamento IS NOT NULL
        QUALIFY row_number() OVER (PARTITION BY data, product_id, group_id, acabamento ORDER BY chave_raw) = 1
    """)
    # PTAX e CDI são iguais para todos: une as cópias de cada aluno e deduplica por data
    con.execute(f"""
        CREATE OR REPLACE TABLE stg_cambio AS
        SELECT data, arg_max(cotacao_compra, data_hora_cotacao) AS cotacao_compra,
                     arg_max(cotacao_venda, data_hora_cotacao) AS cotacao_venda
        FROM (SELECT CAST(data AS DATE) AS data, TRY_CAST(cotacao_compra AS DOUBLE) AS cotacao_compra,
                     TRY_CAST(cotacao_venda AS DOUBLE) AS cotacao_venda,
                     TRY_CAST(data_hora_cotacao AS TIMESTAMP) AS data_hora_cotacao
              FROM {q('cambio')})
        WHERE cotacao_venda IS NOT NULL AND cotacao_compra IS NOT NULL
        GROUP BY data
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE stg_cdi AS
        SELECT CAST(data AS DATE) AS data, max(TRY_CAST(taxa_dia AS DOUBLE)) AS taxa_dia
        FROM {q('cdi')} GROUP BY 1
    """)

    d0, d1 = con.execute("SELECT min(data), max(data) FROM stg_preco").fetchone()
    if d0 is None:
        raise RuntimeError("silver sem preços: rode a coleta e `python -m tcg silver` antes do gold")

    con.execute(f"""
        CREATE OR REPLACE TABLE dim_colecao AS
        SELECT CAST(group_id AS INTEGER) AS group_id, nome, sigla,
               CAST(data_lancamento AS DATE) AS data_lancamento, responsavel,
               CASE WHEN regexp_matches(nome, '^ME') THEN 'Mega Evolution'
                    ELSE 'Scarlet & Violet' END AS serie
        FROM {q('colecao')}
        QUALIFY row_number() OVER (PARTITION BY group_id ORDER BY nome) = 1
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_produto AS
        SELECT CAST(product_id AS INTEGER) AS product_id, CAST(group_id AS INTEGER) AS group_id,
               nome, tipo_produto,
               CASE WHEN tipo_produto <> 'selado' THEN NULL
                    WHEN lower(nome) LIKE '% case%' THEN 'booster box case'
                    WHEN lower(nome) LIKE '%booster box%' THEN 'booster box'
                    WHEN lower(nome) LIKE '%elite trainer box%' THEN 'elite trainer box'
                    WHEN lower(nome) LIKE '%booster bundle%' THEN 'booster bundle'
                    WHEN lower(nome) LIKE '%blister%' THEN 'blister'
                    WHEN lower(nome) LIKE '%booster pack%' THEN 'booster pack'
                    ELSE 'outro' END AS categoria_selado,
               raridade, numero, image_url, url
        FROM {q('produto')}
        QUALIFY row_number() OVER (PARTITION BY product_id, group_id ORDER BY nome) = 1
    """)
    con.execute("""
        CREATE OR REPLACE TABLE dim_acabamento AS
        SELECT CAST(row_number() OVER (ORDER BY acabamento) AS INTEGER) AS acabamento_id, acabamento
        FROM (SELECT DISTINCT acabamento FROM stg_preco)
    """)
    con.execute(f"""
        CREATE OR REPLACE TABLE dim_data AS
        SELECT CAST(d AS DATE) AS data, dayname(CAST(d AS DATE)) AS dia_semana,
               isodow(CAST(d AS DATE)) AS dia_semana_num, weekofyear(CAST(d AS DATE)) AS semana,
               strftime(CAST(d AS DATE), '%Y-%m') AS mes
        FROM generate_series(DATE '{d0}', DATE '{d1}', INTERVAL 1 DAY) t(d)
    """)
    # Um dia de calendário: PTAX da última cotação conhecida (nunca posterior) + CDI (0 sem taxa)
    con.execute("""
        CREATE OR REPLACE TABLE fato_cambio_diario AS
        SELECT cal.data, c.cotacao_compra, c.cotacao_venda, c.data AS data_ptax,
               COALESCE(d.taxa_dia, 0.0) AS cdi_taxa_dia
        FROM dim_data cal
        ASOF LEFT JOIN stg_cambio c ON cal.data >= c.data
        LEFT JOIN stg_cdi d ON d.data = cal.data
    """)
    con.execute("""
        CREATE OR REPLACE TABLE fato_preco_diario AS
        SELECT x.data, x.product_id, x.group_id, x.acabamento, a.acabamento_id,
               x.market_price, x.low_price, x.mid_price, x.high_price,
               x.cotacao_compra, x.cotacao_venda, x.data_ptax,
               x.market_price * x.cotacao_venda AS market_price_brl,
               x.low_price * x.cotacao_venda AS low_price_brl,
               x.mid_price * x.cotacao_venda AS mid_price_brl,
               x.high_price * x.cotacao_venda AS high_price_brl
        FROM (SELECT p.*, c.cotacao_compra, c.cotacao_venda, c.data AS data_ptax
              FROM stg_preco p ASOF LEFT JOIN stg_cambio c ON p.data >= c.data) x
        LEFT JOIN dim_acabamento a ON a.acabamento = x.acabamento
    """)
    sem_cambio = con.execute("SELECT count(*) FROM fato_preco_diario WHERE cotacao_venda IS NULL").fetchone()[0]
    if sem_cambio:
        log.warning("%d linhas de preço sem PTAX anterior (1º dia antes de qualquer cotação?)", sem_cambio)


def build_gold(store, group_id: int, exportar: bool = True) -> Path:
    config.GOLD_DB.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.GOLD_DB))
    try:
        store.setup_duckdb(con)
        construir(con, fontes_silver(store))
        if exportar:
            for t in GOLD_TABELAS:
                with tempfile.TemporaryDirectory() as tmp:
                    arq = Path(tmp) / f"{t}.parquet"
                    con.execute(f"COPY {t} TO '{arq}' (FORMAT PARQUET)")
                    store.put(f"gold/group_id={group_id}/{t}.parquet", arq.read_bytes())
    finally:
        con.close()
    return config.GOLD_DB


def abrir_gold(somente_leitura: bool = True) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(config.GOLD_DB), read_only=somente_leitura)


def carregar_fato(con) -> pd.DataFrame:
    """Fato de preço já enriquecido com produto e coleção (insumo das análises)."""
    df = con.execute("""
        SELECT f.data, f.group_id, c.sigla, f.product_id, f.acabamento, f.market_price,
               f.market_price_brl, f.cotacao_compra, f.cotacao_venda,
               p.nome, p.tipo_produto, p.categoria_selado, p.raridade, p.numero, p.image_url, p.url
        FROM fato_preco_diario f
        JOIN dim_produto p ON p.product_id = f.product_id AND p.group_id = f.group_id
        JOIN dim_colecao c ON c.group_id = f.group_id
    """).df()
    df["data"] = pd.to_datetime(df["data"])
    return df


def carregar_cambio(con) -> pd.DataFrame:
    df = con.execute("SELECT * FROM fato_cambio_diario ORDER BY data").df()
    df["data"] = pd.to_datetime(df["data"])
    return df
