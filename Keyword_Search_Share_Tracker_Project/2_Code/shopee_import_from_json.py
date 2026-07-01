"""
Import dữ liệu Shopee Search (toàn sàn) từ file JSON all-in-one vào PostgreSQL.
Table: search_keyword_shopee

Cách dùng:
    python shopee_import_from_json.py
    python shopee_import_from_json.py --file shopee_search_all_keywords_2026-03-10.json
"""

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import asyncpg

# ── Cấu hình ──────────────────────────────────────────────────
# Load from environment variables — never commit credentials to version control.
# Set these in a .env file or your shell environment before running.
DB_CONFIG = {
    "user": os.getenv("DB_USER", "your_user"),
    "password": os.getenv("DB_PASSWORD", "your_password"),
    "database": os.getenv("DB_NAME", "your_database"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
}

TABLE_NAME = "search_keyword_shopee"
BATCH_SIZE = 50

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
    created_at       DATE NOT NULL,
    key_word         TEXT NOT NULL,
    product_base_id  TEXT NOT NULL,
    product_name     TEXT,
    url              TEXT,
    brand            TEXT,
    url_thumbnail    TEXT,
    UNIQUE (created_at, key_word, product_base_id)
)
"""

INSERT_SQL = f"""
INSERT INTO {TABLE_NAME}
    (created_at, key_word, product_base_id, product_name, url, brand, url_thumbnail)
VALUES ($1, $2, $3, $4, $5, $6, $7)
ON CONFLICT (created_at, key_word, product_base_id) DO NOTHING
"""


def normalize_keyword(keyword: str) -> str:
    """Chuẩn hóa keyword: viết hoa chữ đầu, còn lại viết thường."""
    compact = " ".join((keyword or "").split())
    if not compact:
        return ""
    return compact[0].upper() + compact[1:].lower()


def parse_items(keyword: str, data: dict, date_now) -> list[tuple]:
    items = data.get("items") or []
    rows = []
    seen = set()

    for item in items:
        basic = item.get("item_basic") or {}
        itemid = basic.get("itemid")
        shopid = basic.get("shopid")
        if not itemid or not shopid:
            continue

        product_base_id = f"1__{itemid}__{shopid}"
        if product_base_id in seen:
            continue
        seen.add(product_base_id)

        rows.append((
            date_now,
            keyword,
            product_base_id,
            basic.get("name", ""),
            f"https://shopee.vn/product/{shopid}/{itemid}",
            basic.get("brand", ""),
            basic.get("image", ""),
        ))

    return rows


async def import_all(json_path: Path) -> None:
    print(f"[INFO] Doc file: {json_path.name}")
    with open(json_path, encoding="utf-8") as f:
        all_data: dict = json.load(f)

    date_now = datetime.now().date()
    total_rows = 0
    skipped = []

    pool = await asyncpg.create_pool(**DB_CONFIG, min_size=2, max_size=10)
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
    print(f"[INFO] Bang {TABLE_NAME} san sang.")

    keywords = list(all_data.keys())
    print(f"[INFO] Tong {len(keywords)} keywords trong file.\n")

    for i, keyword in enumerate(keywords, 1):
        normalized_keyword = normalize_keyword(keyword)
        rows = parse_items(normalized_keyword, all_data[keyword], date_now)

        if not rows:
            print(f"  [{i}/{len(keywords)}] x '{normalized_keyword}' - khong co items")
            skipped.append(normalized_keyword)
            continue

        batches = [rows[j:j + BATCH_SIZE] for j in range(0, len(rows), BATCH_SIZE)]
        async with pool.acquire() as conn:
            for batch in batches:
                await conn.executemany(INSERT_SQL, batch)

        total_rows += len(rows)
        print(f"  [{i}/{len(keywords)}] OK '{normalized_keyword}' - {len(rows)} san pham")

    await pool.close()

    print(f"\n{'=' * 50}")
    print(f"  XONG: {total_rows} ban ghi da import vao {TABLE_NAME}")
    if skipped:
        print(f"  Bo qua ({len(skipped)} keywords trong): {skipped}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", default=None, help="Duong dan file JSON")
    args = parser.parse_args()

    base_dir = Path(__file__).parent

    if args.file:
        json_path = Path(args.file)
    else:
        candidates = sorted(
            base_dir.glob("shopee_search_all_keywords_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            print("[ERROR] Khong tim thay file shopee_search_all_keywords_*.json")
            sys.exit(1)
        json_path = candidates[0]

    if not json_path.exists():
        print(f"[ERROR] File khong ton tai: {json_path}")
        sys.exit(1)

    asyncio.run(import_all(json_path))
