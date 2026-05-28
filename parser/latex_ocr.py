"""Распознавание формул с картинок в LaTeX через pix2tex (бесплатно, локально).

pix2tex тянет torch — это тяжёлая зависимость, поэтому она в отдельной
группе extras `[parser]` и импортируется лениво. Если pix2tex не установлен,
обёртка не падает, а возвращает None (парсинг продолжается без OCR).

Уверенность pix2tex напрямую не отдаёт, поэтому оцениваем эвристически и
неуверенные результаты пишем в parser/data/ocr_review.log для ручной проверки.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

OCR_REVIEW_LOG = Path(__file__).resolve().parent / "data" / "ocr_review.log"
_SUSPICIOUS = ("?", "\\text{", "□", "�")


@dataclass(slots=True)
class OcrResult:
    latex: str | None
    confidence: str  # high | medium | low


def _assess(latex: str) -> str:
    s = latex.strip()
    if len(s) < 3:
        return "low"
    if any(tok in s for tok in _SUSPICIOUS):
        return "low"
    if any(c in s for c in "\\^_{}"):  # есть структура формулы — вероятно ок
        return "medium"
    return "low"


class LatexOCR:
    """Ленивая обёртка над pix2tex.cli.LatexOCR."""

    def __init__(self) -> None:
        self._model = None
        self._available: bool | None = None

    def _ensure(self) -> bool:
        if self._available is None:
            try:
                from pix2tex.cli import LatexOCR as _Pix2Tex

                self._model = _Pix2Tex()
                self._available = True
                logger.info("pix2tex загружен")
            except Exception as exc:  # noqa: BLE001
                logger.warning("pix2tex недоступен (%s) — OCR формул выключен", exc)
                self._available = False
        return self._available

    def image_to_latex(self, png: bytes) -> OcrResult:
        if not self._ensure():
            return OcrResult(latex=None, confidence="low")
        try:
            from PIL import Image

            img = Image.open(io.BytesIO(png)).convert("RGB")
            latex = (self._model(img) or "").strip()  # type: ignore[misc]
        except Exception as exc:  # noqa: BLE001
            logger.warning("OCR упал: %s", exc)
            return OcrResult(latex=None, confidence="low")

        conf = _assess(latex)
        if conf == "low" and latex:
            self._log_for_review(latex)
        return OcrResult(latex=latex or None, confidence=conf)

    @staticmethod
    def _log_for_review(latex: str) -> None:
        OCR_REVIEW_LOG.parent.mkdir(parents=True, exist_ok=True)
        with OCR_REVIEW_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"{datetime.now().isoformat()}\t{latex}\n")


_ocr: LatexOCR | None = None


def get_ocr() -> LatexOCR:
    global _ocr
    if _ocr is None:
        _ocr = LatexOCR()
    return _ocr
