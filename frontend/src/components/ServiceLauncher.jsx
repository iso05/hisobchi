import React, {useEffect, useRef, useState} from 'react';
import {Calculator, MessagesSquare, FilePenLine, Languages, Sparkles, ArrowUpRight} from 'lucide-react';
import {words} from '../lib/catalog-copy.js';
import './service-tools.css';

const languageNames = {uz:'O‘zbekcha', ru:'Русский', en:'English'};

export default function ServiceLauncher({lang, onLanguage, fromChat = false}) {
  const t = (...strings) => words(lang,...strings);
  const [open,setOpen] = useState(null);
  const root = useRef(null);
  const closeTimer = useRef(null);
  const pinned = useRef(false);
  const triggers = useRef({});
  const actions = [
    ['/',Calculator,fromChat ? t('Bosh sahifaga qaytish','На главную','Back to home') : t('To‘lovni hisoblash','Рассчитать пошлину','Calculate a fee')],
    ['/ai-yordamchi',MessagesSquare,t('AI yordamchiga yozish','Спросить ИИ-помощника','Ask the AI assistant')],
    ['/ariza',FilePenLine,t('Ariza yaratish','Создать заявление','Create an application')],
  ];
  const stopTimer = () => clearTimeout(closeTimer.current);
  function close() {stopTimer();pinned.current=false;setOpen(null);}
  useEffect(() => {
    const outside = e => {if (!root.current?.contains(e.target)) close();};
    document.addEventListener('pointerdown',outside);
    return () => {document.removeEventListener('pointerdown',outside);clearTimeout(closeTimer.current);};
  },[]);
  function group(id) {
    return {
      className:'tool-group', 'data-open':open===id,
      onPointerEnter:e=>{
        if (e.pointerType !== 'mouse') return;
        stopTimer();
        if (open !== id) {pinned.current=false;setOpen(id);}
      },
      onPointerLeave:e=>{
        if (e.pointerType === 'mouse' && !pinned.current) {
          stopTimer();closeTimer.current=setTimeout(()=>setOpen(null),180);
        }
      },
    };
  }
  function trigger(id) {
    return {
      type:'button',ref:el=>{triggers.current[id]=el;},'aria-expanded':open===id,'aria-controls':'tools-'+id,
      onClick:()=>{stopTimer();if (open===id && pinned.current) close();else {pinned.current=true;setOpen(id);}},
      onKeyDown:e=>{
        if (e.key==='ArrowDown' || e.key==='ArrowUp') {
          e.preventDefault();stopTimer();pinned.current=true;setOpen(id);
          requestAnimationFrame(()=>document.querySelector('#tools-'+id+' :is(a,button)')?.focus());
        }
      },
    };
  }
  return <aside className="service-tools" ref={root} aria-label={t('Til va xizmatlar','Язык и услуги','Language and services')}
    onBlur={e=>{if (!e.currentTarget.contains(e.relatedTarget)) close();}}
    onKeyDown={e=>{if (e.key==='Escape' && open) {e.preventDefault();triggers.current[open]?.focus();close();}}}>
    <div {...group('language')}>
      <button {...trigger('language')} className="tool-language" aria-label={t('Sahifa tili','Язык страницы','Page language')}><Languages size={19}/>{lang.toUpperCase()}</button>
      {open==='language' && <div id="tools-language" className="tool-options">{Object.entries(languageNames).filter(([code])=>code!==lang).map(([code,name])=><button key={code} type="button" lang={code} onClick={()=>{onLanguage(code);triggers.current.language?.focus();close();}}>{name}<span>{code.toUpperCase()}</span></button>)}</div>}
    </div>
    <div {...group('services')}>
      <button {...trigger('services')} className="tool-services"><Sparkles size={21}/>{t('Nima qilmoqchisiz?','Чем помочь?','How can we help?')}</button>
      {open==='services' && <nav id="tools-services" className="tool-options" aria-label={t('Xizmatlar','Услуги','Services')}>{actions.map(([href,Icon,label])=><a href={href} key={href}><Icon size={18}/>{label}<ArrowUpRight size={14}/></a>)}</nav>}
    </div>
  </aside>;
}
