# QUESTION_GENERATION/prompting.py
from __future__ import annotations
from typing import Dict, List, Literal, Optional, TypedDict

PromptStructKey = Literal["struktur1","struktur2","struktur3"]
TopicKey = Literal["matematika","biologi","fisika","kimia"]

class ChatMessage(TypedDict):
    role: Literal["system","user","assistant"]
    content: str

def topic_label(t: TopicKey) -> str:
    return {
        "matematika": "Matematika",
        "biologi": "Biologi",
        "fisika": "Fisika",
        "kimia": "Kimia",
    }[t]

BLOCKS: Dict[TopicKey, Dict[str, str]] = {
    "matematika": {
        "sp": """
• Tulis 1 soal hitung tingkat menengah pada salah satu: aljabar (fungsi/invers/sistem), trigonometri (identitas/evaluasi), kalkulus dasar (limit/turunan/integral sederhana), atau statistika singkat.
• Gunakan angka realistis; pembulatan 2 desimal bila perlu; hindari pembuktian formal.
• Distraktor meniru kesalahan umum (tanda, identitas salah, aturan turunan/limit, salah pembulatan).
""".strip(),
        "cot": """
• Lakukan penalaran multi-langkah secara internal (jangan ditampilkan).

Contoh:
Sample Question (referensi): Sebuah toko menjual Tipe A, B, C. Total biaya 10 A + 15 B + 8 C adalah Rp11.80 juta. Total 8 A + 12 B + 10 C adalah Rp10.64 juta. Total 6 A + 9 B + 12 C adalah Rp9.86 juta. Berapakah harga satu Tipe C?
Sample Answer (internal): Susun SPL tiga variabel → eliminasi/substitusi → C ≈ 0,405 juta → pilih opsi yang cocok.

• Buat soal baru setipe (mis. SPL, identitas trig lalu evaluasi sudut, turunan lalu substitusi nilai, statistik dari data kecil).
• Distraktor mewakili kesalahan langkah (eliminasi keliru, identitas salah, aturan turunan salah, pembulatan salah).
""".strip(),
        "qc": """
Quality Constraints:
• Clarity & notation: notasi konsisten, stem spesifik, data cukup.
• Difficulty target: menengah (≤3 langkah).
• Distraktor effectiveness / discrimination: tiga pengecoh plausible mewakili kesalahan langkah/konsep berbeda.
• Numerical hygiene: hasil masuk akal; pembulatan 2 desimal; satuan/notasi konsisten bila ada.
""".strip(),
    },
    "biologi": {
        "sp": """
• Tulis 1 soal konsep/aplikasi ringkas pada: genetika dasar (termasuk Hardy-Weinberg), struktur/fungsi sel/jaringan, atau ekologi ringkas.
• Istilah baku; jika ada hitungan (mis. frekuensi alel) gunakan angka kecil dan pembulatan 2 desimal.
• Distraktor mencerminkan miskonsepsi umum (dominansi ≠ frekuensi, salah baca rasio/diagram, salah alur DNA→RNA→Protein).
""".strip(),
        "cot": """
• Lakukan identifikasi konsep/rasio/relasi data mini secara internal; JANGAN tampilkan langkah.

Contoh (analog Hardy-Weinberg):
Sample Question (referensi): Dalam populasi besar, frekuensi alel p=0,6 dan q=0,4. Berapakah frekuensi heterozigot?
Sample Answer (internal): 2pq = 2(0,6)(0,4) = 0,48 → pilih opsi yang sesuai.

• Buat soal baru setipe (tabel kecil/rasio genotipe/konsep aliran energi).
• Distraktor harus plausible dan memetakan miskonsepsi (dominansi ≠ frekuensi, salah tafsir grafik/tabel).
""".strip(),
        "qc": """
Quality Constraints:
• Clarity: istilah baku, tanpa ambiguitas proses/struktur; data cukup untuk satu jawaban paling benar.
• Difficulty target: menengah (1–2 inferensi/rasio sederhana).
• Distractor effectiveness / discrimination: tiga pengecoh plausible memetakan miskonsepsi nyata.
• Consistency check: verifikasi internal hubungan genotipe–fenotipe/energi/aliran materi sebelum menetapkan kunci.
""".strip(),
    },
    "fisika": {
        "sp": """
• Tulis 1 soal hitung menengah pada: kinematika (GLB/GLBB/proyektil), dinamika (Hukum Newton/bidang miring), energi–impuls, atau listrik dasar (V-I-R).
• Gunakan satuan SI (gunakan g = 9,8 m s^-2 bila perlu), angka realistis, pembulatan 2 desimal.
• Distraktor umum: komponen vektor/sinyal/tanda salah, konversi/satuan salah, gaya efektif salah.
""".strip(),
        "cot": """
• Uraikan komponen vektor/persamaan relevan secara internal; JANGAN tampilkan langkah.

Contoh gaya (diadaptasi dari paper, proyektil mendarat ke cekungan):
Sample Question (referensi): Sebuah bola ditendang dengan kecepatan 25 m s^-1 pada sudut 45 derajat di atas horizontal dan mendarat ke cekungan sedalam 1,0 m. Hitung laju bola sesaat sebelum menyentuh cekungan.
Sample Answer (internal): vx = v cos45; vy^2 = (v sin45)^2 + 2 a Δy dengan a = -9,8 dan Δy = -1,0; vy ≈ 18,22; v = sqrt(vx^2 + vy^2) ≈ 25,39 m s^-1.

• Buat soal baru setipe (proyektil/bidang miring/energi-impuls/rangkaian).
• Distraktor = sin/cos salah, tanda salah, atau satuan salah.
""".strip(),
        "qc": """
Quality Constraints:
• Clarity & SI: besaran dan satuan SI eksplisit; simbol konsisten.
• Difficulty target: menengah (2–3 langkah).
• Physical plausibility: cek orde besaran/kewajaran; konservasi energi/impuls bila relevan.
• Distractor effectiveness / discrimination: tiga pengecoh plausible dari kesalahan khas (komponen sin–cos, tanda kerja/energi, salah satuan).
""".strip(),
    },
    "kimia": {
        "sp": """
• Tulis 1 soal hitung menengah pada: stoikiometri (termasuk pereaksi pembatas), konsentrasi (molaritas/persen massa), asam–basa kuat (pH), atau kesetimbangan sederhana.
• Gunakan massa atom umum (H=1, C=12, N=14, O=16, Na=23, Cl=35,5); pembulatan 2 desimal; satuan tepat.
• Distraktor: koefisien salah, konversi mol-gram-volume salah, log/pH salah.
""".strip(),
        "cot": """
• Lakukan perhitungan dan pengecekan koefisien secara internal; JANGAN tampilkan langkah.

Contoh gaya (diadaptasi dari paper, elektrolisis Cr^3+):
Sample Question (referensi): Arus 0,0353 A dialirkan selama 35 menit melalui larutan Cr^3+. Berapa massa Cr yang terendapkan? (Mr Cr = 52,0 g/mol; 3 elektron per atom; F = 96.500 C/mol)
Sample Answer (internal): Q = I·t = 0,0353 × 2100 = 74,16 C; n(e) = Q/F = 0,000769 mol; n(Cr) = n(e)/3 = 0,000256 mol; m = 0,000256 × 52,0 = 0,0133 g.

• Buat soal baru setipe (stoikiometri/pH/kesetimbangan ringan).
• Distraktor = kesalahan umum (koefisien, konversi mol-gram-volume, log/pH, salah konsep pereaksi pembatas).
""".strip(),
        "qc": """
Quality Constraints:
• Clarity & units: reaksi/koefisien/satuan jelas; data cukup.
• Difficulty target: menengah; angka realistis; pembulatan 2 desimal.
• Distractor effectiveness / discrimination: tiga pengecoh plausible dari kesalahan umum (koefisien salah, konversi keliru, log/pH salah).
• Numerical hygiene: konsistensi angka penting & satuan; hasil realistis.
""".strip(),
    },
}

OUTPUT_CONTRACT = """
OUTPUT CONTRACT (STRICT, SINGLE ITEM):
- Keluarkan HANYA JSON array berisi 1 objek:
  [{"question":"...","options":["A. ...","B. ...","C. ...","D. ..."],"answer":"A","solution":"Ringkasan langkah/alasan 3–6 baris, plain text."}]
- Field "solution" WAJIB ada, berisi ringkasan langkah/alasan (3–6 baris, plain text; tanpa LaTeX/markdown).
- Tanpa teks lain di luar JSON, tanpa code fences.
- Opsi wajib berawalan "A. "/"B. "/"C. "/"D. " dan "answer" = A/B/C/D.
- NO LaTeX: jangan gunakan tanda $, backslash, atau perintah LaTeX; tulis plain text (sin, cos, pi, (a)/(b)).
""".strip()

def build_messages_single(
    struct_key: PromptStructKey,
    topic: TopicKey,
    avoid_terms: Optional[List[str]] = None,
) -> List[ChatMessage]:
    t = topic_label(topic)

    parts: List[str] = [BLOCKS[topic]["sp"]]
    if struct_key in ("struktur2","struktur3"):
        parts.append(BLOCKS[topic]["cot"])
    if struct_key == "struktur3":
        parts.append(BLOCKS[topic]["qc"])

    system_content = f"""
Kamu adalah guru {t} SMA (kelas 12) dan berbahasa Indonesia.
Tulis TEPAT 1 soal pilihan ganda kualitas baik dan SERTAKAN "solution" (3-6 baris, plain text).
Pastikan ada jawaban yang benar.
{ "\n\n".join(parts) }

{OUTPUT_CONTRACT}
""".strip()

    avoid_block = ""
    if avoid_terms:
        avoid_block = (
            "\n\nTambahan penting:\n"
            f"- Hindari mengulang konteks/kata kunci/angka berikut: {', '.join(avoid_terms)}.\n"
            "- Jangan tampilkan daftar ini pada output."
        )

    return [
        {"role":"system","content":system_content},
        {"role":"user","content": f'Topik: {t}. Buat 1 soal sesuai instruksi dan kembalikan JSON single-item dengan field "solution".{avoid_block}'},
    ]
