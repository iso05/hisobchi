import { localImpact, saveLocalReport } from './impact.js';

const baseUrl = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '');
export const isDemo = !baseUrl;

export async function serverRequest(path, options = {}) {
  const response = await fetch(`${baseUrl || '/api/v1'}${path}`, { ...options, credentials: 'include', headers: { 'Content-Type': 'application/json' } });
  let data;
  try { data = await response.json(); } catch { throw new Error('Server javobi mos emas. Backend ishga tushganini tekshiring.'); }
  if (!response.ok) {
    const message = typeof data.detail === 'string' ? data.detail : Array.isArray(data.detail) ? data.detail.map(d => `${d.loc?.slice(-1)[0] || 'Maydon'}: ${d.msg}`).join('; ') : 'So‘rov bajarilmadi.';
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return data;
}

async function impactRequest(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(`${baseUrl}${path}`, { ...options, signal: controller.signal, headers: { 'Content-Type': 'application/json' } });
    if (!response.ok) throw new Error('Statistika xizmati javob bermadi. Keyinroq qayta urinib ko‘ring.');
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') throw new Error('Statistika xizmatidan javob kelmadi. Qayta urinib ko‘ring.');
    throw error;
  } finally { clearTimeout(timeout); }
}

export async function getImpact() {
  return isDemo ? localImpact() : impactRequest('/impact');
}

export async function saveBenefitReport(payload) {
  return isDemo ? saveLocalReport(payload) : impactRequest('/benefit-reports', { method: 'POST', body: JSON.stringify(payload) });
}
