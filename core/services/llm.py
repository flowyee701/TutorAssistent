"""Абстракция LLM-провайдера + готовые задачи (parse_query).

Принципы (см. files/prompts.md, §«Общие принципы»):
- Провайдер абстрагирован: YandexGPT основной, GigaChat — будущий fallback.
- Каждый вызов может упасть → ловим всё, отдаём безопасный результат.
- Снимаем markdown-обёртку ```json перед разбором.
- Логируем в LlmCallLog: purpose, model, токены, стоимость, latency.

SDK YandexGPT синхронный — гоняем его в пуле потоков через asyncio.to_thread.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from pydantic import ValidationError

from core.config import settings
from core.db.engine import SessionLocal
from core.db.models import LlmCallLog
from core.schemas.llm import SearchParams

logger = logging.getLogger(__name__)

# YandexGPT Lite: 0.2 руб / 1000 токенов → копеек за токен
KOPECKS_PER_1K_TOKENS_LITE = 20  # 0.2 руб = 20 коп


def _strip_md(s: str) -> str:
    """Убирает markdown-обёртку ```json ... ``` вокруг JSON."""
    s = s.strip()
    if s.startswith("```"):
        s = s.removeprefix("```json").removeprefix("```").strip()
        s = s.removesuffix("```").strip()
    return s


@dataclass(slots=True)
class LlmResponse:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None

    @property
    def total_tokens(self) -> int | None:
        if self.prompt_tokens is None and self.completion_tokens is None:
            return None
        return (self.prompt_tokens or 0) + (self.completion_tokens or 0)

    def cost_kopecks(self, per_1k: int = KOPECKS_PER_1K_TOKENS_LITE) -> int | None:
        total = self.total_tokens
        if total is None:
            return None
        return round(total / 1000 * per_1k)


class LlmProvider(ABC):
    name: str

    @abstractmethod
    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 300,
    ) -> LlmResponse: ...


class YandexGPTProvider(LlmProvider):
    """Обёртка над YandexGPT Lite. SDK импортируется лениво."""

    def __init__(self, model: str = "yandexgpt-lite") -> None:
        self.name = model
        self._model_name = model
        self._sdk = None

    def _completions(self):  # noqa: ANN202 — тип из внешнего SDK
        if self._sdk is None:
            # Пакет yandex-cloud-ml-sdk помечен deprecated в пользу
            # yandex-ai-studio-sdk, но совместимый импорт ещё работает.
            try:
                from yandex_cloud_ml_sdk import YCloudML
            except ImportError:  # pragma: no cover
                from yandex_ai_studio_sdk import YCloudML  # type: ignore[no-redef]
            if not settings.yc_folder_id or not settings.yc_api_key:
                raise RuntimeError("YC_FOLDER_ID / YC_API_KEY не заданы в .env")
            self._sdk = YCloudML(folder_id=settings.yc_folder_id, auth=settings.yc_api_key)
        return self._sdk.models.completions(self._model_name)

    async def complete(
        self,
        system: str,
        user: str,
        *,
        temperature: float = 0.1,
        max_tokens: int = 300,
    ) -> LlmResponse:
        model = self._completions().configure(temperature=temperature, max_tokens=max_tokens)
        messages = [
            {"role": "system", "text": system},
            {"role": "user", "text": user},
        ]
        result = await asyncio.to_thread(model.run, messages)
        alt = result.alternatives[0]
        usage = getattr(result, "usage", None)
        return LlmResponse(
            text=alt.text,
            model=self._model_name,
            prompt_tokens=getattr(usage, "input_text_tokens", None) if usage else None,
            completion_tokens=getattr(usage, "completion_tokens", None) if usage else None,
        )


_provider: LlmProvider | None = None


def get_provider() -> LlmProvider:
    """Singleton-провайдер, выбирается через env (пока только YandexGPT)."""
    global _provider
    if _provider is None:
        _provider = YandexGPTProvider()
    return _provider


async def log_llm_call(
    *,
    purpose: str,
    response: LlmResponse | None,
    latency_ms: int,
    success: bool,
    user_id: int | None = None,
    model: str | None = None,
) -> None:
    """Пишет строку в LlmCallLog отдельной короткой сессией."""
    try:
        async with SessionLocal() as session:
            session.add(
                LlmCallLog(
                    user_id=user_id,
                    purpose=purpose,
                    model=model or (response.model if response else "unknown"),
                    prompt_tokens=response.prompt_tokens if response else None,
                    completion_tokens=response.completion_tokens if response else None,
                    cost_kopecks=response.cost_kopecks() if response else None,
                    latency_ms=latency_ms,
                    success=success,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 — логирование не должно ронять основной поток
        logger.exception("failed to write LlmCallLog")


# =========================================================================
# Промпты (см. files/prompts.md §1)
# =========================================================================

PARSE_QUERY_SYSTEM = """Ты — помощник репетитора по подготовке к ЕГЭ и ОГЭ. \
Твоя единственная задача — превратить свободный запрос репетитора в структуру \
параметров поиска по базе задач.

ВАЖНО: ты не решаешь задачи и не даёшь советов. Ты только парсишь запрос в JSON.

Верни ТОЛЬКО валидный JSON, без markdown, без ```, без пояснений. Поля (включай \
только те, что явно следуют из запроса):
- subject: "MATH_PROFILE" | "MATH_BASE" | "PHYSICS" | "INFORMATICS"
- exam_type: "OGE" | "EGE"
- topics: массив path тегов из предоставленного списка
- difficulty_min: 1-5
- difficulty_max: 1-5
- count: число задач
- format: "WARMUP" | "HOMEWORK_BY_TOPIC" | "TEST" | "EGE_VARIANT" | "CUSTOM"

Правила:
1. Теги бери ТОЛЬКО из списка, который дан. Если ничего не подходит — topics: [].
2. "Сложный" = 4-5; "средний" = 3; "лёгкий/простой" = 1-2.
3. "Разминка/разогрев" = format WARMUP, count 3-5, difficulty_max 2.
4. "Контрольная" = format TEST. "Вариант ЕГЭ" = format EGE_VARIANT, count около 19.
5. "несколько" = 5, "много" = 15.
6. Если запрос непонятен или не по теме — верни {"error": "Не понял запрос"}.
7. Не подставляй значения, которых нет в запросе.

Примеры:
Запрос: "10 задач на квадратные уравнения, в основном дискриминант, средний уровень и выше, ЕГЭ профиль"
Ответ: {"subject":"MATH_PROFILE","exam_type":"EGE","topics":["algebra.equations.quadratic","algebra.equations.quadratic.discriminant"],"difficulty_min":3,"difficulty_max":5,"count":10,"format":"HOMEWORK_BY_TOPIC"}

Запрос: "контрольная по производным на 4 задачи"
Ответ: {"topics":["calculus.derivatives"],"format":"TEST","count":4}

Запрос: "разогрев по тригонометрии для 11 класса"
Ответ: {"topics":["algebra.equations.trigonometric"],"format":"WARMUP","count":4,"difficulty_max":2}

Запрос: "полный вариант ЕГЭ по физике"
Ответ: {"subject":"PHYSICS","exam_type":"EGE","format":"EGE_VARIANT","count":19}

Запрос: "что-нибудь интересное"
Ответ: {"error":"Не понял запрос"}"""


async def parse_query(
    query: str,
    tags: list[dict],
    *,
    user_id: int | None = None,
) -> SearchParams:
    """Парсит свободный запрос репетитора в SearchParams (prompts.md §1)."""
    provider = get_provider()
    user_prompt = (
        f"Доступные теги:\n{json.dumps(tags, ensure_ascii=False)}\n\n"
        f'Запрос репетитора:\n"{query}"'
    )
    t0 = time.monotonic()
    response: LlmResponse | None = None
    success = False
    try:
        response = await provider.complete(
            PARSE_QUERY_SYSTEM, user_prompt, temperature=0.1, max_tokens=300
        )
        params = SearchParams.model_validate_json(_strip_md(response.text))
        success = params.error is None
    except (ValidationError, json.JSONDecodeError) as exc:
        logger.warning("parse_query bad JSON: %s", exc)
        params = SearchParams(error="Не понял запрос")
    except Exception:  # noqa: BLE001
        logger.exception("parse_query failed")
        params = SearchParams(error="Сервис временно недоступен")
    finally:
        latency_ms = int((time.monotonic() - t0) * 1000)
        await log_llm_call(
            purpose="parse_query",
            response=response,
            latency_ms=latency_ms,
            success=success,
            user_id=user_id,
        )
    return params
