# PLAN.md — Thai Fund Screener (SEC Open Data)

วางไฟล์นี้ไว้ root ของโปรเจกต์แล้วบอก Claude Code ว่า "อ่าน PLAN.md ก่อนเริ่มทุก session"
ทำทีละ Task ห้ามข้าม — Task N ต้องรันผ่านและตรวจแล้วจึงเริ่ม Task N+1

## Context Capsule (ใช้เปิด session ใหม่ทุกครั้ง)

```
Project: thai-fund-screener — ดึงข้อมูลกองทุนรวมทุกกองในไทยจาก SEC Open Data API
         แล้วคัดกรอง Active/Passive จัดอันดับ Top 25+25 เปรียบเทียบนโยบายและความเสี่ยง
Stack: Python 3.11+, requests, pandas, openpyxl
Current state: [อัปเดตทุกครั้งว่า Task ไหนเสร็จแล้ว]
This session goal: [Task เดียวจาก Launch Plan]
Key decisions: SEC API เป็นแหล่งข้อมูลหลัก / rate limit 5 req/s / เก็บ raw JSON แยกจาก
               ข้อมูลที่ clean แล้ว / classify passive จาก keyword ในนโยบาย+ชื่อกอง
Files relevant: [เฉพาะไฟล์ที่จะแตะใน session นี้]
```

## F — Frame

- **Goal:** ระบบดึงข้อมูลกองทุนรวมทุกกองในไทย (~2,000+ กอง) จาก SEC Open Data API แล้วคัด
  กรองออกมาเป็นตารางเปรียบเทียบ Top 25 กองเชิงรุก + Top 25 กองเชิงรับ พร้อมนโยบาย ระดับ
  ความเสี่ยง ผลตอบแทน และค่าธรรมเนียม
- **Done means:** รัน pipeline จบได้ไฟล์ `output/top25_comparison.xlsx` ที่มี 2 ชีต (Active /
  Passive) ข้อมูลครบทุกคอลัมน์ ไม่มีกองซ้ำ ไม่มีกองที่ปิดขายปนมา
- **Constraints:** SEC API ต้องใช้ key ส่วนตัว (env: `SEC_API_KEY`), rate limit ~5 req/s, บาง
  endpoint คืน 204 (ไม่มีข้อมูล), เฟสดึงรายกองใช้เวลานาน ต้อง resume ได้
- **Out of scope:** UI/เว็บแอป, การซื้อขายจริง, การพยากรณ์ผลตอบแทน, ข้อมูล intraday

## A — Analyze (ชิ้นงาน + dependency)

| # | ชิ้นงาน | ขนาด | ขึ้นกับ |
|---|---------|------|---------|
| 1 | API client (auth, retry, rate limit, cache) | M | - |
| 2 | Fetch master list (AMC → funds ทุกกอง) | S | 1 |
| 3 | Fetch รายละเอียดรายกอง (policy/performance/fee/risk) + resume | L | 2 |
| 4 | Data cleaning (ตัดกองปิด, กองเฉพาะกลุ่ม, รวม share class) | M | 3 |
| 5 | Classifier Active/Passive | M | 4 |
| 6 | Ranking + คัด Top 25+25 | M | 5 |
| 7 | Export Excel เปรียบเทียบ | S | 6 |

ความเสี่ยงสูงสุด = ชิ้น 3 (schema จริงของ performance/fee ยังไม่เคยเห็น) → ทำ spike ก่อน: ยิงกอง
ตัวอย่าง 3 กอง dump raw JSON มาดูโครงสร้างจริงก่อนเขียน parser

## B — Blueprint

- `client.py` — Input: URL / Output: dict หรือ None / State: request count สำหรับ rate limit
- `fetch_details.py` — Input: all_funds.json / Output: raw/{proj_id}.json ทีละไฟล์ / State:
  checkpoint.json (ล้มแล้วรันต่อได้ไม่เริ่มใหม่)
- `classify.py` — Input: policy_desc + fund_name / Output: คอลัมน์ management_style /
  กติกา: เจอ keyword ดัชนี ("ดัชนี", "index", "SET50", "S&P", "Nasdaq", "MSCI", "ETF",
  "passive") → Passive, ไม่เจอ → Active, กำกวม → flag ให้รีวิวมือ

```
thai-fund-screener/
├── PLAN.md              ← ไฟล์นี้ (source of truth)
├── .env                 ← SEC_API_KEY (ห้าม commit)
├── src/
│   ├── client.py        ← SEC API client: get() พร้อม retry/rate-limit/บันทึก cache
│   ├── fetch_master.py  ← ดึง AMC ทั้งหมด → กองทุนทุกกอง → data/raw/all_funds.json
│   ├── fetch_details.py ← ไล่ดึง policy/performance/fee รายกอง, resume จาก checkpoint
│   ├── clean.py         ← กรองสถานะปิด, ตัด AI/UI class, normalize คอลัมน์
│   ├── classify.py      ← Active/Passive จาก keyword + benchmark type
│   ├── rank.py          ← คะแนน = ผลตอบแทน 1/3/5 ปี + Sharpe (ถ้ามี) - ค่าธรรมเนียม
│   └── export.py        ← สร้าง top25_comparison.xlsx (2 ชีต)
├── data/
│   ├── raw/             ← JSON ดิบจาก API (cache, ไม่แก้ไขมือ)
│   ├── checkpoint.json  ← proj_id ที่ดึงแล้ว (ใช้ resume)
│   └── processed/       ← CSV ที่ clean แล้ว
└── output/
    └── top25_comparison.xlsx
```

## L — Launch Plan

- [ ] Task 0: Spike — ยิง API จริง 3 กอง (policy/performance/fee) dump raw JSON
      มาดู schema จริง แล้วอัปเดต PLAN.md ส่วน parser ให้ตรงความจริง
- [ ] Task 1: client.py + test ยิง /fund/amc สำเร็จ (พิมพ์จำนวน บลจ.)
- [ ] Task 2: fetch_master.py → all_funds.json ครบ ตรวจ: จำนวนกอง > 1,500
- [ ] Task 3: fetch_details.py + checkpoint/resume ตรวจ: kill กลางทางแล้วรันต่อได้
- [ ] Task 4: clean.py ตรวจ: ไม่มีกองสถานะปิด, จำนวนหลัง clean สมเหตุสมผล
- [ ] Task 5: classify.py ตรวจ: สุ่ม 20 กองเทียบกับ Factsheet จริง ถูก ≥ 18/20
- [ ] Task 6: rank.py ตรวจ: กองที่ติด Top ไม่มีค่า null ในคอลัมน์คะแนน
- [ ] Task 7: export.py ตรวจ: เปิด Excel แล้วครบ 2 ชีต × 25 แถว

กติกา: 1 Task = 1 session ของ Claude Code ถ้าจะข้ามไป Task อื่น เปิด session ใหม่ พร้อม Context
Capsule เสมอ

## E — Edge Cases & Risks

- API คืน 204/404 บางกอง → บันทึกเป็น "no data" ใน checkpoint อย่า retry ซ้ำไม่รู้จบ
- โดน 429 rate limit → backoff 5 วิแล้วลองใหม่ สูงสุด 3 ครั้ง
- กองหนึ่งมีหลาย share class (-A, -D, -SSF, -RMF) → เลือก class สะสมมูลค่าหลักตัวเดียว กันติด
  Top ซ้ำ
- ชื่อกองมี "ดัชนี" แต่เป็น active enhanced index → classifier ต้องมี flag "ambiguous"
- ผลตอบแทนบางกองเป็น null (กองใหม่ < 1 ปี) → ตัดออกจาก ranking ที่ต้องใช้ 3/5 ปี
- Encoding ภาษาไทย → เขียน CSV ด้วย utf-8-sig เสมอ
- อย่า hardcode API key ในโค้ด → อ่านจาก env เท่านั้น และใส่ .env ใน .gitignore
