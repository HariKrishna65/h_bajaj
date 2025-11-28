from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from .config import settings
from .ocr import OCRLine


NUMERIC_RE = re.compile(r"[-+]?\d+(?:[,]\d{3})*(?:[.]\d+)?")
TOTAL_KEYWORDS = ("total", "amount", "balance", "due", "subtotal", "grand")
def _token_is_numeric(token: str) -> bool:
    token = token.strip(",:;")
    return bool(token) and bool(NUMERIC_RE.fullmatch(token))


def _extract_name(line_text: str) -> str:
    tokens = [tok for tok in line_text.split() if tok]
    if not tokens:
        return ""
    if tokens and _token_is_numeric(tokens[0]):
        tokens = tokens[1:]

    name_tokens: List[str] = []
    for token in tokens:
        if "/" in token and sum(ch.isdigit() for ch in token) >= 2:
            break
        name_tokens.append(token)

    if not name_tokens:
        name_tokens = tokens[:]
        while name_tokens and _token_is_numeric(name_tokens[-1]):
            name_tokens.pop()

    return " ".join(name_tokens).strip(" :-")


@dataclass(slots=True)
class BillItem:
    item_name: str
    item_amount: float
    item_rate: Optional[float]
    item_quantity: Optional[float]


@dataclass(slots=True)
class PageResult:
    page_no: int
    page_type: str
    bill_items: List[BillItem]


def _normalize_number(token: str) -> Optional[float]:
    token = token.replace(" ", "")
    if token.count(",") > 1 and "." not in token:
        token = token.replace(",", "")
    else:
        token = token.replace(",", "")
    token = token.replace("O", "0")
    try:
        return float(token)
    except ValueError:
        return None


def _is_total_line(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in TOTAL_KEYWORDS)


def _group_lines(lines: List[OCRLine]) -> List[str]:
    lines_sorted = sorted(lines, key=lambda line: line.center_y)
    groups: List[List[OCRLine]] = []
    current: List[OCRLine] = []
    last_y: Optional[float] = None

    for line in lines_sorted:
        if last_y is None or abs(line.center_y - last_y) <= settings.row_merge_threshold:
            current.append(line)
        else:
            groups.append(current)
            current = [line]
        last_y = line.center_y
    if current:
        groups.append(current)

    merged = []
    for bucket in groups:
        content = " ".join(l.text for l in sorted(bucket, key=lambda l: l.bbox[0][0]))
        merged.append(" ".join(content.split()))
    return merged


def _extract_item(
    line_text: str,
    drop_last_number: bool = False,
    qty_before_rate: bool = False,
) -> Optional[BillItem]:
    if not line_text or len(line_text.split()) <= 1:
        return None
    if _is_total_line(line_text):
        return None

    matches = NUMERIC_RE.findall(line_text)
    values: List[float] = []
    for match in matches:
        number = _normalize_number(match)
        if number is not None:
            values.append(number)

    if drop_last_number and len(values) >= 2:
        values = values[:-1]

    if not values:
        return None

    amount = values[-1]
    if amount < settings.min_item_amount:
        return None

    if qty_before_rate:
        quantity = values[-3] if len(values) >= 3 else None
        rate = values[-2] if len(values) >= 2 else None
    else:
        quantity = values[-2] if len(values) >= 2 else None
        rate = values[-3] if len(values) >= 3 else None

    if quantity is not None and quantity > settings.max_reasonable_quantity:
        quantity = None
    if quantity is None and rate:
        try:
            derived = amount / rate
        except ZeroDivisionError:
            derived = None
        if derived and 0 < derived <= settings.max_reasonable_quantity:
            quantity = round(derived, 2)

    name_part = _extract_name(line_text)
    if len(name_part) < 3:
        return None

    return BillItem(
        item_name=name_part,
        item_amount=amount,
        item_rate=rate,
        item_quantity=quantity,
    )


def infer_page_type(lines: Iterable[OCRLine]) -> str:
    joined = " ".join(line.text.lower() for line in lines)
    if "pharmacy" in joined:
        return "Pharmacy"
    if "final bill" in joined or "summary" in joined:
        return "Final Bill"
    return "Bill Detail"


def extract_page_items(lines: List[OCRLine]) -> PageResult:
    page_no = lines[0].page_no if lines else 1
    page_type = infer_page_type(lines)
    merged_rows = _group_lines(lines)
    bill_items: List[BillItem] = []

    drop_last = False
    qty_before_rate = False
    row_iter = merged_rows
    if merged_rows:
        header = merged_rows[0].lower()
        if "gross" in header and "discount" in header:
            drop_last = True
            row_iter = merged_rows[1:]
        if "qty" in header and "rate" in header:
            qty_before_rate = header.index("qty") < header.index("rate")

    for row in row_iter:
        item = _extract_item(
            row,
            drop_last_number=drop_last,
            qty_before_rate=qty_before_rate,
        )
        if item:
            bill_items.append(item)
    return PageResult(page_no=page_no, page_type=page_type, bill_items=bill_items)

