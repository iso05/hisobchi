// Self-reported outcomes only. Generated answers never increment these totals.
const STORAGE_KEY = 'hisobchi:demo-benefit-reports:v1';

export function validateAmounts(standard, paid) {
  const empty = value => value === '' || value == null;
  if (empty(standard) && empty(paid)) return { standard_amount: null, paid_amount: null, saving_amount: null };
  if (empty(standard) || empty(paid)) throw new Error('Ikkala summani ham kiriting yoki ikkalasini bo‘sh qoldiring.');
  const parse = value => typeof value === 'number' ? value : Number(String(value).replace(/\s/g, ''));
  const before = parse(standard), after = parse(paid);
  if (![before, after].every(n => Number.isSafeInteger(n) && n >= 0 && n <= 1e15)) throw new Error('Summalarni manfiy bo‘lmagan butun so‘mda kiriting.');
  if (after > before) throw new Error('Amalda to‘langan boj imtiyozsiz bojdan katta bo‘lishi mumkin emas. Summalarni tekshiring.');
  return { standard_amount: before, paid_amount: after, saving_amount: before - after };
}

export function summarizeReports(reports) {
  const known = reports.filter(r => r.saving_amount != null);
  return { confirmed_reports: reports.length, reports_with_amount: known.length, reported_saving_amount: known.reduce((sum, r) => sum + r.saving_amount, 0), currency: 'UZS', scope: 'browser_demo', is_demo: true };
}

function readReports(storage) {
  const parsed = JSON.parse(storage.getItem(STORAGE_KEY) || '[]');
  if (!Array.isArray(parsed)) throw new Error('Saqlangan statistika formati buzilgan.');
  const seen = new Set();
  return parsed.map(r => {
    if (!r || typeof r.calculation_id !== 'string' || seen.has(r.calculation_id)) throw new Error('Saqlangan tasdiq ma’lumotlari mos emas.');
    seen.add(r.calculation_id);
    return { ...r, ...validateAmounts(r.standard_amount, r.paid_amount) };
  });
}

export function localImpact(storage = localStorage) {
  return summarizeReports(readReports(storage));
}

export function saveLocalReport(payload, storage = localStorage) {
  const reports = readReports(storage);
  const existing = reports.find(r => r.calculation_id === payload.calculation_id);
  if (existing) return { report: existing, impact: summarizeReports(reports) };
  if (typeof payload.calculation_id !== 'string' || !payload.calculation_id) throw new Error('Hisob identifikatori topilmadi.');
  const report = { id: payload.calculation_id, calculation_id: payload.calculation_id, service_id: payload.service_id, ...validateAmounts(payload.standard_amount, payload.paid_amount), reported_at: new Date().toISOString(), is_demo: true, verification: 'self_reported' };
  const updated = [...reports, report];
  storage.setItem(STORAGE_KEY, JSON.stringify(updated));
  return { report, impact: summarizeReports(updated) };
}
