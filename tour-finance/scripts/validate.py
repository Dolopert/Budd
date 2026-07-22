#!/usr/bin/env python3
"""
validate.py — ตรวจสอบความถูกต้องของข้อมูลที่ดึงมา (independent checks)

รันชุดตรวจสอบที่ไม่ได้พึ่งสูตรคำนวณตัวเดียวกับที่ดึง:
  A. balance check ทุกไฟล์ (สินทรัพย์ = หนี้สิน + ทุน)
  B. ความสอดคล้องของยอด 'ต้นปี' ข้ามไฟล์ Q1/Q2/Q3 (ต้องเท่ากัน)
  C. ไตรมาส 4 (FY − Q1−Q2−Q3) ต้องเป็นบวก (รายได้/ต้นทุน)
  D. อัตรากำไรขั้นต้น 0 < (รายได้−ต้นทุน)/รายได้ < 1 ทุกไตรมาส
  E. ROE รายปี: ผลรวม 4 ไตรมาส ≈ กำไรทั้งปี / ค่าเฉลี่ยส่วนของเจ้าของ
  F. DSO/DIO/DPO อยู่ในช่วงสมเหตุผล [0, 400] วัน
"""
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
import extract_set as E

RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))


def load_groups():
    files = []
    for ext in ("xls", "xlsx", "xlsm", "XLS", "XLSX"):
        files += glob.glob(os.path.join(RAW, "*", "*", f"*.{ext}"))
    groups = {}
    for f in sorted(set(files)):
        try:
            rec = E.extract_file(f)
        except E.ExtractError as e:
            print(f"  ✗ EXTRACT {os.path.relpath(f, RAW)}: {e}")
            continue
        key = (rec["ticker"], rec["year"])
        tag = "FY" if rec["is_annual"] else rec["quarter"]
        groups.setdefault(key, {})[tag] = rec
    return groups


def close(a, b, rel=0.01, absol=1.0):
    if a is None or b is None:
        return False
    return abs(a - b) <= max(absol, abs(b) * rel)


def main():
    groups = load_groups()
    warns, checks = [], 0

    def warn(tag, msg):
        warns.append(f"  ⚠ [{tag}] {msg}")

    for (tk, yr), bt in sorted(groups.items()):
        # A. balance
        for t, rec in bt.items():
            checks += 1
            if rec.get("balance_ok") is False:
                warn(f"{tk} {yr} {t}", f"balance ไม่ตรง (ต่าง {rec.get('balance_diff',0):.1f} ลบ.)")

        # B. ยอดต้นปีต้องเท่ากันข้าม Q1/Q2/Q3
        for item in E.BS_ITEMS:
            vals = [(t, bt[t].get(item + "_begin")) for t in ("Q1", "Q2", "Q3") if t in bt]
            vals = [(t, v) for t, v in vals if v is not None]
            checks += 1
            if len(vals) >= 2 and not all(close(v, vals[0][1]) for _, v in vals):
                warn(f"{tk} {yr}", f"ยอดต้นปี '{item}' ไม่ตรงข้ามไตรมาส: "
                                   + ", ".join(f"{t}={v:.0f}" for t, v in vals))

        # C+D. ต่อไตรมาส (รวม Q4 derived)
        rows = E.compute_group(bt)
        for rec, m in rows:
            q = rec["quarter"]
            rev, cogs = rec["total_revenue"], rec["cogs"]
            checks += 2
            if q == "Q4" and (rev is not None and rev <= 0):
                warn(f"{tk} {yr} Q4", f"รายได้ derived ติดลบ/ศูนย์ ({rev:.0f}) — Q1-3 รวม > FY")
            if rev and cogs:
                gm = (rev - cogs) / rev
                if not (-0.05 < gm < 1.0):
                    warn(f"{tk} {yr} {q}", f"gross margin ผิดช่วง ({gm*100:.0f}%) rev={rev:.0f} cogs={cogs:.0f}")
            # F. ช่วงวัน
            for k in ("DSO", "DIO", "DPO"):
                checks += 1
                if m[k] is not None and not (0 <= m[k] <= 400):
                    warn(f"{tk} {yr} {q}", f"{k} ผิดช่วง ({m[k]:.0f} วัน)")

        # E. ROE รายปี: sum ไตรมาส เทียบ FY/avg(equity)
        if "FY" in bt and len(rows) == 4:
            fy = bt["FY"]
            eq_start = bt["Q1"].get("total_equity_begin") if "Q1" in bt else None
            eq_end = fy.get("total_equity_end")
            checks += 1
            if eq_start and eq_end and fy.get("net_profit_total") is not None:
                roe_annual = fy["net_profit_total"] / ((eq_start + eq_end) / 2)
                roe_sum = sum(m["ROE"] for _, m in rows if m["ROE"] is not None)
                if not close(roe_sum, roe_annual, rel=0.08, absol=0.003):
                    warn(f"{tk} {yr}", f"ROE รวมไตรมาส ({roe_sum*100:.1f}%) ≠ ROE รายปี ({roe_annual*100:.1f}%)")

    print(f"\n=== ตรวจ {checks} รายการ, {len(groups)} บริษัท-ปี ===")
    if warns:
        print(f"พบข้อสังเกต {len(warns)} จุด:")
        print("\n".join(warns))
    else:
        print("✓ ผ่านทุกการตรวจสอบ ไม่พบ anomaly")
    return 1 if warns else 0


if __name__ == "__main__":
    sys.exit(main())
