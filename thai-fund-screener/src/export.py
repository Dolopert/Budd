"""Task 7: export the ranked funds into output/top25_comparison.xlsx with
separate Active and Passive sheets."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"
IN_FILE = DATA_DIR / "processed" / "funds_ranked.csv"
OUT_FILE = Path(__file__).parent.parent / "output" / "top25_comparison.xlsx"

COLUMNS = [
    "proj_id", "proj_name_th", "proj_name_en", "comp_name_th",
    "management_style", "ambiguous", "return_1y", "return_3y", "return_5y",
    "sharpe", "total_fee", "score",
]


def main():
    if not IN_FILE.exists():
        raise SystemExit("Run rank.py first")

    df = pd.read_csv(IN_FILE)
    cols = [c for c in COLUMNS if c in df.columns]

    active = df[df["management_style"] == "Active"][cols].sort_values("score", ascending=False)
    passive = df[df["management_style"] == "Passive"][cols].sort_values("score", ascending=False)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(OUT_FILE, engine="openpyxl") as writer:
        active.to_excel(writer, sheet_name="Active", index=False)
        passive.to_excel(writer, sheet_name="Passive", index=False)

    print(f"Active: {len(active)} rows, Passive: {len(passive)} rows -> {OUT_FILE}")


if __name__ == "__main__":
    main()
