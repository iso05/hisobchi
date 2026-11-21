import FieldInput from './FieldInput.jsx';
import React, {useEffect, useRef, useState} from 'react';
import {ExternalLink, RotateCcw, Scale} from 'lucide-react';
import {serverRequest} from '../lib/api.js';
import {languages, optionName, questionName, words} from '../lib/catalog-copy.js';
import {formState, scopeNotes} from '../lib/calculator-scope.js';

function citation(source, lang) {
  const label = source.article || source.title || 'Lex.uz';
  if (lang === 'uz') return label;
  const t = (...args) => words(lang,...args);
  if (/BHM/.test(label)) return t('', 'Базовая расчётная величина', 'Base calculation amount');
  if (/613-son.*I–II/.test(label)) return t('', 'Постановление № 613, пункт 17', 'Resolution 613, clause 17');
  if (/613-son/.test(label)) return t('', 'Постановление № 613, пункт 15', 'Resolution 613, clause 15');
  const appendix = label.match(/Ilova,\s*(\d+)-band(?:\s+(“[^”]+”(?:[,\s“”a-z–]*”)?))?/u);
  if (appendix) return t('', 'Приложение, пункт ', 'Appendix, clause ') + appendix[1] + (appendix[2] ? ' · '+appendix[2].replace(/ va /g, ', ').replace(/,\s*$/,'') : '');
  const article = label.match(/(\d+)-modda/);
  const clause = label.match(/(\d+)-band/);
  if (article) return t('', 'Статья ', 'Article ') + article[1] + (clause ? t('', ', пункт ', ', clause ')+clause[1] : '');
  return label;
}

export default function FeeForm({service, lang}) {
  const [model,setModel] = useState(null);
  const [attempt,setAttempt] = useState(0);
  const [entered,setEntered] = useState({});
  const [asOf,setAsOf] = useState('');
  const [result,setResult] = useState(null);
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const resultRef = useRef(null);
  const active = useRef(null);
  const t = (...args) => words(lang,...args);
  const money = v => new Intl.NumberFormat({uz:'uz-UZ',ru:'ru-RU',en:'en-GB'}[lang],{maximumFractionDigits:10}).format(v)+' '+t('so‘m','сум','UZS');
  useEffect(() => {
    const ctl = new AbortController();
    const query = '?service_id='+encodeURIComponent(service.id);
    setError('');
    Promise.all([serverRequest('/calculator/schema'+query,{signal:ctl.signal}), serverRequest('/rules/current'+query,{signal:ctl.signal})])
      .then(([schema,current]) => {if (!ctl.signal.aborted) {setModel({schema,current});setAsOf(current.server_date);}})
      .catch(() => {if (!ctl.signal.aborted) setError('load');});
    return () => {ctl.abort(); active.current?.abort();};
  },[service.id,attempt]);
  const {visible,answers} = formState(service.id, model?.schema.questions || [], entered);
  function update(key,value) {
    const next = formState(service.id, model.schema.questions, {...entered,[key]:value});
    setEntered(Object.fromEntries(next.visible.filter(q => q.key in next.answers).map(q => [q.key,next.answers[q.key]])));
    setResult(null); setError('');
  }
  async function calculate(e) {
    e.preventDefault();
    if (busy) return;
    const ctl = new AbortController();
    active.current = ctl;
    setError(''); setBusy(true); setResult(null);
    try {
      const data = await serverRequest('/calculate',{method:'POST',signal:ctl.signal,body:JSON.stringify({service_id:service.id,answers,as_of_date:asOf})});
      if (ctl.signal.aborted) return;
      if (!data.result || (data.result.payable_amount == null && !data.result.unrounded_payable)) setError('scope');
      else {
        setResult(data.result);
        requestAnimationFrame(() => resultRef.current?.focus({preventScroll: !window.matchMedia('(max-width: 760px)').matches}));
      }
    } catch (e) {if (!ctl.signal.aborted) setError(e.status === 422 ? 'input' : 'request');}
    finally {if (!ctl.signal.aborted) setBusy(false);}
  }
  const note = scopeNotes[service.id];
  const amount = result?.payable_amount;
  const config = model?.current.rule?.config;
  return <div className="workspace fee-workspace">
    <section className="chat-card manual-card refined-calculator">
      <div className="panel-heading"><h2>{t('Sizning holatingiz','Ваша ситуация','Your situation')}</h2><button className="icon-button" disabled={busy} type="button" aria-label={t('Tozalash','Сбросить','Reset')} onClick={() => {setEntered({});setResult(null);setError('');}}><RotateCcw size={17}/></button></div>
      {service.id.startsWith('court_') && <p className="form-note">{t('Hisob tanlangan talab va ko‘rsatilgan imtiyozlar uchun. Pochta va boshqa xarajatlar alohida.','Расчёт учитывает выбранное требование и перечисленные льготы. Почтовые и другие расходы оплачиваются отдельно.','Covers the selected claim and listed benefits. Postage and other costs are separate.')}</p>}
      {!model && !error && <p role="status">{t('Savollar yuklanmoqda…','Загружаем вопросы…','Loading questions…')}</p>}
      {model && <form className="manual-form" onSubmit={calculate}>
        {note && <aside className="demo-scope-note fee-scope-note">
          <strong>{t('Izoh','Примечание','Note')}</strong>
          <span>{note[languages.indexOf(lang)]}</span>
        </aside>}
        {config?.bhm_amount != null && <div className="current-rule compact-bhm"><div><span>{t('Bazaviy hisoblash miqdori','Базовая расчётная величина','Base calculation amount')}</span><strong>{money(config.bhm_amount)}</strong></div><small>{model.current.rule?.effective_from}</small></div>}
        {visible.map(q => <label className="field" key={q.key}><span>{questionName(q,lang)}</span>
          {q.type === 'choice' ? <select name={q.key} required={q.required !== false} value={answers[q.key] ?? ''} disabled={busy} onChange={e=>update(q.key,e.target.value)}><option value="">{t('Tanlang','Выберите','Select an option')}</option>{q.options.map(o=><option key={o.value} value={o.value}>{optionName(q,o,lang)}</option>)}</select>
          : <FieldInput name={q.key} type={q.type === 'text' ? 'text' : 'number'} min={q.min} max={q.key.endsWith('_numerator') ? Math.min(q.max ?? Infinity, answers[q.key.replace('_numerator','_denominator')] ?? Infinity) : q.max} step={q.step ?? 1} required={q.required !== false} maxLength={300} disabled={busy} value={answers[q.key] ?? ''} onValueChange={value =>update(q.key,q.type === 'text' || value === '' ? value : Number(value))}/>}
        </label>)}
        <label className="field">{t('Hisoblash sanasi','Дата расчёта','Calculation date')}<input required type="date" name="as_of_date" min={model.current.rule?.effective_from} max={model.current.server_date} value={asOf} disabled={busy} onChange={e=>{setAsOf(e.target.value);setError('');setResult(null);}}/></label>
        <button className="primary-button full-width" type="submit" disabled={busy}>{busy ? t('Hisoblanmoqda…','Считаем…','Calculating…') : t('Bojni hisoblash','Рассчитать пошлину','Calculate fee')}</button>
      </form>}
      {error && <div className="error-box" role="alert">{error === 'scope' ? t('Bu holat uchun e’lon qilingan aniq stavka yo‘q.','Для этой ситуации нет опубликованной однозначной ставки.','There is no published, unambiguous rate for this case.') : error === 'input' ? t('Kiritilgan sonlar va ulushlarni tekshiring.','Проверьте суммы и доли.','Check the amounts and shares you entered.') : t('Xizmatga ulanib bo‘lmadi. Yana urinib ko‘ring.','Не удалось подключиться. Попробуйте снова.','Could not connect. Please try again.')}{error === 'load' && <button type="button" onClick={()=>setAttempt(v=>v+1)}>{t('Qayta urinish','Повторить','Retry')}</button>}</div>}
    </section>
    <section className="chat-card fee-result" ref={resultRef} tabIndex={-1} aria-live="polite">
      <Scale size={25}/><h2>{t('Sizning hisobingiz','Ваш расчёт','Your fee')}</h2>
      {!result ? <p>{t('Savollarga javob bering. Shu yerda boj summasi va qonundagi asosi chiqadi.','Ответьте на вопросы, чтобы увидеть сумму и основание в законе.','Answer the questions to see the fee and its legal basis.')}</p> : <>
        <p>{amount == null ? t('Yaxlitlashdan oldingi aniq hisob','Точный расчёт до округления','Exact amount before rounding') : t('To‘lanadigan davlat boji','Госпошлина к уплате','State duty payable')}</p>
        <strong className="fee-total">{amount == null ? result.unrounded_payable+' '+t('so‘m','сум','UZS') : money(amount)}</strong>
        {result.benefit_unspecified && <p className="benefit-note">{amount === 0 ? t('Shaxsiy imtiyoz tanlanmadi. Boshqa javoblaringiz bo‘yicha boj 0 so‘m.','Личная льгота не выбрана. По остальным ответам пошлина равна нулю.','No personal benefit was selected. Your other answers give a zero fee.') : t('Bu hisobga qo‘shimcha imtiyoz kiritilmadi. Agar sizga tegishli imtiyoz aniqlansa, to‘lovingiz kamayishi mumkin.','В расчёт не включена дополнительная льгота. Если выяснится, что вам положена льгота, сумма может уменьшиться.','No additional benefit was applied. If you qualify for an additional benefit, your fee may be lower.')}</p>}
        {result.status === 'exempt' && <p>{t('Siz tanlagan holat davlat bojidan ozod.','В выбранном случае госпошлина не взимается.','The selected case is exempt from state duty.')}</p>}
        {result.saving_amount > 0 && <dl><dt>{t('Imtiyozsiz boj','Пошлина без льготы','Fee before relief')}</dt><dd>{money(result.standard_amount)}</dd><dt>{t('Imtiyoz miqdori','Размер льготы','Fee reduction')}</dt><dd>{money(result.saving_amount)}</dd></dl>}
        {result.previous_payment_credit > 0 && <p>{t('Oldingi to‘lov','Ранее уплачено','Previously paid')} · {money(result.previous_payment_credit)}</p>}
        {result.arithmetic?.map((line,i)=><p className="fee-equation" key={i}>{line}</p>)}
        {answers.exemption_parties === 'one' && result.status === 'standard' && <p>{t('Faqat bir taraf ozod bo‘lsa, bojni ikkinchi taraf to‘liq to‘laydi.','Если освобождена только одна сторона, другая уплачивает пошлину полностью.','If only one party is exempt, the other party pays the full duty.')}</p>}
        {result.interpretation_note && <p>{t(result.interpretation_note,'Совместное применение двух ставок основано на пояснении наставника-нотариуса.','Applying both rates together follows the notary mentor’s interpretation.')}</p>}
        {lang === 'uz' && !result.arithmetic?.length && <p>{result.explanation}</p>}
        <h3>{t('Qonuniy asos','Правовое основание','Legal basis')}</h3>
        {result.legal_basis?.map((s,i)=><a className="fee-source" key={i} href={s.url} target="_blank" rel="noreferrer">{citation(s,lang)} <ExternalLink size={15}/></a>)}
      </>}
    </section>
  </div>;
}
