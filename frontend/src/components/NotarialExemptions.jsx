import React, { useState } from 'react';
import { plain } from '../lib/plain-language.js';
import { BookOpen, ArrowUpRight, ChevronDown } from 'lucide-react';

export default function NotarialExemptions({items=[]}) {
  const [all,setAll] = useState(false);
  if (!items.length) return null;
  const shown=all?items:items.filter(item=>item.applicable);
  return <details className="notarial-reference"><summary><span className="square-icon"><BookOpen size={19}/></span><span><strong>Notariusdagi imtiyozlar</strong><small>11-modda · 20 ta holat</small></span><ChevronDown className="reference-chevron" size={18}/></summary>
    <div className="reference-body"><p>Har bir imtiyozning o‘z sharti bor. Sizga mosini tanlang. Hujjatlarni notarius tekshiradi.</p><div className="reference-filter"><button type="button" aria-pressed={!all} onClick={()=>setAll(false)}>Shu xizmatga mos</button><button type="button" aria-pressed={all} onClick={()=>setAll(true)}>Barcha 20 holat</button></div>
      <div className="reference-items">{shown.map(item=><article key={item.number}><span className="reference-number">{String(item.number).padStart(2,'0')}</span><div><h3>{plain(item.title)}</h3><p>{plain(item.description)}</p>{all&&!item.applicable&&<small className="other-action">Boshqa notarius xizmatiga tegishli</small>}<a href={item.url} target="_blank" rel="noreferrer">11-modda, {item.number}-band <ArrowUpRight size={13}/></a></div></article>)}</div>
      <p className="reference-footnote">Bitimning faqat bir tarafi ozod bo‘lsa, 20-modda bo‘yicha bojni ikkinchi taraf to‘liq to‘laydi.</p>
    </div>
  </details>;
}
