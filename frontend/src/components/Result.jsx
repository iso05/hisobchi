import React, { useEffect, useState } from 'react';
import { FilePenLine, Check, ShieldCheck, ExternalLink, Info, CheckCircle2, CircleHelp, Wallet, ChevronRight } from 'lucide-react';
import { plain } from '../lib/plain-language.js';
const money = value => value == null ? 'Aniqlanmagan' : new Intl.NumberFormat('uz-UZ').format(value);

export default function Result({ result, pending }) {
  const [expanded, setExpanded] = useState(false);
  useEffect(() => setExpanded(false), [result]);
  if (!result) return <aside className="result-card result-empty" aria-label="Hisob natijasi">
    <div className="panel-heading"><h2>Sizning hisobingiz</h2><span className="small-badge">Natija</span></div>
    <div className="empty-content"><div className="empty-visual"><Wallet size={34} strokeWidth={1.4} /><span className="floating-check"><Check size={16} /></span></div>
      <h3>{pending ? 'Holatingizni aniqlayapmiz' : 'Hisobingiz shu yerda chiqadi'}</h3>
      <p>{pending ? 'Kerakli savollarga javob bering. Natija shu yerda ko‘rinadi.' : 'Savollarga javob bering. So‘ng hisoblash tugmasini bosing.'}</p>
      <div className="empty-checks"><span><Check size={15} /> To‘lanadigan davlat boji</span><span><Check size={15} /> Imtiyoz va qonun asosi</span><span><Check size={15} /> Keyingi amaliy qadam</span></div>
    </div><div className="panel-note"><ShieldCheck size={17} /><span>Hisob bilan birga qonun havolasi ham ko‘rsatiladi.</span></div>
  </aside>;
  const exempt = ['exempt', 'discounted'].includes(result.status);
  const unknown = result.payable_amount == null;
  return <aside className="result-card has-result" aria-label="Hisob natijasi" aria-live="polite">
    <div className="panel-heading"><h2>Sizning hisobingiz</h2><span className="small-badge">{result.is_demo ? 'Namuna' : 'Natija'}</span></div>
    <div className="service-summary"><span className="square-icon"><FilePenLine size={21} /></span><h3>{plain(result.title)}</h3></div>
    <div className={`amount ${unknown ? 'amount-unknown' : ''}`}>{unknown ? 'Tekshirish kerak' : <>{money(result.payable_amount)} <span>so‘m</span></>}</div>
    <p className="amount-label">{unknown ? 'Aniq summa hali belgilanmagan' : result.duty_breakdown?.length ? 'Jami davlat boji' : 'To‘lanadigan davlat boji'}</p>
    <div className={`benefit-banner ${exempt ? '' : 'benefit-pending'}`}>{exempt ? <CheckCircle2 size={22} /> : <CircleHelp size={22} />}<strong>{plain(result.benefit_title)}</strong></div>
    <p className="result-explanation">{plain(result.explanation)}</p>
    {result.duty_breakdown?.length > 0 && <div className="breakdown duty-components" aria-label="Davlat boji qismlari">{result.duty_breakdown.map(part => <React.Fragment key={part.name}><span>{part.name} · {part.pay_percent}%</span><strong>{money(part.amount)} so‘m</strong></React.Fragment>)}</div>}
    {result.interpretation_note && <p className="form-note">{result.interpretation_note}</p>}
    {result.review_note && <p className="review-note">{result.review_note}</p>}
    {result.rule_version && <p className="result-version">Qoida #{result.rule_version} · Hisob sanasi: {result.as_of_date}{result.verified_at && <> · Tekshirilgan: {result.verified_at}</>}</p>}
    <details className="result-sources"><summary><ShieldCheck size={15}/> Qonuniy asoslar <span>{(result.legal_basis || []).length}</span></summary>{(result.legal_basis || []).map((source,index)=><div className="legal-row" key={index}><div><span className="eyebrow">Huquqiy asos</span><strong>{source.article||source.title}</strong></div>{/^https:\/\/(www\.)?(lex\.uz|my\.gov\.uz|sud\.uz)(\/|$)/.test(source.url)&&<a href={source.url} target="_blank" rel="noreferrer">Manba <ExternalLink size={14}/></a>}</div>)}</details>
    {result.standard_amount != null && <div className="breakdown"><span>Chegirmasiz to‘lov</span><strong>{money(result.standard_amount)} so‘m</strong>{result.saving_amount != null && <><span>Kamroq to‘lanadigan summa</span><strong>{money(result.saving_amount)} so‘m</strong></>}</div>}
    {result.previous_payment_credit > 0 && <div className="breakdown"><span>Jami hisoblangan boj</span><strong>{money(result.total_duty_amount)} so‘m</strong><span>Oldin to‘langan boj</span><strong>−{money(result.previous_payment_credit)} so‘m</strong></div>}
    <div className="next-section"><div className="next-heading"><span className="square-icon"><FilePenLine size={20} /></span><div><h3>Keyingi qadam</h3><p>Imtiyozdan qanday foydalanaman?</p></div></div><button className="outline-button full-width" onClick={() => setExpanded(v => !v)} aria-expanded={expanded}>{expanded ? 'Yo‘riqnomani yopish' : 'Yo‘riqnomani ko‘rish'}<ChevronRight size={16} className={expanded ? 'rotate' : ''} /></button>{expanded && <ol className="steps-list">{(result.next_steps || []).map((step, i) => <li key={i}>{step}</li>)}</ol>}</div>
    <div className="panel-note"><Info size={17} /><span>{plain(result.other_costs_note)}</span></div>
  </aside>;
}

