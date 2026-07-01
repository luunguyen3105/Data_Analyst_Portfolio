"""Rule-based tagging engine (FR-1, FR-2, FR-3, QC-2).

Simplified reference implementation that runs on synthetic data only. Classifies each SKU
into one product category and a target-audience (gender) label from its product name, using
an ordered keyword dictionary so that the logic stays decoupled from the data (NFR-3).
"""
from pathlib import Path

import pandas as pd

# Accessory / gift listings can contain a real product keyword (e.g. a free toothpaste
# bundled with a shower gel) without being that product. Checked first so they do not get
# miscategorized by the bundled item's name (QC-2).
GIFT_KEYWORDS = ["tang kem", "qua tang", "freegift", "free gift"]

# Ordered by priority: the first matching category wins (FR-3). Combo sits above single
# shampoo/conditioner so a "shampoo + conditioner" listing is not tagged as plain shampoo.
CATEGORY_RULES = [
    ("Combo (Shampoo and hair conditioner)", ["dau goi va dau xa", "combo dau goi"]),
    ("Shampoo", ["dau goi"]),
    ("Hair conditioner", ["dau xa"]),
    ("Hair styling for men", ["sap vuot toc", "tao kieu"]),
    ("Facewash", ["rua mat"]),
    ("Deodorant", ["khu mui", "lan khu mui"]),
    ("Bodymist", ["body mist"]),
    ("Perfume", ["nuoc hoa"]),
    ("Shower gel", ["sua tam"]),
]

GENDER_RULES = [
    ("Unisex", ["unisex", "ca gia dinh"]),
    ("Male", ["nam"]),
    ("Female", ["nu"]),
]


def classify(product_name: str) -> tuple[str, str]:
    """Return (partner_category, partner_function) for a single product name."""
    name = product_name.lower()

    if any(kw in name for kw in GIFT_KEYWORDS):
        return "Others", "Others"

    category = "Others"
    for label, keywords in CATEGORY_RULES:
        if any(kw in name for kw in keywords):
            category = label
            break

    if category == "Others":
        return category, "Others"

    gender = "Unisex"
    for label, keywords in GENDER_RULES:
        if any(kw in name for kw in keywords):
            gender = label
            break

    return category, gender


def tag_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Add partner_category and partner_function columns to a products DataFrame."""
    tagged = df["product_name"].apply(classify)
    df = df.copy()
    df["partner_category"] = tagged.apply(lambda t: t[0])
    df["partner_function"] = tagged.apply(lambda t: t[1])
    return df


if __name__ == "__main__":
    data_path = Path(__file__).resolve().parents[1] / "sample_data" / "sample_products.csv"
    df = tag_dataframe(pd.read_csv(data_path))

    print(df[["sku_id", "product_name", "partner_category", "partner_function"]].to_string(index=False))
    print("\nSKU count by category:")
    print(df["partner_category"].value_counts())
