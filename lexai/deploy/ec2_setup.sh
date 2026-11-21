#!/usr/bin/env bash
# LexAI — EC2 GPU serverni sozlash.
# AMI: "Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)" — NVIDIA drayverlari tayyor.
# Instance: g4dn.xlarge (T4, Kaggle bilan bir xil) yoki g5.xlarge (A10G, tezroq).
# Instance'ga S3'dan o'qish huquqi bor IAM role biriktirilgan bo'lishi kerak.
#
# Ishlatish (EC2 ichida, ubuntu foydalanuvchisi):
#   aws s3 cp s3://<BUCKET>/lexai/ec2_setup.sh . && bash ec2_setup.sh <BUCKET> [https://webapp-origin]
set -euo pipefail

BUCKET="${1:?bucket nomini bering}"
CORS_ORIGINS="${2:-}"
ROOT=/opt/lexai

sudo mkdir -p "$ROOT" && sudo chown "$USER":"$USER" "$ROOT"

echo "== S3'dan fayllar"
aws s3 sync "s3://$BUCKET/lexai/" "$ROOT/" --exclude "ec2_setup.sh"
nvidia-smi --query-gpu=name,memory.total --format=csv

echo "== Python muhit"
sudo apt-get update -y -qq && sudo apt-get install -y -qq python3-venv >/dev/null
python3 -m venv "$ROOT/venv"
"$ROOT/venv/bin/pip" install -q --upgrade pip
"$ROOT/venv/bin/pip" install -q -r "$ROOT/app/requirements.txt"

echo "== .env"
if [ ! -f "$ROOT/.env" ]; then
  KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
  cat > "$ROOT/.env" <<EOF
LEXAI_ADAPTER_DIR=$ROOT/lora
LEXAI_DATA_DIR=$ROOT/data
LEXAI_EMBED_MODEL=intfloat/multilingual-e5-large
LEXAI_API_KEY=$KEY
LEXAI_CORS_ORIGINS=$CORS_ORIGINS
LEXAI_TOP_K=4
HF_HOME=$ROOT/hf_cache
EOF
  chmod 600 "$ROOT/.env"
  echo "API kalit $ROOT/.env ichida (LEXAI_API_KEY). Uni web-app backend'ining maxfiy sozlamasiga qo'ying."
fi

echo "== systemd xizmati"
sudo tee /etc/systemd/system/lexai.service >/dev/null <<EOF
[Unit]
Description=LexAI API
After=network-online.target

[Service]
User=$USER
WorkingDirectory=$ROOT/app
EnvironmentFile=$ROOT/.env
ExecStart=$ROOT/venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --workers 1
Restart=on-failure
TimeoutStartSec=900

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now lexai
echo "Xizmat ishga tushdi. Model yuklanishi 2-5 daqiqa oladi. Kuzatish:"
echo "  journalctl -u lexai -f"
echo "  curl localhost:8000/health"
