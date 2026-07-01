"""
Tag video từ CSV + rules trong video_tagging_config.xlsx (file quản lý chung).

Output columns (thêm vào video gốc):
  - brand_scope: No Brand | Single-brand | Multi-brand
  - brand_detail: Obagi; CeraVe | ... | No Brand
  - skin_concern: multi-label, '; '
  - product_type: multi-label, '; '
  - partnership_flag: True hoặc trống
  - content_type: single label — keyword khớp sớm nhất (hashtag trước, rồi description)
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "video_tagging_config.xlsx"
VIDEO_FILE = BASE / "video__analytics_202605201029  - remove dup.csv"
OUTPUT_CSV = BASE / "videos_tagged.csv"

SEP = "; "


def load_config(path: Path) -> dict[str, pd.DataFrame]:
    return {s: pd.read_excel(path, sheet_name=s) for s in pd.ExcelFile(path).sheet_names}


def _search_text(df: pd.DataFrame, source: str) -> pd.Series:
    hashtags = df["hashtags"].fillna("").str.lower()
    desc = df["description"].fillna("").str.lower()
    if source == "hashtags":
        return hashtags
    if source == "description":
        return desc
    return hashtags + " " + desc


def _text_match(text: pd.Series, pattern: str) -> pd.Series:
    if not pattern or not str(pattern).strip():
        return pd.Series(False, index=text.index)
    return text.str.contains(str(pattern), regex=True, na=False)


def tag_brand_fields(df: pd.DataFrame, brand_cfg: pd.DataFrame) -> pd.DataFrame:
    text = _search_text(df, "both")
    flags: dict[str, pd.Series] = {}
    displays: dict[str, str] = {}

    for _, row in brand_cfg.iterrows():
        key = row["brand_key"]
        display = row["brand_display"]
        pat = row["keyword_pattern"]
        flags[key] = _text_match(text, pat)
        displays[key] = display

    brand_keys = list(flags.keys())
    count = sum(flags[k].astype(int) for k in brand_keys)
    scope = pd.Series(
        np.select(
            [count == 0, count == 1, count >= 2],
            ["No Brand", "Single-brand", "Multi-brand"],
            default="No Brand",
        ),
        index=df.index,
    )

    def _detail_row(i: int) -> str:
        hits = [displays[k] for k in brand_keys if flags[k].iloc[i]]
        return SEP.join(hits) if hits else "No Brand"

    detail = pd.Series((_detail_row(i) for i in range(len(df))), index=df.index)

    out = df.copy()
    out["brand_scope"] = scope
    out["brand_detail"] = detail
    return out


def tag_multi_labels(df: pd.DataFrame, rules: pd.DataFrame) -> pd.Series:
    """Gom multi-label thành chuỗi '; '."""
    hits: list[list[str]] = [[] for _ in range(len(df))]
    for _, row in rules.iterrows():
        label = row["label"]
        source = str(row.get("source", "both")).lower()
        pat = row["keyword_pattern"]
        mask = _text_match(_search_text(df, source), pat).to_numpy()
        for pos, hit in enumerate(mask):
            if hit:
                hits[pos].append(label)
    return pd.Series((SEP.join(x) if x else "" for x in hits), index=df.index)


def apply_skin_concern_fallback(
    df: pd.DataFrame, skin_concern: pd.Series, fallback_cfg: pd.DataFrame
) -> pd.Series:
    """Nếu skin_concern trống mà có từ skincare chung -> gán label fallback (Skincare)."""
    if fallback_cfg is None or len(fallback_cfg) == 0:
        return skin_concern
    row = fallback_cfg.iloc[0]
    label = row["label"]
    source = str(row.get("source", "both")).lower()
    pattern = row["keyword_pattern"]
    empty = skin_concern.fillna("").eq("")
    generic = _text_match(_search_text(df, source), pattern)
    return skin_concern.where(~(empty & generic), label)


def _first_match_offset(text: str, pattern: str) -> int | None:
    if not text or not pattern or not str(pattern).strip():
        return None
    m = re.search(str(pattern), text, flags=re.IGNORECASE)
    return m.start() if m else None


def _content_type_search_offsets(hashtag: str, description: str, source: str, pattern: str) -> list[int]:
    """Vị trí khớp: hashtag trước, description sau (offset = len(hashtag)+1)."""
    offsets: list[int] = []
    src = source.lower()
    if src in ("hashtags", "both"):
        pos = _first_match_offset(hashtag, pattern)
        if pos is not None:
            offsets.append(pos)
    if src in ("description", "both"):
        pos = _first_match_offset(description, pattern)
        if pos is not None:
            base = len(hashtag) + 1 if src == "both" else 0
            offsets.append(base + pos)
    return offsets


def tag_content_type(df: pd.DataFrame, rules: pd.DataFrame) -> pd.Series:
    """
    Single label: chọn label có keyword xuất hiện sớm nhất.
    Thứ tự văn bản: hashtags -> description. Hòa vị trí: priority nhỏ hơn thắng.
    """
    rule_list = [
        (
            int(row["priority"]) if "priority" in rules.columns and pd.notna(row.get("priority")) else 99,
            row["label"],
            str(row.get("source", "both")).lower(),
            row["keyword_pattern"],
        )
        for _, row in rules.iterrows()
    ]

    hashtags = df["hashtags"].fillna("").str.lower().tolist()
    descriptions = df["description"].fillna("").str.lower().tolist()
    results: list[str] = []

    for h, d in zip(hashtags, descriptions):
        best_label = ""
        best_pos: int | None = None
        best_priority = 99

        for priority, label, source, pattern in rule_list:
            offsets = _content_type_search_offsets(h, d, source, pattern)
            if not offsets:
                continue
            pos = min(offsets)
            if best_pos is None or pos < best_pos or (pos == best_pos and priority < best_priority):
                best_pos = pos
                best_label = label
                best_priority = priority

        results.append(best_label)

    return pd.Series(results, index=df.index)


def tag_partnership(df: pd.DataFrame, rules: pd.DataFrame) -> pd.Series:
    out = pd.Series("", index=df.index, dtype="object")
    for _, row in rules.iterrows():
        source = str(row.get("source", "both")).lower()
        pat = row["keyword_pattern"]
        mask = _text_match(_search_text(df, source), pat)
        out = out.where(~mask, row["label"])
    return out


def main() -> None:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Chua co {CONFIG_PATH.name}. Chay: python build_video_tagging_config.py"
        )

    cfg = load_config(CONFIG_PATH)
    print(f"[INFO] Reading video: {VIDEO_FILE.name}")
    df = pd.read_csv(VIDEO_FILE)

    df = tag_brand_fields(df, cfg["brand_keywords"])
    skin = tag_multi_labels(df, cfg["skin_concern"])
    fallback_sheet = cfg["skin_concern_fallback"] if "skin_concern_fallback" in cfg else None
    df["skin_concern"] = apply_skin_concern_fallback(df, skin, fallback_sheet)
    df["product_type"] = tag_multi_labels(df, cfg["product_type"])
    df["partnership_flag"] = tag_partnership(df, cfg["partnership_flag"])
    df["content_type"] = tag_content_type(df, cfg["content_type"])

    tag_cols = [
        "brand_scope",
        "brand_detail",
        "skin_concern",
        "product_type",
        "partnership_flag",
        "content_type",
    ]
    base_cols = [c for c in df.columns if c not in tag_cols]
    df = df[base_cols + tag_cols]

    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[OK] Tagged {len(df)} videos -> {OUTPUT_CSV}")
    print("\n--- brand_scope ---")
    print(df["brand_scope"].value_counts().to_string())
    print("\n--- brand_detail (top) ---")
    print(df["brand_detail"].value_counts().head(8).to_string())
    print("\n--- partnership_flag ---")
    print(df["partnership_flag"].replace("", "(blank)").value_counts().head(5).to_string())
    print("\n--- content_type ---")
    print(df["content_type"].replace("", "(blank)").value_counts().to_string())
    print("\n--- skin_concern (top) ---")
    print(df["skin_concern"].replace("", "(blank)").value_counts().head(10).to_string())


if __name__ == "__main__":
    main()
