import React, { useState } from 'react';
import { Search, Check, X, CarFront, House, KeyRound, FileKey, Handshake, Landmark, Scale, BriefcaseBusiness, Smartphone, Lightbulb, Calculator, Copy, HeartCrack, Gavel, FileSearch, ScrollText } from 'lucide-react';
import { words, categoryName, serviceName } from '../lib/catalog-copy.js';
import { plain } from '../lib/plain-language.js';
import { SERVICE_ICONS } from '../lib/service-icons.js';

const normalize = (text) => String(text).toLowerCase().replace(/[‘’ʻʼ`]/g, "'");

const serviceIcons = {notary_car:CarFront,notary_property:House,notary_vehicle_power:KeyRound,notary_property_power:FileKey,notary_lease:Handshake,notary_inheritance:Landmark,court_civil:Scale,court_economic:BriefcaseBusiness,vehicle_power_electronic:Smartphone,patent_application:Lightbulb,court_copies:Copy,court_divorce:HeartCrack,court_economic_filing:Gavel,court_special_proceeding:FileSearch,court_nonproperty:ScrollText};

export default function ServicePicker({ services, selected, onSelect, lang = "uz" }) {
  const t = (...values) => words(lang, ...values);
  const [query, setQuery] = useState('');
  const [category, setCategory] = useState('Barchasi');
  const categories = ['Barchasi', ...new Set(services.map(s => s.category).filter(Boolean))];
  const matches = services.filter(s => (category === 'Barchasi' || s.category === category) && normalize(`${serviceName(s, lang)} ${categoryName(s.category,lang)} ${s.name} ${plain(s.name)} ${plain(s.category)} ${s.description || ''} ${s.category || ''}`).includes(normalize(query)));
  const current = services.find(s => s.id === selected);
  const CurrentIcon = serviceIcons[current?.id] || SERVICE_ICONS[current?.icon] || Calculator;
  return <>
    <form className="console-search" role="search" onSubmit={e => { e.preventDefault(); if (matches.length) onSelect(matches[0].id); }}>
      <Search size={23} /><label className="sr-only" htmlFor="service-search">{t('Xizmatni qidirish','Поиск услуги','Search services')}</label><input id="service-search" type="search" placeholder={t('Qaysi xizmat uchun boj hisoblaymiz?','Для какой услуги рассчитать пошлину?','Which service do you need?')} value={query} onChange={e => setQuery(e.target.value)} />
      {query && <button className="icon-button" type="button" aria-label={t('Qidiruvni tozalash','Очистить поиск','Clear search')} onClick={() => setQuery('')}><X size={17} /></button>}
      <button type="submit" className="primary-button">{t('Topish','Найти','Search')}</button>
    </form>
    <div className="search-categories category-marquee" role="group" aria-label={t('Xizmat toifalari','Категории услуг','Service categories')}>
      <div className="category-track">
        {[false,true].map(duplicate => (
          <div className="category-cycle" key={String(duplicate)} aria-hidden={duplicate || undefined}>
            {categories.map(c => (
              <button key={c} type="button" tabIndex={duplicate ? -1 : 0} aria-pressed={category === c} onClick={() => setCategory(c)}>
                {c === 'Barchasi' ? t('Barchasi','Все','All') : categoryName(c,lang)}
              </button>
            ))}
          </div>
        ))}
      </div>
    </div>
    <div className="search-results rich-service-grid" aria-label={t('Topilgan kalkulyatorlar','Найденные калькуляторы','Matching calculators')}>{matches.map(service => { const Icon=serviceIcons[service.id] || SERVICE_ICONS[service.icon] || Calculator; return <button key={service.id} aria-pressed={selected === service.id} className="search-service rich-service" onClick={() => onSelect(service.id)}><span className="service-pictogram"><Icon size={30} strokeWidth={1.6}/></span><span className="service-card-copy"><strong>{serviceName(service,lang)}</strong><small>{categoryName(service.category,lang)}</small></span>{selected === service.id && <Check className="service-selected-mark" size={18}/>}</button>; })}{!matches.length && <p className="search-empty">{t('Mos xizmat topilmadi. Boshqa so‘z kiriting yoki toifani o‘zgartiring.','Ничего не найдено. Измените запрос или категорию.','No matches. Try a different search or category.')}</p>}</div>
    {current && <section id="selected-calculator" tabIndex={-1} className="console-current selected-service-header" aria-label={t('Tanlangan kalkulyator','Выбранный калькулятор','Selected calculator')}><span className="selected-service-icon"><CurrentIcon size={27} strokeWidth={1.6}/></span><div><span>{t('Tanlangan xizmat','Выбранная услуга','Selected service')}</span><h2>{serviceName(current,lang)}</h2></div><span className="selected-rule-badge"><Check size={14}/> {t('Davlat boji hisobi','Госпошлина','State duty')}</span></section>}
  </>;
}
