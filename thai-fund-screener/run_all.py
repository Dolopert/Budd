"""One-shot runner for the full Thai Fund Screener pipeline.

Usage:
    export SEC_API_KEY=xxxx      # or put it in .env
    python run_all.py            # runs every stage in order
    python run_all.py --from clean   # resume from a given stage

Stages run in dependency order. fetch_details is the slow, resumable one;
if it dies you can just re-run and it picks up from checkpoint.json.
"""
import argparse
import runpy
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"

STAGES = [
    ("spike", "src/spike.py"),                # Task 0: dump sample raw JSON
    ("fetch_master", "src/fetch_master.py"),  # Task 2: all_funds.json
    ("fetch_details", "src/fetch_details.py"),# Task 3: per-fund raw JSON (slow, resumable)
    ("clean", "src/clean.py"),                # Task 4
    ("classify", "src/classify.py"),          # Task 5
    ("rank", "src/rank.py"),                  # Task 6
    ("export", "src/export.py"),              # Task 7
]


def load_dotenv():
    env_file = Path(__file__).parent / ".env"
    if not env_file.exists():
        return
    import os
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="start", default="spike",
                        help="stage name to start from: " + ", ".join(s for s, _ in STAGES))
    parser.add_argument("--skip-spike", action="store_true",
                        help="skip the Task 0 sample dump")
    args = parser.parse_args()

    load_dotenv()

    stage_names = [s for s, _ in STAGES]
    if args.start not in stage_names:
        sys.exit(f"Unknown stage '{args.start}'. Choose from: {', '.join(stage_names)}")

    start_idx = stage_names.index(args.start)
    for name, script in STAGES[start_idx:]:
        if name == "spike" and args.skip_spike:
            continue
        print(f"\n{'=' * 60}\n>>> {name}  ({script})\n{'=' * 60}")
        runpy.run_path(str(Path(__file__).parent / script), run_name="__main__")


if __name__ == "__main__":
    main()
