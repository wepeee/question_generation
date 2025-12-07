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

Struktur folder (disederhanakan, disesuaikan dengan repo ini):

    question_generation/
    ├─ main.py               # Entry point untuk menjalankan 1 eksperimen
    ├─ quiz_service.py       # Orkestrasi generator + verifier + logging CSV
    ├─ json_utils.py         # Utility untuk encoding/decoding JSON aman
    ├─ normalize.py          # (opsional) Normalisasi / pembersihan teks
    ├─ models/
    │   └─ openrouter.py     # Wrapper OpenAI-compatible untuk Ollama (Qwen, Gemma, LLaMA, Phi)
    ├─ utils/
    │   └─ load_env.py       # Helper untuk load .env
    ├─ outputs/
    │   ├─ biology/
    │   │   ├─ struktur1/    # CSV Biologi – Struktur 1
    │   │   ├─ struktur2/    # CSV Biologi – Struktur 2
    │   │   └─ struktur3/    # CSV Biologi – Struktur 3
    │   ├─ chemistry/
    │   │   ├─ struktur1/
    │   │   ├─ struktur2/
    │   │   └─ struktur3/
    │   ├─ mathematics/
    │   │   ├─ struktur1/
    │   │   ├─ struktur2/
    │   │   └─ struktur3/
    │   └─ physics/
    │       ├─ struktur1/
    │       ├─ struktur2/
    │       └─ struktur3/
    └─ README.md             # Dokumen ini

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

    pip install openai requests python-dotenv pandas numpy

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

    # === GEMINI VERIFIER (GOOGLE) ===
    GEMINI_API_KEY=ISI_API_KEY_GEMINI_KAMU
    GEMINI_VERIFIER_MODEL=gemini-2.5-pro

    # Opsional: pengaturan retry / delay
    GEMINI_PRO_DELAY_SEC=30
    GEMINI_DELAY_BETWEEN_CALLS=1.0
    GENAI_MAX_RETRIES=6
    GENAI_BACKOFF_BASE=1.8
    GENAI_TIMEOUT=90


Catatan:
- Tanpa Ollama dan API key Gemini, eksperimen penuh tidak bisa dijalankan.
- `.env` jangan di-commit ke repo publik.

---

## 4. Instalasi

1. Clone / download repo.
2. Masuk ke folder:

       cd question_generation

3. Install dependensi:

       pip install openai requests python-dotenv pandas numpy

4. Buat `.env` seperti contoh.
5. Install model Ollama yang diperlukan:

       ollama pull qwen2.5:7b
       ollama pull gemma3:12b
       ollama pull llama3:8b
       ollama pull phi3:mini

6. Pastikan server Ollama jalan (biasanya otomatis):

       ollama serve

---

## 5. Cara Menjalankan Eksperimen

`main.py` biasanya memanggil fungsi:

    main(structure, subject, model_alias, count=...)

Parameter:
- `structure` : `"struktur1"`, `"struktur2"`, atau `"struktur3"`
- `subject`   : `"mathematics"`, `"physics"`, `"biology"`, `"chemistry"`
- `model_alias` : `"qwen"`, `"gemma"`, `"llama"`, `"phi"`
- `count`     : jumlah soal yang digenerate (misalnya 50 atau 100)

Contoh isi minimal `main.py`:

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

    outputs/{subject}/{strukturX}/NAMA_MODEL_TIMESTAMP.csv

Contoh:

- `outputs/mathematics/struktur1/qwen_20251204_120000.csv`
- `outputs/biology/struktur3/phi_20251207_024133.csv`

Setiap baris CSV berisi:
- struktur prompt, subject, model
- teks soal, opsi, jawaban benar
- solusi generator
- hasil verifikasi (solution_verifier, clarity, context_accuracy, quality_of_working, final_answer_accuracy)
- waktu eksekusi dalam ms

---

## 6. Analisis Hasil (Singkat)

Analisis lanjutan (rata-rata per struktur × model × subject, BERTScore, grafik, dsb.) dikerjakan di notebook / project terpisah dan **tidak** menjadi bagian repo ini.

---

## 7. Contoh Penggunaan

Contoh 1 – 20 soal Matematika, Struktur 1, model Qwen:

    from quiz_service import main

    if __name__ == "__main__":
        main("struktur1", "mathematics", "qwen", count=20)

Lalu jalankan:

    python main.py

Contoh 2 – 50 soal Fisika, Struktur 3, model Gemma:

    if __name__ == "__main__":
        main("struktur3", "physics", "gemma", count=50)

Lalu jalankan:

    python main.py

---

## 8. Catatan Penting / Limitasi

- **API Key & Kuota**  
  Verifier memakai gemini-2.5-pro lewat library google-generativeai. Jika kuota habis / rate limit, script akan melempar error "quota / resource exhausted". Kode sudah punya mekanisme retry, tapi kalau kuota 0 tetap gagal.

- **Waktu Eksekusi**  
  Model besar (gemma3:12b, llama3:8b) jauh lebih lambat. Uji dulu dengan `count` kecil (~5–10) sebelum full run.

- **Reproducibility**  
  Teks prompt untuk S1, S2, S3 disimpan sebagai blok di kode. Jika prompt diubah, pastikan versi kode di repo sama dengan versi yang dipakai saat eksperimen.

- **Pengetesan Project**  
  1) Code bisa dijalankan tanpa error setelah `.env`, Ollama, dan API key disiapkan.  
  2) README ini menjelaskan deskripsi, instalasi, cara menjalankan, dan contoh penggunaan.  
  3) Struktur folder rapi, komentar di kode menjelaskan fungsi modul dan parameter penting.

---
