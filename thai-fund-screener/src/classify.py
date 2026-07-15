"""Task 5: classify each fund as Active/Passive based on keywords found in
its name and policy description."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"
IN_FILE = DATA_DIR / "processed" / "funds_clean.csv"
OUT_FILE = DATA_DIR / "processed" / "funds_classified.csv"

PASSIVE_KEYWORDS = [
    "ดัชนี", "index", "set50", "set100", "s&p", "nasdaq", "msci",
    "etf", "passive", "tracker",
]
ACTIVE_HINT_KEYWORDS = ["enhanced", "active"]


def classify_row(row) -> tuple[str, bool]:
    name = f"{row.get('proj_name_th', '')} {row.get('proj_name_en', '')}".lower()
    policy = str(row.get("policy_desc", "") or "").lower()
    haystack = f"{name} {policy}"

    has_passive_kw = any(kw in haystack for kw in PASSIVE_KEYWORDS)
    has_active_hint = any(kw in haystack for kw in ACTIVE_HINT_KEYWORDS)

    if has_passive_kw and has_active_hint:
        return "Active", True  # e.g. "active enhanced index" -> flagged for manual review
    if has_passive_kw:
        return "Passive", False
    return "Active", False


def main():
    if not IN_FILE.exists():
        raise SystemExit("Run clean.py first")

    df = pd.read_csv(IN_FILE)
    results = df.apply(classify_row, axis=1, result_type="expand")
    df["management_style"] = results[0]
    df["ambiguous"] = results[1]

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")

    counts = df["management_style"].value_counts().to_dict()
    print(f"Classified {len(df)} funds: {counts}, ambiguous={int(df['ambiguous'].sum())}")
    print(f"-> {OUT_FILE}")


if __name__ == "__main__":
    main()
