"""
LexAI — davlat boji jadvalini tuzatish (v2 -> v3).

Muammo (v2): 227 ta yozuvda `fee_rate == legal_operation`. Bular aslida guruh
sarlavhalari (stavkasi yo'q), haqiqiy stavkalar keyingi qatorlarda. Natijada
"jismoniy shaxs tomonidan — BHMning 2 baravari" kabi qatorlar qaysi harakatga
tegishli ekanini yo'qotgan.

Yechim (v3):
  * sarlavha qatorlari  -> type = "fee_group_heading", fee_rate = None
  * stavkali qatorlar   -> type = "fee_entry" + `context_path` (bo'lim > ... > harakat)
  * RAG korpusidagi fee chunklari to'liq yo'l bilan qayta yoziladi
    (embedding/FAISS/BM25 ni Kaggle'da QAYTA QURISH kerak).

Ierarxiya evristikasi (asl HTML'dagi chekinish yo'qolgan, shuning uchun taxminiy):
  1. "a)", "b¹)" kabi harf belgili qator — bo'lim ostidagi yuqori daraja; stek tozalanadi.
  2. Oldingi qator ham sarlavha bo'lsa — yangi sarlavha uning bolasi.
  3. Keyingi qator sarlavha bo'lsa (guruhlar guruhi) — harf-belgili darajagacha qaytiladi.
  4. Aks holda (bevosita stavkali bolalari bor) — oldingi shu turdagi sarlavhaning qo'shnisi.
Har bir guruh `review/fee_hierarchy_review.tsv` ga yoziladi — LexUZ bilan tekshirish uchun.

Ishlatish:
  python3 -I fix_fee_table.py <LexHackaton papkasi> <chiqish papkasi>
"""
import json
import re
import sys
from pathlib import Path

MARKER = re.compile(r"^[a-zʼʻ'’]{1,3}[¹²³⁴⁵⁶⁷⁸⁹]*\)\s")
LAW_PREFIX = "Oʻzbekiston Respublikasining OʻRQ-600-sonli Davlat boji toʻgʻrisida Qonuniga ilova."


def is_heading(rec):
    return (
        rec.get("type") == "fee_entry"
        and rec.get("fee_rate", "").strip() == rec.get("legal_operation", "").strip()
    )


def clean_rate(s):
    return re.sub(r"^[—–-]\s*", "", s.strip())


def build_hierarchy(records):
    out = []
    stack = []  # [(record_id, text, kind)] kind: "marker" | "g2" | "g1"
    prev_heading = False
    review = []
    n = len(records)
    for i, rec in enumerate(records):
        rec = dict(rec)
        t = rec["type"]
        if t == "section_heading":
            stack, prev_heading = [], False
            out.append(rec)
            continue
        if t != "fee_entry":  # notes
            out.append(rec)
            continue

        op = rec["legal_operation"].strip()
        if is_heading(rec):
            nxt = next((r for r in records[i + 1:] if r["type"] != "note"), None)
            next_is_heading = nxt is not None and is_heading(nxt)
            if MARKER.match(op):
                stack = [(rec["record_id"], op, "marker")]
            elif prev_heading:
                stack.append((rec["record_id"], op, "g2" if next_is_heading else "g1"))
            elif next_is_heading:
                while stack and stack[-1][2] != "marker":
                    stack.pop()
                stack.append((rec["record_id"], op, "g2"))
            else:
                while stack and stack[-1][2] == "g1":
                    stack.pop()
                stack.append((rec["record_id"], op, "g1"))
            rec["type"] = "fee_group_heading"
            rec["fee_rate"] = None
            rec["parent_ids"] = [s[0] for s in stack[:-1]]
            prev_heading = True
            out.append(rec)
            continue

        # stavkali qator
        if MARKER.match(op):
            stack = []
        rec["parent_ids"] = [s[0] for s in stack]
        rec["context_path"] = [rec["section_title"].rstrip(":")] + [s[1] for s in stack] + [op]
        rec["fee_rate_clean"] = clean_rate(rec["fee_rate"])
        prev_heading = False
        out.append(rec)

    # bolalar soni va review jadvali
    by_id = {r["record_id"]: r for r in out}
    children = {r["record_id"]: [] for r in out if r["type"] == "fee_group_heading"}
    for r in out:
        if r["type"] == "fee_entry" and r["parent_ids"]:
            children[r["parent_ids"][-1]].append(r["record_id"])
        if r["type"] == "fee_group_heading" and r["parent_ids"]:
            children[r["parent_ids"][-1]].append(r["record_id"])
    for hid, ch in children.items():
        by_id[hid]["child_ids"] = ch
        h = by_id[hid]
        review.append([
            hid,
            " > ".join(by_id[p]["legal_operation"][:60] for p in h["parent_ids"]) or "-",
            h["legal_operation"][:90],
            str(len(ch)),
            "; ".join(f'{by_id[c]["legal_operation"][:40]} = {by_id[c].get("fee_rate_clean") or "(guruh)"}' for c in ch)[:300],
        ])
    return out, review


def rate_looks_valid(s):
    return bool(re.search(r"bhm|foiz|baravar|%|soʻm|so'm|ozod|undirilmaydi|stavka|bepul", s.lower()))


def fee_chunk_text(rec):
    path = rec["context_path"]
    body = " > ".join(path[1:])
    return (
        f"{LAW_PREFIX} Boʻlim: {rec['section_title']} "
        f"Huquqiy harakat: {body}. Davlat boji stavkasi: {rec['fee_rate_clean']}"
    )


def main(src, dst):
    src, dst = Path(src), Path(dst)
    (dst / "review").mkdir(parents=True, exist_ok=True)
    table = json.loads((src / "state_duty_table_normalized_v2.json").read_text())
    records, review = build_hierarchy(table["records"])

    leaves = [r for r in records if r["type"] == "fee_entry"]
    heads = [r for r in records if r["type"] == "fee_group_heading"]
    suspicious = [r for r in leaves if not rate_looks_valid(r["fee_rate_clean"])]
    empty_heads = [h for h in heads if not h.get("child_ids")]
    for r in suspicious:
        r["needs_review"] = "fee_rate maydonida stavka belgisi yo'q"
    for h in empty_heads:
        h["needs_review"] = "guruh sarlavhasining bolasi topilmadi"

    table["records"] = records
    table["version"] = "v3"
    table["statistics"] = {
        "total_records": len(records),
        "sections": sum(r["type"] == "section_heading" for r in records),
        "fee_entries": len(leaves),
        "fee_group_headings": len(heads),
        "notes": sum(r["type"] == "note" for r in records),
        "review_required": len(suspicious) + len(empty_heads),
    }
    table["review_items"] = [r["record_id"] for r in suspicious + empty_heads]
    (dst / "state_duty_table_normalized_v3.json").write_text(json.dumps(table, ensure_ascii=False, indent=1))

    with open(dst / "review" / "fee_hierarchy_review.tsv", "w") as f:
        f.write("heading_id\tparents\theading\tn_children\tchildren\n")
        for row in review:
            f.write("\t".join(x.replace("\t", " ") for x in row) + "\n")

    # RAG korpusi v3: fee chunklarini to'liq yo'l bilan qayta yozish, sarlavhalarni olib tashlash
    leaf_by_id = {r["record_id"]: r for r in leaves}
    head_ids = {h["record_id"] for h in heads}
    n_rewritten = n_dropped = 0
    with open(src / "rag_corpus_v2_fixed.jsonl") as fin, open(dst / "rag_corpus_v3.jsonl", "w") as fout:
        for line in fin:
            ch = json.loads(line)
            cid = ch["chunk_id"]
            if cid in head_ids:
                n_dropped += 1
                continue
            if cid in leaf_by_id:
                rec = leaf_by_id[cid]
                ch["text"] = fee_chunk_text(rec)
                ch["metadata"]["context_path"] = rec["context_path"]
                ch["metadata"]["fee_rate"] = rec["fee_rate_clean"]
                n_rewritten += 1
            fout.write(json.dumps(ch, ensure_ascii=False) + "\n")

    print(json.dumps(table["statistics"], ensure_ascii=False))
    print(f"korpus v3: {n_rewritten} fee chunk qayta yozildi, {n_dropped} sarlavha chunk olib tashlandi")
    print(f"shubhali stavkalar: {len(suspicious)}, bolasiz sarlavhalar: {len(empty_heads)}")
    for r in suspicious:
        print("  REVIEW", r["record_id"], "|", r["legal_operation"][:60], "|", r["fee_rate_clean"][:60])
    for h in empty_heads:
        print("  REVIEW (bolasiz)", h["record_id"], "|", h["legal_operation"][:80])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
