import FieldInput from './FieldInput.jsx';
import React, { useEffect, useState } from 'react';
import { CheckCircle2, CircleHelp, HeartHandshake, LoaderCircle, Wallet } from 'lucide-react';
import { validateAmounts } from '../lib/impact.js';

const money = value => new Intl.NumberFormat('uz-UZ').format(value);

export function ImpactSummary({ impact, loading, error, onRetry }) {
  return <section className="impact-section" aria-label="Imtiyozlardan foydalanish statistikasi">
    <div className="impact-title"><span className="square-icon"><HeartHandshake size={22} /></span><div><h2>Imtiyozdan amaliy foydagacha</h2><p>Foydalanuvchilar tasdiqlagan natijalar</p></div><span className="small-badge">{impact?.scope === 'global' ? 'Umumiy statistika' : 'Shu brauzer · demo'}</span></div>
    {error ? <div className="impact-error" role="alert"><p>{error}</p><button className="outline-button" onClick={onRetry}>Qayta urinish</button></div> : <div className="impact-metrics" aria-live="polite" aria-busy={loading}>
      <div><span><CheckCircle2 size={16} /> Tasdiqlangan foydalanish</span><strong>{loading ? '…' : money(impact?.confirmed_reports || 0)} <small>ta</small></strong><p>“Imtiyozdan foydalandim” deb bildirilgan</p></div>
      <div><span><Wallet size={16} /> Bildirilgan tejalgan summa</span><strong>{loading ? '…' : money(impact?.reported_saving_amount || 0)} <small>so‘m</small></strong><p>{loading ? 'Ma’lumot olinmoqda' : `${impact?.reports_with_amount || 0} ta summasi ko‘rsatilgan tasdiq asosida`}</p></div>
    </div>}
    <p className="impact-note">{impact?.scope === 'global' ? 'Bu raqamlar foydalanuvchilar bildirgan natijalar; to‘lov tizimi orqali tekshirilmagan.' : 'Demo ma’lumotlari shu brauzerda saqlanadi. Haqiqiy umumiy statistika emas.'} Har bir xabar yoki hisob avtomatik ravishda tejalgan pul deb sanalmaydi.</p>
  </section>;
}

export function BenefitReport({ result, calculationId, onSave }) {
  const [open, setOpen] = useState(false);
  const [saved, setSaved] = useState(null);
  const [standard, setStandard] = useState('');
  const [paid, setPaid] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    setOpen(false); setSaved(null); setError('');
    setStandard(result.standard_amount == null ? '' : String(result.standard_amount));
    setPaid(result.standard_amount == null || result.payable_amount == null ? '' : String(result.payable_amount));
  }, [result, calculationId]);
  if (!['exempt', 'discounted'].includes(result.status)) return null;

  async function confirm(event) {
    event.preventDefault();
    if (busy) return;
    setError('');
    let amounts;
    try { amounts = validateAmounts(standard, paid); }
    catch (e) { setError(e.message); return; }
    setBusy(true);
    try {
      const response = await onSave({ calculation_id: calculationId, service_id: result.service_id, standard_amount: amounts.standard_amount, paid_amount: amounts.paid_amount });
      setSaved(response.report);
    } catch (e) { setError(e.message === 'Failed to fetch' ? 'Statistika xizmatiga ulanib bo‘lmadi. Tasdiq saqlanmadi.' : e.message); }
    finally { setBusy(false); }
  }

  if (saved) return <div className="report-saved" role="status"><CheckCircle2 size={22} /><div><h3>Tasdiqingiz saqlandi</h3><p>{saved.saving_amount == null ? 'Foydalanish soni qo‘shildi. Summa noma’lum bo‘lgani uchun tejash hisobiga qo‘shilmadi.' : `${money(saved.saving_amount)} so‘m tejash foydalanuvchi bildirgan natija sifatida qo‘shildi.`}</p></div></div>;
  return <section className="benefit-report" aria-label="Imtiyozdan foydalanganlikni bildirish"><h3>Imtiyozdan foydalandingizmi?</h3><p>To‘lov yoki murojaatni amalga oshirgach, natijangizni bildiring.</p>
    {!open ? <button className="primary-button full-width" onClick={() => setOpen(true)}>{result.status === 'exempt' ? 'Imtiyozdan foydalandim' : 'Imtiyoz bilan to‘ladim'}</button> : <form onSubmit={confirm}>
      <div className="report-inputs"><label>Imtiyozsiz davlat boji <span>so‘m</span><FieldInput type="number" min={0} step={1} value={standard} onValueChange={value => setStandard(value)} placeholder="Masalan: 800 000" disabled={busy} /></label><label>Amalda to‘lagan davlat boji <span>so‘m</span><FieldInput type="number" min={0} step={1} value={paid} onValueChange={value => setPaid(value)} placeholder="Ozod bo‘lsangiz: 0" disabled={busy} /></label></div>
      <p className="report-hint"><CircleHelp size={14} /> Summalarni bilmasangiz, ikkala maydonni ham bo‘sh qoldiring. Faqat foydalanish soni qayd etiladi.</p>
      {error && <p className="report-error" role="alert">{error}</p>}
      <div className="report-actions"><button type="button" className="outline-button" onClick={() => setOpen(false)} disabled={busy}>Bekor qilish</button><button type="submit" className="primary-button" disabled={busy}>{busy ? <><LoaderCircle size={16} className="spin" /> Saqlanmoqda</> : 'Ha, foydalandim — tasdiqlash'}</button></div>
      <p className="report-disclaimer">Bu siz bildirgan natija. Bir hisob faqat bir marta sanaladi.{result.is_demo ? ' Demo tasdig‘i haqiqiy umumiy statistikaga kirmaydi.' : ''}</p>
    </form>}
  </section>;
}
