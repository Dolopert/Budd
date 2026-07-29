# สรุป Session 2 — Review ระเบียบวิธีวิจัย + วิเคราะห์สถิติ + วิชวลไลซ์

ต่อจาก `SESSION_SUMMARY.md` (ข้อมูล 200/200 จุด, validate 0 error) — session นี้เน้น
**ตรวจ/แก้ proposal, รันสถิติจริง, ยืนยันการจัดกลุ่ม DIV ด้วยข้อมูล segment, และสร้างแผนที่รายได้**

## 1. Review + แก้ร่าง proposal

- **บทที่ 6 (ระเบียบวิธีวิจัย)** — เขียนใหม่ทั้งบท → `output/บทที่6_ระเบียบวิธีวิจัย_ฉบับแก้.docx`
  รายละเอียดจุดที่แก้ทั้งหมดใน `docs/proposal_review.md` (12 ประเด็น เรียงตามความรุนแรง)
- **บทที่ 2 (แนวคิด/ทฤษฎี)** — แก้เต็ม → `output/บทที่2_แนวคิดและทฤษฎี_ฉบับแก้เต็ม.pdf`
  แก้คำผิด + ป้าย ROA/ROE + หมายเหตุความสอดคล้องกับบท 6 + **เพิ่ม 2.1.6 ทฤษฎีที่สมมติฐานอ้าง**
  (TCT, Internalization+RBV, MPT, Economies of Scale/Scope, Trade-off Theory)

### ประเด็นระเบียบวิธีที่ต้องแก้ (สรุปจาก proposal_review.md)
1. 🔴 DIV ยังไม่ได้วัดจริง (เกณฑ์ 20% อ้างลอย) → **แก้แล้วด้วย Base Sheet (ข้อ 3)**
2. 🔴 Hausman อาจเลือก FE ซึ่งลบ DIV (time-invariant) → **ประกาศใช้ RE เป็นหลัก**
3. 🔴 สมการไม่มี dummy ไตรมาส → เพิ่ม Q2/Q3/Q4
4. 🔴 ไม่จัดการโควิด (BP fail) → ตัด 20 จุด rev_low หรือใส่ COVID dummy
5. 🟠 Durbin-Watson ผิดบริบท panel → ใช้ Wooldridge test
6. 🟠 t-test ต้องทำระดับบริษัท (n=3 vs 7) ไม่ใช่ระดับ obs
7. 🟠 สูตร CCC/ROA/ROE: รายไตรมาส (90/91/92 วัน) + ยอดเฉลี่ย + ฐาน broad

## 2. ผลวิเคราะห์สถิติจริง (สคริปต์ใหม่ใน `scripts/`)

| สคริปต์ | ทำอะไร | ผลหลัก |
|---------|--------|--------|
| `analysis_run.py` (เดิม) | VIF + Pooled/FE/RE + Hausman | VIF < 2 ทุกตัว (ไม่มี multicollinearity) |
| `analysis_run_fixed.py` (เดิม) | RE + ฤดูกาล + ตัดโควิด + clustered SE | **DIV ไม่มีนัยสำคัญทุกสมการ; LEV(−) + ฤดูกาล(Q2/Q3−) มีนัยสำคัญ** |
| `wooldridge_test.py` | Wooldridge serial-correlation (Drukker 2003) | มี autocorrelation ทุกสมการ (p=0.002–0.016) |
| `analysis_noseason_nocluster.py` | เทียบ ตัดฤดูกาล + SE ธรรมดา | ไม่คุม → R² ตก + ค่า p เล็กเทียม (CCC DIV 0.34→0.09) |
| `power_div.py` | Power analysis กลุ่ม DIV | n=3 เล็กเกินไป; ต้อง ~10 บริษัท/กลุ่ม (ทิศ**ตรงข้าม**สมมติฐาน) |
| `split_5v5.py` | 3v7 vs 5v5 (ย้าย CENTEL/ERW) | ผลไวต่อการจัดกลุ่มมาก → ห้ามฝืนบาลานซ์ |
| `annual_vs_quarterly.py` | รายไตรมาส vs รวมรายปี | DIV ยังไม่มีนัยสำคัญทั้งคู่ (N บริษัทคงที่) |
| `report_lineitems.py` | บรรทัดงบที่ดึงต่อบริษัท (DSO/DIO/DPO) | ASIA รวม 2 บรรทัดเจ้าหนี้; ERW การค้าล้วน; MINT กันลูกหนี้ไม่หมุนเวียน |

**ข้อสรุปเชิงสถิติ:** ตัวขับความสามารถในการทำกำไรจริง = **หนี้ (LEV, −) และฤดูกาล** ไม่ใช่การกระจาย
ความเสี่ยงต่างประเทศ (DIV) เมื่อคุมขนาด/หนี้/ฤดูกาลแล้ว

## 3. ยืนยันการจัดกลุ่ม DIV ด้วยข้อมูล segment จริง (Base Sheet)

ผู้ใช้ส่ง "Analytic - กลุ่มตัวอย่าง.csv" = สัดส่วนรายได้ใน/นอกประเทศจริง FY2564–2568

**% รายได้ต่างประเทศเฉลี่ย 5 ปี:** SHR 84.8% · MINT 78.4% · DUSIT 39.1% (→ DIV=1)
ASIA 12.5% · CENTEL 10.1% · ERW 9.7% · อื่น ๆ 0% (→ DIV=0)

- ✅ ยืนยัน 3v7 ด้วยเกณฑ์ 20% จริง
- ✅ **เกณฑ์ 20% ตกในช่องว่างธรรมชาติ** (สูงสุดในประเทศ ASIA 19% ↔ ต่ำสุดต่างประเทศ DUSIT 25%)
- ✅ ไม่มีบริษัทข้ามเส้น 20% ในปีใดเลย → กลุ่ม time-invariant สมเหตุสมผล
- อ้างอิงเกณฑ์: Rugman (1981) 10%, Rugman & Verbeke (2004) 20%/50%, Sullivan (1994) DOI ต่อเนื่อง

## 4. วิชวลไลซ์ — แผนที่การไหลของรายได้ (`viz/`)

`viz/tour_revenue_worldmap.html` — แผนที่โลก sleek dark-grey (self-contained)
- ไทยเป็นฐานเดียว · เส้นแยกสีตามบริษัท (MINT/SHR/DUSIT/CENTEL/ERW) ไปแหล่งรายได้ต่างประเทศ
- แผงซ้าย: bar chart เทียบ % ต่างประเทศ (เส้นประ 20%) + ไอคอน + สลับ Value/Share
- ข้อมูล: % จาก Base Sheet (จริง) + แบ่งย่อยรายประเทศเป็นค่าประมาณจากรายงานบริษัท (ต้องยืนยัน)
- Build ใหม่: `python viz/build_worldmap.py` (ต้องมี `viz/countries.js` — Natural Earth 110m)

## 5. สิ่งที่ยังทำต่อได้

- ดึง % รายประเทศจริงจากหมายเหตุ segment (ตอนนี้แบ่งย่อยรายประเทศเป็นค่าประมาณ)
- ทำ DIV แบบต่อเนื่อง (% ต่างประเทศจริงต่อปี) แทน dummy — ข้อมูล Base Sheet พร้อมแล้ว
- Robustness เกณฑ์ 10%/50% ตามที่เขียนในบท 6

## หมายเหตุ environment
- ใช้ `python` (ไม่ใช่ `python3` — เป็น shim เสียในเครื่องนี้)
- ตั้ง `PYTHONUTF8=1` กัน print ภาษาไทย/สัญลักษณ์ crash (cp874)
- deps: openpyxl, xlrd, pyyaml, pandas, statsmodels, linearmodels, scipy, python-docx, PyMuPDF
