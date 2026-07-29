# -*- coding: utf-8 -*-
"""รายงานว่าแต่ละบริษัทดึง "บรรทัด" ใดจากงบดุลมาคำนวณ DSO/DIO/DPO
สะท้อนกฎจริงในไปป์ไลน์: label ขึ้นต้นด้วย alias + ไม่มีคำใน exclude (DL-1/DL-5)"""
import os, glob, re
import extract_set as E

INTL_ORDER = ["ASIA","CENTEL","DUSIT","ERW","MANRIN","MINT","OHTL","SHANG","SHR","VRANDA"]
RAW = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "raw"))

CATS = {
    "DSO ← ลูกหนี้": (["ลูกหนี้การค้าและลูกหนี้หมุนเวียนอื่น","ลูกหนี้การค้าและลูกหนี้อื่น",
                       "ลูกหนี้การค้า","ลูกหนี้หมุนเวียนอื่น","ลูกหนี้อื่น"], ["ไม่หมุนเวียน"]),
    "DIO ← สินค้าคงเหลือ": (["สินค้าคงเหลือ"], []),
    "DPO ← เจ้าหนี้": (["เจ้าหนี้การค้าและเจ้าหนี้หมุนเวียนอื่น","เจ้าหนี้การค้าและเจ้าหนี้อื่น",
                        "เจ้าหนี้การค้า","เจ้าหนี้หมุนเวียนอื่น","เจ้าหนี้อื่น"], ["ไม่หมุนเวียน"]),
}

def pick_file(tk):
    for yr in ("2568","2567","2566"):
        for pat in (f"{tk}/{yr}/FY_FS.*", f"{tk}/{yr}/Q3_FS.*"):
            hit = glob.glob(os.path.join(RAW, pat))
            if hit:
                return hit[0], yr
    return None, None

def matched_rows(sheet, aliases, exclude):
    al = [E.nospace(a) for a in aliases]; ex = [E.nospace(e) for e in exclude]
    out = []
    ncol = min(sheet.ncols, 8)
    for r in range(sheet.nrows):
        lab = E.row_label(sheet, r, ncol)
        if not lab:
            continue
        n = E.nospace(lab)
        if any(e in n for e in ex):
            continue
        if any(n.startswith(a) for a in al):
            out.append(lab)
    return out

print(f"{'บริษัท':7} | รายการที่ดึงมาคำนวณ (จากงบดุล)")
print("="*90)
for tk in INTL_ORDER:
    path, yr = pick_file(tk)
    if not path:
        print(f"{tk:7} | (ไม่พบไฟล์)"); continue
    grids = E.open_book(path)
    bs = E.get_bs_sheets(grids)
    labels = {k: [] for k in CATS}
    for sh in bs:
        for cat,(al,ex) in CATS.items():
            labels[cat] += matched_rows(sh, al, ex)
    # ยุบซ้ำ รักษาลำดับ
    print(f"{tk:7} | (งบปี {yr})")
    for cat in CATS:
        seen = list(dict.fromkeys(labels[cat]))
        if not seen:
            print(f"        · {cat:22}: — ไม่พบ —")
        elif len(seen) == 1:
            print(f"        · {cat:22}: {seen[0]}")
        else:
            print(f"        · {cat:22}: [รวม {len(seen)} บรรทัด]")
            for s in seen:
                print(f"        {'':24}   + {s}")
    print("-"*90)
