import FieldInput from './FieldInput.jsx';
import React, {useEffect,useRef,useState} from 'react';
import {ArrowRight, Check, Download} from 'lucide-react';
import {refundLimit,refundDraft,missingField,money} from '../lib/refund.js';
import {agencies,grounds,exclusions,clauseChoices,excessTypes,civilBenefits,kinTypes,languageIndex} from '../lib/refund-options.js';
import {refundCopy} from '../lib/refund-copy.js';
import SignaturePad from './SignaturePad.jsx';
import RefundPdfPreview from './RefundPdfPreview.jsx';

function saveFile(blob,name) {
  const url=URL.createObjectURL(blob);
  const link=document.createElement('a');
  try {link.href=url;link.download=name;document.body.append(link);link.click();}
  finally {link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
}

export default function RefundDemo({lang}) {
  const [docLang,setDocLang]=useState(()=>lang==='ru'?'ru':'uz');
  const [mode,setMode]=useState('');
  const [data,setData]=useState({});
  const [draft,setDraft]=useState(null);
  const [consent,setConsent]=useState(false);
  const [signature,setSignature]=useState('');
  const [showPdf,setShowPdf]=useState(false);
  const [busy,setBusy]=useState(false);
  const [status,setStatus]=useState('');
  const [invalid,setInvalid]=useState('');
  const form=useRef(null), editor=useRef(null), version=useRef(0);
  const copy=refundCopy(lang), idx=languageIndex(lang);
  function invalidate(){version.current++;setShowPdf(false);setConsent(false);setSignature('');setDraft(null);setInvalid('');setStatus('');setBusy(false);}
  function clear(){invalidate();setMode('');setData({});}
  useEffect(()=>{
    function restore(e){if(e.persisted) clear();}
    window.addEventListener('pagehide',clear);window.addEventListener('pageshow',restore);
    return ()=>{version.current++;window.removeEventListener('pagehide',clear);window.removeEventListener('pageshow',restore);};
  },[]);
  function change(key,value){
    invalidate();
    setData(previous=>{
      const next={...previous,[key]:value};
      if(key==='agency') {next.reason='';next.authority='';}
      if(key==='agency'||key==='reason') {
        for(const field of ['orderRef','benefit','appeal','kin','tariffClause','tariffPart','due','requested']) delete next[field];
      }
      return next;
    });
  }
  const choices=clauseChoices(data.agency,mode);
  const blocked=Object.hasOwn(exclusions,data.reason);
  const hasCase=choices.includes(data.reason) && !blocked;
  const over=mode==='overpaid';
  const due = data.reason === 'exemption' ? 0 : data.due;
  let limit;
  try { limit = refundLimit(mode, data.amount, due); } catch { /* Incomplete payment details. */ }
  const hint = limit == null ? '' : (over ? copy.maximum : copy.mustMatch) + ' ' + money(limit,'en') + ' ' + copy.currency;
  function prepare(e){
    e.preventDefault();
    const missing=missingField(data,mode);
    if(missing || limit == null){
      const field=missing || (over && data.reason!=='exemption' ? 'due':'amount');
      setInvalid(field);setStatus(missing?'missing':'invalidAmount');form.current?.elements.namedItem(field)?.focus();return;
    }
    setDraft(refundDraft(data,mode,docLang));setStatus('');setInvalid('');
    requestAnimationFrame(()=>editor.current?.focus());
  }
  async function download(format){
    if(!consent || !signature || !draft?.trim() || busy) return;
    const attempt=++version.current;
    setBusy(true);setStatus('');
    try {
      const create=format==='pdf' ? (await import('../lib/refund-pdf.js')).signedPdf : (await import('../lib/refund-word.js')).signedLetter;
      const blob=await create(draft,signature,docLang,data.name);
      if(attempt!==version.current)return;
      saveFile(blob,(docLang==='ru'?'zayavlenie-vozvrat':'davlat-bojini-qaytarish')+'.'+format);
      clear();setStatus('cleared');
    } catch {if(attempt===version.current){setBusy(false);setStatus('failed');}}
  }
  function input(key,type='text',constraints={}){
    return <label className="field">{copy[key]}<FieldInput name={key} type={type} value={data[key]??''} onValueChange={value =>change(key,value)} aria-invalid={key===invalid}
      maxLength={200} required={key!=='orderRef'} min={type==='number'?(key==='due'?0:1):undefined} max={type==='number'?1e12:undefined} step={type==='number'?1:undefined} {...constraints}/></label>;
  }
  function select(key,options){
    return <label className="field">{copy[key]}<select name={key} value={data[key]??''} onChange={e=>change(key,e.target.value)} aria-invalid={invalid===key} required><option value="">{copy.select}</option>{options.map(([id,label])=><option value={id} key={id}>{label}</option>)}</select></label>;
  }
  const translated=options=>Object.entries(options).map(([id,list])=>[id,list[idx]]);
  function caseLabel(id){
    if(exclusions[id]) return exclusions[id][idx];
    if(over) return excessTypes[id][idx];
    const g=grounds[id];
    return g.clause+' · '+(lang==='en'?g.en:g[lang].fact);
  }
  return <main className="refund-page" lang={lang}>
    <section className="console-intro"><h1>{copy.title}</h1><p>{copy.subtitle}</p></section>
    <label className="refund-document-language"><span>{copy.language}</span><select name="documentLanguage" value={docLang} disabled={busy} onChange={e=>{invalidate();setDocLang(e.target.value);}}><option value="uz">O‘zbekcha</option><option value="ru">Русский</option></select></label>
    <h2>{copy.mode}</h2><div className="refund-kind-options">{['full','overpaid'].map(k=><button key={k} aria-pressed={mode===k} disabled={busy} onClick={()=>{if(k!==mode){change('reason','');setMode(k);}}}><strong>{copy[k]}</strong>{mode===k?<Check size={18}/>:<ArrowRight size={18}/>}</button>)}</div>
    {mode && <div className="refund-layout"><section className="chat-card manual-card"><h2>{copy.facts}</h2>
      <form className="manual-form" autoComplete="off" onSubmit={prepare} ref={form}><fieldset disabled={busy}>
        {select('agency',Object.entries(agencies).map(([id,a])=>[id,a.names[idx]]))}
        {!!choices.length && select('reason',choices.map(id=>[id,caseLabel(id)]))}
        {data.agency && !choices.length && <p role="status">{copy.onlyExcess}</p>}
        {blocked && <p role="status">{copy.blocked} <a href="https://lex.uz/docs/-3517337" target="_blank" rel="noreferrer">{({reduced:131,withdrawn:131,cancelled:174,rejected:138})[data.reason]} · Lex.uz</a></p>}
        {hasCase && <>
          {!over && <p className="form-note">{caseLabel(data.reason)}</p>}
          {input('authority')}
          {data.reason==='exemption' && <>{select('benefit',translated(civilBenefits))}<label><input type="checkbox" checked={!!data.appeal} onChange={e=>change('appeal',e.target.checked)}/> {copy.appeal}</label></>}
          {data.reason==='kin' && select('kin',translated(kinTypes))}
          {data.reason==='rate' && <div className="refund-fields">{input('tariffClause')}{input('tariffPart')}</div>}
          {!over && ['civil','economic','administrative'].includes(data.agency) && input('orderRef')}
          <div className="refund-fields refund-amount-fields">{input('amount','number')}{over && data.reason!=='exemption' && input('due','number')}</div>
          <div className="refund-request-entry">
            {input('requested','number',{min: !over && limit != null ? limit : 1, max: limit ?? 1e12, 'aria-describedby': hint ? 'refund-limit' : undefined})}
            {hint && <small id="refund-limit">{hint}</small>}
          </div>
          <div className="refund-fields">{input('date','date')}{input('receipt')}</div>{input('name')}{input('address')}{input('phone','tel')}
          {input('bank')}{input('account')}
        </>}
      </fieldset>
      {hasCase && <button type="submit" className="primary-button" disabled={!!draft || busy}>{copy.title}<ArrowRight size={16}/></button>}
      </form></section>
      <section className="result-card refund-preview"><h2>{copy.edit}</h2>
        {draft!==null ? <><textarea className="document-editor" lang={docLang} ref={editor} aria-label={copy.edit} value={draft} disabled={busy} autoComplete="off" spellCheck={false} onChange={e=>{setDraft(e.target.value);setConsent(false);setSignature('');setStatus('');}}/>
          <div className="refund-preview-actions">
            <button type="button" className="outline-button" disabled={!draft.trim()||busy} onClick={()=>setShowPdf(true)}>{copy.pdfPreview}</button>
            <button type="button" className="outline-button" disabled={!draft.trim()||consent||busy} onClick={()=>setConsent(true)}>{consent?copy.confirmed:copy.confirm}</button>
          </div>
          {showPdf && <RefundPdfPreview text={draft} signature={signature} lang={docLang} name={data.name} copy={copy} onClose={()=>setShowPdf(false)}/>}
          {consent && <><SignaturePad copy={copy} disabled={busy} onSign={setSignature}/><div className="refund-downloads">{['pdf','docx'].map(f=><button className="primary-button" key={f} type="button" disabled={busy || !signature} onClick={()=>download(f)}><Download size={16}/>{copy.download} · {f.toUpperCase()}</button>)}</div></>}
        </>:<p>{copy.previewEmpty}</p>}
        <div className="panel-note refund-legal-note"><a href="https://lex.uz/docs/-4680944#-4682898" target="_blank" rel="noreferrer">{copy.source}</a></div>
      </section></div>}
    {status&&<p className="refund-requested" role="status">{copy[status]}{status==='missing'?' · '+copy[invalid]:''}</p>}
    {mode&&<button className="outline-button" type="button" onClick={clear}>{copy.startOver}</button>}
  </main>;
}
