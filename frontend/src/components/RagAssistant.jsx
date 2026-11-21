import React from 'react';
import { MessageSquareText, Send } from 'lucide-react';
import AiNotice from './AiNotice.jsx';
import { words } from '../lib/catalog-copy.js';

export default function RagAssistant({ lang }) {
  const t = (...values) => words(lang, ...values);
  const title = t('Davlat boji yordamchisi', 'Помощник по госпошлинам', 'State duty assistant');
  const status = t('AI yordamchi hali ulanmagan.', 'ИИ-помощник пока не подключён.', 'The AI assistant is not connected yet.');
  const inputLabel = t('Xabar yozish', 'Написать сообщение', 'Write a message');

  return (
    <section className="rag-inline" aria-label={title}>
      <div className="rag-layout">
        <section className="rag-chat" aria-labelledby="assistant-title">
          <header className="rag-heading">
            <span className="rag-heading-symbol" aria-hidden="true"><MessageSquareText size={23} /></span>
            <div>
              <h1 id="assistant-title">{title}</h1>
              <span id="assistant-status">{status}</span>
            </div>
          </header>
          <div className="rag-messages" />
          <div className="conversation-dock">
            <div className="rag-composer">
              <textarea rows={1} aria-label={inputLabel} aria-describedby="assistant-status" placeholder={inputLabel} disabled />
              <button className="send-button" type="button" aria-label={t('Yuborish', 'Отправить', 'Send')} disabled>
                <Send size={20} />
              </button>
            </div>
            <div className="rag-footnote"><AiNotice locale={lang} /></div>
          </div>
        </section>
      </div>
    </section>
  );
}
