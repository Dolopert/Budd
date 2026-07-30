# data/segment — ที่เก็บข้อมูลสัดส่วนรายได้ใน/นอกประเทศ (single source สำหรับแผนที่ viz)

โฟลเดอร์นี้คือ **แหล่งข้อมูลเดียว** ที่ `viz/build_worldmap.py` อ่านไปสร้าง Year Slider + แผนที่
แก้ CSV ที่นี่ที่เดียว แล้ว rebuild — ไม่มีการ hardcode ตัวเลขในโค้ด viz อีก

## ไฟล์

| ไฟล์ | คือ | ที่มา |
|------|-----|-------|
| `../segment_base.csv` | Base Sheet ต้นฉบับ (in/out รายได้ 10 บริษัท × 5 ปี) | ผู้ใช้ยืนยัน (งบ segment) |
| `segment_by_year.csv` | สรุป normalize → ล้านบาท + % + ธง DIV รายปี | สร้างจาก `scripts/build_segment.py` |
| `geo_flows.csv` | รายภูมิภาค/ประเทศบนแผนที่ (arcs) | MINT จริง · อื่น ๆ ประมาณการ |
| `notes/<TICKER>/<ปี>/` | โฟลเดอร์รอรับ **ภาพหมายเหตุ segment ภูมิศาสตร์** | ผู้ใช้อัปโหลด |

## workflow เพิ่มข้อมูลรายประเทศจริง (ยืนยันทีละบริษัท)

1. วางภาพหน้าหมายเหตุ **"ข้อมูลจำแนกตามส่วนงานภูมิศาสตร์ — รายได้"** ลงใน
   `notes/<TICKER>/<ปีของฉบับงบ>/` เช่น `notes/SHR/2568/geo.png`
   (งบ FY หนึ่งฉบับให้ 2 ปี: ปีปัจจุบัน + ปีก่อน)
2. สกัดตัวเลขรายภูมิภาค → เพิ่มแถวใน `geo_flows.csv` ตั้ง `verified=1` + ระบุ `source`
   ลบ/แทนแถวเดิมของบริษัทนั้นที่ `verified=0` (ประมาณการ)
3. rebuild: `PYTHONUTF8=1 python viz/build_worldmap.py`

## คอลัมน์ geo_flows.csv

`ticker, year, region, cont, value_M, pct, lat, lon, verified, source`
- `cont` = ทวีป/กลุ่ม (Europe/Asia/Oceania/Americas/Africa/Middle East/Other) — ใช้ทำ toggle ทวีป↔ประเทศ
- `value_M` = ล้านบาท · `pct` = % ของรายได้ต่างประเทศบริษัทนั้น
- `verified` = 1 ยืนยันจากงบ / 0 ประมาณการ (viz ติดป้าย "ประมาณการ")

## rebuild ทั้งชุด

```
PYTHONUTF8=1 python scripts/build_segment.py     # อัปเดต segment_by_year.csv จาก Base Sheet
PYTHONUTF8=1 python viz/build_worldmap.py         # สร้าง tour_revenue_worldmap.html
```
