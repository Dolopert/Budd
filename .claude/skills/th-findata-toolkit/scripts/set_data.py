#!/usr/bin/env python3
"""
Thai Market (SET) Stock Data Fetcher
====================================
Fetch fundamentals, valuation metrics, financial statements, and price data for
stocks listed on the Stock Exchange of Thailand (SET / mai).

Two free data sources, no API key required:
  1. SET official public API  (www.set.or.th)  -> valuation snapshot, profile, price
  2. yfinance ({SYMBOL}.BK)                      -> financial statements, price history

Symbols are the plain SET ticker (e.g. DELTA, PTT, CPALL, AOT, KBANK). The ".BK"
suffix is added automatically for the yfinance fallback.

Usage:
    python set_data.py DELTA                      # Basic info + valuation snapshot
    python set_data.py DELTA --metrics            # Full valuation / fundamental metrics
    python set_data.py DELTA --price              # Latest price snapshot
    python set_data.py DELTA --financials         # Income statement, balance sheet, cash flow
    python set_data.py DELTA --history --period 1y  # OHLCV price history
    python set_data.py DELTA PTT CPALL --screen   # Screen several stocks against value filters
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common.utils import output_json, output_table, safe_div, safe_float, error_exit

SET_API_BASE = "https://www.set.or.th/api/set/stock"

# SET's public API expects browser-like headers, otherwise it returns 403/redirects.
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.set.or.th/en/market/product/stock/quote",
    "Accept-Language": "en-US,en;q=0.9,th;q=0.8",
}


# ---------------------------------------------------------------------------
# Low-level fetch helpers
# ---------------------------------------------------------------------------

def _set_get(symbol: str, path: str, params: dict | None = None):
    """GET a SET public-API endpoint and return parsed JSON (or None on failure)."""
    import requests

    url = f"{SET_API_BASE}/{symbol.upper()}/{path}"
    q = {"lang": "en"}
    if params:
        q.update(params)
    try:
        resp = requests.get(url, headers=_HEADERS, params=q, timeout=20)
        if resp.status_code == 200 and resp.text.strip():
            return resp.json()
        return {"_http_status": resp.status_code}
    except Exception as e:  # network, JSON, etc.
        return {"_error": str(e)}


def _yf_ticker(symbol: str):
    """Return a yfinance Ticker for the Thai symbol ({SYMBOL}.BK)."""
    import yfinance as yf

    sym = symbol.upper()
    if not sym.endswith(".BK"):
        sym = f"{sym}.BK"
    return yf.Ticker(sym)


# ---------------------------------------------------------------------------
# Public commands
# ---------------------------------------------------------------------------

def fetch_basic_info(symbols: list[str]) -> list[dict]:
    """Company profile + valuation snapshot from the SET API (yfinance fallback)."""
    results = []
    for sym in symbols:
        rec = {"symbol": sym.upper(), "source": "set.or.th"}
        profile = _set_get(sym, "company-profile/overview")
        highlight = _set_get(sym, "highlight-data")

        if isinstance(profile, dict) and profile and "_error" not in profile \
                and "_http_status" not in profile:
            rec.update({
                "name": profile.get("nameEN") or profile.get("name") or sym.upper(),
                "sector": profile.get("sectorName") or profile.get("sector"),
                "industry": profile.get("industryName") or profile.get("industry"),
                "market": profile.get("market"),
            })
        if isinstance(highlight, dict) and "_error" not in highlight \
                and "_http_status" not in highlight:
            rec.update({
                "currency": "THB",
                "market_cap": highlight.get("marketCap"),
                "pe": highlight.get("pe"),
                "pbv": highlight.get("pbv"),
                "dividend_yield_pct": highlight.get("dividendYield") or highlight.get("yield"),
            })

        # Fallback to yfinance if SET gave us nothing usable.
        if "name" not in rec and "market_cap" not in rec:
            rec = _basic_info_yf(sym)
        results.append(rec)
    return results


def _basic_info_yf(symbol: str) -> dict:
    """yfinance fallback for basic info."""
    try:
        info = _yf_ticker(symbol).info
        return {
            "symbol": symbol.upper(),
            "source": "yfinance",
            "name": info.get("longName") or info.get("shortName", symbol.upper()),
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "currency": info.get("currency", "THB"),
            "pe": info.get("trailingPE"),
            "pbv": info.get("priceToBook"),
            "dividend_yield_pct": (info.get("dividendYield") or 0) * 100 or None,
        }
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e)}


def fetch_metrics(symbol: str) -> dict:
    """
    Full fundamental / valuation metrics for a single SET stock.
    Combines the SET valuation snapshot with yfinance profitability & growth data.
    """
    out = {"symbol": symbol.upper(), "currency": "THB"}

    highlight = _set_get(symbol, "highlight-data")
    if isinstance(highlight, dict) and "_error" not in highlight \
            and "_http_status" not in highlight:
        out["valuation"] = {
            "market_cap": highlight.get("marketCap"),
            "pe": highlight.get("pe"),
            "pbv": highlight.get("pbv"),
            "dividend_yield_pct": highlight.get("dividendYield") or highlight.get("yield"),
            "eps": highlight.get("eps"),
            "book_value_per_share": highlight.get("bookValue"),
            "_source": "set.or.th",
        }

    # yfinance enriches profitability / leverage / growth (fields SET highlight lacks).
    try:
        info = _yf_ticker(symbol).info
        out["profitability"] = {
            "roe": _pct(info.get("returnOnEquity")),
            "roa": _pct(info.get("returnOnAssets")),
            "gross_margin": _pct(info.get("grossMargins")),
            "operating_margin": _pct(info.get("operatingMargins")),
            "net_margin": _pct(info.get("profitMargins")),
        }
        out["leverage"] = {
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
        }
        out["growth"] = {
            "revenue_growth_yoy": _pct(info.get("revenueGrowth")),
            "earnings_growth_yoy": _pct(info.get("earningsGrowth")),
        }
        # Fill valuation from yfinance if SET was unavailable.
        out.setdefault("valuation", {
            "market_cap": info.get("marketCap"),
            "pe": info.get("trailingPE"),
            "pbv": info.get("priceToBook"),
            "dividend_yield_pct": (info.get("dividendYield") or 0) * 100 or None,
            "eps": info.get("trailingEps"),
            "_source": "yfinance",
        })
        # Simple derived PEG for a quick hype check.
        pe = (out.get("valuation") or {}).get("pe")
        eg = info.get("earningsGrowth")
        if pe and eg and eg > 0:
            out["derived"] = {"peg": round(pe / (eg * 100), 2)}
    except Exception as e:
        out["_yfinance_error"] = str(e)

    return out


def fetch_price(symbol: str) -> dict:
    """Latest price snapshot from the SET API (yfinance fallback)."""
    price = _set_get(symbol, "price")
    if isinstance(price, dict) and "_error" not in price and "_http_status" not in price:
        price["symbol"] = symbol.upper()
        price["_source"] = "set.or.th"
        return price
    # Fallback
    try:
        hist = _yf_ticker(symbol).history(period="5d")
        if not hist.empty:
            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else last
            return {
                "symbol": symbol.upper(),
                "_source": "yfinance",
                "close": round(float(last["Close"]), 2),
                "change": round(float(last["Close"] - prev["Close"]), 2),
                "change_pct": round(float(safe_div(last["Close"] - prev["Close"], prev["Close"]) * 100), 2),
                "volume": int(last["Volume"]),
            }
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e)}
    return {"symbol": symbol.upper(), "error": "no price data"}


def fetch_financials(symbol: str) -> dict:
    """Income statement, balance sheet, cash flow via yfinance (known schema)."""
    try:
        t = _yf_ticker(symbol)
        out = {"symbol": symbol.upper(), "currency": "THB", "_source": "yfinance"}
        for label, df in (
            ("income_statement", t.financials),
            ("balance_sheet", t.balance_sheet),
            ("cash_flow", t.cashflow),
        ):
            if df is not None and not df.empty:
                out[label] = {
                    str(col.date()): {str(k): safe_float(v) for k, v in df[col].items()}
                    for col in df.columns
                }
            else:
                out[label] = {}
        return out
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e)}


def fetch_history(symbol: str, period: str = "1y") -> dict:
    """OHLCV price history via yfinance."""
    try:
        hist = _yf_ticker(symbol).history(period=period)
        if hist.empty:
            return {"symbol": symbol.upper(), "error": "no history"}
        rows = [
            {
                "date": str(idx.date()),
                "open": round(float(r["Open"]), 2),
                "high": round(float(r["High"]), 2),
                "low": round(float(r["Low"]), 2),
                "close": round(float(r["Close"]), 2),
                "volume": int(r["Volume"]),
            }
            for idx, r in hist.iterrows()
        ]
        return {"symbol": symbol.upper(), "period": period, "currency": "THB", "bars": rows}
    except Exception as e:
        return {"symbol": symbol.upper(), "error": str(e)}


def screen(symbols: list[str]) -> list[dict]:
    """
    Quick value screen. Flags stocks that pass simple fundamental filters:
      pe < 20, pbv < 3, dividend_yield >= 2%, roe >= 10%.
    Thresholds are intentionally generic — tune per sector.
    """
    rows = []
    for sym in symbols:
        m = fetch_metrics(sym)
        val = m.get("valuation", {}) or {}
        prof = m.get("profitability", {}) or {}
        pe = safe_float(val.get("pe"))
        pbv = safe_float(val.get("pbv"))
        dy = safe_float(val.get("dividend_yield_pct"))
        roe = safe_float(prof.get("roe"))
        passes = []
        if pe is not None and pe < 20:
            passes.append("PE<20")
        if pbv is not None and pbv < 3:
            passes.append("PBV<3")
        if dy is not None and dy >= 2:
            passes.append("Yield>=2%")
        if roe is not None and roe >= 10:
            passes.append("ROE>=10%")
        rows.append({
            "symbol": sym.upper(),
            "pe": pe, "pbv": pbv, "dividend_yield_pct": dy, "roe": roe,
            "filters_passed": passes,
            "score": len(passes),
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pct(v):
    """Convert a fraction (0.15) to a percentage (15.0); pass through None."""
    v = safe_float(v)
    return round(v * 100, 2) if v is not None else None


def main():
    p = argparse.ArgumentParser(description="SET (Thai market) stock data fetcher")
    p.add_argument("symbols", nargs="+", help="SET tickers, e.g. DELTA PTT CPALL")
    p.add_argument("--metrics", action="store_true", help="Full fundamental metrics (single symbol)")
    p.add_argument("--price", action="store_true", help="Latest price snapshot (single symbol)")
    p.add_argument("--financials", action="store_true", help="Financial statements (single symbol)")
    p.add_argument("--history", action="store_true", help="OHLCV price history (single symbol)")
    p.add_argument("--period", default="1y", help="History period (1mo,3mo,6mo,1y,2y,5y,max)")
    p.add_argument("--screen", action="store_true", help="Value screen across all symbols")
    args = p.parse_args()

    if args.screen:
        output_json(screen(args.symbols))
    elif args.metrics:
        output_json(fetch_metrics(args.symbols[0]))
    elif args.price:
        output_json(fetch_price(args.symbols[0]))
    elif args.financials:
        output_json(fetch_financials(args.symbols[0]))
    elif args.history:
        output_json(fetch_history(args.symbols[0], args.period))
    else:
        output_json(fetch_basic_info(args.symbols))


if __name__ == "__main__":
    main()
