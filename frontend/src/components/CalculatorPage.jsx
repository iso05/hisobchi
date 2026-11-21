import React, {useEffect, useRef, useState} from 'react';
import {usePageLanguage} from '../lib/usePageLanguage.js';
import HeroMotion from './HeroMotion.jsx';
import ServiceLauncher from './ServiceLauncher.jsx';
import ServicePicker from './ServicePicker.jsx';
import FeeForm from './FeeForm.jsx';
import {words} from '../lib/catalog-copy.js';
import {serverRequest} from '../lib/api.js';
import {useModalScrollLock} from '../lib/useModalScrollLock.js';
import './calculator-page.css';

export default function CalculatorPage() {
  useModalScrollLock();
  const [lang,setLang] = usePageLanguage();
  const [services,setServices] = useState(null);
  const [error,setError] = useState(false);
  const [retry,setRetry] = useState(0);
  const [selected,setSelected] = useState(null);
  const [selection,setSelection] = useState(0);
  const deepLink = useRef(new URLSearchParams(location.search).get('calculator'));
  const t = (...args)=>words(lang,...args);
  useEffect(()=>{
    document.title = t('Davlat boji kalkulyatorlari','Калькуляторы госпошлины','State duty calculators')+' · Hisobchi';
  },[lang]);
  useEffect(()=>{
    let current;
    function refresh() {
      current?.abort();
      current = new AbortController();
      const {signal} = current;
      serverRequest('/services',{signal}).then(data=>{
        if (signal.aborted) return;
        setServices(data.services);setError(false);
        setSelected(id=>data.services.some(s=>s.id===id) ? id : null);
        const id = deepLink.current;
        if (id && data.services.some(s=>s.id===id)) {setSelected(id);setSelection(n=>n+1);deepLink.current=null;}
      }).catch(()=>{if (!signal.aborted) setError(true);});
    }
    refresh();window.addEventListener('focus',refresh);
    return ()=>{current?.abort();window.removeEventListener('focus',refresh);};
  },[retry]);
  useEffect(()=>{
    if (!selection) return;
    const frame = requestAnimationFrame(()=>{
      const el = document.getElementById('selected-calculator');
      el?.focus({preventScroll:true});
      el?.scrollIntoView({block:'start',behavior:matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'});
    });
    return ()=>cancelAnimationFrame(frame);
  },[selection]);
  const chosen = services?.find(s=>s.id===selected);
  return <>
    <a href="/" className="floating-brand" aria-label="Hisobchi"><span className="brand"><span className="brand-mark" aria-hidden="true"><i/><i/></span>hisobchi</span></a>
    <main className="search-console-page fee-page"><section className="hero console-intro"><HeroMotion/><h1>{t('Davlat boji','Калькуляторы','State duty')} <span>{t('kalkulyatorlari','госпошлины','calculators')}</span></h1><p>{t('Xizmatni tanlang. Qancha boj to‘lashingizni va qaysi imtiyoz sizga tegishli ekanini biling.','Выберите услугу, чтобы узнать сумму пошлины и доступные льготы.','Choose a service to see your fee and the benefits that apply to you.')}</p></section>
      <section id="calculators" className="calculator-section">
        {error && <p role="alert">{t('Katalogni yuklab bo‘lmadi.','Не удалось загрузить каталог.','Could not load the catalogue.')} <button className="outline-button" onClick={()=>setRetry(n=>n+1)}>{t('Qayta urinish','Повторить','Retry')}</button></p>}
        {!services && !error && <p role="status">{t('Yuklanmoqda…','Загрузка…','Loading…')}</p>}
        {services && <ServicePicker services={services} selected={selected} lang={lang} onSelect={id=>{setSelected(id);setSelection(n=>n+1);}}/>}
      </section>
      {chosen && <FeeForm key={chosen.id} service={chosen} lang={lang}/>}
    </main><ServiceLauncher lang={lang} onLanguage={setLang}/>
  </>;
}
