#!/usr/bin/env python3
"""
compare.py — เทียบตัวเลขที่บริษัทรายงานในงบ กับที่เราคำนวณตามสูตร

ตรวจสอบ 2 ทาง:
  1. EPS: กำไรต่อหุ้นที่บริษัทรายงาน  vs  กำไรส่วนบริษัทแม่ ÷ จำนวนหุ้น (เราคำนวณ)
     -> ตรวจการดึงกำไรสุทธิอย่างอิสระ (EPS เป็นตัวเลขที่ผ่านการสอบทาน)
  2. อัตราส่วนรายปี (annualized) แบบมาตรฐานสำหรับเทียบกับเว็บ (settrade/shareinvestor)
     -> NPM, ROA, ROE (ทั้งฐานกำไรรวม และกำไรส่วนบริษัทแม่)

ใช้:
    python3 compare.py            # เทียบทุกบริษัท-ปีใน data/raw
"""
import os
import re
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
import extract_set as E

RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))


def norm(v):
    return re.sub(r"\s+", " ", str(v).strip())


def find_eps(pl, col, row_end):
    """กำไรต่อหุ้นขั้นพื้นฐานที่รายงาน (บาท/หุ้น) — ค่าเล็ก ไม่คูณหน่วย"""
    best = None
    for r in range(row_end):
        lab = norm(E.row_label(pl, r, col))
        if "ต่อหุ้น" not in lab:
            continue
        v = pl.cell_value(r, col)
        if isinstance(v, (int, float)) and v != 0 and abs(v) < 1000:
            # ชอบบรรทัด 'ขั้นพื้นฐาน' ถ้ามี; มิฉะนั้นเอาตัวแรก
            if "พื้นฐาน" in lab or "ส่วนที่เป็นของผู้ถือหุ้น" in lab:
                return v
            if best is None:
                best = v
    return best


def find_shares(pl, col, row_end):
    """จำนวนหุ้นสามัญถัวเฉลี่ยถ่วงน้ำหนัก -> จำนวนหุ้น (แปลงจากพัน/ล้านหุ้น)"""
    for r in range(row_end):
        lab = norm(E.row_label(pl, r, col))
        if "จำนวนหุ้นสามัญ" in lab and "ถัวเฉลี่ย" in lab:
            v = pl.cell_value(r, col)
            if not isinstance(v, (int, float)) or v == 0:
                continue
            if "พันหุ้น" in lab:
                return v * 1_000
            if "ล้านหุ้น" in lab:
                return v * 1_000_000
            return v
    return None


def extract_reported(path):
    """ดึง EPS + จำนวนหุ้น ที่รายงานในงบ (นอกเหนือจาก extract_file ปกติ)"""
    grids = E.open_book(path)
    pl = E.get_pl_sheet(grids)
    _, year, _ = E.detect_period(pl)
    col = E.pl_current_consol_col(pl, year)
    end = E.pl_first_statement_end(pl, col)
    return {"eps_reported": find_eps(pl, col, end), "shares": find_shares(pl, col, end)}


def load():
    files = []
    for ext in ("xls", "xlsx", "xlsm", "XLS", "XLSX"):
        files += glob.glob(os.path.join(RAW, "*", "*", f"*.{ext}"))
    groups = {}
    for f in sorted(set(files)):
        try:
            rec = E.extract_file(f)
            rec.update(extract_reported(f))
        except E.ExtractError as e:
            print(f"  ✗ {os.path.relpath(f, RAW)}: {e}")
            continue
        key = (rec["ticker"], rec["year"])
        tag = "FY" if rec["is_annual"] else rec["quarter"]
        groups.setdefault(key, {})[tag] = rec
    return groups


def main():
    groups = load()

    print("=" * 82)
    print("1) ตรวจกำไรสุทธิ: กำไรรวม (ที่เราใช้)  vs  กำไรส่วนแม่ + ส่วนได้เสียส่วนน้อย (จากงบ)")
    print("=" * 82)
    print(f"{'บริษัท/งวด':>12} {'กำไรรวม':>10} {'ส่วนแม่':>10} {'ส่วนน้อย':>10} {'แม่+น้อย':>10} {'EPS งบ':>8}  ")
    for (tk, yr), bt in sorted(groups.items()):
        for t in ("Q1", "Q2", "Q3", "FY"):
            if t not in bt:
                continue
            r = bt[t]
            npt = r.get("net_profit_total")
            npp = r.get("net_profit_parent")
            npm_ = r.get("net_profit_minority")
            summ = (npp + npm_) if (npp is not None and npm_ is not None) else None
            epsr = r.get("eps_reported")
            flag = ""
            if summ is not None and npt is not None and abs(summ - npt) > max(0.5, abs(npt) * 0.01):
                flag = " ⚠ ไม่ตรง"
            f = lambda x: f"{x:.1f}" if x is not None else "—"
            print(f"{tk+'/'+t:>12} {f(npt):>10} {f(npp):>10} {f(npm_):>10} {f(summ):>10} "
                  f"{(f'{epsr:.4f}' if epsr is not None else '—'):>8}{flag}")

    print()
    print("=" * 78)
    print("2) อัตราส่วนรายปี (annualized) สำหรับเทียบกับเว็บ — FY2568")
    print("=" * 78)
    print(f"{'บริษัท':>8} {'NPM':>7} {'ROA':>7} {'ROE(รวม)':>9} {'ROE(แม่)':>9} {'GM':>7}  หมายเหตุ")
    for (tk, yr), bt in sorted(groups.items()):
        if "FY" not in bt or "Q1" not in bt:
            continue
        fy, q1 = bt["FY"], bt["Q1"]
        rev, cogs = fy["total_revenue"], fy["cogs"]
        npt, npp = fy["net_profit_total"], fy.get("net_profit_parent")
        ta = (q1["total_assets_begin"] + fy["total_assets_end"]) / 2
        te = (q1["total_equity_begin"] + fy["total_equity_end"]) / 2
        npm = npt / rev if rev else None
        roa = npt / ta if ta else None
        roe_t = npt / te if te else None
        roe_p = npp / te if (npp is not None and te) else None
        gm = (rev - cogs) / rev if rev else None
        note = "กำไรแม่≠รวม (minority สูง)" if (npp is not None and abs(npp - npt) > abs(npt) * 0.1) else ""
        f = lambda x: f"{x*100:.1f}%" if x is not None else "—"
        print(f"{tk:>8} {f(npm):>7} {f(roa):>7} {f(roe_t):>9} {f(roe_p):>9} {f(gm):>7}  {note}")

    print("\nหมายเหตุ: ROA/ROE เป็นฐานรายปี (กำไรทั้งปี ÷ ค่าเฉลี่ยสินทรัพย์/ทุน ต้นปี-ปลายปี)")
    print("เว็บส่วนใหญ่ (settrade) รายงาน ROE ฐานกำไรส่วนบริษัทแม่ -> เทียบคอลัมน์ ROE(แม่)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
