# Thai Fund Screener (SEC Open Data)

Pulls every Thai mutual fund from the [SEC Open Data API](https://api-portal.sec.or.th/),
classifies each as Active or Passive, ranks them, and exports a Top 25 + Top 25
comparison spreadsheet. See [PLAN.md](PLAN.md) for the full design and task log.

## Requirements

- Python 3.11+
- A SEC Open Data API key (register at https://api-portal.sec.or.th/, free)
- **Network access to `api.sec.or.th`** — note this cannot be run from the
  Claude Code web sandbox, whose egress policy blocks that host. Run it on your
  own machine or any environment with open outbound HTTPS.

## Setup

```bash
cd thai-fund-screener
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# provide your key (either export it, or drop it in .env)
echo "SEC_API_KEY=your_primary_key_here" > .env
```

`.env` is git-ignored — never commit your key.

## Run everything

```bash
.venv/bin/python run_all.py
```

This runs all stages in order. Output lands in `output/top25_comparison.xlsx`
(two sheets: Active, Passive).

The slow stage is `fetch_details` (~2,000 funds at ~5 req/s). It is **resumable**:
if it dies, just run again and it continues from `data/checkpoint.json`.

### Resume / run a single stage

```bash
.venv/bin/python run_all.py --from clean        # skip the fetch stages
.venv/bin/python run_all.py --skip-spike        # skip the Task 0 sample dump
.venv/bin/python src/classify.py                # run one stage directly
```

## Pipeline stages

| Stage | Script | Output |
|-------|--------|--------|
| Task 0 | `src/spike.py` | `data/raw/spike/*.json` — sample raw responses |
| Task 1 | `src/client.py` | SEC API client (auth, retry, rate limit) |
| Task 2 | `src/fetch_master.py` | `data/raw/all_funds.json` |
| Task 3 | `src/fetch_details.py` | `data/raw/{proj_id}.json` + `data/checkpoint.json` |
| Task 4 | `src/clean.py` | `data/processed/funds_clean.csv` |
| Task 5 | `src/classify.py` | `data/processed/funds_classified.csv` |
| Task 6 | `src/rank.py` | `data/processed/funds_ranked.csv` |
| Task 7 | `src/export.py` | `output/top25_comparison.xlsx` |

## ⚠️ One schema still needs live confirmation

The `factsheet/performance` response schema was not confirmable offline. After
your first real run, open `data/raw/spike/factsheet_performance.json` and check
the actual field names for 1y/3y/5y return and Sharpe ratio. If they differ from
the guesses in `src/rank.py`, update `PERFORMANCE_KEY_CANDIDATES` there. Every
other endpoint's fields are confirmed from the public SEC API spec.
