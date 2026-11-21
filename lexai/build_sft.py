"""
LexAI — Gemma 4 E2B IT uchun SFT (supervised fine-tuning) dataset generatori.

Yondashuv: RAG-grounded SFT. Model qonunni yod olmaydi (2B model 556 ta tarifni
ishonchli yodlay olmaydi va bu gallyutsinatsiyani oshiradi). Model quyidagilarni o'rganadi:
  * berilgan manbalar ichidan to'g'ri chunkni tanlash (yaqin "distractor"lar orasidan),
  * stavka / modda matnini o'zgartirmasdan chiqarish,
  * har bir javobga manba ID sini biriktirish,
  * manbada javob bo'lmasa — ochiq aytish (refusal),
  * savoldagi noto'g'ri raqamni tuzatish (wrong premise),
  * BHM qiymati berilganda summani hisoblash, berilmaganda so'rash.

Barcha javoblar deterministik ravishda manba ma'lumotlaridan yasaladi — LLM ishlatilmagan.

Ishlatish:
  python3 -I build_sft.py <LexHackaton papkasi> <data_v3 papkasi> <chiqish papkasi>
"""
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

SEED = 600
rng = random.Random(SEED)

SYSTEM_RULES = (
    "Siz LexAI — Oʻzbekiston Respublikasi qonunchiligi boʻyicha huquqiy yordamchisiz. "
    "Faqat quyida berilgan manbalarga tayanib javob bering. Stavka, muddat, raqam va qonun "
    "matnini oʻzgartirmang. Har bir javobda manba ID sini koʻrsating. Agar manbalarda javob "
    "boʻlmasa, buni ochiq ayting va taxmin qilmang."
)

LAW_REF = "OʻRQ-600 «Davlat boji toʻgʻrisida»gi Qonun"
TABLE_REF = "Davlat boji stavkalarining miqdorlari ilovasi"
NO_ANSWER = (
    "Berilgan manbalarda bu savolga aniq javob topilmadi. Taxminiy stavka yoki raqam "
    "keltira olmayman. Iltimos, savolni aniqlashtiring yoki tegishli manba bilan qayta soʻrang."
)
OUT_OF_SCOPE = (
    "Bu savol {topic} bilan bogʻliq. Mening hozirgi bilimlar bazam faqat {law} bilan "
    "cheklangan, shuning uchun bu borada ishonchli javob bera olmayman. Tegishli qonun "
    "hujjatini (masalan, lex.uz orqali) yoki malakali yuristni tavsiya qilaman."
)

TOKEN_RE = re.compile(r"[a-zA-Zʻʼ'’0-9¹²³]+")
MONTHS = {m: i + 1 for i, m in enumerate(
    "yanvar fevral mart aprel may iyun iyul avgust sentabr oktabr noyabr dekabr".split())}


# ---------------------------------------------------------------- utils
def toks(s):
    return set(t.lower() for t in TOKEN_RE.findall(s) if len(t) > 2)


def jaccard(a, b):
    return len(a & b) / (len(a | b) or 1)


MAX_AMD = 8  # bitta namunadagi o'zgartirish chunklari soni (kontekst uzunligini cheklash)


def assign_splits(samples):
    """Vazifa bo'yicha stratifikatsiya; bir split_key (masalan, aka-uka qatorlar) bitta splitda."""
    by_task = defaultdict(set)
    for s in samples:
        by_task[s["task"]].add(s["split_key"])
    where = {}
    for task, keys in by_task.items():
        ks = sorted(keys, key=lambda k: hashlib.sha1(k.encode()).hexdigest())
        n = len(ks)
        n_test = max(1, round(n * 0.05)) if n >= 10 else 0
        n_val = max(1, round(n * 0.05)) if n >= 10 else 0
        for i, k in enumerate(ks):
            where.setdefault(k, "test" if i < n_test else "val" if i < n_test + n_val else "train")
    return where


def fmt_som(x):
    x = round(x)
    return f"{x:,}".replace(",", " ") + " soʻm"


def fmt_num(x):
    s = f"{x:.4f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def render_context(chunks):
    parts = []
    for i, ch in enumerate(chunks, 1):
        ref = ch["metadata"].get("source_reference", "")
        parts.append(f"[{i}] ID: {ch['chunk_id']} | {ref}\n{ch['text']}")
    return "\n\n".join(parts)


def make_user(chunks, question):
    if chunks:
        ctx = render_context(chunks)
    else:
        ctx = "(manba topilmadi)"
    return f"{SYSTEM_RULES}\n\n### Manbalar\n{ctx}\n\n### Savol\n{question}"


def sample(task, key, chunks, question, answer, gold_ids):
    return {
        "task": task,
        "split_key": key,
        "gold_chunk_ids": gold_ids,
        "messages": [
            {"role": "user", "content": make_user(chunks, question)},
            {"role": "assistant", "content": answer},
        ],
    }


def with_distractors(gold, pool, k, exclude=()):
    """gold: chunk list; pool: [(score, chunk)] sorted desc."""
    gid = {g["chunk_id"] for g in gold} | set(exclude)
    ds = [c for _, c in pool if c["chunk_id"] not in gid][:k]
    ctx = gold + ds
    rng.shuffle(ctx)
    return ctx


# ---------------------------------------------------------------- loading
def load(src, v3):
    corpus = [json.loads(l) for l in open(Path(v3) / "rag_corpus_v3.jsonl")]
    table = json.loads((Path(v3) / "state_duty_table_normalized_v3.json").read_text())
    law = json.loads((Path(src) / "law_structured_v2.json").read_text())
    return corpus, table, law


# ---------------------------------------------------------------- fee tasks
RATE_SIMPLE = re.compile(r"^BHMning ([\d]+(?:,\d+)?) (baravari|foizi)$")
RATE_PCT_MIN = re.compile(
    r"^(daʼvo bahosining|shartnoma summasining) ([\d]+(?:,\d+)?) foizi miqdorida, biroq "
    r"BHMning ([\d]+(?:,\d+)?) baravaridan kam boʻlmagan miqdorda$")

FEE_Q = [
    "{op} uchun davlat boji qancha?",
    "{op} — bu holatda davlat boji stavkasi qanday?",
    "Davlat boji: {op}. Qancha toʻlanadi?",
    "Qonun ilovasiga koʻra «{op}» holati uchun davlat bojining miqdori qancha?",
]


def path_text(rec):
    # Bo'lim nomi ham kiradi: "a) mulkiy da'vo" fuqarolik sudida 4%, iqtisodiy sudda 2% — farqlash shart.
    sec = re.sub(r"^\d+\.\s*", "", rec["context_path"][0]).rstrip(":").strip()
    p = [sec] + [x.rstrip(":").strip() for x in rec["context_path"][1:]]
    return " — ".join(p)


def fee_answer(rec, cid):
    return (
        f"{path_text(rec)} uchun davlat boji stavkasi: **{rec['fee_rate_clean']}**.\n\n"
        f"Manba: {LAW_REF}, {TABLE_REF}, {rec['source_row']}-qator [{cid}]."
    )


def parse_mult(s):
    return float(s.replace(",", "."))


def leaf(rec):
    return rec["context_path"][-1].rstrip(":").strip()


def short_op(rec):
    return " — ".join(x.rstrip(":").strip() for x in rec["context_path"][-2:])


def sib_key(rec):
    return (rec["section_title"], tuple(rec["parent_ids"]))


def fee_tasks(fee_chunks, recs, out):
    tok = {c["chunk_id"]: toks(c["text"]) for c in fee_chunks}
    by_path = Counter(path_text(r) for r in recs.values())
    chunk_by_id = {c["chunk_id"]: c for c in fee_chunks}
    short_count = Counter(short_op(r) for r in recs.values())
    siblings = defaultdict(list)
    for c in fee_chunks:
        r = recs[c["chunk_id"]]
        if r["parent_ids"]:
            siblings[sib_key(r)].append(c["chunk_id"])
    # egizak: yo'li eng o'xshash (Jaccard >= 0.8), lekin boshqa qator
    twins = {}
    ptok = {c["chunk_id"]: toks(path_text(recs[c["chunk_id"]])) for c in fee_chunks}
    for c in fee_chunks:
        best = max(((jaccard(ptok[c["chunk_id"]], ptok[o["chunk_id"]]), o["chunk_id"]) for o in fee_chunks
                    if o is not c and path_text(recs[o["chunk_id"]]) != path_text(recs[c["chunk_id"]])),
                   default=(0, None))
        if best[0] >= 0.8:
            twins[c["chunk_id"]] = best[1]
    stats = Counter()
    wrong_rates = [r["fee_rate_clean"] for r in recs.values()]
    for c in fee_chunks:
        cid = c["chunk_id"]
        rec = recs[cid]
        op = path_text(rec)
        sec = rec["context_path"][0]
        key = "fee:" + "/".join(rec["parent_ids"] or [cid])  # siblings stay in one split
        pool = sorted(((jaccard(tok[cid], tok[o["chunk_id"]]), o) for o in fee_chunks if o is not c),
                      key=lambda x: -x[0])[:12]
        siblings_same_text = by_path[op] > 1

        # 1) lookup: 2 paraphrase. v4: ba'zan qisqa savol (oxirgi 2 bo'lak), javobda esa to'liq yo'l
        #    manbadan — model savolni emas, chunkni ko'chirishni o'rganadi.
        short = short_op(rec)
        for i, t in enumerate(rng.sample(FEE_Q, 2)):
            use_short = i == 1 and short_count[short] == 1 and rng.random() < 0.5
            q = t.format(op=short if use_short else op, sec=sec)
            ctx = with_distractors([c], pool, rng.randint(2, 4))
            out.append(sample("fee_lookup_short" if use_short else "fee_lookup", key, ctx, q,
                              fee_answer(rec, cid), [cid]))
            stats["fee_lookup_short" if use_short else "fee_lookup"] += 1

        # 1b) v4 egizak: deyarli bir xil yo'lli boshqa qator kontekstda MAJBURIY
        twin = twins.get(cid)
        if twin and rng.random() < 0.5:
            q = rng.choice(FEE_Q).format(op=op, sec=sec)
            ctx = [c, chunk_by_id[twin]] + [o for _, o in pool if o["chunk_id"] not in (cid, twin)][:rng.randint(1, 2)]
            rng.shuffle(ctx)
            out.append(sample("fee_twin", key, ctx, q, fee_answer(rec, cid), [cid]))
            stats["fee_twin"] += 1

        # 1c) v4 near-miss: so'ralgan qator yo'q, faqat aka-ukalari bor -> rad + mavjudlarini sanash
        sibs = [s for s in siblings[sib_key(rec)] if s != cid and leaf(recs[s]) != leaf(rec)]
        if sibs and rng.random() < 0.7:
            pick = sibs[:5]
            ctx = [chunk_by_id[s] for s in pick]
            rng.shuffle(ctx)
            q = rng.choice(FEE_Q).format(op=op, sec=sec)
            lines = "\n".join(f"- {leaf(recs[s])} — **{recs[s]['fee_rate_clean']}** [{s}]" for s in pick)
            # «» faqat manbadan aynan iqtibos uchun; so'ralgan (manbada yo'q) holat oddiy qo'shtirnoqda
            a = (f"Berilgan manbalarda soʻralgan holat (\"{leaf(rec)}\") uchun davlat boji stavkasi koʻrsatilmagan, "
                 f"shuning uchun uni taxmin qilmayman.\n\nManbalarda faqat quyidagi yaqin holatlar bor:\n"
                 f"{lines}\n\nAgar savolingiz shulardan biriga tegishli boʻlsa, aniqlashtiring.")
            out.append(sample("fee_near_miss", key, ctx, q, a, pick))
            stats["fee_near_miss"] += 1

        # 2) refusal: gold yo'q
        if not siblings_same_text and rng.random() < 0.18:
            q = rng.choice(FEE_Q).format(op=op, sec=sec)
            ctx = with_distractors([], pool, rng.randint(3, 4), exclude=[cid])
            out.append(sample("fee_no_answer", key, ctx, q, NO_ANSWER, []))
            stats["fee_no_answer"] += 1

        # 3) wrong premise
        if rng.random() < 0.25:
            wrong = rng.choice([w for w in wrong_rates if w != rec["fee_rate_clean"]])
            q = f"{op} uchun davlat boji {wrong} miqdorida, toʻgʻrimi?"
            a = (f"Yoʻq, bu notoʻgʻri. Manbaga koʻra, {op} uchun davlat boji stavkasi — "
                 f"**{rec['fee_rate_clean']}** («{wrong}» emas).\n\n"
                 f"Manba: {LAW_REF}, {TABLE_REF}, {rec['source_row']}-qator [{cid}].")
            ctx = with_distractors([c], pool, rng.randint(2, 3))
            out.append(sample("fee_wrong_premise", key, ctx, q, a, [cid]))
            stats["fee_wrong_premise"] += 1

        # 4) hisoblash
        m = RATE_SIMPLE.match(rec["fee_rate_clean"])
        if m and rng.random() < 0.35:
            mult = parse_mult(m.group(1)) * (1 if m.group(2) == "baravari" else 0.01)
            if rng.random() < 0.8:
                bhm = rng.choice([340000, 375000, 412000])
                q = (f"Bazaviy hisoblash miqdori (BHM) {fmt_som(bhm)} deb olinsa, {op} uchun "
                     f"qancha davlat boji toʻlanadi?")
                a = (f"Manbaga koʻra stavka — **{rec['fee_rate_clean']}** [{cid}].\n\n"
                     f"Hisob: {fmt_num(mult)} × {fmt_som(bhm)} = **{fmt_som(mult * bhm)}**.\n\n"
                     f"Eslatma: hisob siz koʻrsatgan BHM qiymati ({fmt_som(bhm)}) asosida qilindi; "
                     f"toʻlov sanasidagi amaldagi BHM qiymatini tekshiring.\n\n"
                     f"Manba: {LAW_REF}, {TABLE_REF}, {rec['source_row']}-qator [{cid}].")
                task = "fee_calc"
            else:
                q = f"{op} uchun necha soʻm davlat boji toʻlashim kerak?"
                a = (f"Manbaga koʻra stavka — **{rec['fee_rate_clean']}** [{cid}].\n\n"
                     f"Summani soʻmda hisoblash uchun toʻlov sanasidagi bazaviy hisoblash miqdori "
                     f"(BHM) qiymati kerak: summa = {fmt_num(mult)} × BHM. Berilgan manbalarda BHM "
                     f"qiymati koʻrsatilmagan, shuning uchun aniq soʻm summasini aytmayman.\n\n"
                     f"Manba: {LAW_REF}, {TABLE_REF}, {rec['source_row']}-qator [{cid}].")
                task = "fee_calc_needs_bhm"
            ctx = with_distractors([c], pool, 2)
            out.append(sample(task, key, ctx, q, a, [cid]))
            stats[task] += 1

        m2 = RATE_PCT_MIN.match(rec["fee_rate_clean"])
        if m2:
            base_name, pct, minm = m2.group(1), parse_mult(m2.group(2)), parse_mult(m2.group(3))
            for _ in range(6):
                bhm = rng.choice([340000, 375000, 412000])
                value = rng.choice([2, 5, 8, 15, 40, 120, 500]) * 1_000_000
                pct_amt, min_amt = value * pct / 100, minm * bhm
                res = max(pct_amt, min_amt)
                q = (f"{op}: daʼvo/shartnoma summasi {fmt_som(value)}, BHM {fmt_som(bhm)}. "
                     f"Davlat boji qancha boʻladi?")
                which = "foiz boʻyicha summa minimal chegaradan katta" if pct_amt >= min_amt \
                    else "foiz boʻyicha summa minimal chegaradan kichik, shuning uchun minimal miqdor olinadi"
                a = (f"Manbaga koʻra stavka — **{rec['fee_rate_clean']}** [{cid}].\n\n"
                     f"Hisob:\n- {fmt_num(pct)}% × {fmt_som(value)} = {fmt_som(pct_amt)}\n"
                     f"- Minimal chegara: {fmt_num(minm)} × {fmt_som(bhm)} = {fmt_som(min_amt)}\n"
                     f"- {which}.\n\nNatija: **{fmt_som(res)}**.\n\n"
                     f"Eslatma: hisob siz koʻrsatgan BHM qiymati asosida; imtiyozlar (8–15-moddalar) "
                     f"qoʻllanishi mumkinligini alohida tekshiring.\n\n"
                     f"Manba: {LAW_REF}, {TABLE_REF}, {rec['source_row']}-qator [{cid}].")
                ctx = with_distractors([c], pool, 2)
                out.append(sample("fee_calc_pct_min", key, ctx, q, a, [cid]))
                stats["fee_calc_pct_min"] += 1
    return stats


# ---------------------------------------------------------------- article tasks
def normative(text):
    return text.split("Normativ matn:", 1)[1].strip() if "Normativ matn:" in text else text


def article_tasks(art_chunks, law, all_chunks, out):
    stats = Counter()
    titles = {a["article"]: a["title"] for a in law["articles"]}
    by_art = defaultdict(list)
    for c in art_chunks:
        by_art[c["metadata"]["article"]].append(c)
    tok = {c["chunk_id"]: toks(c["text"]) for c in all_chunks}
    norm_pool = [c for c in all_chunks if c["metadata"]["chunk_type"] in ("article_normative", "note")]

    for art, chs in by_art.items():
        title = titles.get(art, "")
        key = "art:" + art
        n = len(chs)
        for k, c in enumerate(chs, 1):
            cid = c["chunk_id"]
            pool = sorted(((jaccard(tok[cid], tok[o["chunk_id"]]), o) for o in norm_pool
                           if o["metadata"].get("article") != art), key=lambda x: -x[0])[:10]
            body = normative(c["text"])
            if n == 1:
                qs = [f"{art} («{title}») nima deydi?",
                      f"Davlat boji toʻgʻrisidagi qonunda «{title.lower()}» masalasi qanday belgilangan?",
                      f"«{title}» haqida qonunda nima deyilgan? Matnini keltiring."]
            else:
                qs = [f"{art} («{title}») matnining {k}/{n}-qismini manbadan aynan keltiring."]
            for q in qs:
                a = (f"{art} «{title}» ({k}/{n}-qism):\n\n«{body}»\n\nManba: {LAW_REF}, {art} [{cid}]."
                     if n > 1 else
                     f"{art} «{title}»da quyidagicha belgilangan:\n\n«{body}»\n\nManba: {LAW_REF}, {art} [{cid}].")
                ctx = with_distractors([c], pool, 2)
                out.append(sample("article_quote", key, ctx, q, a, [cid]))
                stats["article_quote"] += 1
        # sarlavha -> modda raqami
        c = chs[0]
        pool = sorted(((jaccard(tok[c["chunk_id"]], tok[o["chunk_id"]]), o) for o in norm_pool
                       if o["metadata"].get("article") != art), key=lambda x: -x[0])[:10]
        q = f"Qonunning qaysi moddasi «{title}» deb nomlanadi?"
        a = f"Bu — {art} «{title}» ({c['metadata'].get('chapter', '')}).\n\nManba: {LAW_REF}, {art} [{c['chunk_id']}]."
        out.append(sample("article_locate", key, with_distractors([c], pool, 3), q, a, [c["chunk_id"]]))
        stats["article_locate"] += 1
    return stats


# ---------------------------------------------------------------- amendment tasks
AMD_RE = re.compile(r"(\d{4})-yil (\d{1,2})-([a-zʻʼ]+?)dagi ((?:OʻRQ|OʻzRQ|PF|PQ|ZRU)-\d+)")


def parse_amd(text):
    m = AMD_RE.search(text)
    if not m:
        return None
    y, d, mon, num = m.groups()
    mo = MONTHS.get(mon.rstrip("d"))
    if not mo:
        return None
    return (int(y), mo, int(d)), f"{y}-yil {d}-{mon}", num


def amd_body(text):
    return text.split("Oʻzgartirishlar tarixi:", 1)[1].strip() if "Oʻzgartirishlar tarixi:" in text else text


def amendment_tasks(amd_chunks, art_chunks, out):
    stats = Counter()
    by_art = defaultdict(list)
    for c in amd_chunks:
        by_art[c["metadata"]["article"]].append(c)
    art_first = {}
    for c in art_chunks:
        art_first.setdefault(c["metadata"]["article"], c)
    by_law = defaultdict(set)
    parsed = {}
    for c in amd_chunks:
        p = parse_amd(c["text"])
        parsed[c["chunk_id"]] = p
        if p:
            by_law[p[2]].add(c["metadata"]["article"])

    def line(c):
        p = parsed[c["chunk_id"]]
        return f"{p[1]} — {p[2]}: {amd_body(c['text'])} [{c['chunk_id']}]" if p \
            else f"{amd_body(c['text'])} [{c['chunk_id']}]"

    for art, chs in by_art.items():
        key = "amd:" + art
        chs = sorted(chs, key=lambda c: parsed[c["chunk_id"]][0] if parsed[c["chunk_id"]] else (9999, 0, 0))
        windows = [chs[i:i + MAX_AMD] for i in range(0, len(chs), MAX_AMD)]
        for w in windows:
            ctx = list(w)
            if art in art_first:
                ctx.append(art_first[art])  # chalg'ituvchi: normativ matn tarix bilan aralashmasin
            rng.shuffle(ctx)
            lines = [f"{i}. {line(c)}" for i, c in enumerate(w, 1)]
            if len(windows) == 1:
                qs = [f"{art}ga qanday oʻzgartirishlar kiritilgan?",
                      f"{art}ning oʻzgartirishlar tarixini sanalar boʻyicha koʻrsating."]
                head = f"{art}ga kiritilgan oʻzgartirishlar (sanalar boʻyicha, jami {len(w)} ta):"
            else:
                d0 = parsed[w[0]["chunk_id"]][1] if parsed[w[0]["chunk_id"]] else "?"
                d1 = parsed[w[-1]["chunk_id"]][1] if parsed[w[-1]["chunk_id"]] else "?"
                qs = [f"{art}ga {d0} dan {d1} gacha kiritilgan oʻzgartirishlarni sanab bering."]
                head = (f"Berilgan manbalarga koʻra, {art}ga {d0} – {d1} oraligʻida kiritilgan "
                        f"oʻzgartirishlar ({len(w)} ta):")
            a = (head + "\n\n" + "\n".join(lines) +
                 "\n\nEslatma: bu oʻzgartirishlar tarixi; amaldagi normativ matn alohida keltiriladi.")
            for q in qs:
                out.append(sample("amendment_history", key, ctx, q, a, [c["chunk_id"] for c in w]))
                stats["amendment_history"] += 1
            # bitta o'zgartirish
            for c in w:
                p = parsed[c["chunk_id"]]
                if not p or rng.random() > 0.5:
                    continue
                q = f"{p[2]} bilan {art}ga qanday oʻzgartirish kiritilgan?"
                same = [x for x in w if parsed[x["chunk_id"]] and parsed[x["chunk_id"]][2] == p[2]]
                a = (f"{p[2]} ({p[1]}) bilan {art}ga quyidagi oʻzgartirish(lar) kiritilgan:\n\n" +
                     "\n".join(f"- {amd_body(x['text'])} [{x['chunk_id']}]" for x in same))
                out.append(sample("amendment_single", key, ctx, q, a, [x["chunk_id"] for x in same]))
                stats["amendment_single"] += 1

    # qonun raqami -> qaysi moddalar (juda ko'p chunkli hujjatlar o'tkazib yuboriladi)
    for num, arts in by_law.items():
        gold = [c for c in amd_chunks if parsed[c["chunk_id"]] and parsed[c["chunk_id"]][2] == num]
        if len(gold) > MAX_AMD:
            continue
        others = [c for c in amd_chunks if c not in gold]
        ctx = gold + rng.sample(others, min(3, len(others)))
        rng.shuffle(ctx)
        arts_sorted = sorted(arts, key=lambda s: (int(re.match(r"\d+", s).group()), s))
        a = (f"{num} bilan OʻRQ-600ning quyidagi moddalariga oʻzgartirish kiritilgan: "
             f"{', '.join(arts_sorted)}.\n\nManbalar: " + ", ".join(f"[{c['chunk_id']}]" for c in gold) + ".")
        q = f"{num}-sonli hujjat bilan Davlat boji toʻgʻrisidagi qonunning qaysi moddalari oʻzgartirilgan?"
        out.append(sample("amendment_by_law", "amdlaw:" + num, ctx, q, a, [c["chunk_id"] for c in gold]))
        stats["amendment_by_law"] += 1
    return stats


# ---------------------------------------------------------------- out of scope
OOS = [
    ("Soliq kodeksi", "Qoʻshilgan qiymat soligʻi stavkasi hozir necha foiz?"),
    ("Soliq kodeksi", "Jismoniy shaxslardan olinadigan daromad soligʻi stavkasi qancha?"),
    ("Soliq kodeksi", "Mol-mulk soligʻini qachongacha toʻlash kerak?"),
    ("Mehnat kodeksi", "Ishdan boʻshatishda ish beruvchi necha kun oldin ogohlantirishi shart?"),
    ("Mehnat kodeksi", "Yillik mehnat taʼtilining eng kam muddati qancha?"),
    ("Jinoyat kodeksi", "Firibgarlik uchun qanday jazo belgilangan?"),
    ("Maʼmuriy javobgarlik toʻgʻrisidagi kodeks", "Qizil chiroqdan oʻtganlik uchun jarima qancha?"),
    ("Oila kodeksi", "Aliment miqdori qanday belgilanadi?"),
    ("Fuqarolik kodeksi", "Da'vo muddati umumiy qoidaga koʻra necha yil?"),
    ("Bojxona kodeksi", "Chet eldan avtomobil olib kirishda bojxona boji qancha?"),
    ("Uy-joy kodeksi", "Kvartirani xususiylashtirish tartibi qanday?"),
    ("Pensiya taʼminoti toʻgʻrisidagi qonun", "Pensiyaga chiqish yoshi necha?"),
]


def oos_tasks(all_chunks, out):
    stats = Counter()
    for topic, q in OOS:
        for _ in range(3):
            ctx = rng.sample(all_chunks, 3)
            a = OUT_OF_SCOPE.format(topic=topic, law=LAW_REF)
            out.append(sample("out_of_scope", "oos:" + q, ctx, q, a, []))
            stats["out_of_scope"] += 1
    return stats


# ---------------------------------------------------------------- validation
def _load_verifier():
    import importlib.util
    spec = importlib.util.spec_from_file_location("verifier", Path(__file__).with_name("verifier.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def validate(samples, chunk_text):
    errors = []
    ver = _load_verifier()
    for i, s in enumerate(samples):
        u, a = s["messages"][0]["content"], s["messages"][1]["content"]
        for p in ver.verify(u, a):
            errors.append((i, s["task"], "verifier: " + p))
        for cid in re.findall(r"\[(ORQ600_[A-Z0-9_]+)\]", a):
            if f"ID: {cid} " not in u:
                errors.append((i, s["task"], f"javobdagi {cid} kontekstda yoʻq"))
        for g in s["gold_chunk_ids"]:
            if f"ID: {g} " not in u:
                errors.append((i, s["task"], f"gold {g} kontekstda yoʻq"))
        if s["task"] in ("fee_lookup", "fee_lookup_short", "fee_twin", "fee_wrong_premise", "fee_calc",
                         "fee_calc_needs_bhm", "fee_calc_pct_min"):
            rate = re.search(r"\*\*(.+?)\*\*", a).group(1)
            if rate not in chunk_text[s["gold_chunk_ids"][0]]:
                errors.append((i, s["task"], "stavka manba matnida yoʻq"))
        if s["task"] == "article_quote":
            quote = re.search(r":\n\n«(.+)»\n\nManba", a, re.S).group(1)
            if quote not in chunk_text[s["gold_chunk_ids"][0]]:
                errors.append((i, s["task"], "iqtibos manba bilan mos emas"))
        if s["task"] in ("fee_no_answer",) and re.search(r"BHMning \d", a):
            errors.append((i, s["task"], "refusal ichida stavka bor"))
    return errors


def main(src, v3, dst):
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    corpus, table, law = load(src, v3)
    recs = {r["record_id"]: r for r in table["records"]
            if r["type"] == "fee_entry" and not r.get("needs_review")}
    fee_chunks = [c for c in corpus if c["chunk_id"] in recs]
    art_chunks = [c for c in corpus if c["metadata"]["chunk_type"] == "article_normative"]
    amd_chunks = [c for c in corpus if c["metadata"]["chunk_type"] == "amendment_history"]
    chunk_text = {c["chunk_id"]: c["text"] for c in corpus}

    out = []
    stats = Counter()
    stats += fee_tasks(fee_chunks, recs, out)
    stats += article_tasks(art_chunks, law, corpus, out)
    stats += amendment_tasks(amd_chunks, art_chunks, out)
    stats += oos_tasks(corpus, out)

    errors = validate(out, chunk_text)
    if errors:
        for e in errors[:30]:
            print("XATO", e)
        raise SystemExit(f"{len(errors)} ta validatsiya xatosi")

    where = assign_splits(out)
    splits = defaultdict(list)
    for s in out:
        splits[where[s["split_key"]]].append(s)
    for name, rows in splits.items():
        rng.shuffle(rows)
        with open(dst / f"lexai_sft_{name}.jsonl", "w") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    lens = sorted(len(s["messages"][0]["content"]) + len(s["messages"][1]["content"]) for s in out)
    report = {
        "seed": SEED,
        "total": len(out),
        "by_task": dict(stats),
        "by_split": {k: len(v) for k, v in splits.items()},
        "by_split_task": {k: dict(Counter(s["task"] for s in v)) for k, v in splits.items()},
        "chars_p50": lens[len(lens) // 2],
        "chars_p95": lens[int(len(lens) * 0.95)],
        "chars_max": lens[-1],
        "excluded_review_records": table["review_items"],
        "validation_errors": 0,
    }
    (dst / "dataset_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1))
    print(json.dumps(report, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:4])
