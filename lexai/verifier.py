"""
LexAI — model javobini manbaga nisbatan deterministik tekshirish.

Model javob yozgandan KEYIN ishlatiladi (RAG pipeline'da ham, eval'da ham):

    from verifier import verify, guard
    problems = verify(prompt, answer)      # [] bo'lsa — javob manbaga mos
    safe_answer = guard(prompt, answer)    # mos bo'lmasa — xavfsiz rad javobi

Tekshiruvlar:
  1. Javobdagi har bir [ID] kontekstda bor.
  2. "… uchun davlat boji stavkasi: **X**" da: X va holat (yo'l) bo'laklari aynan
     ko'rsatilgan chunk matnida bor. Bu "uch oygacha" so'ralganda "ikki oygacha"
     stavkasini "uch oygacha" deb berish xatosini ushlaydi.
  3. Ro'yxat qatorlaridagi "… — stavka [ID]" ham o'sha chunkka mos.
  4. «…» ichidagi iqtiboslar (≥ 20 belgi) ko'rsatilgan chunklardan biridan aynan olingan.
  5. "a × b = c" hisoblari qayta hisoblanadi.
  6. Javobdagi har bir "BHMning N baravari/foizi" ko'rsatilgan chunklardan birida bor.
"""
import re

CTX_RE = re.compile(r"\[(\d+)\] ID: (\S+) \| [^\n]*\n(.*?)(?=\n\n\[\d+\] ID: |\n\n### Savol)", re.S)
ID_RE = re.compile(r"\[(ORQ600_[A-Z0-9_]+)\]")
CLAIM_RE = re.compile(r"^(?:.*?Manbaga koʻra, )?(.+?) uchun davlat boji stavkasi(?::| —) \*\*(.+?)\*\*", re.M)
DENIED_RE = re.compile(r"\s*\(«[^«»]*» emas\)")  # wrong-premise: rad etilgan stavka da'vo emas
KNOWN_TITLES = {"davlat boji toʻgʻrisida"}
LIST_RE = re.compile(r"^- (.+) — \*\*(.+?)\*\* \[(ORQ600_[A-Z0-9_]+)\]$", re.M)
QUOTE_RE = re.compile(r"«([^«»]{20,})»")
RATE_RE = re.compile(r"BHMning [\d]+(?:,\d+)? (?:baravari|foizi)")
CALC_RE = re.compile(r"([\d]+(?:,\d+)?)(%?) × ([\d ]+) soʻm = \**([\d ]+) soʻm")

REFUSAL = ("Berilgan manbalarda bu savolga aniq javob topilmadi. Taxminiy stavka yoki raqam "
           "keltira olmayman. Iltimos, savolni aniqlashtiring yoki tegishli manba bilan qayta soʻrang.")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "ʼ")).strip().lower()


def parse_context(prompt):
    return {cid: text for _, cid, text in CTX_RE.findall(prompt)}


def _segments(path):
    return [p.strip(" :.") for p in path.split(" — ") if len(p.strip(" :.")) >= 2]


def verify(prompt, answer):
    ctx = parse_context(prompt)
    nctx = {k: norm(v) for k, v in ctx.items()}
    problems = []
    answer = DENIED_RE.sub("", answer)
    cited = ID_RE.findall(answer)

    for cid in cited:
        if cid not in ctx:
            problems.append(f"{cid} kontekstda yoʻq")
    cited_ok = [c for c in cited if c in ctx]
    cited_text = " \n ".join(nctx[c] for c in cited_ok)

    # 2. asosiy da'vo: yo'l + stavka birinchi keltirilgan chunkka mos bo'lishi kerak
    for m in CLAIM_RE.finditer(answer):
        path, rate = m.group(1), m.group(2)
        if not cited_ok:
            problems.append("stavka aytilgan, lekin manba ID yoʻq")
            break
        own = nctx[cited_ok[0]]
        if norm(rate) not in own:
            problems.append(f"stavka «{rate}» {cited_ok[0]} da yoʻq")
        for seg in _segments(path):
            if norm(seg) not in own:
                problems.append(f"holat «{seg}» {cited_ok[0]} da yoʻq")

    # 3. ro'yxat qatorlari
    for path, rate, cid in LIST_RE.findall(answer):
        if cid not in nctx:
            continue
        if norm(rate) not in nctx[cid]:
            problems.append(f"roʻyxat: stavka «{rate}» {cid} da yoʻq")
        for seg in _segments(path):
            if norm(seg) not in nctx[cid]:
                problems.append(f"roʻyxat: holat «{seg}» {cid} da yoʻq")

    # 4. iqtiboslar
    for q in QUOTE_RE.findall(answer):
        if norm(q) not in KNOWN_TITLES and norm(q) not in cited_text:
            problems.append(f"iqtibos manbada aynan yoʻq: «{q[:60]}…»")

    # 5. hisob-kitob
    for a, pct, b, c in CALC_RE.findall(answer):
        k = float(a.replace(",", ".")) / (100 if pct else 1)
        exp = round(k * int(b.replace(" ", "")))
        got = int(c.replace(" ", ""))
        if abs(exp - got) > 1:
            problems.append(f"hisob xato: {a}{pct} × {b} = {c} (toʻgʻrisi {exp})")

    # 6. har bir BHM stavkasi manbada bo'lishi kerak
    for r in set(RATE_RE.findall(answer)):
        if norm(r) not in cited_text:
            problems.append(f"«{r}» keltirilgan manbalarda yoʻq")

    return problems


def guard(prompt, answer):
    """Tekshiruvdan o'tmagan javob o'rniga xavfsiz rad javobini qaytaradi."""
    return answer if not verify(prompt, answer) else REFUSAL
