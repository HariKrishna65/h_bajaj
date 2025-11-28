from __future__ import annotations

import asyncio
import mimetypes
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import ParseResult, unquote, urlparse

import httpx
from loguru import logger

from .config import settings


class DownloadError(Exception):
    """Raised when document download fails."""


async def _write_temp_file(content: bytes, suffix: Optional[str]) -> Path:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        _write_binary_file,
        content,
        suffix,
    )


def _write_binary_file(content: bytes, suffix: Optional[str]) -> Path:
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


async def download_document(url: str) -> Path:
    """Download the remote document and persist it locally."""
    local_candidate = Path(url).expanduser()
    if local_candidate.exists():
        return await _copy_local_file(local_candidate)

    parsed = urlparse(url)
    if parsed.scheme == "file":
        return await _handle_file_uri(parsed)

    headers = {"User-Agent": "BFHL-BillExtractor/1.0"}
    timeout = httpx.Timeout(settings.request_timeout)

    async with httpx.AsyncClient(timeout=timeout, headers=headers) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            logger.exception("Failed to download %s", url)
            raise DownloadError(str(exc)) from exc

    content_length = resp.headers.get("Content-Length")
    if content_length:
        size_mb = int(content_length) / (1024 * 1024)
        if size_mb > settings.max_document_size_mb:
            raise DownloadError(
                f"Document too large: {size_mb:.1f} MB "
                f"(limit {settings.max_document_size_mb} MB)"
            )

    content_type = resp.headers.get("Content-Type")
    suffix = mimetypes.guess_extension(content_type or "")
    return await _write_temp_file(resp.content, suffix)


async def _copy_local_file(local_path: Path) -> Path:
    if not local_path.exists():
        raise DownloadError(f"Local file not found: {local_path}")
    content = await asyncio.to_thread(local_path.read_bytes)
    suffix = local_path.suffix or None
    return await _write_temp_file(content, suffix)


async def _handle_file_uri(parsed_url: ParseResult) -> Path:
    path_str = unquote(parsed_url.path)
    if parsed_url.netloc:
        path_str = f"//{parsed_url.netloc}{path_str}"
    if path_str.startswith("/") and len(path_str) >= 3 and path_str[2] == ":":
        path_str = path_str.lstrip("/")
    local_path = Path(path_str).expanduser()
    return await _copy_local_file(local_path)

