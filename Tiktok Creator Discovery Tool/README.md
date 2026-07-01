# TikTok Creator Discovery & Analytics Tool

> *Note: Sensitive data, proprietary dictionaries, and client identities have been anonymized or removed.*

## 1. Business Context
The initial scope of this project was to build a data-driven tool to discover and evaluate TikTok Creators exclusively for the **Beauty & Personal Care** industry. However, the data architecture and tagging rules proved so effective that multiple clients from other industries requested access.

To capture this market opportunity, I led the expansion of the logic from a single-industry focus into a **Full Market Category Tagging System**, enabling the platform to classify, analyze, and rank creators across all e-commerce categories.

---

## 2. My Role (Technical Data Analyst)

I drove the analytical logic and data specifications across both major phases of the project:

### 🎯 Phase 1: Beauty Industry Tagging & Dashboard
- **Rule-Based Tagging Engine:** Designed the deterministic, multi-tiered cascade tagging rules (Product Link > Hashtag Dictionary > Keyword Dictionary > Creator Prior) to classify both **Creators and Videos** accurately.
- **Dashboard Foundation:** The structured outputs from these tagging rules directly fed the data marts, forming the data foundation used to build the initial Beauty Creator Discovery Dashboard.

### 🎯 Phase 2: Full Market Scaling (All Categories)
- **Hashtag Purity Algorithm:** To scale beyond Beauty, I engineered a mathematical "Purity Algorithm" to isolate and extract highly relevant, niche-specific hashtags for any given category or brand, cutting through TikTok's generic noise.
- **Data Pipeline Expansion:** Utilized the purified hashtag dictionaries to query and extract the massive pool of cross-industry videos.
- **Creator Percentile Ranking:** Engineered a dynamic scoring system using SQL Window Functions to evaluate and rank creators by **percentile** (based on View Rate, Engagement Rate, etc.) within their newly identified Category and Follower Tier, enabling clients to easily pick top-tier KOLs.
- **Rule Expansion:** Formulated the code and logic rules for all the new industry categories, handing the specifications over to the backend Data Engineering team for production deployment.

---

## 3. Technical Implementation (ClickHouse)

This project heavily utilized **ClickHouse** for big data processing. The SQL scripts in this repository demonstrate advanced Data Engineering and Analytics capabilities:

- **Complex Data Types:** Extensive use of `Array`, `Tuple`, and `LowCardinality` for optimized storage and fast querying of nested data (like hashtag lists and time-series metrics).
- **Advanced Aggregation:** Utilized ClickHouse-specific functions like `argMax` to dynamically determine a Creator's Primary Niche without expensive subqueries or self-joins.
- **Array Functions & Lambdas:** Leveraged `arrayJoin`, `arrayFilter`, and high-order Lambda functions (`h -> lower(h)`) to process strings and match dictionary tags at scale directly within the database engine.
- **Dynamic Time Windows:** Used `CROSS JOIN` techniques with static arrays to calculate 14-day, 30-day, and 90-day moving windows efficiently.

---

## 4. Repository Structure & Key Assets

- 📂 **`/1_Tagging Logic`**
  - 📄 `tagging_rule_spec_for_backend.md`: The deterministic backend tagging architecture (Category & Concern cascade logic).
  - 📂 `/Full Category Rule Tagging`: Contains the NLP scripts for the Hashtag Purity Algorithm.
  - 📊 `sample_creator_ranked_output.xlsx`: **[Demo Data]** An anonymized sample of the final output, showing how creators are ranked by percentiles across different tiers and niches.

- 📂 **`/2_ClickHouse_SQL`**
  - 📄 `02_creator_analytics.sql`: Advanced queries for Niche assignment and dynamic Percentile scoring (using Window Functions).
  - 📄 `03_video_analytics.sql`: Queries for deduplication, brand-hashtag matching, and viral trend discovery.

- 📂 **`/3_Dashboard Layout`**
  - Wireframes and mockup structures for the final customer-facing discovery tool.

---

## 5. Dashboard Layout Mockups

Below are the mockups designed to translate the complex backend data structures into an intuitive, user-friendly interface for our clients:

### Brand & Channel Group Context
![Brand & Channel Group Context](3_Dashboard%20Layout/Brand_Channel%20group%20context.png)

### Channel Deep Dive
![Channel Deep Dive](3_Dashboard%20Layout/Channel%20deep%20dive.png)
