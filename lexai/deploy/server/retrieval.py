"""
LexAI — gibrid qidiruv (BM25 + multilingual-e5-large/FAISS), RRF bilan birlashtirish.

* BM25 sof Python'da (pickle yo'q — pickle fayllarni boshqa mashinada ochish xavfli).
* Dense qismi ixtiyoriy: `index.faiss` va e5 modeli bo'lmasa faqat BM25 ishlaydi
  (lokal sinov uchun qulay).
* Indeks `kaggle_build_and_upload.py` da quriladi: passage'lar "passage: " prefiksi bilan,
  so'rov esa "query: " prefiksi bilan (e5 talabi) kodlanadi.
"""
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

TOKEN_RE = re.compile(r"[a-zA-Zʻʼ0-9¹²³⁴⁵]+")


ARTICLE_RE = re.compile(r"(\d+[¹²³]?)\s*-\s*modda", re.I)
AMEND_RE = re.compile(r"oʻzgartir|o'zgartir|o‘zgartir|ozgartir|tahrir", re.I)
STEM = 5 # o'zbek tili qo'shimchali: "qaytariladi"/"qaytarish", "nikohdan"/"nikohni" -> umumiy prefiks


OG_APOS = re.compile(r"(?<=[oOgG])['’‘ʼ`]")   # o' g' -> oʻ gʻ (korpusdagi kabi)
OTHER_APOS = re.compile(r"['’`]")              # da'vo -> daʼvo


def normalize(s):
    return OTHER_APOS.sub("ʼ", OG_APOS.sub("ʻ", s))


def tokenize(s):
    out = []
    for t in TOKEN_RE.findall(normalize(s)):
        t = t.lower()
        out.append(t[:STEM] if len(t) > STEM and not t[0].isdigit() else t)
    return out


class BM25:
    def __init__(self, docs, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(tokenize(d)) for d in docs]
        self.len = [sum(t.values()) for t in self.tf]
        self.avg = sum(self.len) / max(1, len(self.len))
        df = Counter(w for t in self.tf for w in t)
        n = len(docs)
        self.idf = {w: math.log(1 + (n - f + 0.5) / (f + 0.5)) for w, f in df.items()}

    def search(self, query, k):
        q = tokenize(query)
        scores = []
        for i, tf in enumerate(self.tf):
            s = 0.0
            for w in q:
                f = tf.get(w)
                if f:
                    s += self.idf[w] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * self.len[i] / self.avg))
            if s > 0:
                scores.append((s, i))
        scores.sort(reverse=True)
        return [i for _, i in scores[:k]]


class Retriever:
    def __init__(self, data_dir, embed_model=None, device="cuda"):
        data_dir = Path(data_dir)
        self.chunks = [json.loads(l) for l in open(data_dir / "rag_corpus_v3.jsonl")]
        self.bm25 = BM25([c["text"] for c in self.chunks])
        self.faiss_index = None
        self.encoder = None
        idx_path = data_dir / "index" / "law_index_v3.faiss"
        if embed_model and idx_path.exists():
            import faiss
            from sentence_transformers import SentenceTransformer
            self.faiss_index = faiss.read_index(str(idx_path))
            ids = json.loads((data_dir / "index" / "chunk_ids_v3.json").read_text())
            assert ids == [c["chunk_id"] for c in self.chunks], "indeks va korpus tartibi mos emas"
            self.encoder = SentenceTransformer(embed_model, device=device)

    def dense(self, query, k):
        v = self.encoder.encode(["query: " + query], normalize_embeddings=True)
        _, I = self.faiss_index.search(v.astype("float32"), k)
        return [int(i) for i in I[0] if i >= 0]

    def routed(self, query, pool):
        """Qoidaviy yo'naltirish: savolda "N-modda" bo'lsa, o'sha moddaning chunklari.
        "o'zgartirish" so'ralsa — o'zgartirishlar tarixi, aks holda normativ matn."""
        m = ARTICLE_RE.search(query)
        if not m:
            return []
        art = m.group(1) + "-modda"
        want = "amendment_history" if AMEND_RE.search(query) else "article_normative"
        hits = [i for i, c in enumerate(self.chunks)
                if c["metadata"].get("article") == art and c["metadata"]["chunk_type"] == want]
        if not hits:
            return []
        # bir modda ichida BM25 bo'yicha tartiblash
        order = {i: r for r, i in enumerate(self.bm25.search(query, len(self.chunks)))}
        return sorted(hits, key=lambda i: order.get(i, 10 ** 6))[:pool]

    def search(self, query, k=4, pool=20, rrf_k=60):
        routed = self.routed(query, pool)
        if routed:
            return [self.chunks[i] for i in routed[:max(k, 8)]]
        ranked = [self.bm25.search(query, pool)]
        if self.faiss_index is not None:
            ranked.append(self.dense(query, pool))
        score = defaultdict(float)
        for lst in ranked:
            for r, i in enumerate(lst):
                score[i] += 1.0 / (rrf_k + r + 1)
        top = sorted(score, key=lambda i: -score[i])[:k]
        return [self.chunks[i] for i in top]
