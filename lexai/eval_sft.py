"""
LexAI — test to'plamida baholash (bazaviy Gemma vs LoRA adapter).

    # GPU kerak emas: scorer'ni oltin javoblar bilan tekshirish (100% chiqishi kerak)
    python3 -I eval_sft.py --test sft/lexai_sft_test.jsonl --self-test

    # Kaggle: bazaviy model
    python eval_sft.py --test sft/lexai_sft_test.jsonl --model unsloth/gemma-4-E2B-it --out base.jsonl
    # Kaggle: fine-tune qilingan adapter
    python eval_sft.py --test sft/lexai_sft_test.jsonl --model /kaggle/working/lexai_lora --out lora.jsonl
"""
import argparse
import difflib
import json
import re
from collections import defaultdict

REFUSAL_KEYS = ("topilmadi", "bera olmayman", "keltira olmayman", "koʻrsatilmagan")
FEE_TASKS = {"fee_lookup", "fee_lookup_short", "fee_twin", "fee_wrong_premise", "fee_calc",
             "fee_calc_needs_bhm", "fee_calc_pct_min"}


def _load_verifier():
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("verifier", Path(__file__).with_name("verifier.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_refusal(text):
    p = norm(text)
    return any(k in p for k in REFUSAL_KEYS)


def norm(s):
    return re.sub(r"\s+", " ", s.replace("’", "ʼ")).strip().lower()


def bold(s):
    return re.findall(r"\*\*(.+?)\*\*", s)


def score(sample, pred):
    """Bir nechta mezon; har biri 0/1. 'ok' — barcha mezonlar bajarildi."""
    gold = sample["messages"][1]["content"]
    task = sample["task"]
    p = norm(pred)
    r = {}
    if task in FEE_TASKS:
        b = bold(gold)
        r["rate_exact"] = int(norm(b[0]) in p)
        if task in ("fee_calc", "fee_calc_pct_min"):
            r["amount_exact"] = int(norm(b[-1]) in p)
        if task == "fee_wrong_premise":
            r["rejects_premise"] = int(p.startswith("yoʻq") or "notoʻgʻri" in p)
        if task == "fee_calc_needs_bhm":
            r["no_invented_amount"] = int(not re.search(r"\d[\d ]{4,} soʻm", pred))
        r["cites_gold"] = int(all(g.lower() in p for g in sample["gold_chunk_ids"]))
    elif task == "fee_near_miss":
        r["refuses"] = int(any(k in p for k in REFUSAL_KEYS))
        r["lists_alternatives"] = int(all(g.lower() in p for g in sample["gold_chunk_ids"]))
    elif task in ("fee_no_answer", "out_of_scope"):
        r["refuses"] = int(any(k in p for k in REFUSAL_KEYS))
        r["no_rate_leak"] = int(not re.search(r"bhmning \d", p))
    elif task == "article_quote":
        q = re.search(r":\n\n«(.+)»\n\nManba", gold, re.S).group(1)
        nq = norm(q)
        r["quote_sim>=0.9"] = int(nq in p or difflib.SequenceMatcher(None, nq, p, autojunk=False)
                                  .find_longest_match(0, len(nq), 0, len(p)).size >= 0.9 * len(nq))
        r["cites_gold"] = int(all(g.lower() in p for g in sample["gold_chunk_ids"]))
    elif task == "article_locate":
        art = re.match(r"Bu — (\S+)", gold).group(1)
        r["article"] = int(norm(art) in p)
        r["cites_gold"] = int(all(g.lower() in p for g in sample["gold_chunk_ids"]))
    elif task.startswith("amendment"):
        laws = set(re.findall(r"OʻRQ-\d+", gold))
        r["laws_all"] = int(all(norm(l) in p for l in laws))
        r["cites_gold"] = int(all(g.lower() in p for g in sample["gold_chunk_ids"]))
    r["ok"] = int(all(r.values()))
    return r


def report(rows):
    agg = defaultdict(lambda: defaultdict(list))
    for task, r in rows:
        for k, v in r.items():
            agg[task][k].append(v)
            agg["_ALL_"][k].append(v)
    for task in sorted(agg):
        parts = ", ".join(f"{k}={sum(v)}/{len(v)}" for k, v in agg[task].items())
        print(f"{task:22s} {parts}")


def generate_all(model_path, samples, max_new_tokens):
    from unsloth import FastModel
    model, tokenizer = FastModel.from_pretrained(model_name=model_path, max_seq_length=4096, load_in_4bit=True)
    FastModel.for_inference(model)
    tok = getattr(tokenizer, "tokenizer", tokenizer)
    preds = []
    for i, s in enumerate(samples):
        msgs = [s["messages"][0]]
        try:
            prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:
            msgs = [{"role": "user", "content": [{"type": "text", "text": s["messages"][0]["content"]}]}]
            prompt = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(prompt, return_tensors="pt", add_special_tokens=False).to(model.device)
        out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False)
        preds.append(tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True))
        if i % 10 == 0:
            print(f"{i}/{len(samples)}")
    return preds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True)
    ap.add_argument("--model")
    ap.add_argument("--out")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--preds", help="oldingi --out faylidan javoblarni olib, GPU'siz qayta baholash")
    ap.add_argument("--max_new_tokens", type=int, default=768)
    a = ap.parse_args()
    samples = [json.loads(l) for l in open(a.test)]
    if a.self_test:
        preds = [s["messages"][1]["content"] for s in samples]
    elif a.preds:
        preds = [json.loads(l)["pred"] for l in open(a.preds)]
        assert len(preds) == len(samples), "preds va test soni mos emas (boshqa test faylimi?)"
    else:
        preds = generate_all(a.model, samples, a.max_new_tokens)

    ver = _load_verifier()
    prompts = [s["messages"][0]["content"] for s in samples]
    problems = [ver.verify(u, p) for u, p in zip(prompts, preds)]
    guarded = [ver.guard(u, p) for u, p in zip(prompts, preds)]

    rows = [(s["task"], score(s, p)) for s, p in zip(samples, preds)]
    print("### XOM JAVOBLAR (model chiqishi)")
    report(rows)

    rows_g = [(s["task"], score(s, g)) for s, g in zip(samples, guarded)]
    print("\n### TEKSHIRUVCHIDAN KEYIN (verifier.guard)")
    report(rows_g)

    caught = sum(1 for (_, r), pr in zip(rows, problems) if not r["ok"] and pr)
    false_alarm = sum(1 for (_, r), pr in zip(rows, problems) if r["ok"] and pr)
    unsafe = sum(1 for (_, r), g in zip(rows_g, guarded) if not r["ok"] and not is_refusal(g))
    wrong = sum(1 for _, r in rows if not r["ok"])
    print(f"\nxato javoblar: {wrong} | tekshiruvchi ushladi: {caught} | "
          f"toʻgʻri javobni keraksiz bloklagan: {false_alarm} | "
          f"tekshiruvdan keyin ham xato VA rad emas (xavfli): {unsafe}")

    if a.out:
        with open(a.out, "w") as f:
            for s, p, (_, r), pr in zip(samples, preds, rows, problems):
                f.write(json.dumps({"task": s["task"], "pred": p, "gold": s["messages"][1]["content"],
                                    "score": r, "verifier": pr}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
