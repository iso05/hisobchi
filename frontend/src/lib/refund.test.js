import test from 'node:test';
import assert from 'node:assert/strict';
import {refundAmounts,refundDraft,missingField} from './refund.js';

import {grounds,agencies,exclusions} from './refund-options.js';
import {amountWords} from './amount-words.js';
const data={agency:'civil',bank:'Test Bank',account:'0001',address:'Test',phone:'12345',reason:'rate',tariffClause:'1',tariffPart:'a',authority:'Tashkilot',name:'Namuna arizachi',service:'Notarius xizmati',amount:'600000',requested:'160000',due:'440000',receipt:'DEMO-001',date:'2026-11-01',situation:'Keragidan ko‘p to‘ladim.'};

test('full refund requests the paid amount',()=>{
  assert.deepEqual(refundAmounts('full','440000','','440000'),{paid:440000,due:0,requested:440000});
});
test('overpayment requests only the excess, including a zero lawful fee',()=>{
  assert.deepEqual(refundAmounts('overpaid','600000','440000','160000'),{paid:600000,due:440000,requested:160000});
  assert.equal(refundAmounts('overpaid','440000','0','440000').requested,440000);
});
test('missing selection, invalid money and non-excess payments cannot generate a refund',()=>{
  for(const [mode,paid,due] of [['','600000','440000'],['full','',''],['full','-1',''],['full','1.5',''],['overpaid','600000',''],['overpaid','440000','440000'],['overpaid','100','200'],['overpaid','600000','-1']]) assert.throws(()=>refundAmounts(mode,paid,due,1));
});
test('overpayment uses the difference in figures and words in both languages',()=>{
  const uz=refundDraft(data,'overpaid');
  assert.match(uz,/bir yuz oltmish ming/);
  assert.match(uz,/ilovasi 1-bandining «a»/);
  assert.match(uz,/18-moddasi birinchi qismi 1-bandiga/);
  const ru=refundDraft(data,'overpaid','ru');
  assert.match(ru,/сто шестьдесят тысяч/);
  assert.match(ru,/Номер счёта/);
});
test('all allowed agency and case pairs supply statutory text and the right enclosure',()=>{
  for (const [agency,a] of Object.entries(agencies)) for (const reason of a.cases) for (const lang of ['uz','ru']) {
    const d={...data,agency,reason,requested:data.amount};
    const letter=refundDraft(d,'full',lang);
    assert.ok(letter.includes(grounds[reason][lang].condition));
    assert.equal(letter.includes('3. '+grounds[reason][lang].proof),Boolean(grounds[reason][lang].proof));
    assert.ok(!letter.includes('undefined'));
  }
});
test('invalid cases, exclusions and missing bank details cannot produce a letter',()=>{
  for (const reason of Object.keys(exclusions)) assert.throws(()=>refundDraft({...data,reason},'full'));
  assert.throws(()=>refundDraft({...data,agency:'registry',reason:'14'},'full'));
  assert.equal(missingField({...data,bank:''},'overpaid'),'bank');
});
test('special overpayments carry their own legal basis and amount',()=>{
  assert.match(refundDraft({...data,reason:'exemption',benefit:'2',appeal:true},'overpaid'),/olti yuz ming/);
  assert.match(refundDraft({...data,agency:'notary',reason:'kin',kin:'child'},'overpaid','ru'),/5%/);
  assert.throws(()=>refundDraft({...data,agency:'notary',reason:'exemption',benefit:'2'},'overpaid'));
});
test('amount words cover currency limits, teens and Russian thousands',()=>{
  assert.equal(amountWords(22021,'ru'),'двадцать две тысячи двадцать один');
  assert.equal(amountWords(11000,'ru'),'одиннадцать тысяч');
  assert.equal(amountWords(1e12,'uz'),'bir trillion');
});

test('requested sum is explicit and bounded, and does not change the recorded overpayment',()=>{
  for(const requested of ['',0,-1,0.5,160001]) {
    assert.throws(()=>refundDraft({...data,requested},'overpaid'));
  }
  assert.throws(()=>refundDraft({...data,agency:'registry',reason:'12',requested:550000},'full'));
  for(const [lang,excess,requested] of [['uz','bir yuz oltmish ming','yuz ming'],['ru','сто шестьдесят тысяч','сто тысяч']]) {
    const letter=refundDraft({...data,requested:'100000'},'overpaid',lang);
    const [facts,request]=letter.split(lang==='ru'?'На основании изложенного':'Yuqoridagilarga asoslanib');
    assert.ok(facts.includes(excess));
    assert.ok(request.includes(requested));
  }
});
