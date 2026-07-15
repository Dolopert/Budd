"""Task 2: pull the full fund profile list (all share classes) from SEC and
write data/raw/all_funds.json."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from client import SECClient

RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
OUT_FILE = RAW_DIR / "all_funds.json"


def fetch_all_profiles(client: SECClient) -> list[dict]:
    funds = []
    cursor = None
    while True:
        params = {"page_size": 100}
        if cursor:
            params["next_cursor"] = cursor
        page = client.get("/v2/fund/general-info/profiles", params=params)
        if not page:
            break
        items = page.get("data") if isinstance(page, dict) else page
        if not items:
            break
        funds.extend(items)
        cursor = page.get("next_cursor") if isinstance(page, dict) else None
        if not cursor:
            break
    return funds


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    client = SECClient()
    funds = fetch_all_profiles(client)
    OUT_FILE.write_text(json.dumps(funds, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Fetched {len(funds)} fund/share-class records -> {OUT_FILE}")
    print(f"Total requests: {client.request_count}")


if __name__ == "__main__":
    main()
