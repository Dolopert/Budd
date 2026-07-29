#!/usr/bin/env python3
"""
trace_dump.py — ดัมพ์ "การรันแต่ละสูตร" (formula trace) ต่อจุดข้อมูล

ใช้ extract_file จริง + ทำ chaining ซ้ำเหมือน compute_group แต่เก็บค่ากลางทุกตัว
(ยอดต้น/ปลาย/เฉลี่ยของงบดุลที่ chain แล้ว + flow + การแทนค่าในสูตร 7 ตัวชี้วัด)
-> เขียน output/formula_trace.json (ให้ artifact แท็บใหม่ใช้แสดง)

cross-check ทุกค่ากับ output/metrics_all.csv — ถ้าเพี้ยนเกิน 0.05 จะ print เตือน

ใช้: python scripts/trace_dump.py
"""
import os, sys, csv, glob, json

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract_set as E

RAW = os.path.normpath(os.path.join(HERE, "..", "data", "raw"))
OUT = os.path.normpath(os.path.join(HERE, "..", "output"))
BS = E.BS_ITEMS   # trade_receivables, inventory, trade_payables, total_assets, total_equity


def load_metrics_csv():
    """(ticker,year,quarter) -> row dict (สำหรับ rev_low + cross-check)"""
    idx = {}
    p = os.path.join(OUT, "metrics_all.csv")
    with open(p, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            idx[(row["ticker"], int(row["year"]), row["quarter"])] = row
    return idx


def build_seq(by_tag):
    """สร้างลำดับไตรมาสเหมือน compute_group (de-cumulate / derive Q4)"""
    if E._cumulative_year(by_tag):
        return E._decumulate(by_tag)
    seq = [by_tag[t] for t in ("Q1", "Q2", "Q3") if t in by_tag]
    if "Q4" in by_tag:
        seq.append(by_tag["Q4"])
    else:
        q4 = E.derive_q4(by_tag)
        if q4:
            seq.append(q4)
    return seq


def main():
    files = []
    for ext in ("xls", "xlsx", "xlsm", "XLS", "XLSX"):
        files += glob.glob(os.path.join(RAW, "*", "*", f"*.{ext}"))
    groups = {}
    for f in sorted(set(files)):
        try:
            rec = E.extract_file(f)
        except Exception as e:
            print(f"  skip {os.path.relpath(f, RAW)}: {e}")
            continue
        tk = rec["ticker"] or os.path.basename(os.path.dirname(os.path.dirname(f)))
        groups.setdefault((tk, rec["year"]), {})[
            "FY" if rec["is_annual"] else rec["quarter"]] = rec

    mcsv = load_metrics_csv()
    trace, mism = [], 0
    for (tk, yr), by_tag in sorted(groups.items()):
        seq = build_seq(by_tag)
        if not seq:
            continue
        prev = {it: seq[0].get(it + "_begin") for it in BS}
        for rec in seq:
            q = rec["quarter"]
            cur = {it: rec.get(it + "_end") for it in BS}
            avg = {it: E._avg(prev[it], cur[it]) for it in BS}
            days = E.days_for(q)
            np_, rev, cogs = rec["net_profit_total"], rec["total_revenue"], rec["cogs"]
            m = E.metrics(np_, rev, cogs, avg["trade_receivables"], avg["inventory"],
                          avg["trade_payables"], avg["total_assets"], avg["total_equity"], days)

            def r2(x):
                return round(x, 2) if isinstance(x, (int, float)) else None

            entry = {
                "ticker": tk, "year": yr, "quarter": q, "days": days,
                "seed": (q == seq[0]["quarter"]),  # Q1 ใช้ยอด 'ต้นปี' เป็นต้นงวด
                "rev": r2(rev), "cogs": r2(cogs), "np": r2(np_),
                # ยอดต้น(chain)/ปลาย/เฉลี่ย ของ 5 รายการงบดุล
                "bs": {it: {"beg": r2(prev[it]), "end": r2(cur[it]), "avg": r2(avg[it])}
                       for it in BS},
                # ผลแต่ละสูตร (สัดส่วน + วัน + %)
                "out": {k: (round(m[k], 4) if isinstance(m[k], float) else None)
                        for k in ("NPM", "ROA", "ROE", "DSO", "DIO", "DPO", "CCC")},
            }
            # rev_low flag + ค่าที่เก็บจริงใน metrics_all.csv (สำหรับคอลัมน์เทียบ)
            ref = mcsv.get((tk, yr, q))
            entry["rev_low"] = 1 if (ref and ref.get("rev_low") == "Y") else 0
            entry["ref"] = {}
            if ref:
                for k in ("NPM", "ROA", "ROE", "DSO", "DIO", "DPO", "CCC"):
                    try:
                        entry["ref"][k] = round(float(ref[k]), 4)
                    except (TypeError, ValueError, KeyError):
                        entry["ref"][k] = None

            # cross-check กับ CSV
            if ref:
                for k in ("NPM", "ROA", "ROE", "DSO", "DIO", "DPO", "CCC"):
                    a, b = m[k], ref.get(k)
                    try:
                        b = float(b)
                    except (TypeError, ValueError):
                        b = None
                    if a is not None and b is not None and abs(a - b) > 0.05:
                        print(f"  MISMATCH {tk} {yr} {q} {k}: trace={a:.4f} csv={b:.4f}")
                        mism += 1
            trace.append(entry)
            prev = cur

    outp = os.path.join(OUT, "formula_trace.json")
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, separators=(",", ":"))
    print(f"\nwrote {len(trace)} points -> {os.path.relpath(outp)}  | mismatches: {mism}")


if __name__ == "__main__":
    main()
