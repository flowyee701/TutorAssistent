"""Реестр источников PDF для скачивания.

ФИПИ публикует демоверсии/спецификации на doc.fipi.ru, а «открытый банк
заданий» — это интерактивное веб-приложение (ege.fipi.ru), массовой выгрузки
PDF там нет. Поэтому источники держим в редактируемом реестре:

1. Встроенный DEFAULT_REGISTRY ниже — шаблон с шаблонными URL демоверсий.
   URL обязательно проверь вручную: ФИПИ периодически меняет пути.
2. Внешний файл parser/data/sources.json — переопределяет/дополняет встроенный
   реестр, чтобы добавлять ссылки без правки кода. Формат:

   {
     "math_ege_demo": [
       {"url": "https://doc.fipi.ru/.../ma-prof-demo-2026.pdf",
        "filename": "ma_prof_demo_2026.pdf",
        "source_label": "FIPI_2026_DEMO"}
     ]
   }
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from core.db.models import ExamType, Subject

DATA_DIR = Path(__file__).resolve().parent / "data"
RAW_DIR = DATA_DIR / "raw"
SOURCES_JSON = DATA_DIR / "sources.json"


@dataclass(slots=True)
class PdfSource:
    url: str
    filename: str
    source_label: str  # пишется в Task.source, напр. FIPI_2024_DEMO
    subject: Subject = Subject.MATH_PROFILE
    exam_type: ExamType = ExamType.EGE


# Шаблон. URL — ориентировочные, ПРОВЕРЬ перед запуском (могут отдавать 404).
DEFAULT_REGISTRY: dict[str, list[PdfSource]] = {
    "math_ege_demo": [
        PdfSource(
            url=f"https://doc.fipi.ru/ege/demoversii-specifikacii-kodifikatory/{year}/"
            f"ma-prof-{year}.pdf",
            filename=f"ma_prof_demo_{year}.pdf",
            source_label=f"FIPI_{year}_DEMO",
        )
        for year in range(2019, 2027)
    ],
}


def _registry_to_dict(reg: dict[str, list[PdfSource]]) -> dict[str, list[dict]]:
    return {
        key: [
            {
                "url": s.url,
                "filename": s.filename,
                "source_label": s.source_label,
                "subject": s.subject.value,
                "exam_type": s.exam_type.value,
            }
            for s in items
        ]
        for key, items in reg.items()
    }


def load_sources(collection: str) -> list[PdfSource]:
    """Возвращает источники коллекции, учитывая override из sources.json."""
    items: list[PdfSource] = list(DEFAULT_REGISTRY.get(collection, []))

    if SOURCES_JSON.exists():
        override = json.loads(SOURCES_JSON.read_text(encoding="utf-8"))
        if collection in override:
            # Полная замена коллекции данными из файла
            items = [
                PdfSource(
                    url=row["url"],
                    filename=row["filename"],
                    source_label=row.get("source_label", "USER_UPLOAD"),
                    subject=Subject(row.get("subject", Subject.MATH_PROFILE.value)),
                    exam_type=ExamType(row.get("exam_type", ExamType.EGE.value)),
                )
                for row in override[collection]
            ]
    return items


def collections() -> list[str]:
    keys = set(DEFAULT_REGISTRY)
    if SOURCES_JSON.exists():
        keys |= set(json.loads(SOURCES_JSON.read_text(encoding="utf-8")))
    return sorted(keys)


def write_template(path: Path = SOURCES_JSON) -> Path:
    """Создаёт sources.json-шаблон из встроенного реестра (для редактирования)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_registry_to_dict(DEFAULT_REGISTRY), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path
