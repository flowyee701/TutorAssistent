"""Хранилище изображений задач.

На проде — S3-совместимое объектное хранилище (Yandex Object Storage).
В dev без настроенного S3 — fallback на локальную файловую систему
(parser/data/images/), что удобно для парсинга и визуальной проверки.
"""

from __future__ import annotations

import logging
from pathlib import Path

from core.config import settings

logger = logging.getLogger(__name__)

LOCAL_IMAGES_DIR = Path(__file__).resolve().parents[2] / "parser" / "data" / "images"


class Storage:
    """Единый интерфейс: save_png(data, key) -> public/локальный URL."""

    def __init__(self) -> None:
        self._use_s3 = bool(
            settings.s3_endpoint_url and settings.s3_bucket and settings.s3_access_key
        )
        self._client = None
        if not self._use_s3:
            LOCAL_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
            logger.info("Storage: S3 не настроен, использую локально %s", LOCAL_IMAGES_DIR)

    def _s3(self):  # noqa: ANN202 — тип boto3-клиента
        if self._client is None:
            import boto3

            self._client = boto3.client(
                "s3",
                endpoint_url=settings.s3_endpoint_url,
                aws_access_key_id=settings.s3_access_key,
                aws_secret_access_key=settings.s3_secret_key,
                region_name=settings.s3_region,
            )
        return self._client

    def save_png(self, data: bytes, key: str) -> str:
        """Сохраняет PNG. key — например 'tasks/math_ege/abc123_p2_i0.png'."""
        if self._use_s3:
            self._s3().put_object(
                Bucket=settings.s3_bucket,
                Key=key,
                Body=data,
                ContentType="image/png",
            )
            base = settings.s3_endpoint_url.rstrip("/")
            return f"{base}/{settings.s3_bucket}/{key}"

        dest = LOCAL_IMAGES_DIR / key
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest.as_uri()


_storage: Storage | None = None


def get_storage() -> Storage:
    global _storage
    if _storage is None:
        _storage = Storage()
    return _storage
