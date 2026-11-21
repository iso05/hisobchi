// Display only. Actual fee computation stays in the Python backend.
export function tariffSummary(calculator) {
  const rule = calculator.rule?.config;
  if (!rule) return 'Qoida kiritilmagan';
  const p = rule.parameters || {};
  switch (calculator.id) {
    case 'notary_car': return `${rule.car_bhm_multiplier} BHM`;
    case 'notary_property': return `${p.other_bhm}–${p.center_bhm} BHM / maxsus`;
    case 'notary_vehicle_power':
    case 'notary_property_power': return `${p.relative_bhm} / ${p.other_bhm} BHM`;
    case 'notary_lease': return `${p.relative_bhm} / ${p.individual_bhm} / ${p.legal_bhm} BHM`;
    case 'notary_inheritance': return `${p.other_bhm} / ${p.real_vehicle_bhm} BHM × ulush`;
    case 'court_civil':
    case 'court_economic': return `${p.claim_percent}% · kamida ${p.minimum_bhm} BHM`;
    case 'vehicle_power_electronic': return `${p.base_bhm} BHM × muddat ulushi`;
    case 'patent_application': return `${p.individual_base_bhm} / ${p.legal_base_bhm} BHM + qo‘shimcha`;
    default: return 'Shartlarga qarab';
  }
}

export function benefitSummary(calculator) {
  const rule = calculator.rule?.config;
  if (!rule) return [];
  if (calculator.id === 'notary_car') return [{label:'Qarindoshga',value:`${rule.relative_pay_percent}% to‘lanadi`},{label:'Bank krediti',value:`${rule.bank_pay_percent}% to‘lanadi`}];
  const percentFields = calculator.parameters.filter(p => p.unit === '%');
  if (percentFields.length) return percentFields.map(field => ({label:field.label,value:`${rule.parameters[field.key]}%`}));
  return [{label:'Imtiyoz va istisnolar',value:calculator.id === 'notary_inheritance' ? 'Voyaga yetmagan / 11-modda' : 'Qarindoshlik / maxsus holat'}];
}
