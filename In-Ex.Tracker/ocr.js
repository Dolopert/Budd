// Finance Slip — OCR text parsing module
// แยกมาจาก app.js (cleanLine, cleanName, meaningfulToken, OCR_FIXES, fixOcrWords, parseSlipText)
// โหลดหลัง app.js — เรียก getMyAccounts()/norm() จาก app.js ตอน runtime

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