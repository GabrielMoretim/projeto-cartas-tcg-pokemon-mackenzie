"""Contrato comum da silver: modelos Pydantic + schemas Parquet (nomes e tipos fixos)."""
from __future__ import annotations

import json
from datetime import date, datetime
from typing import Literal

import pyarrow as pa
from pydantic import BaseModel, ValidationError, field_validator


class Colecao(BaseModel):
    group_id: int
    nome: str
    sigla: str
    data_lancamento: date
    responsavel: str


class Produto(BaseModel):
    product_id: int
    group_id: int
    nome: str
    tipo_produto: Literal["carta", "selado"]
    raridade: str | None = None
    numero: str | None = None
    image_url: str | None = None
    url: str | None = None


class PrecoDiario(BaseModel):
    data: date
    product_id: int
    group_id: int
    acabamento: str
    market_price: float | None = None  # nulo NÃO é zero
    low_price: float | None = None
    mid_price: float | None = None
    high_price: float | None = None
    moeda: str = "USD"
    fonte: str = "tcgcsv"
    chave_raw: str

    @field_validator("market_price", "low_price", "mid_price", "high_price")
    @classmethod
    def _nao_negativo(cls, v):
        if v is not None and v < 0:
            raise ValueError("preço negativo")
        return v


class CambioDiario(BaseModel):
    data: date
    cotacao_compra: float
    cotacao_venda: float
    data_hora_cotacao: datetime
    boletim: Literal["Fechamento"]
    chave_raw: str

    @field_validator("cotacao_compra", "cotacao_venda")
    @classmethod
    def _positiva(cls, v):
        if v <= 0:
            raise ValueError("cotação deve ser > 0")
        return v


class CdiDiario(BaseModel):
    data: date
    taxa_dia: float  # % ao dia, como publicada
    chave_raw: str

    @field_validator("taxa_dia")
    @classmethod
    def _nao_negativa(cls, v):
        if v < 0:
            raise ValueError("taxa negativa")
        return v


MODELOS = {
    "colecao": Colecao, "produto": Produto, "preco_diario": PrecoDiario,
    "cambio_diario": CambioDiario, "cdi_diario": CdiDiario,
}

_i, _s, _d, _f, _t = pa.int32(), pa.string(), pa.date32(), pa.float64(), pa.timestamp("us")
SCHEMAS = {
    "colecao": pa.schema([("group_id", _i), ("nome", _s), ("sigla", _s),
                          ("data_lancamento", _d), ("responsavel", _s)]),
    "produto": pa.schema([("product_id", _i), ("group_id", _i), ("nome", _s), ("tipo_produto", _s),
                          ("raridade", _s), ("numero", _s), ("image_url", _s), ("url", _s)]),
    "preco_diario": pa.schema([("data", _d), ("product_id", _i), ("group_id", _i), ("acabamento", _s),
                               ("market_price", _f), ("low_price", _f), ("mid_price", _f),
                               ("high_price", _f), ("moeda", _s), ("fonte", _s), ("chave_raw", _s)]),
    "cambio_diario": pa.schema([("data", _d), ("cotacao_compra", _f), ("cotacao_venda", _f),
                                ("data_hora_cotacao", _t), ("boletim", _s), ("chave_raw", _s)]),
    "cdi_diario": pa.schema([("data", _d), ("taxa_dia", _f), ("chave_raw", _s)]),
}


def validar(tabela: str, linhas: list[dict]) -> tuple[list[BaseModel], list[dict]]:
    """Valida cada linha. Devolve (válidas, quarentena com motivo)."""
    modelo, ok, ruins = MODELOS[tabela], [], []
    for linha in linhas:
        try:
            ok.append(modelo(**linha))
        except (ValidationError, TypeError) as e:
            ruins.append({"registro": json.loads(json.dumps(linha, default=str)), "motivo": str(e)})
    return ok, ruins


def para_tabela(tabela: str, registros: list[BaseModel]) -> pa.Table:
    schema = SCHEMAS[tabela]
    return pa.Table.from_pylist([r.model_dump() for r in registros], schema=schema)
