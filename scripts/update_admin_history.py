from pathlib import Path
path=Path(__file__).resolve().parents[1]/'frontend/src/Admin.jsx'
text=path.read_text(encoding='utf-8')
text=text.replace('<th>Versiya</th><th>Sanadan</th><th>Davlat boji</th><th>Qarindoshga</th>','<th>Kalkulyator / versiya</th><th>Sanadan</th><th>Davlat boji</th><th>BHM</th>')
text=text.replace('<td>#{rule.id}</td>','<td>{calculators.find(c => c.id === rule.service_id)?.name} · #{rule.id}</td>')
text=text.replace('<td>{rule.config.car_bhm_multiplier} BHM</td><td>{rule.config.relative_pay_percent}%</td>','<td>{tariffSummary({id:rule.service_id,rule})}</td><td>{money(rule.config.bhm_amount)} so‘m</td>')
text=text.replace("rule.id === current?.id ? 'Amalda'", "currentRuleIds.has(rule.id) ? 'Amalda'")
path.write_text(text,encoding='utf-8')
