#!/usr/bin/env python3
"""
set_ratios.py — อัตราส่วนวงจรเงินสดรายปี 2 ฐาน: สูตร SET (เทียบเว็บ) vs CFA

สูตร SET (settrade/SETSMART) — ต่างจาก CFA:
  • ฐาน 365 วัน + กระแส 12 เดือน (รายปี = FY)
  • ยอดงบดุล 'ปลายงวด' (ไม่ใช่ค่าเฉลี่ย)
  • DSO ใช้ 'รายได้จากการดำเนินธุรกิจ' = รวมรายได้ − รายได้อื่น
  • DIO/DPO ใช้ 'ต้นทุน' = ต้นทุนขาย + ค่าเสื่อมราคา (จากงบกระแสเงินสด)
CFA (ของเรา) — ค่าเฉลี่ยงบดุลต้นปี-ปลายปี, รวมรายได้, ต้นทุนขายแคบ, 365

ใช้:  python3 set_ratios.py      # เขียน output/set_ratios.csv + พิมพ์ตาราง
"""
import os
import sys
import csv
import glob

sys.path.insert(0, os.path.dirname(__file__))
import extract_set as E

RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))
OUT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "output"))


def load_fy():
    """คืน dict (ticker,year) -> {'FY':rec, 'Q1':rec} เท่าที่มี (ต้องมี FY + Q1 สำหรับยอดต้นปี)"""
    files = []
    for ext in ("xls", "xlsx", "xlsm", "XLS", "XLSX"):
        files += glob.glob(os.path.join(RAW, "*", "*", f"*.{ext}"))
    groups = {}
    for f in sorted(set(files)):
        try:
            rec = E.extract_file(f)
        except E.ExtractError:
            continue
        key = (rec["ticker"], rec["year"])
        tag = "FY" if rec["is_annual"] else rec["quarter"]
        groups.setdefault(key, {})[tag] = rec
    return groups


def set_basis(fy):
    """อัตราส่วนสูตร SET (รายปี, ปลายงวด, 365)"""
    rev = fy["total_revenue"]
    oth = fy.get("other_income") or 0
    op_rev = rev - oth                                   # รายได้จากการดำเนินธุรกิจ
    dep = fy.get("depreciation") or 0
    # เอกสาร SET ระบุ 'ต้นทุน + ค่าเสื่อม' แต่ตัวเลขจริงบนเว็บ settrade บ่งชี้ว่า
    # ใช้ต้นทุนที่ต่ำกว่า cogs -> ใช้ cogs ล้วน (ใกล้เว็บสุด empirically) เก็บ dep ไว้อ้างอิง
    cost = fy["cogs"]
    ar, inv = fy["trade_receivables_end"], fy["inventory_end"]
    ap = fy.get("trade_payables_broad_end") or fy["trade_payables_end"]  # เจ้าหนี้กว้าง (SET)
    dso = ar / op_rev * 365 if op_rev else None
    dio = inv / cost * 365 if cost else None
    dpo = ap / cost * 365 if cost else None
    ccc = (dso + dio - dpo) if None not in (dso, dio, dpo) else None
    de = fy["total_liabilities_end"] / fy["total_equity_end"] if fy["total_equity_end"] else None
    npm = fy["net_profit_total"] / rev if rev else None
    return dict(DSO=dso, DIO=dio, DPO=dpo, CCC=ccc, NPM=npm, DE=de,
                op_rev=op_rev, cost=cost, dep=dep)


def cfa_basis(bt):
    """อัตราส่วนแบบ CFA รายปี (ค่าเฉลี่ยต้นปี-ปลายปี, รวมรายได้, ต้นทุนขายแคบ, 365)"""
    fy, q1 = bt["FY"], bt.get("Q1")
    if not q1:
        return None
    rev, cogs = fy["total_revenue"], fy["cogs"]

    def avg(base):
        return (q1[base + "_begin"] + fy[base + "_end"]) / 2
    dso = avg("trade_receivables") / rev * 365 if rev else None
    dio = avg("inventory") / cogs * 365 if cogs else None
    dpo = avg("trade_payables") / cogs * 365 if cogs else None
    ccc = (dso + dio - dpo) if None not in (dso, dio, dpo) else None
    return dict(DSO=dso, DIO=dio, DPO=dpo, CCC=ccc)


def main():
    groups = load_fy()
    rows = []
    print(f"{'บริษัท':>7} | {'ฐาน':>4} | {'DSO':>6} {'DIO':>6} {'DPO':>7} {'CCC':>7} | {'NPM':>6} {'D/E':>5}")
    print("-" * 66)
    for (tk, yr), bt in sorted(groups.items()):
        if "FY" not in bt:
            continue
        s = set_basis(bt["FY"])
        c = cfa_basis(bt)
        f = lambda x: f"{x:.1f}" if x is not None else "—"
        p = lambda x: f"{x*100:.1f}%" if x is not None else "—"
        print(f"{tk:>7} | {'SET':>4} | {f(s['DSO']):>6} {f(s['DIO']):>6} {f(s['DPO']):>7} {f(s['CCC']):>7} | "
              f"{p(s['NPM']):>6} {f(s['DE']):>5}")
        if c:
            print(f"{'':>7} | {'CFA':>4} | {f(c['DSO']):>6} {f(c['DIO']):>6} {f(c['DPO']):>7} {f(c['CCC']):>7} |")
        rows.append(dict(ticker=tk, year=yr,
                         DSO_SET=s["DSO"], DIO_SET=s["DIO"], DPO_SET=s["DPO"], CCC_SET=s["CCC"],
                         NPM_SET=s["NPM"], DE_SET=s["DE"],
                         DSO_CFA=(c or {}).get("DSO"), DIO_CFA=(c or {}).get("DIO"),
                         DPO_CFA=(c or {}).get("DPO"), CCC_CFA=(c or {}).get("CCC"),
                         op_revenue=s["op_rev"], cost_incl_dep=s["cost"], depreciation=s["dep"]))

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "set_ratios.csv")
    with open(path, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0].keys()))
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    print(f"\n-> {os.path.relpath(path)}  ({len(rows)} บริษัท-ปี)")
    print("หมายเหตุ:")
    print(" • SET เป็นรายปี (FY); ระดับไตรมาสต้องใช้กระแส 12 เดือน (TTM) — รอข้อมูลปีก่อน")
    print(" • DSO ฐาน SET ตรวจแล้วตรง settrade ~99% (MINT 3 ปี)")
    print(" • DPO ใช้เจ้าหนี้กว้าง (ปรับตาม MINT) — บริษัทอื่นอาจ over/under-count")
    print("   ต้องมีตัวเลข settrade ของแต่ละบริษัทมา calibrate จึงจะยืนยันได้")
    print(" • DIO ยังต่ำกว่า settrade เพราะ settrade ใช้ต้นทุน standardized ~0.6x งบ (black-box)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
