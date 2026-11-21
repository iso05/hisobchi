"""
LexAI — Kaggle'da (T4 GPU) Gradio demo + web-app uchun API.

Kaggle katagida:
    !pip install -q gradio faiss-cpu sentence-transformers
    !python lexai/kaggle/gradio_demo.py --adapter /kaggle/working/lexai_lora

Chiqqan https://….gradio.live havolasini Hisobchi backend'ining LEXAI_URL o'zgaruvchisiga yozing.
backend/app/lexai.py `/ask_json` endpoint'ini chaqiradi:
    {"answer", "verified", "mode", "sources": [{"id","reference","text"}], "latency_ms"}

Eslatma: pip gradio Pillow'ni buzsa ("_imaging extension was built for another version"),
    !pip install -q --force-reinstall --no-deps "pillow==<gradio talab qilgan versiya>"
so'ng kernelni qayta ishga tushiring.
"""
import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # lexai/
sys.path[:0] = [str(ROOT / "deploy" / "server"), str(ROOT)]

from build_sft import make_user                      # noqa: E402  trening bilan bir xil prompt
from retrieval import Retriever                      # noqa: E402
from verifier import REFUSAL, verify                 # noqa: E402
import answering                                     # noqa: E402

OUT_OF_SCOPE = ("Bu savol mening hozirgi bilimlar bazamdan tashqarida: men faqat OʻRQ-600 «Davlat boji "
                "toʻgʻrisida»gi Qonun boʻyicha javob beraman. Tegishli qonun hujjatini lex.uz orqali "
                "yoki malakali yurist bilan aniqlashtiring.")
LABELS = {"jadval": "📋 Jadvaldan aniq stavka", "model": "🤖 Model javobi (tekshirilgan)",
          "manba": "📖 Qonun matnidan", "mavzudan_tashqari": "ℹ️ Mavzudan tashqari",
          "rad": "⚠️ Aniq javob topilmadi"}
EXAMPLES = [
    "Ajrashish uchun qancha boj to'lanadi?",
    "Ikkinchi marta ajrashsam qancha boj to'layman?",
    "Mulkiy da'vo arizasi uchun fuqarolik sudiga qancha davlat boji to'lanadi?",
    "Iqtisodiy sudga mulkiy da'vo uchun boj qancha?",
    "Pasport olish uchun davlat boji qancha?",
    "Davlat boji qachon qaytariladi?",
    "Kimlar sudda davlat bojidan ozod qilinadi?",
    "10-moddaga qanday o'zgartirishlar kiritilgan?",
    "Qo'shilgan qiymat solig'i stavkasi qancha?",
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="/kaggle/working/lexai_lora")
    ap.add_argument("--data", default=None, help="rag_corpus_v3.jsonl (+ index/) papkasi")
    ap.add_argument("--embed-model", default="intfloat/multilingual-e5-large")
    ap.add_argument("--no-share", action="store_true")
    args = ap.parse_args()

    data = args.data
    if data is None:
        built = Path("/kaggle/working/lexai_deploy/data")
        data = built if (built / "index" / "law_index_v3.faiss").exists() else ROOT / "data_v3"
    retriever = Retriever(data, embed_model=args.embed_model)
    print("qidiruv:", data, "| dense:", retriever.faiss_index is not None)

    from unsloth import FastModel
    model, tokenizer = FastModel.from_pretrained(args.adapter, max_seq_length=4096, load_in_4bit=True)
    FastModel.for_inference(model)
    tok = getattr(tokenizer, "tokenizer", tokenizer)

    def generate(prompt_text):
        msgs = [{"role": "user", "content": prompt_text}]
        try:
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        except Exception:
            msgs = [{"role": "user", "content": [{"type": "text", "text": prompt_text}]}]
            text = tokenizer.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(text, return_tensors="pt", add_special_tokens=False).to(model.device)
        out = model.generate(**ids, max_new_tokens=512, do_sample=False)
        return tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()

    def core(question):
        t0 = time.time()
        ans, verified, mode, chunks = answering.answer(
            question, retriever, generate, make_user, verify, REFUSAL, OUT_OF_SCOPE)
        return {"answer": ans, "verified": verified, "mode": mode,
                "sources": [{"id": c["chunk_id"], "reference": c["metadata"].get("source_reference", ""),
                             "text": c["text"]} for c in chunks],
                "latency_ms": int((time.time() - t0) * 1000)}

    def ask(question):
        r = core(question)
        sources = "\n\n---\n\n".join(f"**{s['id']}** — {s['reference']}\n\n{s['text'][:700]}" for s in r["sources"])
        return r["answer"], f"{LABELS[r['mode']]} · {r['latency_ms'] / 1000:.1f} s", sources

    import gradio as gr
    with gr.Blocks(title="LexAI") as demo:
        gr.Markdown("# LexAI — davlat boji bo‘yicha huquqiy yordamchi\n"
                    "OʻRQ-600 «Davlat boji toʻgʻrisida»gi Qonun asosida")
        q = gr.Textbox(label="Savol", placeholder="Masalan: Ajrashish uchun qancha boj to'lanadi?")
        btn = gr.Button("So‘rash", variant="primary")
        ans = gr.Markdown()
        stat = gr.Markdown()
        with gr.Accordion("Manbalar", open=False):
            src = gr.Markdown()
        gr.Examples(EXAMPLES, inputs=q)
        btn.click(ask, q, [ans, stat, src], api_name="ask")
        q.submit(ask, q, [ans, stat, src], api_name=False)
        api_in = gr.Textbox(visible=False)
        api_out = gr.JSON(visible=False)
        gr.Button(visible=False).click(core, api_in, api_out, api_name="ask_json")

    demo.queue().launch(share=not args.no_share)


if __name__ == "__main__":
    main()
