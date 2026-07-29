# TOUR Sector — Quarterly Financials (5-Year)

ดึงและคำนวณตัวชี้วัดการเงินรายไตรมาสของหุ้นกลุ่มท่องเที่ยว (TOUR) ในตลาดหลักทรัพย์ไทย

## ขอบเขต

- **บริษัท (10):** ASIA, CENTEL, DUSIT, ERW, MANRIN, MINT, OHTL, SHANG, SHR, VRANDA
- **ช่วงเวลา:** 5 ปี (2564–2568) × 4 ไตรมาส = **200 จุดข้อมูลต่อ 1 ตัวชี้วัด**
- **ตัวชี้วัดเป้าหมาย (7):** ROA, ROE, NPM, DSO, DIO, DPO, CCC

## แหล่งข้อมูล (ต่อ 1 ไตรมาส)

**ทางที่แนะนำ — ไฟล์งบเต็มจาก SET (.xls ไฟล์เดียว):** มีชีต `BS` (งบดุล) + `PL` (งบกำไรขาดทุน) + `CF` (กระแสเงินสด) ในไฟล์เดียว — `scripts/extract_set.py` ดึงอัตโนมัติได้

> **ข้อค้นพบสำคัญ:** 7 ตัวชี้วัดเป้าหมาย (ROA, ROE, NPM, DSO, DIO, DPO, CCC) คำนวณได้จาก **PL + BS ล้วน — ไม่ต้องใช้ MD&A** (MD&A เดิมป้อนแค่ EBITDA/core profit ซึ่งไม่ใช่ตัวเป้าหมาย) ทำให้ไฟล์ SET ชุดเดียวพอ

MD&A ยังมีประโยชน์เสริม (EBITDA, ตัวเลข core, อัตราส่วนที่บริษัทรายงานเองสำหรับ reverse-eng) แต่ไม่จำเป็นต่อ 7 ตัวหลัก

**ข้อควรระวังที่เจอจริง (CENTEL 2568):**
- งบไตรมาสมีงบกำไรขาดทุน **2 ชุดในชีตเดียว** (3 เดือน + สะสม) → ใช้เฉพาะชุด 3 เดือน (extractor จัดการให้)
- **หน่วยต่างกัน**: งบไตรมาส=พันบาท, งบรายปีตรวจสอบ=บาท → extractor อ่านหน่วยจาก header เอง
- **ชื่อชีต/รายการต่าง**: `'PL'` vs `'PL '`, "กำไรสำหรับงวด" vs "กำไรสำหรับปี" → จัดการผ่าน `mapping/line_items.yml`

## โครงสร้างโฟลเดอร์

```
tour-finance/
├── data/raw/<COMPANY>/<YEAR>/     # ไฟล์ดิบจาก SET (CSV/PDF) แยกตามบริษัท/ปี
│   └── ตั้งชื่อไฟล์: Q<n>_mda.pdf, Q<n>_income.csv, Q<n>_balance.csv
├── scripts/                        # สคริปต์ build ที่รันซ้ำได้ (build5yr.py ฯลฯ)
├── output/                         # ไฟล์ Excel ผลลัพธ์ (<COMPANY>_5yr.xlsx)
└── docs/                           # methodology + นิยามตัวชี้วัด
```

### ข้อตกลงการตั้งชื่อไฟล์ดิบ

ใน `data/raw/<COMPANY>/<YEAR>/` ให้ตั้งชื่อไฟล์ตามไตรมาส:

| ประเภท | รูปแบบชื่อ | ตัวอย่าง |
|--------|-----------|----------|
| งบเต็ม SET (.xls) | `Q<n>_FS.xls` / `FY_FS.xls` | `Q1_FS.xls`, `FY_FS.xls` |
| MD&A (ถ้ามี, เสริม) | `Q<n>_mda.pdf` | `Q1_mda.pdf` |

> ปีใช้ พ.ศ. (2564–2568). ไตรมาส Q1–Q4. ไฟล์ `FY_FS.xls` = งบรายปีตรวจสอบแล้ว (ใช้ทำ Q4 = FY − Q1−Q2−Q3)

### การเติมงบที่เหลือ (2564–2567) — คำสั่งเดียวจบ

`ingest.py` **ตรวจบริษัท+ปี+ไตรมาสจากเนื้อหางบเอง** แล้วจัดเข้าโฟลเดอร์ที่ถูกต้อง +
คำนวณใหม่ทั้งหมด ไม่ต้องตั้งชื่อไฟล์/แยกโฟลเดอร์เอง โยน zip หรือโฟลเดอร์เข้ามาได้เลย:

```bash
cd tour-finance
python3 scripts/ingest.py ~/downloads/งบปี2567.zip   # แตก zip ซ้อน + จัดเก็บ + rebuild
python3 scripts/ingest.py <ไฟล์.xls> <ไฟล์2.xls> ...  # ระบุไฟล์ตรงๆ ก็ได้
python3 scripts/ingest.py --rebuild                   # คำนวณใหม่จาก data/raw ที่มี (ไม่ import)
```

ระบบข้ามไฟล์ฉบับอังกฤษ (`_e_`) อัตโนมัติ ใช้ฉบับไทยเป็นหลัก และจะพ่นสรุปว่าบริษัท/ปีไหนครบ 4 ไตรมาสแล้ว

หลัง ingest ให้สร้างรายงานใหม่ (ทุกไฟล์ผูกสูตรสด เติมปีไหนคำนวณเอง):

```bash
python3 scripts/validate.py                    # ตรวจความถูกต้อง (balance/flow/ช่วงค่า)
python3 scripts/build_combined_linked.py       # → output/TOUR_all_linked.xlsx (ไฟล์รวมหลัก)
python3 scripts/annual_avg_compare.py 2567 --xlsx   # เทียบ 2จุด/5จุด ปีที่เพิ่งเติม
```

## การใช้งาน — สร้างเทมเพลต

`scripts/build_5yr.py` สร้างโครง Excel 5 ปีเต็ม (formula ครบทั้ง 20 ไตรมาส เชื่อมไป input sheets — เติมข้อมูลปีไหน คอลัมน์นั้นคำนวณเอง)

```bash
cd tour-finance/scripts
pip install openpyxl
python3 build_5yr.py CENTEL     # → output/CENTEL_5yr.xlsx
python3 build_5yr.py --all      # สร้างครบทั้ง 10 บริษัท
```

> ต่างจาก `MINT_test_5yr_v4.xlsx` (ต้นแบบที่ทำมือ มี formula เฉพาะปี 2568) — generator วาง formula ครบทุกไตรมาส พร้อมเติมข้อมูลปี 2564–2567

## สถานะปัจจุบัน

- [x] **pipeline + generator ครบ** — ingest → extract → validate → รายงานสูตรสด (พร้อมรับข้อมูล)
- [x] **ทั้ง 10 บริษัท / 2568** — ครบ 4 ไตรมาส + FY (validate ผ่าน 312 จุด, 0 error)
- [x] **MINT / 2566–2567** — มีเฉพาะงบรายปี (FY)
- [ ] **2564–2567 อีก 9 บริษัท + MINT รายไตรมาส** — เหลือ ~160 จุด (ปัจจุบัน 40/200)

> เติมได้ทันทีด้วย `python3 scripts/ingest.py <zip>` (ดู "การเติมงบที่เหลือ" ด้านบน)
> โครง 5 ปีในไฟล์ผลลัพธ์วางช่องรอไว้แล้ว — เติมปีไหน ตาราง/อัตราส่วน/กราฟฤดูกาลอัปเดตเอง

### ผลลัพธ์ที่มีตอนนี้ (`output/`)

| ไฟล์ | คือ |
|------|-----|
| `TOUR_all_linked.xlsx` | **ไฟล์รวมหลัก** — 10 บริษัท ราย FY + รายไตรมาส สูตรสดทั้งหมด |
| `metrics_all.csv` | ชุดข้อมูลดิบ 7 ตัวชี้วัด รายไตรมาส |
| `ratios_report.xlsx` | รายงานสรุป 4 ชีต (ค่าคงที่) |
| `seasonal_2568.html` | กราฟ/heatmap ฤดูกาลรายไตรมาส (interactive) |
| `annual_avg_compare_2568.xlsx` | เทียบค่าเฉลี่ยงบดุล 2จุด vs 5จุด |
| `workflow.html` | ผังการทำงานทั้งหมด |

## โครงไฟล์ Excel ต้นแบบ (7 ชีต)

จาก `MINT_test_5yr_v4.xlsx`:

1. `MDA_Cumulative_Input` — ข้อมูลสะสมจาก MD&A
2. `BalanceSheet_Input`
3. `IncomeStatement_Actual`
4. `<COMPANY>_Quarterly` — 20 คอลัมน์ (5 ปี × 4 ไตรมาส)
5. `Methodology_CFA`
6. `Methodology_ReverseEng`
7. `Notes`

## Methodology (สรุป)

- **หลัก:** สูตร CFA / Damodaran มาตรฐาน — ค่าเฉลี่ยงบดุล ÷ (รายได้ หรือ ต้นทุนขาย) × จำนวนวัน
- **เสริม:** reverse-engineer เทียบกับตัวเลขที่แต่ละบริษัทเปิดเผยเอง เพื่อหา assumption ร่วม เมื่อข้อมูลครบทุกบริษัท

รายละเอียดใน [`docs/methodology.md`](docs/methodology.md) และ [`docs/metrics.md`](docs/metrics.md)
