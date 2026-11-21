import {useEffect, useState} from 'react';
import {languages} from './catalog-copy.js';

const storageKey = 'hisobchi.calculator.language';

export function usePageLanguage() {
  const [lang,setLang] = useState(() => {
    try { return languages.find(code => code === localStorage.getItem(storageKey)) || 'uz'; }
    catch { return 'uz'; }
  });
  useEffect(() => {
    document.documentElement.lang = lang;
    try { localStorage.setItem(storageKey,lang); } catch { /* Storage is optional. */ }
  },[lang]);
  return [lang,setLang];
}
