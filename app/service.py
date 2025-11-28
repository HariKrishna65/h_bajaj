from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Dict, List

from loguru import logger

from .downloader import download_document
from .line_items import PageResult, extract_page_items
from .ocr import OCRLine, run_ocr
from .pdf_utils import PageImage, load_document


async def _process_page(page: PageImage) -> PageResult | None:
    lines = run_ocr(page.image, page.page_no)
    if not lines:
        return None
    return extract_page_items(lines)


async def extract_bill(document_url: str) -> Dict:
    temp_path: Path | None = None
    try:
        temp_path = await download_document(document_url)
        pages = load_document(temp_path)
        tasks = [asyncio.create_task(_process_page(page)) for page in pages]
        page_results: List[PageResult] = []
        for task in tasks:
            result = await task
            if result:
                page_results.append(result)
    finally:
        if temp_path and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                logger.warning("Could not delete temp file %s", temp_path)

    total_items = sum(len(page.bill_items) for page in page_results)
    final_total = sum(item.item_amount for page in page_results for item in page.bill_items)

    payload = {
        "pagewise_line_items": [
            {
                "page_no": str(page.page_no),
                "page_type": page.page_type,
                "bill_items": [
                    {
                        "item_name": item.item_name,
                        "item_amount": round(item.item_amount, 2),
                        "item_rate": round(item.item_rate, 2) if item.item_rate else None,
                        "item_quantity": round(item.item_quantity, 2) if item.item_quantity else None,
                    }
                    for item in page.bill_items
                ],
            }
            for page in sorted(page_results, key=lambda p: p.page_no)
        ],
        "total_item_count": total_items,
        "reconciled_amount": round(final_total, 2),
    }
    return payload

