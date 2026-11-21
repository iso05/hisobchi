"""Declarative calculator definitions. No user supplied code or eval."""
import hashlib
import json
import re
from datetime import date
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator

ICONS = ['calculator','car','house','key','file','handshake','landmark','scale','briefcase','phone','lightbulb','wallet','building','shield','coins','book']
IDENTIFIER = r'^[a-z][a-z0-9_]{0,59}$'


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Condition(Strict):
    field: str = Field(pattern=IDENTIFIER)
    op: Literal['eq','ne','gt','gte','lt','lte'] = 'eq'
    value: str = Field(max_length=300)


class Effect(Strict):
    operation: Literal['none','replace','add','multiply','exempt'] = 'none'
    unit: Literal['bhm','percent','fixed','number'] = 'bhm'
    value: Decimal = Field(default=Decimal(0), ge=0, le=10**12, decimal_places=6)
    basis: Literal['initial','current','bhm','field'] = 'initial'
    field: str = ''
    times_input: bool = False


class Option(Strict):
    value: str = Field(pattern=IDENTIFIER)
    label: str = Field(min_length=1,max_length=200)
    effect: Effect = Field(default_factory=Effect)


class Factor(Strict):
    key: str = Field(pattern=IDENTIFIER)
    label: str = Field(min_length=1,max_length=250)
    type: Literal['choice','number','text'] = 'choice'
    required: bool = True
    help: str = Field(default='',max_length=600)
    minimum: Decimal = Field(default=Decimal(0),ge=0,le=10**15)
    maximum: Decimal = Field(default=Decimal(10**12),ge=0,le=10**15)
    options: list[Option] = Field(default_factory=list,max_length=60)
    effect: Effect = Field(default_factory=Effect)
    when: dict[str,list[str]] = Field(default_factory=dict,max_length=1)


class Rule(Strict):
    label: str = Field(min_length=1,max_length=200)
    conditions: list[Condition] = Field(min_length=1,max_length=12)
    effect: Effect


class Source(Strict):
    title: str = Field(min_length=1,max_length=250)
    url: str = Field(max_length=3000)
    find_text: str = Field(default='',max_length=600)
    section: Literal['auto','appendix','notarial','civil','economic','administrative','registry','custom'] = 'auto'

    @field_validator('url')
    @classmethod
    def official(cls, url):
        p = urlsplit(url)
        if p.scheme != 'https' or p.hostname not in {'lex.uz','www.lex.uz'} or p.username or p.password or p.port:
            raise ValueError('Manba https://lex.uz/ havolasi bo‘lishi kerak.')
        return url


class Definition(Strict):
    name: str = Field(min_length=2,max_length=180)
    category: str = Field(min_length=2,max_length=90)
    icon: str = 'calculator'
    description: str = Field(default='',max_length=600)
    bhm_amount: int = Field(default=440000,ge=1,le=10**9,strict=True)
    effective_from: date
    base: Effect = Field(default_factory=lambda:Effect(operation='replace',unit='bhm',value=1))
    combine: Literal['sequence','sum'] = 'sequence'
    factors: list[Factor] = Field(default_factory=list,max_length=40)
    rules: list[Rule] = Field(default_factory=list,max_length=40)
    minimum: Decimal | None = Field(default=None,ge=0,le=10**15)
    minimum_unit: Literal['bhm','fixed'] = 'bhm'
    maximum: Decimal | None = Field(default=None,ge=0,le=10**15)
    maximum_unit: Literal['bhm','fixed'] = 'bhm'
    sources: list[Source] = Field(default_factory=list,max_length=25)

    @model_validator(mode='after')
    def coherent(self):
        if self.icon not in ICONS:
            raise ValueError('Ro‘yxatdagi ikonkani tanlang.')
        keys={f.key:f for f in self.factors}
        if len(keys)!=len(self.factors):
            raise ValueError('Omil kalitlari takrorlanmasin.')
        def effect(e, owner=None):
            if e.basis=='field' and (e.field not in keys or keys[e.field].type!='number'):
                raise ValueError('Hisoblash asosi uchun raqamli omilni tanlang.')
            if e.times_input and (owner is None or owner.type!='number'):
                raise ValueError('Kiritilgan songa ko‘paytirish faqat raqamli omil uchun.')
            if e.operation=='multiply' and e.unit not in {'number','percent'}:
                raise ValueError('Ko‘paytirishda oddiy son yoki foizni tanlang.')
            if e.operation in {'replace','add'} and e.unit=='number':
                raise ValueError('Summa uchun BHM, foiz yoki so‘mni tanlang.')
        if self.base.operation!='replace' or self.base.times_input or self.base.basis in {'current','initial'} and self.base.unit=='percent':
            raise ValueError('Boshlang‘ich boj: BHM, so‘m yoki raqamli omildan foiz bo‘lsin.')
        effect(self.base)
        previous={}
        for f in self.factors:
            if f.minimum>f.maximum:
                raise ValueError('Omilning eng kam qiymati eng ko‘p qiymatdan katta.')
            if f.type=='choice' and (not f.options or len({o.value for o in f.options})!=len(f.options)):
                raise ValueError('Tanlash omilida takrorlanmagan variantlar bo‘lsin.')
            for dependency,values in f.when.items():
                if dependency not in previous or previous[dependency].type!='choice' or not values or set(values)-{o.value for o in previous[dependency].options}:
                    raise ValueError('Savol sharti oldingi tanlash omilining variantiga bog‘lansin.')
            if f.type=='text' and f.effect.operation!='none':
                raise ValueError('Matn maydoniga arifmetik amal berilmaydi; shartli qoidadan foydalaning.')
            effect(f.effect,f)
            for o in f.options:
                effect(o.effect,f)
            previous[f.key]=f
        for r in self.rules:
            for c in r.conditions:
                if c.field not in keys:
                    raise ValueError('Qoida omili topilmadi.')
                f=keys[c.field]
                if c.op not in {'eq','ne'} and f.type!='number':
                    raise ValueError('Solishtirish uchun raqamli omil kerak.')
                if f.type=='number':
                    try:
                        if not Decimal(c.value).is_finite(): raise ValueError()
                    except Exception:
                        raise ValueError('Shart qiymati chekli son bo‘lsin.')
                if f.type=='choice' and c.value not in {o.value for o in f.options}:
                    raise ValueError('Qoida varianti topilmadi.')
            effect(r.effect)
        low=self.minimum*(self.bhm_amount if self.minimum_unit=='bhm' else 1) if self.minimum is not None else None
        high=self.maximum*(self.bhm_amount if self.maximum_unit=='bhm' else 1) if self.maximum is not None else None
        if low is not None and high is not None and low>high:
            raise ValueError('Eng kam boj eng ko‘p bojdan oshmasin.')
        return self


def digest(definition):
    return hashlib.sha256(definition.model_dump_json().encode()).hexdigest()


def service(service_id, definition):
    return {'id':service_id,'name':definition.name,'category':definition.category,'icon':definition.icon,'description':definition.description,'scope':definition.description or 'Admin sozlagan davlat boji hisobi.','review_note':'','dynamic':True}


def questions(definition):
    return [{'key':f.key,'label':f.label,'type':f.type,'required':f.required,'help':f.help,'min':str(f.minimum),'max':str(f.maximum),'step':'any','when':f.when,
             **({'options':[{'value':o.value,'label':o.label} for o in f.options]} if f.type=='choice' else {})} for f in definition.factors]


def formatted(value):
    text=format(value,',f').replace(',',' ')
    return text.rstrip('0').rstrip('.') if '.' in text else text


def evaluate(service_id, definition, raw, as_of, rule_id=None, preview=False):
    if not isinstance(raw,dict) or set(raw)-{f.key for f in definition.factors}:
        raise HTTPException(422,'Javoblar ushbu kalkulyatorga mos emas.')
    answers={}
    for f in definition.factors:
        if not all(answers.get(k) in values for k,values in f.when.items()):
            continue
        value=raw.get(f.key)
        if value is None or value=='':
            if f.required:
                return {'result':None,'question':next(q for q in questions(definition) if q['key']==f.key)}
            continue
        if f.type=='number':
            try:
                if isinstance(value,bool) or len(str(value))>60: raise ValueError()
                value=Decimal(str(value))
                if not value.is_finite() or not f.minimum<=value<=f.maximum: raise ValueError()
                if value.as_tuple().exponent < -6: raise ValueError()
            except Exception:
                raise HTTPException(422,f'{f.label}: {f.minimum} dan {f.maximum} gacha son kiriting.')
        elif not isinstance(value,str) or len(value)>300:
            raise HTTPException(422,f'{f.label}: matnni tekshiring.')
        elif f.type=='choice' and value not in {o.value for o in f.options}:
            raise HTTPException(422,f'{f.label}: mos variantni tanlang.')
        answers[f.key]=value
    bhm=Decimal(definition.bhm_amount)
    initial=current=Decimal(0)
    steps=[]
    exempt=False
    active=0

    def amount(e, answer=None):
        value=e.value * (answer if e.times_input and answer is not None else 1)
        if e.unit=='bhm':return value*bhm
        if e.unit in {'fixed','number'}:return value
        basis={'initial':initial,'current':current,'bhm':bhm}.get(e.basis)
        if e.basis=='field':
            if e.field not in answers:
                raise HTTPException(422,'Hisoblash asosi bo‘lgan raqamli maydonni to‘ldiring.')
            basis=answers[e.field]
        return value/100*basis

    def expression(e,answer=None):
        if e.unit=='bhm':
            text=f'{formatted(bhm)} × {formatted(e.value)}'
        elif e.unit=='percent':
            basis={'initial':initial,'current':current,'bhm':bhm}.get(e.basis)
            if e.basis=='field':basis=answers[e.field]
            text=f'{formatted(basis)} × {formatted(e.value)}%'
        else:text=formatted(e.value)
        if e.times_input and answer is not None:text+=f' × {formatted(answer)}'
        return text

    initial=amount(definition.base)
    if initial>10**15:raise HTTPException(422,'Boshlang‘ich boj juda katta.')
    current=initial if definition.combine=='sequence' else Decimal(0)
    steps.append(f'Boshlang‘ich boj: {expression(definition.base)} = {formatted(initial)} so‘m.')

    def apply(e,label,answer=None):
        nonlocal current,exempt,active
        if e.operation=='none' or exempt:return
        active+=1
        before=current
        if e.operation=='exempt':
            current=Decimal(0);exempt=True;formula='Davlat boji olinmaydi'
        elif e.operation=='multiply':
            current*=e.value/(100 if e.unit=='percent' else 1) * (answer if e.times_input and answer is not None else 1)
            formula=f'{formatted(before)} × {formatted(e.value)}'+('%' if e.unit=='percent' else '')+(f' × {formatted(answer)}' if e.times_input and answer is not None else '')
        else:
            formula=expression(e,answer)
            if e.operation=='replace':current=amount(e,answer)
            elif e.operation=='add':
                current+=amount(e,answer)
                formula=f'{formatted(before)} + ({formula})'
        if not current.is_finite() or current>10**15:raise HTTPException(422,'Hisoblangan summa ishchi chegaradan oshdi.')
        steps.append(f'{label}: {formula} = {formatted(current)} so‘m.')

    for f in definition.factors:
        if f.key not in answers:continue
        a=answers[f.key]
        if f.type=='choice':
            o=next(o for o in f.options if o.value==a)
            apply(o.effect,f'{f.label} — {o.label}')
        else:apply(f.effect,f.label,a if f.type=='number' else None)
    for r in definition.rules:
        def matches(c):
            if c.field not in answers:return False
            a=answers[c.field];b=Decimal(c.value) if isinstance(a,Decimal) else c.value
            return {'eq':lambda:a==b,'ne':lambda:a!=b,'gt':lambda:a>b,'gte':lambda:a>=b,'lt':lambda:a<b,'lte':lambda:a<=b}[c.op]()
        if all(matches(c) for c in r.conditions):apply(r.effect,r.label)
    if definition.combine=='sum' and not active:current=initial
    if not exempt:
        if definition.minimum is not None:
            floor=definition.minimum*(bhm if definition.minimum_unit=='bhm' else 1)
            if current<floor:current=floor;steps.append(f'Eng kam boj qo‘llandi: {formatted(current)} so‘m.')
        if definition.maximum is not None:
            ceiling=definition.maximum*(bhm if definition.maximum_unit=='bhm' else 1)
            if current>ceiling:current=ceiling;steps.append(f'Eng ko‘p boj qo‘llandi: {formatted(current)} so‘m.')
    integer=current==current.to_integral_value()
    standard=int(initial) if initial==initial.to_integral_value() else None
    result={'service_id':service_id,'title':definition.name,'status':'needs_verification' if not integer else 'exempt' if exempt else 'discounted' if current<initial else 'standard',
        'payable_amount':int(current) if integer else None,'standard_amount':standard,'saving_amount':max(0,standard-int(current)) if integer and standard is not None else None,
        'currency':'UZS','benefit_title':'Bojdan ozod' if exempt else 'Admin kiritgan qoida bo‘yicha hisob',
        'explanation':'\n\n'.join(steps)+(' Kasr so‘m hosil bo‘ldi; summa yashirin yaxlitlanmadi.' if not integer else ''),'formula_steps':steps,
        'legal_basis':[{'title':s.title,'article':s.title,'url':s.url,'find_text':s.find_text,'section':s.section} for s in definition.sources],
        'category':definition.category,
        'next_steps':['Natijadagi manbalar va hisobga kiritgan ma’lumotlaringizni tekshiring.'],
        'other_costs_note':'Faqat davlat boji. Boshqa xizmat haqlari alohida.','rule_version':rule_id,'as_of_date':str(as_of),
        'verified_at':None,'review_status':'admin_configured','review_note':'Admin sozlagan stavka va shartlar asosida hisoblandi.', 'is_demo':preview}
    return {'result':result,'question':None}


def install(app,database,admin,today):
    from fastapi import Depends
    with database.connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS custom_calculators(id TEXT PRIMARY KEY, definition TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1, tested_hash TEXT, deleted_at TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS custom_categories(name TEXT PRIMARY KEY COLLATE NOCASE, icon TEXT NOT NULL);
        ''')

    def row_data(row):
        d=Definition.model_validate_json(row['definition'])
        current=database.current_rule(str(today()),row['id'])
        latest=next((r for r in database.all_rules(row['id']) if r['status']=='published'),None)
        return {**service(row['id'],d),'definition':d.model_dump(mode='json'),'revision':row['revision'],'active':row['deleted_at'] is None,'tested':row['tested_hash']==digest(d),'published':latest is not None,'rule':current,'latest_version':latest['id'] if latest else None,'has_changes':not latest or Definition.model_validate(latest['config']['definition']).model_dump(mode='json')!=d.model_dump(mode='json')}

    @app.get('/api/v1/admin/builder',dependencies=[Depends(admin)])
    def listing():
        with database.connect() as db:rows=db.execute('SELECT * FROM custom_calculators ORDER BY created_at,id').fetchall()
        return {'calculators':[row_data(r) for r in rows],'icons':ICONS,'server_date':str(today())}

    @app.get('/api/v1/admin/categories',dependencies=[Depends(admin)])
    def categories():
        from .catalog import CATALOG
        defaults={i['category']:{'name':i['category'],'icon':i['icon']} for i in CATALOG}
        with database.connect() as db:
            for r in db.execute('SELECT * FROM custom_categories ORDER BY name'):defaults[r['name']]=dict(r)
        return {'categories':list(defaults.values())}

    class CategoryRequest(Strict):
        name: str = Field(min_length=2,max_length=90)
        icon: str = 'calculator'

    @app.post('/api/v1/admin/categories',dependencies=[Depends(admin)])
    def category(body:CategoryRequest):
        if body.icon not in ICONS:raise HTTPException(422,'Ikonkani tanlang.')
        with database.connect() as db:
            db.execute('INSERT OR IGNORE INTO custom_categories(name,icon) VALUES(?,?)',(body.name,body.icon))
        return {'category':body.model_dump()}

    class SaveRequest(Strict):
        definition: Definition
        revision: int | None = None

    def save(body,service_id=None):
        import uuid
        service_id=service_id or 'custom_'+uuid.uuid4().hex[:16]
        encoded=body.definition.model_dump_json()
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM custom_calculators WHERE id=?',(service_id,)).fetchone()
            if row:
                if row['deleted_at']:raise HTTPException(409,'Avval kalkulyatorni qayta tiklang.')
                if body.revision!=row['revision']:raise HTTPException(409,'Boshqa o‘zgarish saqlangan. Ro‘yxatni yangilang.')
                if row['definition']!=encoded:
                    db.execute('UPDATE custom_calculators SET definition=?, revision=revision+1 WHERE id=?',(encoded,service_id))
            else:
                db.execute('INSERT INTO custom_calculators(id,definition) VALUES(?,?)',(service_id,encoded))
                db.execute('INSERT INTO calculators(id) VALUES(?)',(service_id,))
            db.execute('INSERT OR IGNORE INTO custom_categories(name,icon) VALUES(?,?)',(body.definition.category,body.definition.icon))
            row=db.execute('SELECT * FROM custom_calculators WHERE id=?',(service_id,)).fetchone()
        return {'calculator':row_data(row)}

    @app.post('/api/v1/admin/builder',dependencies=[Depends(admin)])
    def create(body:SaveRequest):return save(body)

    @app.put('/api/v1/admin/builder/{service_id}',dependencies=[Depends(admin)])
    def update(service_id:str,body:SaveRequest):
        with database.connect() as db:
            if not db.execute('SELECT 1 FROM custom_calculators WHERE id=?',(service_id,)).fetchone():raise HTTPException(404,'Kalkulyator topilmadi.')
        return save(body,service_id)

    class PreviewRequest(Strict):
        revision: int
        answers: dict = Field(default_factory=dict)

    @app.post('/api/v1/admin/builder/{service_id}/preview',dependencies=[Depends(admin)])
    def preview(service_id:str,body:PreviewRequest):
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM custom_calculators WHERE id=? AND deleted_at IS NULL',(service_id,)).fetchone()
            if not row:raise HTTPException(404,'Kalkulyator topilmadi.')
            if row['revision']!=body.revision:raise HTTPException(409,'Qoralama yangilangan. Qayta oching.')
            d=Definition.model_validate_json(row['definition'])
            outcome=evaluate(service_id,d,body.answers,today(),preview=True)
            if outcome['result'] and outcome['result']['payable_amount'] is not None:
                db.execute('UPDATE custom_calculators SET tested_hash=? WHERE id=?',(digest(d),service_id))
        return outcome

    class PublishRequest(Strict):
        revision: int

    @app.post('/api/v1/admin/builder/{service_id}/publish',dependencies=[Depends(admin)])
    def publish(service_id:str,body:PublishRequest):
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row=db.execute('SELECT * FROM custom_calculators WHERE id=? AND deleted_at IS NULL',(service_id,)).fetchone()
            if not row:raise HTTPException(404,'Kalkulyator topilmadi.')
            if row['revision']!=body.revision:raise HTTPException(409,'Qoralama o‘zgargan. Qayta oching.')
            d=Definition.model_validate_json(row['definition'])
            if not d.sources:raise HTTPException(422,'E’lon qilish uchun kamida bitta Lex.uz manbasini qo‘shing.')
            if row['tested_hash']!=digest(d):raise HTTPException(422,'Shu qoralamani avval sinab ko‘ring.')
            latest=db.execute("SELECT * FROM rules WHERE service_id=? AND status='published' ORDER BY effective_from DESC,id DESC LIMIT 1",(service_id,)).fetchone()
            if latest and str(d.effective_from)<latest['effective_from']:raise HTTPException(422,'Sana oxirgi e’lon qilingan qoidadan oldin bo‘lmasin.')
            if latest and json.loads(latest['config'])['definition']==d.model_dump(mode='json'):
                return {'published':True,'rule_id':latest['id']}
            config={'kind':'dynamic','definition':d.model_dump(mode='json'),'bhm_amount':d.bhm_amount,'effective_from':str(d.effective_from),'verified_at':str(today()),'law_url':d.sources[0].url,'law_article':d.sources[0].title,'bhm_source_url':'https://lex.uz/docs/-8283656','change_note':'Admin konstruktordan e’lon qildi.'}
            cursor=db.execute("INSERT INTO rules(service_id,status,effective_from,config,published_at) VALUES(?,'published',?,?,CURRENT_TIMESTAMP)",(service_id,str(d.effective_from),json.dumps(config,ensure_ascii=False)))
            db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)',(cursor.lastrowid,'Konstruktor: '+d.name+' e’lon qilindi'))
        return {'published':True,'rule_id':cursor.lastrowid}

    @app.delete('/api/v1/admin/builder/{service_id}',dependencies=[Depends(admin)])
    def delete(service_id:str):
        with database.connect() as db:
            if not db.execute('SELECT 1 FROM custom_calculators WHERE id=?',(service_id,)).fetchone():raise HTTPException(404,'Kalkulyator topilmadi.')
            db.execute('UPDATE custom_calculators SET deleted_at=CURRENT_TIMESTAMP WHERE id=?',(service_id,))
            db.execute('UPDATE calculators SET deleted_at=CURRENT_TIMESTAMP WHERE id=?',(service_id,))
        return {'deleted':True}

    @app.post('/api/v1/admin/builder/{service_id}/restore',dependencies=[Depends(admin)])
    def restore(service_id:str):
        with database.connect() as db:
            if not db.execute('SELECT 1 FROM custom_calculators WHERE id=?',(service_id,)).fetchone():raise HTTPException(404,'Kalkulyator topilmadi.')
            db.execute('UPDATE custom_calculators SET deleted_at=NULL WHERE id=?',(service_id,))
            db.execute('UPDATE calculators SET deleted_at=NULL WHERE id=?',(service_id,))
        return {'restored':True}


def published_services(database,as_of):
    with database.connect() as db:ids=[r['id'] for r in db.execute('SELECT id FROM custom_calculators WHERE deleted_at IS NULL ORDER BY created_at,id')]
    result=[]
    for i in ids:
        r=database.current_rule(str(as_of),i)
        if r:result.append(service(i,Definition.model_validate(r['config']['definition'])))
    return result
