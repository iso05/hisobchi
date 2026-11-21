import React, { useEffect } from 'react'
import RagAssistant from './components/RagAssistant.jsx'
import RefundDemo from './components/RefundDemo.jsx'
import { usePageLanguage } from './lib/usePageLanguage.js'
import { words } from './lib/catalog-copy.js'
import ServiceLauncher from './components/ServiceLauncher.jsx'
import { useModalScrollLock } from './lib/useModalScrollLock.js'

function Brand({ small = false }) {
  return (
    <span className={`brand ${small ? 'brand-small' : ''}`}>
      <span className="brand-mark" aria-hidden="true">
        <i />
        <i />
      </span>
      {!small && 'hisobchi'}
    </span>
  )
}

export default function App() {
  useModalScrollLock()
  const [lang, setLang] = usePageLanguage()
  const t = (...strings) => words(lang, ...strings)
  const refundPage = ['/ariza', '/ai-ariza', '/ai-xizmat'].includes(
    window.location.pathname
  )
  useEffect(() => {
    if (refundPage)
      document.title =
        t('Ariza yaratish', 'Создать заявление', 'Create an application') +
        ' · Hisobchi'
    else if (window.location.pathname === '/ai-yordamchi')
      document.title =
        t(
          'Davlat boji yordamchisi',
          'Помощник по госпошлинам',
          'State duty assistant'
        ) + ' · Hisobchi'
  }, [lang, refundPage])
  const assistantPage = window.location.pathname === '/ai-yordamchi'
  if (assistantPage)
    return (
      <>
        <main className="conversation-page">
          <RagAssistant lang={lang} />
        </main>
        <ServiceLauncher lang={lang} onLanguage={setLang} fromChat />
      </>
    )
  return (
    <>
      <a
        href="/"
        className="floating-brand"
        aria-label={t(
          'Hisobchi bosh sahifasi',
          'Главная страница Hisobchi',
          'Hisobchi home'
        )}
      >
        <Brand />
      </a>
      <RefundDemo lang={lang} />
      <ServiceLauncher lang={lang} onLanguage={setLang} />
      <footer className="footer">
        <Brand />
        <p>
          {t(
            'Huquqingizni biling. Ongli to‘lov qiling.',
            'Знайте свои права. Платите осознанно.',
            'Know your rights. Understand your fees.'
          )}
        </p>
        <span>LexHackathon 2026</span>
      </footer>
    </>
  )
}
