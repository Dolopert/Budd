# -*- coding: utf-8 -*-
# สร้าง CSV สรุป single-source สำหรับ viz แผนที่รายได้ต่างประเทศ
#   อ่าน  : data/segment_base.csv        (Base Sheet ต้นฉบับ ผู้ใช้ยืนยัน)
#   เขียน : data/segment/segment_by_year.csv  (สรุป normalize ล้านบาท + % + ธง DIV รายปี)
# หน่วยในต้นฉบับ: ASIA = พันบาท (÷1e3), บริษัทอื่น = บาทเต็ม (÷1e6) -> ล้านบาท
import csv, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data', 'segment_base.csv')
OUTDIR = os.path.join(ROOT, 'data', 'segment')
os.makedirs(OUTDIR, exist_ok=True)
YEARS = [2564, 2565, 2566, 2567, 2568]


def _num(s):
    s = s.replace(',', '').strip()
    return float(s) if s else 0.0


def main():
    rows = list(csv.reader(open(SRC, encoding='utf-8')))
    scale = lambda tk: 1e3 if tk == 'ASIA' else 1e6
    out = [['ticker', 'year', 'total_M', 'intl_M', 'dom_M', 'intl_pct', 'div']]
    i = 2
    while i < 33:                                  # Value section (ก่อน 'Percentage')
        r = rows[i]
        if r and r[0].strip() and len(r) > 1 and r[1].strip() == 'Domenestic':
            tk = r[0].strip(); sc = scale(tk)
            for j, yr in enumerate(YEARS):
                intl = _num(rows[i + 1][2 + j]) / sc
                tot = _num(rows[i + 2][2 + j]) / sc
                dom = tot - intl
                pct = round(intl / tot * 100, 1) if tot else 0.0
                out.append([tk, yr, round(tot, 1), round(intl, 1),
                            round(dom, 1), pct, 1 if pct >= 20 else 0])
            i += 3
        else:
            i += 1
    dst = os.path.join(OUTDIR, 'segment_by_year.csv')
    with open(dst, 'w', newline='', encoding='utf-8-sig') as f:
        csv.writer(f).writerows(out)
    print('written', dst, '(', len(out) - 1, 'rows )')


if __name__ == '__main__':
    main()
