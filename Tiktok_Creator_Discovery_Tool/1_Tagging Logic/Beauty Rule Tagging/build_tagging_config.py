"""
Tạo file Excel cấu hình tagging creator.
Chạy lại script này khi cần reset file mẫu; sau đó chỉnh sửa Excel thủ công.
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
OUTPUT = BASE / "creator_tagging_config.xlsx"

# --- Sheet: key_type (single label, ưu tiên theo cột priority nhỏ = cao) ---
KEY_TYPE = pd.DataFrame(
    [
        {
            "label": "Doctor",
            "priority": 1,
            "source": "profile",
            "keyword_pattern": (
                r"bác sĩ|bac si|bacsi|bs da lieu|bsdl|chuyen khoa da lieu|da lieu|"
                r"dược sĩ|duoc si|duocsi|\bds\b|si da|ngành y|nganh y|ngành dược|nganh duoc|"
                r"y khoa|y dược|y duoc|med student|medical student|clinic|medical|"
                r"doctor|dr\.|\bdr\b|pharmacist|bs\.|dermatologist|derma\b|skincarebacsi|y tế|da liễu"
            ),
            "notes": "Chuyên gia y tế / da liễu (channel_name + description)",
        },
        {
            "label": "Beauty KOC",
            "priority": 2,
            "source": "both",
            "keyword_pattern": r"for work|fw:|booking|collab|brand inbox|\bkoc\b|kocvn|kocvietnam|beautykoc|tiktokkoc|kocbeauty|reviewkoc|kocskincare|\bkol\b|\bkols\b|affiliate|pr:|hợp tác|hop tac|tài trợ|tai tro|narocnik|partner",
            "notes": "KOC/KOL + tín hiệu nhận job / PR / collab (description + hashtag video)",
        },
        {
            "label": "Mom & Baby",
            "priority": 3,
            "source": "both",
            "keyword_pattern": r"mẹ bỉm|me bim|bỉm sữa|bim sua|làm mẹ|lam me|mẹ và bé|me va be|nuôi con|nuoi con|motherhood|mebimsa|bebim|mevabe",
            "notes": "Nội dung mẹ và bé",
        },
        {
            "label": "Gym",
            "priority": 4,
            "source": "both",
            "keyword_pattern": r"\bgym\b|fitness|workout|thể dục|the duc|personal trainer|yoga\b|pilates|tập luyện|tap luyen",
            "notes": "Fitness / gym",
        },
        {
            "label": "Skincare/Beauty",
            "priority": 5,
            "source": "both",
            "keyword_pattern": r"skincare|beauty|làm đẹp|lam dep|mỹ phẩm|my pham|dưỡng da|duong da|makeup|make up|chamsocda|lamdep|goclamdep|reviewlamdep",
            "notes": "Creator skincare / beauty (không có signal KOC rõ hơn)",
        },
        {
            "label": "Lifestyle",
            "priority": 6,
            "source": "both",
            "keyword_pattern": r"lifestyle|vlog\b|daily\b|cuộc sống|cuoc song|chia sẻ cuộc|chia se cuoc|xuhuong\b|fyp\b",
            "notes": "Lifestyle / vlog / trend",
        },
        {
            "label": "Unknown",
            "priority": 99,
            "source": "fallback",
            "keyword_pattern": "",
            "notes": "Không khớp rule nào ở trên",
        },
    ]
)

# --- Sheet: tier ---
TIER = pd.DataFrame(
    [
        {"label": "Nano", "min_followers": 0, "max_followers": 999, "notes": "< 1K"},
        {"label": "Micro", "min_followers": 1000, "max_followers": 9999, "notes": "1K – 10K"},
        {"label": "Rising", "min_followers": 10000, "max_followers": 99999, "notes": "10K – 100K"},
        {"label": "Macro", "min_followers": 100000, "max_followers": 999999, "notes": "100K – 1M"},
        {"label": "Mega", "min_followers": 1000000, "max_followers": None, "notes": ">= 1M"},
    ]
)

# --- Sheet: brand_keywords (dùng cho brand loyalty từ video) ---
BRAND_KEYWORDS = pd.DataFrame(
    [
        {"brand": "obagi", "brand_display": "Obagi", "keyword_pattern": r"obagi"},
        {
            "brand": "la_roche_posay",
            "brand_display": "La Roche-Posay",
            "keyword_pattern": r"larocheposay|larocheposayvn|lrpvn|\blrp\b|anthelios|cicaplast|effaclar|uvair|toleriane|uvmune|hyalu",
        },
        {
            "brand": "cerave",
            "brand_display": "CeraVe",
            "keyword_pattern": r"cerave|ceravepartner|ceravevietnam|hợptáccùngcerave|hop_tac_cung_cerave",
        },
        {"brand": "bioderma", "brand_display": "Bioderma", "keyword_pattern": r"bioderma|sensibio|sebium"},
        {"brand": "cocoon", "brand_display": "Cocoon", "keyword_pattern": r"cocoon|cocoonvietnam|myphamthuanchay"},
    ]
)

# --- Sheet: brand_loyalty ---
BRAND_LOYALTY = pd.DataFrame(
    [
        {
            "label": "No-Brand",
            "min_brand_count": 0,
            "max_brand_count": 0,
            "notes": "Không có video mention brand nào trong 5 brand",
        },
        {
            "label": "Single Brand",
            "min_brand_count": 1,
            "max_brand_count": 1,
            "notes": "Chỉ 1 brand",
        },
        {
            "label": "Multi-Brand",
            "min_brand_count": 2,
            "max_brand_count": None,
            "notes": ">= 2 brand",
        },
    ]
)

# --- Sheet: platform_addons ---
PLATFORM_ADDONS = pd.DataFrame(
    [
        {
            "label": "multi-platform",
            "keyword_pattern": r"\big\b|instagram|youtube|\byt\b|facebook|\bfb\b|pinterest|threads|spotify",
            "source": "description",
            "notes": "Có mention nền tảng khác ngoài TikTok",
        },
        {
            "label": "only Tiktok",
            "keyword_pattern": "",
            "source": "fallback",
            "notes": "Mặc định khi không khớp multi-platform",
        },
    ]
)

# --- Sheet: readme ---
README = pd.DataFrame(
    [
        {"topic": "File", "detail": "creator_tagging_config.xlsx – chỉnh keyword/label tại đây, chạy tag_creator.py"},
        {
            "topic": "key_type",
            "detail": "Single label; priority nhỏ thắng. source: description | channel_name | hashtags_agg | profile (channel_name+description) | profile_both | both (description+hashtags)",
        },
        {"topic": "tier", "detail": "Theo followers; không có profile -> Unknown; max_followers null = không giới hạn trên"},
        {"topic": "brand_loyalty", "detail": "No-Brand | Single Brand | Multi-Brand (theo số brand khác nhau)"},
        {"topic": "brand_detail", "detail": "Brand display, sắp xếp nhiều->ít video, phân cách | cho Power BI"},
        {"topic": "platform_addons", "detail": "Chỉ đọc description (channel profile)"},
        {"topic": "active_status", "detail": "Đã bỏ — dữ liệu video crawl theo hashtag, không theo danh sách creator"},
    ]
)


def main() -> None:
    with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
        README.to_excel(writer, sheet_name="readme", index=False)
        KEY_TYPE.to_excel(writer, sheet_name="key_type", index=False)
        TIER.to_excel(writer, sheet_name="tier", index=False)
        BRAND_KEYWORDS.to_excel(writer, sheet_name="brand_keywords", index=False)
        BRAND_LOYALTY.to_excel(writer, sheet_name="brand_loyalty", index=False)
        PLATFORM_ADDONS.to_excel(writer, sheet_name="platform_addons", index=False)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
