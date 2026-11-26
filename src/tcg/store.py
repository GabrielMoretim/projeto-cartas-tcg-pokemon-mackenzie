"""Acesso ao data lake: S3/RustFS (produção) ou pasta local (desenvolvimento e testes)."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from . import config


class S3Store:
    def __init__(self):
        import boto3
        from botocore.config import Config

        self.bucket = config.S3_BUCKET
        self.client = boto3.client(
            "s3",
            endpoint_url=config.S3_ENDPOINT,
            aws_access_key_id=config.S3_ACCESS_KEY,
            aws_secret_access_key=config.S3_SECRET_KEY,
            region_name=config.S3_REGION,
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 5}),
        )

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def put(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def list(self, prefix: str) -> list[str]:
        keys, pag = [], self.client.get_paginator("list_objects_v2")
        for page in pag.paginate(Bucket=self.bucket, Prefix=prefix):
            keys += [o["Key"] for o in page.get("Contents", [])]
        return sorted(keys)

    def uri(self, key: str) -> str:
        return f"s3://{self.bucket}/{key}"

    def setup_duckdb(self, con) -> None:
        u = urlparse(config.S3_ENDPOINT)
        con.execute("INSTALL httpfs; LOAD httpfs;")
        con.execute(f"SET s3_endpoint='{u.netloc}'")
        con.execute(f"SET s3_region='{config.S3_REGION}'")
        con.execute(f"SET s3_access_key_id='{config.S3_ACCESS_KEY}'")
        con.execute(f"SET s3_secret_access_key='{config.S3_SECRET_KEY}'")
        con.execute("SET s3_url_style='path'")
        con.execute(f"SET s3_use_ssl={'true' if u.scheme == 'https' else 'false'}")


class LocalStore:
    """Mesma interface do S3Store, em disco. Usada nos testes e com STORE=local."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root or config.LOCAL_LAKE)

    def _p(self, key: str) -> Path:
        return self.root / key

    def exists(self, key: str) -> bool:
        return self._p(key).exists()

    def put(self, key: str, data: bytes) -> None:
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._p(key).read_bytes()

    def list(self, prefix: str) -> list[str]:
        base = self.root
        if not base.exists():
            return []
        return sorted(
            p.relative_to(base).as_posix()
            for p in base.rglob("*")
            if p.is_file() and p.relative_to(base).as_posix().startswith(prefix)
        )

    def uri(self, key: str) -> str:
        return str(self._p(key))

    def setup_duckdb(self, con) -> None:
        pass


def get_store():
    return LocalStore() if config.STORE == "local" else S3Store()


def put_raw(store, key: str, data: bytes) -> bool:
    """Grava no bruto só se a chave não existir (imutabilidade + idempotência)."""
    if store.exists(key):
        return False
    store.put(key, data)
    return True
