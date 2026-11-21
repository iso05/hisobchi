"""
Kaggle -> AWS S3: v3 RAG indeksini quradi va deploy uchun barcha fayllarni S3'ga yuklaydi.
Lokal kompyuterga hech narsa yuklab olinmaydi.

Kaggle'da oldin: Add-ons -> Secrets ga qo'shing (kod ichiga kalit YOZMANG):
    AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, LEXAI_S3_BUCKET

Ishlatish (Kaggle katagi):
    !pip install -q faiss-cpu sentence-transformers boto3
    !python deploy/kaggle_build_and_upload.py \
        --adapter /kaggle/working/lexai_lora \
        --base "$LEXAI_BASE_MODEL" \
        --with-base

--with-base: trening qilingan AYNAN o'sha bazaviy model papkasini ham S3'ga yuklaydi (~10 GB).
            Shunda EC2'da HuggingFace token/litsenziya kerak bo'lmaydi va vaznlar bir xil bo'ladi.
            Bersangiz, adapter_config.json dagi base yo'li /opt/lexai/base_model ga almashtiriladi.
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # lexai_finetune/
EC2_BASE = "/opt/lexai/base_model"


def secrets():
    try:
        from kaggle_secrets import UserSecretsClient
        c = UserSecretsClient()
        get = c.get_secret
    except ImportError:  # Kaggle tashqarisida — muhit o'zgaruvchilari
        get = os.environ.get
    keys = ["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "LEXAI_S3_BUCKET"]
    vals = {k: get(k) for k in keys}
    missing = [k for k, v in vals.items() if not v]
    if missing:
        sys.exit(f"Secrets yetishmayapti: {missing} (Kaggle: Add-ons -> Secrets)")
    return vals


def build_index(corpus_path, out_dir, model_name):
    import faiss
    from sentence_transformers import SentenceTransformer
    chunks = [json.loads(l) for l in open(corpus_path)]
    enc = SentenceTransformer(model_name, device="cuda")
    emb = enc.encode(["passage: " + c["text"] for c in chunks], batch_size=32,
                     normalize_embeddings=True, show_progress_bar=True).astype("float32")
    index = faiss.IndexFlatIP(emb.shape[1])
    index.add(emb)
    out_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(out_dir / "law_index_v3.faiss"))
    (out_dir / "chunk_ids_v3.json").write_text(json.dumps([c["chunk_id"] for c in chunks]))
    print(f"indeks: {index.ntotal} vektor, dim={emb.shape[1]}")


def stage(args):
    st = Path("/kaggle/working/lexai_deploy") if Path("/kaggle").exists() else Path("lexai_deploy")
    if st.exists():
        shutil.rmtree(st)
    (st / "app").mkdir(parents=True)
    (st / "data").mkdir()

    # server kodi + prompt/verifier (trening bilan bir xil fayllar)
    for f in ["app.py", "retrieval.py"]:
        shutil.copy(HERE / "server" / f, st / "app" / f)
    for f in ["build_sft.py", "verifier.py"]:
        shutil.copy(ROOT / f, st / "app" / f)
    shutil.copy(HERE / "server" / "requirements.txt", st / "app" / "requirements.txt")
    shutil.copy(HERE / "ec2_setup.sh", st / "ec2_setup.sh")

    shutil.copy(ROOT / "data_v3" / "rag_corpus_v3.jsonl", st / "data" / "rag_corpus_v3.jsonl")
    build_index(st / "data" / "rag_corpus_v3.jsonl", st / "data" / "index", args.embed_model)

    # LoRA adapter (checkpoint papkalarisiz) + base yo'lini EC2 uchun to'g'rilash
    shutil.copytree(args.adapter, st / "lora", ignore=shutil.ignore_patterns("checkpoint-*"))
    cfg_path = st / "lora" / "adapter_config.json"
    cfg = json.loads(cfg_path.read_text())
    print("adapter base (Kaggle):", cfg.get("base_model_name_or_path"))
    cfg["base_model_name_or_path"] = EC2_BASE if args.with_base else args.hf_base
    cfg_path.write_text(json.dumps(cfg, indent=2))
    print("adapter base (EC2):   ", cfg["base_model_name_or_path"])
    return st


def upload(st, base_dir, s):
    import boto3
    s3 = boto3.client("s3", region_name=s["AWS_REGION"], aws_access_key_id=s["AWS_ACCESS_KEY_ID"],
                      aws_secret_access_key=s["AWS_SECRET_ACCESS_KEY"])
    bucket, prefix = s["LEXAI_S3_BUCKET"], "lexai"

    def put_dir(src, dst):
        n = 0
        for p in Path(src).rglob("*"):
            if p.is_file():
                key = f"{prefix}/{dst}/{p.relative_to(src).as_posix()}"
                s3.upload_file(str(p), bucket, key)
                n += 1
        print(f"  s3://{bucket}/{prefix}/{dst}/  <- {n} fayl")

    for d in ["app", "data", "lora"]:
        put_dir(st / d, d)
    s3.upload_file(str(st / "ec2_setup.sh"), bucket, f"{prefix}/ec2_setup.sh")
    if base_dir:
        print("bazaviy model yuklanmoqda (bir necha daqiqa)...")
        put_dir(base_dir, "base_model")
    print("tayyor:", f"s3://{bucket}/{prefix}/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--base", help="trening qilingan bazaviy model papkasi ($LEXAI_BASE_MODEL)")
    ap.add_argument("--with-base", action="store_true")
    ap.add_argument("--hf-base", default="unsloth/gemma-4-E2B-it",
                    help="--with-base bo'lmasa, EC2 shu nomni HuggingFace'dan yuklaydi")
    ap.add_argument("--embed-model", default="intfloat/multilingual-e5-large")
    args = ap.parse_args()
    if args.with_base and not (args.base and Path(args.base, "config.json").exists()):
        sys.exit("--with-base uchun --base papkasida config.json boʻlishi kerak")
    s = secrets()
    st = stage(args)
    upload(st, args.base if args.with_base else None, s)


if __name__ == "__main__":
    main()
