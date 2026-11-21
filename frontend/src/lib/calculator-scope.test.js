import assert from 'node:assert/strict';
import test from 'node:test';
import {formState} from './calculator-scope.js';
import {optionName, questionName} from './catalog-copy.js';

const benefit = {key:'special_status',label:'Mavjud imtiyozlar',type:'choice', options:[{value:'none',label:'Imtiyoz yo‘q'},{value:'unsure',label:'Bilmayman'}]};
test('an earlier inheritance field remains visible when a later answer activates it',()=>{
  const minor = {key:'minor',when:{special_status:['none','unsure']},options:[{value:'yes'}]};
  const {visible,answers}=formState('notary_inheritance',[minor,benefit],{minor:'yes',special_status:'unsure'});
  assert.equal(visible.length,2);
  assert.equal(answers.minor,'yes');
  assert.equal(answers.special_status,'unsure');
});
test('out-of-scope answers do not survive a change of court stage',()=>{
  const stage = {key:'stage',options:[{value:'first'},{value:'appeal'}]};
  const business = {key:'small_business',options:[{value:'yes'},{value:'no'}]};
  const state = formState('court_economic',[stage,business],{stage:'appeal',small_business:'yes'});
  assert.equal(state.answers.small_business,undefined);
  assert.deepEqual(state.visible[1].options.map(o=>o.value),['no']);
});
test('unknown benefit and other relatives have a label in all three languages',()=>{
  assert.deepEqual(['uz','ru','en'].map(l=>questionName(benefit,l)),['Mavjud imtiyozlar','Доступные льготы','Available benefits']);
  assert.deepEqual(['uz','ru','en'].map(l=>optionName(benefit,benefit.options[1],l)),['Bilmayman','Не знаю','I don’t know']);
  const other = {value:'other',label:'Boshqa shaxs (shu jumladan, yuqorida ko‘rsatilmagan qarindoshlar)'};
  assert.match(optionName({key:'relative_type'},other,'ru'),/родственники/);
  assert.match(optionName({key:'relative_type'},other,'en'),/relatives not listed/);
});
