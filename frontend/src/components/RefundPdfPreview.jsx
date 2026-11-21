import React, { useEffect, useRef, useState } from 'react';
import { X } from 'lucide-react';

export default function RefundPdfPreview({ text, signature, lang, name, copy, onClose }) {
  const dialog = useRef(null), pages = useRef(null);
  const [status, setStatus] = useState('loading');
  useEffect(() => {
    const modal = dialog.current;
    modal.showModal();
    return () => modal.close();
  }, []);
  useEffect(() => {
    let stopped = false, task;
    const host = pages.current;
    async function render() {
      const [{ signedPdf }, pdfjs, worker] = await Promise.all([
        import('../lib/refund-pdf.js'), import('pdfjs-dist'), import('pdfjs-dist/build/pdf.worker.min.mjs?url'),
      ]);
      if (stopped) return;
      pdfjs.GlobalWorkerOptions.workerSrc = worker.default;
      const blob = await signedPdf(text, signature, lang, name);
      const data = await blob.arrayBuffer();
      if (stopped) return;
      task = pdfjs.getDocument({ data, isEvalSupported: false });
      const pdf = await task.promise;
      for (let n = 1; n <= pdf.numPages; n++) {
        const page = await pdf.getPage(n);
        if (stopped) return;
        const viewport = page.getViewport({ scale: 2 });
        const canvas = document.createElement('canvas');
        canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
        canvas.setAttribute('aria-label', String(n) + ' / ' + pdf.numPages);
        await page.render({ canvas, viewport }).promise;
        if (stopped) return;
        host.appendChild(canvas);
      }
      setStatus('ready');
    }
    render().catch(() => { if (!stopped) setStatus('failed'); });
    return () => { stopped = true; task?.destroy().catch(() => {}); host.replaceChildren(); };
  }, [text, signature, lang, name]);
  return <dialog ref={dialog} className="refund-pdf-modal" aria-labelledby="refund-pdf-title"
    onCancel={e => { e.preventDefault(); onClose(); }}>
    <header><h2 id="refund-pdf-title">{copy.pdfPreview}</h2>
      <button type="button" className="outline-button" aria-label={copy.closePreview} onClick={onClose} autoFocus><X size={20}/></button>
    </header>
    <div className="refund-pdf-scroll">
      {status !== 'ready' && <p role="status">{status === 'failed' ? copy.failed : copy.loadingPdf}</p>}
      <div className="refund-pdf-pages" ref={pages} aria-hidden="true"/>
      <div className="refund-sr-text" lang={lang}>{text}</div>
    </div>
  </dialog>;
}
