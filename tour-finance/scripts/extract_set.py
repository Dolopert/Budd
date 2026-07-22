#!/usr/bin/env python3
"""
extract_set.py — ดึงข้อมูลงบการเงินจากไฟล์ SET (.xls) แบบ config-driven

รับไฟล์ .xls ที่ตลาดหลักทรัพย์เผยแพร่ (ชีต BS / PL / CF) แล้ว:
  1. ตรวจหน่วยจาก header อัตโนมัติ (บาท / พันบาท / ล้านบาท) -> normalize เป็นล้านบาท
  2. ตรวจงวด (ไตรมาส/รายปี) + ปี จากหัวข้องบ
  3. เลือกคอลัมน์ "งบการเงินรวม + งวดปัจจุบัน" อัตโนมัติ
  4. map ชื่อรายการผ่าน mapping/line_items.yml (fail-loud ถ้าหา required ไม่เจอ)
  5. ตรวจ balance check: รวมสินทรัพย์ = รวมหนี้สิน + รวมส่วนของผู้ถือหุ้น

ใช้:
    python3 extract_set.py <ไฟล์.xls> [<ไฟล์.xls> ...]      # ดึง + คำนวณ 7 ตัวชี้วัด
    python3 extract_set.py --dir <โฟลเดอร์บริษัท/ปี>          # ดึงทุกไฟล์ในโฟลเดอร์

7 ตัวชี้วัด (คำนวณจาก PL + BS ล้วน ไม่ต้องใช้ MD&A):
    NPM, ROA, ROE, DSO, DIO, DPO, CCC
"""
import os
import re
import sys
import glob
import xlrd
import yaml

MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "mapping", "line_items.yml")
DAYS = {"Q1": 90, "Q2": 91, "Q3": 92, "Q4": 92}
THAI_MONTH_Q = {"มีนาคม": "Q1", "มิถุนายน": "Q2", "กันยายน": "Q3", "ธันวาคม": "Q4"}


class ExtractError(Exception):
    pass


def load_map():
    with open(MAP_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def norm(s):
    """normalize label: strip + ยุบช่องว่างซ้ำ"""
    return re.sub(r"\s+", " ", str(s).strip())


def nospace(s):
    """ตัดช่องว่างทั้งหมด สำหรับเทียบ label (บาง label ใส่เว้นวรรคในวงเล็บ)"""
    return re.sub(r"\s+", "", str(s).strip())


# ---------- sheet lookup (ทนต่อชื่อชีตที่มีช่องว่างต่อท้าย เช่น 'PL ') ----------
def get_sheet(wb, target):
    for sh in wb.sheets():
        if norm(sh.name).upper() == target.upper():
            return sh
    raise ExtractError(f"ไม่พบชีต '{target}' (มีชีต: {wb.sheet_names()})")


# ---------- unit detection ----------
def detect_unit_divisor(sheet):
    """คืนตัวหารเพื่อแปลงค่าในงบ -> ล้านบาท"""
    for r in range(min(sheet.nrows, 10)):
        for c in range(sheet.ncols):
            t = norm(sheet.cell_value(r, c))
            if "หน่วย" in t or "บาท" in t:
                if "พันบาท" in t:
                    return 1_000.0
                if "ล้านบาท" in t:
                    return 1.0
                if "บาท" in t:
                    return 1_000_000.0
    raise ExtractError("ตรวจหน่วยไม่ได้ (ไม่พบ 'หน่วย ... บาท' ใน header)")


# ---------- period detection ----------
def detect_period(pl_sheet):
    """คืน (quarter_label, year_be, is_annual) จากหัวข้องบกำไรขาดทุน"""
    for r in range(min(pl_sheet.nrows, 12)):
        for c in range(pl_sheet.ncols):
            t = norm(pl_sheet.cell_value(r, c))
            m = re.search(r"สิ้นสุดวันที่\s*\d{1,2}\s*(\S+)\s*(25\d\d)", t)
            if not m:
                continue
            month, year = m.group(1), int(m.group(2))
            is_annual = "สำหรับปี" in t or "รอบปี" in t
            q = THAI_MONTH_Q.get(month, "Q4")
            return q, year, is_annual
    raise ExtractError("ตรวจงวด (ไตรมาส/ปี) ไม่ได้จากหัวข้องบ")


# ---------- column detection ----------
def pl_current_consol_col(pl_sheet, year_be):
    """คอลัมน์ 'งบการเงินรวม + ปีปัจจุบัน' = คอลัมน์ปีแรกสุดที่มีค่า == year_be"""
    for r in range(min(pl_sheet.nrows, 12)):
        cols = [c for c in range(pl_sheet.ncols)
                if str(pl_sheet.cell_value(r, c)).strip() in (str(year_be), f"{year_be}.0")]
        if len(cols) >= 1:
            return cols[0]                       # ตัวแรก = งบรวม งวดปัจจุบัน
    raise ExtractError("หาคอลัมน์งบรวมงวดปัจจุบัน (PL) ไม่ได้")


def bs_date_cols(bs_sheet, year_be):
    """คืน (col_current, col_begin) ของงบการเงินรวม

    งบไตรมาสใช้วันที่เต็ม ('31 มีนาคม 2568'); งบรายปีตรวจสอบแล้วใช้เลขปีล้วน
    ('2568'/'2567') — รับทั้งสองแบบ
    """
    date_re = re.compile(r"\d{1,2}\s+\S+\s+25\d\d")

    def is_period_header(v):
        t = norm(v)
        if date_re.search(t):
            return True
        return t in (str(year_be), f"{year_be}.0", str(year_be - 1), f"{year_be - 1}.0")

    for r in range(min(bs_sheet.nrows, 12)):
        cols = [c for c in range(bs_sheet.ncols)
                if is_period_header(bs_sheet.cell_value(r, c))]
        if len(cols) >= 2:
            return cols[0], cols[1]              # [รวม-ปัจจุบัน, รวม-ต้นงวด, เฉพาะ..., ...]
    raise ExtractError("หาคอลัมน์วันที่/ปี (BS) ไม่ได้")


# ---------- line-item lookup ----------
def pl_first_statement_end(pl_sheet):
    """งบไตรมาสมีงบกำไรขาดทุน 2 ชุด (3 เดือน + สะสม) ในชีตเดียว —
    คืนแถวสิ้นสุดของชุดแรก = แถว 'รวมรายได้' ครั้งที่ 2 (ถ้าไม่มี = ทั้งชีต)
    """
    rev_rows = [r for r in range(pl_sheet.nrows)
                if nospace(pl_sheet.cell_value(r, 0)) in ("รวมรายได้", "รายได้รวม")]
    return rev_rows[1] if len(rev_rows) >= 2 else pl_sheet.nrows


def find_value(sheet, col, spec, divisor, row_end=None):
    """คืนค่า (ล้านบาท) ของ canonical item ตาม spec; sum ถ้ากำหนด
    row_end จำกัดขอบเขตแถว (ใช้กันไม่ให้ข้ามไปงบชุดสะสม)
    """
    match_mode = spec.get("match", "prefix")
    aliases = [nospace(a) for a in spec["aliases"]]
    do_sum = spec.get("sum", False)
    limit = row_end if row_end is not None else sheet.nrows
    found = []
    for r in range(limit):
        label = nospace(sheet.cell_value(r, 0))
        if not label:
            continue
        hit = False
        for an in aliases:
            if match_mode == "exact" and label == an:
                hit = True
            elif match_mode == "prefix" and label.startswith(an):
                hit = True
            if hit:
                break
        if not hit:
            continue
        v = sheet.cell_value(r, col)
        if isinstance(v, (int, float)) and v != 0:
            found.append(v / divisor)
            if not do_sum:
                break
    if not found:
        return None
    return sum(found) if do_sum else found[0]


def extract_file(path):
    """ดึง canonical values จากไฟล์ SET หนึ่งไฟล์ -> dict"""
    cfg = load_map()
    wb = xlrd.open_workbook(path)
    pl = get_sheet(wb, "PL")
    bs = get_sheet(wb, "BS")

    q, year, is_annual = detect_period(pl)
    pl_div = detect_unit_divisor(pl)
    bs_div = detect_unit_divisor(bs)
    pl_col = pl_current_consol_col(pl, year)
    bs_cur, bs_beg = bs_date_cols(bs, year)

    out = {"file": os.path.basename(path), "quarter": q, "year": year,
           "is_annual": is_annual, "pl_unit_div": pl_div, "bs_unit_div": bs_div}
    missing = []

    # income statement (เฉพาะงบชุดแรก = 3 เดือน; กันข้ามไปงบสะสม)
    pl_end = pl_first_statement_end(pl)
    for name, spec in cfg["income_statement"].items():
        v = find_value(pl, pl_col, spec, pl_div, row_end=pl_end)
        if v is None and spec.get("required"):
            missing.append(f"PL:{name}")
        out[name] = v

    # balance sheet: เก็บทั้งยอดปลายงวด (cur) และต้นงวด (beg)
    for name, spec in cfg["balance_sheet"].items():
        v_cur = find_value(bs, bs_cur, spec, bs_div)
        v_beg = find_value(bs, bs_beg, spec, bs_div)
        if v_cur is None and spec.get("required"):
            missing.append(f"BS:{name}")
        out[name + "_end"] = v_cur
        out[name + "_begin"] = v_beg

    if missing:
        raise ExtractError(f"{os.path.basename(path)}: หา required item ไม่เจอ -> {missing}")

    # balance check: รวมสินทรัพย์ = รวมหนี้สิน + รวมส่วนของผู้ถือหุ้น (ยอดปลายงวด)
    ta, tl, te = out["total_assets_end"], out["total_liabilities_end"], out["total_equity_end"]
    if ta and tl and te:
        diff = abs(ta - (tl + te))
        tol = max(1.0, ta * 0.005)               # ผ่อนปรน 0.5% กันปัดเศษ
        out["balance_ok"] = diff <= tol
        out["balance_diff"] = diff
        if not out["balance_ok"]:
            raise ExtractError(
                f"{os.path.basename(path)}: BALANCE CHECK ล้มเหลว "
                f"(สินทรัพย์ {ta:.1f} != หนี้สิน {tl:.1f} + ทุน {te:.1f}, ต่าง {diff:.1f} ล้านบาท)")
    return out


def days_for(q):
    return DAYS[q]


def metrics(np_, rev, cogs, ar_avg, inv_avg, ap_avg, ta_avg, te_avg, days):
    def safe(a, b):
        return a / b if b else None
    dso = safe(ar_avg, rev) and ar_avg / rev * days
    dio = safe(inv_avg, cogs) and inv_avg / cogs * days
    dpo = safe(ap_avg, cogs) and ap_avg / cogs * days
    ccc = (dio + dso - dpo) if None not in (dio, dso, dpo) else None
    return {
        "NPM": safe(np_, rev), "ROA": safe(np_, ta_avg), "ROE": safe(np_, te_avg),
        "DSO": dso, "DIO": dio, "DPO": dpo, "CCC": ccc,
    }


def compute_quarter(rec):
    """คำนวณ 7 ตัวชี้วัดจาก record (ต้นทุน/รายได้ = งวดปัจจุบัน; งบดุลใช้ค่าเฉลี่ยต้น-ปลายงวด)"""
    def avg(a, b):
        return (a + b) / 2 if (a is not None and b is not None) else (a if b is None else b)
    m = metrics(
        rec["net_profit_total"], rec["total_revenue"], rec["cogs_components"],
        avg(rec["trade_receivables_begin"], rec["trade_receivables_end"]),
        avg(rec["inventory_begin"], rec["inventory_end"]),
        avg(rec["trade_payables_begin"], rec["trade_payables_end"]),
        avg(rec["total_assets_begin"], rec["total_assets_end"]),
        avg(rec["total_equity_begin"], rec["total_equity_end"]),
        days_for(rec["quarter"]),
    )
    return m


def fmt(v, pct=False):
    if v is None:
        return "—"
    return f"{v*100:.1f}%" if pct else f"{v:.1f}"


def derive_q4(recs_by_tag):
    """สร้าง record ไตรมาส 4 = FY − Q1 − Q2 − Q3 (งบดุล Q4 ใช้ปลายปี = FY)"""
    need = ["Q1", "Q2", "Q3", "FY"]
    if any(t not in recs_by_tag for t in need):
        return None
    fy, q1, q2, q3 = (recs_by_tag[t] for t in ["FY", "Q1", "Q2", "Q3"])
    flow = lambda k: fy[k] - q1[k] - q2[k] - q3[k]
    q4 = {"quarter": "Q4", "year": fy["year"], "is_annual": False, "derived": True}
    for k in ["total_revenue", "cogs_components", "net_profit_total"]:
        q4[k] = flow(k)
    # งบดุล Q4: ต้นงวด = ปลาย Q3 (ก.ย.), ปลายงวด = ปลายปี (จากไฟล์ FY)
    for base in ["trade_receivables", "inventory", "trade_payables",
                 "total_assets", "total_equity"]:
        q4[base + "_begin"] = q3[base + "_end"]
        q4[base + "_end"] = fy[base + "_end"]
    return q4


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    if argv[1] == "--dir":
        files = sorted(glob.glob(os.path.join(argv[2], "*.XLS")) +
                       glob.glob(os.path.join(argv[2], "*.xls")))
    else:
        files = argv[1:]
    if not files:
        print("ไม่พบไฟล์")
        return 1

    recs = []
    for f in files:
        try:
            rec = extract_file(f)
            recs.append(rec)
            unit = {1e6: "บาท", 1e3: "พันบาท", 1.0: "ล้านบาท"}.get(rec["pl_unit_div"], "?")
            tag = "FY" if rec["is_annual"] else rec["quarter"]
            print(f"✓ {rec['file']:32s} {tag}/{rec['year']}  หน่วย={unit}  "
                  f"balance_ok={rec.get('balance_ok')}")
        except ExtractError as e:
            print(f"✗ {e}")
            return 2

    print("\n=== ค่าที่ดึงได้ (ล้านบาท) ===")
    hdr = f"{'งวด':>7} {'รายได้':>12} {'ต้นทุนขาย':>12} {'กำไรสุทธิ':>12} {'AR_end':>10} {'INV_end':>10} {'AP_end':>10} {'สินทรัพย์':>12} {'ทุน':>12}"
    print(hdr)
    for r in recs:
        tag = "FY" if r["is_annual"] else r["quarter"]
        print(f"{tag+'/'+str(r['year']):>7} {r['total_revenue']:>12.1f} {r['cogs_components']:>12.1f} "
              f"{r['net_profit_total']:>12.1f} {r['trade_receivables_end']:>10.1f} "
              f"{r['inventory_end']:>10.1f} {r['trade_payables_end']:>10.1f} "
              f"{r['total_assets_end']:>12.1f} {r['total_equity_end']:>12.1f}")

    # ประกอบ Q4 จาก FY − Q1−Q2−Q3 (ถ้ามีครบ)
    by_tag = {("FY" if r["is_annual"] else r["quarter"]): r for r in recs}
    q4 = derive_q4(by_tag)
    if q4:
        rev4 = q4["total_revenue"]
        print(f"\n[Q4 = FY−Q1−Q2−Q3]  รายได้={rev4:.1f}  ต้นทุนขาย={q4['cogs_components']:.1f}  "
              f"กำไรสุทธิ={q4['net_profit_total']:.1f} ล้านบาท")

    print("\n=== 7 ตัวชี้วัดรายไตรมาส ===")
    print(f"{'งวด':>7} {'NPM':>8} {'ROA':>8} {'ROE':>8} {'DSO':>7} {'DIO':>7} {'DPO':>7} {'CCC':>7}")
    ordered = [by_tag[t] for t in ["Q1", "Q2", "Q3"] if t in by_tag]
    if q4:
        ordered.append(q4)
    for r in ordered:
        m = compute_quarter(r)
        print(f"{r['quarter']+'/'+str(r['year']):>7} {fmt(m['NPM'],1):>8} {fmt(m['ROA'],1):>8} "
              f"{fmt(m['ROE'],1):>8} {fmt(m['DSO']):>7} {fmt(m['DIO']):>7} "
              f"{fmt(m['DPO']):>7} {fmt(m['CCC']):>7}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
