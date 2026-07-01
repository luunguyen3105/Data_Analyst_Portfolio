"""Master DB merge (DR-1, DR-2, FR-4).

Merges the previous master snapshot with the current period's data. Illustrates a recurring
real-world issue: the same SKU appears across monthly exports with inconsistent id suffixes
(e.g. "_old" / "_new" left by a prior re-tagging run), so a naive concat + dedup would
create duplicate rows for the same product.

Grain is `sku_id x partner_category` (DR-1): a combo maps to several categories and must keep
one row per category, so dedup is on the composite key, never on sku_id alone.
"""
import pandas as pd

COMPOSITE_KEY = ["sku_id", "partner_category"]


def normalize_id(raw_id: str) -> str:
    """Strip inconsistent re-tag suffixes so the same SKU reconciles across snapshots (DR-2)."""
    for suffix in ("_old", "_new"):
        if raw_id.endswith(suffix):
            return raw_id[: -len(suffix)]
    return raw_id


def merge_master_db(df_old: pd.DataFrame, df_new: pd.DataFrame) -> pd.DataFrame:
    """Merge previous (existing) and current (new) snapshots, keeping the new row on conflict.

    FR-4: existing SKUs keep their prior tags; when the same SKU x category appears in both
    snapshots the current period's row wins (refreshed revenue/units).
    """
    df_old = df_old.copy()
    df_new = df_new.copy()
    df_old["sku_id"] = df_old["sku_id"].map(normalize_id)
    df_new["sku_id"] = df_new["sku_id"].map(normalize_id)

    # Explicit priority so the current period's row wins on conflict (FR-4); relying on the
    # alphabetical order of "old"/"new" would silently keep the wrong row.
    df_old["_priority"] = 0  # existing snapshot
    df_new["_priority"] = 1  # current period — preferred

    merged = pd.concat([df_old, df_new], ignore_index=True)
    merged = merged.sort_values("_priority").drop_duplicates(subset=COMPOSITE_KEY, keep="last")
    return merged.drop(columns="_priority").reset_index(drop=True)


if __name__ == "__main__":
    df_old = pd.DataFrame(
        {
            "sku_id": ["SKU001_old", "SKU002_old", "SKU003_old"],
            "partner_category": ["Shower gel", "Facewash", "Deodorant"],
            "revenue": [850_000, 600_000, 450_000],
        }
    )
    df_new = pd.DataFrame(
        {
            "sku_id": ["SKU001_new", "SKU004"],
            "partner_category": ["Shower gel", "Shampoo"],
            "revenue": [890_000, 990_000],
        }
    )

    result = merge_master_db(df_old, df_new)
    print(result.to_string(index=False))
    print(f"\n{len(df_old) + len(df_new)} input rows -> {len(result)} unique rows after merge")
