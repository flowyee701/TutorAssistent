"""FastAPI приложение для Mini App и вебхуков.

Запуск:
    uvicorn api.main:app --reload
"""

from __future__ import annotations

import logging

from fastapi import FastAPI
from sqlalchemy import text

from core.config import settings
from core.db.engine import engine

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Tutor AI API",
    version="0.1.0",
    docs_url="/docs" if settings.app_env != "prod" else None,
    redoc_url=None,
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, object]:
    """Базовый health-check: проверяет подключение к БД."""
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:  # noqa: BLE001
        logger.warning("db health failed: %s", exc)
    return {
        "status": "ok" if db_ok else "degraded",
        "env": settings.app_env,
        "db": db_ok,
    }
