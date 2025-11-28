from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, HttpUrl


class ExtractRequest(BaseModel):
    document: HttpUrl


class BillItemSchema(BaseModel):
    item_name: str
    item_amount: float
    item_rate: Optional[float] = None
    item_quantity: Optional[float] = None


class PageLineItemsSchema(BaseModel):
    page_no: str
    page_type: str
    bill_items: List[BillItemSchema]


class DataSchema(BaseModel):
    pagewise_line_items: List[PageLineItemsSchema]
    total_item_count: int
    reconciled_amount: float


class TokenUsageSchema(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ExtractResponse(BaseModel):
    is_success: bool
    token_usage: TokenUsageSchema
    data: DataSchema

