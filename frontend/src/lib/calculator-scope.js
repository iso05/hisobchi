// These presets are displayed as scope conditions before a fee is calculated.
export function scopeFor(id, answers = {}) {
  switch (id) {
    case 'notary_car': return {damaged:'no'};
    case 'notary_property': return {transaction:'ordinary'};
    case 'court_civil': return {mixed_claims:'no', special_status:'none', ...(answers.claim_type && answers.claim_type !== 'debt' ? {stage:'first'} : {})};
    case 'court_economic': return {mixed_claims:'no', special_status:'none'};
    case 'vehicle_power_electronic': return {recipient:'other'};
    default: return {};
  }
}

export const scopeNotes = {
  notary_car:['YTHda shikastlanmagan transport uchun. Qarindoshlik va bank krediti birga kelgan bitim bu hisobga kirmaydi. Ayirboshlashda qiymati yuqori transportni tanlang.', 'Для транспорта без повреждений в ДТП. Расчёт исключает одновременное применение родства и банковского кредита. При обмене выберите более дорогое транспортное средство.', 'For vehicles without accident damage. Sales involving both kinship and bank credit are outside this calculator. For an exchange, select the higher-value vehicle.'],
  notary_property:['Odatdagi oldi-sotdi uchun. Toshkentdagi maxsus xorijiy xarid va undan keyingi qayta sotuv alohida tartibga kiradi.', 'Для обычной купли-продажи. Особые сделки иностранных покупателей в Ташкенте и последующая перепродажа имеют отдельные ставки.', 'For ordinary sales. Special foreign purchases in Tashkent and subsequent resales have separate rates.'],
  court_civil:['Bitta talab, summa so‘mda. Ro‘yxatdagi imtiyozli talablar birinchi bosqich uchun.', 'Одно требование в сумах. Перечисленные льготные иски рассчитаны для первой инстанции.', 'One claim in UZS. Listed exempt claims cover first-instance filings.'],
  court_economic:['Bitta pul talabi, summa so‘mda. Shikoyat bosqichida faqat umumiy stavka hisoblanadi.', 'Одно денежное требование в сумах. Для жалоб доступен общий тариф.', 'One money claim in UZS. Appeals cover the standard rate only.'],
  vehicle_power_electronic:['Qarindosh bo‘lmagan vakil uchun. Umumiy stavka yoki I–II guruh nogironligi bo‘yicha hisob.', 'Для представителя, не являющегося родственником. Общая ставка или льгота по инвалидности I–II группы.', 'For a representative who is not a relative. Covers the standard rate and the group I–II disability benefit.'],
  patent_application:['Bitta talabgor uchun ariza berish bosqichi. Bitta imtiyoz asosini tanlang.', 'Подача заявки одним заявителем. Выберите одно применимое основание для льготы.', 'Filing stage for a single applicant. Choose one applicable benefit.'],
  notary_inheritance:['Bitta mulk va bitta merosxo‘r ulushi uchun. Sud qarori bilan qayta berish va ishdagi baxtsiz hodisa sug‘urtasi alohida hisoblanadi.', 'Для одного объекта и доли одного наследника. Переоформление по решению суда и страхование от несчастного случая на работе рассчитываются отдельно.', 'For one asset and one heir’s share. Court-ordered reissues and workplace accident policies are outside this calculation.'],
};

export function formState(id, questions, entered) {
  const preset = scopeFor(id, entered);
  const excluded = new Set(['multiple','needs_review','registry','court_reissue','work_insurance']);
  const fields = questions.map(q => ({
    ...q, options: q.options?.filter(o => {
      if (id === 'notary_car' && q.key === 'bank_credit' && entered.relative_type && entered.relative_type !== 'other') return o.value !== 'yes';
      if (id === 'court_economic' && entered.stage === 'appeal' && q.key === 'small_business') return o.value === 'no';
      return id.startsWith('custom_') || !excluded.has(o.value);
    }),
  }));
  const answers = {...preset};
  for (const q of fields) {
    const v = entered[q.key];
    if (!(q.key in preset) && v !== undefined && v !== '' && (!q.options || q.options.some(o => o.value === v))) answers[q.key] = v;
  }
  const applies = q => Object.entries(q.when || {}).every(([k,values]) => values.includes(answers[k]));
  // A schema may display a dependent field before its controlling field.
  // Remove stale nested branches until the remaining answers are consistent.
  for (;;) {
    const stale = fields.filter(q => q.key in answers && !(q.key in preset) && !applies(q));
    if (!stale.length) break;
    for (const q of stale) delete answers[q.key];
  }
  return {answers,visible:fields.filter(q => !(q.key in preset) && applies(q))};
}
