import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateAmounts, saveLocalReport, localImpact } from './impact.js';

const memory = () => { const values = new Map(); return { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }; };
test('unconfirmed calculations never create stats', () => {
  assert.deepEqual(localImpact(memory()), { confirmed_reports: 0, reports_with_amount: 0, reported_saving_amount: 0, currency: 'UZS', scope: 'browser_demo', is_demo: true });
});
test('reported actual payments produce a difference, including exemption zero', () => {
  assert.deepEqual(validateAmounts('800 000', '400000'), { standard_amount: 800000, paid_amount: 400000, saving_amount: 400000 });
  assert.equal(validateAmounts('800000', '0').saving_amount, 800000);
});
test('unknown saving stays unknown and increases only use count', () => {
  const storage = memory();
  const result = saveLocalReport({ calculation_id: 'a', service_id: 'court', standard_amount: null, paid_amount: null }, storage);
  assert.equal(result.report.saving_amount, null);
  assert.equal(result.impact.confirmed_reports, 1);
  assert.equal(result.impact.reports_with_amount, 0);
  assert.equal(result.impact.reported_saving_amount, 0);
});
test('repeated confirmation of same calculation does not double count', () => {
  const storage = memory(), payload = { calculation_id: 'a', service_id: 'court', standard_amount: 800000, paid_amount: 0 };
  saveLocalReport(payload, storage);
  saveLocalReport(payload, storage);
  assert.equal(localImpact(storage).confirmed_reports, 1);
  assert.equal(localImpact(storage).reported_saving_amount, 800000);
});
test('separate reports persist and sum their known savings only', () => {
  const storage = memory();
  saveLocalReport({ calculation_id: 'a', service_id: 'court', standard_amount: 800000, paid_amount: 0 }, storage);
  saveLocalReport({ calculation_id: 'b', service_id: 'vehicle_power', standard_amount: 200000, paid_amount: 100000 }, storage);
  saveLocalReport({ calculation_id: 'c', service_id: 'court' }, storage);
  const totals = localImpact(storage);
  assert.equal(totals.confirmed_reports, 3);
  assert.equal(totals.reports_with_amount, 2);
  assert.equal(totals.reported_saving_amount, 900000);
});
test('invalid amounts and missing pairs are rejected', () => {
  for (const pair of [['100', '200'], ['100', ''], ['', '0'], ['-1', '0'], ['1.5', '0'], ['abc', '0'], [Infinity, 0]]) assert.throws(() => validateAmounts(...pair));
});
test('unavailable storage is a save failure, not a successful report', () => {
  const storage = { getItem: () => null, setItem: () => { throw new Error('Quota exceeded'); } };
  assert.throws(() => saveLocalReport({ calculation_id: 'a', service_id: 'court' }, storage));
});
