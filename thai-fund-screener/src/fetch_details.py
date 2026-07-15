"""Task 3: for every distinct proj_id, fetch specifications/fees/benchmark/
performance and cache raw JSON per fund. Resumable via checkpoint.json —
re-running skips proj_ids already recorded as done or no_data."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import SECClient

DATA_DIR = Path(__file__).parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
ALL_FUNDS_FILE = RAW_DIR / "all_funds.json"
CHECKPOINT_FILE = DATA_DIR / "checkpoint.json"

ENDPOINTS = {
    "specifications": "/v2/fund/general-info/specifications",
    "fees": "/v2/fund/general-info/mutual-fund-fees",
    "benchmark": "/v2/fund/factsheet/benchmarks",
    "performance": "/v2/fund/factsheet/performance",
}


def load_checkpoint() -> dict:
    if CHECKPOINT_FILE.exists():
        return json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
    return {}


def save_checkpoint(checkpoint: dict):
    CHECKPOINT_FILE.write_text(json.dumps(checkpoint, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_one(client: SECClient, proj_id: str) -> dict:
    result = {}
    for key, path in ENDPOINTS.items():
        data = client.get(path, params={"proj_id": proj_id, "page_size": 100})
        result[key] = data.get("data") if isinstance(data, dict) else data
    return result


def main():
    if not ALL_FUNDS_FILE.exists():
        raise SystemExit("Run fetch_master.py first to generate data/raw/all_funds.json")

    funds = json.loads(ALL_FUNDS_FILE.read_text(encoding="utf-8"))
    proj_ids = sorted({f["proj_id"] for f in funds if f.get("proj_id")})

    checkpoint = load_checkpoint()
    client = SECClient()

    for i, proj_id in enumerate(proj_ids, 1):
        if checkpoint.get(proj_id) in ("done", "no_data"):
            continue
        try:
            detail = fetch_one(client, proj_id)
            has_any = any(v for v in detail.values())
            out_file = RAW_DIR / f"{proj_id}.json"
            out_file.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
            checkpoint[proj_id] = "done" if has_any else "no_data"
        except Exception as e:
            print(f"[{i}/{len(proj_ids)}] FAILED {proj_id}: {e}")
            checkpoint[proj_id] = "error"

        if i % 20 == 0:
            save_checkpoint(checkpoint)
            print(f"[{i}/{len(proj_ids)}] checkpointed, requests={client.request_count}")

    save_checkpoint(checkpoint)
    print(f"Done. {len(proj_ids)} funds processed, requests={client.request_count}")


if __name__ == "__main__":
    main()
