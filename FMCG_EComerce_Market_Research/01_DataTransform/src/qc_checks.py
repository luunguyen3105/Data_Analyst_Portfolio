"""Automated QC checks (QC-1, QC-3).

Run before handing a rebuilt master DB to the partner. Instead of trusting a full pipeline
re-run blindly, compare aggregates against the previous build and surface anything that
moved more than expected, plus validate that combo coefficients conserve revenue.
"""
import pandas as pd

REVENUE_DRIFT_THRESHOLD_PCT = 5.0
COMBO_COEFFICIENT_TOLERANCE = 0.01


def cross_check_revenue(
    df_before: pd.DataFrame,
    df_after: pd.DataFrame,
    group_col: str = "partner_category",
    value_col: str = "revenue",
) -> pd.DataFrame:
    """QC-1: per-category revenue drift between two builds; flag movement over the threshold."""
    agg_before = df_before.groupby(group_col)[value_col].sum().rename("before")
    agg_after = df_after.groupby(group_col)[value_col].sum().rename("after")

    comparison = pd.concat([agg_before, agg_after], axis=1).fillna(0)
    # A category may exist in only one period (newly added / dropped). Mask a zero baseline
    # with NaN (kept as float, not object) so the division stays numeric and .round works.
    baseline = comparison["before"].where(comparison["before"] != 0)
    comparison["diff_pct"] = ((comparison["after"] - comparison["before"]) / baseline * 100).round(2)
    comparison["flagged"] = comparison["diff_pct"].abs() > REVENUE_DRIFT_THRESHOLD_PCT
    return comparison.reset_index()


def validate_combos(df: pd.DataFrame, combo_col: str = "combo_id", coef_col: str = "coefficient_in_combo") -> pd.DataFrame:
    """QC-3: each combo must have >= 2 rows and coefficients summing to ~1 (revenue conservation)."""
    grouped = df.groupby(combo_col)[coef_col].agg(["count", "sum"]).rename(columns={"count": "n_rows", "sum": "coef_sum"})
    grouped["ok"] = (grouped["n_rows"] >= 2) & ((grouped["coef_sum"] - 1.0).abs() <= COMBO_COEFFICIENT_TOLERANCE)
    return grouped.reset_index()


if __name__ == "__main__":
    df_before = pd.DataFrame(
        {"partner_category": ["Shower gel", "Shampoo", "Deodorant"], "revenue": [1_000_000, 800_000, 300_000]}
    )
    df_after = pd.DataFrame(
        {"partner_category": ["Shower gel", "Shampoo", "Deodorant"], "revenue": [1_020_000, 950_000, 295_000]}
    )

    print("QC-1 revenue cross-check:")
    rev = cross_check_revenue(df_before, df_after)
    print(rev.to_string(index=False))
    flagged = rev[rev["flagged"]]
    if not flagged.empty:
        print(f"-> {len(flagged)} category(ies) moved more than {REVENUE_DRIFT_THRESHOLD_PCT}% - needs review before handoff.")

    combos = pd.DataFrame(
        {
            "combo_id": ["C1", "C1", "C2", "C2"],
            "coefficient_in_combo": [0.6, 0.4, 0.7, 0.5],  # C2 sums to 1.2 -> should fail
        }
    )
    print("\nQC-3 combo validation:")
    print(validate_combos(combos).to_string(index=False))
