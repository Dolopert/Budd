"""Task 4: turn raw per-fund JSON into one clean row per fund (share classes
merged), dropping closed/suspended funds."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
ALL_FUNDS_FILE = RAW_DIR / "all_funds.json"
PROCESSED_DIR = DATA_DIR / "processed"
OUT_FILE = PROCESSED_DIR / "funds_clean.csv"

CLOSED_STATUSES = {"ยกเลิกกองทุน", "ปิดกองทุน", "เลิกโครงการ", "closed", "terminated"}

# preference order for which share class represents the fund when several exist
CLASS_PRIORITY = ["-A", "-D", "", "-SSF", "-RMF"]


def pick_primary_class(rows: list[dict]) -> dict:
    def rank(row):
        name = (row.get("fund_class_name") or "").upper()
        for i, suffix in enumerate(CLASS_PRIORITY):
            if suffix and name.endswith(suffix.upper()):
                return i
        return len(CLASS_PRIORITY)

    return sorted(rows, key=rank)[0]


def load_detail(proj_id: str) -> dict:
    f = RAW_DIR / f"{proj_id}.json"
    if not f.exists():
        return {}
    return json.loads(f.read_text(encoding="utf-8"))


def main():
    if not ALL_FUNDS_FILE.exists():
        raise SystemExit("Run fetch_master.py first")

    all_funds = json.loads(ALL_FUNDS_FILE.read_text(encoding="utf-8"))

    by_proj = {}
    for row in all_funds:
        proj_id = row.get("proj_id")
        if not proj_id:
            continue
        by_proj.setdefault(proj_id, []).append(row)

    records = []
    for proj_id, rows in by_proj.items():
        primary = pick_primary_class(rows)
        status = (primary.get("fund_status") or "").strip()
        if status.lower() in CLOSED_STATUSES:
            continue

        detail = load_detail(proj_id)
        fees = detail.get("fees") or []
        benchmark = detail.get("benchmark") or []
        performance = detail.get("performance") or []
        specifications = detail.get("specifications") or []
        policy_desc = " ".join(
            str(s.get("spec_desc", "")) for s in specifications if s.get("spec_desc")
        )

        records.append(
            {
                "proj_id": proj_id,
                "proj_name_th": primary.get("proj_name_th"),
                "proj_name_en": primary.get("proj_name_en"),
                "comp_name_th": primary.get("comp_name_th"),
                "fund_status": status,
                "fund_class_name": primary.get("fund_class_name"),
                "n_share_classes": len(rows),
                "policy_desc": policy_desc,
                "fees_raw": fees,
                "benchmark_raw": benchmark,
                "performance_raw": performance,
            }
        )

    df = pd.DataFrame.from_records(records)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Clean funds: {len(df)} (from {len(by_proj)} distinct proj_id) -> {OUT_FILE}")


if __name__ == "__main__":
    main()
