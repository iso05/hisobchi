import {agencies, grounds, exclusions, allowedExcess, civilBenefits, kinTypes} from './refund-options.js';
import {amountWords} from './amount-words.js';

export function refundLimit(mode, paidValue, dueValue) {
  if (!['full','overpaid'].includes(mode)) throw new Error('Avval qaytarish turini tanlang.');
  const paid=Number(paidValue);
  if (String(paidValue).trim()==='' || !Number.isSafeInteger(paid) || paid<1 || paid>1e12) throw new Error('To‘lagan summangizni butun raqam bilan kiriting.');
  if (mode==='full') return paid;
  const due=Number(dueValue);
  if (String(dueValue).trim()==='' || !Number.isSafeInteger(due) || due<0 || due>1e12) throw new Error('To‘lash kerak bo‘lgan summani butun raqam bilan kiriting.');
  if (paid<=due) throw new Error('Ortiqcha to‘lov yo‘q: to‘lagan summa kerakli summadan katta bo‘lishi kerak.');
  return paid-due;
}

export function refundAmounts(mode, paid, due, requestedValue) {
  const maximum = refundLimit(mode, paid, due);
  const requested = Number(requestedValue);
  if (!Number.isSafeInteger(requested) || requested < 1 || requested > maximum ||
      (mode === 'full' && requested !== maximum)) throw new Error('Invalid requested refund');
  return {paid:Number(paid), due:mode === 'full' ? 0 : Number(due), requested};
}

export const money = (value, locale='uz') => new Intl.NumberFormat(locale).format(value);

export function missingField(d,mode) {
  const agency=agencies[d.agency];
  if (!agency) return 'agency';
  if (mode==='full' ? !agency.cases.includes(d.reason) : !allowedExcess(d.agency).includes(d.reason)) return 'reason';
  const fields=['authority','name','address','phone','amount','requested','date','receipt','bank','account'];
  if (mode==='overpaid') {
    if (d.reason==='exemption' && !Object.hasOwn(civilBenefits,d.benefit)) return 'benefit';
    if (d.reason==='kin' && !Object.hasOwn(kinTypes,d.kin)) return 'kin';
    if (d.reason==='rate') fields.push('tariffClause','tariffPart');
    if (d.reason!=='exemption') fields.push('due');
  }
  return fields.find(k=>!String(d[k]??'').trim());
}

export function refundDraft(d, mode, lang='uz') {
  if (!['uz','ru'].includes(lang) || Object.hasOwn(exclusions,d.reason) || missingField(d,mode)) throw Error('Incomplete application');
  const ru=lang==='ru', idx=ru?1:0;
  const sums=refundAmounts(mode,d.amount,d.reason==='exemption'?0:d.due,d.requested);
  const fmt=n=>money(n,lang);
  const requested=fmt(sums.requested)+' ('+amountWords(sums.requested,lang)+')';
  const agency=agencies[d.agency], over=mode==='overpaid';
  const row=grounds[d.reason];
  const recipient=agency.recipient[idx].replace('%',()=>d.authority.trim());
  let purpose=agency.purpose[idx];
  if (d.reason==='3') purpose=ru?'за подачу жалобы в суд':'sudga shikoyat berish uchun';
  if (d.reason==='14') purpose=ru?'за подачу заявления о выдаче судебного приказа':'sud buyrug‘i berish haqida ariza bilan murojaat qilish uchun';
  const paymentDate=d.date.split('-').reverse().join('.');
  const payment=ru ? `Я уплатил(а) государственную пошлину ${purpose} в размере ${fmt(sums.paid)} сум (дата платежа: ${paymentDate}, платёжный документ № ${d.receipt}).` :
    `Men ${purpose} ${fmt(sums.paid)} so‘m miqdorida davlat boji to‘laganman (to‘lov sanasi: ${paymentDate}, to‘lov hujjati raqami: ${d.receipt}).`;
  let fact,condition,proof;
  if (over) {
    if (d.reason==='exemption') {
      fact=ru?`Моё требование относится к категории «${civilBenefits[d.benefit][idx]}». Согласно пункту ${d.benefit} части первой статьи 8 Закона «О государственной пошлине» я освобождён(а) от уплаты пошлины.`:
        `Talabim «${civilBenefits[d.benefit][idx]}» toifasiga kiradi. «Davlat boji to‘g‘risida»gi Qonun 8-moddasi birinchi qismining ${d.benefit}-bandiga ko‘ra, ushbu da’vo bo‘yicha davlat bojini to‘lashdan ozodman.`;
      if (d.appeal) fact+=ru?' Освобождение распространяется на подачу жалобы согласно пункту 29 постановления Пленума Верховного суда № 37 от 16.12.2024.':' Oliy sud Plenumining 2024-yil 16-dekabrdagi 37-son qarori 29-bandiga ko‘ra, bu imtiyoz shikoyat berishda ham qo‘llanadi.';
    } else if (d.reason==='kin') {
      fact=ru?`Транспортное средство передано родственнику собственника (категория: ${kinTypes[d.kin][idx]}). Согласно примечанию к подпункту «о» пункта 4 приложения к Закону «О государственной пошлине» подлежит уплате 5% установленной ставки, что составляет ${fmt(sums.due)} сум.`:
        `Transport vositasi mulkdorning qarindoshiga o‘tkazilgan (qarindoshligi: ${kinTypes[d.kin][idx]}). «Davlat boji to‘g‘risida»gi Qonun ilovasi 4-bandi «o» kichik bandi izohiga ko‘ra, belgilangan stavkaning 5 foizi, ya’ni ${fmt(sums.due)} so‘m to‘lanishi lozim edi.`;
    } else {
      fact=ru?`Согласно подпункту «${d.tariffPart}» пункта ${d.tariffClause} приложения к Закону «О государственной пошлине» следовало уплатить ${fmt(sums.due)} сум.`:
        `«Davlat boji to‘g‘risida»gi Qonun ilovasi ${d.tariffClause}-bandining «${d.tariffPart}» kichik bandiga ko‘ra, ${fmt(sums.due)} so‘m to‘lanishi lozim edi.`;
    }
    const excess = sums.paid - sums.due;
    const overpaid = fmt(excess)+' ('+amountWords(excess,lang)+')';
    fact+=ru?` В результате излишне уплачено ${overpaid} сум.`:` Natijada ${overpaid} so‘m ortiqcha to‘langan.`;
    condition=ru?'Согласно пункту 1 части первой статьи 18 указанного Закона излишне уплаченная сумма государственной пошлины подлежит возврату.':'Mazkur Qonunning 18-moddasi birinchi qismi 1-bandiga ko‘ra, ortiqcha to‘langan summa qaytarilishi lozim.';
    if(d.agency==='notary') proof=ru?'Копия нотариально удостоверенного документа.':'Notarial tasdiqlangan hujjat nusxasi.';
  } else {
    fact=row[lang].fact;
    if (d.orderRef?.trim()) fact+=' ('+d.orderRef.trim()+')';
    condition=ru?`Согласно пункту ${row.clause} части первой статьи 18 Закона Республики Узбекистан «О государственной пошлине», если ${row.ru.condition}, уплаченная пошлина подлежит возврату.`:
      `«Davlat boji to‘g‘risida»gi O‘zbekiston Respublikasi Qonunining 18-moddasi birinchi qismi ${row.clause}-bandiga ko‘ra, ${row.uz.condition}, to‘langan davlat boji qaytarilishi lozim.`;
    proof=row[lang].proof;
  }
  return [
    [recipient,(ru?'Заявитель: ':'Ariza beruvchi: ')+d.name,(ru?'Адрес: ':'Manzil: ')+d.address,(ru?'Телефон: ':'Telefon: ')+d.phone].join('\n'),
    ru?'ЗАЯВЛЕНИЕ':'ARIZA',
    ru?(over?'о возврате излишне уплаченной государственной пошлины':'о возврате уплаченной государственной пошлины'):(over?'Ortiqcha to‘langan davlat bojini qaytarish to‘g‘risida':'To‘langan davlat bojini qaytarish to‘g‘risida'),
    payment,fact,condition,
    ru?'На основании изложенного прошу:':'Yuqoridagilarga asoslanib, SO‘RAYMAN:',
    ru?`1. Подтвердить правомерность возврата уплаченной государственной пошлины в размере ${requested} сум и выдать мне соответствующую справку.\n2. Направить письменное уведомление в налоговый орган в установленном порядке.`:
      `1. To‘langan ${requested} so‘m miqdoridagi davlat bojini qaytarish qonuniy ekanligini tasdiqlab, bu haqda ma’lumotnoma berishingizni.\n2. Mablag‘ni qaytarish uchun davlat soliq organiga belgilangan tartibda yozma xabar yuborishingizni.`,
    [(ru?'Прошу перечислить возвращаемые средства по следующим реквизитам:':'Qaytariladigan mablag‘ni quyidagi hisob raqamiga o‘tkazishingizni so‘rayman:'),(ru?'Банк: ':'Bank nomi: ')+d.bank,(ru?'Номер счёта (карты): ':'Hisob (karta) raqami: ')+d.account].join('\n'),
    [(ru?'Приложения:':'Ilova:'),ru?'1. Копия платёжного документа.':'1. To‘lov hujjati (kvitansiya) nusxasi.',ru?'2. Копия документа, удостоверяющего личность.':'2. Shaxsni tasdiqlovchi hujjat nusxasi.',proof && '3. '+proof].filter(Boolean).join('\n'),
    (ru?'Дата: ':'Sana: ')+new Intl.DateTimeFormat('ru-RU').format(new Date()),
  ].join('\n\n');
}
