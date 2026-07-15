"""Task 6: score funds by return (1/3/5y) + Sharpe (if present) - fees, then
keep the top 25 Active and top 25 Passive.

NOTE: the exact field names for getFactsheetPerformance are unverified
(Task 0 live spike is still pending in this environment — see PLAN.md). This
module looks up return/Sharpe/fee values by trying several candidate key
names so it keeps working once the real schema is confirmed; adjust
PERFORMANCE_KEY_CANDIDATES / FEE_KEY_CANDIDATES after running the spike.
"""
import ast
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"
IN_FILE = DATA_DIR / "processed" / "funds_classified.csv"
OUT_FILE = DATA_DIR / "processed" / "funds_ranked.csv"

PERFORMANCE_KEY_CANDIDATES = {
    "return_1y": ["return_1y", "return1y", "yield_1y", "return_1_y"],
    "return_3y": ["return_3y", "return3y", "yield_3y", "return_3_y"],
    "return_5y": ["return_5y", "return5y", "yield_5y", "return_5_y"],
    "sharpe": ["sharpe_ratio", "sharpe"],
}
FEE_KEY_CANDIDATES = ["rate"]


def parse_list_field(value) -> list[dict]:
    if isinstance(value, list):
        return value
    if not value or not isinstance(value, str):
        return []
    try:
        parsed = ast.literal_eval(value)
        return parsed if isinstance(parsed, list) else []
    except (ValueError, SyntaxError):
        return []


def first_present(d: dict, keys: list[str]):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None


def extract_performance(row) -> dict:
    entries = parse_list_field(row.get("performance_raw"))
    latest = entries[-1] if entries else {}
    out = {}
    for metric, candidates in PERFORMANCE_KEY_CANDIDATES.items():
        out[metric] = first_present(latest, candidates)
    return out


def extract_total_fee(row) -> float | None:
    fees = parse_list_field(row.get("fees_raw"))
    rates = [first_present(f, FEE_KEY_CANDIDATES) for f in fees]
    rates = [r for r in rates if isinstance(r, (int, float))]
    return sum(rates) if rates else None


def score(row) -> float | None:
    r1, r3, r5 = row.get("return_1y"), row.get("return_3y"), row.get("return_5y")
    returns = [r for r in (r1, r3, r5) if pd.notna(r)]
    if not returns:
        return None
    avg_return = sum(returns) / len(returns)
    sharpe_bonus = row.get("sharpe") if pd.notna(row.get("sharpe")) else 0
    fee_penalty = row.get("total_fee") if pd.notna(row.get("total_fee")) else 0
    return avg_return + sharpe_bonus - fee_penalty


def main():
    if not IN_FILE.exists():
        raise SystemExit("Run classify.py first")

    df = pd.read_csv(IN_FILE)

    perf = df.apply(extract_performance, axis=1, result_type="expand")
    df = pd.concat([df, perf], axis=1)
    df["total_fee"] = df.apply(extract_total_fee, axis=1)
    df["score"] = df.apply(score, axis=1)

    # ranking requires at least 3y return per PLAN.md edge cases
    rankable = df[df["return_3y"].notna() & df["score"].notna()].copy()

    top_active = rankable[rankable["management_style"] == "Active"].nlargest(25, "score")
    top_passive = rankable[rankable["management_style"] == "Passive"].nlargest(25, "score")

    ranked = pd.concat([top_active, top_passive])
    ranked.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    print(f"Rankable funds: {len(rankable)}")
    print(f"Top Active: {len(top_active)}, Top Passive: {len(top_passive)}")
    print(f"-> {OUT_FILE}")


if __name__ == "__main__":
    main()
