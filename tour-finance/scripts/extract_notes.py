#!/usr/bin/env python3
"""
extract_notes.py — ดึง 'ลูกหนี้การค้าล้วน / เจ้าหนี้การค้าล้วน' จากหมายเหตุประกอบงบ (NOTES.docx)

หน้างบดุลรวม 'ลูกหนี้การค้าและลูกหนี้หมุนเวียนอื่น' เป็นบรรทัดเดียว — หมายเหตุแยกเป็น
ลูกหนี้การค้า (trade) กับ ลูกหนี้หมุนเวียนอื่น (non-trade) ตัวนี้ให้ DSO/DPO ใกล้ที่บริษัทรายงาน

สถานะ (proof-of-concept):
  ✓ DUSIT (.docx) ลูกหนี้การค้า: DSO=20.7 ตรงที่บริษัทรายงาน (21)
  ⚠ ยังไม่ทั่วถึง: ไฟล์ .DOC เก่า (SHANG) อ่านไม่ได้ด้วย zipfile;
    บาง format หมายเหตุใช้คำ/โครงต่าง (MINT); เจ้าหนี้บางเจ้ายัง parse ไม่ครบ
  -> หมายเหตุแต่ละบริษัทโครงต่างกันมาก การทำครบ 10 บริษัทต้อง tune รายเจ้า

ใช้:  python3 extract_notes.py <NOTES.docx>       # พิมพ์ลูกหนี้/เจ้าหนี้การค้าล้วน (conso ปัจจุบัน/ก่อน)
"""
import os
import re
import sys
import zipfile


def notes_text(path):
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8", errors="replace")
    t = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", xml))
    # docx แตกตัวเลขด้วยช่องว่าง: '417 , 483' -> '417,483', '( 11 , 196 )' -> '(11,196)'
    t = re.sub(r"(\d)\s*,\s*(\d)", r"\1,\2", t)
    t = re.sub(r"\(\s*(\d)", r"(\1", t)
    t = re.sub(r"(\d)\s*\)", r"\1)", t)
    return t


def clean_num(tok):
    """'417 , 483' / '(11,196)' -> float (วงเล็บ = ติดลบ)"""
    t = tok.replace(" ", "")
    neg = t.startswith("(") or t.endswith(")")
    t = t.strip("()").replace(",", "")
    if not re.fullmatch(r"-?\d+(\.\d+)?", t):
        return None
    return -float(t) if neg else float(t)


def sum_trade(text, section_kw, line_kw, exclude_kw):
    """ในโน้ต section_kw: รวมบรรทัดที่ขึ้นต้น line_kw (ไม่ใช่ exclude_kw)
    คืน (conso_current, conso_prior) หน่วยพันบาท
    """
    i = text.find(section_kw)
    if i < 0:
        return None, None
    seg = text[i:i + 900]
    # ตัดหัวตาราง (งบการเงินรวม ... 2568 2567 ...) ออกก่อน เพื่อไม่ให้ปีปนเป็นตัวเลข
    hdr = re.search(r"25\d\d\s+25\d\d\s+25\d\d\s+25\d\d\s*\(?\s*พัน\s*บาท\s*\)?", seg)
    if hdr:
        seg = seg[hdr.end():]
    # จำกัดถึงท้ายตารางแยกยอด (ก่อน 'หัก ค่าเผื่อ' / 'รวม') กันไปโดนตาราง aging/related-party
    end = re.search(r"หัก\s*ค่าเผื่อ|รวมลูกหนี้|รวมเจ้าหนี้", seg)
    if end:
        seg = seg[:end.start()]
    cur = prev = 0.0
    found = False
    # แบ่ง seg เป็นบล็อกตาม label ลูกหนี้/เจ้าหนี้ แล้วอ่านตัวเลข (คั่นด้วยช่องว่างล้วนหลัง join comma)
    parts = re.split(r"(ลูกหนี้[^\d(]*|เจ้าหนี้[^\d(]*)(?=[\d(])", seg)
    j = 1
    while j < len(parts) - 1:
        lab = re.sub(r"\s+", "", parts[j])
        after = parts[j + 1]
        nums = re.findall(r"\(?\d[\d,]*(?:\.\d+)?\)?", after)[:4]   # 4 คอลัมน์: รวม-ปัจจุบัน/ก่อน, เฉพาะ-ปัจจุบัน/ก่อน
        vals = [v for v in (clean_num(n) for n in nums) if v is not None]
        if lab.startswith(line_kw) and not any(e in lab for e in exclude_kw) and len(vals) >= 2:
            cur += vals[0]
            prev += vals[1]
            found = True
        j += 2
    return (cur, prev) if found else (None, None)


def extract(path):
    txt = notes_text(path)
    # line_kw='ลูกหนี้การค้า' (startswith) พอ — บรรทัด non-trade ขึ้นต้น 'ลูกหนี้หมุนเวียน'
    ar_c, ar_p = sum_trade(txt, "ลูกหนี้การค้าและลูกหนี้ หมุนเวียน อื่น", "ลูกหนี้การค้า", [])
    if ar_c is None:
        ar_c, ar_p = sum_trade(txt, "ลูกหนี้การค้าและลูกหนี้หมุนเวียนอื่น", "ลูกหนี้การค้า", [])
    ap_c, ap_p = sum_trade(txt, "เจ้าหนี้การค้าและเจ้าหนี้ หมุนเวียน อื่น", "เจ้าหนี้การค้า", [])
    if ap_c is None:
        ap_c, ap_p = sum_trade(txt, "เจ้าหนี้การค้าและเจ้าหนี้หมุนเวียนอื่น", "เจ้าหนี้การค้า", [])
    return dict(trade_ar_end=ar_c, trade_ar_begin=ar_p, trade_ap_end=ap_c, trade_ap_begin=ap_p)


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 1
    for p in argv[1:]:
        r = extract(p)
        f = lambda x: f"{x/1000:.1f} ลบ." if x is not None else "—"
        print(f"{os.path.basename(os.path.dirname(p))}: "
              f"ลูกหนี้การค้าล้วน ปลาย={f(r['trade_ar_end'])} ต้น={f(r['trade_ar_begin'])} | "
              f"เจ้าหนี้การค้าล้วน ปลาย={f(r['trade_ap_end'])} ต้น={f(r['trade_ap_begin'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
