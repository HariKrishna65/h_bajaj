from __future__ import annotations

from fastapi import FastAPI, HTTPException

from .schemas import (
    DataSchema,
    ExtractRequest,
    ExtractResponse,
    TokenUsageSchema,
)
from .service import extract_bill


app = FastAPI(
    title="BFHL Bill Extraction API",
    version="0.1.0",
    description="Extracts line items and totals from medical bills.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/extract-bill-data", response_model=ExtractResponse)
async def extract_bill_data(payload: ExtractRequest) -> ExtractResponse:
    try:
        data = await extract_bill(str(payload.document))
    except Exception as exc:  # pragma: no cover - surfaced to clients
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ExtractResponse(
        is_success=True,
        token_usage=TokenUsageSchema(),
        data=DataSchema(**data),
    )

