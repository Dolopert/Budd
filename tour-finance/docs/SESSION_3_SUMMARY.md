# สรุป Session 3 — Year Slider + ยืนยันรายประเทศจากงบ + Toggle ทวีป/ประเทศ

ต่อจาก `SESSION_2_SUMMARY.md` — session นี้ทำ viz แผนที่รายได้ต่างประเทศให้ **โต้ตอบราย 5 ปี**
และ **ยืนยันตัวเลขรายประเทศจากหมายเหตุงบจริง** (แทนค่าประมาณเดิม)

## 1. Local CSV store (single source) — `data/segment/`
เลิก hardcode ตัวเลขใน viz แล้ว — `viz/build_worldmap.py` อ่านจาก CSV:
| ไฟล์ | คือ |
|------|-----|
| `data/segment_base.csv` | Base Sheet ต้นฉบับ (in/out รายได้ 10 บริษัท × 5 ปี — ผู้ใช้ยืนยัน) |
| `data/segment/segment_by_year.csv` | สรุป normalize (ล้านบาท + % + ธง DIV) จาก `scripts/build_segment.py` |
| `data/segment/geo_flows.csv` | รายประเทศ/ภูมิภาคบนแผนที่ (year-aware, ติดธง verified) |
| `data/segment/notes/<บ.>/<ปี>/` | ภาพหมายเหตุ + `EXTRACTED.md` (audit trail รายบริษัท) |

rebuild: `PYTHONUTF8=1 python scripts/build_segment.py && PYTHONUTF8=1 python viz/build_worldmap.py`

## 2. Task 1 — Year Slider (2564–2568)
- เลื่อน slider/คลิกปี → bars %, เส้นเกณฑ์ 20%, กลุ่ม DIV (นับใหม่ทุกปี), มูลค่ารวม, เส้นแผนที่ เปลี่ยนตามปีจริง
- ทุกตัวเลขจาก Base Sheet (หน่วยตรวจแล้ว: ASIA=พันบาท, อื่น=บาทเต็ม → ล้านบาท)
- logic "ตลาดที่ยังไม่เข้า = เส้นไม่โผล่" (thb=0 ในปีนั้น)

## 3. ยืนยันรายประเทศจากหมายเหตุงบจริง (แก้ค่าประมาณเดิมที่มั่ว)
| บริษัท | สถานะ | แหล่ง | ค่าที่แก้ |
|--------|-------|-------|----------|
| **MINT** | ✅ 5/5 ปี | หมายเหตุ 8.2 ภูมิศาสตร์ (งบ 4 ฉบับ) | ยุโรป 94.5→88.5B, +ออส/นิวซีแลนด์ 14.5B (เดิมหาย) |
| **ERW** | ✅ 5/5 ปี | One Report FY2565–2568 น.229 | ฟิลิปปินส์+ญี่ปุ่น (เข้าญี่ปุ่น 2567) |
| **SHR** | ✅ 5/5 ปี | NOTES.pdf น.48 หมายเหตุ 27 (+งบเก่า) | UK 4.4→3.4B, มัลดีฟส์ 2.3→2.6B · Outrigger(มอริเชียส/ฟิจิ) แยกประมาณ 44:56 |
| **CENTEL** | ✅ 5/5 ปี | NOTES(1).pdf น.87 (+งบ FY2565–67) | มัลดีฟส์ 2.5→1.9B, ญี่ปุ่น 0.5→1.6B, ตัดตะวันออกกลางออก (เข้า Osaka 2566) |
| **DUSIT** | 🔶 ไทย/ตปท. verified | งบ + One Report | **ไม่เปิดรายประเทศ** → รายประเทศคงเป็นประมาณการ |

- พบ **restatement** (MINT 2566, SHR 2566) → ใช้ฉบับล่าสุดของแต่ละปี ตรง Base Sheet
- ผลรวมรายประเทศ = Base Sheet intl ทุกปี (ต่าง ±0–4% ช่วงโควิด = definitional "รายได้ลูกค้าภายนอก")

## 4. Task 2 — Toggle ความละเอียด ทวีป ↔ ประเทศ
- ปุ่มมุมซ้ายบนแผนที่: **ประเทศ** (14 ประเทศ) ↔ **ทวีป** (ยุบตาม `cont`: Europe/Asia/Oceania/Americas/Africa/Middle East/Other)
- โหมดทวีปรวมทุกประเทศใน cont เดียวกันของบริษัทเดียวกัน (เช่น ERW/CENTEL ฟิลิปปินส์+ญี่ปุ่น → เอเชีย)
- ใช้ได้ทั้ง 2 โหมดพร้อม year slider

## 5. หมายเหตุ
- viz self-contained (`viz/tour_revenue_worldmap.html`) · env: `python` + `PYTHONUTF8=1`
- ยังทำต่อได้: DUSIT รายประเทศ (ถ้าเจอ IR deck) · CENTEL/SHR ปีเก่ายืนยันเพิ่ม · DIV ต่อเนื่องใน regression
