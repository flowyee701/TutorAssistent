# Tutor AI

AI-ассистент репетиторов: Telegram-бот + Mini App для сборки домашних заданий из проверенного банка задач (ЕГЭ/ОГЭ).

> Стек: Python 3.12 · aiogram 3 · FastAPI · SQLAlchemy 2.0 (async) · Alembic · PostgreSQL 16 + pgvector · Redis · YandexGPT · ЮKassa.

## Структура

```
core/        # Бизнес-логика, БД, сервисы
  config.py
  db/        # модели, движок, сидинг тегов
bot/         # Telegram-бот (aiogram)
api/         # FastAPI для Mini App и вебхуков
parser/      # Парсинг PDF в задачи (позже)
migrations/  # Alembic
pdf_templates/
tests/
```

## Быстрый старт

### 1. Зависимости

Рекомендуется [uv](https://docs.astral.sh/uv/) — быстрый и без сюрпризов.

```bash
# установить uv (один раз)
curl -LsSf https://astral.sh/uv/install.sh | sh

# создать venv и установить зависимости
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Альтернатива — обычный `pip`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Env

```bash
cp .env.example .env
# заполнить TELEGRAM_BOT_TOKEN, YC_*, YOOKASSA_* по мере появления
```

### 3. Postgres + Redis

```bash
docker compose up -d
docker compose ps   # postgres healthy, redis healthy
```

### 4. Миграции

```bash
alembic upgrade head
```

Создать новую миграцию после изменений в `core/db/models.py`:

```bash
alembic revision --autogenerate -m "add something"
alembic upgrade head
```

### 5. Сидинг тегов

```bash
python -m core.db.seed
# или один файл:
python -m core.db.seed tags_math_ege.json
```

В БД появится дерево тегов для математики (профильная), ЕГЭ. Аналогичные JSON-файлы для других предметов/уровней кладите в `core/db/tags/`.

### 6. Запуск

```bash
# бот (long polling)
python -m bot.main

# API
uvicorn api.main:app --reload --port 8000
# health-check:
curl http://localhost:8000/health
```

### Deep link для реферала

Формат: `https://t.me/<TELEGRAM_BOT_USERNAME>?start=ref_<USER_ID>`. При первом `/start` бот проставит `referred_by_id` у нового пользователя.

## Разработка

```bash
ruff check .
black .
pytest
```

## Парсер ФИПИ и наполнение банка (Спринт 2)

Конвейер `parser/`: скачивание PDF → парсинг в `Task` → автотегирование через YandexGPT.

```bash
# 0. Тяжёлый OCR-стек (torch) ставится отдельно и только если нужен OCR формул:
pip install -e ".[parser]"

# 1. Источники. ФИПИ меняет ссылки — отредактируй URL в шаблоне:
python -m parser.pipeline sources --template      # создаст parser/data/sources.json
#    впиши реальные ссылки на демоверсии/PDF, сохрани.

# 2. Скачать (идемпотентно, пропускает уже скачанное; распаковывает zip):
python -m parser.pipeline download --collection math_ege_demo

# 3. Распарсить в Task (дедуп по content_hash). --ocr включает pix2tex:
python -m parser.pipeline parse --collection math_ege_demo --ocr

# 4. Тегировать (нужны YC_FOLDER_ID/YC_API_KEY в .env), батчи по 15:
python -m parser.pipeline tag --subject MATH_PROFILE --exam EGE

# всё сразу:
python -m parser.pipeline all --collection math_ege_demo

# статистика и чек критериев готовности:
python -m parser.pipeline stats --subject MATH_PROFILE --exam EGE
```

Что где:
- `parser/sources.py` — реестр источников (+ override через `parser/data/sources.json`).
- `parser/downloader.py` — httpx-загрузка с ретраями.
- `parser/fipi_parser.py` — PyMuPDF: текст, картинки, разбивка по нумерации, `content_hash`.
- `parser/latex_ocr.py` — pix2tex (ленивый импорт; без extras просто выключен).
- `parser/tagger.py` — YandexGPT Lite, батч-тегирование, `unclassified` для неуверенных.
- `core/services/llm.py` — абстракция провайдера + `parse_query` + лог в `LlmCallLog`.
- `core/services/storage.py` — картинки в S3 либо локально (`parser/data/images/`).

### Ручная верификация задач

Adminer поднимается вместе с БД: <http://localhost:8081>
(System: **PostgreSQL**, Server: `postgres`, User/DB — из `.env`).
Проверенным задачам ставь `verification_status = HUMAN_VERIFIED`.

## Критерии готовности спринта 1

- [x] `docker compose up -d` поднимает Postgres (pgvector) + Redis.
- [x] Бот отвечает на `/start`, создаёт `User` в БД (через `AuthMiddleware`).
- [x] Deep link с рефералом корректно заполняет `referred_by_id`.
- [x] В БД полное дерево тегов математики ЕГЭ после `python -m core.db.seed`.
- [x] `GET /health` отвечает `{"status": "ok"}` при поднятой БД.
- [x] Код в Git, README с инструкцией.

## Критерии готовности спринта 2

Код конвейера готов; цифры достигаются прогоном на реальных данных (требуют ссылок ФИПИ и ключей YandexGPT) — проверяются командой `parser.pipeline stats`:

- [ ] ≥1500 задач по математике ЕГЭ в `Task`.
- [ ] ≥80% задач с тегами (не `unclassified`).
- [ ] ≥500 задач со статусом `HUMAN_VERIFIED`.
- [ ] Формулы корректно рендерятся (визуальная проверка ~50 шт.).
