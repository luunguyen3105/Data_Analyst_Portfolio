# Hashtag Purity Algorithm (Methodology & Output)

## 1. The Problem: "The Noise of TikTok"
TikTok videos contain highly unstructured text data. Creators frequently use generic, high-traffic hashtags like `#fyp`, `#xuhuong`, `#viral`, or `#tiktok` alongside niche-specific hashtags to maximize their reach. 

If we classify videos using a naive frequency count, generic hashtags will always dominate the top results, making it impossible to automatically identify which hashtags truly belong to a specific industry (e.g., Beauty, Electronics, Fashion).

## 2. The Solution: Purity Scoring (TF-IDF inspired)
To solve this, I developed the **Hashtag Purity Algorithm**. Instead of just looking at raw volume (Term Frequency), this algorithm evaluates how **exclusive** a hashtag is to a specific Category compared to the entire market (Inverse Document Frequency concept).

### The Mathematical Logic:
For any given Hashtag ($H$) and Category ($C$):

1. **Category Frequency ($CF$)**: How many times $H$ appears in videos mapped to $C$.
2. **Global Frequency ($GF$)**: How many times $H$ appears across **all** videos on TikTok.
3. **Purity Score**: $Purity = \frac{CF}{GF}$

### Decision Rules:
A hashtag is selected as a "Dictionary Tag" for a Category if it meets two thresholds:
1. **Volume Threshold:** Global Frequency > `MIN_VOLUME` (Ensures the hashtag is statistically significant and not just a typo).
2. **Purity Threshold:** Purity Score > `80%` (Ensures the hashtag is highly exclusive to this category).

---

## 3. Example Output

Here is a conceptual example of how the algorithm processes hashtags and filters out the noise:

| Hashtag | Category | Category Freq (CF) | Global Freq (GF) | Purity Score | Action |
|---------|----------|--------------------|------------------|--------------|--------|
| `#serum` | Beauty | 45,000 | 48,000 | **93.7%** | ✅ **KEEP** (High purity, specific to Beauty) |
| `#skincare` | Beauty | 120,000 | 125,000 | **96.0%** | ✅ **KEEP** (High purity) |
| `#iphone15` | Electronics | 30,000 | 31,000 | **96.7%** | ✅ **KEEP** (High purity for Electronics) |
| `#fyp` | Beauty | 2,500,000 | 25,000,000 | **10.0%** | ❌ **DROP** (Generic noise, low purity) |
| `#xuhuong` | Electronics | 500,000 | 15,000,000 | **3.3%** | ❌ **DROP** (Generic noise) |

---

## 4. Impact
By running this algorithm across the historical database of millions of videos, we automatically generated clean, highly accurate **Hashtag-to-Category Dictionaries** for the backend Tagging Engine to use. 

This completely eliminated the need for manual curation of thousands of hashtags and prevented the Data Engineering pipeline from misclassifying videos based on generic viral tags.
