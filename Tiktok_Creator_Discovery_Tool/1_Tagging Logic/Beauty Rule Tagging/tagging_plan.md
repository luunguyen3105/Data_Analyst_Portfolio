# Tagging Plan — Creator & Video (Beauty / Sắc Đẹp → Multi-Category)

> Tài liệu này ghi lại **những gì đã làm** cho ngành Sắc Đẹp và **đề xuất mở rộng** sang nhiều ngành hàng.
> Cập nhật: 2026-06-18

---

## PHẦN 1 — ĐÃ LÀM (Beauty / Sắc Đẹp)

### 1.1 Tổng quan kiến trúc

```
[Excel config]  →  [build script]  →  [config .xlsx]  →  [tag script]  →  [output CSV]
```

Hai luồng độc lập, cùng dùng chung data CSV từ ClickHouse:

| Luồng | Build config | Tag script | Output |
|-------|-------------|-----------|--------|
| **Creator** | `build_tagging_config.py` | `tag_creator.py` | `creators_tagged.csv` |
| **Video** | `build_video_tagging_config.py` | `tag_video.py` | `videos_tagged.csv` |

Input data:
- `channels_full_*.csv` (hoặc fallback `channels_202605201038.csv`) — thông tin channel
- `video__analytics_202605201029 - remove dup.csv` — video đã dedup

---

### 1.2 CREATOR TAGGING

**File:** `tag_creator.py` + `creator_tagging_config.xlsx`

#### Các dimension đã tag

| Dimension | Kiểu | Mô tả | Labels |
|-----------|------|--------|--------|
| `key_type` | Single label | Loại creator (ưu tiên cascade) | Doctor → Beauty KOC → Mom & Baby → Gym → Skincare/Beauty → Lifestyle → Unknown |
| `tier` | Single label | Phân tầng theo followers | Nano (<1K) → Micro (1K–10K) → Rising (10K–100K) → Macro (100K–1M) → Mega (≥1M) |
| `brand_loyalty` | Single label | Mức độ gắn với brand | No-Brand / Single Brand / Multi-Brand |
| `brand_detail` | Text | Danh sách brand (sắp xếp nhiều→ít video) | "Obagi\|CeraVe\|..." |
| `brand_count` | Int | Số brand khác nhau xuất hiện | 0, 1, 2, ... |
| `platform_addons` | Single label | Có hoạt động nền tảng khác không | only Tiktok / multi-platform |

#### Logic `key_type`

- **Nguồn text** hỗ trợ: `description`, `channel_name`, `hashtags_agg` (tổng hợp hashtag từ tất cả video), `profile` (name+desc), `profile_both` (name+desc+hashtags), `both` (desc+hashtags)
- Cascade theo `priority` — rule priority nhỏ thắng, dừng ngay khi khớp

```
priority 1 → Doctor       (source: profile)       — bác sĩ, da liễu, dermatologist...
priority 2 → Beauty KOC   (source: both)           — koc, kol, affiliate, booking...
priority 3 → Mom & Baby   (source: both)           — mẹ bỉm, bỉm sữa, nuôi con...
priority 4 → Gym          (source: both)           — gym, fitness, workout, yoga...
priority 5 → Skincare/Beauty (source: both)        — skincare, làm đẹp, mỹ phẩm...
priority 6 → Lifestyle    (source: both)           — vlog, cuộc sống, fyp...
priority 99 → Unknown     (fallback)
```

#### Logic `brand_loyalty`

1. Với mỗi video → match text (hashtags + description) với regex pattern của từng brand
2. Group by `channel_id` → đếm số brand khác nhau xuất hiện trong video
3. Gán: 0 brand → No-Brand, 1 → Single Brand, ≥2 → Multi-Brand

**Brands đã có (5 brands trong creator config):**
`Obagi`, `La Roche-Posay`, `CeraVe`, `Bioderma`, `Cocoon`

#### Build flow

```
build_tagging_config.py
  └─ Xuất creator_tagging_config.xlsx
       ├─ Sheet: readme
       ├─ Sheet: key_type      (priority, source, keyword_pattern)
       ├─ Sheet: tier          (min/max_followers)
       ├─ Sheet: brand_keywords (brand, regex)
       ├─ Sheet: brand_loyalty  (label, min/max_brand_count)
       └─ Sheet: platform_addons (keyword_pattern, source)
```

---

### 1.3 VIDEO TAGGING

**File:** `tag_video.py` + `video_tagging_config.xlsx`

#### Các dimension đã tag

| Dimension | Kiểu | Mô tả | Labels |
|-----------|------|--------|--------|
| `brand_scope` | Single label | Video đề cập mấy brand | No Brand / Single-brand / Multi-brand |
| `brand_detail` | Text | Tên brand xuất hiện | "Obagi; CeraVe" hoặc "No Brand" |
| `skin_concern` | Multi-label | Nhu cầu da được đề cập | Sun Protection; Acne; Moisturizing; Cleansing; Exfoliating; Brightening; Anti-aging |
| `product_type` | Multi-label | Loại sản phẩm | Sunscreen; Cleanser; Serum; Moisturizer; Toner; Eye Cream; Micellar |
| `partnership_flag` | Boolean | Có dấu hiệu hợp tác/PR | True / (trống) |
| `content_type` | Single label | Thể loại nội dung | Sponsored/Partnership → Review → Tutorial → Unboxing |

#### Logic đặc biệt — `content_type`

Không đơn giản là cascade — chọn label có **keyword xuất hiện sớm nhất** trong văn bản:
- Thứ tự tìm kiếm: `hashtags` trước → `description` sau
- Nếu hòa vị trí → `priority` nhỏ hơn thắng

#### Logic `skin_concern` fallback

- Tag multi-label từ concern keywords
- Nếu không match concern cụ thể nào **nhưng** có từ skincare chung (`skincare`, `chamsocda`, `lamdep`...) → gán nhãn fallback `Skincare`

#### Brands đã có (10 brands trong video config)

`Obagi`, `La Roche-Posay`, `CeraVe`, `Bioderma`, `Cocoon`, `Vichy`, `Eucerin`, `Cetaphil`, `SVR`, `Torriden`

Mỗi brand có:
- **Sheet hashtag riêng** (quản lý danh sách hashtag thủ công)
- **`brand_extra_pattern`** (regex bổ sung ngoài hashtag list)
- Auto-compile thành `brand_keywords` (regex tổng hợp)

#### Build flow

```
build_video_tagging_config.py
  ├─ Đọc hashtag từ: video_tagging_config.xlsx (ưu tiên) → tagging_video_by_hashtag.xlsx (fallback)
  └─ Xuất video_tagging_config.xlsx
       ├─ Sheet: readme, output_fields
       ├─ Sheet: Obagi, La Roche-Posay, Cerave, Bioderma, Cocoon, Vichy, Eucerin, Cetaphil, SVR, Torriden
       ├─ Sheet: brand_hashtag    (long format: brand_key, hashtag)
       ├─ Sheet: brand_keywords   (regex tổng hợp)
       ├─ Sheet: brand_extra_pattern
       ├─ Sheet: brand_scope
       ├─ Sheet: skin_concern
       ├─ Sheet: skin_concern_fallback
       ├─ Sheet: product_type
       ├─ Sheet: partnership_flag
       └─ Sheet: content_type
```

---

### 1.4 Điểm mạnh của kiến trúc hiện tại

- ✅ **Config ngoài Excel** — business chỉnh keyword không cần sửa code
- ✅ **Cascade rõ ràng** — priority-based, dễ debug
- ✅ **Multi-label** cho concern & product_type — đúng với tính chất ngành đẹp
- ✅ **Brand loyalty** từ video aggregate → tín hiệu mạnh cho creator
- ✅ **Rebuild-safe** — `load_existing_rules()` giữ rule đã chỉnh tay, không ghi đè khi rebuild config
- ✅ **Fallback** skin_concern khi không match concern cụ thể

---

### 1.5 Hạn chế hiện tại

- ❌ **Hardcode cho Beauty** — key_type labels (Doctor, Skincare/Beauty...) không áp được cho ngành khác
- ❌ **Brand list nhỏ** — 5–10 brands, Beauty-only
- ❌ **Không có category_confidence** — không biết mức độ tin cậy của tag
- ❌ **Không versioning từ điển** — không track được khi nào config thay đổi
- ❌ **Input là CSV tĩnh** — không kết nối trực tiếp ClickHouse, phải export/import thủ công
- ❌ **Không có coverage metric** — chưa đo được bao nhiêu % video/creator được tag tốt
- ❌ **`platform_addons` chỉ đọc description** — bỏ sót tín hiệu từ hashtag và bio

---

## PHẦN 2 — RECOMMEND (Mở rộng Multi-Category)

### 2.1 Nguyên tắc thiết kế

> Giữ nguyên kiến trúc hiện tại (Excel config → build script → tag script → CSV).
> Mở rộng bằng cách **tách config theo category** thay vì viết lại hoàn toàn.

---

### 2.2 CREATOR TAGGING — Đề xuất mở rộng

#### A. Tách `key_type` thành 2 tầng

Hiện tại `key_type` mix cả "loại creator theo ngành" (Doctor, Skincare/Beauty) với "vai trò" (KOC, Mom). Nên tách:

| Dimension mới | Mô tả | Ví dụ labels |
|---------------|--------|-------------|
| `creator_role` | Vai trò của creator | KOC/KOL, Doctor/Expert, Seller, Casual |
| `creator_niche` | Lĩnh vực chuyên sâu | Beauty, Fashion, Food, Fitness, Parenting, Tech, Lifestyle, ... |

**Logic gợi ý:**
- `creator_role`: cascade từ tín hiệu rõ nhất (Doctor signal → KOC/KOL signal → Seller signal → Casual)
- `creator_niche`: dựa trên phân phối category của video → category nào chiếm ≥ 40% → đó là niche

#### B. Thêm `category_affinity` từ video aggregate

```
Với mỗi creator:
  → Đếm video theo category (từ video_category_tag)
  → Tính % video mỗi category
  → Top-1 category có % cao nhất → creator_primary_category
  → Nếu top-1 ≥ 60% → "Specialized", ngược lại → "Generalist"
```

| Dimension | Ý nghĩa |
|-----------|---------|
| `creator_primary_category` | Ngành hàng chủ đạo |
| `creator_focus_type` | Specialized (≥60%) / Generalist (<60%) |

#### C. Mở rộng Brand Loyalty sang nhiều ngành

Hiện tại brand loyalty chỉ cho Beauty. Cần:
- Tách brand list theo category vào config riêng
- Khi tag creator, load brand list theo category phù hợp
- Hoặc tag brand loyalty **per-category** (creator này loyal với Beauty brands nào? Fashion brands nào?)

#### D. Thêm `engagement_quality_tier`

Ngoài tier theo followers (Nano/Micro/...), thêm tier theo engagement rate:

```
engagement_rate = (liked + commented + shared) / viewed

Tier:
  High Engagement:  ≥ 5%
  Medium:           1% – 5%
  Low:              < 1%
```

---

### 2.3 VIDEO TAGGING — Đề xuất mở rộng

#### A. Thêm `category_l1` + `category_l2`

Đây là dimension quan trọng nhất cần thêm — hiện tại hoàn toàn thiếu.

**Nguồn để xác định category (theo độ ưu tiên):**

| Tier | Nguồn | Confidence |
|------|--------|-----------|
| 0 | Product link (list_product_base_id → analytics.products) | 1.0 |
| 1 | Hashtag khớp hashtag_dict per category | 0.8 |
| 2 | Keyword trong description/search_keywords | 0.65 |
| 3 | Creator prior (từ lịch sử video của channel) | 0.5 |
| 4 | Unknown | 0.0 |

**Xử lý conflict** (1 video match nhiều category):
- Tính tổng weighted score per category (weight = count_unique_video đã normalize)
- Category nào score cao nhất → thắng
- Nếu hòa → giữ `category_l2 = Unknown`, hạ confidence 0.1

#### B. Tổng quát hóa `skin_concern` → `concern`

Hiện tại `skin_concern` hardcode cho Beauty. Đề xuất:

```
concern = [] (multi-label, rỗng nếu không có concern dict cho category đó)

Với Beauty:    concern = [Acne, Moisturizing, Sun Protection, ...]
Với Food:      concern = [Organic, Diet, Keto, Vegan, ...]
Với Fitness:   concern = [Weight Loss, Muscle Gain, Recovery, ...]
Với Fashion:   (không có concern, để trống)
```

Config structure đề xuất:
```json
{
  "category": "beauty",
  "concerns": {
    "Acne": {"keywords": ["mun", "acne", "trimun", "effaclar"], "source": "both"},
    "Sun Protection": {"keywords": ["spf", "sunscreen", "kemchongnang"], "source": "both"}
  }
}
```

#### C. Tổng quát hóa `product_type` → `item_type`

Tương tự, `product_type` hiện tại là Beauty-specific (Sunscreen, Cleanser...).
Mỗi category cần có `item_type` riêng:

```
Beauty:   Sunscreen, Cleanser, Serum, Moisturizer, ...
Fashion:  Dress, Shirt, Pants, Accessories, ...
Food:     Snack, Drink, Supplement, Ingredient, ...
```

#### D. Giữ nguyên các dimension đã tốt

| Dimension | Giữ/Sửa | Ghi chú |
|-----------|---------|---------|
| `brand_scope` | ✅ Giữ | Mở rộng brand list per category |
| `brand_detail` | ✅ Giữ | |
| `partnership_flag` | ✅ Giữ | Pattern có thể chung tất cả ngành |
| `content_type` | ✅ Giữ | Sponsored/Review/Tutorial/Unboxing đúng cho mọi ngành |

#### E. Thêm `tag_confidence` + `tag_dict_version`

```python
# Mỗi video sau khi tag cần có:
video["category_confidence"] = 0.8   # float 0–1
video["tag_dict_version"]    = "v2026.06"
video["tagged_at"]           = "2026-06-18"
```

Dùng để:
- Filter khi query: `WHERE category_confidence >= 0.65`
- Re-tag khi update từ điển (chỉ re-tag dòng có version cũ)

---

### 2.4 Cấu trúc Config đề xuất

```
config/
├── shared/
│   ├── stoplist.json               # Hashtag vô nghĩa: fyp, xuhuong, viral...
│   ├── tier_config.json            # Nano/Micro/Macro/Mega (chung)
│   ├── partnership_patterns.json   # #ad, hợptác, tài trợ... (chung)
│   └── content_type_rules.json     # Review/Tutorial/Unboxing (chung)
│
├── categories/
│   ├── beauty/
│   │   ├── hashtag_dict.json       # (category, hashtag, weight) — từ Category count hashtag.xlsx
│   │   ├── brand_dict.json         # Brand list + regex — từ cate_topbrand + top_creator_by_shop
│   │   ├── concern_dict.json       # Skin concern keywords
│   │   └── item_type_dict.json     # Product type keywords
│   ├── fashion_women/
│   │   ├── hashtag_dict.json
│   │   ├── brand_dict.json
│   │   └── item_type_dict.json
│   ├── food/
│   │   ├── hashtag_dict.json
│   │   ├── brand_dict.json
│   │   ├── concern_dict.json       # Diet/Organic/Keto...
│   │   └── item_type_dict.json
│   └── ... (25+ categories)
│
└── category_registry.json          # Master: map category_l1 → folder + config params
```

---

### 2.5 Roadmap triển khai

#### Giai đoạn 1 — Nền tảng (ưu tiên cao)
- [ ] Sinh `hashtag_dict.json` cho tất cả 30 categories từ `Category count hashtag.xlsx`
- [ ] Sinh `brand_dict.json` cho 5 categories đã có brand data
- [ ] Tạo `stoplist.json` từ danh sách hashtag generic đã biết
- [ ] Viết `category_registry.json`

#### Giai đoạn 2 — Nâng cấp Video Tagging
- [ ] Thêm `category_l1`, `category_l2`, `category_confidence` vào output video
- [ ] Tổng quát hóa `skin_concern` → `concern` (load từ config per category)
- [ ] Tổng quát hóa `product_type` → `item_type`
- [ ] Thêm `tag_dict_version`

#### Giai đoạn 3 — Nâng cấp Creator Tagging
- [ ] Tách `key_type` → `creator_role` + `creator_niche`
- [ ] Thêm `creator_primary_category` từ video aggregate
- [ ] Thêm `creator_focus_type` (Specialized / Generalist)
- [ ] Mở rộng Brand Loyalty per-category

#### Giai đoạn 4 — Chất lượng & Vận hành
- [ ] Script `validate_dicts.py` — đo coverage, overlap
- [ ] Script `estimate_coverage.py` — ước tính % video được tag
- [ ] Tích hợp ClickHouse trực tiếp (thay thế export CSV thủ công)
- [ ] Versioning config + tự động re-tag khi bump version

---

### 2.6 Ước tính coverage ban đầu

Dựa trên `Category count hashtag.xlsx` (10.4M video, 30 categories):

| Category | Video count | Hashtag riêng (sau filter stoplist) | Ước tính coverage |
|----------|-------------|--------------------------------------|------------------|
| Chăm sóc sắc đẹp | 1.9M | Cao (đã có brand + concern logic) | ~85% |
| Trang phục nữ | 1.4M | Trung bình | ~70% |
| Đồ ăn & Đồ uống | 751K | Trung bình | ~65% |
| Trang phục nam | 698K | Trung bình | ~65% |
| Đồ gia dụng | 663K | Thấp (hashtag generic hơn) | ~55% |
| Long tail (25 categories còn lại) | ~5.5M | Thấp → cần bổ sung | ~40–60% |

> **Mục tiêu**: Coverage ≥ 80%, Accuracy trên Tier 0 ≥ 85% cho top 10 categories.
