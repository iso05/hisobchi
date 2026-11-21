import hashlib
import json
import os
import re
import secrets
import time
import uuid
from urllib.parse import urlsplit
from datetime import date
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError

from .calculator import today
from .catalog import BY_ID, CATALOG, public_service, applies, precise_result_sources
from .engine import calculate, missing_question, get_questions, prepare_answers, validate_parameters
from .db import Database
from .models import Answers, CalculateRequest, LoginRequest, ReportRequest, RuleConfig, CatalogRuleConfig
from .notarial import reference_for
from . import builder, lexai

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
ALLOWED = {'http://127.0.0.1:5173', 'http://localhost:5173', 'http://127.0.0.1:8000', 'http://localhost:8000'}
SERVICE = {'id': 'notary_car', 'name': 'Avtomobil oldi-sotdisi', 'description': 'Notarial davlat boji va imtiyozlar', 'icon': 'car'}


def create_app(db_path=None, admin_password=None):
    database_path = db_path or os.getenv('HISOBCHI_DB', 'data/hisobchi.sqlite3')
    database_path = Path(database_path)
    if not database_path.is_absolute():
        database_path = ROOT / database_path
    database = Database(database_path)
    database.initialize()
    password = admin_password if admin_password is not None else os.getenv('ADMIN_PASSWORD', '')
    public_origin = os.getenv('HISOBCHI_PUBLIC_ORIGIN', '').strip().rstrip('/')
    if public_origin:
        url = urlsplit(public_origin)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.path or url.query or url.fragment:
            raise ValueError('HISOBCHI_PUBLIC_ORIGIN must be a single HTTPS origin')
    allowed_origins = {public_origin} if public_origin else ALLOWED
    secure_cookie = bool(public_origin)
    app = FastAPI(title='Hisobchi API', version='0.2.0')
    app.state.database = database
    app.add_middleware(CORSMiddleware, allow_origins=sorted(allowed_origins), allow_credentials=True, allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Content-Type'])
    @app.middleware('http')
    async def protect_response(request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        response.headers['X-Frame-Options'] = 'DENY'
        if request.url.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        if secure_cookie and request.url.scheme == 'https':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'
        return response


    def require_origin(request: Request):
        # Same-origin browser requests and our Vite proxy are supported. Reject cross-site writes.
        origin = request.headers.get('origin')
        if origin and origin not in allowed_origins:
            raise HTTPException(403, 'Bu manzildan o‘zgartirishga ruxsat yo‘q.')
        if request.headers.get('sec-fetch-site') == 'cross-site' and origin not in allowed_origins:
            raise HTTPException(403, 'Begona saytdan so‘rov rad etildi.')

    def admin(request: Request):
        token = request.cookies.get('hisobchi_admin', '')
        with database.connect() as db:
            session = db.execute('SELECT expires_at FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
        if not session or session['expires_at'] < time.time():
            raise HTTPException(401, 'Admin sifatida kiring.')
        if request.method != 'GET':
            require_origin(request)
        return True

    def owner(request: Request, response: Response):
        token = request.cookies.get('hisobchi_visitor', '')
        if not re.fullmatch(r'[0-9a-f]{64}', token):
            token = secrets.token_hex(32)
            response.set_cookie('hisobchi_visitor', token, httponly=True, secure=secure_cookie, samesite='strict', max_age=30*86400, path='/api/v1')
        return hashlib.sha256(token.encode()).hexdigest()

    def store_result(result, answers, visitor):
        calculation_id = str(uuid.uuid4())
        sources = precise_result_sources(result['service_id'], result.get('legal_basis', [])) if result['service_id'] in BY_ID else result.get('legal_basis', [])
        result = {**result, 'calculation_id': calculation_id, 'legal_basis':sources}
        with database.connect() as db:
            db.execute('INSERT INTO calculations(public_id,service_id,owner,rule_id,answers,result) VALUES(?,(SELECT id FROM calculators WHERE slug=?),?,?,?,?)', (calculation_id, result['service_id'], visitor, result.get('rule_version'), json.dumps(answers,ensure_ascii=False), json.dumps(result, ensure_ascii=False)))
        return result

    def perform(body, visitor):
        if body.service_id not in BY_ID:
            as_of = body.as_of_date or today()
            if as_of > today():
                raise HTTPException(422,'Kelajak sanasiga yakuniy hisob berilmaydi.')
            rule = database.current_rule(str(as_of),body.service_id)
            if not rule or rule['config'].get('kind')!='dynamic' or not database.calculator_active(body.service_id):
                raise HTTPException(404,'Kalkulyator shu sanada faol emas.')
            outcome = builder.evaluate(body.service_id,builder.Definition.model_validate(rule['config']['definition']),body.answers,as_of,rule['id'])
            if outcome['result']:
                outcome['result']=store_result(outcome['result'],body.answers,visitor)
            return outcome
        if body.service_id not in BY_ID or not database.calculator_active(body.service_id):
            raise HTTPException(404, 'Kalkulyator hozir faol emas.')
        answers = prepare_answers(body.service_id,body.answers)
        question = missing_question(body.service_id,answers)
        if question:
            return {'result': None, 'question': question}
        as_of = body.as_of_date or today()
        if as_of > today():
            raise HTTPException(422, 'Kelajak sanasiga yakuniy hisob berilmaydi. E’lon qilingan rejalashtirilgan qoidani admin panelda ko‘ring.')
        rule = database.current_rule(str(as_of),body.service_id)
        result = calculate(body.service_id,answers,rule,as_of)
        return {'result': store_result(result, answers, visitor), 'question': None}

    @app.get('/health')
    def health():
        return {'status': 'ok', 'service': 'hisobchi', 'calculator_count': len(CATALOG)+len(builder.published_services(database,today()))}

    @app.post('/api/v1/assistant/chat', dependencies=[Depends(require_origin)])
    def assistant_chat(body: lexai.ChatQuestion) -> lexai.ChatAnswer:
        return lexai.ask(body.question)

    @app.get('/api/v1/services')
    def services():
        with database.connect() as db:
            active = {r['slug'] for r in db.execute('SELECT slug FROM calculators WHERE deleted_at IS NULL')}
        return {'services': [public_service(item) for item in CATALOG if item['id'] in active]+builder.published_services(database,today())}

    @app.get('/api/v1/calculator/schema')
    def schema(service_id: str='notary_car'):
        if service_id not in BY_ID:
            rule=database.current_rule(str(today()),service_id)
            if not rule or rule['config'].get('kind')!='dynamic' or not database.calculator_active(service_id):raise HTTPException(404,'Kalkulyator faol emas.')
            d=builder.Definition.model_validate(rule['config']['definition'])
            return {'service':builder.service(service_id,d),'questions':builder.questions(d),'sources':[s.model_dump() for s in d.sources],'exceptions':[],'notarial_exemptions':[]}
        if service_id not in BY_ID or not database.calculator_active(service_id):
            raise HTTPException(404, 'Kalkulyator hozir faol emas.')
        return {'service': public_service(BY_ID[service_id]), 'questions':get_questions(service_id),'sources':BY_ID[service_id]['sources'],'exceptions':BY_ID[service_id]['exceptions'],'notarial_exemptions':reference_for(service_id)}

    @app.get('/api/v1/rules/current')
    def current_rule(service_id: str='notary_car'):
        if service_id not in BY_ID and not (database.calculator_active(service_id) and database.current_rule(str(today()),service_id)):
            raise HTTPException(404,'Kalkulyator topilmadi.')
        return {'rule': database.current_rule(str(today()),service_id), 'server_date': str(today())}

    @app.post('/api/v1/calculate')
    def calculate_endpoint(body: CalculateRequest, request: Request, response: Response):
        require_origin(request)
        return perform(body, owner(request, response))


    @app.post('/api/v1/admin/login')
    def login(body: LoginRequest, request: Request, response: Response):
        require_origin(request)
        client_key = hashlib.sha256((request.client.host if request.client else 'local').encode()).hexdigest()
        now = int(time.time())
        if not password or len(password) < 16 or password == 'replace-with-a-long-local-password':
            raise HTTPException(503, 'Mahalliy admin parolini sozlang.')
        valid = secrets.compare_digest(hashlib.sha256(body.password.encode()).digest(), hashlib.sha256(password.encode()).digest())
        token = secrets.token_urlsafe(32)
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            db.execute('DELETE FROM login_attempts WHERE attempted_at<=?',(now-300,))
            failures = db.execute('SELECT COUNT(*) FROM login_attempts WHERE client_hash=?',(client_key,)).fetchone()[0]
            if failures >= 5:
                raise HTTPException(429, 'Urinishlar ko‘p. 5 daqiqadan keyin qayta urinib ko‘ring.')
            if not valid:
                db.execute('INSERT INTO login_attempts(client_hash,attempted_at) VALUES(?,?)',(client_key,now))
            else:
                db.execute('DELETE FROM login_attempts WHERE client_hash=?',(client_key,))
                previous = request.cookies.get('hisobchi_admin','')
                db.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(previous.encode()).hexdigest(),))
                db.execute('DELETE FROM sessions WHERE expires_at<=?',(now,))
                db.execute('INSERT INTO sessions(token_hash,expires_at) VALUES(?,?)',(hashlib.sha256(token.encode()).hexdigest(),now+4*3600))
        if not valid:
            raise HTTPException(401, 'Parol noto‘g‘ri.')
        response.set_cookie('hisobchi_admin', token, httponly=True, secure=secure_cookie, samesite='strict', max_age=4*3600, path='/api/v1')
        return {'authenticated': True}

    @app.get('/api/v1/admin/me', dependencies=[Depends(admin)])
    def me():
        return {'authenticated': True}

    @app.post('/api/v1/admin/logout', dependencies=[Depends(admin)])
    def logout(request: Request, response: Response):
        with database.connect() as db:
            db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(request.cookies.get('hisobchi_admin', '').encode()).hexdigest(),))
        response.delete_cookie('hisobchi_admin', path='/api/v1', secure=secure_cookie, httponly=True, samesite='strict')
        return {'authenticated': False}

    @app.get('/api/v1/admin/rules', dependencies=[Depends(admin)])
    def list_rules(service_id: str='notary_car'):
        return {'rules': database.all_rules(None if service_id=='all' else service_id), 'server_date': str(today())}

    @app.get('/api/v1/admin/calculators', dependencies=[Depends(admin)])
    def list_calculators():
        return {'calculators': [{**public_service(item), 'active': database.calculator_active(item['id']), 'rule': database.current_rule(str(today()),item['id']), 'parameters':item['parameters'],'sources':item['sources']} for item in CATALOG], 'server_date': str(today())}

    @app.get('/api/v1/legal-sources')
    def legal_sources():
        return {'calculators':[{**public_service(item),'sources':item['sources'],'exceptions':item['exceptions']} for item in CATALOG]}

    @app.put('/api/v1/admin/calculators/{calculator_id}', dependencies=[Depends(admin)])
    def edit_calculator(calculator_id: str, body: dict):
        if calculator_id not in BY_ID:
            raise HTTPException(404, 'Kalkulyator topilmadi.')
        if body.get('reviewed') is not True:
            raise HTTPException(422, 'Qonun manbasi va qiymatlarni tekshirganingizni belgilang.')
        try:
            config = (RuleConfig if calculator_id=='notary_car' else CatalogRuleConfig).model_validate({k:v for k,v in body.items() if k!='reviewed'})
        except ValidationError:
            raise HTTPException(422,'Stavkalar, manba havolalari va sanalarni tekshiring.')
        if config.verified_at > today():
            raise HTTPException(422, 'Tekshirilgan sana kelajakda bo‘lishi mumkin emas.')
        if calculator_id!='notary_car':
            validate_parameters(calculator_id,config.parameters)
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            record = db.execute('SELECT deleted_at,id FROM calculators WHERE slug=?', (calculator_id,)).fetchone()
            if not record or record['deleted_at'] is not None:
                raise HTTPException(409, 'Avval o‘chirilgan kalkulyatorni qayta tiklang.')
            latest = db.execute("SELECT MAX(effective_from) AS value FROM rules WHERE status='published' AND service_id=(SELECT id FROM calculators WHERE slug=?)",(calculator_id,)).fetchone()['value']
            if latest and str(config.effective_from) < latest:
                raise HTTPException(422, 'Kuchga kirish sanasi oxirgi e’lon qilingan qoidadan oldin bo‘lishi mumkin emas.')
            cursor = db.execute("INSERT INTO rules(service_id,status,effective_from,config,published_at) VALUES(?,'published',?,?,CURRENT_DATE)", (record['id'],str(config.effective_from), config.model_dump_json()))
            rule_id = cursor.lastrowid
            db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (rule_id, 'Kalkulyator stavkalari tahrirlandi va saqlandi'))
        return {'rule': next(r for r in database.all_rules(calculator_id) if r['id'] == rule_id)}

    @app.delete('/api/v1/admin/calculators/{calculator_id}', dependencies=[Depends(admin)])
    def delete_calculator(calculator_id: str):
        if calculator_id not in BY_ID:
            raise HTTPException(404, 'Kalkulyator topilmadi.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor = db.execute('UPDATE calculators SET deleted_at=CURRENT_DATE WHERE slug=? AND deleted_at IS NULL', (calculator_id,))
            if cursor.rowcount:
                rule = db.execute("SELECT id FROM rules WHERE status='published' AND service_id=(SELECT id FROM calculators WHERE slug=?) ORDER BY effective_from DESC,id DESC LIMIT 1",(calculator_id,)).fetchone()
                db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (rule['id'], 'Kalkulyator o‘chirildi (tarix saqlandi)'))
        return {'deleted': True}

    @app.post('/api/v1/admin/calculators/{calculator_id}/restore', dependencies=[Depends(admin)])
    def restore_calculator(calculator_id: str):
        if calculator_id not in BY_ID:
            raise HTTPException(404, 'Kalkulyator topilmadi.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            cursor = db.execute('UPDATE calculators SET deleted_at=NULL WHERE slug=? AND deleted_at IS NOT NULL', (calculator_id,))
            if cursor.rowcount:
                rule = db.execute("SELECT id FROM rules WHERE status='published' AND service_id=(SELECT id FROM calculators WHERE slug=?) ORDER BY effective_from DESC,id DESC LIMIT 1",(calculator_id,)).fetchone()
                db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (rule['id'], 'Kalkulyator qayta tiklandi'))
        return {'restored': True}

    @app.post('/api/v1/admin/rules', dependencies=[Depends(admin)])
    def create_rule(body: RuleConfig):
        if body.verified_at > today():
            raise HTTPException(422, 'Tekshirilgan sana kelajakda bo‘lishi mumkin emas.')
        with database.connect() as db:
            cursor = db.execute("INSERT INTO rules(service_id,status,effective_from,config) VALUES((SELECT id FROM calculators WHERE slug='notary_car'),'draft',?,?)", (str(body.effective_from), body.model_dump_json()))
            rule_id = cursor.lastrowid
            db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (rule_id, 'Yangi qoralama yaratildi'))
        return {'rule': next(r for r in database.all_rules() if r['id'] == rule_id)}

    class PublishRequest(BaseModel):
        reviewed: bool

    @app.post('/api/v1/admin/rules/{rule_id}/publish', dependencies=[Depends(admin)])
    def publish(rule_id: int, body: PublishRequest):
        if not body.reviewed:
            raise HTTPException(422, 'Manba va qiymatlarni tekshirganingizni tasdiqlang.')
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT * FROM rules WHERE id=?', (rule_id,)).fetchone()
            if not row:
                raise HTTPException(404, 'Qoida topilmadi.')
            if row['status'] != 'draft':
                raise HTTPException(409, 'Qoida allaqachon e’lon qilingan.')
            config = RuleConfig.model_validate_json(row['config'])
            latest = db.execute("SELECT MAX(effective_from) AS value FROM rules WHERE status='published' AND service_id=(SELECT id FROM calculators WHERE slug='notary_car')").fetchone()['value']
            if latest and str(config.effective_from) < latest:
                raise HTTPException(422, 'Yangi qoida oxirgi e’lon qilingan qoidaning sanasidan oldin boshlana olmaydi.')
            db.execute("UPDATE rules SET status='published',published_at=CURRENT_DATE WHERE id=?", (rule_id,))
            db.execute('INSERT INTO audit(rule_id,action) VALUES(?,?)', (rule_id, 'Admin manbani tekshirib e’lon qildi'))
        return {'rule': next(r for r in database.all_rules() if r['id'] == rule_id)}

    @app.get('/api/v1/admin/audit', dependencies=[Depends(admin)])
    def audit():
        with database.connect() as db:
            return {'events': [dict(r) for r in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]}

    def impact(db):
        row = db.execute('SELECT COUNT(*) confirmed_reports, COUNT(saving_amount) reports_with_amount, COALESCE(SUM(saving_amount),0) reported_saving_amount FROM reports').fetchone()
        return {**dict(row), 'currency': 'UZS', 'scope': 'global', 'is_demo': False}

    @app.get('/api/v1/impact')
    def impact_endpoint():
        with database.connect() as db:
            return impact(db)

    @app.post('/api/v1/benefit-reports')
    def report(body: ReportRequest, request: Request, response: Response):
        require_origin(request)
        visitor = owner(request, response)
        with database.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            calc = db.execute('SELECT * FROM calculations WHERE public_id=? AND owner=?', (body.calculation_id, visitor)).fetchone()
            if not calc:
                raise HTTPException(404, 'Hisob topilmadi yoki ushbu brauzerga tegishli emas.')
            result = json.loads(calc['result'])
            if result['status'] not in {'discounted', 'exempt'} or result['service_id'] != body.service_id:
                raise HTTPException(422, 'Bu hisob uchun imtiyozdan foydalanish tasdig‘i qo‘shilmaydi.')
            saved = db.execute('SELECT * FROM reports WHERE calculation_id=?', (calc['id'],)).fetchone()
            if not saved:
                saving = body.standard_amount - body.paid_amount if body.standard_amount is not None else None
                db.execute('INSERT INTO reports(public_id,calculation_id,standard_amount,paid_amount,saving_amount) VALUES(?,?,?,?,?)', (str(uuid.uuid4()), calc['id'], body.standard_amount, body.paid_amount, saving))
                saved = db.execute('SELECT * FROM reports WHERE calculation_id=?', (calc['id'],)).fetchone()
            return {'report': {**{k:saved[k] for k in ('standard_amount','paid_amount','saving_amount','created_at')}, 'id':saved['public_id'], 'calculation_id':body.calculation_id, 'service_id': body.service_id, 'verification': 'self_reported', 'is_demo': False, 'reported_at': saved['created_at']}, 'impact': impact(db)}

    builder.install(app,database,admin,today)
    return app


app = create_app()
