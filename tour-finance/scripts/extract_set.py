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
import openpyxl
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


# ---------- unified reader: รองรับทั้ง .xls (xlrd) และ .xlsx (openpyxl) ----------
class Grid:
    """หน้าตาชีตแบบ 0-based เหมือนกันไม่ว่าไฟล์ต้นทางเป็น .xls หรือ .xlsx"""
    def __init__(self, name, nrows, ncols, getter):
        self.name = name
        self.nrows = nrows
        self.ncols = ncols
        self._get = getter

    def cell_value(self, r, c):
        v = self._get(r, c)
        return "" if v is None else v


def open_book(path):
    """คืน list ของ Grid (0-based) จากไฟล์ .xls หรือ .xlsx"""
    if path.lower().endswith((".xlsx", ".xlsm")):
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        grids = []
        for ws in wb.worksheets:
            nr, nc = ws.max_row or 0, ws.max_column or 0
            data = [[cell.value for cell in row] for row in ws.iter_rows()]

            def make_getter(d):
                def g(r, c):
                    if 0 <= r < len(d) and 0 <= c < len(d[r]):
                        return d[r][c]
                    return None
                return g
            grids.append(Grid(ws.title, nr, nc, make_getter(data)))
        return grids
    # .xls
    wb = xlrd.open_workbook(path)
    return [Grid(sh.name, sh.nrows, sh.ncols,
                 (lambda s: (lambda r, c: s.cell_value(r, c)))(sh))
            for sh in wb.sheets()]


# ---------- label reading (label อาจอยู่คนละคอลัมน์ตาม indent เช่น ASIA) ----------
def row_label(sheet, r, upto):
    """label ของแถว = ข้อความช่องแรกที่ไม่ว่าง ในคอลัมน์ 0..upto-1 (ซ้ายของคอลัมน์ตัวเลข)"""
    for c in range(max(0, upto)):
        t = norm(sheet.cell_value(r, c))
        if t:
            return t
    return ""


def sheet_has_label(sheet, targets, scan_cols=10):
    """จริงถ้ามีแถวใดที่ label (นับช่องซ้ายสุดที่ไม่ว่าง) ตรงกับ targets"""
    tset = {nospace(t) for t in targets}
    for r in range(sheet.nrows):
        if nospace(row_label(sheet, r, scan_cols)) in tset:
            return True
    return False


# ---------- content-based sheet lookup (ทนต่อชื่อชีตแปลกๆ เช่น 'FS.T') ----------
def get_bs_sheet(grids):
    for g in grids:                                   # งบดุล = ชีตที่มีบรรทัด 'รวมสินทรัพย์'
        if sheet_has_label(g, ["รวมสินทรัพย์"]):
            return g
    for g in grids:                                   # เผื่อไว้: ชื่อขึ้นต้น BS
        if norm(g.name).upper().startswith("BS"):
            return g
    raise ExtractError(f"ไม่พบชีตงบดุล — มีชีต: {[g.name for g in grids]}")


def get_pl_sheet(grids):
    """งบกำไรขาดทุน = ชีตที่มี 'รวมรายได้'; ถ้ามีทั้ง PL(3)/PL(6) เลือก 3 เดือน"""
    pls = [g for g in grids if sheet_has_label(g, ["รวมรายได้", "รายได้รวม"])]
    if not pls:
        pls = [g for g in grids if norm(g.name).upper().startswith("PL")]
    if not pls:
        raise ExtractError(f"ไม่พบชีตงบกำไรขาดทุน — มีชีต: {[g.name for g in grids]}")
    for g in pls:                                     # ชอบชีต 3 เดือนที่ระบุชัด '(3)'
        if "(3)" in g.name:
            return g
    return pls[0]                                     # ที่เหลือ = ชีตเดียว/รวม (row-window ตัดชุดสะสม)


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


# ---------- header-row detection (ใช้ร่วมกันทั้ง period + column) ----------
DATE_RE = re.compile(r"\d{1,2}\s+\S+\s+(25\d\d)")


def year_of(v):
    """คืนปี พ.ศ. ถ้า cell เป็น 'ตัวบอกงวด' (เลขปีล้วน หรือวันที่เต็ม) มิฉะนั้น None"""
    if isinstance(v, (int, float)) and 2500 <= v <= 2600:
        return int(v)
    t = norm(v)
    if re.fullmatch(r"25\d\d(\.0)?", t):
        return int(float(t))
    m = DATE_RE.search(t)                          # '31 มีนาคม 2568'
    return int(m.group(1)) if m else None


def period_header(sheet):
    """หาแถว header ของงวด = แถวแรกที่มี 'ตัวบอกงวด' >= 2 ช่อง
    คืน (row, [cols เรียงซ้าย->ขวา], [ปีของแต่ละ col])
    คอลัมน์ซ้ายสุด = งบรวมงวดปัจจุบัน; ถัดไป = งบรวมงวดเทียบ (ต้นงวด/ปีก่อน)
    """
    for r in range(min(sheet.nrows, 16)):
        cols, yrs = [], []
        for c in range(sheet.ncols):
            y = year_of(sheet.cell_value(r, c))
            if y is not None:
                cols.append(c)
                yrs.append(y)
        if len(cols) >= 2:
            return r, cols, yrs
    raise ExtractError("หาแถว header ของงวดไม่ได้ (ไม่พบเลขปี/วันที่ >=2 ช่อง)")


def detect_period(pl_sheet):
    """คืน (quarter_label, year_be, is_annual) — อ่านปีจากแถว header เท่านั้น
    (กันเลขอื่นที่ไม่ใช่ปีมารบกวน) และดูชนิดงวดจากข้อความหัวตาราง
    """
    _, _, yrs = period_header(pl_sheet)
    year = max(yrs)                                # งวดปัจจุบัน = ปีมากสุดในแถว header
    blob = " ".join(norm(pl_sheet.cell_value(r, c))
                    for r in range(min(pl_sheet.nrows, 16)) for c in range(pl_sheet.ncols))
    is_annual = any(k in blob for k in ["สำหรับปี", "รอบปี", "สิบสองเดือน", "สำหรับงวดสิบสอง"])
    if is_annual:
        return "Q4", year, True
    month = next((m for m in THAI_MONTH_Q if m in blob), None)
    if month is None:
        raise ExtractError("ตรวจเดือนสิ้นงวดไม่ได้จากหัวข้องบ")
    return THAI_MONTH_Q[month], year, False


# ---------- column selection (งบการเงินรวม = คอลัมน์ซ้ายสุดของแต่ละงวด) ----------
def pl_current_consol_col(pl_sheet, year_be):
    """คอลัมน์งบรวม-งวดปัจจุบัน = คอลัมน์ตัวบอกงวดซ้ายสุดที่ปี == year_be"""
    _, cols, yrs = period_header(pl_sheet)
    for c, y in zip(cols, yrs):
        if y == year_be:
            return c
    return cols[0]


def bs_date_cols(bs_sheet, year_be):
    """คืน (col_current, col_begin) ของงบการเงินรวม = สองคอลัมน์งวดซ้ายสุด"""
    _, cols, _ = period_header(bs_sheet)
    return cols[0], cols[1]


# ---------- line-item lookup ----------
def pl_first_statement_end(pl_sheet, label_upto):
    """งบไตรมาสมีงบกำไรขาดทุน 2 ชุด (3 เดือน + สะสม) ในชีตเดียว —
    คืนแถวสิ้นสุดของชุดแรก = แถว 'รวมรายได้' ครั้งที่ 2 (ถ้าไม่มี = ทั้งชีต)
    """
    rev_rows = [r for r in range(pl_sheet.nrows)
                if nospace(row_label(pl_sheet, r, label_upto)) in ("รวมรายได้", "รายได้รวม")]
    return rev_rows[1] if len(rev_rows) >= 2 else pl_sheet.nrows


def find_value(sheet, col, spec, divisor, row_end=None):
    """คืนค่า (ล้านบาท) ของ canonical item ตาม spec; sum ถ้ากำหนด
    row_end จำกัดขอบเขตแถว (ใช้กันไม่ให้ข้ามไปงบชุดสะสม)
    label อ่านจากช่องซ้ายสุดที่ไม่ว่าง (คอลัมน์ 0..col-1) รองรับ indent หลายคอลัมน์
    """
    match_mode = spec.get("match", "prefix")
    aliases = [nospace(a) for a in spec["aliases"]]
    do_sum = spec.get("sum", False)
    limit = row_end if row_end is not None else sheet.nrows
    found = []
    for r in range(limit):
        label = nospace(row_label(sheet, r, col))
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
    grids = open_book(path)
    pl = get_pl_sheet(grids)
    bs = get_bs_sheet(grids)

    q, year, is_annual = detect_period(pl)
    pl_div = detect_unit_divisor(pl)
    bs_div = detect_unit_divisor(bs)
    pl_col = pl_current_consol_col(pl, year)
    bs_cur, bs_beg = bs_date_cols(bs, year)

    out = {"file": os.path.basename(path), "quarter": q, "year": year,
           "is_annual": is_annual, "pl_unit_div": pl_div, "bs_unit_div": bs_div}
    missing = []

    # income statement (เฉพาะงบชุดแรก = 3 เดือน; กันข้ามไปงบสะสม)
    pl_end = pl_first_statement_end(pl, pl_col)
    for name, spec in cfg["income_statement"].items():
        v = find_value(pl, pl_col, spec, pl_div, row_end=pl_end)
        if v is None and spec.get("required"):
            missing.append(f"PL:{name}")
        out[name] = v

    # COGS: ใช้ subtotal ถ้ามี (ASIA) มิฉะนั้นผลรวม components (CENTEL/ERW); เป็นค่าบวกเสมอ
    cogs = out.get("cogs_subtotal") or out.get("cogs_components")
    if cogs is None:
        missing.append("PL:cogs (ทั้ง subtotal และ components)")
    out["cogs"] = abs(cogs) if cogs is not None else None

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
        rec["net_profit_total"], rec["total_revenue"], rec["cogs"],
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
    for k in ["total_revenue", "cogs", "net_profit_total"]:
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
        pats = ["*.XLS", "*.xls", "*.XLSX", "*.xlsx", "*.XLSM", "*.xlsm"]
        files = sorted({f for p in pats for f in glob.glob(os.path.join(argv[2], p))})
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
        print(f"{tag+'/'+str(r['year']):>7} {r['total_revenue']:>12.1f} {r['cogs']:>12.1f} "
              f"{r['net_profit_total']:>12.1f} {r['trade_receivables_end']:>10.1f} "
              f"{r['inventory_end']:>10.1f} {r['trade_payables_end']:>10.1f} "
              f"{r['total_assets_end']:>12.1f} {r['total_equity_end']:>12.1f}")

    # ประกอบ Q4 จาก FY − Q1−Q2−Q3 (ถ้ามีครบ)
    by_tag = {("FY" if r["is_annual"] else r["quarter"]): r for r in recs}
    q4 = derive_q4(by_tag)
    if q4:
        rev4 = q4["total_revenue"]
        print(f"\n[Q4 = FY−Q1−Q2−Q3]  รายได้={rev4:.1f}  ต้นทุนขาย={q4['cogs']:.1f}  "
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
