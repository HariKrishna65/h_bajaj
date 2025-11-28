from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

import numpy as np
import pypdfium2 as pdfium
from PIL import Image

from .config import settings


@dataclass(slots=True)
class PageImage:
    page_no: int  # 1-indexed
    image: np.ndarray  # BGR numpy array


def _bitmap_to_bgr(bitmap: pdfium.PdfBitmap) -> np.ndarray:
    """Convert Pdfium bitmap into a BGR numpy array."""
    array = bitmap.to_numpy()
    if array.shape[2] == 4:  # drop alpha if present
        array = array[:, :, :3]
    return array


def pdf_to_images(pdf_path: Path) -> List[PageImage]:
    doc = pdfium.PdfDocument(pdf_path)
    scale = settings.render_dpi / 72.0
    images: List[PageImage] = []
    for idx in range(len(doc)):
        page = doc[idx]
        bitmap = page.render(scale=scale)
        images.append(PageImage(page_no=idx + 1, image=_bitmap_to_bgr(bitmap)))
        page.close()
        bitmap.close()
    doc.close()
    return images


def image_file_to_pages(path: Path) -> List[PageImage]:
    with Image.open(path) as img:
        rgb = img.convert("RGB")
        array = np.array(rgb)[:, :, ::-1]  # RGB->BGR
    return [PageImage(page_no=1, image=array)]


def load_document(path: Path) -> List[PageImage]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return pdf_to_images(path)
    if suffix in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
        return image_file_to_pages(path)
    raise ValueError(f"Unsupported document type: {suffix}")

