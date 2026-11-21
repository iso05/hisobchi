import React, { useEffect, useRef, useState } from 'react';
import { MessageSquareText, Send } from 'lucide-react';
import AiNotice from './AiNotice.jsx';
import { words } from '../lib/catalog-copy.js';
import { serverRequest } from '../lib/api.js';

export default function RagAssistant({ lang }) {
  const t = (...values) => words(lang, ...values);
  const title = t('Davlat boji yordamchisi', 'Помощник по госпошлинам', 'State duty assistant');
  const inputLabel = t('Savolingizni yozing', 'Введите вопрос', 'Type your question');
  const [draft, setDraft] = useState('');
  const [turns, setTurns] = useState([]);
  const [pending, setPending] = useState(false);
  const request = useRef(null);
  const log = useRef(null);

  useEffect(() => () => request.current?.abort(), []);
  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [turns]);

  async function send(question, retry = false) {
    question = question.trim();
    if (!question || request.current) return;
    const controller = new AbortController();
    request.current = controller;
    setPending(true);
    setTurns(previous => [...(retry ? previous.slice(0, -1) : previous), { question }]);
    if (!retry) setDraft('');
    const finish = update => setTurns(previous => [...previous.slice(0, -1), { question, ...update }]);
    try {
      const reply = await serverRequest('/assistant/chat', {
        method: 'POST', body: JSON.stringify({ question }), signal: controller.signal,
      });
      finish({ reply });
    } catch (error) {
      if (!controller.signal.aborted) finish({ error: error.status || 502 });
    } finally {
      request.current = null;
      if (!controller.signal.aborted) setPending(false);
    }
  }

  return (
    <section className="rag-inline" aria-label={title}>
      <div className="rag-layout">
        <section className="rag-chat" aria-labelledby="assistant-title">
          <header className="rag-heading">
            <span className="rag-heading-symbol" aria-hidden="true"><MessageSquareText size={23} /></span>
            <div><h1 id="assistant-title">{title}</h1>
              <span>LexAI</span>
            </div>
          </header>
          <div className="rag-messages" role="log" aria-live="polite" ref={log}>
            {turns.map(({ question, reply, error }, index) => <React.Fragment key={index}>
              <div className="rag-message user"><p>{question}</p></div>
              <div className="rag-message assistant">
                {reply ? <>
                  <p>{reply.answer}</p>
                  <small>{!reply.verified && t('LexAI javobni tasdiqlay olmadi. ', 'LexAI не подтвердил ответ. ', 'LexAI could not verify this answer. ')}
                    <a href="/">{t('Summani kalkulyatorda hisoblang', 'Рассчитать сумму в калькуляторе', 'Calculate the amount with the calculator')}</a>
                    {' · '}{(reply.latency_ms / 1000).toFixed(1)} s</small>
                  {reply.sources.length > 0 && <details className="rag-sources">
                    <summary>{t('Manbalar', 'Источники', 'Sources')} ({reply.sources.length})</summary>
                    {reply.sources.map((source, i) => <div key={i}>
                      <strong>{source.reference || source.id}</strong>
                      {source.reference && <small> · {source.id}</small>}
                      {source.text && <p>{source.text}</p>}
                    </div>)}
                  </details>}
                </> : error ? <>
                  <p>{error === 504 ? t('Javob kutilgan vaqtda kelmadi.', 'Время ожидания истекло.', 'The request timed out.')
                    : t('Hozir LexAI xizmatidan javob olish imkoni bo‘lmadi.', 'Сейчас не удалось получить ответ LexAI.', 'LexAI could not respond right now.')}</p>
                  {index === turns.length - 1 && <button type="button" className="outline-button" onClick={() => send(question, true)}>{t('Qayta urinish', 'Попробовать снова', 'Try again')}</button>}
                </> : <p>{t('Javob tayyorlanmoqda…', 'Готовим ответ…', 'Preparing an answer…')}</p>}
              </div>
            </React.Fragment>)}
          </div>
          <div className="conversation-dock">
            <form className="rag-composer" onSubmit={event => { event.preventDefault(); send(draft); }}>
              <textarea rows={1} aria-label={inputLabel} placeholder={inputLabel} maxLength={3000}
                value={draft} onChange={event => setDraft(event.target.value)}
                onKeyDown={event => {
                  if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
                    event.preventDefault(); send(draft);
                  }
                }} />
              <button className="send-button" type="submit" aria-label={t('Yuborish', 'Отправить', 'Send')} disabled={pending || !draft.trim()}><Send size={20} /></button>
            </form>
            <div className="rag-footnote"><AiNotice locale={lang} /></div>
          </div>
        </section>
      </div>
    </section>
  );
}
