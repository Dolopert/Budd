# -*- coding: utf-8 -*-
# สร้างแผนที่รายได้ต่างประเทศ + Year Slider 5 ปี (2564-2568)
# อ่านข้อมูลจาก CSV single-source ใน data/segment/ (ไม่ hardcode ตัวเลขในโค้ด):
#   - segment_by_year.csv : สัดส่วนใน/นอกประเทศรายปี (จาก Base Sheet ผู้ใช้ยืนยัน)
#   - geo_flows.csv       : รายภูมิภาค/ประเทศบนแผนที่ (MINT จริง, อื่น ๆ ประมาณการ)
# แก้ CSV แล้ว rebuild:  PYTHONUTF8=1 python viz/build_worldmap.py
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SEG = os.path.join(ROOT, 'data', 'segment')
LAND = open(os.path.join(HERE, 'countries.js'), encoding='utf-8').read()

YEARS = [2564, 2565, 2566, 2567, 2568]          # พ.ศ.
YEARS_CE = [2021, 2022, 2023, 2024, 2025]        # ค.ศ. (แสดงคู่บน slider)


def load_by_year():
    """segment_by_year.csv -> {ticker: {fp[5], tot[5], intl[5]}} เรียงตามปี"""
    data = {}
    for r in csv.DictReader(open(os.path.join(SEG, 'segment_by_year.csv'), encoding='utf-8-sig')):
        tk = r['ticker']; d = data.setdefault(tk, {'fp': [0] * 5, 'tot': [0] * 5, 'intl': [0] * 5})
        j = YEARS.index(int(r['year']))
        d['fp'][j] = float(r['intl_pct']); d['tot'][j] = float(r['total_M']); d['intl'][j] = float(r['intl_M'])
    return data


def load_flows(data):
    """geo_flows.csv -> arc แบบ year-aware: แต่ละ (บริษัท, ภูมิภาค) มี thb[5]/pct[5]
    ปีที่มีข้อมูลจริงใช้ค่านั้น · ปีที่ขาด (บริษัทประมาณการที่มีปีเดียว) ปรับตามสัดส่วน
    รายได้ต่างประเทศของบริษัทนั้นในปีนั้น (intl ratio) เทียบปีฐานที่มีข้อมูล"""
    rows = list(csv.DictReader(open(os.path.join(SEG, 'geo_flows.csv'), encoding='utf-8-sig')))
    keyed = {}                                        # (co,region) -> {year: {v,cont,lat,lon,ok}}
    for r in rows:
        k = (r['ticker'], r['region'])
        keyed.setdefault(k, {'meta': {'co': r['ticker'], 'country': r['region'], 'cont': r['cont'],
                                      'lat': float(r['lat']), 'lon': float(r['lon']),
                                      'ok': int(r['verified'])}, 'y': {}})
        keyed[k]['y'][int(r['year'])] = float(r['value_M'])
    out = []
    for k, rec in keyed.items():
        co = rec['meta']['co']; ys = rec['y']
        base_y = max(ys)                              # ปีฐานที่มีข้อมูล (ล่าสุด)
        intl = data[co]['intl']
        thb, pct = [], []
        for j, yr in enumerate(YEARS):
            if yr in ys:
                v = ys[yr]
            else:                                     # ปรับตามสัดส่วน intl ของบริษัทในปีนั้น
                bj = YEARS.index(base_y)
                ratio = (intl[j] / intl[bj]) if intl[bj] else 0
                v = round(ys[base_y] * ratio, 1)
            thb.append(v)
            pct.append(round(v / intl[j] * 100) if intl[j] else 0)
        out.append({**rec['meta'], "thb": thb, "pct": pct})
    return out


_DATA = load_by_year()
CFG = {"YEARS": YEARS, "YEARS_CE": YEARS_CE, "DATA": _DATA, "FLOWS": load_flows(_DATA)}

HTML = r'''<style>
  :root{--bg:#151619;--panel:#191a1d;--card:#202225;--line:#2b2d31;--land:#2f3135;--coast:#45484e;
    --t1:#ecedf0;--t2:#9a9ea7;--t3:#696d76;--home:#4ade80;--hot:#fbbf24;
    --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}
  *{box-sizing:border-box}
  .app{background:var(--bg);color:var(--t1);font-family:var(--font);border-radius:14px;overflow:hidden;display:grid;grid-template-columns:296px 1fr;height:664px}
  .sr-only{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0,0,0,0)}
  .panel{background:var(--panel);border-right:1px solid var(--line);overflow-y:auto;padding:16px 15px;scrollbar-width:thin}
  .eyebrow{font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--home);font-weight:700;margin:0 0 5px}
  .h1{font-size:18px;font-weight:750;letter-spacing:-.02em;line-height:1.12;margin:0}
  .lede{font-size:11.5px;color:var(--t2);line-height:1.45;margin:6px 0 14px}
  .toggle{display:flex;background:#101113;border:1px solid var(--line);border-radius:9px;padding:3px;gap:2px;margin-bottom:16px}
  .toggle button{flex:1;font:inherit;font-size:11.5px;font-weight:600;color:var(--t2);background:none;border:0;padding:6px;border-radius:6px;cursor:pointer;transition:.13s}
  .toggle button.on{background:#2f3237;color:var(--t1)}
  .lbl{font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:var(--t3);font-weight:700;margin:0 0 9px;display:flex;align-items:center;gap:6px}
  .barrow{display:grid;grid-template-columns:58px 1fr 40px;gap:9px;align-items:center;padding:4px 4px;border-radius:7px;cursor:pointer;transition:.12s}
  .barrow:hover,.barrow.hot{background:#232528}
  .barrow.on{background:#26292e;box-shadow:inset 0 0 0 1px #3a3d44}
  .barrow .tk{font-size:11.5px;font-weight:700;display:flex;align-items:center;gap:6px;color:var(--t1)}
  .dot{width:8px;height:8px;border-radius:50%;flex:none}
  .track{height:8px;background:#26282c;border-radius:5px;position:relative}
  .fill{display:block;height:100%;min-width:2px;border-radius:5px;transition:width .5s cubic-bezier(.4,0,.2,1)}
  .th20{position:absolute;top:-2px;bottom:-2px;left:20%;width:1px;background:repeating-linear-gradient(#5f6f92 0 2px,transparent 2px 4px)}
  .bval{font-size:10.5px;text-align:right;font-family:var(--mono);color:var(--t2);font-weight:600}
  .note{font-size:10px;color:var(--t3);margin:7px 2px 16px;display:flex;align-items:center;gap:5px}
  .sect{border-top:1px solid var(--line);padding-top:15px;margin-top:4px}
  .tiles{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:6px}
  .tile{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 10px}
  .tile .k{font-size:9.5px;letter-spacing:.06em;text-transform:uppercase;color:var(--t3);font-weight:600}
  .tile .v{font-size:16px;font-weight:750;font-family:var(--mono);margin-top:2px;letter-spacing:-.02em}
  .dhead{display:flex;align-items:center;gap:8px;margin:2px 0 10px}
  .dhead .nm{font-size:15px;font-weight:750}
  .chip{font-size:9.5px;font-weight:700;padding:2px 8px;border-radius:20px;color:#08111f}
  .drow{display:grid;grid-template-columns:1fr 44px;gap:8px;align-items:center;padding:4px 0}
  .drow .rl{display:flex;align-items:center;gap:6px;font-size:12px;min-width:0}
  .drow .rl span{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .drow .mt{grid-column:1/3;height:5px;background:#26282c;border-radius:4px;overflow:hidden;margin-top:1px}
  .drow .mt i{display:block;height:100%;border-radius:4px}
  .drow .rv{font-size:11px;text-align:right;font-family:var(--mono);color:var(--t2)}
  .ic{width:13px;height:13px;flex:none;color:var(--t3)}
  .maph{position:relative}
  #map{position:absolute;inset:0;width:100%;height:100%;display:block}
  .legend{position:absolute;right:14px;top:13px;background:#191a1de6;backdrop-filter:blur(7px);border:1px solid var(--line);border-radius:10px;padding:9px 11px;font-size:10.5px;color:var(--t2);pointer-events:none}
  .geoseg{position:absolute;left:14px;top:13px;display:flex;align-items:center;background:#101113ee;border:1px solid var(--line);border-radius:9px;padding:3px;gap:2px;backdrop-filter:blur(6px);z-index:2}
  .geoseg .gl{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);font-weight:700;padding:0 7px 0 5px}
  .geoseg button{font:inherit;font-size:11px;font-weight:600;color:var(--t2);background:none;border:0;padding:5px 11px;border-radius:6px;cursor:pointer;transition:.13s}
  .geoseg button.on{background:#2f3237;color:var(--t1)}
  .legend .lg{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);font-weight:700;margin-bottom:5px}
  .legend span{display:flex;align-items:center;gap:7px;padding:1px 0}
  .legend i{width:14px;height:3px;border-radius:2px}
  .esttag{position:absolute;left:14px;bottom:14px;background:#191a1de6;backdrop-filter:blur(7px);border:1px solid var(--line);border-radius:9px;padding:7px 10px;font-size:9.5px;color:var(--t3);max-width:220px;line-height:1.4}
  .esttag b{color:#fbbf24;font-weight:700}
  /* --- Year slider --- */
  .yearwrap{position:absolute;left:0;right:0;bottom:0;padding:12px 18px 14px;background:linear-gradient(transparent,#151619cc 34%);pointer-events:none}
  .yearbar{pointer-events:auto;background:#101113ee;border:1px solid var(--line);border-radius:12px;padding:9px 14px 11px;backdrop-filter:blur(6px)}
  .yearhd{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px}
  .yearhd .yv{font-size:19px;font-weight:800;font-family:var(--mono);letter-spacing:-.02em}
  .yearhd .yce{font-size:10.5px;color:var(--t3);font-weight:600}
  .yearhd .ytag{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--home);font-weight:700}
  #yslider{-webkit-appearance:none;appearance:none;width:100%;height:5px;border-radius:4px;background:#2b2d31;outline:none;cursor:pointer}
  #yslider::-webkit-slider-thumb{-webkit-appearance:none;width:17px;height:17px;border-radius:50%;background:var(--home);border:3px solid #101113;box-shadow:0 0 0 1px #4ade80;cursor:pointer;transition:.1s}
  #yslider::-webkit-slider-thumb:hover{transform:scale(1.15)}
  #yslider::-moz-range-thumb{width:14px;height:14px;border-radius:50%;background:var(--home);border:3px solid #101113;cursor:pointer}
  .yticks{display:flex;justify-content:space-between;margin-top:5px}
  .yticks button{font:inherit;font-size:10px;font-weight:700;font-family:var(--mono);color:var(--t3);background:none;border:0;padding:2px 4px;cursor:pointer;transition:.12s;border-radius:4px}
  .yticks button.on{color:var(--home)}
  .yticks button:hover{color:var(--t1)}
  .yhint{position:absolute;left:18px;bottom:96px;font-size:10px;color:var(--t3);pointer-events:none;display:flex;align-items:center;gap:5px;opacity:.85}
  @media(max-width:720px){.app{grid-template-columns:1fr;height:auto}.panel{max-height:none;border-right:0;border-bottom:1px solid var(--line)}.maph{height:440px}}
</style>
<div class="app">
  <h2 class="sr-only">Dark interactive world map of overseas revenue for 10 Thai-listed hotel companies over 5 years (2021-2025), with a year slider and a left panel bar chart comparing each company's foreign revenue share.</h2>
  <aside class="panel">
    <p class="eyebrow" id="eyebrow">TOUR Sector · FY2025</p>
    <h1 class="h1">รายได้โรงแรมไทยจากต่างประเทศ</h1>
    <p class="lede">สัดส่วนรายได้ต่างประเทศของแต่ละบริษัทจดทะเบียนไทย เลื่อน Slider เปลี่ยนปี (2564–2568) — แถบเทียบสัดส่วน แผนที่ลากเส้นทางรายได้</p>
    <div class="toggle" id="viewSeg"><button data-v="thb">มูลค่า</button><button data-v="pct" class="on">สัดส่วน</button></div>
    <p class="lbl" id="barlbl">สัดส่วนรายได้ต่างประเทศ</p>
    <div id="bars"></div>
    <p class="note" id="barnote"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/></svg>เส้นประ = เกณฑ์ 20% (DIV = 1 ถ้าเกิน)</p>
    <div class="sect"><p class="lbl" id="dlbl">ภาพรวม</p><div id="detail"></div></div>
  </aside>
  <div class="maph">
    <canvas id="map"></canvas>
    <div class="legend" id="legend"></div>
    <div class="geoseg" id="geoSeg"><span class="gl">ความละเอียด</span><button data-g="country" class="on">ประเทศ</button><button data-g="cont">ทวีป</button></div>
    <div class="esttag" id="esttag"></div>
    <div class="yhint"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 12h8M8 12l3-3M8 12l3 3"/></svg>เลื่อนดูการเปลี่ยนแปลงราย 5 ปี</div>
    <div class="yearwrap"><div class="yearbar">
      <div class="yearhd"><div><span class="yv" id="yv">2568</span> <span class="yce" id="yce">/ 2025</span></div><span class="ytag" id="ytag">ปีล่าสุด</span></div>
      <input type="range" id="yslider" min="0" max="4" step="1" value="4" aria-label="เลือกปี">
      <div class="yticks" id="yticks"></div>
    </div></div>
  </div>
</div>
<script>
const CFG=__CFG__;
__LAND__
(function(){
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const YEARS=CFG.YEARS, YCE=CFG.YEARS_CE, DATA=CFG.DATA;
  const IDS=Object.keys(DATA);
  const COL={MINT:"#ff8a4c",SHR:"#ff5d8f",DUSIT:"#b78bff",CENTEL:"#38d9c4",ERW:"#a3e635"};
  const CIDX={MINT:0,SHR:1,DUSIT:2,CENTEL:3,ERW:4};
  const FLOWS=CFG.FLOWS;
  const TH=[15,100];
  // --- ความละเอียด: ประเทศ (ดิบ) หรือ ทวีป (รวม) ---
  const CONT_META={Europe:{lat:50,lon:10,nm:"ยุโรป"},Asia:{lat:34,lon:113,nm:"เอเชีย"},
    Oceania:{lat:-27,lon:141,nm:"โอเชียเนีย"},Americas:{lat:-12,lon:-60,nm:"อเมริกา"},
    Africa:{lat:-6,lon:22,nm:"แอฟริกา"},"Middle East":{lat:24,lon:47,nm:"ตะวันออกกลาง"},Other:{lat:8,lon:78,nm:"อื่น ๆ"}};
  function contFlows(){                      // รวมทุกประเทศใน cont เดียวกันของบริษัทเดียวกัน -> 1 จุด/ทวีป
    const m={};
    FLOWS.forEach(f=>{const k=f.co+"|"+f.cont,c=CONT_META[f.cont]||{lat:f.lat,lon:f.lon,nm:f.cont};
      if(!m[k])m[k]={co:f.co,country:c.nm,cont:f.cont,lat:c.lat,lon:c.lon,ok:1,thb:[0,0,0,0,0],pct:[0,0,0,0,0]};
      for(let j=0;j<5;j++)m[k].thb[j]+=f.thb[j];
      if(!f.ok)m[k].ok=0;});
    Object.values(m).forEach(f=>{for(let j=0;j<5;j++){const it=DATA[f.co].intl[j];f.pct[j]=it?Math.round(f.thb[j]/it*100):0;}});
    return Object.values(m);
  }
  const CONT_FLOWS=contFlows();
  let geo="country",curFlows=FLOWS,CN={},COUNTRIES=[];
  function setGeoData(){curFlows=geo==="cont"?CONT_FLOWS:FLOWS;CN={};
    curFlows.forEach(f=>{(CN[f.country]=CN[f.country]||{country:f.country,lat:f.lat,lon:f.lon,cont:f.cont,flows:[]}).flows.push(f);});
    COUNTRIES=Object.values(CN);}
  setGeoData();
  const fmt=v=>"฿"+(v>=1000?(v/1000).toFixed(v>=100000?0:1)+"B":Math.round(v)+"M");
  const PIN='<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-6.5-5.7-6.5-10.5a6.5 6.5 0 0113 0C18.5 15.3 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/></svg>';

  let view="pct",sel="all",hot=null,yi=4;   // yi = ดัชนีปี (4 = 2568 ล่าสุด)

  // ---- helpers อิงปีปัจจุบัน ----
  const fpOf=id=>DATA[id].fp[yi];            // % ต่างประเทศ ปีนี้
  const totOf=id=>DATA[id].tot[yi];          // รายได้รวม (ล้านบาท) ปีนี้
  const intlOf=id=>DATA[id].intl[yi];        // รายได้ต่างประเทศ ปีนี้
  const domOf=id=>totOf(id)-intlOf(id);      // รายได้ในประเทศ ปีนี้
  const isIntl=id=>fpOf(id)>=20;             // จัดกลุ่ม DIV ตามปี (>=20%)
  const fThb=f=>f.thb[yi];                   // มูลค่า arc ปีนี้ (year-aware)
  const fPct=f=>f.pct[yi];                   // % ของรายได้ตปท.บริษัทนั้น ปีนี้

  // ---------- LEFT: bar chart ----------
  const barsEl=document.getElementById("bars");
  function renderBars(){
    const pctV=view==="pct",mxT=Math.sqrt(Math.max(...IDS.map(totOf)));
    document.getElementById("barlbl").textContent=pctV?"สัดส่วนรายได้ต่างประเทศ":"รายได้รวม (ขนาด)";
    document.getElementById("barnote").style.display=pctV?"":"none";
    const rows=[...IDS].sort((a,b)=>pctV?fpOf(b)-fpOf(a):totOf(b)-totOf(a));
    barsEl.innerHTML=rows.map(id=>{
      const col=COL[id]||"#51607e";const on=sel===id;const fp=fpOf(id);
      const w=pctV?fp:Math.sqrt(totOf(id))/mxT*100;
      return `<div class="barrow${on?' on':''}" data-co="${id}">
        <span class="tk"><i class="dot" style="background:${col}"></i>${id}</span>
        <span class="track"><span class="fill" style="width:${w}%;background:${col}"></span>${pctV?'<i class="th20"></i>':''}</span>
        <span class="bval">${pctV?fp+"%":fmt(totOf(id))}</span></div>`;
    }).join("");
    barsEl.querySelectorAll(".barrow").forEach(el=>{const id=el.dataset.co;
      el.onclick=()=>{sel=sel===id?"all":id;hot=null;sync();};
      el.onmouseenter=()=>{hot=id;renderDetail();markHot();};
      el.onmouseleave=()=>{hot=null;renderDetail();markHot();};});
  }
  function markHot(){barsEl.querySelectorAll(".barrow").forEach(el=>el.classList.toggle("hot",el.dataset.co===hot));}

  // ---------- LEFT: detail ----------
  const detEl=document.getElementById("detail"),dlbl=document.getElementById("dlbl");
  function vis(f){return (sel==="all"||f.co===sel)&&f.thb[yi]>0;}  // ต้องมีรายได้ในปีนั้น (ตลาดที่ยังไม่เข้า = ไม่โผล่)
  function coDetail(id){
    const fl=curFlows.filter(f=>f.co===id&&f.thb[yi]>0).sort((a,b)=>fThb(b)-fThb(a)),col=COL[id]||"#51607e",fp=fpOf(id);
    const mx=Math.max(1,...fl.map(f=>view==="thb"?fThb(f):fPct(f)));
    dlbl.textContent="บริษัท";
    const est=fl.length&&!fl[0].ok?'<span style="font-size:9px;color:var(--t3);font-weight:600"> · ประมาณการ</span>':'';
    detEl.innerHTML=`<div class="dhead"><i class="dot" style="width:11px;height:11px;background:${col}"></i><span class="nm">${id}</span>
      <span class="chip" style="background:${isIntl(id)?'#ff8a4c':'#38d9c4'}">${fp}% ต่างประเทศ</span></div>`+
      (fl.length?`<p style="font-size:9.5px;color:var(--t3);margin:-4px 0 6px">ปลายทางรายได้ต่างประเทศ${est}</p>`+fl.map(f=>`<div class="drow"><div class="rl">${PIN}<span>${f.country}</span></div>
        <div class="rv">${view==="thb"?fmt(fThb(f)):"~"+fPct(f)+"%"}</div>
        <div class="mt"><i style="width:${(view==="thb"?fThb(f):fPct(f))/mx*100}%;background:${col}"></i></div></div>`).join("")
        :`<p style="font-size:11.5px;color:var(--t2)">ในประเทศล้วน — รายได้เกือบทั้งหมดรับรู้ในไทย</p>`)+
      `<div class="drow" style="border-top:1px solid var(--line);margin-top:6px;padding-top:8px"><div class="rl" style="color:var(--home)">${PIN.replace('currentColor','#4ade80')}<span>ไทย (ในประเทศ)</span></div><div class="rv">${view==="thb"?fmt(domOf(id)):"~"+(100-fp).toFixed(0)+"%"}</div></div>`;
  }
  function countryDetail(name){
    const c=CN[name],fl=c.flows.filter(vis).sort((a,b)=>fThb(b)-fThb(a));
    const mx=Math.max(1,...fl.map(f=>view==="thb"?fThb(f):fPct(f)));
    dlbl.textContent="ปลายทาง";
    detEl.innerHTML=`<div class="dhead">${PIN.replace('currentColor','#fbbf24')}<span class="nm">${name}</span></div>`+
      fl.map(f=>`<div class="drow"><div class="rl"><i class="dot" style="background:${COL[f.co]}"></i><span>${f.co}</span></div>
        <div class="rv">${view==="thb"?fmt(fThb(f)):"~"+fPct(f)+"%"}</div>
        <div class="mt"><i style="width:${(view==="thb"?fThb(f):fPct(f))/mx*100}%;background:${COL[f.co]}"></i></div></div>`).join("")+
      `<p style="font-size:10.5px;color:var(--t3);margin-top:7px">${fl.length} ${fl.length>1?'บริษัท':'บริษัท'}ดำเนินการที่นี่</p>`;
  }
  function overview(){
    dlbl.textContent="ภาพรวม";
    const tot=IDS.reduce((s,id)=>s+intlOf(id),0),dom=IDS.reduce((s,id)=>s+domOf(id),0);
    const nIntl=IDS.filter(isIntl).length;
    const top=[...COUNTRIES].map(c=>({n:c.country,v:c.flows.reduce((s,f)=>s+fThb(f),0)})).sort((a,b)=>b.v-a.v)[0];
    detEl.innerHTML=`<div class="tiles">
      <div class="tile"><div class="k">ต่างประเทศ</div><div class="v" style="color:#ff8a4c">${fmt(tot)}</div></div>
      <div class="tile"><div class="k">ในประเทศ</div><div class="v" style="color:#4ade80">${fmt(dom)}</div></div>
      <div class="tile"><div class="k">ตลาดใหญ่สุด</div><div class="v" style="font-size:13px">${top.n}</div></div>
      <div class="tile"><div class="k">บริษัท intl</div><div class="v">${nIntl}<span style="font-size:11px;color:var(--t3)"> / 10</span></div></div></div>
      <p style="font-size:11px;color:var(--t2);line-height:1.5;margin-top:8px">ปี ${YEARS[yi]}: บริษัทที่เข้าเกณฑ์ต่างประเทศ (≥20%) มี <b style="color:#ff8a4c">${nIntl}</b> บริษัท — MINT รายได้ยุโรปปีเดียว (${fmt(fThb(FLOWS[0]))}) ยังมากกว่ารายได้ในประเทศทั้ง 10 โรงแรมรวมกัน</p>`;
  }
  function renderDetail(){if(hot&&DATA[hot])coDetail(hot);else if(hot)countryDetail(hot);else if(sel!=="all")coDetail(sel);else overview();}

  function renderLegend(){
    document.getElementById("legend").innerHTML='<div class="lg">บริษัท · % ต่างประเทศ '+YEARS[yi]+'</div>'+
      Object.keys(COL).map(k=>`<span><i style="background:${COL[k]}"></i>${k} · ${fpOf(k)}%</span>`).join('')+
      '<span style="margin-top:3px"><i style="background:#4ade80;height:9px;width:9px;border-radius:50%"></i>ไทย (ฐาน)</span>';
  }
  document.getElementById("esttag").innerHTML='<b>สัดส่วนใน/นอกประเทศ</b>: จริงจาก Base Sheet ทุกปี · <b>รายประเทศ</b>: MINT · ERW · SHR · CENTEL จริงจากงบ (SHR แยกมอริเชียส/ฟิจิ ประมาณ) — DUSIT เปิดแค่ไทย/ตปท. (ประเทศ=ประมาณ)';

  // ---------- MAP ----------
  const cv=document.getElementById("map"),ctx=cv.getContext("2d");
  let W=0,H=0,dpr=Math.min(devicePixelRatio||1,2),lc=null,t0=performance.now();
  const LAT_T=82,LAT_B=-56;
  const px=(lat,lon)=>[(lon+180)/360*W,(LAT_T-lat)/(LAT_T-LAT_B)*H];
  function bakeLand(){lc=document.createElement("canvas");lc.width=Math.round(W*dpr);lc.height=Math.round(H*dpr);const g=lc.getContext("2d");g.setTransform(dpr,0,0,dpr,0,0);
    g.fillStyle="#2f3135";g.strokeStyle="#45484e";g.lineWidth=.7;g.lineJoin="round";
    for(const ring of LAND){g.beginPath();let p0=null;
      for(let i=0;i<ring.length;i+=2){const[x,y]=px(ring[i+1],ring[i]);if(p0!==null&&Math.abs(x-p0)>W*.5)g.moveTo(x,y);else if(i===0)g.moveTo(x,y);else g.lineTo(x,y);p0=x;}
      g.closePath();g.fill();g.stroke();}}
  function resize(){const r=cv.parentNode.getBoundingClientRect();W=Math.round(r.width);H=Math.round(r.height);cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);bakeLand();}

  function curMax(){let m=0;COUNTRIES.forEach(c=>{if(c.flows.some(vis))m=Math.max(m,c.flows.filter(vis).reduce((s,f)=>s+fThb(f),0));});return m||1;}
  const rad=(v,mx,mn,mr)=>mn+Math.sqrt(Math.max(0,v))/Math.sqrt(mx)*(mr-mn);
  function cThb(c){return c.flows.filter(vis).reduce((s,f)=>s+fThb(f),0);}
  function dotR(c){if(view==="thb")return rad(cThb(c),curMax(),4,22);if(sel!=="all"){const f=c.flows.find(x=>x.co===sel);return f?5+Math.sqrt(fPct(f))*2.3:4;}return 5+Math.sqrt(new Set(c.flows.map(f=>f.co)).size)*4.5;}
  function litArc(f){if(!hot)return true;return DATA[hot]?f.co===hot:f.country===hot;}
  function litC(c){if(!hot)return true;if(DATA[hot])return c.flows.some(f=>f.co===hot&&vis(f));return c.country===hot;}

  function txt(s,x,y,fill,font,size){ctx.font=font;ctx.textAlign="center";ctx.lineJoin="round";ctx.lineWidth=size;ctx.strokeStyle="rgba(6,10,18,.92)";ctx.strokeText(s,x,y);ctx.fillStyle=fill;ctx.fillText(s,x,y);}

  function draw(now){
    const t=(now-t0)/1000;ctx.clearRect(0,0,W,H);if(lc)ctx.drawImage(lc,0,0,W,H);
    const HUB=px(TH[0],TH[1]);
    const totIntl=IDS.reduce((s,id)=>s+intlOf(id),0);
    const contMode=geo==="cont",wsc=contMode?0.55:1;   // โหมดทวีป: เส้นบางลง กางแยกมากขึ้น กัน้ทับกัน
    curFlows.filter(vis).forEach((f,i)=>{const P=px(f.lat,f.lon);const lit=litArc(f);const col=COL[f.co];const v=fThb(f);
      const w=(view==="thb"?Math.min(15,Math.max(.9,Math.sqrt(v)/15)):Math.max(.9,Math.min(7,fPct(f)/10)))*wsc;
      const mx=(HUB[0]+P[0])/2,my=(HUB[1]+P[1])/2,dx=P[0]-HUB[0],dy=P[1]-HUB[1],len=Math.hypot(dx,dy)||1;
      const off=0.12*len+8+(CIDX[f.co]-2)*(contMode?26:17);const cx=mx-dy/len*off,cy=my+dx/len*off;
      ctx.save();ctx.globalAlpha=lit?(hot?0.95:(contMode?0.48:0.62)):0.05;ctx.lineWidth=w+(hot&&lit?0.7:0);ctx.strokeStyle=col;ctx.shadowColor=col;ctx.shadowBlur=lit?(contMode?2:9):0;ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(HUB[0],HUB[1]);ctx.quadraticCurveTo(cx,cy,P[0],P[1]);ctx.stroke();ctx.restore();
      if(!reduce&&lit&&!(contMode&&!hot)){const sp=0.09+Math.min(0.15,v/130000);const np=hot&&lit?(contMode?2:4):2;
        for(let k=0;k<np;k++){let tt=((t*sp)+k/np+i*0.11)%1;const s=1-tt,u=1-s;const x=u*u*HUB[0]+2*u*s*cx+s*s*P[0],y=u*u*HUB[1]+2*u*s*cy+s*s*P[1];
          ctx.save();ctx.globalAlpha=Math.sin(s*Math.PI)*.9;ctx.fillStyle=col;ctx.shadowColor=col;ctx.shadowBlur=7;ctx.beginPath();ctx.arc(x,y,1.7,0,7);ctx.fill();ctx.restore();}}});
    // โหมดทวีป: แตกเส้นย่อยจากศูนย์ทวีป -> ประเทศจริง (ลำดับชั้น ไทย->ทวีป->ประเทศ)
    if(geo==="cont"){
      FLOWS.filter(vis).forEach(f=>{const cm=CONT_META[f.cont];if(!cm)return;
        const A=px(cm.lat,cm.lon),B=px(f.lat,f.lon);
        if(Math.hypot(A[0]-B[0],A[1]-B[1])<6)return;              // ประเทศทับศูนย์ทวีป -> ไม่ต้องแตกเส้น
        const lit=!hot||hot===f.co||hot===cm.nm||hot===f.country,col=COL[f.co];
        // เส้นโค้งประ กางตามบริษัท (แต่ละบริษัทโค้งคนละทาง -> แยกออกว่ามาจากใคร)
        const mx=(A[0]+B[0])/2,my=(A[1]+B[1])/2,dx=B[0]-A[0],dy=B[1]-A[1],len=Math.hypot(dx,dy)||1;
        const off=(CIDX[f.co]-2)*13+7,cx=mx-dy/len*off,cy=my+dx/len*off;
        ctx.save();ctx.globalAlpha=lit?0.55:0.05;ctx.strokeStyle=col;ctx.lineWidth=lit&&hot?1.6:1.1;ctx.setLineDash([4,3]);ctx.lineCap="round";
        ctx.beginPath();ctx.moveTo(A[0],A[1]);ctx.quadraticCurveTo(cx,cy,B[0],B[1]);ctx.stroke();ctx.restore();
        ctx.save();ctx.globalAlpha=lit?0.95:0.12;ctx.fillStyle=lit?col:"#c3d0e8";ctx.shadowColor=col;ctx.shadowBlur=lit?6:0;ctx.beginPath();ctx.arc(B[0],B[1],2.8,0,7);ctx.fill();ctx.restore();
        if(lit)txt(f.country,B[0],B[1]+12,"#9aa4b8","600 9px "+getFont(),2.4);});
    }
    COUNTRIES.forEach(c=>{if(!c.flows.some(vis))return;const P=px(c.lat,c.lon);const r=dotR(c);const lit=litC(c);const on=hot===c.country;
      ctx.save();ctx.globalAlpha=lit?1:.28;const cc=on?"#fbbf24":"#dbe6fb";ctx.shadowColor=cc;ctx.shadowBlur=on?12:4;ctx.fillStyle=cc;ctx.beginPath();ctx.arc(P[0],P[1],r,0,7);ctx.fill();ctx.restore();
      if(lit)txt(c.country,P[0],P[1]-r-4,on?"#ffe58a":"#c3d0e8","600 11px "+getFont(),3);});
    const pulse=reduce?0:Math.sin(t*1.6)*.5+.5,hr=view==="thb"?rad(IDS.reduce((s,id)=>s+domOf(id),0),Math.max(1,totIntl),8,24):17;
    ctx.save();ctx.strokeStyle="rgba(74,222,128,"+(0.14+pulse*.2)+")";ctx.lineWidth=1.6;ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr+5+pulse*6,0,7);ctx.stroke();
    ctx.shadowColor="#4ade80";ctx.shadowBlur=15;ctx.fillStyle="#4ade80";ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr,0,7);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle="rgba(8,12,21,.6)";ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr*.34,0,7);ctx.fill();ctx.restore();
    txt("ไทย",HUB[0],HUB[1]-hr-6,"#d6ffe8","750 13px "+getFont(),3.4);
    raf=requestAnimationFrame(draw);
  }
  function getFont(){return '-apple-system,"Segoe UI",Roboto,Arial,sans-serif';}

  cv.addEventListener("pointermove",e=>{const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let f=null;
    COUNTRIES.forEach(c=>{if(!c.flows.some(vis))return;const P=px(c.lat,c.lon);if(Math.hypot(P[0]-mx,P[1]-my)<dotR(c)+6)f=c.country;});
    if(f!==hot){hot=f;renderDetail();markHot();}cv.style.cursor=f?"pointer":"default";});
  cv.addEventListener("pointerleave",()=>{hot=null;renderDetail();markHot();});

  function sync(){renderBars();renderDetail();markHot();renderLegend();}

  // ---------- YEAR slider ----------
  const yslider=document.getElementById("yslider");
  function updYearHead(){
    document.getElementById("yv").textContent=YEARS[yi];
    document.getElementById("yce").textContent="/ "+YCE[yi];
    document.getElementById("ytag").textContent=yi===4?"ปีล่าสุด":(yi===0?"ปีเริ่มต้น":"");
    document.getElementById("eyebrow").textContent="TOUR Sector · FY"+YCE[yi];
    document.querySelectorAll("#yticks button").forEach((b,i)=>b.classList.toggle("on",i===yi));
  }
  function setYear(v){yi=Math.max(0,Math.min(4,v|0));yslider.value=yi;updYearHead();sync();}
  yslider.addEventListener("input",e=>setYear(+e.target.value));
  document.getElementById("yticks").innerHTML=YEARS.map((y,i)=>`<button data-i="${i}">${y}</button>`).join("");
  document.querySelectorAll("#yticks button").forEach(b=>b.onclick=()=>setYear(+b.dataset.i));

  document.getElementById("viewSeg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;view=b.dataset.v;document.querySelectorAll("#viewSeg button").forEach(x=>x.classList.toggle("on",x===b));renderBars();renderDetail();});
  // toggle ความละเอียด ประเทศ <-> ทวีป
  document.getElementById("geoSeg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;geo=b.dataset.g;document.querySelectorAll("#geoSeg button").forEach(x=>x.classList.toggle("on",x===b));hot=null;setGeoData();renderDetail();markHot();});
  let raf;new ResizeObserver(resize).observe(cv.parentNode);resize();updYearHead();renderLegend();renderBars();overview();raf=requestAnimationFrame(draw);
})();
</script>'''

HTML = HTML.replace('__CFG__', json.dumps(CFG, ensure_ascii=False)).replace('__LAND__', LAND)
out = os.path.join(HERE, 'tour_revenue_worldmap.html')
open(out, 'w', encoding='utf-8').write(HTML)
print('written', out, len(HTML), 'chars')
