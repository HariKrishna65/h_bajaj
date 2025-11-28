from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import List

import easyocr
import numpy as np

from .config import settings


@dataclass(slots=True)
class OCRLine:
    text: str
    bbox: List[List[float]]
    score: float
    page_no: int

    @property
    def center_y(self) -> float:
        ys = [p[1] for p in self.bbox]
        return sum(ys) / len(ys)


@lru_cache(maxsize=1)
def _get_reader() -> easyocr.Reader:
    return easyocr.Reader([settings.ocr_language], gpu=False, verbose=False)


def run_ocr(image: np.ndarray, page_no: int) -> List[OCRLine]:
    reader = _get_reader()
    results = reader.readtext(image, detail=1, paragraph=False)
    lines: List[OCRLine] = []
    for bbox, text, score in results:
        if not text or not text.strip():
            continue
        normalized_bbox = [[float(x), float(y)] for x, y in bbox]
        lines.append(
            OCRLine(
                text=text.strip(),
                bbox=normalized_bbox,
                score=float(score),
                page_no=page_no,
            )
        )
    return lines

