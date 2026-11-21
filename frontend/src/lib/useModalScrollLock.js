import { useEffect } from 'react';

export function useModalScrollLock() {
  useEffect(() => {
    let restore = null;
    const sync = () => {
      if (document.querySelector('dialog[open]')) {
        if (restore) return;
        const y = window.scrollY;
        const body = document.body;
        const saved = ['position', 'top', 'width', 'overflow', 'paddingRight'].map(key => [key, body.style[key]]);
        const overflow = document.documentElement.style.overflow;
        const gutter = window.innerWidth - document.documentElement.clientWidth;
        const padding = parseFloat(getComputedStyle(body).paddingRight) || 0;
        Object.assign(body.style, { position: 'fixed', top: `-${y}px`, width: '100%', overflow: 'hidden', paddingRight: `${padding + gutter}px` });
        document.documentElement.style.overflow = 'hidden';
        restore = () => {
          saved.forEach(([key, value]) => { body.style[key] = value; });
          document.documentElement.style.overflow = overflow;
          window.scrollTo({ top: y, behavior: 'instant' });
        };
      } else if (restore) {
        restore(); restore = null;
      }
    };
    const observer = new MutationObserver(sync);
    observer.observe(document.documentElement, { subtree: true, attributes: true, attributeFilter: ['open'], childList: true });
    sync();
    return () => { observer.disconnect(); restore?.(); };
  }, []);
}
