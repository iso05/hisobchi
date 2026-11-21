"""
LexAI — Gemma 4 E2B IT ni LoRA bilan fine-tune qilish (Kaggle, 2 × T4, Unsloth).

Kaggle'da:
    !pip install -q unsloth
    !python train_gemma4_lora.py --data /kaggle/input/lexai-sft/sft --out /kaggle/working/lexai_lora

Eslatmalar:
  * MODEL_NAME ni notebookingizda hozir ishlayotgan nom bilan bir xil qiling.
  * T4 bf16 ni qo'llamaydi -> fp16 avtomatik tanlanadi.
  * Faqat javob (assistant) tokenlari bo'yicha loss hisoblanadi (train_on_responses_only).
    Chat-template markerlari tokenizerdan avtomatik aniqlanadi va tekshiriladi.
"""
import argparse
import json
import os

MODEL_NAME = os.environ.get("LEXAI_BASE_MODEL", "unsloth/gemma-4-E2B-it")


def load_jsonl(path):
    with open(path) as f:
        return [json.loads(l) for l in f]


def to_template_messages(msgs, list_content):
    if not list_content:
        return [{"role": m["role"], "content": m["content"]} for m in msgs]
    return [{"role": m["role"], "content": [{"type": "text", "text": m["content"]}]} for m in msgs]


def detect_format(tok):
    """Chat template string content qabul qiladimi yoki [{type:text}] ro'yxatmi — aniqlaydi."""
    probe = [{"role": "user", "content": "<<U>>"}, {"role": "assistant", "content": "<<A>>"}]
    for list_content in (False, True):
        try:
            s = tok.apply_chat_template(to_template_messages(probe, list_content), tokenize=False)
            if "<<U>>" in s and "<<A>>" in s:
                return list_content
        except Exception:
            pass
    raise RuntimeError("Chat template user/assistant xabarlarini render qila olmadi")


def detect_markers(tok, list_content):
    full = tok.apply_chat_template(
        to_template_messages([{"role": "user", "content": "<<U>>"}, {"role": "assistant", "content": "<<A>>"}], list_content),
        tokenize=False)
    gen = tok.apply_chat_template(
        to_template_messages([{"role": "user", "content": "<<U>>"}], list_content),
        tokenize=False, add_generation_prompt=True)
    bos = getattr(tok, "bos_token", None) or ""
    instruction_part = full.split("<<U>>")[0].replace(bos, "")
    response_part = gen.split("<<U>>")[1]
    # trening matnida ham aynan shu prefiks bo'lishi kerak
    assert response_part in full.split("<<U>>")[1], (response_part, full)
    return instruction_part, response_part, full


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="lexai_sft_{train,val}.jsonl joylashgan papka")
    ap.add_argument("--out", default="/kaggle/working/lexai_lora")
    ap.add_argument("--max_seq_length", type=int, default=4096)
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--r", type=int, default=16)
    ap.add_argument("--grad_accum", type=int, default=8)
    ap.add_argument("--max_steps", type=int, default=-1, help="tez sinov uchun, masalan 30")
    args = ap.parse_args()

    from unsloth import FastModel
    from unsloth.chat_templates import train_on_responses_only
    import torch
    from datasets import Dataset
    from trl import SFTConfig, SFTTrainer

    model, tokenizer = FastModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=args.max_seq_length,
        load_in_4bit=True,
        full_finetuning=False,
    )
    model = FastModel.get_peft_model(
        model,
        finetune_vision_layers=False,
        finetune_language_layers=True,
        finetune_attention_modules=True,
        finetune_mlp_modules=True,
        r=args.r,
        lora_alpha=args.r,
        lora_dropout=0,
        bias="none",
        random_state=3407,
    )

    tok = getattr(tokenizer, "tokenizer", tokenizer)  # processor bo'lsa ichidagi tokenizer
    list_content = detect_format(tokenizer)
    instruction_part, response_part, probe = detect_markers(tokenizer, list_content)
    print("chat template namunasi:\n", probe)
    print("instruction_part =", repr(instruction_part))
    print("response_part    =", repr(response_part))

    def render(rows):
        texts, dropped = [], 0
        bos = getattr(tok, "bos_token", None) or ""
        for r in rows:
            t = tokenizer.apply_chat_template(to_template_messages(r["messages"], list_content), tokenize=False)
            if bos and t.startswith(bos):
                t = t[len(bos):]  # trainer BOS ni o'zi qo'shadi — ikki marta bo'lmasin
            if len(tok(t)["input_ids"]) > args.max_seq_length:
                dropped += 1
                continue
            texts.append({"text": t})
        return Dataset.from_list(texts), dropped

    train_ds, d1 = render(load_jsonl(os.path.join(args.data, "lexai_sft_train.jsonl")))
    val_ds, d2 = render(load_jsonl(os.path.join(args.data, "lexai_sft_val.jsonl")))
    print(f"train={len(train_ds)} val={len(val_ds)}  (max_seq_length dan uzun, tashlandi: {d1}+{d2})")

    fp16 = not torch.cuda.is_bf16_supported()
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        args=SFTConfig(
            dataset_text_field="text",
            max_seq_length=args.max_seq_length,
            per_device_train_batch_size=1,
            per_device_eval_batch_size=1,
            gradient_accumulation_steps=args.grad_accum,
            num_train_epochs=args.epochs,
            max_steps=args.max_steps,
            learning_rate=args.lr,
            lr_scheduler_type="cosine",
            warmup_ratio=0.05,
            weight_decay=0.01,
            optim="adamw_8bit",
            fp16=fp16,
            bf16=not fp16,
            logging_steps=10,
            eval_strategy="steps",
            eval_steps=50,
            save_strategy="steps",
            save_steps=100,
            save_total_limit=2,
            output_dir=args.out + "_ckpt",
            report_to="none",
            seed=3407,
        ),
    )
    trainer = train_on_responses_only(trainer, instruction_part=instruction_part, response_part=response_part)

    # Maskalash to'g'ri ishlayotganini tekshirish: label'lar faqat javobni qamrashi kerak
    ex = trainer.train_dataset[0]
    labels = [t for t in ex["labels"] if t != -100]
    assert labels, "Barcha label'lar -100: response_part topilmadi, markerlarni tekshiring"
    print("label namunasi (javob boshi):", tok.decode(labels[:60]))

    trainer.train()
    model.save_pretrained(args.out)
    tokenizer.save_pretrained(args.out)
    print("LoRA adapter saqlandi:", args.out)
    # Ixtiyoriy:
    # model.save_pretrained_merged(args.out + "_merged16", tokenizer, save_method="merged_16bit")
    # model.save_pretrained_gguf(args.out + "_gguf", tokenizer, quantization_method="q4_k_m")


if __name__ == "__main__":
    main()
