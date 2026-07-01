# ARCHITECTURE — FMCG Market Research Data Pipeline

End-to-end flow that turns raw marketplace sales data into a standardized monthly master
database ready for the market-research dashboard. See [SCOPE.md](SCOPE.md) for context and
[REQUIREMENTS.md](REQUIREMENTS.md) for the requirement IDs referenced below.

## Processing flow

```
                 ┌─────────────────────────┐
   raw export    │  input/  (per period)   │   hundreds of thousands of SKUs
   (marketplace) │  YYYYMM sales snapshot   │   no standard taxonomy
                 └────────────┬────────────┘
                              │
            ┌─────────────────┴────────────────────────┐
            │                                          │
            ▼                                          ▼
   ┌──────────────────┐               ┌──────────────────────────────────────┐
   │  EXISTING SKUs   │               │              NEW SKUs                │
   │  keep prior tags │               │  1. Rule-based Tagging Engine        │
   │  refresh rev/qty │               │  2. LLM Text Classifier Fallback     │ FR-1, FR-2, FR-7
   │  (FR-4)          │               │     (category, brand, line, gender)  │
   └────────┬─────────┘               └──────────────────┬───────────────────┘
            │                                            │
            │                                            ▼
            │                                  ┌────────────────────┐
            │                                  │  combo allocation  │  FR-6, DR-5
            │                                  │  coefficient ≈ 1   │
            │                                  └─────────┬──────────┘
            │                                            │
            └───────────────────────┬────────────────────┘
                                    ▼
                          ┌────────────────────┐
                          │   MASTER DB MERGE  │  DR-1 grain: product_id × category
                          │   normalize keys   │  DR-2 strip _old/_new, dedup
                          │   dedup composite  │
                          └─────────┬──────────┘
                                    ▼
                          ┌────────────────────┐
                 │    AUTOMATED QC    │  QC-1..QC-5
                 │  cross-check rev   │  flag drift > threshold
                 │  audit "Others"    │  validate combos
                 └─────────┬──────────┘
                           │  pass?
                 ┌─────────┴──────────┐
              no │                    │ yes
                 ▼                    ▼
          review flagged      ┌────────────────────┐
          rows, fix rules     │  HANDOFF / UPLOAD  │  only after QC passes
                              │  master DB + report │
                              └────────────────────┘
```

## Components

| Stage | Module | Key requirements |
|-------|--------|------------------|
| Tag new SKUs | [`src/tagging_engine.py`](src/tagging_engine.py) | FR-1, FR-2, FR-3, QC-2 |
| Merge & dedup master DB | [`src/master_db_merge.py`](src/master_db_merge.py) | DR-1, DR-2, FR-4 |
| Quality control | [`src/qc_checks.py`](src/qc_checks.py) | QC-1, QC-3 |
| Edge-case regression | [`tests/`](tests/) | NFR-4 |
| Narrative demo | [`notebooks/analysis_demo.ipynb`](notebooks/analysis_demo.ipynb) | full flow |

## Design notes

- **Hybrid Tagging Engine:** Combines the speed and predictability of a rule-based dictionary with an intelligent **LLM-based fallback (Azure GPT)**. Deterministic rules process 90% of the data instantly, while the LLM handles highly ambiguous, misspelled, or novel SKU names to extract full taxonomy (brand, category, line, gender).

- **Existing vs. new split (FR-4):** re-tagging every SKU each month would let dictionary
  tweaks silently shift historical numbers. Existing SKUs keep their prior tags; only new
  SKUs run through the engine.
- **Grain (DR-1):** a combo listing maps to several categories, so the master DB is keyed by
  `product_id × category`, not by `product_id` alone. Deduplicating to a single id would
  drop combo rows and undercount categories.
- **QC gate:** the pipeline is allowed to produce numbers, but they are only handed off once
  every QC check passes — the gate is what makes the figures trustworthy to the partner.
