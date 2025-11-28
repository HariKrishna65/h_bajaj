import asyncio
import json
from pathlib import Path

from app.service import extract_bill

TRAIN_DOCS = [
    f"train_sample_{i}.pdf" for i in range(1, 16)
]

OUTPUT_DIR = Path("train_outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

TOKEN_BLOCK = {"total_tokens": 0, "input_tokens": 0, "output_tokens": 0}

async def process(doc_name: str):
    path = Path(doc_name)
    if not path.exists():
        print(f"[WARN] Missing {doc_name}")
        return None
    uri = path.resolve().as_uri()
    data = await extract_bill(uri)
    response = {
        "is_success": True,
        "token_usage": TOKEN_BLOCK,
        "data": data,
    }
    out_path = OUTPUT_DIR / f"{path.stem}.json"
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(response, fh, indent=2)
    print(f"Saved {out_path}")
    return str(out_path)

async def main():
    results = []
    for doc in TRAIN_DOCS:
        result = await process(doc)
        if result:
            results.append({"document": doc, "output": result})
    index_path = OUTPUT_DIR / "index.json"
    with index_path.open("w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2)
    print(f"Index written to {index_path}")

if __name__ == "__main__":
    asyncio.run(main())
