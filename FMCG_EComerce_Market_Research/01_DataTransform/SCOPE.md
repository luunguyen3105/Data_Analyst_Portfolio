# SCOPE — FMCG Market Research Data Pipeline

> Case study based on a real project for Marico (an FMCG group in the personal-care
> category). All data in this repository is synthetic; it contains no real business
> figures, internal table/system names, or confidential partner information.

## 1. Business context

The partner is an FMCG brand that needs to **track the market share and category
performance of its own products and competitors** across e-commerce marketplaces. The raw
sales data from the marketplaces (hundreds of thousands of SKUs per month) **has no
standard taxonomy**: product names are abbreviated, misspelled, mixed-language, and the
marketplace's native categories do not map to how the partner groups categories under the
research contract.

Consequence: market share cannot be computed directly from raw data. An intermediate
processing layer is needed to turn raw data into a **standardized monthly master database**
that feeds the market-research dashboard.

## 2. Project objectives

1. Standardize and classify (tag) products by **product category**, **partner brand**, **product line**, and **target audience**
   (gender) according to the partner's contractual definitions.
2. Consolidate the data into a **monthly master database** that is comparable across periods.
3. Guarantee the **reliability of the figures** delivered to the partner through an automated
   QC layer applied before handoff.

## 3. Scope

### In-scope (the Data Analyst role in this project)
- Design and maintain a **hybrid tagging engine**: combining a rule/dictionary-based foundation with an **LLM-based Text Classifier** (via Azure OpenAI GPT). To optimize API costs, rule-based text identifiers process the majority of SKUs, while the LLM is exclusively routed to handle difficult products or those requiring visual/image context to differentiate product lines.
- A **monthly master DB merge** pipeline: normalize identifier keys, deduplicate, and split
  existing data (keep tags) vs. new data (re-tag).
- Handle **combos** (a single listing bundling multiple items) via a revenue-allocation
  coefficient.
- **Automated QC**: cross-check figures across periods, audit the "Others" bucket, validate
  combos.
- Handle **Vietnamese-specific data issues** (encoding/mojibake in product and shop names).

### Out-of-scope (handled by other teams or later phases)
- Collecting / extracting raw data from the marketplaces (data engineering).
- The final visualization and dashboard delivered to the partner (BI team).
- Business strategy recommendations derived from the analysis.


## 4. Deliverables

| Deliverable | Description | Frequency |
|---|---|---|
| Standardized master DB | Tagged SKU table at grain `product_id × category` | Monthly |
| QC report | Cross-checks and a list of flagged rows requiring review | Each build |
| Category overview | Revenue / SKU rollup by `partner_category` | Monthly |

## 5. Role & operating process

The pipeline runs **monthly**, parameterized by data period (`--data-period YYYYMM`). Because
the export of existing data is heavy (hundreds of thousands of rows), the pipeline supports
**checkpoint/resume** so it does not restart from scratch on interruption. Results are only
**handed off / uploaded after QC passes**.

Functional and technical requirements: see [REQUIREMENTS.md](REQUIREMENTS.md).
Processing flow diagram: see [ARCHITECTURE.md](ARCHITECTURE.md).
