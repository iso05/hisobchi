"""
LexAI — javob yig'ish (demo-barqaror rejim).

Sabab: v3 LoRA trening shablonidagi savollarga to'g'ri javob beradi, lekin tabiiy
savollarni ("Nikohni bekor qilish uchun davlat boji qancha?") rad etadi.
Shuning uchun:
  0. Mavzudan tashqari (boshqa qonun) savol -> ochiq rad.
  1. Tarif savoli + mos tarif qatori topilsa -> jadvaldan deterministik javob (model yo'q).
  2. Aks holda -> model + verifier.
  3. Model rad etsa yoki tekshiruvdan o'tmasa, lekin mos normativ/o'zgartirish chunki bo'lsa
     -> manbadan aynan iqtibos (extractive).
  4. Hech biri mos kelmasa -> rad.
Moslik: savolning mazmunli o'zaklari chunk matnida bormi (umumiy so'zlar hisobga olinmaydi).
"""
import re

from retrieval import normalize, tokenize

FEE_WORDS = ("boj", "qancha", "stavka", "toʻla", "narx", "summa", "necha", "miqdor")
STOP = set(tokenize(
    "davlat boj boji bojini bojidan bojga qancha uchun stavka stavkasi qanday nima nimalar boʻyicha "
    "toʻlanadi toʻlash toʻlayman toʻlov kerak mumkin men biz siz qonun qonunda haqida deyilgan qaysi "
    "kim kimlar qachon necha miqdori miqdorda boʻladi boʻladimi qilinadi berish beriladi olish "
    "qilish sud sudga sudda ariza arizasi arizalaridan"))
OUT_OF_SCOPE_RE = re.compile(
    r"\b(qqs|qoʻshilgan qiymat|daromad soligʻi|mol-mulk soligʻi|soliq kodeksi|aksiz|jarima|aliment|"
    r"pensiya|mehnat taʼtil|ishdan boʻshat|jinoyat|firibgar|bojxona|ish haqi|kredit|ipoteka foiz)", re.I)

REFUSAL_KEYS = ("topilmadi", "bera olmayman", "keltira olmayman", "koʻrsatilmagan")


def content_terms(question):
    return [t for t in tokenize(question) if t not in STOP and not t.isdigit() and len(t) > 2]


def relevance(question, chunk):
    terms = content_terms(question)
    if not terms:
        return 0.0
    ct = set(tokenize(chunk["text"]))
    return sum(t in ct for t in terms) / len(terms)


def is_refusal(text):
    t = normalize(text).lower()
    return any(k in t for k in REFUSAL_KEYS)


def _path(c):
    return " — ".join(p.rstrip(":").strip() for p in c["metadata"]["context_path"])


# Sinonimlar: foydalanuvchi tili -> qonun tili (notebookdagi router g'oyasi)
EXPAND = [
    (re.compile(r"ajrash\w*|ajralish\w*|ajrashish"), "nikohni bekor qilish"),
    (re.compile(r"ikkinchi marta|takroran|yana bir marta"), "takroriy"),
    (re.compile(r"boj puli|boj haqi"), "davlat boji"),
]

# Kalit so'z -> modda (normativ matn uchun yo'naltirish)
ROUTES = [
    (re.compile(r"qaytar"), ["18-modda"]),
    (re.compile(r"(ozod|imtiyoz).*(iqtisodiy)|(iqtisodiy).*(ozod|imtiyoz)"), ["9-modda"]),
    (re.compile(r"(ozod|imtiyoz).*(maʼmuriy)|(maʼmuriy).*(ozod|imtiyoz)"), ["10-modda"]),
    (re.compile(r"(ozod|imtiyoz).*notari|notari.*(ozod|imtiyoz)"), ["11-modda"]),
    (re.compile(r"(ozod|imtiyoz).*(fhdyo|fuqarolik holati)|(fhdyo|fuqarolik holati).*(ozod|imtiyoz)"), ["12-modda"]),
    (re.compile(r"(ozod|imtiyoz).*(migratsiya|pasport|viza)|(migratsiya|pasport|viza).*(ozod|imtiyoz)"), ["13-modda"]),
    (re.compile(r"(ozod|imtiyoz).*sud|sud.*(ozod|imtiyoz)"), ["8-modda"]),
    (re.compile(r"ozod|imtiyoz"), ["7-modda", "15-modda"]),
]


def expand(question):
    q = normalize(question).lower()
    for rx, rep in EXPAND:
        q = rx.sub(rep, q)
    return q


def path_relevance(question, chunk):
    """Moslik bo'lim sarlavhasisiz — faqat harakat yo'li bo'yicha (umumiy bo'lim so'zlari aldamasin)."""
    terms = content_terms(question)
    if not terms:
        return 0.0
    pt = set(tokenize(" ".join(chunk["metadata"]["context_path"][1:])))
    return sum(t in pt for t in terms) / len(terms)


def fee_answer(question, chunks, min_rel=0.5):
    q = normalize(question).lower()
    if not any(w in q for w in FEE_WORDS):
        return None, []
    fees = [(path_relevance(question, c), -i, c) for i, c in enumerate(chunks)
            if c["metadata"].get("chunk_type") == "fee_entry"]
    fees = [c for s, _, c in sorted(fees, key=lambda x: (x[0], x[1]), reverse=True) if s >= min_rel]
    if not fees:
        return None, []
    top = fees[0]
    ans = (f"{_path(top)}\n\nDavlat boji stavkasi: **{top['metadata']['fee_rate']}**.\n\n"
           f"Manba: {top['metadata'].get('source_reference', '')} [{top['chunk_id']}].")
    if len(fees) > 1:
        ans += "\n\nAgar holatingiz boshqacha boʻlsa, yaqin holatlar:\n" + "\n".join(
            f"- {_path(c)} — **{c['metadata']['fee_rate']}** [{c['chunk_id']}]" for c in fees[1:3])
    return ans, fees


def routed_chunks(question, all_chunks):
    q = normalize(question).lower()
    for rx, arts in ROUTES:
        if rx.search(q):
            return [c for a in arts for c in all_chunks
                    if c["metadata"].get("article") == a and c["metadata"]["chunk_type"] == "article_normative"]
    return []


def extractive_answer(question, chunks, min_rel=0.5, routed=None):
    good = routed or [c for c in chunks if c["metadata"].get("chunk_type") in ("article_normative", "amendment_history")
                      and relevance(question, c) >= min_rel]
    if not good:
        return None
    parts = []
    for c in good[:2]:
        m = c["metadata"]
        body = c["text"].split("Normativ matn:", 1)[-1].split("Oʻzgartirishlar tarixi:", 1)[-1].strip()
        parts.append(f"**{m.get('article', '')}** — {m.get('source_reference', '')}:\n\n«{body}»\n\n[{c['chunk_id']}]")
    return "Savolingizga oid qonun matni:\n\n" + "\n\n---\n\n".join(parts)


def answer(question, retriever, generate, make_user, verify, refusal, out_of_scope, k=4):
    """Qaytaradi: (javob, verified, rejim, manba_chunklar).
    generate(prompt)->str; make_user(chunks,q)->prompt; verify(prompt,ans)->problems."""
    if OUT_OF_SCOPE_RE.search(normalize(question).lower()):
        return out_of_scope, True, "mavzudan_tashqari", []
    q = expand(question)
    pool = retriever.search(q, k=10)
    det, fees = fee_answer(q, pool)
    if det:
        return det, True, "jadval", fees[:k]
    routed = routed_chunks(q, retriever.chunks)
    chunks = routed[:k] if routed else pool[:k]
    prompt = make_user(chunks, question)
    raw = generate(prompt)
    problems = verify(prompt, raw)
    if not problems and not is_refusal(raw):
        return raw, True, "model", chunks
    ext = extractive_answer(q, chunks, routed=routed[:2] if routed else None)
    if ext:
        return ext, True, "manba", chunks
    return refusal, False, "rad", chunks
