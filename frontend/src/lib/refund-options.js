import grounds from './refund-grounds.json' with {type:'json'};
export {grounds};
const courts = ['2-court','3','4','5','6','7','8','9','9-1','10','11','13','14','14-1'];
export const agencies = {
  civil: {names:['Fuqarolik sudi','Гражданский суд','Civil court'],cases:courts, recipient:['Fuqarolik ishlari bo‘yicha % sudi raisiga','Председателю суда по гражданским делам (%)'], purpose:['sudga murojaat qilish uchun','за обращение в суд']},
  economic:{names:['Iqtisodiy sud','Экономический суд','Economic court'],cases:courts,recipient:['% iqtisodiy sudi raisiga','Председателю экономического суда (%)'],purpose:['iqtisodiy sudga murojaat qilish uchun','за обращение в экономический суд']},
  administrative:{names:['Ma’muriy sud','Административный суд','Administrative court'],cases:['2-court','3','4','5','6','7','10','13'],recipient:['% ma’muriy sudi raisiga','Председателю административного суда (%)'],purpose:['ma’muriy sudga murojaat qilish uchun','за обращение в административный суд']},
  notary:{names:['Notarius','Нотариус','Notary'],cases:['2-notary'],recipient:['% notariusiga','Нотариусу (%)'],purpose:['notarial harakatni amalga oshirish uchun','за совершение нотариального действия']},
  registry:{names:['FHDYO','ЗАГС','Civil registry'],cases:['12'],recipient:['% FHDYO bo‘limi mudiriga','Руководителю отдела ЗАГС (%)'],purpose:['nikohdan ajratishni qayd etish uchun','за регистрацию расторжения брака']},
  migration:{names:['Migratsiya organi','Миграционный орган','Migration authority'],cases:['15'],recipient:['% migratsiya va fuqarolikni rasmiylashtirish bo‘limi boshlig‘iga','Начальнику отдела миграции и оформления гражданства (%)'],purpose:['xorijga chiqish hujjatini olish uchun','за получение документа на право выезда за границу']},
  other:{names:['Boshqa organ (masalan, DXM)','Другой орган (например, центр госуслуг)','Other authority (e.g. public service centre)'],cases:[],recipient:['% rahbariga','Руководителю организации (%)'],purpose:['davlat xizmatidan foydalanish uchun','за предоставление государственной услуги']},
};
export const exclusions = {
  reduced:['Da’vo summasi kamaytirildi','Размер требования уменьшен','Claim amount reduced'],
  withdrawn:['Da’vodan voz kechildi yoki kelishuv bitimi tuzildi','Отказ от иска или мировое соглашение','Claim withdrawn or settlement reached'],
  cancelled:['Sud buyrug‘i bekor qilindi','Судебный приказ отменён','Court order cancelled'],
  rejected:['Sud da’voni rad etdi','Суд отказал в удовлетворении иска','Claim dismissed on its merits'],
};
export const excessTypes = {
  exemption:['Fuqarolik sudida bojdan ozod qilingan da’vo','Освобождение от пошлины в гражданском суде','Exempt civil court claim'],
  rate:['Stavka noto‘g‘ri olingan','Применена неверная ставка','Incorrect rate used'],
  kin:['Transportni qarindoshga o‘tkazish chegirmasi','Передача транспорта родственнику','Vehicle transfer to an eligible relative'],
};
export const civilBenefits = {
  1:['Ish haqi yoki mehnat nizosi','Требования работника по трудовому спору','Wage or employment claim'],
  2:['Aliment undirish','Взыскание алиментов','Maintenance claim'],3:['Mehnatda mayiblik, sog‘liqqa zarar yoki boquvchi vafoti','Вред здоровью или смерть кормильца','Injury or loss of a breadwinner'],
  4:['Qonunga xilof hukm yoki jazo tufayli zarar','Вред от незаконного осуждения или наказания','Damage from unlawful conviction or punishment'],
  5:['Jinoyat tufayli moddiy zarar','Материальный ущерб от преступления','Material damage caused by a crime'],
  10:['Iste’molchi huquqi buzilishi','Нарушение прав потребителя','Consumer rights claim'],
};
export const kinTypes = {
  spouse:['Eri yoki xotini','Супруг или супруга','Spouse'],parent:['Ota-onasi','Родители','Parent'],
  inlaw:['Er yoki xotinining ota-onasi','Родители супруга','Spouse’s parent'],child:['Farzandi','Дети','Child'],
  childSpouse:['Farzandining eri yoki xotini','Супруг ребёнка','Child’s spouse'],grandchild:['Nabirasi','Внуки','Grandchild'],
  grandparent:['Buvisi yoki buvasi','Бабушка или дедушка','Grandparent'],sibling:['Aka-ukasi yoki opa-singlisi','Братья и сёстры','Sibling'],
};
export const languageIndex = lang=>({uz:0,ru:1,en:2})[lang];
export function allowedExcess(agency) {
  return ['rate',...(agency==='civil'?['exemption']:[]),...(agency==='notary'?['kin']:[])];
}
export function clauseChoices(agency,mode) {
  if (!agencies[agency]) return [];
  return mode==='overpaid' ? allowedExcess(agency) : [...agencies[agency].cases,...(agency==='civil'?Object.keys(exclusions):[])];
}
