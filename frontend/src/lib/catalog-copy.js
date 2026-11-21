// Stable API keys keep the same answers when the visitor switches language.
import { plain } from './plain-language.js';

export const languages = ['uz', 'ru', 'en'];
export function words(lang, uz, ru, en) {
  return ({uz, ru, en})[lang] ?? uz;
}

function pairs(rows) {
  return Object.fromEntries(rows.trim().split('\n').map(row => {
    const [key, ru, en] = row.split('|');
    return [key, {ru, en}];
  }));
}

const services = pairs(`
Tezlikni oshirish jarimasi|Штраф за превышение скорости|Speeding fine
Svetofor va to‘xtash chizig‘i jarimasi|Штраф за сигнал светофора и стоп-линию|Signal and stop-line fine
notary_car|Продажа или обмен автомобиля|Vehicle sale or exchange
notary_property|Купля-продажа недвижимости|Real estate sale
notary_vehicle_power|Доверенность на автомобиль у нотариуса|Notarised vehicle power of attorney
notary_property_power|Доверенность на недвижимость|Real estate power of attorney
notary_lease|Заверение договора аренды|Notarisation of a lease
notary_inheritance|Свидетельство о наследстве|Inheritance certificate
court_civil|Взыскание денег в гражданском суде|Civil court money claim
court_economic|Денежный спор в экономическом суде|Economic court money claim
vehicle_power_electronic|Электронная доверенность на автомобиль|Electronic vehicle power of attorney
patent_application|Заявка на изобретение или полезную модель|Invention or utility model application
court_divorce|Расторжение брака через суд|Divorce through the courts
court_copies|Копии судебных документов|Copies of court documents
court_economic_filing|Заявление в экономический суд|Economic court application
court_special_proceeding|Особое производство в гражданском суде|Special proceedings in civil court
court_nonproperty|Неимущественный иск в гражданском суде|Non-property claim in civil court
Qarz shartnomasi|Договор займа|Loan agreement
`);

const fields = pairs(`
radar_speed|Скорость на радаре до вычета 5 км/ч|Recorded speed before the 5 km/h deduction
speed_limit|Ограничение скорости (км/ч)|Posted speed limit (km/h)
signal_action|Что произошло при запрещающем сигнале или жесте?|What happened at the stop signal or traffic officer’s stop instruction?
vehicle_type|Какой вид транспорта передают?|What type of vehicle is being transferred?
special_status|Доступные льготы|Available benefits
transaction_kind|Продажа или обмен?|Sale or exchange?
relative_type|Кем стороны приходятся друг другу?|How are the parties related?
bank_credit|Покупатель использует банковский кредит?|Is the purchase financed by a bank loan?
location|Где нотариус оформляет документ?|Where will the notarisation take place?
exemption_parties|У кого из сторон есть подтверждённая льгота?|Which parties have a documented exemption?
region|Где находится недвижимость?|Where is the property located?
transaction|Какую сделку вы оформляете?|Which transaction are you registering?
party_type|Среди сторон есть организация?|Is either party a legal entity?
operation|Что нужно сделать с договором?|What do you want to do with the agreement?
property_type|Какое имущество переходит по наследству?|What is being inherited?
certificate_kind|Какое свидетельство вы получаете?|What type of certificate do you need?
minor|Наследник несовершеннолетний?|Is the heir a minor?
lived_before|Наследник жил с наследодателем до его смерти?|Did the heir live with the deceased before their death?
registered|Наследник был зарегистрирован по этому адресу ко дню смерти?|Was the heir registered at this address on the date of death?
lives_after|Наследник продолжает жить в этом жилье?|Does the heir still live in this home?
joint_property|Это общая собственность супругов?|Was this property jointly owned by spouses?
estate_numerator|Доля имущества в наследстве — числитель|Share of the property in the estate — numerator
estate_denominator|Доля имущества в наследстве — знаменатель|Share of the property in the estate — denominator
share_numerator|Доля наследника — числитель|Heir’s share — numerator
share_denominator|Доля наследника — знаменатель|Heir’s share — denominator
claim_type|О чём ваш иск?|What are you claiming?
stage|На какой стадии дело?|At what stage is the case?
claim_amount|Какова сумма требования в сумах?|What amount is being claimed in UZS?
small_business|Заявитель — малый бизнес и дело касается его деятельности?|Is this a small business filing about its business activities?
duration|На какой срок нужна доверенность?|How long should the power of attorney last?
benefit_category|Какая льгота вам положена?|Which fee reduction applies?
object_type|На что подаётся заявка?|What are you applying to protect?
applicant_type|Кто подаёт заявку?|Who is applying?
object_count|Сколько изобретений или полезных моделей в заявке?|How many inventions or utility models are in this application?
description_pages|Сколько листов в описании изобретения?|How many sheets does the invention description contain?
individual_benefit|Какая льгота действует для заявителя?|Which individual applicant benefit applies?
legal_benefit|На каком основании организация получает льготу?|Which organisational benefit applies?
marriage|Какая ситуация применима к браку?|Which situation applies to the marriage?
division|Вы также просите суд разделить имущество?|Are you also asking the court to divide property?
court_kind|В каком суде запрашиваете копии?|Which court will issue the copies?
pages|Сколько всего страниц?|How many pages in total?
business_relief|Заявитель — малый бизнес и обращается по делу о своей деятельности?|Is this a small business applying about its business activities?
filing|О чём заявление?|What are you filing for?
fact|Что вы просите суд установить?|What do you want the court to establish?
subject|Чего касается требование?|What does the claim concern?
Qanday xizmat kerak?|Какое действие нужно оформить?|What would you like to do?
`);

const options = pairs(`
stop_line|Только заехал(а) за стоп-линию|Crossed the stop line only
passed_signal|Проехал(а) на запрещающий сигнал или жест|Drove through the stop signal or instruction
no|Нет|No
yes|Да|Yes
unsure|Не знаю|I don’t know
none|Ни одно из перечисленных оснований|None of the listed grounds
car|Автомобиль|Car
motorcycle|Мотоцикл, мотоколяска или моторная лодка|Motorcycle, motorised sidecar or motorboat
sale|Продажа|Sale
exchange|Обмен|Exchange
spouse|Супруг или супруга|Spouse
parent|Отец или мать|Parent
child|Сын или дочь|Child
spouse_parent|Родитель супруга или супруги|Spouse’s parent
child_spouse|Супруг или супруга ребёнка|Child’s spouse
grandchild|Внук или внучка|Grandchild
grandparent|Бабушка или дедушка|Grandparent
sibling|Брат или сестра|Sibling
nephew_niece|Племянник или племянница|Nephew or niece
relative_type.other|Другое лицо (в том числе родственники, не указанные выше)|Another person (including relatives not listed above)
office|В нотариальной конторе|At the notary’s office
outside|За пределами конторы|Outside the notary’s office
outreach|На выездном приёме в здании махалли|At an outreach appointment in the mahalla building
detention|Доверенность лица под стражей|Power of attorney of a person held in custody
one|Только одна сторона|One party only
both|Обе стороны имеют подтверждённое основание|Both parties have documented grounds
disability_organization|Общественное объединение людей с инвалидностью или учреждение из п. 4 ст. 11|Association of persons with disabilities or an institution covered by Article 11(4)
islamic_finance|Исламский банк или микрофинансовая организация приобретает имущество для продажи клиенту по стандартам исламского финансирования|Islamic bank or microfinance organisation acquiring the asset for resale to a client under Islamic finance standards
state_orphan_home|Государство купило вторичное жильё и оформляет его на ребёнка без попечения родителей|State-purchased existing housing registered to an orphan or a child without parental care
tashkent|Город Ташкент|Tashkent city
nukus|Город Нукус|Nukus city
capital|Областной центр|Regional capital
region.other|Другой населённый пункт|Other settlement
ordinary|Обычная купля-продажа|Ordinary sale
individual|Физическое лицо|Individual
legal|Юридическое лицо|Legal entity
party_type.individual|Обе стороны — физические лица|Both parties are individuals
party_type.legal|Хотя бы одна сторона — юридическое лицо|At least one party is a legal entity
certify|Удостоверить или изменить|Notarise or amend
cancel|Расторгнуть договор|Terminate the agreement
home|Жилой дом или квартира|Residential house or flat
real_estate|Другая недвижимость|Other real estate
vehicle|Транспортное средство|Vehicle
housing_coop|Пай в жилищном кооперативе|Housing cooperative share
deposit|Банковский вклад|Bank deposit
salary|Заработная плата|Wages
pension|Средства на личном накопительном пенсионном счёте|Personal funded pension account balance
government_bond|Государственные облигации|Government bonds
insurance|Сумма личного или имущественного страхования|Personal or property insurance proceeds
passenger_insurance|Обязательное страхование пассажира или имущества гражданина|Compulsory passenger or personal property insurance proceeds
copyright|Авторское право|Copyright
royalty|Авторское вознаграждение|Royalties
credit_certificate|Сертификат или аккредитив кредитной организации|Certificate or letter of credit issued by a credit institution
property_type.other|Иное имущество|Other property
certificate_kind.first|Первичное свидетельство|First certificate
partial|Свидетельство на часть имущества|Certificate for part of the property
remaining|Свидетельство на оставшуюся часть|Certificate for the remaining part
duty_death|Наследодатель погиб при исполнении служебного или гражданского долга|Deceased died performing official or civic duty
guardianship|У наследника хроническое психическое заболевание и установлена опека|Heir has a chronic mental illness and is under legally established guardianship
farmer|Наследник продолжает деятельность фермерского хозяйства и наследует его имущество|Heir continues the farm business and inherits its property
dehkan|Наследник продолжает деятельность дехканского хозяйства и наследует его имущество|Heir continues the dehkan farm and inherits its property
state_authority|Налоговый или финансовый орган оформляет наследство государства|Tax or finance authority registering state inheritance
debt|Долг или другое имущественное денежное требование|Debt or other monetary property claim
claim_type.salary|Требование работника о заработной плате|Employee’s wage claim
alimony|Взыскание алиментов|Maintenance payments
consumer|Иск потребителя о защите его прав|Claim to enforce consumer rights
health|Возмещение вреда от трудового увечья, повреждения здоровья или смерти кормильца|Compensation for workplace injury, harm to health or loss of a breadwinner
crime|Возмещение материального ущерба от преступления|Compensation for material damage caused by a crime
stage.first|Первое обращение в суд|First-instance filing
appeal|Апелляция, кассация или ревизия|Appeal, cassation or review
one_month|До одного месяца|Up to one month
six_months|Более месяца и до шести месяцев|Over one month and up to six months
three_years|Более шести месяцев и до трёх лет|Over six months and up to three years
disability|Инвалидность I или II группы|Group I or II disability
invention|Изобретение|Invention
utility|Полезная модель|Utility model
disability2|Инвалидность II группы|Group II disability
education|Учащийся, научный или научно-педагогический работник|Student, researcher or academic research and teaching staff
small_or_education|Малый бизнес либо аккредитованная образовательная или научная организация|Small business or an accredited educational or research organisation
marriage.first|Первый брак|First marriage
repeat|Повторный брак|Subsequent marriage
statutory|Супруг признан безвестно отсутствующим или недееспособным вследствие психического заболевания либо осуждён минимум на три года лишения свободы|Spouse legally declared missing or incapacitated due to mental illness, or sentenced to at least three years in prison
civil|Гражданский суд|Civil court
economic|Экономический суд|Economic court
nonproperty|Неимущественный иск|Non-property claim
insolvency|Возбуждение дела о неплатёжеспособности|Open insolvency proceedings
contract|Спор о заключении, изменении или расторжении хозяйственного договора|Dispute over entering into, amending or terminating a business contract
paternity|Признание или установление отцовства|Recognition or establishment of paternity
birth|Установление материнства или времени рождения ребёнка|Establish the child’s maternity or time of birth
gambling|Внесение лица в реестр лиц с игровой зависимостью|Enter a person in the register of persons with gambling dependency
fact.ordinary|Другое дело особого производства по общей ставке|Other special proceeding at the standard rate
lease|Изменение или расторжение договора найма жилья|Amend or terminate a residential lease
inventory|Исключение имущества из описи|Remove property from an inventory
subject.nonproperty|Иное неимущественное или не подлежащее оценке требование|Other non-property claim or claim that cannot be valued
Shartnomani bekor qilish|Расторгнуть договор|Terminate agreement
Shartnomani o‘zgartirish|Изменить договор|Amend agreement
Shartnomani tasdiqlash|Удостоверить договор|Certify agreement
`);

const categories = pairs(`
Yo‘l harakati jarimalari|Дорожные штрафы|Traffic fines
Notarial|Нотариус|Notary
Sud|Суды|Courts
Davlat xizmati|Госуслуги|Public services
Patent|Патенты|Patents
`);

function translated(dict, key, fallback, lang) {
  return lang === 'uz' ? plain(fallback) : dict[key]?.[lang] ?? dict[fallback]?.[lang] ?? fallback;
}
export const serviceName = (service, lang) => translated(services, service.id, service.name, lang);
export const categoryName = (name, lang) => translated(categories, name, name, lang);
export const questionName = (q, lang) => translated(fields, q.key, q.label, lang);
export const optionName = (q, o, lang) => translated(options, options[q.key+'.'+o.value] ? q.key+'.'+o.value : o.value, o.label, lang);
