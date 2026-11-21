# LexAI — RAG + Gemma 4 E2B fine-tune (OʻRQ-600 «Davlat boji toʻgʻrisida»)

Hisobchi web-app'idagi AI yordamchining modeli va ma'lumotlar quvuri. Backend
`backend/app/lexai.py` orqali Gradio `/ask_json` endpoint'ini chaqiradi (`LEXAI_URL`).

## Papka tuzilmasi

| Yo'l | Vazifasi |
|---|---|
| `data_source/` | Dastlabki (v2) ma'lumotlar: qonun moddalari, RAG korpusi, davlat boji jadvali |
| `fix_fee_table.py` | v2 → v3: jadvaldagi 227 guruh sarlavhasini ajratadi, har bir stavkaga to'liq yo'l qo'shadi |
| `data_v3/` | Tuzatilgan jadval, v3 RAG korpusi, ierarxiya review fayli |
| `build_sft.py` | SFT dataset generatori (deterministik, LLM ishlatilmagan) |
| `sft/`, `sft_v4/` | Trening datasetlari (v3 — hozirgi adapter shu bilan o'qitilgan) |
| `train_gemma4_lora.py` | Unsloth LoRA trening (Kaggle T4) |
| `eval_sft.py` | Baholash (xom va tekshiruvchidan keyingi natija) |
| `verifier.py` | Javobni manbaga nisbatan deterministik tekshirish |
| `deploy/server/` | `retrieval.py` (BM25+e5), `answering.py` (tarif/model/manba yo'naltirish), `app.py` (FastAPI) |
| `deploy/` | AWS (S3 + EC2) deploy skriptlari va qo'llanma |
| `kaggle/gradio_demo.py` | Kaggle'da Gradio demo + `/ask_json` API |

## Qayta yaratish

```bash
python3 -I fix_fee_table.py data_source data_v3
python3 -I build_sft.py data_source data_v3 sft_v4
python3 -I eval_sft.py --test sft_v4/lexai_sft_test.jsonl --self-test
```

Model vaznlari (Gemma 4 E2B va LoRA adapter) repoga kiritilmagan: ular Kaggle'da va S3'da saqlanadi.

## Natijalar (v3 adapter, 106 ta test savoli)

| | Bazaviy Gemma | LexAI LoRA |
|---|---|---|
| Hamma mezon bajarilgan | 33/106 | 102/106 |
| Noto'g'ri stavkani rad etish | 0/8 | 8/8 |

Muhim cheklov: test savollari shablon asosida. Model tabiiy savollarni ko'pincha rad etadi,
shuning uchun `answering.py` tarif savollariga jadvaldan deterministik javob beradi, qolganlariga esa
model → tekshiruvchi → qonun matnidan iqtibos tartibida ishlaydi.

---

## Fine-tune paketi tafsilotlari

## v4 (yangi)

v3 LoRA testda 102/106 natija berdi. Xatolarning umumiy sababi: model shartni manbadan emas, savoldan ko‘chirgan. Masalan, kontekstda faqat "ikki oygacha" bor edi, lekin model shu stavkani "uch oygacha" deb berdi. Shu sababli v4 da ikki qatlamli himoya qo‘shildi:

1. **`verifier.py`** — model javobini manbaga nisbatan tekshiradigan deterministik modul. U quyidagilarni tekshiradi:
   - ko‘rsatilgan ID kontekstda bormi;
   - stavka va javobdagi shart (holat) ko‘rsatilgan chunkda bormi;
   - «…» iqtibos manbadan aynan olinganmi;
   - `a × b = c` hisobi to‘g‘rimi.

   RAG pipeline'ga quyidagicha ulanadi:
   ```python
   from verifier import verify, guard
   answer = guard(prompt, model_answer)   # tekshiruvdan o'tmasa — xavfsiz rad javobi
   ```
   v3 LoRA'ning 3 ta haqiqiy xatosida sinaldi: 3/3 ushlandi, to‘g‘ri javoblarda keraksiz bloklash 0 ta.
2. **`sft_v4/`** — yangi dataset (2398 namuna; train 2089, val 153, test 156). Barcha oltin javoblar `verifier` dan o‘tadi. Yangi vazifalar:
   - `fee_near_miss` (255): so‘ralgan holat kontekstda yo‘q, faqat qo‘shni qatorlar bor. Model rad etadi va mavjud qatorlarni stavkasi bilan sanaydi.
   - `fee_twin` (206): deyarli bir xil yo‘lli qator (masalan, oddiy va jamoaviy belgi) kontekstga majburiy qo‘shiladi.
   - `fee_lookup_short` (251): savol qisqa, javobdagi to‘liq yo‘l esa manbadan olinadi. Bu modelni savolni qaytarishdan ko‘ra manbadan ko‘chirishga o‘rgatadi.
   - Modda savollariga qo‘shimcha shablon qo‘shildi (ortiqcha rad etishni kamaytirish uchun).

`eval_sft.py` endi ikki natija chiqaradi: xom javoblar va `guard` dan keyingi javoblar. Eng muhim ko‘rsatkich — **"tekshiruvdan keyin ham xato VA rad emas (xavfli)"** soni. U 0 bo‘lishi kerak. `--preds` bilan eski natijani GPU'siz qayta baholash mumkin.

## Tarkibi

| Fayl | Vazifasi |
|---|---|
| `fix_fee_table.py` | Jadval v2 → v3: 227 guruh sarlavhasini ajratadi, har bir stavkaga to‘liq `context_path` qo‘shadi, RAG korpusini qayta yozadi |
| `data_v3/state_duty_table_normalized_v3.json` | Tuzatilgan jadval (556 stavka, 227 guruh, 1 ta review) |
| `data_v3/rag_corpus_v3.jsonl` | 841 chunk (556 fee chunk to‘liq yo‘l bilan, sarlavha chunklari olib tashlangan) |
| `data_v3/review/fee_hierarchy_review.tsv` | Har bir guruh va uning bolalari — LexUZ bilan qo‘lda tekshirish uchun |
| `build_sft.py` | SFT dataset generatori (deterministik, seed=600, LLM ishlatilmagan) |
| `sft/lexai_sft_{train,val,test}.jsonl` | 1716 / 107 / 106 namuna, `messages` (user/assistant) formatida |
| `sft/dataset_report.json` | Vazifalar bo‘yicha statistika |
| `train_gemma4_lora.py` | Unsloth + TRL LoRA trening (Kaggle 2×T4) |
| `eval_sft.py` | Bazaviy model va LoRA'ni test to‘plamida baholash |

## Ishga tushirish (Kaggle)

1. `sft/` papkasini Kaggle Dataset sifatida yuklang (masalan, `lexai-sft`).
2. Bazaviy modelni baholang (taqqoslash uchun):
   ```
   !pip install -q unsloth
   !python eval_sft.py --test /kaggle/input/lexai-sft/sft/lexai_sft_test.jsonl --model unsloth/gemma-4-E2B-it --out base.jsonl
   ```
3. Avval tez sinov qiling (`--max_steps 30`), keyin to‘liq trening boshlang:
   ```
   !python train_gemma4_lora.py --data /kaggle/input/lexai-sft/sft --out /kaggle/working/lexai_lora
   ```
   Log'da `instruction_part`, `response_part` va "label namunasi" chiqadi. Label namunasi javob matni bilan boshlanishi kerak.
4. Adapterni baholang:
   ```
   !python eval_sft.py --test /kaggle/input/lexai-sft/sft/lexai_sft_test.jsonl --model /kaggle/working/lexai_lora --out lora.jsonl
   ```

`MODEL_NAME` notebookda ishlatilayotgan nom bilan bir xil bo‘lishi kerak (`LEXAI_BASE_MODEL` muhit o‘zgaruvchisi orqali).

## Muhim: inference trening formatiga mos bo‘lishi kerak

- **RAG indeksini `rag_corpus_v3.jsonl` dan qayta quring** (embedding, FAISS, BM25). Fee chunklarining matni o‘zgardi. Eski v2 indeks qaytargan chunklar model o‘rgangan formatga mos kelmaydi.
- Promptni `build_sft.py` dagi `make_user()` bilan aynan bir xil yig‘ing: qoidalar matni, so‘ng `### Manbalar` (`[n] ID: … | havola` + matn), so‘ng `### Savol`.
- Hisob-kitobda BHM qiymatini promptga **Fee Calculation Engine** berishi kerak. Model BHM berilmasa summa aytmaslikka o‘rgatilgan.

## Vazifalar

| Vazifa | Soni | Nimani o‘rgatadi |
|---|---|---|
| `fee_lookup` | 1112 | Yaqin distractorlar orasidan to‘g‘ri tarifni topish va manba ID bilan aytish |
| `fee_wrong_premise` | 159 | Savoldagi noto‘g‘ri stavkani rad etish |
| `fee_no_answer` | 111 | Manbada javob yo‘q bo‘lsa, ochiq aytish |
| `fee_calc` / `fee_calc_pct_min` | 141 / 12 | BHM berilganda hisoblash, jumladan % va minimal chegara |
| `fee_calc_needs_bhm` | 39 | BHM berilmasa, summa to‘qimaslik |
| `article_quote` / `article_locate` | 115 / 33 | Modda matnini o‘zgartirmasdan keltirish |
| `amendment_*` | 173 | O‘zgartirishlar tarixini sanalar bo‘yicha berish, normativ matn bilan aralashtirmaslik |
| `out_of_scope` | 36 | Boshqa qonunlar bo‘yicha savolga javob bermaslik |

## Ma'lum cheklovlar

- Jadval ierarxiyasi evristika bilan tiklangan, chunki asl HTML'dagi chekinishlar yo‘qolgan. `fee_hierarchy_review.tsv` ni tanlab LexUZ bilan solishtiring.
- `FEE_767` (f-band, uyali aloqa) manbaning o‘zida stavkasiz. U datasetdan chiqarilgan.
- Savollar shablon asosida, shuning uchun real foydalanuvchi tiliga qaraganda rasmiyroq. Keyingi bosqich: real savollar yoki LLM parafrazi (javoblar shu skriptdan qoladi).
- Imtiyozlar (8–15-moddalar) va refund (18-modda) `article_quote` orqali qamrab olingan, router'dagi 147 bandlik maxsus javoblar formati alohida qo‘shilmagan.
- `BHM` qiymatlari (340 000 / 375 000 / 412 000 so‘m) faqat misol uchun olingan va har doim promptda beriladi. Ular amaldagi BHM sifatida taqdim etilmaydi.
