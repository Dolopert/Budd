let entries = JSON.parse(localStorage.getItem('fs9') || '[]');
let curType = 'expense';
let curFilter = 'all';
let slipImgEl = null;     // full-res image for OCR/QR
let slipThumb = null;     // compressed thumbnail, ready to save immediately

function init(){
  const now=new Date();
  document.getElementById('fDate').value=now.toISOString().split('T')[0];
  document.getElementById('hdrDate').textContent=now.toLocaleDateString('th-TH',{weekday:'long',day:'numeric',month:'long',year:'numeric'});
  render(); setType('expense');
}

const imgZone=document.getElementById('imgZone'), fileInput=document.getElementById('fileInput'),
      slipPrev=document.getElementById('slipPreview'), imgHolder=document.getElementById('imgPlaceholder'),
      scanOverlay=document.getElementById('scanOverlay'), scanTxt=document.getElementById('scanTxt'),
      scanBar=document.getElementById('scanBar'),
      btnScan=document.getElementById('btnScan'), btnRemove=document.getElementById('btnRemoveImg');

document.getElementById('browseLink').onclick=e=>{e.stopPropagation();fileInput.click();};
imgZone.onclick=e=>{ if(!imgZone.classList.contains('has-img')) fileInput.click(); };
fileInput.onchange=e=>{
  const files=[...e.target.files]; e.target.value='';
  if(files.length===0) return;
  if(files.length===1){ loadImg(files[0]); }       // single โ’ normal form flow
  else { files.forEach(f=>batchFiles.push(f)); renderBatchTray(); } // multiple โ’ batch tray
};
imgZone.addEventListener('dragover',e=>{e.preventDefault();imgZone.classList.add('drag-over');});
imgZone.addEventListener('dragleave',()=>imgZone.classList.remove('drag-over'));
imgZone.addEventListener('drop',e=>{e.preventDefault();imgZone.classList.remove('drag-over'); if(e.dataTransfer.files[0]) loadImg(e.dataTransfer.files[0]);});

function loadImg(file){
  const reader=new FileReader();
  reader.onload=ev=>{
    const dataUrl=ev.target.result;
    slipPrev.src=dataUrl; slipPrev.classList.add('show');
    imgHolder.style.display='none'; imgZone.classList.add('has-img'); imgZone.style.cursor='default';
    document.getElementById('qrResult').classList.remove('show');
    document.getElementById('ocrBanner').classList.remove('show');
    clearOcrHighlight();
    slipThumb=null;
    slipImgEl=new Image();
    slipImgEl.onload=()=>{ slipThumb=makeThumbFrom(slipImgEl); };
    slipImgEl.src=dataUrl;
  };
  reader.readAsDataURL(file);
}

btnRemove.onclick=e=>{ e.stopPropagation(); resetImage(); };
function resetImage(){
  slipImgEl=null; slipThumb=null;
  slipPrev.src=''; slipPrev.classList.remove('show');
  imgHolder.style.display=''; imgZone.classList.remove('has-img'); imgZone.style.cursor='';
  fileInput.value='';
  document.getElementById('qrResult').classList.remove('show');
  document.getElementById('ocrBanner').classList.remove('show');
  clearOcrHighlight();
}

function qrDecode(imgEl){
  try{
    const c=document.createElement('canvas'), ctx=c.getContext('2d');
    let w=imgEl.naturalWidth, h=imgEl.naturalHeight;
    const s=Math.min(1,1400/Math.max(w,h));
    w=Math.round(w*s); h=Math.round(h*s); c.width=w; c.height=h;
    ctx.drawImage(imgEl,0,0,w,h);
    const d=ctx.getImageData(0,0,w,h);
    const code=(typeof jsQR==='function')?jsQR(d.data,w,h,{inversionAttempts:'attemptBoth'}):null;
    return code?code.data:null;
  }catch{ return null; }
}

function makeOcrCanvas(imgEl){
  const c=document.createElement('canvas'), ctx=c.getContext('2d');
  let w=imgEl.naturalWidth, h=imgEl.naturalHeight;
  const scale=Math.min(3, 2000/Math.max(w,h));
  w=Math.round(w*scale); h=Math.round(h*scale); c.width=w; c.height=h;
  ctx.imageSmoothingEnabled=true; ctx.imageSmoothingQuality='high';
  ctx.drawImage(imgEl,0,0,w,h);
  const img=ctx.getImageData(0,0,w,h), p=img.data;
  let sum=0;
  for(let i=0;i<p.length;i+=4){ const g=0.299*p[i]+0.587*p[i+1]+0.114*p[i+2]; p[i]=p[i+1]=p[i+2]=g; sum+=g; }
  const thr=(sum/(p.length/4))*0.92;
  for(let i=0;i<p.length;i+=4){
    let g=(p[i]-128)*1.6+128;
    if(g<thr-30) g=Math.max(0,g-40); else if(g>thr+30) g=Math.min(255,g+40);
    g=g<0?0:g>255?255:g; p[i]=p[i+1]=p[i+2]=g;
  }
  ctx.putImageData(img,0,0); return c;
}

// โ”€โ”€ Scan: QR + OCR โ”€โ”€
btnScan.onclick=async e=>{
  e.stopPropagation();
  if(!slipImgEl) return;
  if(typeof Tesseract==='undefined'){ toast('OCR engine เธขเธฑเธเนเธซเธฅเธ”เนเธกเนเน€เธชเธฃเนเธ เธฅเธญเธเนเธซเธกเน','err'); return; }
  btnScan.disabled=true; btnRemove.disabled=true;
  scanOverlay.classList.add('show'); scanBar.style.width='0%';

  scanTxt.textContent='เธเธณเธฅเธฑเธเธชเนเธเธ QRโ€ฆ';
  let qrData=null;
  try{ qrData=qrDecode(slipImgEl); }catch{}
  if(qrData){
    const isUrl=/^https?:\/\//i.test(qrData);
    document.getElementById('qrText').innerHTML='QR: '+(isUrl?`<a href="${esc(qrData)}" target="_blank" rel="noopener">${esc(qrData)}</a>`:esc(qrData));
    document.getElementById('qrResult').classList.add('show');
    const refMatch=qrData.match(/(?:ref|transRef|billerID)[=:]?\s*([A-Za-z0-9]{6,})/i)||qrData.match(/[?&]ref=([A-Za-z0-9]{6,})/i)||qrData.match(/\b([A-Za-z0-9]{12,})\b/);
    if(refMatch) setField('fRef',refMatch[1]);
  }

  scanTxt.textContent='เธเธณเธฅเธฑเธเธญเนเธฒเธเธเนเธญเธเธงเธฒเธก (OCR)โ€ฆ';
  let text='';
  try{
    const canvas=makeOcrCanvas(slipImgEl);
    const result=await Tesseract.recognize(canvas,'tha+eng',{
      logger:m=>{
        if(m.status==='recognizing text'){ scanBar.style.width=Math.round(m.progress*100)+'%'; }
        else if(m.status==='loading language traineddata'||m.status==='initializing tesseract'){ scanTxt.textContent='เธเธณเธฅเธฑเธเนเธซเธฅเธ”เธ•เธฑเธงเธญเนเธฒเธ OCRโ€ฆ'; }
      }
    });
    text=result?.data?.text||'';
  }catch(err){
    scanOverlay.classList.remove('show'); btnScan.disabled=false; btnRemove.disabled=false;
    toast('OCR เนเธกเนเธชเธณเน€เธฃเนเธ โ€” เธเธฃเธญเธเน€เธญเธเนเธ”เนเน€เธฅเธข','err'); return;
  }

  const found=parseSlipText(text);
  applyParsed(found);
  document.getElementById('ocrBanner').classList.add('show');
  scanOverlay.classList.remove('show'); btnScan.disabled=false; btnRemove.disabled=false;
  const n=Object.values(found).filter(v=>v!=null && v!=='').length;
  toast(n? `เธชเนเธเธเธเธญเธฃเนเธกเนเธฅเนเธง เธเธ ${n} เธเนเธญเธ โ“` : 'เธญเนเธฒเธเนเธ”เนเนเธกเนเธเธฑเธ” โ€” เธเธฃเธธเธ“เธฒเธเธฃเธญเธเน€เธญเธ', n?'ok':'err');
};

// โ•โ•โ•โ•โ•โ•โ•โ• Batch: เธซเธฅเธฒเธขเธชเธฅเธดเธ + เธเธฑเธ”เธขเธทเธเธขเธฑเธ โ•โ•โ•โ•โ•โ•โ•โ•
let reviewQueue=[];   // [{id, found, thumb, dataUrl}]

let batchFiles=[];   // accumulated File objects waiting to be scanned

document.getElementById('batchAddMore').onclick=()=>{ document.getElementById('batchInput').click(); };
document.getElementById('batchInput').onchange=e=>{
  const files=[...e.target.files]; e.target.value='';
  files.forEach(f=>batchFiles.push(f));
  renderBatchTray();
};
document.getElementById('batchStart').onclick=()=>{
  if(!batchFiles.length) return;
  const files=batchFiles.slice();
  clearBatchTray();
  runBatch(files);
};
function clearBatchTray(){ batchFiles=[]; renderBatchTray(); }
function removeBatchAt(i){ batchFiles.splice(i,1); renderBatchTray(); }
function renderBatchTray(){
  const tray=document.getElementById('batchTray');
  const thumbs=document.getElementById('batchThumbs');
  if(!batchFiles.length){ tray.style.display='none'; thumbs.innerHTML=''; return; }
  tray.style.display='block';
  document.getElementById('batchTrayCount').textContent=`เน€เธฅเธทเธญเธเนเธฅเนเธง ${batchFiles.length} เธฃเธนเธ`;
  document.getElementById('batchStart').textContent=`๐” เน€เธฃเธดเนเธกเธชเนเธเธ (${batchFiles.length})`;
  thumbs.innerHTML='';
  batchFiles.forEach((f,i)=>{
    const div=document.createElement('div'); div.className='bt-item';
    const img=document.createElement('img');
    const r=new FileReader(); r.onload=ev=>{ img.src=ev.target.result; }; r.readAsDataURL(f);
    const x=document.createElement('button'); x.className='bt-x'; x.textContent='โ•'; x.onclick=()=>removeBatchAt(i);
    div.appendChild(img); div.appendChild(x); thumbs.appendChild(div);
  });
}

function loadImageEl(file){
  return new Promise((resolve,reject)=>{
    const r=new FileReader();
    r.onload=ev=>{ const im=new Image(); im.onload=()=>resolve({img:im,dataUrl:ev.target.result}); im.onerror=reject; im.src=ev.target.result; };
    r.onerror=reject; r.readAsDataURL(file);
  });
}
function makeThumbFrom(imgEl){
  try{ const max=360; let w=imgEl.naturalWidth,h=imgEl.naturalHeight; const s=Math.min(1,max/Math.max(w,h)); const cw=Math.round(w*s),ch=Math.round(h*s); const c=document.createElement('canvas'); c.width=cw;c.height=ch; const x=c.getContext('2d'); x.fillStyle='#fff';x.fillRect(0,0,cw,ch); x.drawImage(imgEl,0,0,cw,ch); return c.toDataURL('image/jpeg',0.7); }catch{ return null; }
}

async function runBatch(files){
  if(typeof Tesseract==='undefined'){ toast('OCR เธขเธฑเธเนเธซเธฅเธ”เนเธกเนเน€เธชเธฃเนเธ เธฅเธญเธเนเธซเธกเน','err'); return; }
  reviewQueue=[];
  scanOverlay.classList.add('show'); imgZone.classList.add('has-img');
  imgHolder.style.display='none';

  const batchWrap=document.getElementById('batchProgressWrap');
  const batchBar=document.getElementById('batchBar');
  const batchLabel=document.getElementById('batchProgressLabel');
  const ocrLabel=document.getElementById('ocrLabel');
  batchWrap.style.display= files.length>1 ? 'block' : 'none';
  batchBar.style.width='0%';
  batchLabel.textContent=`0 / ${files.length}`;

  let i=0;
  for(const f of files){
    i++;
    scanTxt.textContent=`เธเธณเธฅเธฑเธเธญเนเธฒเธเธชเธฅเธดเธ ${i}/${files.length}โ€ฆ`;
    ocrLabel.textContent=''; scanBar.style.width='0%';
    batchLabel.textContent=`${i-1} / ${files.length}`;
    batchBar.style.width=Math.round(((i-1)/files.length)*100)+'%';
    try{
      const {img,dataUrl}=await loadImageEl(f);
      const qr=qrDecode(img);
      let text='';
      try{ const res=await Tesseract.recognize(makeOcrCanvas(img),'tha+eng',{ logger:m=>{
        if(m.status==='recognizing text'){ scanBar.style.width=Math.round(m.progress*100)+'%'; ocrLabel.textContent='OCR '+Math.round(m.progress*100)+'%'; }
      }}); text=res?.data?.text||''; }catch{}
      const found=parseSlipText(text);
      if(qr){ const rm=qr.match(/(?:ref|transRef|billerID)[=:]?\s*([A-Za-z0-9]{6,})/i)||qr.match(/[?&]ref=([A-Za-z0-9]{6,})/i)||qr.match(/\b([A-Za-z0-9]{12,})\b/); if(rm && !found.ref) found.ref=rm[1]; }
      const c=classifyCategory(found); if(c) found.category=c.cat;
      // duplicate check: same date + amount already in saved entries or earlier in this batch
      const isDup = !!(found.amount>0 && found.date) && (
        entries.some(e=>e.date===found.date && Math.abs(e.amount-found.amount)<0.01) ||
        reviewQueue.some(q=>q.found.date===found.date && Math.abs((q.found.amount||0)-found.amount)<0.01)
      );
      reviewQueue.push({ id:'rq'+Date.now()+Math.random(), found, thumb:makeThumbFrom(img), dataUrl, duplicate:isDup });
    }catch{}
  }
  batchBar.style.width='100%'; batchLabel.textContent=`${files.length} / ${files.length}`;
  setTimeout(()=>{ scanOverlay.classList.remove('show'); batchWrap.style.display='none'; resetImage();
    if(!reviewQueue.length){ toast('เธญเนเธฒเธเธชเธฅเธดเธเนเธกเนเธชเธณเน€เธฃเนเธ','err'); return; }
    openReview();
  }, 400);
}

// โ•โ•โ•โ•โ•โ•โ•โ• Review: listing + swipe per row โ•โ•โ•โ•โ•โ•โ•โ•
function catIcon(cat){
  const c=cat||'';
  if(/เธญเธฒเธซเธฒเธฃ|เน€เธเธฃเธทเนเธญเธเธ”เธทเนเธก/.test(c)) return '๐”';
  if(/เธเธญเธเธเธณ|เธเธธเธเน€เธเธญเธฃเน/.test(c)) return '๐’';
  if(/เน€เธ”เธดเธเธ—เธฒเธ/.test(c)) return '๐—';
  if(/เธชเธฒเธเธฒเธฃเธ“เธนเธเนเธ เธ/.test(c)) return '๐’ก';
  if(/เธชเธธเธเธ เธฒเธ|เธขเธฒ/.test(c)) return '๐’';
  if(/เธเนเธญเธเธเธดเนเธ/.test(c)) return '๐๏ธ';
  if(/เธเธฑเธเน€เธ—เธดเธ/.test(c)) return '๐ฌ';
  if(/เน€เธ•เธดเธกเน€เธเธดเธ|wallet/i.test(c)) return '๐“ฒ';
  if(/เน€เธเนเธฒ|เธ—เธตเนเธเธฑเธ/.test(c)) return '๐ ';
  if(/เธเธฒเธฃเธจเธถเธเธฉเธฒ/.test(c)) return '๐“';
  return '๐งพ';
}

function openReview(){
  document.getElementById('reviewScreen').classList.add('show');
  renderReviewList();
}
function closeReview(){
  document.getElementById('reviewScreen').classList.remove('show');
  document.getElementById('reviewList').innerHTML='';
}
function updateReviewProgress(){
  document.getElementById('reviewProgress').textContent=`เน€เธซเธฅเธทเธญ ${reviewQueue.length} เนเธ`;
}

function renderReviewList(){
  updateReviewProgress();
  const list=document.getElementById('reviewList');
  list.innerHTML='';
  if(!reviewQueue.length){ finishReview(); return; }
  reviewQueue.forEach(item=>{ list.appendChild(buildReviewRow(item)); });
}

function buildReviewRow(item){
  const f=item.found;
  const sym=f.currency||'เธฟ';
  const amtCls=f.type==='income'?'income':'expense';
  const amtSign=f.type==='income'?'+':'โ’';
  const amtTxt=`${amtSign}${sym}${(f.amount||0).toLocaleString('th-TH',{minimumFractionDigits:2})}`;
  const sub=`${esc(f.category||'')}${f.category&&f.date?' ยท ':''}${esc(f.date||'')}`;

  const wrap=document.createElement('div'); wrap.className='sw-wrap'; wrap.dataset.id=item.id;
  wrap.innerHTML=`<div class="sw-bg">
    <div class="bg-save"><span class="bg-lbl">โ“ เธเธฑเธเธ—เธถเธ</span></div>
    <div class="bg-del"><span class="bg-lbl">โ• เธฅเธ</span></div>
  </div>`;

  const card=document.createElement('div'); card.className='rcard';
  card.innerHTML=`
    <div class="rc-ico">${catIcon(f.category)}</div>
    <div class="rc-mid">
      <div class="rc-title">${esc(f.desc||'(เนเธกเนเธกเธตเธฃเธฒเธขเธเธฒเธฃ)')}</div>
      <div class="rc-sub">${sub}</div>
      ${item.duplicate?'<span class="rc-dup">โ  เธญเธฒเธเธเนเธณ</span>':''}
    </div>
    <div class="rc-amt ${amtCls}">${amtTxt}</div>`;
  wrap.appendChild(card);

  attachRowSwipe(card, wrap,
    ()=> dismissRow(item.id,'save'),
    ()=> dismissRow(item.id,'del'),
    ()=> openEditModal(item.id)
  );
  return wrap;
}

function attachRowSwipe(card, wrap, onSave, onDel, onTap){
  let startX=0, startY=0, curX=0, dragging=false, moved=false;
  const bgSave=wrap.querySelector('.bg-save');
  const bgDel =wrap.querySelector('.bg-del');
  const TH=100;

  const down=x=>{ startX=x; dragging=true; moved=false; card.style.transition='none'; };
  const move=(x,y)=>{
    if(!dragging) return;
    curX=x-startX;
    if(Math.abs(curX)>8) moved=true;
    card.style.transform=`translateX(${curX}px)`;
    const o=Math.min(1,Math.abs(curX)/TH);
    if(curX>0){ bgSave.style.opacity=o; bgDel.style.opacity=0; }
    else       { bgDel.style.opacity=o; bgSave.style.opacity=0; }
  };
  const up=()=>{
    if(!dragging) return; dragging=false;
    if(!moved){ card.style.transform=''; bgSave.style.opacity=0; bgDel.style.opacity=0; onTap(); return; }
    card.style.transition='transform .2s ease, opacity .2s ease';
    if(curX>TH)       { card.style.transform=`translateX(110%)`; card.style.opacity='0'; setTimeout(()=>onSave(),200); }
    else if(curX<-TH) { card.style.transform=`translateX(-110%)`; card.style.opacity='0'; setTimeout(()=>onDel(),200); }
    else              { card.style.transform=''; bgSave.style.opacity=0; bgDel.style.opacity=0; }
    curX=0;
  };

  card.addEventListener('touchstart',e=>{ const t=e.touches[0]; startX=t.clientX; startY=t.clientY; down(t.clientX); },{passive:true});
  card.addEventListener('touchmove', e=>{ const t=e.touches[0]; if(Math.abs(t.clientX-startX)>Math.abs(t.clientY-startY)) move(t.clientX,t.clientY); },{passive:true});
  card.addEventListener('touchend',  up);
  card.addEventListener('mousedown', e=>down(e.clientX));
  window.addEventListener('mousemove',e=>{ if(dragging) move(e.clientX,e.clientY); });
  window.addEventListener('mouseup',  ()=>{ if(dragging) up(); });
}

function dismissRow(id, action){
  const idx=reviewQueue.findIndex(x=>x.id===id); if(idx<0) return;
  const item=reviewQueue[idx];
  if(action==='save') saveFromReview(item.found, item.thumb);
  reviewQueue.splice(idx,1);
  // remove the DOM row
  const el=document.querySelector(`.sw-wrap[data-id="${id}"]`);
  if(el) el.remove();
  updateReviewProgress();
  if(!reviewQueue.length) finishReview();
}

function saveFromReview(f, thumb){
  if(!f.amount || f.amount<=0) return;
  const entry={ id:Date.now()+Math.floor(Math.random()*1000), type:f.type||'expense',
    desc:f.desc||'(เนเธกเนเธกเธตเธฃเธฒเธขเธเธฒเธฃ)', amount:f.amount, date:f.date||new Date().toISOString().split('T')[0],
    time:new Date().toTimeString().slice(0,8),
    currency:f.currency||'เธฟ', category:f.category||'', method:'เนเธญเธเน€เธเธดเธ (Internet Banking)',
    ref:f.ref||'', note:f.note||'', thumb:thumb||null };
  entries.unshift(entry);
  rememberCategory(entry);
  if(!save()){
    // localStorage full โ€” retry without thumbnail to at least save the data
    entry.thumb=null;
    if(!save()){ entries.shift(); toast('เธเธทเนเธเธ—เธตเนเน€เธเนเธเธเนเธญเธกเธนเธฅเน€เธ•เนเธก โ€” เธเธฑเธเธ—เธถเธเนเธกเนเนเธ”เน','err'); return; }
    toast('เธเธฑเธเธ—เธถเธเนเธฅเนเธง (เนเธกเนเธกเธตเธฃเธนเธ โ€” เธเธทเนเธเธ—เธตเนเน€เธ•เนเธก)','ok');
  }
  if(getSheetUrl() && autoSendOn()){ entry.synced=true; sendToSheet([sheetRow(entry)]).catch(()=>{ entry.synced=false; save(); }); }
}

function finishReview(){
  closeReview(); render();
  window.scrollTo({top:0,behavior:'smooth'});
  toast('เธเธฑเธเธ—เธถเธเธชเธฅเธดเธเน€เธชเธฃเนเธเธชเธดเนเธ โ“','ok');
}

// โ•โ•โ•โ•โ•โ•โ•โ• Edit modal โ•โ•โ•โ•โ•โ•โ•โ•
let _editId=null;
function openEditModal(id){
  const item=reviewQueue.find(x=>x.id===id); if(!item) return;
  _editId=id;
  const f=item.found;
  document.getElementById('eType').value=f.type||'expense';
  document.getElementById('eAmt').value=f.amount||'';
  document.getElementById('eDate').value=f.date||'';
  document.getElementById('eDesc').value=f.desc||'';
  document.getElementById('eCat').value=f.category||'';
  document.getElementById('eRef').value=f.ref||'';
  document.getElementById('eNote').value=f.note||'';
  document.getElementById('editModal').classList.add('show');
}
function closeEditModal(){ document.getElementById('editModal').classList.remove('show'); _editId=null; }
function saveEditModal(){
  if(!_editId) return;
  const item=reviewQueue.find(x=>x.id===_editId); if(!item) return;
  item.found.type=document.getElementById('eType').value;
  item.found.amount=parseFloat(document.getElementById('eAmt').value)||0;
  item.found.date=document.getElementById('eDate').value;
  item.found.desc=document.getElementById('eDesc').value;
  item.found.category=document.getElementById('eCat').value;
  item.found.ref=document.getElementById('eRef').value;
  item.found.note=document.getElementById('eNote').value;
  closeEditModal();
  // update the row in listing without full re-render
  const wrap=document.querySelector(`.sw-wrap[data-id="${_editId}"]`);
  if(wrap){ const fresh=buildReviewRow(item); wrap.replaceWith(fresh); }
  else renderReviewList();
  toast('เนเธเนเนเธเนเธฅเนเธง โ€” เธเธฑเธ”เธเธงเธฒเน€เธเธทเนเธญเธเธฑเธเธ—เธถเธ โ“','ok');
}
document.getElementById('editModal').addEventListener('click',e=>{ if(e.target.id==='editModal') closeEditModal(); });



// โ”€โ”€ Parse OCR text (note is NOT auto-filled) โ”€โ”€
// โ”€โ”€ OCR noise cleaning โ”€โ”€
// remove stray OCR symbols and lone junk characters
function cleanLine(l){
  if(!l) return '';
  let s=l.trim();
  // remove characters that are almost never in slips (OCR artifacts)
  s=s.replace(/[|~`^ยฌยฐโ€ขยท_=<>{}\[\]\\\/]+/g,' ');
  // collapse repeated punctuation/spaces
  s=s.replace(/\s{2,}/g,' ').replace(/[.\-]{3,}/g,' ').trim();
  // drop a line that is just 1 stray character (e.g. a lone "เธ" or "x")
  if(s.length<=1) return '';
  // drop lines with no letters/digits at all (pure symbols)
  if(!/[A-Za-z0-9เธ-เน]/.test(s)) return '';
  return s;
}
// is a single token meaningful, or is it OCR junk?
function meaningfulToken(tok){
  if(!tok) return false;
  if(tok.length<=1) return false;                 // lone character e.g. "เธ", "x"
  if(/^[\d.\-,:/]+$/.test(tok) && tok.length<=3) return false; // short numeric/symbol junk e.g. "7/", "12-", ":"
  // short latin token with no vowel and not an ALL-CAPS acronym โ’ gibberish (e.g. "xvn", "kfg")
  if(/^[A-Za-z]+$/.test(tok) && tok.length<=4 && !/[aeiouAEIOU]/.test(tok) && tok!==tok.toUpperCase()) return false;
  return true;
}
// clean an extracted name: strip symbols, drop meaningless fragments, trim lone letters
function cleanName(s){
  if(!s) return '';
  // strip OCR artifact symbols incl. parentheses, slashes, quotes, math signs
  let t=s.replace(/[|~`^ยฌยฐโ€ขยท_=<>{}\[\]\\\/()"'*+]+/g,' ').replace(/\s{2,}/g,' ').trim();
  // drop meaningless tokens (lone letters, "7/", gibberish)
  t=t.split(' ').filter(meaningfulToken).join(' ');
  // remove trailing/leading single stray letters left from OCR (e.g. "เธชเธกเธเธฒเธข เธ")
  t=t.replace(/\s+[A-Za-zเธ-เน]\s*$/,'').replace(/^\s*[A-Za-zเธ-เน]\s+/,'');
  return t.trim();
}

// เนเธเนเธเธณ OCR เธ—เธตเนเน€เธเธตเนเธขเธเธเนเธญเธขเธ•เธฒเธกเธเธฃเธดเธเธ—
const OCR_FIXES = [
  // เนเธญเธเน€เธเธดเธ
  [/เนเธญ[เธเธบ]?เนเธซเน/g,'เนเธญเธเนเธซเน'], [/เนเธญเน€เธเธดเธ/g,'เนเธญเธเน€เธเธดเธ'], [/เนเธญเธเน€เธเธดเธ/g,'เนเธญเธเน€เธเธดเธ'], [/เนเธญเธ เน€เธเธดเธ/g,'เนเธญเธเน€เธเธดเธ'],
  // เธเธณเธเธงเธ
  [/เธเนเธฒเธเธงเธ/g,'เธเธณเธเธงเธ'], [/เธเธฒเธเธงเธ/g,'เธเธณเธเธงเธ'], [/เธเน?เธฒเธเธงเธ/g,'เธเธณเธเธงเธ'],
  // เน€เธฅเธเธ—เธตเนเธฃเธฒเธขเธเธฒเธฃ
  [/เน€เธฅเธเธ—เธต[เนเธต]?เธฃเธฒเธขเธเธฒเธฃ/g,'เน€เธฅเธเธ—เธตเนเธฃเธฒเธขเธเธฒเธฃ'], [/เน€เธฅเธเธ—เธต เธฃเธฒเธขเธเธฒเธฃ/g,'เน€เธฅเธเธ—เธตเนเธฃเธฒเธขเธเธฒเธฃ'],
  // เธเนเธฒเธเธฃเธฃเธกเน€เธเธตเธขเธก
  [/เธเนเธฒเธเธฃเธฃเธกเน€เธเธต?เธขเธก/g,'เธเนเธฒเธเธฃเธฃเธกเน€เธเธตเธขเธก'], [/เธเนเธฒเธเธฃเธฃเธกเน€เธเธขเธก/g,'เธเนเธฒเธเธฃเธฃเธกเน€เธเธตเธขเธก'],
  // เธชเธณเน€เธฃเนเธ
  [/เธชเธฒเน€เธฃเนเธ/g,'เธชเธณเน€เธฃเนเธ'], [/เธชเน?เธฒเน€เธฃเนเธ/g,'เธชเธณเน€เธฃเนเธ'], [/เธช[เธฑเธฒ]เน€เธฃเนเธ/g,'เธชเธณเน€เธฃเนเธ'],
  // เธเธฒเธ—
  [/เธเธฒ เธ—/g,'เธเธฒเธ—'], [/เธเธฒเธซ/g,'เธเธฒเธ—'],
  // เธเธฃเนเธญเธกเน€เธเธขเน
  [/เธเธฃเนเธญเธกเน€เธเธข/g,'เธเธฃเนเธญเธกเน€เธเธขเน'], [/เธเธฃเธญเธกเน€เธเธขเน/g,'เธเธฃเนเธญเธกเน€เธเธขเน'],
  // เธเธฒเธข/เธเธฒเธ/เธเธฒเธเธชเธฒเธง
  [/เธ\s*\.\s*เธช\s*\./g,'เธ.เธช.'], [/เธเธฒเธเธชเธฒเน…/g,'เธเธฒเธเธชเธฒเธง'],
  // เธ—เธฑเนเธงเนเธ: เธ•เธฑเธ” zero-width / เธญเธฑเธเธเธฃเธฐเนเธเธฅเธ
  [/[\u200B-\u200D\uFEFF]/g,''],
];
function fixOcrWords(t){
  let s=t||'';
  for(const [re,rep] of OCR_FIXES){ s=s.replace(re,rep); }
  return s;
}

function parseSlipText(raw){
  const out={ amount:null, date:null, ref:null, type:null, desc:null, note:null, sender:null, receiver:null, payee:null };
  if(!raw) return out;
  const text=fixOcrWords(raw.replace(/\u00A0/g,' '));
  // clean lines: drop pure-noise lines and stray single junk characters
  const lines=text.split(/\n+/)
    .map(l=>cleanLine(l))
    .filter(l=>l && l.length>0);

  const amtCandidates=[];
  const numRe=/(\d{1,3}(?:,\d{3})*(?:\.\d{2})|\d+\.\d{2})/g;
  lines.forEach(l=>{
    const near=/เธเธณเธเธงเธ|เธเธฒเธ—|amount|baht|THB/i.test(l);
    let m; while((m=numRe.exec(l))!==null){
      const val=parseFloat(m[1].replace(/,/g,''));
      if(val>0) amtCandidates.push({val, near, isFee:/เธเธฃเธฃเธกเน€เธเธตเธขเธก|fee/i.test(l)});
    }
  });
  let m2; while((m2=numRe.exec(text))!==null){ const val=parseFloat(m2[1].replace(/,/g,'')); if(val>0) amtCandidates.push({val,near:false,isFee:false}); }
  const nonFee=amtCandidates.filter(c=>!c.isFee);
  if(nonFee.length){ const near=nonFee.filter(c=>c.near); const pool=near.length?near:nonFee; out.amount=Math.max(...pool.map(c=>c.val)); }

  const thMonths={'เธก.เธ.':1,'เธกเธเธฃเธฒเธเธก':1,'เธ.เธ.':2,'เธเธธเธกเธ เธฒเธเธฑเธเธเน':2,'เธกเธต.เธ.':3,'เธกเธตเธเธฒเธเธก':3,'เน€เธก.เธข.':4,'เน€เธกเธฉเธฒเธขเธ':4,'เธ.เธ.':5,'เธเธคเธฉเธ เธฒเธเธก':5,'เธกเธด.เธข.':6,'เธกเธดเธ–เธธเธเธฒเธขเธ':6,'เธ.เธ.':7,'เธเธฃเธเธเธฒเธเธก':7,'เธช.เธ.':8,'เธชเธดเธเธซเธฒเธเธก':8,'เธ.เธข.':9,'เธเธฑเธเธขเธฒเธขเธ':9,'เธ•.เธ.':10,'เธ•เธธเธฅเธฒเธเธก':10,'เธ.เธข.':11,'เธเธคเธจเธเธดเธเธฒเธขเธ':11,'เธ.เธ.':12,'เธเธฑเธเธงเธฒเธเธก':12};
  let dm=text.match(/(\d{1,2})\s*(เธก\.เธ\.|เธ\.เธ\.|เธกเธต\.เธ\.|เน€เธก\.เธข\.|เธ\.เธ\.|เธกเธด\.เธข\.|เธ\.เธ\.|เธช\.เธ\.|เธ\.เธข\.|เธ•\.เธ\.|เธ\.เธข\.|เธ\.เธ\.|เธกเธเธฃเธฒเธเธก|เธเธธเธกเธ เธฒเธเธฑเธเธเน|เธกเธตเธเธฒเธเธก|เน€เธกเธฉเธฒเธขเธ|เธเธคเธฉเธ เธฒเธเธก|เธกเธดเธ–เธธเธเธฒเธขเธ|เธเธฃเธเธเธฒเธเธก|เธชเธดเธเธซเธฒเธเธก|เธเธฑเธเธขเธฒเธขเธ|เธ•เธธเธฅเธฒเธเธก|เธเธคเธจเธเธดเธเธฒเธขเธ|เธเธฑเธเธงเธฒเธเธก)\s*(\d{2,4})/);
  if(dm){
    const d=parseInt(dm[1],10), mo=thMonths[dm[2]], y=parseInt(dm[3],10);
    let year=y<100?2500+y:y; if(year>2400)year-=543;
    out.date=`${year}-${String(mo).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
  } else {
    let dm2=text.match(/(\d{1,2})[\/\-.](\d{1,2})[\/\-.](\d{2,4})/);
    if(dm2){ let d=+dm2[1],mo=+dm2[2],y=+dm2[3]; let year=y<100?2500+y:y; if(year>2400)year-=543; out.date=`${year}-${String(mo).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
    else { let dm3=text.match(/(20\d{2})[\-.](\d{1,2})[\-.](\d{1,2})/); if(dm3) out.date=`${dm3[1]}-${String(+dm3[2]).padStart(2,'0')}-${String(+dm3[3]).padStart(2,'0')}`; }
  }

  let refLine=lines.find(l=>/เน€เธฅเธเธ—เธตเนเธฃเธฒเธขเธเธฒเธฃ|เธฃเธฒเธขเธเธฒเธฃ|ref|transaction/i.test(l));
  let refStr=(refLine||text).match(/([A-Z0-9]{10,})/i);
  if(refStr) out.ref=refStr[1];

  if(/เธฃเธฑเธเน€เธเธดเธ|เน€เธเธดเธเน€เธเนเธฒ|received|เนเธญเธเน€เธเธดเธเธฃเธฑเธ/i.test(text)) out.type='income';
  else if(/เนเธญเธเน€เธเธดเธ|เน€เธ•เธดเธกเน€เธเธดเธ|เธเนเธฒเธข|เธเธณเธฃเธฐ|payment|transfer/i.test(text)) out.type='expense';

  // โ”€โ”€ extract names (sender / receiver) โ”€โ”€
  // Thai slips list names with prefixes เธเธฒเธข/เธเธฒเธ/เธ.เธช./เธเธเธ./เธเธฃเธดเธฉเธฑเธ—, or service names like "TrueMoney Wallet"
  const nameRe=/(เธเธฒเธข|เธเธฒเธเธชเธฒเธง|เธ\.เธช\.|เธเธฒเธ|เธ”\.เธ\.|เธ”\.เธ\.|เธเธเธ\.|เธเธกเธ\.|เธเธฃเธดเธฉเธฑเธ—)\s*[^\n]{1,40}/g;
  const names=[];
  let nm; while((nm=nameRe.exec(text))!==null){ const c=cleanName(nm[0]); if(c.length>=3) names.push(c); }
  // service/merchant names (English-ish wallet/shop)
  const svc=lines.find(l=>/Wallet|TrueMoney|ShopeePay|Rabbit|PromptPay/i.test(l));

  // first name = sender (เธเธนเนเนเธญเธ), second = receiver (เธเธนเนเธฃเธฑเธ)
  out.sender = names[0] || null;
  out.receiver = names[1] || svc || null;

  // โ”€โ”€ เธฃเธฐเธเธธเธ—เธดเธจเธเธฒเธเธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธ (เนเธกเนเธเธเธงเนเธฒเน€เธ”เธฒเธเธฒเธเธเธณ) โ”€โ”€
  // เธ–เนเธฒเธ•เธฑเนเธเธเธทเนเธญ/เน€เธฅเธเธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธเนเธงเนเนเธ Admin เธเธฐเนเธเนเธฃเธฐเธเธธเธงเนเธฒเน€เธเธดเธเน€เธเนเธฒ/เธญเธญเธ
  const me=getMyAccounts(); // array of keywords (เธเธทเนเธญ/เน€เธฅเธเธเธฑเธเธเธต)
  if(me.length){
    const inSender = me.some(m=> out.sender && norm(out.sender).includes(norm(m)) );
    const inReceiver = me.some(m=> out.receiver && norm(out.receiver).includes(norm(m)) );
    // also check raw text halves: เธเธฑเธเธเธตเน€เธฃเธฒเธญเธขเธนเนเธเธฑเนเธเธเธ(เธเธนเนเนเธญเธ)=เธเนเธฒเธข, เธเธฑเนเธเธฅเนเธฒเธ(เธเธนเนเธฃเธฑเธ)=เธฃเธฑเธ
    if(inSender && !inReceiver) out.type='expense';
    else if(inReceiver && !inSender) out.type='income';
  }

  // For expense, the payee that matters = receiver. For income, the payer = sender.
  out.payee = (out.type==='income') ? (out.sender||out.receiver) : (out.receiver||out.sender);

  // description: prefer a meaningful payee; fall back to slip header
  if(out.payee){
    out.desc = cleanName(out.payee.replace(/^(เธเธฒเธข|เธเธฒเธเธชเธฒเธง|เธ\.เธช\.|เธเธฒเธ|เธ”\.เธ\.|เธ”\.เธ\.|เธเธเธ\.|เธเธกเธ\.|เธเธฃเธดเธฉเธฑเธ—)\s*/,'')).slice(0,40) || out.payee;
  } else if(/เน€เธ•เธดเธกเน€เธเธดเธ/.test(text)) out.desc='เน€เธ•เธดเธกเน€เธเธดเธ';
  else if(/เนเธญเธเน€เธเธดเธ/.test(text)) out.desc='เนเธญเธเน€เธเธดเธ';
  else { const head=cleanName(lines[0]||''); if(head && head.length<=30) out.desc=head; }
  // final scrub: never surface OCR junk in the description field
  if(out.desc){ out.desc=cleanName(out.desc); if(!out.desc) out.desc=null; }

  // note: record direction + both names so the key is traceable
  if(out.sender || out.receiver){
    out.note = `${out.type==='income'?'เธฃเธฑเธเธเธฒเธ':'เนเธญเธเนเธซเน'}: ${out.payee||''}`.trim();
  }

  out.fullText = text;  // for category classification
  return out;
}

// โ•โ•โ•โ•โ•โ•โ•โ• Category classifier (Level 1: keyword rules + Level 2: learned memory) โ•โ•โ•โ•โ•โ•โ•โ•
// Built-in keyword dataset (Thai merchants). Custom dataset (imported) is merged on top.
const CAT_RULES_DEFAULT = [
  { cat:'เธญเธฒเธซเธฒเธฃ & เน€เธเธฃเธทเนเธญเธเธ”เธทเนเธก', kw:['STARBUCKS','เธชเธ•เธฒเธฃเนเธเธฑเธเธชเน','CAFE AMAZON','เธเธฒเน€เธเน เธญเน€เธกเธเธญเธ','AMAZON','COFFEE','เธเธฒเนเธ','CAFE','เธเธฒเน€เธเน','MCDONALD','เนเธกเธเนเธ”เธเธฑเธฅ','KFC','เน€เธเน€เธญเธเธเธต','BURGER KING','เน€เธเธญเธฃเนเน€เธเธญเธฃเน','PIZZA','เธเธดเธเธเนเธฒ','PIZZA HUT','DOMINO','SUBWAY','SUKISHI','เธชเธธเธเธตเน','MK','เน€เธญเนเธกเน€เธ','SHABU','เธเธฒเธเธน','HOTPOT','YAYOI','เธขเธฒเนเธขเธญเธด','FUJI','เธเธนเธเธด','OISHI','เนเธญเธญเธดเธเธด','ZEN','BONCHON','เธเธญเธเธเธญเธ','TEXAS','CHESTER','เน€เธเธชเน€เธ•เธญเธฃเน','SWENSEN','DAIRY QUEEN','AFTER YOU','เธญเธฒเธเน€เธ•เธญเธฃเนเธขเธน','BAKERY','เน€เธเน€เธเธญเธฃเธตเน','S&P','เน€เธญเธชเนเธญเธเธ”เนเธเธต','AU BON PAIN','เธฃเนเธฒเธเธญเธฒเธซเธฒเธฃ','เธ เธฑเธ•เธ•เธฒเธเธฒเธฃ','เธญเธฒเธซเธฒเธฃ','BBQ','BUFFET','เธเธธเธเน€เธเนเธ•เน','เธเนเธงเธขเน€เธ•เธตเนเธขเธง','เธเนเธฒเธงเธกเธฑเธเนเธเน','FOODPANDA','เธเธนเนเธ”เนเธเธเธ”เนเธฒ','TRUE COFFEE','INTHANIN','เธญเธดเธเธ—เธเธดเธฅ','PUNTHAI','เธเธฑเธเธเธธเนเนเธ—เธข','CHATIME','เธเธฒเธ•เธฃเธฒเธกเธทเธญ'] },
  { cat:'เธเธญเธเธเธณ / เธเธธเธเน€เธเธญเธฃเนเธกเธฒเธฃเนเน€เธเนเธ•', kw:['7-ELEVEN','7 ELEVEN','SEVEN','เน€เธเน€เธงเนเธ','CP ALL','LOTUS','เนเธฅเธ•เธฑเธช','TESCO','เน€เธ—เธชเนเธเน','BIG C','เธเธดเนเธเธเธต','BIGC','MAKRO','เนเธกเนเธเนเธเธฃ','เนเธกเธเนเธเธฃ','TOPS','เธ—เนเธญเธเธชเน','VILLA MARKET','เธงเธดเธฅเธฅเนเธฒ','GOURMET','เธเธนเธฃเนเน€เธกเธ•เน','FOODLAND','เธเธนเนเธ”เนเธฅเธเธ”เน','FAMILYMART','เนเธเธกเธดเธฅเธตเนเธกเธฒเธฃเนเธ—','FAMILY MART','LAWSON','เธฅเธญเธงเนเธชเธฑเธ','CJ EXPRESS','เธเธตเน€เธ','MAX VALU','เนเธกเนเธเธเนเนเธงเธฅเธน','เธกเธดเธเธดเธกเธฒเธฃเนเธ—','เธฃเนเธฒเธเธชเธฐเธ”เธงเธเธเธทเนเธญ','เธ•เธฅเธฒเธ”','SUPERMARKET','เธเธธเธเน€เธเธญเธฃเนเธกเธฒเธฃเนเน€เธเนเธ•'] },
  { cat:'เธเธฒเธฃเน€เธ”เธดเธเธ—เธฒเธ', kw:['GRAB','เนเธเธฃเนเธ','GRABTAXI','BOLT','เนเธเธฅเธ—เน','LINE MAN','LINEMAN','เนเธฅเธเนเนเธกเธ','ROBINHOOD','เนเธฃเธเธดเธเธฎเธนเนเธ”','TAXI','เนเธ—เนเธเธเธตเน','TUKTUK','เธ•เธธเนเธเธ•เธธเนเธ','BTS','เธฃเธ–เนเธเธเนเธฒ','MRT','เน€เธญเนเธกเธญเธฒเธฃเนเธ—เธต','ARL','เนเธญเธฃเนเธเธญเธฃเนเธ•เธฅเธดเธเธเน','PTT','เธเธ•เธ—','BANGCHAK','เธเธฒเธเธเธฒเธ','SHELL','เน€เธเธฅเธฅเน','ESSO','เน€เธญเธชเนเธเน','CALTEX','เธเธฒเธฅเน€เธ—เนเธเธเน','SUSCO','เธเธฑเธชเนเธเน','เธเนเธณเธกเธฑเธ','FUEL','เน€เธ•เธดเธกเธเนเธณเธกเธฑเธ','EXPRESSWAY','เธ—เธฒเธเธ”เนเธงเธ','EASY PASS','M-FLOW','MFLOW','เธ—เธตเนเธเธญเธ”เธฃเธ–','PARKING','AIRASIA','เนเธญเธฃเนเน€เธญเน€เธเธตเธข','NOK AIR','เธเธเนเธญเธฃเน','เธเธฒเธฃเธเธดเธเนเธ—เธข','BANGKOK AIRWAYS','เธฃเธ–เธ—เธฑเธงเธฃเน','BUS','เธฃเธ–เน€เธกเธฅเน'] },
  { cat:'เธเนเธฒเธชเธฒเธเธฒเธฃเธ“เธนเธเนเธ เธ', kw:['เธเธฒเธฃเนเธเธเนเธฒ','MEA','เธเธฒเธฃเนเธเธเนเธฒเธเธเธฃเธซเธฅเธงเธ','PEA','เธเธฒเธฃเนเธเธเนเธฒเธชเนเธงเธเธ เธนเธกเธดเธ เธฒเธ','เนเธเธเนเธฒ','ELECTRIC','เธเนเธฒเนเธ','เธเธฒเธฃเธเธฃเธฐเธเธฒ','เธเธฃเธฐเธเธฒ','WATER','เธเนเธฒเธเนเธณ','MWA','PWA','TRUE','เธ—เธฃเธน','TRUEMOVE','AIS','เน€เธญเนเธญเน€เธญเธช','DTAC','เธ”เธตเนเธ—เธ','NT','TOT','CAT','3BB','เธ—เธฃเธตเธเธตเธเธต','เธญเธดเธเน€เธ—เธญเธฃเนเน€เธเนเธ•','INTERNET','WIFI','เธกเธทเธญเธ–เธทเธญ','เธเนเธฒเนเธ—เธฃ','เธเธณเธฃเธฐเธเธดเธฅ','HOSTING','DOMAIN','ICLOUD','DROPBOX','ADOBE','CANVA','NOTION','SUBSCRIPTION','เธเนเธฒเธชเธกเธฒเธเธดเธ'] },
  { cat:'เธชเธธเธเธ เธฒเธ / เธขเธฒ', kw:['เนเธฃเธเธเธขเธฒเธเธฒเธฅ','HOSPITAL','เธฃเธ.','เธเธฅเธดเธเธดเธ','CLINIC','PHARMACY','เธฃเนเธฒเธเธขเธฒ','เน€เธ เธชเธฑเธ','WATSONS','เธงเธฑเธ•เธชเธฑเธ','BOOTS','เธเธนเนเธ—เธชเน','FASCINO','เธเธฒเธชเธเธดเนเธ','PURE','EVE AND BOY','MATSUMOTO','BANGKOK HOSPITAL','BUMRUNGRAD','เธเธณเธฃเธธเธเธฃเธฒเธฉเธเธฃเน','SAMITIVEJ','เธชเธกเธดเธ•เธดเน€เธงเธ','BNH','PHYATHAI','เธเธเธฒเนเธ—','เธ—เธฑเธเธ•เธเธฃเธฃเธก','DENTAL','เธซเธกเธญเธเธฑเธ','เธ•เธฃเธงเธเธชเธธเธเธ เธฒเธ','เธงเธฑเธเธเธตเธ','VACCINE','เธขเธฒ','MEDICINE','เนเธงเนเธเธ•เธฒ','เธซเธญเนเธงเนเธ'] },
  { cat:'เธเนเธญเธเธเธดเนเธ', kw:['SHOPEE','เธเนเธญเธเธเธตเน','เธเนเธญเธเธเธตเน','LAZADA','เธฅเธฒเธเธฒเธ”เนเธฒ','TIKTOK SHOP','เธ•เธดเนเธเธ•เนเธญเธ','UNIQLO','เธขเธนเธเธดเนเธเธฅเน','H&M','ZARA','MUJI','เธกเธนเธเธด','SUPERSPORTS','ADIDAS','NIKE','CHARLES & KEITH','CENTRAL','เน€เธเนเธเธ—เธฃเธฑเธฅ','ROBINSON','เนเธฃเธเธดเธเธชเธฑเธ','THE MALL','เน€เธ”เธญเธฐเธกเธญเธฅเธฅเน','SIAM PARAGON','EMPORIUM','ICONSIAM','เนเธญเธเธญเธเธชเธขเธฒเธก','POWER BUY','เน€เธเธฒเน€เธงเธญเธฃเนเธเธฒเธข','BANANA IT','JIB','ADVICE','COM7','IT CITY','STUDIO 7','IKEA','เธญเธดเน€เธเธตเธข','HOMEPRO','เนเธฎเธกเนเธเธฃ','DOHOME','เธ”เธนเนเธฎเธก','THAIWATSADU','เนเธ—เธงเธฑเธชเธ”เธธ','GLOBAL HOUSE','INDEX LIVING','DAISO','เนเธ”เนเธเธฐ','MINISO'] },
  { cat:'เธเธฑเธเน€เธ—เธดเธ', kw:['NETFLIX','เน€เธเนเธ•เธเธฅเธดเธเธเน','SPOTIFY','เธชเธเธญเธ•เธดเธเธฒเธข','YOUTUBE','DISNEY','เธ”เธดเธชเธเธตเธขเน','HBO','VIU','เธงเธดเธง','WETV','IQIYI','PRIME VIDEO','APPLE MUSIC','APPLE TV','JOOX','MAJOR','เน€เธกเน€เธเธญเธฃเน','SF CINEMA','เน€เธญเธชเน€เธญเธ','เนเธฃเธเธซเธเธฑเธ','CINEMA','เธซเธเธฑเธ','STEAM','เธชเธ•เธตเธก','GARENA','เธเธฒเธฃเธตเธเนเธฒ','PLAYSTATION','XBOX','NINTENDO','GAME','เน€เธเธก','เธเธญเธเน€เธชเธดเธฃเนเธ•','CONCERT','TICKET'] },
  { cat:'เน€เธ•เธดเธกเน€เธเธดเธ / E-Wallet', kw:['TRUEMONEY','TRUE MONEY','เธ—เธฃเธนเธกเธฑเธเธเธตเน','TRUE WALLET','WALLET','เธงเธญเธฅเน€เธฅเนเธ—','RABBIT','เนเธฃเธเธเธดเธ—','LINE PAY','เนเธฅเธเนเน€เธเธขเน','SHOPEEPAY','เธเนเธญเธเธเธตเนเน€เธเธขเน','DOLFIN','เธ”เธญเธฅเธเธดเธ','AIRPAY','เธเธฃเนเธญเธกเน€เธเธขเน','PROMPTPAY','TOPUP','เน€เธ•เธดเธกเน€เธเธดเธ','เน€เธ•เธดเธกเน€เธเธก','GIFT CARD','เธเธฑเธ•เธฃเน€เธเธดเธเธชเธ”'] },
  { cat:'เธเนเธฒเน€เธเนเธฒ / เธ—เธตเนเธเธฑเธ', kw:['เธเนเธฒเน€เธเนเธฒ','RENT','RENTAL','เธเธญเธเนเธ”','CONDO','APARTMENT','เธญเธเธฒเธฃเนเธ—เน€เธกเธเธ—เน','เธซเธญเธเธฑเธ','DORMITORY','DORM','เธเนเธฒเธเน€เธเนเธฒ','AGODA','เธญเนเธเธ”เนเธฒ','BOOKING','HOTEL','เนเธฃเธเนเธฃเธก','AIRBNB','RESORT','เธฃเธตเธชเธญเธฃเนเธ—','HOSTEL','เธเนเธฒเธชเนเธงเธเธเธฅเธฒเธ','เธเธดเธ•เธดเธเธธเธเธเธฅ'] },
  { cat:'เธเธฒเธฃเธจเธถเธเธฉเธฒ', kw:['เธกเธซเธฒเธงเธดเธ—เธขเธฒเธฅเธฑเธข','UNIVERSITY','เนเธฃเธเน€เธฃเธตเธขเธ','SCHOOL','เธงเธดเธ—เธขเธฒเธฅเธฑเธข','COLLEGE','เธชเธ–เธฒเธเธฑเธ','INSTITUTE','เธเนเธฒเน€เธ—เธญเธก','TUITION','เธเธญเธฃเนเธช','COURSE','เธ•เธดเธง','เน€เธฃเธตเธขเธเธเธดเน€เธจเธฉ','UDEMY','COURSERA','SKILLLANE','SKOOLDIO','เธซเธเธฑเธเธชเธทเธญ','BOOK','SE-ED','เธเธตเน€เธญเนเธ”','NAIIN','เธเธฒเธขเธญเธดเธเธ—เธฃเน','B2S','KINOKUNIYA','เน€เธเธฃเธทเนเธญเธเน€เธเธตเธขเธ','STATIONERY'] },
];

// custom dataset imported by user (stored), merged with default
function customRules(){ try{ return JSON.parse(localStorage.getItem('fs9_customKw')||'[]'); }catch{ return []; } }
function getCatRules(){
  const custom=customRules();
  if(!custom.length) return CAT_RULES_DEFAULT;
  const map={};
  CAT_RULES_DEFAULT.forEach(r=>{ map[r.cat]=[...r.kw]; });
  custom.forEach(r=>{ if(!map[r.cat]) map[r.cat]=[]; map[r.cat]=map[r.cat].concat(r.kw||r.keywords||[]); });
  return Object.keys(map).map(cat=>({cat, kw:map[cat]}));
}

// Memory format v2: { key: { "เธซเธกเธงเธ” A": count, "เธซเธกเธงเธ” B": count } }
// (v1 was { key: "เธซเธกเธงเธ”" } โ€” auto-converted on read)
function learnedMap(){ try{ return JSON.parse(localStorage.getItem('fs9_catMemory')||'{}'); }catch{ return {}; } }
function saveLearned(m){ try{ localStorage.setItem('fs9_catMemory',JSON.stringify(m)); }catch{} }

// get the winning (most frequent) category for a key, with counts
function bestCatFor(key){
  const mem=learnedMap(); const v=mem[key];
  if(!v) return null;
  if(typeof v==='string') return { cat:v, count:1, total:1 }; // v1 format
  let bestCat=null, bestN=0, total=0;
  for(const c in v){ total+=v[c]; if(v[c]>bestN){ bestN=v[c]; bestCat=c; } }
  return bestCat? { cat:bestCat, count:bestN, total } : null;
}

// โ”€โ”€ Keyword dataset management โ”€โ”€
function kwCount(){ return getCatRules().reduce((s,r)=>s+r.kw.length,0); }
function showKwInfo(){
  const rules=getCatRules();
  const total=kwCount();
  const custom=customRules().length;
  toast(`${rules.length} เธซเธกเธงเธ”, ${total} keyword${custom?` (custom ${custom})`:''}`,'ok');
}
function exportKeywords(){
  // export current effective dataset in the dataset file format
  const out={ _meta:{name:'Finance Slip keyword dataset (exported)', exported:new Date().toISOString()},
    categories: getCatRules().map(r=>({cat:r.cat, keywords:r.kw})) };
  downloadBlob(new Blob([JSON.stringify(out,null,2)],{type:'application/json'}), `keyword-dataset-${dateStamp()}.json`);
  toast('เธชเนเธเธญเธญเธ keyword เนเธฅเนเธง โ“','ok');
}
function resetKeywords(){
  if(!confirm('เธเธทเธเธเนเธฒ keyword เน€เธเนเธเธเธธเธ”เน€เธฃเธดเนเธกเธ•เนเธ? (เธฅเธ keyword เธ—เธตเนเธเธณเน€เธเนเธฒเน€เธญเธ)')) return;
  localStorage.removeItem('fs9_customKw');
  toast('เธเธทเธเธเนเธฒ keyword เน€เธฃเธดเนเธกเธ•เนเธเนเธฅเนเธง โ“','ok');
}
document.getElementById('kwFile').onchange=e=>{
  const file=e.target.files[0]; if(!file) return;
  const r=new FileReader();
  r.onload=ev=>{
    try{
      const data=JSON.parse(ev.target.result);
      // accept either {categories:[{cat,keywords}]} or [{cat,kw}]
      let cats = Array.isArray(data) ? data : data.categories;
      if(!Array.isArray(cats)) throw new Error('เธฃเธนเธเนเธเธเนเธเธฅเนเนเธกเนเธ–เธนเธเธ•เนเธญเธ');
      const parsed = cats.map(c=>({ cat:c.cat, kw:(c.kw||c.keywords||[]).filter(Boolean) })).filter(c=>c.cat && c.kw.length);
      if(!parsed.length) throw new Error('เนเธกเนเธเธ keyword เนเธเนเธเธฅเน');
      localStorage.setItem('fs9_customKw', JSON.stringify(parsed));
      toast(`เธเธณเน€เธเนเธฒ keyword: ${parsed.length} เธซเธกเธงเธ”, ${parsed.reduce((s,c)=>s+c.kw.length,0)} เธเธณ โ“`,'ok');
    }catch(err){ toast('เธเธณเน€เธเนเธฒเนเธกเนเธชเธณเน€เธฃเนเธ: '+(err.message||err),'err'); }
    e.target.value='';
  };
  r.readAsText(file);
};

// push local category memory to the Sheet (Categories tab)
async function pushCats(){
  const url=getSheetUrl(); if(!url) return false;
  const mem=learnedMap();
  if(!Object.keys(mem).length) return false;
  // send winning category per key (Sheet stores simple keyโ’category)
  const cats={};
  for(const k in mem){ const b=bestCatFor(k); if(b) cats[k]=b.cat; }
  try{
    await fetch(url,{ method:'POST', headers:{'Content-Type':'text/plain;charset=utf-8'},
      body: JSON.stringify({ action:'cats', cats }) });
    return true;
  }catch{
    try{ await fetch(url,{ method:'POST', mode:'no-cors', headers:{'Content-Type':'text/plain;charset=utf-8'}, body: JSON.stringify({action:'cats', cats}) }); return true; }catch{ return false; }
  }
}

// pull category memory from the Sheet and merge into local (fills gaps with count=1)
async function pullCats(silent){
  const url=getSheetUrl(); if(!url){ if(!silent) toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); return false; }
  try{
    const res=await fetch(url,{method:'GET'});
    const info=JSON.parse(await res.text());
    if(info && info.ok && info.cats){
      const local=learnedMap();
      let added=0;
      for(const k in info.cats){
        const cloudCat=info.cats[k];
        if(!cloudCat) continue;
        let v=local[k];
        if(typeof v==='string') v={ [v]:1 };
        if(!v){ v={}; added++; }
        if(!v[cloudCat]) v[cloudCat]=1;   // adopt cloud category if missing
        local[k]=v;
      }
      saveLearned(local);
      if(!silent) toast(`เธ”เธถเธเธเธงเธฒเธกเธเธณเธซเธกเธงเธ”เธเธฒเธเธเธฅเธฒเธงเธ”เน +${added} โ“`,'ok');
      return true;
    }
  }catch(err){ if(!silent) toast('เธ”เธถเธเธเธงเธฒเธกเธเธณเนเธกเนเธชเธณเน€เธฃเนเธ','err'); }
  return false;
}
function payeeKey(s){ return (s||'').toUpperCase().replace(/[^A-Z0-9เธ-เน]/g,'').slice(0,40); }
// โ”€โ”€ เธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธ (เธชเธณเธซเธฃเธฑเธเธฃเธฐเธเธธเธ—เธดเธจเนเธญเธเน€เธเนเธฒ/เธญเธญเธ) โ”€โ”€
function norm(s){ return (s||'').toUpperCase().replace(/[^A-Z0-9เธ-เน]/g,''); }
function getMyAccounts(){ try{ return JSON.parse(localStorage.getItem('fs9_myAccounts')||'[]'); }catch{ return []; } }
function setMyAccounts(arr){ try{ localStorage.setItem('fs9_myAccounts',JSON.stringify(arr)); }catch{} }
function setMyAccountsPrompt(){
  const cur=getMyAccounts().join(', ');
  const v=prompt('เนเธชเนเธเธทเนเธญ/เน€เธฅเธเธเธฑเธเธเธตเธเธญเธเธเธธเธ“ (เธเธฑเนเธเธ”เนเธงเธขเธเธธเธฅเธ เธฒเธ)\nเน€เธเนเธ: เธเธฒเธขเธชเธกเธเธฒเธข, 4347, เธเธฃเนเธญเธกเน€เธเธขเนเธเธญเธเธเธฑเธ\n\nเธฃเธฐเธเธเนเธเนเธฃเธฐเธเธธเธงเนเธฒเธชเธฅเธดเธเน€เธเนเธเน€เธเธดเธเน€เธเนเธฒเธซเธฃเธทเธญเธญเธญเธ', cur);
  if(v===null) return;
  const arr=v.split(',').map(s=>s.trim()).filter(s=>s.length>=2);
  setMyAccounts(arr);
  toast(arr.length?`เธเธฑเธเธ—เธถเธเธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธ ${arr.length} เธฃเธฒเธขเธเธฒเธฃ โ“`:'เธฅเนเธฒเธเธเธฑเธเธเธตเธ•เธฑเธงเน€เธญเธเนเธฅเนเธง','ok');
}

// pull transaction rows from the Sheet and merge into local (by id, no duplicates)
async function pullData(silent){
  const url=getSheetUrl(); if(!url){ if(!silent) toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); return false; }
  try{
    const res=await fetch(url,{method:'GET'});
    const info=JSON.parse(await res.text());
    if(info && info.ok && Array.isArray(info.data)){
      const existing=new Set(entries.map(e=>String(e.id)));
      let added=0;
      info.data.forEach(r=>{
        if(!r.id || existing.has(String(r.id))) return;
        entries.push({
          id: Number(r.id)||Date.now()+Math.random(),
          type: (r.type==='เธฃเธฒเธขเธฃเธฑเธ'||r.type==='income') ? 'income' : 'expense',
          desc: r.desc||'', amount: parseFloat(r.amount)||0,
          date: normDate(r.date), currency: r.currency||'เธฟ',
          category: r.category||'', method: r.method||'', ref: r.ref!=null?String(r.ref):'',
          note: r.note||'', synced:true
        });
        added++;
      });
      entries.sort((a,b)=>b.id-a.id);
      save();
      render();
      if(!silent) toast(added? `เธ”เธถเธเธเธฒเธ Sheet +${added} เธฃเธฒเธขเธเธฒเธฃ โ“` : 'เธเนเธญเธกเธนเธฅเธ•เธฃเธเธเธฑเธเนเธฅเนเธง โ“','ok');
      return true;
    }
  }catch(err){ if(!silent) toast('เธ”เธถเธเธเนเธญเธกเธนเธฅเนเธกเนเธชเธณเน€เธฃเนเธ: '+(err.message||err),'err'); }
  return false;
}
// normalize date from Sheet (may come as ISO string or Date) to YYYY-MM-DD
function normDate(v){
  if(!v) return new Date().toISOString().split('T')[0];
  const s=String(v);
  let m=s.match(/(\d{4})-(\d{2})-(\d{2})/); if(m) return `${m[1]}-${m[2]}-${m[3]}`;
  const d=new Date(s); if(!isNaN(d)) return d.toISOString().split('T')[0];
  return new Date().toISOString().split('T')[0];
}

// returns {cat, source} or null
function classifyCategory(found){
  const mem = learnedMap();
  // Level 2a: exact payee key match โ€” pick most-used category (frequency weighted)
  const pk = payeeKey(found.payee) || payeeKey(found.receiver) || payeeKey(found.sender);
  if(pk){ const b=bestCatFor(pk); if(b) return { cat:b.cat, source:'learned-payee', count:b.count, total:b.total }; }

  const hay = ((found.fullText||'')+' '+(found.desc||'')+' '+(found.note||'')+' '+(found.payee||'')).toUpperCase();
  if(!hay.trim()) return null;

  // Level 2b: any learned key contained in text โ€” most-used wins
  for(const key in mem){
    if(key && hay.includes(key)){ const b=bestCatFor(key); if(b) return { cat:b.cat, source:'learned', count:b.count, total:b.total }; }
  }

  // Level 1: keyword rules
  for(const rule of getCatRules()){
    for(const k of rule.kw){
      if(hay.includes(k.toUpperCase())) return { cat:rule.cat, source:'rule' };
    }
  }
  return null;
}

// remember the user's choice โ€” increment count for this payeeโ’category pair
function rememberCategory(entry){
  if(!entry || !entry.category) return;
  const key = payeeKey(entry.note) || payeeKey(entry.desc);
  if(!key || key.length<3) return;
  const mem=learnedMap();
  let v=mem[key];
  if(typeof v==='string') v={ [v]:1 };   // upgrade v1 โ’ v2
  if(!v || typeof v!=='object') v={};
  v[entry.category]=(v[entry.category]||0)+1;
  mem[key]=v;
  saveLearned(mem);
}

function applyParsed(d){
  if(d.type) setType(d.type);
  if(d.amount!=null) setField('fAmt', d.amount);
  if(d.date) setField('fDate', d.date);
  if(d.desc) setField('fDesc', d.desc);
  if(d.ref && !document.getElementById('fRef').value) setField('fRef', d.ref);
  if(d.note) setField('fNote', d.note);   // now meaningful: "เนเธญเธเนเธซเน: ..." / "เธฃเธฑเธเธเธฒเธ: ..."
  // auto-categorize (prefer payee key learned memory, then keyword)
  const c=classifyCategory(d);
  if(c){
    const sel=document.getElementById('fCat');
    const opt=Array.from(sel.options).find(o=>o.value===c.cat);
    if(opt){ sel.value=c.cat; sel.classList.add('ocr-f'); sel.addEventListener('change',()=>sel.classList.remove('ocr-f'),{once:true}); }
  }
}

function setField(id,val){ const el=document.getElementById(id); el.value=val; el.classList.add('ocr-f'); el.addEventListener('input',()=>el.classList.remove('ocr-f'),{once:true}); }
function clearOcrHighlight(){ ['fAmt','fDate','fDesc','fRef'].forEach(id=>document.getElementById(id).classList.remove('ocr-f')); }

function setType(t){
  curType=t;
  document.getElementById('pillInc').className='type-pill'+(t==='income'?' a-inc':'');
  document.getElementById('pillExp').className='type-pill'+(t==='expense'?' a-exp':'');
  const row=document.getElementById('amtRow'), sym=document.getElementById('amtSym'), inp=document.getElementById('fAmt');
  row.style.borderBottomColor=t==='income'?'var(--green)':'var(--red)';
  sym.style.color=t==='income'?'var(--green)':'var(--red)';
  inp.style.color=t==='income'?'var(--green)':'var(--red)';
}
function setFilter(f,el){ curFilter=f; document.querySelectorAll('.fbtn').forEach(b=>b.classList.remove('on')); el.classList.add('on'); render(); }

// โ”€โ”€ Save (synchronous & reliable) โ”€โ”€
document.getElementById('btnPost').onclick=postEntry;
function postEntry(){
  const desc=document.getElementById('fDesc').value.trim();
  const amt=parseFloat(document.getElementById('fAmt').value);
  const date=document.getElementById('fDate').value;
  if(!desc){ toast('เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธฃเธฒเธขเธเธฒเธฃ','err'); return; }
  if(!amt||amt<=0){ toast('เธเธฃเธธเธ“เธฒเธเธฃเธญเธเธเธณเธเธงเธเน€เธเธดเธ','err'); return; }
  if(!date){ toast('เธเธฃเธธเธ“เธฒเน€เธฅเธทเธญเธเธงเธฑเธเธ—เธตเน','err'); return; }

  const entry={ id:Date.now(), type:curType, desc, amount:amt, date,
    time:new Date().toTimeString().slice(0,8),
    currency:document.getElementById('fCur').value, category:document.getElementById('fCat').value,
    method:document.getElementById('fMethod').value, ref:document.getElementById('fRef').value.trim(),
    note:document.getElementById('fNote').value.trim(), thumb:slipThumb||null };

  entries.unshift(entry);
  rememberCategory(entry);
  if(getSheetUrl() && entry.category) pushCats();
  if(!save()){ entries.shift(); toast('เธเธทเนเธเธ—เธตเนเธเธฑเธ”เน€เธเนเธเน€เธ•เนเธก','err'); return; }
  toast('เธเธฑเธเธ—เธถเธเนเธฅเนเธง โ“','ok'); afterSave();

  // โ”€โ”€ auto-send to Sheet โ”€โ”€
  if(getSheetUrl() && autoSendOn()){
    sendToSheet([sheetRow(entry)]).then(ok=>{
      if(ok){ entry.synced=true; save(); render(); toast('เธเธฑเธเธ—เธถเธ + เธชเนเธเนเธ Sheet เนเธฅเนเธง โ“','ok'); }
    });
  }
}
function autoSendOn(){ return localStorage.getItem('fs9_autoSend')==='1'; }
function save(){ try{ localStorage.setItem('fs9',JSON.stringify(entries)); return true; }catch{ return false; } }
function afterSave(){
  render(); clearForm();
  // scroll to top so the just-added entry (newest) is visible
  window.scrollTo({top:0, behavior:'smooth'});
}

function clearForm(){
  ['fAmt','fDesc','fRef','fNote'].forEach(id=>{const e=document.getElementById(id);e.value='';e.classList.remove('ocr-f');});
  document.getElementById('fDate').value=new Date().toISOString().split('T')[0];
  document.getElementById('fCat').value=''; document.getElementById('fCur').value='เธฟ';
  document.getElementById('amtSym').textContent='เธฟ';
  resetImage(); setType('expense');
}
function deleteEntry(id, skipConfirm=false){
  const e=entries.find(x=>x.id===id);
  if(!e) return;
  if(!skipConfirm && !confirm('เธฅเธเธฃเธฒเธขเธเธฒเธฃเธเธตเน?\n'+(e.desc||'')+' '+(e.currency||'เธฟ')+e.amount)) return;
  entries=entries.filter(x=>x.id!==id); save(); render();
  if(getSheetUrl()){
    fetch(getSheetUrl(),{ method:'POST', headers:{'Content-Type':'text/plain;charset=utf-8'},
      body: JSON.stringify({ action:'deleteRow', id }) })
      .then(r=>r.text()).then(txt=>{
        let d; try{ d=JSON.parse(txt); }catch{ d=null; }
        if(d && d.ok) toast(d.removed>0?'เธฅเธเธ—เธฑเนเธเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเธฐ Sheet โ“':'เธฅเธเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเนเธง (เนเธกเนเธเธเนเธ Sheet)','ok');
        else toast('เธฅเธเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเนเธง','ok');
      })
      .catch(()=>{
        fetch(getSheetUrl(),{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify({action:'deleteRow',id})});
        toast('เธฅเธเนเธฅเนเธง (เธชเนเธเธเธณเธชเธฑเนเธเธฅเธเนเธ Sheet)','ok');
      });
  } else {
    toast('เธฅเธเธฃเธฒเธขเธเธฒเธฃเนเธฅเนเธง โ“','ok');
  }
}

// โ•โ•โ•โ•โ•โ•โ•โ• iOS-style entry detail popup โ•โ•โ•โ•โ•โ•โ•โ•
let _detailEntryId=null;

let _popupPage=0;
function setPopupPage(n){
  _popupPage=n;
  document.getElementById('iosPages').style.transform=`translateX(${-n*100}%)`;
  document.querySelectorAll('#iosDots .ios-dot').forEach((d,i)=>d.classList.toggle('on',i===n));
}

function openEntryDetail(id){
  const e=entries.find(x=>x.id===id); if(!e) return;
  _detailEntryId=id;
  const sym=e.currency||'เธฟ';
  const amtEl=document.getElementById('iosAmt');
  amtEl.className='ios-amt '+(e.type==='income'?'income':'expense');
  amtEl.textContent=(e.type==='income'?'+':'โ’')+sym+e.amount.toLocaleString('th-TH',{minimumFractionDigits:2});
  document.getElementById('iosDesc').textContent=e.desc||'(เนเธกเนเธกเธตเธฃเธฒเธขเธเธฒเธฃ)';
  const rows=[
    ['เธเธฃเธฐเน€เธ เธ—', e.type==='income'?'เธฃเธฒเธขเธฃเธฑเธ':'เธฃเธฒเธขเธเนเธฒเธข'],
    ['เธงเธฑเธเธ—เธตเน', e.date||'-'],
    ['เธซเธกเธงเธ”เธซเธกเธนเน', e.category||'-'],
    ['เธเนเธญเธเธ—เธฒเธ', e.method||'-'],
    ['เน€เธฅเธเธญเนเธฒเธเธญเธดเธ', e.ref||'-'],
    ['เธซเธกเธฒเธขเน€เธซเธ•เธธ', e.note||'-'],
  ];
  document.getElementById('iosRows').innerHTML=rows.filter(r=>r[1]!=='-'||r[0]==='เธงเธฑเธเธ—เธตเน')
    .map(([k,v])=>`<div class="ios-row"><span class="ir-k">${esc(k)}</span><span class="ir-v">${esc(v)}</span></div>`).join('');

  // page 2: slip image
  const slipImg=document.getElementById('iosSlipImg');
  const noSlip=document.getElementById('iosNoSlip');
  if(e.thumb){ slipImg.src=e.thumb; slipImg.style.display='block'; noSlip.style.display='none'; }
  else { slipImg.src=''; slipImg.style.display='none'; noSlip.style.display='none'; }

  // dots + hint only when slip exists
  const hasDots=!!e.thumb;
  document.getElementById('iosDots').style.display=hasDots?'flex':'none';
  document.getElementById('iosSlipHint').style.display=hasDots?'block':'none';

  const syncEl=document.getElementById('iosSync');
  if(getSheetUrl()) syncEl.innerHTML=e.synced?'<span style="color:var(--green)">โ เธชเนเธ Sheet เนเธฅเนเธง</span>':'<span style="color:var(--muted)">โ‘ เธขเธฑเธเนเธกเนเธชเนเธ Sheet</span>';
  else syncEl.innerHTML='';
  document.getElementById('iosBtnEdit').onclick=()=>{ closeEntryDetail(); openMainEntryEdit(id); };
  document.getElementById('iosBtnDel').onclick=()=>{ closeEntryDetail(); deleteEntry(id,true); };
  setPopupPage(0);
  document.getElementById('iosOverlay').classList.add('show');
  document.getElementById('iosPopup').classList.add('show');
}
function closeEntryDetail(){
  document.getElementById('iosOverlay').classList.remove('show');
  document.getElementById('iosPopup').classList.remove('show');
  _detailEntryId=null;
  // reset page after popup finishes sliding out (350ms) so no snap-back flicker
  setTimeout(()=>{ document.getElementById('iosPages').style.transition='none'; setPopupPage(0); },350);
}

// live finger-tracking swipe for detail popup pages
(function(){
  const popup=document.getElementById('iosPopup');
  const pages=document.getElementById('iosPages');
  let sx=0, sy=0, tracking=false, engaged=false, startPct=0;

  function slipAvailable(){ return document.getElementById('iosDots').style.display!=='none'; }

  popup.addEventListener('touchstart',e=>{
    sx=e.touches[0].clientX; sy=e.touches[0].clientY;
    startPct=_popupPage*-100; tracking=true; engaged=false;
  },{passive:true});

  popup.addEventListener('touchmove',e=>{
    if(!tracking) return;
    const dx=e.touches[0].clientX-sx;
    const dy=e.touches[0].clientY-sy;
    if(!engaged){
      if(Math.abs(dy)>Math.abs(dx)+15){ tracking=false; return; } // clearly vertical โ€” cancel
      if(Math.abs(dx)<10) return;                                  // wait for horizontal intent
      if(!slipAvailable()){ tracking=false; return; }
      engaged=true;
      pages.style.transition='none';
    }
    const w=popup.offsetWidth||window.innerWidth;
    let next=startPct+(dx/w)*100;
    if(next>0)      next=next*0.2;              // rubber-band at start
    if(next<-100)   next=-100+(next+100)*0.2;   // rubber-band at end
    pages.style.transform=`translateX(${next}%)`;
  },{passive:true});

  function snap(e){
    if(!tracking) return; tracking=false;
    if(!engaged) return;
    pages.style.transition='transform .35s cubic-bezier(.32,1,.23,1)';
    const dx=((e.changedTouches&&e.changedTouches.length)?e.changedTouches[0].clientX:sx)-sx;
    if(dx<-50 && _popupPage===0) setPopupPage(1);
    else if(dx>50 && _popupPage===1) setPopupPage(0);
    else setPopupPage(_popupPage);
  }
  popup.addEventListener('touchend',snap,{passive:true});
  popup.addEventListener('touchcancel',snap,{passive:true});
})();

// edit an existing entry from main list (reuse editModal fields)
let _mainEditId=null;
function openMainEntryEdit(id){
  const e=entries.find(x=>x.id===id); if(!e) return;
  _mainEditId=id;
  document.getElementById('eType').value=e.type||'expense';
  document.getElementById('eAmt').value=e.amount||'';
  document.getElementById('eDate').value=e.date||'';
  document.getElementById('eDesc').value=e.desc||'';
  document.getElementById('eCat').value=e.category||'';
  document.getElementById('eRef').value=e.ref||'';
  document.getElementById('eNote').value=e.note||'';
  // temporarily override save button
  const btn=document.querySelector('#editModal .btn-post');
  btn._origOnclick=btn.onclick;
  btn.onclick=saveMainEntryEdit;
  document.getElementById('editModal').classList.add('show');
}
function saveMainEntryEdit(){
  if(!_mainEditId) return;
  const e=entries.find(x=>x.id===_mainEditId); if(!e) return;
  e.type=document.getElementById('eType').value;
  e.amount=parseFloat(document.getElementById('eAmt').value)||0;
  e.date=document.getElementById('eDate').value;
  e.desc=document.getElementById('eDesc').value;
  e.category=document.getElementById('eCat').value;
  e.ref=document.getElementById('eRef').value;
  e.note=document.getElementById('eNote').value;
  e.synced=false;  // mark for re-sync
  save(); render();
  // restore original save button
  const btn=document.querySelector('#editModal .btn-post');
  btn.onclick=btn._origOnclick||null;
  document.getElementById('editModal').classList.remove('show');
  _mainEditId=null;
  toast('เนเธเนเนเธเธฃเธฒเธขเธเธฒเธฃเนเธฅเนเธง โ“','ok');
}

// โ•โ•โ•โ•โ•โ•โ•โ• Entry swipe in main list (เธเธฑเธ”เธเนเธฒเธข=เธฅเธ) โ•โ•โ•โ•โ•โ•โ•โ•
function attachEntrySwipe(entryEl, id){
  let startX=0, curX=0, dragging=false, moved=false;
  const bg=entryEl.parentElement?.querySelector('.entry-sw-bg');
  const TH=90;
  const down=x=>{ startX=x; dragging=true; moved=false; entryEl.style.transition='none'; };
  const move=x=>{ if(!dragging)return; curX=x-startX; if(Math.abs(curX)>8) moved=true;
    if(curX<0){ entryEl.style.transform=`translateX(${curX}px)`; if(bg) bg.style.opacity=Math.min(1,Math.abs(curX)/TH); }
    else{ entryEl.style.transform=''; if(bg) bg.style.opacity=0; } };
  const up=()=>{ if(!dragging)return; dragging=false;
    entryEl.style.transition='transform .2s ease, opacity .2s ease';
    if(curX<-TH){ entryEl.style.transform='translateX(-110%)'; entryEl.style.opacity='0';
      setTimeout(()=>{ deleteEntry(id,true); },200); }
    else{ entryEl.style.transform=''; if(bg) bg.style.opacity=0; } curX=0; };
  entryEl.addEventListener('touchstart',e=>down(e.touches[0].clientX),{passive:true});
  entryEl.addEventListener('touchmove',e=>{ if(dragging) move(e.touches[0].clientX); },{passive:true});
  entryEl.addEventListener('touchend',up);
  entryEl.addEventListener('mousedown',e=>down(e.clientX));
  window.addEventListener('mousemove',e=>{ if(dragging) move(e.clientX); });
  window.addEventListener('mouseup',()=>{ if(dragging) up(); });
}

function monthKey(dateStr){ const d=new Date(dateStr+'T00:00:00'); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; }
function monthLabel(key){ const [y,m]=key.split('-').map(Number); return new Date(y,m-1,1).toLocaleDateString('th-TH',{month:'long',year:'numeric'}); }

function render(){
  const fmtCur=(n,sym)=> (sym||'เธฟ')+n.toLocaleString('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2});

  // filter by type
  const all = curFilter==='all' ? entries : entries.filter(e=>e.type===curFilter);

  // grand totals (all entries shown)
  const gInc=all.filter(e=>e.type==='income').reduce((s,e)=>s+e.amount,0);
  const gExp=all.filter(e=>e.type==='expense').reduce((s,e)=>s+e.amount,0);
  const gBal=gInc-gExp; const gsym=entries[0]?.currency||'เธฟ';
  document.getElementById('sInc').textContent=fmtCur(gInc,gsym);
  document.getElementById('sExp').textContent=fmtCur(gExp,gsym);
  const bel=document.getElementById('sBal'); bel.textContent=(gBal<0?'-':'')+fmtCur(Math.abs(gBal),gsym);
  bel.style.color=gBal<0?'var(--red)':gBal>0?'var(--green)':'var(--ink)';

  const list=document.getElementById('eList');
  if(!all.length){ list.innerHTML='<div class="empty">เธขเธฑเธเนเธกเนเธกเธตเธฃเธฒเธขเธเธฒเธฃ</div>'; document.getElementById('monthSticky').textContent=''; return; }

  // group by month, then by date โ€” newest first
  const byMonth={};
  all.forEach(e=>{ const k=monthKey(e.date); (byMonth[k]=byMonth[k]||[]).push(e); });
  const months=Object.keys(byMonth).sort((a,b)=>b.localeCompare(a));

  let html='';
  months.forEach(mk=>{
    const items=byMonth[mk];
    const inc=items.filter(e=>e.type==='income').reduce((s,e)=>s+e.amount,0);
    const exp=items.filter(e=>e.type==='expense').reduce((s,e)=>s+e.amount,0);
    const bal=inc-exp; const sym=items[0]?.currency||'เธฟ';
    const balCol=bal<0?'var(--red)':'var(--green)';
    // month header
    html+=`<div class="month-head" data-month="${mk}" data-label="${esc(monthLabel(mk))}">
      <span class="mh-title">${esc(monthLabel(mk))}</span>
      <span class="mh-bal" style="color:${balCol}">${bal<0?'-':''}${sym}${Math.abs(bal).toLocaleString('th-TH',{minimumFractionDigits:2})}</span>
    </div>`;
    // by date within month
    const byD={}; items.forEach(e=>{(byD[e.date]=byD[e.date]||[]).push(e);});
    Object.keys(byD).sort((a,b)=>b.localeCompare(a)).forEach(date=>{
      const d=new Date(date+'T00:00:00');
      html+=`<div class="dg-label">${d.toLocaleDateString('th-TH',{weekday:'short',day:'numeric',month:'short'})}</div>`;
      byD[date].forEach(e=>{
        const sign=e.type==='income'?'+':'โ’'; const s=e.currency||'เธฟ';
        html+=`<div class="entry-sw-wrap">
          <div class="entry-sw-bg"><span class="bg-lbl">๐—‘ เธฅเธ</span></div>
          <div class="entry ${e.type}" data-eid="${e.id}" onclick="openEntryDetail(${e.id})">
            <div class="entry-info">
              <div class="entry-desc">${esc(e.desc)}</div>
              <div class="entry-tags">${e.category?`<span class="etag">${esc(e.category)}</span>`:''}<span class="etag">${esc(e.method||'')}</span>${e.ref?`<span class="etag">#${esc(e.ref)}</span>`:''}</div>
              ${e.note?`<div class="entry-note">${esc(e.note)}</div>`:''}
            </div>
            <div class="entry-right">
              <div class="eamount">${sign}${s}${e.amount.toLocaleString('th-TH',{minimumFractionDigits:2})}</div>
              ${ getSheetUrl() ? (e.synced?'<span class="entry-synced">โ เธชเนเธเนเธฅเนเธง</span>':`<span class="entry-unsynced" onclick="event.stopPropagation();syncOne(${e.id})">โ‘ เธชเนเธเนเธ Sheet</span>`) : '' }
            </div>
          </div>
        </div>`;
      });
    });
  });
  list.innerHTML=html;
  // set initial sticky label to the first (newest) month
  const sticky=document.getElementById('monthSticky');
  if(months.length){ sticky.textContent=monthLabel(months[0]); }
  updateStickyMonth();
  // attach swipe-to-delete on each entry
  list.querySelectorAll('.entry[data-eid]').forEach(el=>{
    attachEntrySwipe(el, Number(el.dataset.eid));
  });
}

// update sticky month label based on which month-head is at the top of the viewport
function updateStickyMonth(){
  const sticky=document.getElementById('monthSticky');
  const heads=document.querySelectorAll('.month-head');
  if(!heads.length){ return; }
  const stickyBottom = sticky.getBoundingClientRect().bottom;
  let current=heads[0].getAttribute('data-label');
  heads.forEach(h=>{
    const top=h.getBoundingClientRect().top;
    if(top <= stickyBottom+4){ current=h.getAttribute('data-label'); }
  });
  sticky.textContent=current;
}
window.addEventListener('scroll', ()=>{ requestAnimationFrame(updateStickyMonth); }, {passive:true});

function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
let _tt; function toast(msg,type=''){ const t=document.getElementById('toastEl'); t.textContent=msg; t.className='toast show'+(type?' '+type:''); clearTimeout(_tt); _tt=setTimeout(()=>t.classList.remove('show'),2600); }

// โ•โ•โ•โ•โ•โ•โ•โ• Google Sheet sync โ•โ•โ•โ•โ•โ•โ•โ•
const GS_CODE = `function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000);
  try {
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var data = JSON.parse(e.postData.contents);

    // โ”€โ”€ category memory sync โ”€โ”€
    if (data.action === 'cats') {
      var cs = ss.getSheetByName('Categories') || ss.insertSheet('Categories');
      if (cs.getLastRow() === 0) cs.appendRow(['key','category']);
      var existing = {};
      var vals = cs.getDataRange().getValues();
      for (var i = 1; i < vals.length; i++) existing[vals[i][0]] = i + 1;
      var map = data.cats || {};
      Object.keys(map).forEach(function(k) {
        if (existing[k]) cs.getRange(existing[k], 2).setValue(map[k]);
        else cs.appendRow([k, map[k]]);
      });
      return ContentService.createTextOutput(JSON.stringify({ok:true, cats:Math.max(0, cs.getLastRow()-1)}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // โ”€โ”€ delete one transaction by ID โ”€โ”€
    if (data.action === 'deleteRow') {
      var sh = ss.getSheets()[0];
      var v = sh.getDataRange().getValues();
      var removed = 0;
      for (var r = v.length - 1; r >= 1; r--) {
        if (String(v[r][0]) === String(data.id)) { sh.deleteRow(r + 1); removed++; }
      }
      return ContentService.createTextOutput(JSON.stringify({ok:true, removed:removed}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // โ”€โ”€ clear ALL transactions (keep header) โ”€โ”€
    if (data.action === 'clearAll') {
      var sh2 = ss.getSheets()[0];
      var last = sh2.getLastRow();
      if (last > 1) sh2.deleteRows(2, last - 1);
      return ContentService.createTextOutput(JSON.stringify({ok:true, cleared:Math.max(0,last-1)}))
        .setMimeType(ContentService.MimeType.JSON);
    }

    // โ”€โ”€ clear category memory โ”€โ”€
    if (data.action === 'clearCats') {
      var cc = ss.getSheetByName('Categories');
      if (cc && cc.getLastRow() > 1) cc.deleteRows(2, cc.getLastRow() - 1);
      return ContentService.createTextOutput(JSON.stringify({ok:true})).setMimeType(ContentService.MimeType.JSON);
    }

    // โ”€โ”€ transaction rows โ”€โ”€
    var sheet = ss.getSheets()[0];
    if (sheet.getLastRow() === 0) {
      sheet.appendRow(['ID','เธงเธฑเธเธ—เธตเน','เธเธฃเธฐเน€เธ เธ—','เธฃเธฒเธขเธเธฒเธฃ','เธเธณเธเธงเธ','เธชเธเธธเธฅเน€เธเธดเธ','เธซเธกเธงเธ”เธซเธกเธนเน','เธเนเธญเธเธ—เธฒเธ','เน€เธฅเธเธญเนเธฒเธเธญเธดเธ','เธซเธกเธฒเธขเน€เธซเธ•เธธ']);
    }
    var rows = data.rows || [data];
    rows.forEach(function(r) {
      sheet.appendRow([r.id, r.date, r.type, r.desc, r.amount, r.currency, r.category, r.method, r.ref, r.note]);
    });
    return ContentService.createTextOutput(JSON.stringify({ok:true, added:rows.length, total:sheet.getLastRow()-1}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error:String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  } finally {
    lock.releaseLock();
  }
}

// GET = เธ—เธ”เธชเธญเธ deploy + เธ”เธถเธเธเธงเธฒเธกเธเธณเธซเธกเธงเธ” + เธ”เธถเธเธฃเธฒเธขเธเธฒเธฃเธ—เธฑเนเธเธซเธกเธ” (?data=1)
function doGet(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheets()[0];
  var out = { ok: true, sheetName: sheet.getName(), rows: Math.max(0, sheet.getLastRow()-1) };
  var cs = ss.getSheetByName('Categories');
  var cats = {};
  if (cs && cs.getLastRow() > 1) {
    var vals = cs.getDataRange().getValues();
    for (var i = 1; i < vals.length; i++) if (vals[i][0]) cats[vals[i][0]] = vals[i][1];
  }
  out.cats = cats;
  // include all transaction rows so the app can pull them back
  var data = [];
  if (sheet.getLastRow() > 1) {
    var dv = sheet.getDataRange().getValues();
    for (var r = 1; r < dv.length; r++) {
      var row = dv[r];
      if (!row[0]) continue;
      data.push({
        id: row[0], date: row[1], type: row[2], desc: row[3], amount: row[4],
        currency: row[5], category: row[6], method: row[7], ref: row[8], note: row[9]
      });
    }
  }
  out.data = data;
  return ContentService.createTextOutput(JSON.stringify(out))
    .setMimeType(ContentService.MimeType.JSON);
}`;

function getSheetUrl(){ return localStorage.getItem('fs9_sheetUrl') || ''; }
function openSheetSettings(){
  document.getElementById('sheetUrl').value = getSheetUrl();
  document.getElementById('autoSendChk').checked = autoSendOn();
  document.getElementById('gsCode').textContent = GS_CODE;
  document.getElementById('sheetModal').classList.add('show');
}
function closeSheetSettings(){ document.getElementById('sheetModal').classList.remove('show'); }
function saveSheetUrl(){
  const url=document.getElementById('sheetUrl').value.trim();
  if(url && !/^https:\/\/script\.google\.com\/macros\/s\//.test(url)){ toast('URL เนเธกเนเธ–เธนเธเธ•เนเธญเธ','err'); return; }
  localStorage.setItem('fs9_sheetUrl', url);
  localStorage.setItem('fs9_autoSend', document.getElementById('autoSendChk').checked?'1':'0');
  toast(document.getElementById('autoSendChk').checked?'เธเธฑเธเธ—เธถเธ + เน€เธเธดเธ”เธชเนเธเธญเธฑเธ•เนเธเธกเธฑเธ•เธด โ“':'เธเธฑเธเธ—เธถเธ URL เนเธฅเนเธง โ“','ok');
  closeSheetSettings(); render();
}
function copyGsCode(){
  navigator.clipboard?.writeText(GS_CODE).then(()=>toast('เธเธฑเธ”เธฅเธญเธเนเธเนเธ”เนเธฅเนเธง โ“','ok')).catch(()=>toast('เธเธฑเธ”เธฅเธญเธเนเธกเนเนเธ”เน','err'));
}

// Try a real (readable) request first; if CORS blocks it, fall back to no-cors (fire-and-forget)
async function sendToSheet(rows){
  const url=getSheetUrl();
  if(!url){ toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); openSheetSettings(); return false; }
  // attempt 1: readable response
  try{
    const res=await fetch(url,{ method:'POST',
      headers:{'Content-Type':'text/plain;charset=utf-8'},
      body: JSON.stringify({ rows }) });
    const txt=await res.text();
    let data; try{ data=JSON.parse(txt); }catch{ data=null; }
    if(data && data.ok){ return true; }
    if(data && data.ok===false){ toast('Sheet error: '+data.error,'err'); return false; }
    // got a response but not JSON (e.g. Google login page) โ’ not deployed for "Anyone"
    toast('เธ•เธญเธเธเธฅเธฑเธเธเธดเธ”เธเธเธ•เธด โ€” เธ•เธฃเธงเธ Deploy เธงเนเธฒเธ•เธฑเนเธ "Anyone"','err');
    return false;
  }catch(err){
    // attempt 2: no-cors fire-and-forget (can't confirm)
    try{
      await fetch(url,{ method:'POST', mode:'no-cors',
        headers:{'Content-Type':'text/plain;charset=utf-8'},
        body: JSON.stringify({ rows }) });
      toast('เธชเนเธเนเธฅเนเธง (เธขเธทเธเธขเธฑเธเนเธกเนเนเธ”เน โ€” เน€เธเนเธเนเธ Sheet)','ok');
      return true;
    }catch(err2){ toast('เธชเนเธเนเธกเนเธชเธณเน€เธฃเนเธ: '+(err2.message||err2),'err'); return false; }
  }
}

async function syncOne(id){
  const e=entries.find(x=>x.id===id); if(!e) return;
  toast('เธเธณเธฅเธฑเธเธชเนเธเนเธ Sheetโ€ฆ');
  const ok=await sendToSheet([sheetRow(e)]);
  if(ok){ e.synced=true; save(); render(); toast('เธชเนเธเนเธ Sheet เนเธฅเนเธง โ“','ok'); }
}

// โ”€โ”€ Combined sync: push pending rows up + pull rows & category memory down โ”€โ”€
let _syncing=false;
async function syncNow(silent){
  const url=getSheetUrl();
  if(!url){ if(!silent){ toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); openSheetSettings(); } return; }
  if(_syncing) return;
  _syncing=true;
  const btn=document.getElementById('btnSync');
  if(btn){ btn.classList.add('syncing'); btn.textContent='๐” เธเธณเธฅเธฑเธเธเธดเธเธเนโ€ฆ'; }
  try{
    // 1) push rows not yet sent
    const pending=entries.filter(e=>!e.synced);
    if(pending.length){
      const ok=await sendToSheet(pending.map(sheetRow));
      if(ok) pending.forEach(e=>e.synced=true);
    }
    // 2) push category memory
    await pushCats();
    // 3) pull rows + cats back down (merge)
    await pullData(true);
    await pullCats(true);
    save();
    if(!silent) toast('เธเธดเธเธเนเน€เธฃเธตเธขเธเธฃเนเธญเธข โ“','ok');
  }catch(err){
    if(!silent) toast('เธเธดเธเธเนเธกเธตเธเธฑเธเธซเธฒ: '+(err.message||err),'err');
  }finally{
    _syncing=false;
    if(btn){ btn.classList.remove('syncing'); btn.textContent='๐” เธเธดเธเธเน'; }
  }
}

// โ”€โ”€ Auto-sync (periodic refresh) โ”€โ”€
let _autoTimer=null;
function autoSyncOnPref(){ return localStorage.getItem('fs9_autoSync2')==='1'; }
function toggleAutoSync(){
  const on=document.getElementById('autoSyncChk').checked;
  localStorage.setItem('fs9_autoSync2', on?'1':'0');
  startAutoSync();
  toast(on?'เน€เธเธดเธ”เธญเธญเนเธ•เนเธเธดเธเธเน (เธ—เธธเธ 60 เธงเธด) โ“':'เธเธดเธ”เธญเธญเนเธ•เนเธเธดเธเธเน','ok');
}
function startAutoSync(){
  if(_autoTimer){ clearInterval(_autoTimer); _autoTimer=null; }
  if(autoSyncOnPref() && getSheetUrl()){
    _autoTimer=setInterval(()=>syncNow(true), 60000); // เธ—เธธเธ 60 เธงเธดเธเธฒเธ—เธต
  }
}

function sheetRow(e){
  return { id:e.id, date:e.date, type:e.type==='income'?'เธฃเธฒเธขเธฃเธฑเธ':'เธฃเธฒเธขเธเนเธฒเธข', desc:e.desc,
    amount:e.amount, currency:e.currency, category:e.category, method:e.method, ref:e.ref, note:e.note };
}

document.getElementById('btnTestSheet').onclick=async ()=>{
  const url=document.getElementById('sheetUrl').value.trim();
  if(!url){ toast('เนเธชเน URL เธเนเธญเธ','err'); return; }
  localStorage.setItem('fs9_sheetUrl',url);
  const btn=document.getElementById('btnTestSheet'); btn.disabled=true; btn.textContent='เธเธณเธฅเธฑเธเน€เธเนเธโ€ฆ';
  // 1) GET = เธ•เธฃเธงเธเธงเนเธฒ deploy เนเธเนเนเธ”เน + เธญเนเธฒเธเธเธณเธเธงเธเนเธ–เธงเธเธฑเธเธเธธเธเธฑเธ
  try{
    const res=await fetch(url,{method:'GET'});
    const txt=await res.text();
    let info; try{ info=JSON.parse(txt); }catch{ info=null; }
    if(info && info.ok){
      // 2) เธชเนเธเนเธ–เธงเธ—เธ”เธชเธญเธเธเธฃเธดเธ
      await sendToSheet([sheetRow({id:Date.now(),date:new Date().toISOString().split('T')[0],type:'expense',desc:'เธ—เธ”เธชเธญเธเธเธฒเธฃเน€เธเธทเนเธญเธกเธ•เนเธญ',amount:0,currency:'เธฟ',category:'',method:'เธ—เธ”เธชเธญเธ',ref:'',note:'test'})]);
      toast(`เน€เธเธทเนเธญเธกเธ•เนเธญเธชเธณเน€เธฃเนเธ! เธเธตเธ• "${info.sheetName}" เธกเธต ${info.rows} เนเธ–เธง โ€” เธชเนเธเนเธ–เธงเธ—เธ”เธชเธญเธเนเธฅเนเธง โ“`,'ok');
    } else {
      toast('เน€เธเธทเนเธญเธกเธ•เนเธญเนเธกเนเนเธ”เน โ€” URL เธญเธฒเธเธเธดเธ” เธซเธฃเธทเธญเธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธ Deploy เน€เธเนเธ "Anyone"','err');
    }
  }catch(err){
    toast('เน€เธฃเธตเธขเธ URL เนเธกเนเนเธ”เน: '+(err.message||err)+' (เธฅเธญเธเน€เธเธดเธ” URL เนเธเนเธ—เนเธเนเธซเธกเนเธ”เธน)','err');
  }
  btn.disabled=false; btn.textContent='เธ—เธ”เธชเธญเธเธชเนเธ';
};

// โ•โ•โ•โ•โ•โ•โ•โ• Export / Import โ•โ•โ•โ•โ•โ•โ•โ•
function exportJSON(){
  const blob=new Blob([JSON.stringify(entries,null,2)],{type:'application/json'});
  downloadBlob(blob, `finance-slip-backup-${dateStamp()}.json`);
  toast('เธชเธณเธฃเธญเธเธเนเธญเธกเธนเธฅเนเธฅเนเธง โ“','ok');
}
function exportCSV(){
  const head=['เธงเธฑเธเธ—เธตเน','เธเธฃเธฐเน€เธ เธ—','เธฃเธฒเธขเธเธฒเธฃ','เธเธณเธเธงเธ','เธชเธเธธเธฅเน€เธเธดเธ','เธซเธกเธงเธ”เธซเธกเธนเน','เธเนเธญเธเธ—เธฒเธ','เน€เธฅเธเธญเนเธฒเธเธญเธดเธ','เธซเธกเธฒเธขเน€เธซเธ•เธธ'];
  const rows=entries.map(e=>[e.date, e.type==='income'?'เธฃเธฒเธขเธฃเธฑเธ':'เธฃเธฒเธขเธเนเธฒเธข', e.desc, e.amount, e.currency, e.category, e.method, e.ref, e.note]
    .map(v=>`"${String(v??'').replace(/"/g,'""')}"`).join(','));
  const csv='\uFEFF'+[head.join(','),...rows].join('\n'); // BOM for Thai in Excel
  downloadBlob(new Blob([csv],{type:'text/csv'}), `finance-slip-${dateStamp()}.csv`);
  toast('เธชเนเธเธญเธญเธ CSV เนเธฅเนเธง โ“','ok');
}
function downloadBlob(blob,name){
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=name;
  document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href),2000);
}
function dateStamp(){ const d=new Date(); return d.toISOString().split('T')[0]; }

document.getElementById('importFile').onchange=e=>{
  const file=e.target.files[0]; if(!file) return;
  const r=new FileReader();
  r.onload=ev=>{
    try{
      const data=JSON.parse(ev.target.result);
      if(!Array.isArray(data)) throw new Error('เธฃเธนเธเนเธเธเนเธเธฅเนเนเธกเนเธ–เธนเธเธ•เนเธญเธ');
      const existing=new Set(entries.map(x=>x.id));
      const merged=[...entries];
      let added=0;
      data.forEach(d=>{ if(d && d.id && !existing.has(d.id)){ merged.push(d); added++; } });
      merged.sort((a,b)=>b.id-a.id);
      entries=merged; save(); render();
      toast(`เธเธณเน€เธเนเธฒเนเธฅเนเธง เน€เธเธดเนเธก ${added} เธฃเธฒเธขเธเธฒเธฃ โ“`,'ok');
    }catch(err){ toast('เธเธณเน€เธเนเธฒเนเธกเนเธชเธณเน€เธฃเนเธ: '+(err.message||err),'err'); }
    e.target.value='';
  };
  r.readAsText(file);
};

document.getElementById('fAmt').addEventListener('keydown',e=>{if(e.key==='Enter')document.getElementById('fDesc').focus();});
document.getElementById('sheetModal').addEventListener('click',e=>{ if(e.target.id==='sheetModal') closeSheetSettings(); });

// register service worker (PWA offline support)
// โ”€โ”€ เธญเธฑเธเน€เธ”เธ•เนเธญเธ: เธฅเนเธฒเธ cache + เนเธซเธฅเธ”เน€เธงเธญเธฃเนเธเธฑเธเนเธซเธกเนเธเธฒเธ GitHub โ”€โ”€
async function updateApp(){
  const btn=document.getElementById('btnUpdateApp');
  btn.textContent='โณ เธเธณเธฅเธฑเธเธญเธฑเธเน€เธ”เธ•โ€ฆ'; btn.disabled=true;
  try{
    // 1. tell SW to skip waiting and activate new version
    if('serviceWorker' in navigator){
      const reg=await navigator.serviceWorker.getRegistration();
      if(reg){
        // force check for new SW
        await reg.update();
        if(reg.waiting){ reg.waiting.postMessage({type:'SKIP_WAITING'}); }
      }
    }
    // 2. clear all caches so next load fetches fresh files
    if('caches' in window){
      const keys=await caches.keys();
      await Promise.all(keys.map(k=>caches.delete(k)));
    }
    toast('เธฅเนเธฒเธ cache เนเธฅเนเธง โ€” เธเธณเธฅเธฑเธเนเธซเธฅเธ”เน€เธงเธญเธฃเนเธเธฑเธเนเธซเธกเนโ€ฆ','ok');
    // 3. reload after short delay
    setTimeout(()=>{ window.location.reload(true); }, 900);
  }catch(err){
    toast('เธญเธฑเธเน€เธ”เธ•เนเธกเนเธชเธณเน€เธฃเนเธ: '+(err.message||err),'err');
    btn.textContent='๐” เธญเธฑเธเน€เธ”เธ•เนเธญเธ'; btn.disabled=false;
  }
}

if('serviceWorker' in navigator){
  window.addEventListener('load',()=>{
    navigator.serviceWorker.register('sw.js').then(reg=>{
      // listen for controller change (new SW activated) โ’ reload
      navigator.serviceWorker.addEventListener('controllerchange',()=>{
        window.location.reload();
      });
      // check for updates in background every time app opens
      reg.update().catch(()=>{});
    }).catch(()=>{});
  });
}

// โ•โ•โ•โ•โ•โ•โ•โ• Admin mode (client-side gate) โ•โ•โ•โ•โ•โ•โ•โ•
// NOTE: client-side only โ€” เธเธฑเธเธเธเธ—เธฑเนเธงเนเธ เนเธกเนเนเธเนเธเธงเธฒเธกเธเธฅเธญเธ”เธ เธฑเธขเธฃเธฐเธ”เธฑเธ server
function adminHashSet(){ return localStorage.getItem('fs9_adminHash'); }
function hashStr(s){ let h=5381; for(let i=0;i<s.length;i++){ h=((h<<5)+h)+s.charCodeAt(i); h=h&0xffffffff; } return String(h>>>0); }
function isAdmin(){ return sessionStorage.getItem('fs9_admin')==='1'; }

function adminButtonClick(){
  if(isAdmin()){ adminLogout(); return; }
  let hash=adminHashSet();
  if(!hash){
    // first time: set a password
    const p1=prompt('เธ•เธฑเนเธเธฃเธซเธฑเธช Admin (เธเธฃเธฑเนเธเนเธฃเธ):'); if(!p1) return;
    const p2=prompt('เธขเธทเธเธขเธฑเธเธฃเธซเธฑเธชเธญเธตเธเธเธฃเธฑเนเธ:'); if(p1!==p2){ toast('เธฃเธซเธฑเธชเนเธกเนเธ•เธฃเธเธเธฑเธ','err'); return; }
    localStorage.setItem('fs9_adminHash', hashStr(p1));
    sessionStorage.setItem('fs9_admin','1');
    toast('เธ•เธฑเนเธเธฃเธซเธฑเธช + เน€เธเนเธฒเธชเธนเนเนเธซเธกเธ” Admin โ“','ok'); applyAdminUI(); return;
  }
  const p=prompt('เนเธชเนเธฃเธซเธฑเธช Admin:'); if(p==null) return;
  if(hashStr(p)===hash){ sessionStorage.setItem('fs9_admin','1'); toast('เน€เธเนเธฒเธชเธนเนเนเธซเธกเธ” Admin โ“','ok'); applyAdminUI(); }
  else toast('เธฃเธซเธฑเธชเนเธกเนเธ–เธนเธเธ•เนเธญเธ','err');
}
function adminLogout(){ sessionStorage.removeItem('fs9_admin'); toast('เธญเธญเธเธเธฒเธเนเธซเธกเธ” Admin','ok'); applyAdminUI(); }

function applyAdminUI(){
  const on=isAdmin();
  document.getElementById('adminStrip').style.display = on?'flex':'none';
  document.getElementById('adminPanel').style.display = on?'block':'none';
  document.getElementById('adminBtn').textContent = on?'๐”“ เธญเธญเธ':'๐”’ Admin';
  if(on) renderCatList();
}

function renderCatList(){
  const mem=learnedMap(); const keys=Object.keys(mem);
  document.getElementById('catCount').textContent=keys.length;
  const box=document.getElementById('catList');
  if(!keys.length){ box.innerHTML='<span style="font-size:11px;color:var(--muted)">เธขเธฑเธเนเธกเนเธกเธตเธเธงเธฒเธกเธเธณ</span>'; return; }
  box.innerHTML=keys.map(k=>{
    const b=bestCatFor(k);
    const v=mem[k];
    // build a small breakdown like "เธเธญเธเธเธณร—5, เธญเธฒเธซเธฒเธฃร—1"
    let detail='';
    if(v && typeof v==='object'){
      const parts=Object.keys(v).sort((a,c)=>v[c]-v[a]).map(c=>`${esc(c)}ร—${v[c]}`);
      if(parts.length>1) detail=`<span style="color:var(--muted);font-size:9px"> (${parts.join(', ')})</span>`;
    }
    return `<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:3px 0;border-bottom:1px solid var(--faint);font-size:11px">
    <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(k)} โ’ <b>${esc(b?b.cat:'')}</b>${detail}</span>
    <button onclick="adminDeleteCat('${esc(k).replace(/'/g,"\\'")}')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:11px">โ•</button>
  </div>`;
  }).join('');
}
function adminDeleteCat(key){
  const mem=learnedMap(); delete mem[key]; saveLearned(mem); renderCatList(); toast('เธฅเธเนเธฅเนเธง','ok');
}

// generic POST action helper
async function sheetAction(payload){
  const url=getSheetUrl(); if(!url){ toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); return false; }
  try{
    const res=await fetch(url,{method:'POST',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify(payload)});
    const d=JSON.parse(await res.text()); return d&&d.ok;
  }catch{
    try{ await fetch(url,{method:'POST',mode:'no-cors',headers:{'Content-Type':'text/plain;charset=utf-8'},body:JSON.stringify(payload)}); return true; }catch{ return false; }
  }
}

function adminClearLocal(){
  if(!confirm('เธฅเธเธฃเธฒเธขเธเธฒเธฃเธ—เธฑเนเธเธซเธกเธ”เนเธเน€เธเธฃเธทเนเธญเธเธเธตเน? (เธเนเธญเธกเธนเธฅเธเธ Sheet เนเธกเนเธ–เธนเธเนเธ•เธฐ)')) return;
  entries=[]; save(); render(); toast('เธฅเธเธฃเธฒเธขเธเธฒเธฃเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเนเธง','ok');
}
async function adminClearSheet(){
  if(!confirm('เธฅเธเธฃเธฒเธขเธเธฒเธฃเธ—เธฑเนเธเธซเธกเธ”เธเธ Google Sheet? เธฅเธเนเธฅเนเธงเธเธนเนเนเธกเนเนเธ”เน')) return;
  toast('เธเธณเธฅเธฑเธเธฅเธเธเธ Sheetโ€ฆ');
  const ok=await sheetAction({action:'clearAll'});
  toast(ok?'เธฅเธเธฃเธฒเธขเธเธฒเธฃเธเธ Sheet เนเธฅเนเธง โ“':'เธฅเธเนเธกเนเธชเธณเน€เธฃเนเธ', ok?'ok':'err');
}
function adminClearCatsLocal(){
  if(!confirm('เธฅเธเธเธงเธฒเธกเธเธณเธซเธกเธงเธ”เนเธเน€เธเธฃเธทเนเธญเธเธเธตเน?')) return;
  saveLearned({}); renderCatList(); toast('เธฅเธเธเธงเธฒเธกเธเธณเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเนเธง','ok');
}
async function adminClearCatsSheet(){
  if(!confirm('เธฅเธเธเธงเธฒเธกเธเธณเธซเธกเธงเธ”เธเธ Sheet?')) return;
  const ok=await sheetAction({action:'clearCats'});
  toast(ok?'เธฅเธเธเธงเธฒเธกเธเธณเธเธ Sheet เนเธฅเนเธง โ“':'เธฅเธเนเธกเนเธชเธณเน€เธฃเนเธ', ok?'ok':'err');
}
async function adminClearEverything(){
  if(!confirm('โ ๏ธ เธฅเธเธ—เธธเธเธญเธขเนเธฒเธเธ—เธฑเนเธเนเธเน€เธเธฃเธทเนเธญเธเนเธฅเธฐเธเธ Sheet (เธฃเธฒเธขเธเธฒเธฃ + เธเธงเธฒเธกเธเธณเธซเธกเธงเธ”)?\nเธฅเธเนเธฅเนเธงเธเธนเนเนเธกเนเนเธ”เน!')) return;
  if(!confirm('เธขเธทเธเธขเธฑเธเธญเธตเธเธเธฃเธฑเนเธ โ€” เนเธเนเนเธเธเธฐ?')) return;
  entries=[]; save(); saveLearned({});
  await sheetAction({action:'clearAll'});
  await sheetAction({action:'clearCats'});
  render(); renderCatList(); toast('เธฅเธเธ—เธธเธเธญเธขเนเธฒเธเนเธฅเนเธง','ok');
}
async function adminPullSheetInfo(){
  const url=getSheetUrl(); if(!url){ toast('เธขเธฑเธเนเธกเนเนเธ”เนเธ•เธฑเนเธเธเนเธฒ Sheet URL','err'); return; }
  try{
    const res=await fetch(url,{method:'GET'}); const d=JSON.parse(await res.text());
    if(d&&d.ok) toast(`เธเธตเธ• "${d.sheetName}": ${d.rows} เธฃเธฒเธขเธเธฒเธฃ, ${Object.keys(d.cats||{}).length} เธเธงเธฒเธกเธเธณ`,'ok');
    else toast('เธญเนเธฒเธเธชเธ–เธฒเธเธฐเนเธกเนเนเธ”เน','err');
  }catch{ toast('เน€เธเธทเนเธญเธกเธ•เนเธญเนเธกเนเนเธ”เน','err'); }
}

init();
applyAdminUI();
// restore auto-sync toggle state + start timer
(function(){ const c=document.getElementById('autoSyncChk'); if(c){ c.checked=autoSyncOnPref(); } startAutoSync(); })();
// sync from cloud on start (silent): category memory + transaction rows
if(getSheetUrl()){ pullCats(true); pullData(true); }