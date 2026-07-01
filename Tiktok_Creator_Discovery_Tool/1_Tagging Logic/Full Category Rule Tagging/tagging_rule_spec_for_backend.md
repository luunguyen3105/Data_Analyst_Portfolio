# Spec: Category & Concern Tagging for Videos at Crawl/Transform Layer

> Document handed over to the Data Backend team. Objective: pre-assign tags (category, concern)
> to the video datamart **during the crawl/transform phase**, so that downstream users only need a simple `WHERE` clause
> to filter data by industry/niche, avoiding text processing for every ad-hoc query.

## 1. Objectives & Scope

- Each video (`video_id` = `post_id_platform`) will be assigned:
  - `category_l1`, `category_l2`: Industry/Niche (single label).
  - `concerns`: Specific needs/characteristics (multi-label, e.g., skin concern, health concern).
  - Traceability metadata: source of the tag, confidence score, dictionary version, and timestamp.
- Tagging is **deterministic and rule-based** (dictionary lookup). NO Machine Learning is required at the backend serving layer.
  LLMs (if any) are only run offline to **generate/enrich dictionaries**, not in the real-time pipeline.
- Dictionaries are stored as **external configs (versioned JSON files)** — allowing the business team to update rules without deploying code.

## 2. Additional Columns for Video Datamart

Proposed columns to be added to the video fact table (or a dedicated tag table keyed by `video_id`):

| Column | Type | Description |
|---|---|---|
| `category_l1` | `LowCardinality(String)` | Level 1 Category. `'Unknown'` if undetermined. |
| `category_l2` | `LowCardinality(String)` | Level 2 Category. `'Unknown'` if absent. |
| `category_source` | `Enum8('product_link','hashtag','keyword','creator_prior','llm','unknown')` | The logic layer that decided the tag. |
| `category_confidence` | `Float32` | Confidence score from 0–1 (refer to the table in Section 4). |
| `concerns` | `Array(LowCardinality(String))` | List of matched concerns (multi-label). Empty array if none. |
| `tag_dict_version` | `String` | Dictionary version used for tagging (e.g., `v2026.06`). |
| `tagged_at` | `DateTime` | Timestamp of when the tag was applied. |

Recommendation: Attach these directly to the serving datamart for fast filtering, rather than keeping a separate `video_tag` table that requires JOINs.

## 3. Text Normalization (MANDATORY consistency across all layers)

Apply to `description`, each element in `hashtags`, and `search_keywords`:

1. `lowercase`.
2. Remove Vietnamese diacritics (NFD → strip combining marks): e.g., `dưỡng ẩm` → `duong am`.
3. Replace any character not in `[a-z0-9]` with a space; merge multiple spaces into one.
4. For hashtags: remove `#`, split by `_` and camelCase boundaries before normalizing.
5. Apply **stoplist** for meaningless/generic hashtags/keywords: `xuhuong, fyp, foryou, viral, trending, capcut, xh, xhtiktok, reviewdung, ...` (see `stoplist.json`).

> Why consistency is mandatory: The dictionaries are built using normalized text. If the backend applies different normalization logic during execution, it will result in mismatched tags.

## 4. Category Tagging Logic — Priority Cascade

Evaluate in the following order. **Stop at the first matched tier**:

| Tier | Source | Condition | `category_source` | `category_confidence` |
|---|---|---|---|---|
| 0 | Product Link | `length(list_product_base_id) > 0` → join `analytics.products` → `mapping.categories` | `product_link` | `1.0` |
| 1 | Hashtag Dictionary | Normalized hashtags match `hashtag_to_category.json` | `hashtag` | `0.8` |
| 2 | Keyword Dictionary | Tokens in `description`/`search_keywords` match `keyword_to_category.json` | `keyword` | `0.65` |
| 3 | Creator Prior | Inferred from the category distribution of the creator's historical Tier 0-2 videos. | `creator_prior` | `0.5` |
| 4 | Undetermined | Remaining | `unknown` | `0.0` |

Disambiguation Rules (when a single tier matches multiple categories):
- Tier 1/2: Choose the category with the **highest total match weight** (each dictionary entry has a predefined `weight`).
- If weights are tied → set `category_l2 = 'Unknown'` and reduce `confidence` by 0.1. DO NOT guess randomly.
- Tier 3 is only applied if the creator has ≥ `N` videos already tagged in Tiers 0–2, and the top category accounts for ≥ `P%` (suggested: `N=5`, `P=60`). Otherwise, downgrade to Tier 4.

## 5. Concern Tagging Logic (Multi-label, independent of category)

- Match against normalized `description + hashtags + search_keywords (+ transcript if available)`.
- Each concern maps to a set of keywords in `concern_dict.json`. If matched, append to the `concerns` array.
- Multi-label: 1 video can have multiple concerns. Do not stop early like Category logic.
- Concerns are industry-bound (e.g., skin concerns are only evaluated if `category_l1` ∈ Beauty) to reduce noise and false positives.

## 6. Dictionary Format (External versioned config)

`hashtag_to_category.json` / `keyword_to_category.json`:

```json
{
  "version": "v2026.06",
  "entries": [
    { "term": "tri mun",   "category_l1": "Beauty", "category_l2": "Skincare", "weight": 1.0 },
    { "term": "serum",     "category_l1": "Beauty", "category_l2": "Skincare", "weight": 0.9 },
    { "term": "giam can",  "category_l1": "Health", "category_l2": "Supplement", "weight": 1.0 }
  ]
}
```

`concern_dict.json`:

```json
{
  "version": "v2026.06",
  "scope": { "Beauty": ["acne","dark_spot","aging","dryness","whitening"] },
  "concerns": {
    "acne":      { "terms": ["mun","tri mun","mun an","acne"] },
    "whitening": { "terms": ["trang da","duong trang","brightening"] }
  }
}
```

`stoplist.json`: `{ "version": "v2026.06", "terms": ["xuhuong","fyp","capcut"] }`

> Convention: Business/MI teams maintain these JSON files. The backend simply loads and applies them. Every update bumps the `version`. `tag_dict_version` records the specific version applied to each row.

## 7. Operational Rules (Incremental updates & Performance)

1. **Tag immediately on insert/update** of a video in the transform layer (dbt incremental model using `updated_at`).
2. Persist `tag_dict_version`. When dictionary versions are bumped → **only re-tag** records with an outdated `tag_dict_version` (via background batch job). DO NOT do full historical re-tags on daily runs.
3. Tier 0 (Product Link) has absolute priority: if an older video later gets an affiliate link, upgrade its tag to `product_link` and set `confidence=1.0`.
4. Performance considerations:
   - Tagging is purely dictionary matching on normalized text → O(number of tokens), highly efficient.
   - Avoid heavy regex or `arrayJoin` text parsing on large fact tables during ad-hoc queries; pre-compute tags once at the transform layer.
   - Load dictionaries into memory (hashmaps) once. Do not JOIN dictionary tables inside operational loops.

## 8. Downstream Filtering (Desired Output)

With this spec implemented, downstream queries for industry filtering simply become:

```sql
SELECT * FROM video_datamart
WHERE category_l1 = 'Beauty'
  AND has(concerns, 'acne')
  AND category_confidence >= 0.65;
```

## 9. Quality Assurance (Recommended acceptance criteria)

- Use the Tier 0 subset (videos with actual product links) as **Ground Truth**: temporarily hide the link, force the system to cascade guess using hashtags/keywords, and compare against the actual category to calculate `accuracy`.
- Track 2 key metrics upon every dictionary update: `coverage` (% of videos ≠ Unknown) and `accuracy` (on Tier 0).
- Proposed Acceptance Threshold: Coverage ≥ 80%, Accuracy on Tier 0 ≥ 85% for core categories.

## 10. Action Items for Backend Team Confirmation

1. Will the columns be appended directly to the **existing serving datamart** or stored in a separate **`video_tag` table**?
2. Which layer provides the cleanest `hashtags`/`search_keywords` to feed into this logic (currently visible in `dbt.video__raw`)?
3. What is the mechanism for loading JSON configs (storage location, reload triggers upon version bump)?
4. What is the frequency of background re-tagging when dictionary versions are bumped (daily/weekly batch)?
