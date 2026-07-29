# -*- coding: utf-8 -*-
LAND = open('countries.js', encoding='utf-8').read()

HTML = r'''<style>
  :root{--bg:#151619;--panel:#191a1d;--card:#202225;--line:#2b2d31;--land:#2f3135;--coast:#45484e;
    --t1:#ecedf0;--t2:#9a9ea7;--t3:#696d76;--home:#4ade80;--hot:#fbbf24;
    --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
    --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;}
  *{box-sizing:border-box}
  .app{background:var(--bg);color:var(--t1);font-family:var(--font);border-radius:14px;overflow:hidden;display:grid;grid-template-columns:296px 1fr;height:624px}
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
  .fill{display:block;height:100%;min-width:2px;border-radius:5px;transition:width .35s cubic-bezier(.4,0,.2,1)}
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
  .legend .lg{font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--t3);font-weight:700;margin-bottom:5px}
  .legend span{display:flex;align-items:center;gap:7px;padding:1px 0}
  .legend i{width:14px;height:3px;border-radius:2px}
  @media(max-width:720px){.app{grid-template-columns:1fr;height:auto}.panel{max-height:none;border-right:0;border-bottom:1px solid var(--line)}.maph{height:380px}}
</style>
<div class="app">
  <h2 class="sr-only">Dark interactive world map of overseas revenue for 10 Thai-listed hotel companies, with a left panel comparing each company's foreign revenue share on a bar chart.</h2>
  <aside class="panel">
    <p class="eyebrow">TOUR Sector · FY2025</p>
    <h1 class="h1">Where Thai Hotels Earn Abroad</h1>
    <p class="lede">Foreign revenue routed back to each Thailand-listed parent. Bars compare overseas share; the map traces each company's routes.</p>
    <div class="toggle" id="viewSeg"><button data-v="thb">Value</button><button data-v="pct" class="on">Share</button></div>
    <p class="lbl" id="barlbl">Overseas revenue share</p>
    <div id="bars"></div>
    <p class="note" id="barnote"><svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><path d="M12 8v4M12 16h.01"/></svg>Dashed line = 20% threshold (DIV = 1 if above)</p>
    <div class="sect"><p class="lbl" id="dlbl">Overview</p><div id="detail"></div></div>
  </aside>
  <div class="maph">
    <canvas id="map"></canvas>
    <div class="legend" id="legend"></div>
  </div>
</div>
<script>
__LAND__
(function(){
  const reduce=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const COL={MINT:"#ff8a4c",SHR:"#ff5d8f",DUSIT:"#b78bff",CENTEL:"#38d9c4",ERW:"#a3e635"};
  const CIDX={MINT:0,SHR:1,DUSIT:2,CENTEL:3,ERW:4};
  const FLOWS=[
    ["MINT","Europe",94509,57,48,9],["MINT","Maldives",13264,8,3,73],["MINT","Middle East",11606,7,25,53],["MINT","Latin America",6632,4,8,-66],["MINT","Australia",4974,3,-25,134],
    ["SHR","UK",4373,42,54,-2],["SHR","Maldives",2290,22,3,73],["SHR","Fiji",1041,10,-17,178],["SHR","Mauritius",833,8,-20,57],
    ["DUSIT","Maldives",892,10,3,73],["DUSIT","Philippines",892,10,13,122],["DUSIT","Middle East",625,7,25,53],["DUSIT","Egypt / US",446,5,26,30],
    ["CENTEL","Maldives",2505,10,3,73],["CENTEL","Japan",501,2,36,138],["CENTEL","Middle East",501,2,25,53],
    ["ERW","Philippines",953,12,13,122],
  ].map(f=>({co:f[0],country:f[1],thb:f[2],pct:f[3],lat:f[4],lon:f[5]}));
  const COMPANIES=[{id:"MINT",g:"intl",tot:165805,dom:20},{id:"SHR",g:"intl",tot:10411,dom:22},{id:"DUSIT",g:"intl",tot:8924,dom:68},{id:"CENTEL",g:"dom",tot:25052,dom:86},{id:"ERW",g:"dom",tot:7938,dom:88},{id:"ASIA",g:"dom",tot:1365,dom:91},{id:"OHTL",g:"dom",tot:2524,dom:100},{id:"SHANG",g:"dom",tot:2154,dom:100},{id:"VRANDA",g:"dom",tot:1578,dom:100},{id:"MANRIN",g:"dom",tot:363,dom:100}];
  const CM={};COMPANIES.forEach(c=>{c.fp=100-c.dom;CM[c.id]=c;});
  const domTHB=id=>CM[id].tot*CM[id].dom/100;
  const TH=[15,100];
  const CN={};FLOWS.forEach(f=>{(CN[f.country]=CN[f.country]||{country:f.country,lat:f.lat,lon:f.lon,flows:[]}).flows.push(f);});
  const COUNTRIES=Object.values(CN);
  const fmt=v=>"฿"+(v>=1000?(v/1000).toFixed(v>=100000?0:1)+"B":Math.round(v)+"M");
  const PIN='<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 21s-6.5-5.7-6.5-10.5a6.5 6.5 0 0113 0C18.5 15.3 12 21 12 21z"/><circle cx="12" cy="10.5" r="2.2"/></svg>';

  let view="pct",sel="all",hot=null;

  // ---------- LEFT: bar chart ----------
  const barsEl=document.getElementById("bars");
  function renderBars(){
    const pctV=view==="pct",mxT=Math.sqrt(165805);
    document.getElementById("barlbl").textContent=pctV?"Overseas revenue share":"Total revenue (size)";
    document.getElementById("barnote").style.display=pctV?"":"none";
    const rows=[...COMPANIES].sort((a,b)=>pctV?b.fp-a.fp:b.tot-a.tot);
    barsEl.innerHTML=rows.map(c=>{
      const col=COL[c.id]||"#51607e";const on=sel===c.id;
      const w=pctV?c.fp:Math.sqrt(c.tot)/mxT*100;
      return `<div class="barrow${on?' on':''}" data-co="${c.id}">
        <span class="tk"><i class="dot" style="background:${col}"></i>${c.id}</span>
        <span class="track"><span class="fill" style="width:${w}%;background:${col}"></span>${pctV?'<i class="th20"></i>':''}</span>
        <span class="bval">${pctV?c.fp+"%":fmt(c.tot)}</span></div>`;
    }).join("");
    barsEl.querySelectorAll(".barrow").forEach(el=>{const id=el.dataset.co;
      el.onclick=()=>{sel=sel===id?"all":id;hot=null;sync();};
      el.onmouseenter=()=>{hot=id;renderDetail();markHot();};
      el.onmouseleave=()=>{hot=null;renderDetail();markHot();};});
  }
  function markHot(){barsEl.querySelectorAll(".barrow").forEach(el=>el.classList.toggle("hot",el.dataset.co===hot));}

  // ---------- LEFT: detail ----------
  const detEl=document.getElementById("detail"),dlbl=document.getElementById("dlbl");
  function vis(f){return sel==="all"||f.co===sel;}
  function coDetail(id){
    const c=CM[id],fl=FLOWS.filter(f=>f.co===id).sort((a,b)=>b.thb-a.thb),col=COL[id]||"#51607e";
    const mx=Math.max(1,...fl.map(f=>view==="thb"?f.thb:f.pct));
    dlbl.textContent="Company";
    detEl.innerHTML=`<div class="dhead"><i class="dot" style="width:11px;height:11px;background:${col}"></i><span class="nm">${id}</span>
      <span class="chip" style="background:${c.g==='intl'?'#ff8a4c':'#38d9c4'}">${c.fp}% overseas</span></div>`+
      (fl.length?fl.map(f=>`<div class="drow"><div class="rl">${PIN}<span>${f.country}</span></div>
        <div class="rv">${view==="thb"?fmt(f.thb):"~"+f.pct+"%"}</div>
        <div class="mt"><i style="width:${(view==="thb"?f.thb:f.pct)/mx*100}%;background:${col}"></i></div></div>`).join("")
        :`<p style="font-size:11.5px;color:var(--t2)">Domestic only — 100% of revenue recognised in Thailand.</p>`)+
      `<div class="drow" style="border-top:1px solid var(--line);margin-top:6px;padding-top:8px"><div class="rl" style="color:var(--home)">${PIN.replace('currentColor','#4ade80')}<span>Thailand (domestic)</span></div><div class="rv">${view==="thb"?fmt(domTHB(id)):"~"+c.dom+"%"}</div></div>`;
  }
  function countryDetail(name){
    const c=CN[name],fl=c.flows.filter(vis).sort((a,b)=>b.thb-a.thb);
    const mx=Math.max(1,...fl.map(f=>view==="thb"?f.thb:f.pct));
    dlbl.textContent="Destination";
    detEl.innerHTML=`<div class="dhead">${PIN.replace('currentColor','#fbbf24')}<span class="nm">${name}</span></div>`+
      fl.map(f=>`<div class="drow"><div class="rl"><i class="dot" style="background:${COL[f.co]}"></i><span>${f.co}</span></div>
        <div class="rv">${view==="thb"?fmt(f.thb):"~"+f.pct+"%"}</div>
        <div class="mt"><i style="width:${(view==="thb"?f.thb:f.pct)/mx*100}%;background:${COL[f.co]}"></i></div></div>`).join("")+
      `<p style="font-size:10.5px;color:var(--t3);margin-top:7px">${fl.length} ${fl.length>1?'companies':'company'} operating here</p>`;
  }
  function overview(){
    dlbl.textContent="Overview";
    const tot=FLOWS.reduce((s,f)=>s+f.thb,0),dom=COMPANIES.reduce((s,c)=>s+domTHB(c.id),0);
    const top=[...COUNTRIES].map(c=>({n:c.country,v:c.flows.reduce((s,f)=>s+f.thb,0)})).sort((a,b)=>b.v-a.v)[0];
    detEl.innerHTML=`<div class="tiles">
      <div class="tile"><div class="k">Overseas</div><div class="v" style="color:#ff8a4c">${fmt(tot)}</div></div>
      <div class="tile"><div class="k">Domestic</div><div class="v" style="color:#4ade80">${fmt(dom)}</div></div>
      <div class="tile"><div class="k">Top market</div><div class="v" style="font-size:13px">${top.n}</div></div>
      <div class="tile"><div class="k">Intl firms</div><div class="v">3<span style="font-size:11px;color:var(--t3)"> / 10</span></div></div></div>
      <p style="font-size:11px;color:var(--t2);line-height:1.5;margin-top:8px">MINT's Europe revenue alone (${fmt(94509)}) exceeds the domestic revenue of all 10 hotels combined.</p>`;
  }
  function renderDetail(){if(hot&&CM[hot])coDetail(hot);else if(hot)countryDetail(hot);else if(sel!=="all")coDetail(sel);else overview();}

  // legend
  document.getElementById("legend").innerHTML='<div class="lg">Companies</div>'+
    Object.keys(COL).map(k=>`<span><i style="background:${COL[k]}"></i>${k} · ${CM[k].fp}%</span>`).join('')+
    '<span style="margin-top:3px"><i style="background:#4ade80;height:9px;width:9px;border-radius:50%"></i>Thailand (base)</span>';

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

  function curMax(){let m=0;COUNTRIES.forEach(c=>{if(c.flows.some(vis))m=Math.max(m,c.flows.filter(vis).reduce((s,f)=>s+f.thb,0));});return m||1;}
  const rad=(v,mx,mn,mr)=>mn+Math.sqrt(Math.max(0,v))/Math.sqrt(mx)*(mr-mn);
  function cThb(c){return c.flows.filter(vis).reduce((s,f)=>s+f.thb,0);}
  function dotR(c){if(view==="thb")return rad(cThb(c),curMax(),4,22);if(sel!=="all"){const f=c.flows.find(x=>x.co===sel);return f?5+Math.sqrt(f.pct)*2.3:4;}return 5+Math.sqrt(new Set(c.flows.map(f=>f.co)).size)*4.5;}
  function litArc(f){if(!hot)return true;return CM[hot]?f.co===hot:f.country===hot;}
  function litC(c){if(!hot)return true;if(CM[hot])return c.flows.some(f=>f.co===hot&&vis(f));return c.country===hot;}

  function txt(s,x,y,fill,font,size){ctx.font=font;ctx.textAlign="center";ctx.lineJoin="round";ctx.lineWidth=size;ctx.strokeStyle="rgba(6,10,18,.92)";ctx.strokeText(s,x,y);ctx.fillStyle=fill;ctx.fillText(s,x,y);}

  function draw(now){
    const t=(now-t0)/1000;ctx.clearRect(0,0,W,H);if(lc)ctx.drawImage(lc,0,0,W,H);
    const HUB=px(TH[0],TH[1]);
    FLOWS.filter(vis).forEach((f,i)=>{const P=px(f.lat,f.lon);const lit=litArc(f);const col=COL[f.co];
      const w=view==="thb"?Math.max(.9,Math.sqrt(f.thb)/10):Math.max(.9,f.pct/8);
      const mx=(HUB[0]+P[0])/2,my=(HUB[1]+P[1])/2,dx=P[0]-HUB[0],dy=P[1]-HUB[1],len=Math.hypot(dx,dy)||1;
      const off=0.12*len+8+(CIDX[f.co]-2)*17;const cx=mx-dy/len*off,cy=my+dx/len*off;
      ctx.save();ctx.globalAlpha=lit?(hot?0.95:0.66):0.05;ctx.lineWidth=w+(hot&&lit?0.7:0);ctx.strokeStyle=col;ctx.shadowColor=col;ctx.shadowBlur=lit?9:0;ctx.lineCap="round";
      ctx.beginPath();ctx.moveTo(HUB[0],HUB[1]);ctx.quadraticCurveTo(cx,cy,P[0],P[1]);ctx.stroke();ctx.restore();
      if(!reduce&&lit){const sp=0.09+Math.min(0.15,f.thb/130000);const np=hot&&lit?4:2;
        for(let k=0;k<np;k++){let tt=((t*sp)+k/np+i*0.11)%1;const s=1-tt,u=1-s;const x=u*u*HUB[0]+2*u*s*cx+s*s*P[0],y=u*u*HUB[1]+2*u*s*cy+s*s*P[1];
          ctx.save();ctx.globalAlpha=Math.sin(s*Math.PI)*.9;ctx.fillStyle=col;ctx.shadowColor=col;ctx.shadowBlur=7;ctx.beginPath();ctx.arc(x,y,1.7,0,7);ctx.fill();ctx.restore();}}});
    COUNTRIES.forEach(c=>{if(!c.flows.some(vis))return;const P=px(c.lat,c.lon);const r=dotR(c);const lit=litC(c);const on=hot===c.country;
      ctx.save();ctx.globalAlpha=lit?1:.28;const cc=on?"#fbbf24":"#dbe6fb";ctx.shadowColor=cc;ctx.shadowBlur=on?12:4;ctx.fillStyle=cc;ctx.beginPath();ctx.arc(P[0],P[1],r,0,7);ctx.fill();ctx.restore();
      if(lit)txt(c.country,P[0],P[1]-r-4,on?"#ffe58a":"#c3d0e8","600 11px "+getFont(),3);});
    const pulse=reduce?0:Math.sin(t*1.6)*.5+.5,hr=view==="thb"?rad(COMPANIES.reduce((s,c)=>s+domTHB(c.id),0),165805,8,24):17;
    ctx.save();ctx.strokeStyle="rgba(74,222,128,"+(0.14+pulse*.2)+")";ctx.lineWidth=1.6;ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr+5+pulse*6,0,7);ctx.stroke();
    ctx.shadowColor="#4ade80";ctx.shadowBlur=15;ctx.fillStyle="#4ade80";ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr,0,7);ctx.fill();ctx.shadowBlur=0;ctx.fillStyle="rgba(8,12,21,.6)";ctx.beginPath();ctx.arc(HUB[0],HUB[1],hr*.34,0,7);ctx.fill();ctx.restore();
    txt("Thailand",HUB[0],HUB[1]-hr-6,"#d6ffe8","750 13px "+getFont(),3.4);
    raf=requestAnimationFrame(draw);
  }
  function getFont(){return '-apple-system,"Segoe UI",Roboto,Arial,sans-serif';}

  cv.addEventListener("pointermove",e=>{const r=cv.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let f=null;
    COUNTRIES.forEach(c=>{if(!c.flows.some(vis))return;const P=px(c.lat,c.lon);if(Math.hypot(P[0]-mx,P[1]-my)<dotR(c)+6)f=c.country;});
    if(f!==hot){hot=f;renderDetail();markHot();}cv.style.cursor=f?"pointer":"default";});
  cv.addEventListener("pointerleave",()=>{hot=null;renderDetail();markHot();});

  function sync(){renderBars();renderDetail();markHot();}
  document.getElementById("viewSeg").addEventListener("click",e=>{const b=e.target.closest("button");if(!b)return;view=b.dataset.v;document.querySelectorAll("#viewSeg button").forEach(x=>x.classList.toggle("on",x===b));renderBars();renderDetail();});
  let raf;new ResizeObserver(resize).observe(cv.parentNode);resize();renderBars();overview();raf=requestAnimationFrame(draw);
})();
</script>'''

HTML = HTML.replace('__LAND__', LAND)
open('worldmap.html','w',encoding='utf-8').write(HTML)
print('written chars:', len(HTML))
