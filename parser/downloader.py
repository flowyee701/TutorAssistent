"""Скачивание PDF-источников ФИПИ в parser/data/raw/<collection>/.

Идемпотентно: уже скачанные непустые файлы пропускаются.
ZIP-архивы автоматически распаковываются (берём *.pdf внутри).
"""

from __future__ import annotations

import logging
import time
import zipfile
from pathlib import Path

import httpx

from parser.sources import RAW_DIR, PdfSource, load_sources

logger = logging.getLogger(__name__)

USER_AGENT = "TutorAI-parser/0.1 (+https://github.com/flowyee701/TutorAssistent)"
TIMEOUT = httpx.Timeout(60.0, connect=15.0)
MAX_RETRIES = 3


def _download_one(client: httpx.Client, source: PdfSource, dest_dir: Path) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / source.filename

    if target.exists() and target.stat().st_size > 0:
        logger.info("skip (exists): %s", target.name)
        return _expand_if_zip(target)

    last_exc: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with client.stream("GET", source.url) as resp:
                resp.raise_for_status()
                tmp = target.with_suffix(target.suffix + ".part")
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                        fh.write(chunk)
                tmp.replace(target)
            logger.info("downloaded %s (%d bytes)", target.name, target.stat().st_size)
            return _expand_if_zip(target)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            wait = 2**attempt
            logger.warning(
                "download failed (%d/%d) %s: %s — retry in %ds",
                attempt, MAX_RETRIES, source.url, exc, wait,
            )
            time.sleep(wait)

    logger.error("giving up on %s: %s", source.url, last_exc)
    return []


def _expand_if_zip(path: Path) -> list[Path]:
    """Если файл — ZIP, распаковывает PDF рядом и возвращает их пути."""
    if zipfile.is_zipfile(path):
        out: list[Path] = []
        with zipfile.ZipFile(path) as zf:
            for member in zf.namelist():
                if member.lower().endswith(".pdf"):
                    extracted = path.parent / Path(member).name
                    if not extracted.exists():
                        extracted.write_bytes(zf.read(member))
                    out.append(extracted)
        logger.info("unzipped %d pdf from %s", len(out), path.name)
        return out
    return [path]


def download_collection(collection: str) -> list[Path]:
    """Скачивает все источники коллекции. Возвращает список локальных PDF."""
    sources = load_sources(collection)
    if not sources:
        logger.warning(
            "коллекция '%s' пуста. Добавь ссылки в parser/data/sources.json "
            "(python -m parser.pipeline sources --template)",
            collection,
        )
        return []

    dest_dir = RAW_DIR / collection
    pdfs: list[Path] = []
    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(timeout=TIMEOUT, headers=headers, follow_redirects=True) as client:
        for src in sources:
            pdfs.extend(_download_one(client, src, dest_dir))

    logger.info("collection '%s': %d pdf готово в %s", collection, len(pdfs), dest_dir)
    return pdfs
