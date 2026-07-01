"""
Tag creator từ channels CSV + aggregate video.
Đọc rules từ creator_tagging_config.xlsx (chỉnh keyword tại Excel).
"""
from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
CONFIG_PATH = BASE / "creator_tagging_config.xlsx"

# Ưu tiên file full parse từ social__raw mới nhất; fallback channel cũ
_full_candidates = sorted(BASE.glob("channels_full_*.csv"))
CHANNEL_FILE_LEGACY = BASE / "channels_202605201038.csv"
CHANNEL_FILE = _full_candidates[-1] if _full_candidates else CHANNEL_FILE_LEGACY
VIDEO_FILE = BASE / "video__analytics_202605201029  - remove dup.csv"
OUTPUT_CSV = BASE / "creators_tagged.csv"

REFERENCE_DATE = pd.Timestamp("2026-05-26")  # tagged_at


def _compile(pattern: str) -> re.Pattern[str] | None:
    if not pattern or not str(pattern).strip():
        return None
    return re.compile(str(pattern), re.IGNORECASE)


def _text_match(series: pd.Series, pattern: str | None) -> pd.Series:
    if not pattern:
        return pd.Series(False, index=series.index)
    return series.fillna("").str.contains(pattern, regex=True, na=False)


def load_config(path: Path) -> dict[str, pd.DataFrame]:
    return {sheet: pd.read_excel(path, sheet_name=sheet) for sheet in pd.ExcelFile(path).sheet_names}


def build_creator_base(channels: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    """Một dòng / channel_id; profile từ channels nếu có."""
    ch_ids = videos.groupby("channel_id").agg(
        channel_name_video=("channel_name", "first"),
        video_count_in_dataset=("video_id", "count"),
        last_video_at=("platform_created_at", "max"),
        hashtags_agg=("hashtags", lambda s: " ".join(s.fillna("").astype(str))),
    ).reset_index()

    profile = channels.drop_duplicates("channel_id").copy()
    # Đổi tên video_count của channel profile để không đè video_count_in_dataset
    if "video_count" in profile.columns:
        profile = profile.rename(columns={"video_count": "channel_total_video"})

    out = ch_ids.merge(profile, on="channel_id", how="left")
    out["channel_name"] = out["channel_name"].fillna(out["channel_name_video"])
    return out.drop(columns=["channel_name_video"], errors="ignore")

def tag_key_type(df: pd.DataFrame, cfg: pd.DataFrame) -> pd.Series:
    """Single label: rule priority nhỏ nhất khớp trước."""
    rules = cfg[cfg["label"] != "Unknown"].sort_values("priority")
    name = df["channel_name"].fillna("").str.lower()
    desc = df["description"].fillna("").str.lower()
    tags = df["hashtags_agg"].fillna("").str.lower()
    profile = name + " " + desc
    result = pd.Series("Unknown", index=df.index)
    unmatched = pd.Series(True, index=df.index)

    for _, row in rules.iterrows():
        pat = row["keyword_pattern"]
        source = str(row.get("source", "both")).lower()
        label = row["label"]
        if source == "description":
            mask = _text_match(desc, pat)
        elif source == "channel_name":
            mask = _text_match(name, pat)
        elif source == "hashtags_agg":
            mask = _text_match(tags, pat)
        elif source == "profile":
            # channel_name + description (giống tag_doctor_channels.py)
            mask = _text_match(profile, pat)
        elif source == "profile_both":
            mask = _text_match(profile, pat) | _text_match(tags, pat)
        else:
            # both: description + hashtag video (không gồm channel_name)
            mask = _text_match(desc, pat) | _text_match(tags, pat)
        apply = mask & unmatched
        result.loc[apply] = label
        unmatched = unmatched & ~apply
    return result


def tag_tier(followers: pd.Series, cfg: pd.DataFrame) -> pd.Series:
    f = pd.to_numeric(followers, errors="coerce")
    result = pd.Series("Unknown", index=f.index)
    known = f.notna()
    f_known = f[known].astype(int)
    for _, row in cfg.sort_values("min_followers").iterrows():
        lo = int(row["min_followers"])
        hi = row["max_followers"]
        if pd.isna(hi):
            mask = known & (f >= lo)
        else:
            mask = known & (f >= lo) & (f <= int(hi))
        result = result.where(~mask, row["label"])
    return result


def _video_brand_flags(videos: pd.DataFrame, brand_cfg: pd.DataFrame) -> pd.DataFrame:
    text = (
        videos["hashtags"].fillna("").str.lower()
        + " "
        + videos["description"].fillna("").str.lower()
    )
    out = videos[["video_id", "channel_id"]].copy()
    brand_cols = []
    for _, row in brand_cfg.iterrows():
        brand = row["brand"]
        pat = row["keyword_pattern"]
        col = f"brand_{brand}"
        brand_cols.append(col)
        out[col] = _text_match(text, pat)
    out["brand_count_video"] = out[brand_cols].sum(axis=1)
    out["has_brand"] = out["brand_count_video"] > 0
    return out


def tag_brand_loyalty(
    creators: pd.DataFrame, videos: pd.DataFrame, brand_cfg: pd.DataFrame, loyalty_cfg: pd.DataFrame
) -> tuple[pd.Series, pd.Series, pd.Series]:
    vf = _video_brand_flags(videos, brand_cfg)
    brand_cols = [f"brand_{b}" for b in brand_cfg["brand"].tolist()]
    ch_brand = vf.groupby("channel_id")[brand_cols].sum()

    if "brand_display" in brand_cfg.columns:
        display_map = dict(zip(brand_cfg["brand"], brand_cfg["brand_display"]))
    else:
        display_map = {b: b for b in brand_cfg["brand"]}

    brand_count_s = (ch_brand[brand_cols] > 0).sum(axis=1).astype(int)

    def _detail(channel_id: str) -> str:
        if channel_id not in ch_brand.index:
            return "No-Brand"
        row = ch_brand.loc[channel_id]
        ranked: list[tuple[int, str]] = []
        for col in brand_cols:
            cnt = int(row[col])
            if cnt > 0:
                key = col.replace("brand_", "", 1)
                ranked.append((cnt, display_map.get(key, key)))
        if not ranked:
            return "No-Brand"
        ranked.sort(key=lambda x: (-x[0], x[1]))
        return "|".join(name for _, name in ranked)

    def _loyalty(n_brands: int) -> str:
        if n_brands == 0:
            return "No-Brand"
        if n_brands == 1:
            return "Single Brand"
        return "Multi-Brand"

    cid = creators["channel_id"]
    bc = cid.map(brand_count_s).fillna(0).astype(int)
    loyalty = bc.map(_loyalty)
    detail = cid.map(_detail)
    return loyalty, detail, bc


def tag_platform_addons(description: pd.Series, cfg: pd.DataFrame) -> pd.Series:
    rules = cfg[cfg["label"] != "only Tiktok"]
    desc = description.fillna("").str.lower()
    result = pd.Series("only Tiktok", index=desc.index)
    for _, row in rules.iterrows():
        pat = row["keyword_pattern"]
        mask = _text_match(desc, pat)
        result = result.where(~mask, row["label"])
    return result


def main() -> None:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Chạy build_tagging_config.py trước: {CONFIG_PATH}")

    cfg = load_config(CONFIG_PATH)
    channels = pd.read_csv(CHANNEL_FILE)
    videos = pd.read_csv(VIDEO_FILE)

    creators = build_creator_base(channels, videos)

    creators["key_type"] = tag_key_type(creators, cfg["key_type"])
    creators["tier"] = tag_tier(creators["followers"], cfg["tier"])
    loyalty, brand_detail, brand_n = tag_brand_loyalty(
        creators, videos, cfg["brand_keywords"], cfg["brand_loyalty"]
    )
    creators["brand_loyalty"] = loyalty.values
    creators["brand_detail"] = brand_detail.values
    creators["brand_count"] = brand_n.values
    creators["platform_addons"] = tag_platform_addons(creators["description"], cfg["platform_addons"])
    creators["tagged_at"] = REFERENCE_DATE.isoformat()

    base_cols = [
        "channel_id",
        "channel_name",
        "followers",
        "likes",
        "followings",
        "description",
        "video_count_in_dataset",
        "channel_total_video",
        "last_video_at",
    ]
    extra_profile_cols = [
        c for c in [
            "verified",
            "is_organization",
            "tt_seller",
            "private_account",
            "language",
            "bio_link",
            "create_time_iso",
        ] if c in creators.columns
    ]
    tag_cols = [
        "key_type",
        "tier",
        "brand_loyalty",
        "brand_detail",
        "brand_count",
        "platform_addons",
        "tagged_at",
    ]
    out_cols = [c for c in base_cols if c in creators.columns] + extra_profile_cols + tag_cols
    creators[out_cols].to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"Tagged {len(creators)} creators -> {OUTPUT_CSV}")
    print("\n--- key_type ---")
    print(creators["key_type"].value_counts().to_string())
    print("\n--- tier ---")
    print(creators["tier"].value_counts().to_string())
    print("\n--- brand_loyalty ---")
    print(creators["brand_loyalty"].value_counts().to_string())
    print("\n--- platform_addons ---")
    print(creators["platform_addons"].value_counts().to_string())


if __name__ == "__main__":
    main()
