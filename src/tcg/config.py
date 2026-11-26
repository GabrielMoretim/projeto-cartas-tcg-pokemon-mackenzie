"""Configuração central, lida do ambiente (.env)."""
import os
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

TZ = ZoneInfo("America/Sao_Paulo")

# group_id: (nome, sigla, lançamento). Fonte: página do projeto (TCGplayer, categoryId 3).
COLECOES = {
    23381: ("SV05: Temporal Forces", "TEF", date(2024, 3, 22)),
    23473: ("SV06: Twilight Masquerade", "TWM", date(2024, 5, 24)),
    23529: ("SV: Shrouded Fable", "SFA", date(2024, 8, 2)),
    23537: ("SV07: Stellar Crown", "SCR", date(2024, 9, 13)),
    23651: ("SV08: Surging Sparks", "SSP", date(2024, 11, 8)),
    23821: ("SV: Prismatic Evolutions", "PRE", date(2025, 1, 17)),
    24073: ("SV09: Journey Together", "JTG", date(2025, 3, 28)),
    24269: ("SV10: Destined Rivals", "DRI", date(2025, 5, 30)),
    24325: ("SV: Black Bolt", "BLK", date(2025, 7, 18)),
    24326: ("SV: White Flare", "WHT", date(2025, 7, 18)),
    24380: ("ME01: Mega Evolution", "MEG", date(2025, 9, 26)),
    24448: ("ME02: Phantasmal Flames", "PFL", date(2025, 11, 14)),
    24541: ("ME: Ascended Heroes", "ASC", date(2026, 1, 30)),
    24587: ("ME03: Perfect Order", "POR", date(2026, 3, 27)),
    24655: ("ME04: Chaos Rising", "CRI", date(2026, 5, 22)),
    24688: ("ME05: Pitch Black", "PBL", date(2026, 7, 17)),
    24722: ("ME: 30th Celebration", "30C", date(2026, 9, 16)),
}

S3_ENDPOINT = os.getenv("S3_ENDPOINT", "https://lake-aulas-mackenzie.afonsolelis.tech")
S3_ACCESS_KEY = os.getenv("S3_ACCESS_KEY", "")
S3_SECRET_KEY = os.getenv("S3_SECRET_KEY", "")
S3_REGION = os.getenv("S3_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET", "tcg")
STORE = os.getenv("STORE", "s3")
LOCAL_LAKE = Path(os.getenv("LOCAL_LAKE", "data/lake"))
GOLD_DB = Path(os.getenv("GOLD_DB", "data/gold.duckdb"))

RESPONSAVEL = os.getenv("RESPONSAVEL", "")
TAXA_VENDA = float(os.getenv("TAXA_VENDA", "0.15"))
CAPITAL = 1000.0

# Raridades de "Double Rare em diante" (pergunta 2) e da carteira própria.
# Confira com: SELECT DISTINCT raridade FROM dim_produto  e ajuste conforme a sua coleção.
RARIDADES_ALTAS = {
    "Double Rare", "Ultra Rare", "ACE SPEC Rare", "Illustration Rare",
    "Special Illustration Rare", "Hyper Rare", "Shiny Rare", "Shiny Ultra Rare",
    "Mega Hyper Rare", "Mega Attack Rare", "Black White Rare",
}
RARIDADE_FORA = "Code Card"  # cartas de código digital: fora das perguntas 1, 3 e 4


def group_id() -> int:
    v = os.getenv("GROUP_ID")
    if not v:
        raise SystemExit("Defina GROUP_ID no .env (veja a tabela de coleções no README).")
    gid = int(v)
    if gid not in COLECOES:
        raise SystemExit(f"GROUP_ID {gid} não está na tabela de coleções.")
    return gid


def user_agent() -> str:
    return f"colecao-{COLECOES[group_id()][1].lower()}/1.0"


def data_referencia(agora_utc: datetime | None = None) -> date:
    """Data a que o preço coletado se refere.

    O TCGCSV atualiza por volta de 20h UTC. Antes de 20h30 UTC o que se baixa ainda é o
    preço do dia anterior; gravá-lo como 'hoje' envenenaria o bruto imutável (ADR 0007).
    """
    agora = agora_utc or datetime.now(timezone.utc)
    return agora.date() if agora.time() >= time(20, 30) else agora.date() - timedelta(days=1)
