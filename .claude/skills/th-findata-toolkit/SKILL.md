---
name: findata-toolkit-th
description: Financial data toolkit for Thai (SET) market analysis. Provides scripts to fetch live valuation metrics, company profiles, prices, financial statements, and price history for stocks on the Stock Exchange of Thailand (SET / mai). Uses the free SET public API plus yfinance ({SYMBOL}.BK) as fallback — no API keys required. Use when the user asks to analyze a Thai stock (e.g. DELTA, PTT, CPALL, AOT, KBANK), screen SET stocks, or needs live Thai market data to ground investment analysis.
license: Apache-2.0
---

# FinData Toolkit — Thai (SET) Market

A self-contained data toolkit providing live financial data for **Stock Exchange
of Thailand (SET / mai)** analysis. All data sources are **free** and require
**no API keys**. It complements the US and China FinSkills toolkits with
Thai-market coverage.

## Data sources

| Source | Used for | Notes |
|--------|----------|-------|
| **SET public API** (`www.set.or.th`) | valuation snapshot, company profile, latest price | Free, no key. Needs browser-like headers (handled in `set_data.py`). |
| **yfinance** (`{SYMBOL}.BK`) | financial statements, price history, profitability/growth enrichment, fallback | Free, no key. The `.BK` suffix is added automatically. |

> **Symbols** are the plain SET ticker with no suffix: `DELTA`, `PTT`, `CPALL`,
> `AOT`, `KBANK`, `SCB`, `BBL`, `ADVANC`, `GULF`, `PTTEP`, … The toolkit adds
> `.BK` internally for the yfinance calls.

## Setup

Install dependencies (one-time):

```bash
pip install -r requirements.txt
```

## Available tools

All scripts live in `scripts/`. Run from the skill root directory.

### Stock data (`scripts/set_data.py`)

| Command | Purpose |
|---------|---------|
| `python scripts/set_data.py DELTA` | Basic info + valuation snapshot (name, sector, market cap, P/E, P/BV, yield) |
| `python scripts/set_data.py DELTA --metrics` | Full metrics — valuation, profitability (ROE/ROA/margins), leverage, growth, derived PEG |
| `python scripts/set_data.py DELTA --price` | Latest price snapshot |
| `python scripts/set_data.py DELTA --financials` | Income statement, balance sheet, cash flow |
| `python scripts/set_data.py DELTA --history --period 1y` | OHLCV price history |
| `python scripts/set_data.py DELTA PTT CPALL --screen` | Value screen across several symbols (PE<20, PBV<3, Yield≥2%, ROE≥10%) |

Every command prints JSON to stdout, so you can pipe it straight into analysis.

## How to use in analysis

1. Fetch the data you need with the commands above.
2. Feed the JSON into the FinSkills analysis skills — the methodology is
   market-agnostic and works on Thai fundamentals:
   - **`us-financial-statement-analyzer`** — forensic single-company review
     (DuPont, margins, leverage, earnings quality) on the `--financials` +
     `--metrics` output.
   - **`us-tech-hype-vs-fundamentals`** — valuation-vs-growth check; ideal for
     high-multiple SET names like DELTA where price runs ahead of fundamentals.
   - **`us-undervalued-stock-screener`** / **`us-quant-factor-screener`** —
     apply the value / factor framework to `--screen` output.
   - **`us-dividend-aristocrat-calculator`** — income analysis on the
     dividend-yield and payout fields.

   Skip skills that depend on US-only data (SEC EDGAR insider filings, FRED
   macro): `us-insider-trading-analyzer`, `us-event-driven-detector`,
   `us-sector-rotation-detector`, `us-esg-screener` — those have no Thai data
   source.

## Limitations

- The SET public API is undocumented and its response schema can change; the
  toolkit degrades gracefully to yfinance when a field is missing.
- yfinance fundamentals for SET stocks are typically less deep than for US
  names (fewer historical periods, occasional gaps). Cross-check critical
  figures against the company's official filings on
  [set.or.th](https://www.set.or.th) or [SETSMART](https://www.setsmart.com).
- Reported currency is **THB** unless a source overrides it.
- Requires outbound network access to `www.set.or.th` and Yahoo Finance. In
  restricted/sandboxed environments where these hosts are blocked, run the
  toolkit on a machine with open network access.
