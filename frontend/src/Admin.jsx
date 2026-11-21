import FieldInput from './components/FieldInput.jsx';
import React, { useEffect, useState } from 'react'
import {
  Calculator,
  LogOut,
  CheckCircle2,
  LockKeyhole,
  History,
} from 'lucide-react'
import { serverRequest } from './lib/api.js'
import CalculatorTable from './components/CalculatorTable.jsx'
import BuilderEditor from './components/BuilderEditor.jsx'
import { tariffSummary } from './lib/tariffs.js'

const fields = [
  ['bhm_amount', 'BHM (so‘m)', 'number', '1'],
  ['car_bhm_multiplier', 'Avtomobil: BHM ko‘paytmasi', 'number', '0.001'],
  [
    'motorcycle_bhm_multiplier',
    'Mototransport: BHM ko‘paytmasi',
    'number',
    '0.001',
  ],
  [
    'relative_pay_percent',
    'Qarindoshga: bojning to‘lanadigan foizi',
    'number',
    '0.001',
  ],
  [
    'bank_pay_percent',
    'Bank krediti: bojning to‘lanadigan foizi',
    'number',
    '0.001',
  ],
  [
    'outside_multiplier',
    'Idoradan tashqarida: koeffitsiyent',
    'number',
    '0.001',
  ],
  ['effective_from', 'Kuchga kirish sanasi', 'date'],
  ['verified_at', 'Manba tekshirilgan sana', 'date'],
  ['law_url', 'Davlat boji qonuni (Lex.uz havolasi)', 'url'],
  ['law_article', 'Modda / band', 'text'],
  ['bhm_source_url', 'BHM uchun Lex.uz havolasi', 'url'],
]
const money = (n) => new Intl.NumberFormat('uz-UZ').format(n)

export default function Admin() {
  const [auth, setAuth] = useState(false),
    [checking, setChecking] = useState(true)
  const [password, setPassword] = useState(''),
    [rules, setRules] = useState([]),
    [events, setEvents] = useState([])
  const [form, setForm] = useState(null),
    [error, setError] = useState(''),
    [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false),
    [reviewed, setReviewed] = useState(false),
    [serverDate, setServerDate] = useState('')
  const [calculators, setCalculators] = useState([]),
    [showDeleted, setShowDeleted] = useState(false),
    [editingId, setEditingId] = useState(null)

  const [custom, setCustom] = useState([]),
    [categories, setCategories] = useState([]),
    [builderEditing, setBuilderEditing] = useState(null),
    [builderPreview, setBuilderPreview] = useState(false)
  async function load() {
    const [data, audit, catalog, dynamic, cats] = await Promise.all([
      serverRequest('/admin/rules?service_id=all'),
      serverRequest('/admin/audit'),
      serverRequest('/admin/calculators'),
      serverRequest('/admin/builder'),
      serverRequest('/admin/categories'),
    ])
    setCustom(dynamic.calculators)
    setCategories(cats.categories)
    setRules(data.rules)
    setEvents(audit.events)
    setServerDate(data.server_date)
    setCalculators(catalog.calculators)
  }
  useEffect(() => {
    serverRequest('/admin/me')
      .then(async () => {
        setAuth(true)
        await load()
      })
      .catch((e) => {
        if (e.status !== 401) setError(e.message)
      })
      .finally(() => setChecking(false))
  }, [])

  async function login(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      await serverRequest('/admin/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      })
      setPassword('')
      setAuth(true)
      await load()
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }
  async function logout() {
    setError('')
    try {
      await serverRequest('/admin/logout', { method: 'POST' })
      setAuth(false)
      setForm(null)
    } catch (e) {
      setError(e.message)
    }
  }
  async function save(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await serverRequest(`/admin/calculators/${editingId}`, {
        method: 'PUT',
        body: JSON.stringify({
          ...form,
          bhm_amount: Number(form.bhm_amount),
          reviewed,
        }),
      })
      setForm(null)
      await load()
      setNotice(
        `O‘zgarishlar saqlandi. ${form.effective_from} sanadan qo‘llanadi.`
      )
    } catch (e) {
      setError(e.message)
      if (e.status === 401) setAuth(false)
    } finally {
      setBusy(false)
    }
  }
  function edit(calculator) {
    if (calculator.dynamic) {
      setBuilderEditing(calculator.id)
      setBuilderPreview(false)
      setForm(null)
      return
    }
    setBuilderEditing(null)
    const latest = rules.find(
      (r) => r.status === 'published' && r.service_id === calculator.id
    )
    setEditingId(calculator.id)
    setReviewed(false)
    setError('')
    setNotice('')
    setForm({
      ...(calculator.rule || latest).config,
      effective_from:
        latest?.effective_from > serverDate
          ? latest.effective_from
          : serverDate,
      verified_at: serverDate,
      change_note: '',
    })
  }
  async function changeAvailability(calculator, restore = false) {
    setBusy(true)
    setError('')
    setNotice('')
    try {
      await serverRequest(
        `${calculator.dynamic ? '/admin/builder' : '/admin/calculators'}/${calculator.id}${restore ? '/restore' : ''}`,
        { method: restore ? 'POST' : 'DELETE' }
      )
      setForm(null)
      setBuilderEditing(null)
      await load()
      setNotice(
        restore
          ? 'Kalkulyator qayta tiklandi.'
          : 'Kalkulyator o‘chirildi. Oldingi hisoblar va tarix saqlandi.'
      )
    } catch (e) {
      setError(e.message)
      if (e.status === 401) setAuth(false)
    } finally {
      setBusy(false)
    }
  }
  const currentRuleIds = new Set(
    [...calculators, ...custom].map((c) => c.rule?.id)
  )
  const editingCalculator = calculators.find((c) => c.id === editingId)
  const editFields =
    editingId === 'notary_car'
      ? fields
      : [
          fields[0],
          ...(editingCalculator?.parameters || []).map((p) => [
            `parameters.${p.key}`,
            `${p.label} (${p.unit})`,
            'number',
            '0.001',
          ]),
          ...fields.slice(6),
        ]
  const readValue = (key) =>
    key.startsWith('parameters.')
      ? form.parameters?.[key.split('.')[1]]
      : form[key]
  const changeValue = (key, value) =>
    setForm(
      key.startsWith('parameters.')
        ? {
            ...form,
            parameters: { ...form.parameters, [key.split('.')[1]]: value },
          }
        : { ...form, [key]: value }
    )
  async function refreshCategories() {
    const r = await serverRequest('/admin/categories')
    setCategories(r.categories)
  }
  function openBuilder(id = 'new', preview = false) {
    setBuilderEditing(id)
    setBuilderPreview(preview)
    setForm(null)
    setError('')
    requestAnimationFrame(() =>
      document
        .getElementById(`builder-${id}`)
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    )
  }
  async function publishBuilder(c) {
    setBusy(true)
    setError('')
    try {
      await serverRequest(`/admin/builder/${c.id}/publish`, {
        method: 'POST',
        body: JSON.stringify({ revision: c.revision }),
      })
      await load()
      setNotice('Kalkulyator e’lon qilindi. Saytda o‘z toifasida ko‘rinadi.')
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }
  const allCalculators = [...calculators, ...custom]
  const legacyEditor = form && (
    <section className="admin-editor">
      <h2>{editingCalculator?.name} — tahrirlash</h2>
      <p>
        Davlat boji va foizlarni o‘zgartiring. Masalan: 5% to‘lash = 95%
        kamayish. Saqlanganda oldingi qoida tarixda qoladi.
      </p>
      <form onSubmit={save}>
        <div className="admin-fields">
          {editFields.map(([key, label, type, step]) => (
            <label
              key={key}
              className={`field ${type === 'url' || key === 'law_article' ? 'wide-field' : ''}`}
            >
              {label}
              <FieldInput
                required
                type={type}
                step={step}
                value={readValue(key)}
                disabled={busy}
                max={
                  key === 'verified_at'
                    ? serverDate
                    : key.includes('_percent')
                      ? 100
                      : undefined
                }
                min={
                  key.includes('_percent')
                    ? 0
                    : type === 'number'
                      ? key === 'outside_multiplier' || key === 'bhm_amount'
                        ? 1
                        : 0.001
                      : undefined
                }
                onValueChange={value => changeValue(key, value)}
              />
            </label>
          ))}
        </div>
        <label className="field">
          O‘zgarish izohi va qonuniy asosi
          <textarea
            required
            minLength={10}
            maxLength={1500}
            rows={3}
            value={form.change_note}
            onChange={(e) => setForm({ ...form, change_note: e.target.value })}
            placeholder="Qaysi hujjat bilan nima o‘zgardi?"
          />
        </label>
        <label className="edit-review">
          <input
            type="checkbox"
            required
            checked={reviewed}
            onChange={(e) => setReviewed(e.target.checked)}
          />{' '}
          Qonun manbasi, davlat boji va foizlarni tekshirdim.
        </label>
        <div className="report-actions">
          <button
            type="button"
            className="outline-button"
            disabled={busy}
            onClick={() => setForm(null)}
          >
            Bekor qilish
          </button>
          <button className="primary-button" disabled={busy || !reviewed}>
            {busy ? 'Saqlanmoqda...' : 'O‘zgarishlarni saqlash'}
          </button>
        </div>
      </form>
    </section>
  )
  return (
    <div className="admin-shell">
      <header className="admin-header">
        <a className="brand" href="/">
          hisobchi <small>admin</small>
        </a>
        <div>
          <a href="/">Kalkulyatorga qaytish</a>
          {auth && (
            <button className="outline-button" onClick={logout}>
              <LogOut size={15} /> Chiqish
            </button>
          )}
        </div>
      </header>
      {!auth ? (
        <main className="admin-login">
          <span className="assistant-emblem">
            <LockKeyhole size={25} />
          </span>
          <h1>Qoidalarni boshqarish</h1>
          <p>Faqat mas’ul administrator uchun.</p>
          {checking ? (
            <p>Tekshirilmoqda...</p>
          ) : (
            <form onSubmit={login}>
              <label className="field">
                Admin paroli
                <input
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <button className="primary-button full-width" disabled={busy}>
                {busy ? 'Kirilmoqda...' : 'Kirish'}
              </button>
            </form>
          )}
          {error && (
            <p className="report-error" role="alert">
              {error}
            </p>
          )}
        </main>
      ) : (
        <main className="admin-main">
          <div className="admin-intro">
            <div>
              <span className="intro-badge">
                <Calculator size={14} /> Admin panel
              </span>
              <h1>Kalkulyatorlar</h1>
              <p>
                Omil, variant va hisoblash qoidasini kiriting. Sinab ko‘rib,
                saytga chiqaring.
              </p>
            </div>
            <div className="builder-top-actions">
              <span className="catalog-total">
                {allCalculators.filter((c) => c.active).length} ta kalkulyator
              </span>
              <button
                type="button"
                className="primary-button"
                disabled={!serverDate || busy}
                onClick={() => openBuilder()}
              >
                + Yangi kalkulyator
              </button>
            </div>
          </div>
          {error && (
            <div className="admin-alert" role="alert">
              {error}
            </div>
          )}
          {notice && (
            <div className="admin-success" role="status">
              <CheckCircle2 size={18} /> {notice}
            </div>
          )}
          {builderEditing === 'new' && (
            <div id="builder-new" className="inline-editor-anchor">
              <BuilderEditor
                categories={categories}
                today={serverDate}
                onSaved={load}
                onClose={() => setBuilderEditing(null)}
                onCategories={refreshCategories}
              />
            </div>
          )}
          <CalculatorTable
            calculators={allCalculators}
            showDeleted={showDeleted}
            setShowDeleted={setShowDeleted}
            busy={busy}
            onEdit={(c) => {
              edit(c)
              requestAnimationFrame(() =>
                document
                  .getElementById(`builder-${c.id}`)
                  ?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              )
            }}
            onAvailability={changeAvailability}
            onPreview={(c) => openBuilder(c.id, true)}
            onPublish={publishBuilder}
            renderEditor={(c) =>
              builderEditing === c.id ? (
                <div id={`builder-${c.id}`} className="inline-editor-anchor">
                  <BuilderEditor
                    key={`${c.id}-${builderPreview ? 'preview' : 'edit'}`}
                    calculator={c}
                    categories={categories}
                    today={serverDate}
                    onSaved={load}
                    onClose={() => setBuilderEditing(null)}
                    onCategories={refreshCategories}
                    startPreview={builderPreview}
                  />
                </div>
              ) : form && editingId === c.id ? (
                <div id={`builder-${c.id}`}>{legacyEditor}</div>
              ) : null
            }
          />

          <details className="catalog-history">
            <summary>
              <History size={17} /> Qoida va o‘zgarishlar tarixi
            </summary>
            <div className="admin-table-scroll">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>Kalkulyator / versiya</th>
                    <th>Sanadan</th>
                    <th>Davlat boji</th>
                    <th>BHM</th>
                    <th>Holat</th>
                    <th>Izoh</th>
                  </tr>
                </thead>
                <tbody>
                  {rules.map((rule) => (
                    <tr key={rule.id}>
                      <td>
                        {
                          allCalculators.find((c) => c.id === rule.service_id)
                            ?.name
                        }{' '}
                        · #{rule.id}
                      </td>
                      <td>{rule.effective_from}</td>
                      <td>{tariffSummary({ id: rule.service_id, rule })}</td>
                      <td>{money(rule.config.bhm_amount)} so‘m</td>
                      <td>
                        {rule.status === 'draft'
                          ? 'Qoralama'
                          : currentRuleIds.has(rule.id)
                            ? 'Amalda'
                            : rule.effective_from > serverDate
                              ? 'Rejalashtirilgan'
                              : 'Oldingi'}
                      </td>
                      <td>{rule.config.change_note}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="audit-section">
              {events.map((event) => (
                <p key={event.id}>
                  <time>{event.created_at}</time>
                  <span>
                    #{event.rule_id} · {event.action}
                  </span>
                </p>
              ))}
            </div>
          </details>
        </main>
      )}
    </div>
  )
}
