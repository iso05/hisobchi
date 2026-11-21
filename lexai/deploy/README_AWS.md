# LexAI — Kaggle → AWS deploy

```
Kaggle notebook ──(boto3, Secrets)──► S3: lexai/{app,data,lora,base_model}
                                           │ (IAM role, faqat o'qish)
Web-app backend ──HTTPS, X-API-Key──► EC2 GPU: FastAPI /ask
                                       qidiruv → Gemma 4 E2B + LoRA → verifier
```

Lokal kompyuterga hech narsa yuklab olinmaydi.

## 0. Birinchi navbatda: GPU kvotasi

Yangi AWS akkauntlarda GPU instance kvotasi ko‘pincha **0** bo‘ladi. Kvotani oshirish so‘rovi bir necha soatdan bir necha kungacha ko‘rib chiqilishi mumkin, shuning uchun uni **hoziroq** yuboring:

Service Quotas → Amazon EC2 → **Running On-Demand G and VT instances** → kamida **4** (vCPU).

`g4dn.xlarge` 4 vCPU talab qiladi.

Region: kvota va narx bo‘yicha qulayini tanlang (masalan, `eu-central-1` — Frankfurt). Qolgan barcha qadamlarda shu regionni ishlating.

## 1. S3 bucket

S3 → Create bucket (masalan, `lexai-deploy-<nom>`), **Block all public access: ON**.

## 2. Kaggle uchun IAM foydalanuvchi (faqat yuklash huquqi bilan)

1. IAM → Users → Create user: `kaggle-uploader`.
2. Inline policy sifatida `iam/kaggle-uploader-policy.json` ni qo‘shing (`BUCKET_NOMI` ni o‘zgartiring).
3. Security credentials → **Create access key**.
4. Kaggle notebookda **Add-ons → Secrets** ga quyidagilarni qo‘shing va notebook uchun ularni yoqing:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION` (masalan, `eu-central-1`)
   - `LEXAI_S3_BUCKET`

Kalitlarni hech qachon notebook kodiga yozmang. Yuklash tugagach, bu kalitni IAM'da **Deactivate** qiling.

## 3. Kaggle: indeks qurish va S3'ga yuklash

LoRA adapter `/kaggle/working/lexai_lora` da bo‘lishi kerak. Agar sessiya qayta ishga tushgan bo‘lsa va adapter yo‘qolgan bo‘lsa, treningni qayta ishga tushiring yoki saqlangan versiya output'ini Input sifatida ulang.

```python
!pip install -q faiss-cpu sentence-transformers boto3
!python deploy/kaggle_build_and_upload.py --adapter /kaggle/working/lexai_lora --base "$LEXAI_BASE_MODEL" --with-base
```

- `--with-base` trening qilingan **aynan o‘sha** bazaviy modelni ham S3'ga yuklaydi (taxminan 10 GB). Shunda EC2'da HuggingFace token ham, litsenziya tasdig‘i ham kerak bo‘lmaydi.
- Skript adapter ichidagi Kaggle yo‘lini (`/kaggle/input/...`) EC2 yo‘li bilan (`/opt/lexai/base_model`) avtomatik almashtiradi. Busiz EC2'da model ochilmaydi.

## 4. EC2 uchun IAM role

IAM → Roles → Create role → AWS service: **EC2** → inline policy `iam/ec2-reader-policy.json`. Role nomi, masalan, `lexai-ec2-reader`.

## 5. EC2 instance

| Sozlama | Qiymat |
|---|---|
| AMI | **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)** |
| Instance | `g4dn.xlarge` (T4 — Kaggle bilan bir xil) yoki `g5.xlarge` (A10G — tezroq) |
| Disk | 100 GB gp3 |
| IAM instance profile | `lexai-ec2-reader` |
| Security group | 22 — faqat o‘z IP'ingiz; 443 (yoki 8000) — faqat web-app backend IP'si |

Instance'ga Elastic IP biriktiring, shunda u qayta ishga tushganda IP o‘zgarmaydi.

## 6. Serverni sozlash

SSH yoki Session Manager orqali ulanib:

```bash
aws s3 cp s3://BUCKET_NOMI/lexai/ec2_setup.sh . && bash ec2_setup.sh BUCKET_NOMI
```

Skript quyidagilarni bajaradi:
- S3'dan fayllarni oladi va Python muhitini o‘rnatadi;
- `/opt/lexai/.env` ichida tasodifiy `LEXAI_API_KEY` yaratadi;
- `lexai` systemd xizmatini ishga tushiradi.

Tekshirish:

```bash
journalctl -u lexai -f
curl localhost:8000/health
```

Model yuklanganda `/health` javobida `"model_loaded": true` chiqadi.

```bash
curl -s localhost:8000/ask -H "Content-Type: application/json" -H "X-API-Key: $(grep LEXAI_API_KEY /opt/lexai/.env | cut -d= -f2)" -d '{"question":"Nikohni bekor qilish uchun davlat boji qancha?"}'
```

## 7. HTTPS (Caddy, bepul sertifikat)

API kalit internetda ochiq HTTP orqali yuborilmasligi kerak. Agar domeningiz bo‘lmasa, Elastic IP bilan `sslip.io` dan foydalanish mumkin (masalan, `3-120-45-67.sslip.io`):

```bash
sudo apt-get install -y caddy
echo '3-120-45-67.sslip.io {
  reverse_proxy localhost:8000
}' | sudo tee /etc/caddy/Caddyfile
sudo systemctl restart caddy
```

Shundan keyin security group'da 443-portni oching. 8000-port esa tashqariga yopiq qolsin.

## 8. Web-app integratsiyasi

API kalitni **brauzerga bermang**. Web-app'ning backend qismi so‘rovni o‘zi yuborishi kerak.

**Next.js (App Router) — `app/api/ask/route.ts`:**

```ts
export async function POST(req: Request) {
  const { question } = await req.json();
  const r = await fetch(`${process.env.LEXAI_API_URL}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-API-Key": process.env.LEXAI_API_KEY! },
    body: JSON.stringify({ question }),
  });
  return new Response(await r.text(), { status: r.status, headers: { "Content-Type": "application/json" } });
}
```

**Python (FastAPI/Django backend):**

```python
import os, requests
r = requests.post(f"{os.environ['LEXAI_API_URL']}/ask",
                  headers={"X-API-Key": os.environ["LEXAI_API_KEY"]},
                  json={"question": question}, timeout=60)
data = r.json()
```

**Javob formati:**

```json
{
  "answer": "… uchun davlat boji stavkasi: **BHMning 2 baravari**. Manba: … [ORQ600_TABLE_FEE_004]",
  "verified": true,
  "sources": [{"id": "ORQ600_TABLE_FEE_004", "reference": "OʻRQ-600, …", "text": "…"}],
  "latency_ms": 6400
}
```

- `answer` Markdown formatida keladi (`**…**`), uni Markdown sifatida chizing.
- `sources` ni "Manbalar" bo‘limida ko‘rsating.
- `verified: false` bo‘lsa, javob avtomatik ravishda xavfsiz rad javobiga almashtirilgan bo‘ladi. Xom javob faqat server log'ida qoladi.
- Javob 5–20 soniya olishi mumkin, shuning uchun "yuklanmoqda" holatini ko‘rsating va `timeout` ni kamida 60 soniya qiling.

## Narx va xavfsizlik

- GPU instance ishlab turgan har soat uchun haq olinadi (`g4dn.xlarge` taxminan soatiga $0.5–0.7, regionga qarab; aniq narxni AWS Pricing sahifasida tekshiring). Demo bo‘lmaganda **Stop** qiling. Elastic IP biriktirilgan bo‘lsa, manzil o‘zgarmaydi.
- AWS Budgets'da byudjet ogohlantirishini sozlang.
- S3 bucket ommaga yopiq bo‘lsin. Kaggle kaliti faqat `PutObject`, EC2 role faqat o‘qish huquqiga ega.

## Ma'lum cheklovlar

- **Qidiruv faqat qisman sinalgan.** Lokal sinovda BM25 va modda bo‘yicha yo‘naltirish 10 ta savoldan 6 tasida to‘g‘ri manbani top-4 ichida topdi. e5 dense qismi serverda qo‘shiladi, lekin u lokal sinalmagan. "Ikkinchi marta ajrashsam" kabi so‘zlashuv uslubidagi savollar uchun Kaggle notebookdagi intent router'ingizni `retrieval.py` ga ko‘chirish tavsiya etiladi.
- **Server bitta GPU'da ishlaydi va so‘rovlarni navbat bilan bajaradi.** Demo uchun yetarli, lekin ko‘p foydalanuvchiga mo‘ljallanmagan.
