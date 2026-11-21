import FieldInput from './FieldInput.jsx';
import React, { useEffect, useRef, useState } from 'react';
import { Calculator, LoaderCircle, RotateCcw } from 'lucide-react';
import { plain } from '../lib/plain-language.js';
import { serverRequest } from '../lib/api.js';

export default function ManualCalculator({ serviceId='notary_car', onResult, onInvalidate }) {
  const [schema, setSchema] = useState(null);
  const [rule, setRule] = useState(null);
  const [answers, setAnswers] = useState({});
  const [date, setDate] = useState('');
  const [today, setToday] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const mounted = useRef(true);

  async function load() {
    setError(''); setLoading(true);
    try {
      const [form, current] = await Promise.all([serverRequest(`/calculator/schema?service_id=${serviceId}`), serverRequest(`/rules/current?service_id=${serviceId}`)]);
      if (!mounted.current) return;
      // The checkpoint demo covers standard vehicles, not expert-assessed damage.
      const publicForm = serviceId === 'notary_car' ? {
        ...form,
        questions: form.questions.filter(q => !['damaged','damage_assessed','residual_percent'].includes(q.key)),
      } : form;
      setSchema(publicForm); setRule(current.rule); setDate(current.server_date); setToday(current.server_date);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { mounted.current=true; load(); return () => { mounted.current=false; }; }, [serviceId]);

  function changeAnswer(key, value) {
    setAnswers(previous => {
      const next = { ...previous, [key]: value };
      // Drop answers from branches that disappeared after a capacity/type change.
      let changed = true;
      while (changed) {
        changed = false;
        for (const question of schema?.questions || []) {
          if (question.key in next && !Object.entries(question.when || {}).every(([dependency,values]) => values.includes(next[dependency]))) {
            delete next[question.key]; changed = true;
          }
        }
      }
      return next;
    });
    onInvalidate();
  }

  async function submit(e) {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const { damaged, damage_assessed, residual_percent, ...standardVehicleAnswers } = answers;
      const submittedAnswers = serviceId === 'notary_car' ? { ...standardVehicleAnswers, damaged: 'no' } : answers;
      const response = await serverRequest('/calculate', { method: 'POST', body: JSON.stringify({ service_id: serviceId, answers: submittedAnswers, as_of_date: date }) });
      if (!mounted.current) return;
      if (response.question) setError(response.question.label);
      else onResult(response.result);
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  }

  const visibleQuestions = schema?.questions.filter(q => Object.entries(q.when || {}).every(([key,values]) => values.includes(answers[key]))) || [];
  const completed = visibleQuestions.filter(q => answers[q.key] !== undefined && answers[q.key] !== '').length;
  return <section className="chat-card manual-card refined-calculator" aria-label="Mustaqil kalkulyator"><div className="panel-heading"><div><span className="form-eyebrow">SIZNING HOLATINGIZ</span><h2>Savollarga javob bering</h2><p>Javoblaringizga mos boj va imtiyozni hisoblaymiz.</p></div><button type="button" className="icon-button" aria-label="Javoblarni tozalash" title="Javoblarni tozalash" disabled={loading || busy} onClick={() => {setAnswers({});setError('');onInvalidate();}}><RotateCcw size={18}/></button></div>
    {loading ? <p className="form-loading"><LoaderCircle size={17} className="spin" /> Qoidalar yuklanmoqda...</p> : <form className="manual-form" onSubmit={submit}>
      {serviceId === 'notary_car' && <p className="demo-scope-note">Demo shikastlanmagan transport uchun. YTH va ekspertiza holatlari bu hisobga kirmaydi.</p>}
      <div className="form-progress"><div><span>To‘ldirilgan savollar</span><strong>{completed}<span> / {visibleQuestions.length}</span></strong></div><progress value={completed} max={visibleQuestions.length || 1} aria-label="To‘ldirilgan savollar"/></div>
      {rule && <div className="current-rule compact-bhm"><span className="bhm-symbol"><Calculator size={20}/></span><div><span>Hisoblash uchun asosiy miqdor</span><strong>{new Intl.NumberFormat('uz-UZ').format(rule.config.bhm_amount)} <small>so‘m · BHM</small></strong></div><span className="bhm-rule-date">{rule.effective_from} dan</span></div>}
      {visibleQuestions.map(question => <label className="field" key={question.key}>{plain(question.label)}{question.type === 'choice' ? <select required={question.required !== false} value={answers[question.key] ?? ''} onChange={e => changeAnswer(question.key, e.target.value)} disabled={busy}><option value="" disabled>Tanlang</option>{question.options.map(option => <option key={option.value} value={option.value}>{plain(option.label)}</option>)}</select> : <FieldInput type={question.type === "text" ? "text" : "number"} inputMode={question.type === "text" ? "text" : "decimal"} step={question.step ?? 1} required={question.required !== false} maxLength={300} min={question.min} max={question.max} value={answers[question.key] ?? ''} onValueChange={value => changeAnswer(question.key, question.type === 'text' ? value : value === '' ? '' : Number(value))} disabled={busy} />}{question.help && <span className="question-help">{plain(question.help_by_value?.[answers[question.key]] || question.help)}</span>}</label>)}
      <label className="field">Hisoblash sanasi<input type="date" required value={date} max={today} onChange={e => { setDate(e.target.value); onInvalidate(); }} disabled={busy} /></label>
      {error && <div className="error-box form-error" role="alert">{error}</div>}
      {schema ? <button type="submit" className="primary-button full-width" disabled={busy}>{busy ? 'Hisoblanmoqda...' : 'Davlat bojini hisoblash'}</button> : <button className="outline-button" type="button" onClick={load}>Qayta yuklash</button>}
      <p className="form-note">Natija faqat tanlangan davlat boji uchun. Boshqa xarajatlar alohida.</p>
    </form>}
  </section>;
}
