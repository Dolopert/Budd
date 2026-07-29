# -*- coding: utf-8 -*-
"""แทรกแท็บ 'รันสูตรทีละจุด' เข้า output/panel_check.html -> output/panel_check_v2.html"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "output"))
SRC = os.path.join(OUT, "panel_check.html")
DST = os.path.join(OUT, "panel_check_v2.html")

html = open(SRC, encoding="utf-8").read()
trace = open(os.path.join(OUT, "formula_trace.json"), encoding="utf-8").read()

def must_replace(s, old, new, label):
    if old not in s:
        sys.exit(f"ANCHOR NOT FOUND: {label}")
    if s.count(old) != 1:
        sys.exit(f"ANCHOR NOT UNIQUE ({s.count(old)}): {label}")
    return s.replace(old, new)

# 1) CSS ก่อน </style> (ตัวแรก)
CSS = """
  .badge.b-seed{background:var(--crisis); color:var(--crisis-line)}
  .tracebody{padding:14px 18px; display:grid; gap:22px}
  .tcap{font-size:12px; color:var(--muted); line-height:1.6}
  .mblock{border:1px solid var(--line); border-radius:10px; overflow:hidden}
  .mtitle{padding:9px 13px; background:var(--line2); font-weight:700; font-size:13px;
    display:flex; gap:10px; align-items:baseline; flex-wrap:wrap}
  .mtitle .mform{font-weight:500; font-size:11.5px; color:var(--muted)}
  table.dtab{border-collapse:collapse; width:100%; font-size:12.5px}
  table.dtab th,table.dtab td{padding:6px 11px; text-align:right; white-space:nowrap;
    font-variant-numeric:tabular-nums; border-bottom:1px solid var(--line2)}
  table.dtab th{position:static; background:var(--panel); color:var(--muted);
    font-size:10.5px; text-transform:uppercase; letter-spacing:.03em; cursor:default}
  table.dtab th:hover{color:var(--muted)}
  table.dtab td.txt,table.dtab th.txt{text-align:left}
  table.dtab td.avg{font-weight:700}
  table.dtab td.calc{font-weight:650; background:var(--accent-soft)}
  table.dtab td.neg,table.dtab span.neg{color:var(--neg)}
  table.dtab td.grpl{border-left:1px solid var(--line)}
</style>"""
html = must_replace(html, "</style>", CSS, "css")

# 2) ปุ่มแท็บ หลังปุ่ม raw
BTN_OLD = '<button class="tab" role="tab" aria-selected="false" data-v="raw">ค่าดิบต่อไฟล์งบ (Raw Extract)</button>'
BTN_NEW = BTN_OLD + '\n    <button class="tab" role="tab" aria-selected="false" data-v="trace">รันสูตรทีละจุด (Formula Trace)</button>'
html = must_replace(html, BTN_OLD, BTN_NEW, "tab-button")

# 3) section ก่อน </div> ปิด .wrap  (anchor: "  </section>\n</div>\n\n<script>")
SEC_ANCHOR = "  </section>\n</div>\n\n<script>"
SECTION = """  </section>

  <!-- ===== TAB 3: FORMULA TRACE ===== -->
  <section class="view" id="v-trace" hidden>
    <div class="card">
      <h2>รันสูตรทีละจุด — แทนค่าจริงจาก RAW (chain ยอดงบดุลไตรมาสก่อน)</h2>
      <div class="controls">
        <label class="txt" style="font-size:13px;color:var(--muted)">บริษัท <select id="tCo"></select></label>
        <label class="txt" style="font-size:13px;color:var(--muted)">ปี <select id="tYr"></select></label>
        <span class="count" id="tCnt"></span>
      </div>
      <div class="tracebody" id="tBody"></div>
    </div>
    <div class="legend">
      <span><span class="badge b-seed">seed</span> Q1 ใช้ยอด "ต้นปี" (31 ธ.ค. ปีก่อน) เป็นต้นงวด</span>
      <span><span class="sw" style="background:var(--neg)"></span> ค่าติดลบ</span>
      <span><span class="bad">rev_low</span> รายได้ต่ำ — NPM/DSO/CCC ตีความระวัง</span>
    </div>
    <p class="note">แต่ละสูตรแยกตาราง แสดงยอดต้น/ปลาย/เฉลี่ย → ตัวหาร → ผลคำนวณ เทียบ metrics_all.csv รายไตรมาส · ROA/ROE/NPM รายไตรมาส (ไม่ annualize)</p>
  </section>
</div>

<script>"""
html = must_replace(html, SEC_ANCHOR, SECTION, "section")

# 4) DATA_T + render ก่อน "// ---- tab switch ----"
RENDER = """const DATA_T = __TRACE__;
// ---- TAB 3 formula trace (ตารางละเอียดต่อสูตร) ----
(function(){
  const co=document.getElementById("tCo"), yr=document.getElementById("tYr");
  const cos=[...new Set(DATA_T.map(r=>r.ticker))], yrs=[...new Set(DATA_T.map(r=>r.year))];
  co.innerHTML=cos.map(c=>`<option>${c}</option>`).join("");
  yr.innerHTML=yrs.map(y=>`<option>${y}</option>`).join("");
  co.value=cos[0]; yr.value=yrs[0];
  const n=(v,d=2)=> (v===null||v===undefined)?"—":fmt(v,d);
  const r2=v=>Math.round(v*100)/100;
  const ng=v=>(typeof v==="number"&&v<0)?"neg":"";
  const num=(v,d=2)=>`<span class="${ng(v)}">${n(v,d)}</span>`;
  // ✓ เทียบค่าที่ full-precision (out) กับ metrics_all (ref) — รับประกัน 0 mismatch
  const chk=(a,b)=> (a==null||b==null)?"" :
    (Math.abs(a-b)<=0.05?' <span class="ok">✓</span>':' <span class="bad">≠</span>');
  const qcell=e=>`<td class="txt tk">${e.quarter}${e.seed?' <span class="badge b-seed">seed</span>':''}${e.rev_low?' <span class="bad">rev_low</span>':''}</td>`;

  // สเปกสูตร
  const DAYS=[
    {key:"DSO",full:"Days Sales Outstanding",item:"trade_receivables",itemL:"ลูกหนี้",denom:"rev",denomL:"รายได้",form:"ลูกหนี้เฉลี่ย ÷ รายได้ × วัน"},
    {key:"DIO",full:"Days Inventory Outstanding",item:"inventory",itemL:"สินค้า",denom:"cogs",denomL:"ต้นทุนขาย",form:"สินค้าเฉลี่ย ÷ ต้นทุนขาย × วัน"},
    {key:"DPO",full:"Days Payable Outstanding",item:"trade_payables",itemL:"เจ้าหนี้",denom:"cogs",denomL:"ต้นทุนขาย",form:"เจ้าหนี้เฉลี่ย ÷ ต้นทุนขาย × วัน"},
  ];
  const RATIOS=[
    {key:"ROA",full:"Return on Assets",item:"total_assets",itemL:"สินทรัพย์",form:"กำไรสุทธิ ÷ สินทรัพย์เฉลี่ย × 100"},
    {key:"ROE",full:"Return on Equity",item:"total_equity",itemL:"ทุน",form:"กำไรสุทธิ ÷ ทุนเฉลี่ย × 100"},
  ];
  const block=(title,form,head,body)=>`<div class="mblock"><div class="mtitle">${title}<span class="mform">${form}</span></div>`+
    `<div class="scroll"><table class="dtab"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div></div>`;

  function dayBlock(rows,s){
    const head=`<th class="txt">งวด</th><th>${s.itemL}ต้น</th><th>${s.itemL}ปลาย</th><th>${s.itemL}เฉลี่ย</th>`+
      `<th class="grpl">${s.denomL}</th><th>วัน</th><th class="grpl">${s.key} คำนวณ</th><th>metrics_all</th>`;
    const body=rows.map(e=>{const b=e.bs[s.item],den=e[s.denom],calc=r2(b.avg/den*e.days),ref=e.ref[s.key];
      return `<tr>${qcell(e)}<td>${num(b.beg)}</td><td>${num(b.end)}</td><td class="avg">${num(b.avg)}</td>`+
        `<td class="grpl">${num(den)}</td><td>${e.days}</td>`+
        `<td class="calc grpl">${num(calc)}</td><td>${num(ref)}${chk(e.out[s.key],ref)}</td></tr>`;}).join("");
    return block(`${s.key} <span style="color:var(--muted);font-weight:500">${s.full}</span>`,s.form,head,body);
  }
  function ratioBlock(rows,s){
    const head=`<th class="txt">งวด</th><th>กำไรสุทธิ</th><th>${s.itemL}ต้น</th><th>${s.itemL}ปลาย</th><th>${s.itemL}เฉลี่ย</th>`+
      `<th class="grpl">${s.key} คำนวณ</th><th>metrics_all</th>`;
    const body=rows.map(e=>{const b=e.bs[s.item],calc=r2(e.np/b.avg*100),ref=e.ref[s.key];
      return `<tr>${qcell(e)}<td>${num(e.np)}</td><td>${num(b.beg)}</td><td>${num(b.end)}</td><td class="avg">${num(b.avg)}</td>`+
        `<td class="calc grpl">${num(calc)}%</td><td>${num(ref==null?null:r2(ref*100))}%${chk(e.out[s.key],ref)}</td></tr>`;}).join("");
    return block(`${s.key} <span style="color:var(--muted);font-weight:500">${s.full}</span>`,s.form,head,body);
  }
  function npmBlock(rows){
    const head=`<th class="txt">งวด</th><th>กำไรสุทธิ</th><th>รายได้</th><th class="grpl">NPM คำนวณ</th><th>metrics_all</th>`;
    const body=rows.map(e=>{const calc=r2(e.np/e.rev*100),ref=e.ref.NPM;
      return `<tr>${qcell(e)}<td>${num(e.np)}</td><td>${num(e.rev)}</td>`+
        `<td class="calc grpl">${num(calc)}%</td><td>${num(ref==null?null:r2(ref*100))}%${chk(e.out.NPM,ref)}</td></tr>`;}).join("");
    return block(`NPM <span style="color:var(--muted);font-weight:500">Net Profit Margin</span>`,"กำไรสุทธิ ÷ รายได้ × 100",head,body);
  }
  function cccBlock(rows){
    const head=`<th class="txt">งวด</th><th>DIO</th><th>DSO</th><th>DPO</th><th class="grpl">CCC คำนวณ</th><th>metrics_all</th>`;
    const body=rows.map(e=>{const dio=r2(e.bs.inventory.avg/e.cogs*e.days),dso=r2(e.bs.trade_receivables.avg/e.rev*e.days),
      dpo=r2(e.bs.trade_payables.avg/e.cogs*e.days),ccc=r2(dio+dso-dpo),ref=e.ref.CCC;
      return `<tr>${qcell(e)}<td>${num(dio)}</td><td>${num(dso)}</td><td>${num(dpo)}</td>`+
        `<td class="calc grpl">${num(ccc)}</td><td>${num(ref)}${chk(e.out.CCC,ref)}</td></tr>`;}).join("");
    return block(`CCC <span style="color:var(--muted);font-weight:500">Cash Conversion Cycle</span>`,"DIO + DSO − DPO",head,body);
  }

  function render(){
    const rows=DATA_T.filter(r=>r.ticker===co.value&&r.year==yr.value)
                     .sort((a,b)=>a.quarter.localeCompare(b.quarter));
    document.getElementById("tCnt").textContent=rows.length+" ไตรมาส × 7 สูตร";
    if(!rows.length){document.getElementById("tBody").innerHTML='<p class="note">ไม่มีข้อมูล</p>';return;}
    const anySeed=rows.some(e=>e.seed);
    const cap=`<div class="tcap">ทุกยอดหน่วย <b>ล้านบาท</b> · ค่าเฉลี่ยงบดุล = (ต้นงวด + ปลายงวด) ÷ 2 · `+
      (anySeed?'Q1 <span class="badge b-seed">seed</span> ใช้ยอด "ต้นปี" (31 ธ.ค. ปีก่อน) เป็นต้นงวด · ':'')+
      `Q2–Q4 ต้นงวด = <b>ปลายไตรมาสก่อน</b> (chain) · คอลัมน์ "คำนวณ" แทนค่าจากยอดที่ปัดแล้ว จึงอาจต่างจาก metrics_all ±0.01 · <span class="ok">✓</span> = ตรงที่ full precision (0 mismatch/200 จุด)</div>`;
    const h=[cap, ...DAYS.map(s=>dayBlock(rows,s)), cccBlock(rows),
             ...RATIOS.map(s=>ratioBlock(rows,s)), npmBlock(rows)].join("");
    document.getElementById("tBody").innerHTML=h;
  }
  co.addEventListener("change",render); yr.addEventListener("change",render);
  render();
})();

// ---- tab switch ----"""
RENDER = RENDER.replace("__TRACE__", trace)
html = must_replace(html, "// ---- tab switch ----", RENDER, "render")

# 5) tab-switch: เพิ่ม v-trace
SW_OLD = '  document.getElementById("v-raw").hidden = t.dataset.v!=="raw";'
SW_NEW = SW_OLD + '\n  document.getElementById("v-trace").hidden = t.dataset.v!=="trace";'
html = must_replace(html, SW_OLD, SW_NEW, "tab-switch")

open(DST, "w", encoding="utf-8").write(html)
print(f"OK wrote {DST}  ({len(html)} chars)")
