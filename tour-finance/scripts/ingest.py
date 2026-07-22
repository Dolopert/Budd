#!/usr/bin/env python3
"""
ingest.py — รับไฟล์งบ SET เป็นชุด (zip/โฟลเดอร์) แล้วจัดเก็บ + คำนวณอัตโนมัติ

ทำ 4 ขั้นในคำสั่งเดียว (ออกแบบให้ประหยัด token — พ่นผลสั้นๆ):
  1. แตก zip / หาไฟล์ FINANCIAL_STATEMENTS.*
  2. detect บริษัท (ticker) + ปี + ไตรมาส เอง
  3. คัดลอกเข้า data/raw/<TICKER>/<ปี>/<tag>_FS.<ext>
  4. สแกน data/raw ทั้งหมด -> คำนวณ 7 ตัวชี้วัด (รวม Q4 = FY-Q1-Q2-Q3)
     -> เขียน output/metrics_all.csv (idempotent สะสมข้ามรอบ)

ใช้:
    python3 ingest.py <zip|dir|xls ...>     # นำเข้าไฟล์ใหม่ + rebuild
    python3 ingest.py --rebuild             # rebuild จาก data/raw ที่มีอยู่ (ไม่ import ใหม่)
"""
import os
import re
import sys
import csv
import glob
import shutil
import zipfile
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import extract_set as E

HERE = os.path.dirname(__file__)
RAW = os.path.normpath(os.path.join(HERE, "..", "data", "raw"))
OUT = os.path.normpath(os.path.join(HERE, "..", "output"))
CSV_PATH = os.path.join(OUT, "metrics_all.csv")
# รับทุกไฟล์ spreadsheet (บางงบรายปีใช้ชื่อรหัส SET เช่น 102000_t_25690223.XLSX)
STMT_RE = re.compile(r"\.(xls|xlsx|xlsm)$", re.I)


def is_english_copy(path):
    """ข้ามไฟล์เวอร์ชันภาษาอังกฤษ (รหัส SET '_e_') — ใช้ฉบับไทย '_t_' เป็นหลัก"""
    return bool(re.search(r"_e_\d", os.path.basename(path)))

CSV_COLS = ["ticker", "year", "quarter", "is_annual", "revenue", "cogs", "net_profit",
            "ar_end", "inv_end", "ap_end", "total_assets_end", "total_equity_end",
            "NPM", "ROA", "ROE", "DSO", "DIO", "DPO", "CCC", "balance_ok", "source"]


def find_statements(paths):
    """คืน list ของไฟล์งบ (แตก zip ลงชั่วคราวถ้าจำเป็น)"""
    out = []
    tmp = tempfile.mkdtemp(prefix="ingest_")
    def walk(p):
        if os.path.isdir(p):
            for entry in sorted(os.listdir(p)):
                walk(os.path.join(p, entry))
        elif p.lower().endswith(".zip"):            # รองรับ zip ซ้อน zip (recurse)
            d = tempfile.mkdtemp(dir=tmp)
            with zipfile.ZipFile(p) as z:
                z.extractall(d)
            walk(d)
        elif STMT_RE.search(os.path.basename(p)) and not is_english_copy(p):
            out.append(p)
    for p in paths:
        walk(p)
    return out


def import_file(path):
    """detect + คัดลอกไฟล์งบเข้า data/raw; คืน (ticker, year, tag) หรือ error"""
    try:
        grids = E.open_book(path)
        pl = E.get_pl_sheet(grids)
        ticker = E.detect_company(pl)
        if not ticker:
            return None, "ไม่รู้จักบริษัท (เพิ่มคีย์เวิร์ดใน TICKER_KEYWORDS)"
        q, year, is_annual = E.detect_period(pl)
    except Exception as e:                          # กันไฟล์เดียวล้มทั้ง batch
        return None, str(e)
    tag = "FY" if is_annual else q
    ext = path.lower().rsplit(".", 1)[-1]
    dst_dir = os.path.join(RAW, ticker, str(year))
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, f"{tag}_FS.{ext}")
    shutil.copy(path, dst)
    return (ticker, year, tag), None


def rebuild():
    """สแกน data/raw ทั้งหมด -> คำนวณ -> เขียน metrics_all.csv; คืนสรุปต่อ (ticker,ปี)"""
    files = []
    for ext in ("xls", "xlsx", "xlsm", "XLS", "XLSX"):
        files += glob.glob(os.path.join(RAW, "*", "*", f"*.{ext}"))
    groups = {}                                    # (ticker,year) -> {tag: rec}
    errors = []
    for f in sorted(set(files)):
        try:
            rec = E.extract_file(f)
        except Exception as e:
            errors.append(f"{os.path.relpath(f, RAW)}: {e}")
            continue
        tk = rec["ticker"] or os.path.basename(os.path.dirname(os.path.dirname(f)))
        key = (tk, rec["year"])
        tag = "FY" if rec["is_annual"] else rec["quarter"]
        groups.setdefault(key, {})[tag] = rec

    rows, summary = [], []
    for (tk, yr), by_tag in sorted(groups.items()):
        got = []
        for rec, m in E.compute_group(by_tag):     # chain ยอดงบดุลไตรมาสก่อนหน้า
            rows.append({
                "ticker": tk, "year": yr, "quarter": rec["quarter"], "is_annual": False,
                "revenue": rec["total_revenue"], "cogs": rec["cogs"],
                "net_profit": rec["net_profit_total"],
                "ar_end": rec["trade_receivables_end"], "inv_end": rec["inventory_end"],
                "ap_end": rec["trade_payables_end"],
                "total_assets_end": rec["total_assets_end"],
                "total_equity_end": rec["total_equity_end"],
                **{k: m[k] for k in ("NPM", "ROA", "ROE", "DSO", "DIO", "DPO", "CCC")},
                "balance_ok": rec.get("balance_ok", ""), "source": rec.get("file", ""),
            })
            got.append(rec["quarter"])
        has_fy = "FY" in by_tag
        summary.append((tk, yr, got, has_fy))

    os.makedirs(OUT, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for row in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v)
                        for k, v in row.items()})
    return summary, errors, len(rows)


def main(argv):
    imported = 0
    if argv and argv[0] != "--rebuild":
        stmts = find_statements(argv)
        if not stmts:
            print("ไม่พบไฟล์ FINANCIAL_STATEMENTS ใน args")
            return 1
        for s in stmts:
            info, err = import_file(s)
            if err:
                print(f"✗ {os.path.basename(s)}: {err}")
            else:
                imported += 1
        print(f"นำเข้า {imported} ไฟล์ -> data/raw")
    elif not argv:
        print(__doc__)
        return 1

    summary, errors, nrows = rebuild()
    print(f"\n=== rebuild: {nrows} แถว -> output/metrics_all.csv ===")
    for tk, yr, got, has_fy in summary:
        fy = " +FY" if has_fy else ""
        miss = "" if len(got) == 4 else f"  (ได้ {'/'.join(got) or '-'})"
        mark = "✓" if len(got) == 4 else "…"
        print(f"  {mark} {tk} {yr}: {len(got)}/4 ไตรมาส{fy}{miss}")
    for e in errors:
        print(f"  ✗ {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
