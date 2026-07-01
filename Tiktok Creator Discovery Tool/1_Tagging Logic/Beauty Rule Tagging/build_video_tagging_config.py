"""
Tạo / cập nhật video_tagging_config.xlsx – FILE QUẢN LÝ CHUNG cho tagging video.

Gồm:
  - readme, output_fields
  - Sheet từng brand (Obagi, La Roche-Posay, ...) – chỉnh hashtag tại đây
  - brand_hashtag (gộp từ sheet brand), brand_keywords (regex auto)
  - brand_scope, skin_concern, product_type, partnership_flag, brand_extra_pattern

Nguồn import lần đầu: tagging_video_by_hashtag.xlsx (nếu có).
Sau đó chỉ cần sửa video_tagging_config.xlsx và chạy lại script này.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "video_tagging_config.xlsx"
LEGACY_MANUAL = BASE / "tagging_video_by_hashtag.xlsx"

# Sheet brand trong file quản lý chung
BRAND_SHEETS: list[tuple[str, str, str]] = [
    ("Obagi", "obagi", "Obagi"),
    ("La Roche-Posay", "la_roche_posay", "La Roche-Posay"),
    ("Cerave", "cerave", "CeraVe"),
    ("Bioderma", "bioderma", "Bioderma"),
    ("Cocoon", "cocoon", "Cocoon"),
    ("Vichy", "vichy", "Vichy"),
    ("Eucerin", "eucerin", "Eucerin"),
    ("Cetaphil", "cetaphil", "Cetaphil"),
    ("SVR", "svr", "SVR"),
    ("Torriden", "torriden", "Torriden"),
]

# Hashtag mặc định khi sheet brand mới/chưa có dữ liệu
DEFAULT_BRAND_HASHTAGS: dict[str, list[str]] = {
    "Vichy": ["vichy", "vichyvietnam", "vichyvn", "vichypartner"],
    "Eucerin": ["eucerin", "eucerinvietnam", "eucerinvn"],
    "Cetaphil": ["cetaphil", "cetaphilvietnam", "cetaphilvn"],
    "SVR": ["svr", "svrvietnam", "svrparis", "svr_sebiaclear", "sebiaclear"],
    "Torriden": ["torriden", "torridenvn", "torridenvietnam"],
}

SKIN_CONCERN = pd.DataFrame(
    [
        {"label": "Sun Protection", "source": "both", "keyword_pattern": r"anthelios|kemchongnang|kem chong nang|uvair|uvmune|sunscreen|chongnang|\bspf\b|everydaysunscreen|suncare", "notes": ""},
        {"label": "Acne", "source": "both", "keyword_pattern": r"effaclar|acne|mun\b|muncam|munviem|sebium|dadaumun|trimun", "notes": ""},
        {"label": "Moisturizing", "source": "both", "keyword_pattern": r"cicaplast|duongam|duong am|moisturiz|phuchoida|barrier|baume|kemduong|kem duong", "notes": ""},
        {"label": "Cleansing", "source": "both", "keyword_pattern": r"suaruamat|sua rua mat|gelruamat|cleanser|ruamat|nuoctaytrang|nuoc tay trang|trangdiem|trang diem|taytrang", "notes": ""},
        {"label": "Exfoliating", "source": "both", "keyword_pattern": r"taytebaochet|tay te bao chet|bhatoner|bha\b|exfoliat|aha\b|peel\b", "notes": ""},
        {"label": "Brightening", "source": "both", "keyword_pattern": r"lamsang|lam sang|brighten|vitaminc|vitamin c|trangda|melab3|melab", "notes": ""},
        {"label": "Anti-aging", "source": "both", "keyword_pattern": r"retinol|chong lao hoa|chonglaohoa|antiaging|anti aging|collagen|elastiderm|wrinkle", "notes": ""},
    ]
)

# Chỉ áp dụng khi skin_concern trống sau bước tag chính
SKIN_CONCERN_FALLBACK = pd.DataFrame(
    [
        {
            "label": "Skincare",
            "source": "both",
            "keyword_pattern": r"\bskincare\b|skincaretips|skincareroutine|skincareproducts|skincareviral|skincare101|chamsocda|cham soc da|goclamdep|lamdep|mypham",
            "notes": "Fallback: video chỉ có hashtag/từ skincare chung, chưa khớp concern cụ thể",
        },
    ]
)

PRODUCT_TYPE = pd.DataFrame(
    [
        {"label": "Sunscreen", "source": "both", "keyword_pattern": r"kemchongnang|kem chong nang|sunscreen|\bspf\b|anthelios|uvmune|uvair", "notes": ""},
        {"label": "Cleanser", "source": "both", "keyword_pattern": r"suaruamat|sua rua mat|gelruamat|gel rua mat|cleanser|rua mat|suaruamatcerave", "notes": ""},
        {"label": "Serum", "source": "both", "keyword_pattern": r"\bserum\b|tinhchat|tinh chat|serumobagi|sebiumserum", "notes": ""},
        {"label": "Moisturizer", "source": "both", "keyword_pattern": r"kemduong|kem duong|moisturiz|cicaplast|duongam|baume", "notes": ""},
        {"label": "Toner", "source": "both", "keyword_pattern": r"\btoner\b|nuochoahong|nuoc hoa hong|essence|bhatoner", "notes": ""},
        {"label": "Eye Cream", "source": "both", "keyword_pattern": r"kemmat|kem mat|eye cream|eyecream", "notes": ""},
        {"label": "Micellar", "source": "both", "keyword_pattern": r"micellar|micelar|nuoctaytrang|nuoc tay trang|taytrang", "notes": ""},
    ]
)

PARTNERSHIP_FLAG = pd.DataFrame(
    [
        {
            "label": "True",
            "source": "both",
            "keyword_pattern": r"#ad\b|\bad\b|hợptáccùng|hop_tac_cung|hoptaccung|partner|collab|narocnik|tài trợ|tai tro|sponsored|taitro",
            "notes": "Khớp -> partnership_flag = True; không khớp -> để trống",
        },
    ]
)

CONTENT_TYPE = pd.DataFrame(
    [
        {
            "label": "Sponsored/Partnership",
            "priority": 1,
            "source": "both",
            "keyword_pattern": r"#ad\b|\bad\b|hợptáccùng|hop_tac_cung|hoptaccung|partner|collab|narocnik|tài trợ|tai tro|sponsored|taitro|hợp tác|hop tac",
            "notes": "Single label: keyword khớp sớm nhất (hashtag trước description). Hòa: priority nhỏ thắng.",
        },
        {
            "label": "Review",
            "priority": 2,
            "source": "both",
            "keyword_pattern": r"\breview\b|riview|đánh giá|danh gia|reviewlamdep|reviewskincare|honestreview|thật tình|that tinh|có nên mua|co nen mua",
            "notes": "",
        },
        {
            "label": "Tutorial",
            "priority": 3,
            "source": "both",
            "keyword_pattern": r"tutorial|howto|how to|cách dùng|cach dung|hướng dẫn|huong dan|skincareroutine|routine\b|skincaretips|tip skincare|step\b",
            "notes": "",
        },
        {
            "label": "Unboxing",
            "priority": 4,
            "source": "both",
            "keyword_pattern": r"unbox|unboxing|mở hộp|mo hop|nhận được|nhan duoc|haul\b|opening\b",
            "notes": "",
        },
    ]
)

BRAND_SCOPE = pd.DataFrame(
    [
        {"label": "No Brand", "min_brand_count": 0, "max_brand_count": 0, "notes": "Không mention brand nào trong danh sách brand"},
        {"label": "Single-brand", "min_brand_count": 1, "max_brand_count": 1, "notes": "Đúng 1 brand"},
        {"label": "Multi-brand", "min_brand_count": 2, "max_brand_count": None, "notes": ">= 2 brand"},
    ]
)

BRAND_EXTRA_PATTERN = pd.DataFrame(
    [
        {"brand_key": "la_roche_posay", "keyword_pattern": r"lrpvn|\blrp\b|uvair|toleriane|uvmune|hyalu|melab3|melab", "notes": "Bổ sung ngoài hashtag list"},
        {"brand_key": "cerave", "keyword_pattern": r"ceraveskincare", "notes": ""},
        {"brand_key": "obagi", "keyword_pattern": r"nugen|khoahocobagi", "notes": ""},
        {"brand_key": "bioderma", "keyword_pattern": r"sensibio|sebium", "notes": ""},
        {"brand_key": "cocoon", "keyword_pattern": r"nuoctaytrangbidao|taytebaochet", "notes": ""},
        {"brand_key": "vichy", "keyword_pattern": r"vichyvn|vichypartner|meandmycollagen", "notes": ""},
        {"brand_key": "eucerin", "keyword_pattern": r"eucerinvn|eucerinvietnam", "notes": ""},
        {"brand_key": "cetaphil", "keyword_pattern": r"cetaphilvn|cetaphilvietnam", "notes": ""},
        {"brand_key": "svr", "keyword_pattern": r"svrparis|svrvietnam|sebiaclear", "notes": ""},
        {"brand_key": "torriden", "keyword_pattern": r"torridenvn|torridenvietnam", "notes": ""},
    ]
)

README = pd.DataFrame(
    [
        {"muc": "File này", "noi_dung": "video_tagging_config.xlsx – quản lý TẤT CẢ rule tagging video"},
        {"muc": "Sửa hashtag brand", "noi_dung": "Sheet brand (10 brand) -> chạy lại build_video_tagging_config.py"},
        {"muc": "Chạy tag", "noi_dung": "python tag_video.py -> videos_tagged.csv"},
        {"muc": "File cũ", "noi_dung": "tagging_video_by_hashtag.xlsx đã gộp vào đây; có thể giữ làm backup"},
    ]
)

OUTPUT_FIELDS = pd.DataFrame(
    [
        {"column": "brand_scope", "type": "single", "values": "No Brand | Single-brand | Multi-brand", "config_sheet": "brand_scope"},
        {"column": "brand_detail", "type": "text", "values": "Tên brand; nhiều brand cách '; '. Không có -> No Brand", "config_sheet": "brand_keywords"},
        {
            "column": "skin_concern",
            "type": "multi",
            "values": "Sun Protection; Acne; ... hoặc fallback Skincare (sheet skin_concern_fallback)",
            "config_sheet": "skin_concern + skin_concern_fallback",
        },
        {"column": "product_type", "type": "multi", "values": "Sunscreen; Cleanser; ... (phân cách '; ')", "config_sheet": "product_type"},
        {"column": "partnership_flag", "type": "single", "values": "True hoặc trống", "config_sheet": "partnership_flag"},
        {
            "column": "content_type",
            "type": "single",
            "values": "Sponsored/Partnership | Review | Tutorial | Unboxing | trống",
            "config_sheet": "content_type",
        },
    ]
)


def _escape_hashtag(tag: str) -> str:
    return re.escape(str(tag).strip().lower())


def _read_hashtag_column(path: Path, sheet: str) -> list[str]:
    df = pd.read_excel(path, sheet_name=sheet)
    col = "hashtag" if "hashtag" in df.columns else df.columns[0]
    return [str(t).strip().lower() for t in df[col].dropna() if str(t).strip()]


def load_brand_sheets_from_legacy() -> dict[str, pd.DataFrame]:
    """Đọc sheet brand từ file thủ công cũ."""
    out: dict[str, pd.DataFrame] = {}
    if not LEGACY_MANUAL.exists():
        return out
    xl = pd.ExcelFile(LEGACY_MANUAL)
    for sheet_name, _, _ in BRAND_SHEETS:
        if sheet_name not in xl.sheet_names:
            continue
        tags = _read_hashtag_column(LEGACY_MANUAL, sheet_name)
        out[sheet_name] = pd.DataFrame({"hashtag": tags})
    return out


def load_brand_sheets_from_master() -> dict[str, pd.DataFrame]:
    """Đọc sheet brand từ file quản lý chung (ưu tiên khi rebuild)."""
    out: dict[str, pd.DataFrame] = {}
    if not OUTPUT.exists():
        return out
    xl = pd.ExcelFile(OUTPUT)
    for sheet_name, _, _ in BRAND_SHEETS:
        if sheet_name not in xl.sheet_names:
            continue
        tags = _read_hashtag_column(OUTPUT, sheet_name)
        if tags:
            out[sheet_name] = pd.DataFrame({"hashtag": tags})
    return out


def resolve_brand_sheets() -> dict[str, pd.DataFrame]:
    """Ưu tiên master, fallback legacy manual."""
    master = load_brand_sheets_from_master()
    legacy = load_brand_sheets_from_legacy()
    resolved: dict[str, pd.DataFrame] = {}
    for sheet_name, _, _ in BRAND_SHEETS:
        if sheet_name in master:
            resolved[sheet_name] = master[sheet_name]
        elif sheet_name in legacy:
            resolved[sheet_name] = legacy[sheet_name]
        else:
            tags = DEFAULT_BRAND_HASHTAGS.get(sheet_name, [])
            resolved[sheet_name] = pd.DataFrame({"hashtag": tags})
    return resolved


def brand_sheets_to_long(brand_sheets: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows: list[dict] = []
    for sheet_name, brand_key, brand_display in BRAND_SHEETS:
        df = brand_sheets.get(sheet_name, pd.DataFrame({"hashtag": []}))
        for tag in df["hashtag"].dropna().astype(str):
            tag = tag.strip().lower()
            if tag:
                rows.append(
                    {
                        "brand_key": brand_key,
                        "brand_display": brand_display,
                        "hashtag": tag,
                        "source_sheet": sheet_name,
                    }
                )
    if not rows:
        raise ValueError("Không có hashtag brand nào. Kiểm tra sheet brand hoặc tagging_video_by_hashtag.xlsx")
    return pd.DataFrame(rows).drop_duplicates(["brand_key", "hashtag"])


def build_brand_keywords(
    hashtags_df: pd.DataFrame, extra_df: pd.DataFrame
) -> pd.DataFrame:
    extra_map = extra_df.set_index("brand_key")["keyword_pattern"].to_dict() if len(extra_df) else {}
    records = []
    for brand_key, grp in hashtags_df.groupby("brand_key"):
        display = grp["brand_display"].iloc[0]
        parts = [_escape_hashtag(h) for h in grp["hashtag"]]
        extra = extra_map.get(brand_key, "")
        if extra and str(extra).strip():
            parts.append(str(extra))
        records.append(
            {
                "brand_key": brand_key,
                "brand_display": display,
                "keyword_pattern": "|".join(parts),
                "hashtag_count": len(grp),
            }
        )
    return pd.DataFrame(records)


def load_existing_rules(sheet: str, default: pd.DataFrame) -> pd.DataFrame:
    """Giữ rule đã chỉnh tay trên master (nếu có), không ghi đè khi rebuild."""
    if not OUTPUT.exists():
        return default
    try:
        df = pd.read_excel(OUTPUT, sheet_name=sheet)
        return df if len(df) else default
    except ValueError:
        return default


def main() -> None:
    brand_sheets = resolve_brand_sheets()
    brand_hashtag = brand_sheets_to_long(brand_sheets)

    extra = load_existing_rules("brand_extra_pattern", BRAND_EXTRA_PATTERN)
    skin = load_existing_rules("skin_concern", SKIN_CONCERN)
    skin_fallback = load_existing_rules("skin_concern_fallback", SKIN_CONCERN_FALLBACK)
    product = load_existing_rules("product_type", PRODUCT_TYPE)
    partner = load_existing_rules("partnership_flag", PARTNERSHIP_FLAG)
    # content_type: luôn dùng bản mới (có priority) nếu sheet cũ thiếu cột priority
    content = load_existing_rules("content_type", CONTENT_TYPE)
    if "priority" not in content.columns:
        content = CONTENT_TYPE
    scope = load_existing_rules("brand_scope", BRAND_SCOPE)

    brand_keywords = build_brand_keywords(brand_hashtag, extra)

    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        README.to_excel(writer, sheet_name="readme", index=False)
        OUTPUT_FIELDS.to_excel(writer, sheet_name="output_fields", index=False)

        for sheet_name, df in brand_sheets.items():
            df.to_excel(writer, sheet_name=sheet_name, index=False)

        brand_hashtag.to_excel(writer, sheet_name="brand_hashtag", index=False)
        brand_keywords.to_excel(writer, sheet_name="brand_keywords", index=False)
        extra.to_excel(writer, sheet_name="brand_extra_pattern", index=False)
        scope.to_excel(writer, sheet_name="brand_scope", index=False)
        skin.to_excel(writer, sheet_name="skin_concern", index=False)
        skin_fallback.to_excel(writer, sheet_name="skin_concern_fallback", index=False)
        product.to_excel(writer, sheet_name="product_type", index=False)
        partner.to_excel(writer, sheet_name="partnership_flag", index=False)
        content.to_excel(writer, sheet_name="content_type", index=False)

    print(f"Wrote {OUTPUT}")
    print("Sheets:", pd.ExcelFile(OUTPUT).sheet_names)
    print(f"  brand_hashtag: {len(brand_hashtag)} rows")
    print(f"  brand_keywords: {list(brand_keywords['brand_key'])}")


if __name__ == "__main__":
    main()
