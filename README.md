# Quality-Constrained Prompting for LLM-Based STEM Quiz Generation

Project ini adalah implementasi eksperimen:

> “Quality-Constrained Prompting for LLM-Based STEM Quiz Generation”

Tujuan utama:
- Menghasilkan soal multiple-choice (MCQ) satu item untuk 4 mata pelajaran STEM (Matematika, Fisika, Biologi, Kimia).
- Membandingkan 3 struktur prompting:
  - S1 – Standard Prompting (SP)
  - S2 – SP + Chain-of-Thought (SP+CoT)
  - S3 – SP + Quality Constraints (SP+QC)
- Menguji beberapa model LLM via Ollama sebagai *generator*.
- Menggunakan Gemini 2.5 (via Maia Router) sebagai *LLM-as-judge* untuk menilai soal dengan 4 aspek:
  - Clarity, Context Accuracy, Quality of Working, Final Answer Accuracy.

Output utama: file CSV berisi log soal, skor rubrik, waktu eksekusi, dan metrik lain yang dipakai untuk analisis dan penulisan paper.

---

## 1. Struktur Proyek

Struktur folder (disederhanakan):

    question_generation/
    ├─ main.py                   # Entry point untuk menjalankan 1 eksperimen
    ├─ quiz_service.py           # Orkestrasi generator + verifier + logging CSV
    ├─ models/
    │   └─ openrouter.py         # Wrapper OpenAI-compatible untuk Ollama (Qwen, Gemma, LLaMA, Phi)
    ├─ validator_gemini.py       # Verifier via Maia Router (Gemini 2.5)
    ├─ utils/
    │   └─ load_env.py           # Helper untuk load .env
    ├─ outputs/
    │   ├─ struktur1/            # CSV hasil Struktur 1 (SP)
    │   ├─ struktur2/            # CSV hasil Struktur 2 (SP+CoT)
    │   └─ struktur3/            # CSV hasil Struktur 3 (SP+QC)
    ├─ add_bertscore.py          # (opsional) Tambah kolom BERTScore ke CSV
    ├─ summarize_results.py      # (opsional) Ringkas semua CSV → tabel agregat
    ├─ merge.py                  # (opsional) Merge beberapa CSV
    └─ README.md                 # Dokumen ini

Komentar di dalam source code menjelaskan fungsi tiap modul dan parameter penting.

---

## 2. Prasyarat

### Software

- Python ≥ 3.10 (proyek ini diuji di 3.12)
- pip untuk instal dependensi
- Ollama (untuk LLM generator, lokal/offline)
- API key Maia Router (untuk Gemini 2.5 sebagai verifier)

### Python packages

Minimal paket:

    pip install openai requests python-dotenv pandas numpy bert-score

Kalau ada requirements.txt:

    pip install -r requirements.txt

---

## 3. Konfigurasi Environment

Buat file `.env` di root project. Contoh:

    # === OLLAMA / LOCAL LLM GENERATORS ===
    OLLAMA_OPENAI_URL=http://localhost:11434/v1/chat/completions

    # Nama model harus sama dengan `ollama list`
    OPENROUTER_MODEL_QWEN=qwen2.5:7b
    OPENROUTER_MODEL_GEMMA=gemma3:12b
    OPENROUTER_MODEL_LLAMA=llama3:8b
    OPENROUTER_MODEL_PHI=phi3:mini

    # === MAIA ROUTER (GEMINI VERIFIER) ===
    MAIA_API_KEY=ISI_API_KEY_MAIA_KAMU
    MAIA_BASE_URL=https://api.maiarouter.ai/v1
    MAIA_VERIFIER_MODEL=maia/gemini-2.5-flash

    # Opsional: retry/backoff verifier
    MAIA_MAX_RETRIES=6
    MAIA_BACKOFF_BASE=1.8

Catatan penting:
- Tanpa Ollama dan API key Maia, eksperimen penuh tidak bisa dijalankan.
- Jangan commit `.env` ke repo publik.

---

## 4. Instalasi

1. Clone / download repo.
2. Masuk ke folder:

       cd question_generation

3. (Opsional) Buat virtualenv:

       python -m venv .venv
       .venv\Scripts\activate    (Windows)
       # source .venv/bin/activate (Linux/Mac)

4. Install dependensi:

       pip install -r requirements.txt
       # atau paket minimal seperti di atas

5. Buat `.env` seperti contoh dan isi API key Maia.
6. Install model Ollama yang diperlukan:

       ollama pull qwen2.5:7b
       ollama pull gemma3:12b
       ollama pull llama3:8b
       ollama pull phi3:mini

7. Pastikan server Ollama jalan (biasanya otomatis):

       ollama serve

---

## 5. Cara Menjalankan Eksperimen

`main.py` biasanya memanggil fungsi:

    main(structure, subject, model_alias, count=...)

Parameter:
- structure: "struktur1", "struktur2", atau "struktur3"
- subject: "mathematics", "physics", "biology", "chemistry"
- model_alias: "qwen", "gemma", "llama", "phi"
- count: jumlah soal yang digenerate (misalnya 50 atau 100)

Contoh isi `main.py`:

    from quiz_service import main

    if __name__ == "__main__":
        # contoh: Struktur 1, Matematika, model Qwen, 50 soal
        main("struktur1", "mathematics", "qwen", count=50)

Langkah run:

1. Pastikan:
   - Ollama aktif
   - `.env` sudah benar
   - Internet aktif (untuk Maia Router)

2. Jalankan:

       python main.py

3. Output CSV akan muncul di:

    outputs/{subject}/{strukturX}/MODEL_TIMESTAMP.csv

Setiap baris CSV biasanya berisi:
- struktur prompt, subject, model
- teks soal, opsi, jawaban benar
- solusi generator
- hasil verifikasi (solution_verifier, clarity, context_accuracy, quality_of_working, final_answer_accuracy)
- waktu eksekusi dalam ms

---

## 6. Analisis dan Ringkasan Hasil

### 6.1. Menambahkan BERTScore

    python add_bertscore.py

Script ini:
- Membaca semua CSV di `outputs/`
- Menghitung BERTScore antara solusi generator dan solusi verifier
- Menambah kolom `bertscore` ke CSV

### 6.2. Merangkum ke Tabel Agregat

    python summarize_results.py

Output:
- CSV ringkasan per struktur × model × subject:
  - rata-rata Final Answer Accuracy
  - rata-rata Clarity, Context Accuracy, Quality of Working
  - rata-rata waktu eksekusi
  - rata-rata BERTScore (kalau sudah dihitung)

`merge.py` bisa dipakai untuk menggabungkan beberapa CSV mentah sebelum diringkas.

---

## 7. Contoh Penggunaan Singkat

Contoh 1 – 20 soal Matematika, Struktur 1, model Qwen:

    from quiz_service import main

    if __name__ == "__main__":
        main("struktur1", "mathematics", "qwen", count=20)

Lalu:

    python main.py

Contoh 2 – 50 soal Fisika, Struktur 3, model Gemma:

    if __name__ == "__main__":
        main("struktur3", "physics", "gemma", count=50)

Lalu:

    python main.py

---

## 8. Catatan Penting / Limitasi

- API Key & Kuota  
  Verifier bergantung ke Maia Router (Gemini 2.5). Jika kuota habis / rate limit, script akan berhenti dan menulis partial row ke CSV. Ini harus dicatat di laporan.

- Waktu Eksekusi  
  Model besar (gemma3:12b, llama3:8b) jauh lebih lambat. Uji dulu dengan count kecil (~5–10) sebelum full run.

- Reproducibility  
  Teks prompt untuk S1, S2, S3 disimpan sebagai blok di kode. Kalau kamu mengubah isi prompt (misalnya definisi S3), pastikan versi kode yang ada di repo sama dengan yang dipakai di paper.

- Testing Project  
  Penguji akan:
  1) Cek README ini,
  2) Set `.env` dan Ollama,
  3) Jalanin `python main.py`.  
  Kalau mereka kena error karena env/API tidak di-set, tanggung jawab kamu adalah menuliskan dependensi itu dengan jelas (sudah dilakukan di README ini).

---
