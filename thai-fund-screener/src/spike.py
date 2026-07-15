"""Task 0 spike: hit real SEC API for a few funds and dump raw JSON so we can
see the true response schema before writing fetch_details.py / clean.py."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import SECClient

RAW_DIR = Path(__file__).parent.parent / "data" / "raw" / "spike"

SAMPLE_PROJ_IDS = ["M0001_2545", "M0002_2545", "M0003_2545"]

ENDPOINTS = {
    "amcs": ("/v2/fund/general-info/amcs", {"page_size": 5}),
    "profiles": ("/v2/fund/general-info/profiles", {"page_size": 5}),
    "fees": ("/v2/fund/general-info/mutual-fund-fees", {"page_size": 5}),
    "factsheet_benchmark": ("/v2/fund/factsheet/benchmarks", {"page_size": 5}),
    "factsheet_performance": ("/v2/fund/factsheet/performance", {"page_size": 5}),
}


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = SECClient()

    for name, (path, params) in ENDPOINTS.items():
        print(f"GET {path} params={params}")
        data = client.get(path, params=params)
        out_file = RAW_DIR / f"{name}.json"
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> saved {out_file} ({'null' if data is None else 'ok'})")

    print(f"Total requests: {client.request_count}")


if __name__ == "__main__":
    main()
