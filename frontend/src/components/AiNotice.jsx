import React from 'react';

export const warnings = {
  uz: 'AI xato qilishi mumkin. Muhim ma’lumotlarni tekshiring.',
  'uz-Cyrl': 'AI хато қилиши мумкин. Муҳим маълумотларни текширинг.',
  ru: 'ИИ может ошибаться. Проверяйте важную информацию.',
  en: 'AI can make mistakes. Check important information.',
};

export default function AiNotice({ locale = 'uz', translations = false }) {
  return <div className="ai-notice" lang={locale}>
    {warnings[locale] || warnings.uz}
    {translations && <details><summary>O‘zbekcha · Русский · English</summary>
      {['uz', 'ru', 'en'].filter(key => key !== locale).map(key => <p key={key} lang={key}>{warnings[key]}</p>)}
    </details>}
  </div>;
}
