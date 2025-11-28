from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the extraction service."""

    download_timeout: int = 60  # seconds
    request_timeout: int = 120  # seconds
    max_document_size_mb: int = 25
    render_dpi: int = 220
    ocr_language: str = "en"
    min_item_amount: float = 1.0
    row_merge_threshold: float = 14.0
    max_reasonable_quantity: float = 1000.0


settings = Settings()

