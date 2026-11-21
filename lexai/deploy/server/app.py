"""
LexAI API — FastAPI server (AWS EC2 GPU).

POST /ask   {"question": "..."}  ->  {"answer", "verified", "sources", "latency_ms"}
GET  /health

Oqim: savol -> gibrid qidiruv (v3 korpus) -> trening bilan AYNAN bir xil prompt
(build_sft.make_user) -> Gemma 4 E2B + LoRA -> verifier.verify -> javob.
Tekshiruvdan o'tmagan javob foydalanuvchiga berilmaydi (xavfsiz rad javobi qaytadi),
xom javob faqat server log'iga yoziladi.

Muhit o'zgaruvchilari (/opt/lexai/.env):
  LEXAI_ADAPTER_DIR   /opt/lexai/lora            (adapter_config ichida base yo'li to'g'ri bo'lishi kerak)
  LEXAI_DATA_DIR      /opt/lexai/data            (rag_corpus_v3.jsonl, index/)
  LEXAI_EMBED_MODEL   intfloat/multilingual-e5-large
  LEXAI_API_KEY       web-app backend yuboradigan maxfiy kalit (X-API-Key)
  LEXAI_CORS_ORIGINS  https://sizning-webapp.uz  (vergul bilan; bo'sh bo'lsa CORS o'chiq)
  LEXAI_TOP_K         4
  LEXAI_DRY_RUN       1 bo'lsa model yuklanmaydi (faqat qidiruv + prompt sinovi)
"""
import logging
import os
import sys
import threading
import time
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

HERE = Path(__file__).resolve().parent
for p in (HERE, HERE.parent.parent):  # serverda: app/ ichida; lokalda: lexai_finetune/
    sys.path.insert(0, str(p))
from build_sft import make_user  # noqa: E402  — trening bilan bir xil prompt
from retrieval import Retriever  # noqa: E402
from verifier import REFUSAL, verify  # noqa: E402
import answering  # noqa: E402

OUT_OF_SCOPE = ("Bu savol mening hozirgi bilimlar bazamdan tashqarida: men faqat OʻRQ-600 «Davlat boji "
                "toʻgʻrisida»gi Qonun boʻyicha javob beraman. Tegishli qonun hujjatini lex.uz orqali "
                "yoki malakali yurist bilan aniqlashtiring.")

log = logging.getLogger("lexai")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ADAPTER_DIR = os.environ.get("LEXAI_ADAPTER_DIR", "/opt/lexai/lora")
DATA_DIR = os.environ.get("LEXAI_DATA_DIR", "/opt/lexai/data")
EMBED_MODEL = os.environ.get("LEXAI_EMBED_MODEL", "intfloat/multilingual-e5-large")
API_KEY = os.environ.get("LEXAI_API_KEY", "")
TOP_K = int(os.environ.get("LEXAI_TOP_K", "4"))
DRY_RUN = os.environ.get("LEXAI_DRY_RUN") == "1"
MAX_NEW_TOKENS = int(os.environ.get("LEXAI_MAX_NEW_TOKENS", "512"))

app = FastAPI(title="LexAI API", version="1.0")
origins = [o.strip() for o in os.environ.get("LEXAI_CORS_ORIGINS", "").split(",") if o.strip()]
if origins:
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["POST", "GET"],
                       allow_headers=["Content-Type", "X-API-Key"])

STATE = {}
GPU_LOCK = threading.Lock()  # bitta GPU — so'rovlar navbat bilan


class AskIn(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)


def load():
    STATE["retriever"] = Retriever(DATA_DIR, embed_model=None if DRY_RUN else EMBED_MODEL)
    if DRY_RUN:
        log.warning("DRY_RUN: model yuklanmadi")
        return
    from unsloth import FastModel
    model, tokenizer = FastModel.from_pretrained(model_name=ADAPTER_DIR, max_seq_length=4096, load_in_4bit=True)
    FastModel.for_inference(model)
    STATE["model"], STATE["tokenizer"] = model, tokenizer
    STATE["tok"] = getattr(tokenizer, "tokenizer", tokenizer)
    log.info("model yuklandi: %s", ADAPTER_DIR)


def generate(prompt_text):
    if DRY_RUN:
        return REFUSAL
    tokenizer, tok, model = STATE["tokenizer"], STATE["tok"], STATE["model"]
    msgs = [{"role": "user", "content": prompt_text}]
    try:
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    except Exception:
        msgs = [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}]
        prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    ids = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
    with GPU_LOCK:
        out = model.generate(**ids, max_new_tokens=MAX_NEW_TOKENS, do_sample=False)
    return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()


@app.on_event("startup")
def _startup():
    load()


@app.get("/health")
def health():
    return {"ok": True, "model_loaded": "model" in STATE, "dry_run": DRY_RUN,
            "chunks": len(STATE["retriever"].chunks) if "retriever" in STATE else 0}


@app.post("/ask")
def ask(body: AskIn, x_api_key: str = Header(default="")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")
    t0 = time.time()
    answer, verified, mode, chunks = answering.answer(
        body.question, STATE["retriever"], generate, make_user, verify, REFUSAL, OUT_OF_SCOPE, k=TOP_K)
    log.info("mode=%s verified=%s savol=%r", mode, verified, body.question)
    return {
        "answer": answer,
        "verified": verified,
        "mode": mode,
        "sources": [{"id": c["chunk_id"], "reference": c["metadata"].get("source_reference", ""),
                     "text": c["text"]} for c in chunks],
        "latency_ms": int((time.time() - t0) * 1000),
    }
