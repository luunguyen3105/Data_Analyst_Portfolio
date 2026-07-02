# REQUIREMENTS — FMCG Market Research Data Pipeline

Requirements for the pipeline described in [SCOPE.md](SCOPE.md), grouped into four
categories: Functional, Data, Quality (QC), and Non-functional.

## 1. Functional requirements

| ID | Requirement | Business rationale |
|----|-------------|--------------------|
| FR-1 | Classify each SKU into exactly **product category**, **partner brand**, and **product line** from its product name | Compute market share by full contractual taxonomy |
| FR-2 | Assign a **target audience** (`partner_function`: Male / Female / Unisex / Others) | Partner analyzes by gender segment |
| FR-3 | Apply rules in **priority order**; SKUs matching multiple signals are resolved by explicit rules (e.g. combo before single item) | Prevent overlapping / wrong-category tags |
| FR-4 | Split **existing SKUs** (keep tags from the previous master, only refresh revenue/units) vs. **new SKUs** (run the tagging engine) | Maintain historical consistency across periods |
| FR-5 | Run iteratively per data period `--data-period YYYYMM`, supporting `--resume` on interruption | Monthly operation over large data |
| FR-6 | Allocate **combo** revenue (one listing bundling several items) via `coefficient_in_combo` | Avoid double-counting a combo's revenue |
| FR-7 | Integrate an **LLM Text Classifier** (Azure OpenAI GPT API) | Act as a fallback for difficult SKUs or products requiring visual/image context to identify the product line, while standard SKUs are routed to rule-based logic to optimize API costs |
## 2. Data requirements

| ID | Requirement |
|----|-------------|
| DR-1 | Master DB **grain**: `product_id × category_flag` — combos produce multiple rows and must **not** be deduplicated to a single id |
| DR-2 | **Composite key** for dedup when merging multiple sources/periods; normalize identifier keys (strip inconsistent `_old`/`_new` suffixes left by a previous re-tag run) |
| DR-3 | Normalize **Vietnamese encoding**: detect and fix mojibake in `product_name`, `shop_name` |
| DR-4 | Keep the master DB schema stable across periods (same column set) so the dashboard can compare periods |
| DR-5 | Each combo's `coefficient_in_combo` must sum to ≈ 1 (revenue conservation) |

## 3. Quality requirements (QC — mandatory before handoff)

| ID | Check | Pass threshold / condition |
|----|-------|----------------------------|
| QC-1 | Cross-check total revenue per category between the previous and current period | Difference within the allowed threshold (e.g. ±5%); over threshold → flag for review |
| QC-2 | Audit the **"Others"** bucket | A SKU that belongs to a real category must not fall into Others because of a bundled accessory/gift |
| QC-3 | Validate combos | Each combo has ≥ 2 rows; coefficients sum to ≈ 1 |
| QC-4 | Check duplicate SKUs | No duplicates by composite key after merge |
| QC-5 | Reconcile monthly total revenue (raw source) vs. post-merge | Difference is reasonable and explainable |

> Principle: **only upload/hand off after all QC checks pass.** Automated QC surfaces
> discrepancies early, before incorrect figures reach the partner.

## 4. Non-functional requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Process **hundreds of thousands of rows per period** within an acceptable runtime |
| NFR-2 | Heavy export steps must have **checkpoint/log** to resume on interruption (no full restart) |
| NFR-3 | Tagging logic is **decoupled from data** (configurable dictionary) so keyword changes do not require editing core code |
| NFR-4 | **Unit tests** for the engine, covering edge cases that have caused real data errors |
| NFR-5 | Output is **reproducible** from the same input + same dictionary |
| NFR-6 | Manage **Azure API rate limits and costs** | Implement batch processing and caching for LLM responses to prevent exponential API costs and timeout errors |

## 5. Requirement → code mapping

| Requirement | Reference implementation |
|-------------|--------------------------|
| FR-1, FR-2, FR-3, QC-2 | [`src/tagging_engine.py`](src/tagging_engine.py) |
| DR-1, DR-2, FR-4 | [`src/master_db_merge.py`](src/master_db_merge.py) |
| QC-1, QC-3 | [`src/qc_checks.py`](src/qc_checks.py) |
| NFR-4 | [`tests/`](tests/) |
| Full pipeline (narrative) | [`notebooks/analysis_demo.ipynb`](notebooks/analysis_demo.ipynb) |
