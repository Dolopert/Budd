# ผังการทำงานทั้งหมด — TOUR Quarterly Finance Pipeline

จากไฟล์งบที่ตลาดหลักทรัพย์เผยแพร่ ไปจนถึงอัตราส่วน 7 ตัวและรายงานสูตรสด
(หน้านี้ GitHub เรนเดอร์ Mermaid ให้อัตโนมัติ · เวอร์ชันโต้ตอบ: `output/workflow.html`)

```mermaid
flowchart TD
  A["ไฟล์งบ SET · .xls / .xlsx / .xlsm · zip ซ้อนได้ · อัปโหลด"]

  subgraph P2["② นำเข้า — ingest.py"]
    direction TB
    B["find_statements — เดินหาไฟล์ใน zip ซ้อน"]
    C["ตรวจ ticker + งวด — ข้ามไฟล์อังกฤษ _e_"]
    D["คัดลอกเข้าคลัง — data/raw / TICKER / ปี"]
    B --> C --> D
  end

  subgraph P3["③ สกัดข้อมูล — extract_set.py"]
    direction TB
    E["open_book — ตรวจชนิดไฟล์ด้วย magic-byte"]
    F["หาชีต PL · BS · CF — จับจากเนื้อหา"]
    G["ตรวจงวด·ปี·หน่วย — เลือกคอลัมน์งบรวม งวดปัจจุบัน"]
    H["จับคู่รายการผ่าน alias — line_items.yml"]
    E --> F --> G --> H
  end

  subgraph P4["④ คำนวณ"]
    direction TB
    J["de-cumulate — Q4 = FY − Q1 − Q2 − Q3"]
    K["เฉลี่ยงบดุลแบบ chain — ปลายไตรมาสก่อน → ปลายไตรมาสนี้"]
    L["7 ตัวชี้วัด — NPM ROA ROE · DSO DIO DPO CCC"]
    J --> K --> L
  end

  I{"Balance check — สินทรัพย์ = หนี้สิน + ทุน ?"}
  X["หยุด + แจ้ง error — fail-loud"]
  M[("metrics_all.csv — ชุดข้อมูลหลัก")]

  subgraph P5["⑤ ตรวจสอบ — validate.py"]
    N["312 การตรวจ — balance · flow · ช่วง GM · restatement"]
  end

  subgraph P6["⑥ ผลลัพธ์"]
    direction TB
    O1["ตารางอัตราส่วน (Excel) — report.py → ratios_report.xlsx · build_combined_linked.py → TOUR_all_linked.xlsx"]
    O2["การวิเคราะห์ — annual_avg_compare.py (2จุด/5จุด) · seasonal_2568.html (กราฟฤดูกาล)"]
    O3["เอกสารระเบียบวิธี — methodology.md (DL-1 DL-2 อ้างอิงสูตร)"]
  end

  A --> B
  D --> E
  H --> I
  I -->|ไม่ผ่าน| X
  I -->|ผ่าน| J
  L --> M --> N
  N --> O1
  N --> O2
  N --> O3
```

## หลักสำคัญ 3 อย่างที่ผังนี้บังคับ

1. **fail-loud** — ถ้า balance ไม่ตรง หรือหา required item ไม่เจอ ระบบหยุดทันที ไม่ปล่อยเลขผิดผ่าน
2. **de-cumulation** — งบไตรมาสไทยเป็นตัวเลข 3 เดือน แต่ Q4 ไม่มีแยก ต้องคำนวณ `FY − Q1 − Q2 − Q3`
3. **chained averaging** — งบไตรมาสเทียบ "ต้นปี" เสมอ จึงต้องต่อยอดปลายไตรมาสก่อนหน้าเป็นต้นงวด เพื่อให้ค่าเฉลี่ยงบดุลถูกต้อง

ทุกอัตราส่วนยึดฐาน CFA (นิยามเดียว สม่ำเสมอทุกบริษัท) ตาม [`methodology.md`](methodology.md)
