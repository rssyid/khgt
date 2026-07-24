<div align="center">

# 🌙 KHGT — Kalender Hijriah Global Tunggal

**Aplikasi web kalender Hijriah harian dengan integrasi AI Sirah Nabawiyah, dirancang untuk kemudahan berbagi konten Islami di media sosial.**

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Neon_PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white)
![Vercel](https://img.shields.io/badge/Deployed_on-Vercel-000000?logo=vercel&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![HTML](https://img.shields.io/badge/Frontend-HTML%2FJS%2FCSs-E34F26?logo=html5&logoColor=white)

</div>

---

## 📖 Daftar Isi

- [Tentang Proyek](#-tentang-proyek)
- [Demo & Fitur](#-fitur-utama)
- [Arsitektur Sistem](#-arsitektur-sistem)
- [Struktur Direktori](#-struktur-direktori)
- [Database Schema](#-database-schema)
- [API Reference](#-api-reference)
- [Alur Data (Data Flow)](#-alur-data)
- [Tech Stack](#-tech-stack)
- [Cara Deploy](#-cara-deploy-ke-vercel)
- [Environment Variables](#-environment-variables)
- [Pengembangan Lokal](#-pengembangan-lokal)

---

## 🕌 Tentang Proyek

KHGT (Kalender Hijriah Global Tunggal) adalah aplikasi web yang menampilkan kalender harian dua sistem penanggalan — **Hijriah** dan **Masehi** — secara bersamaan dalam satu kanvas bergaya estetis yang siap diekspor dan dibagikan ke media sosial (Instagram, WhatsApp, dll.).

Aplikasi ini dilengkapi dengan:
- 🤖 **Integrasi AI (Gemini)** untuk menghasilkan ringkasan Sirah Nabawiyah secara otomatis berdasarkan tanggal Hijriah
- 📦 **Sistem caching bertingkat** (SQLite lokal + Neon PostgreSQL) untuk kecepatan optimal dan penghematan kuota API
- ✏️ **Konten yang sepenuhnya dapat diedit** — Pengguna bisa mengedit setiap teks di dalam kanvas sebelum diekspor
- 💾 **Auto-save** — Setiap perubahan tersimpan otomatis ke database PostgreSQL setelah 2 detik berhenti mengetik
- 📸 **Ekspor gambar** langsung sebagai file PNG berkualitas tinggi (2× pixel ratio) atau disalin ke clipboard

---

## ✨ Fitur Utama

| Fitur | Deskripsi |
|---|---|
| 📅 Kalender Ganda | Menampilkan tanggal Hijriah & Masehi secara berdampingan |
| 🤖 AI Sirah Nabawiyah | Generate ringkasan peristiwa sejarah Islam via Google Gemini |
| ⚡ AI Caching | Hasil AI disimpan di Neon DB; tanggal yang sama tidak memanggil Gemini dua kali |
| 💾 Auto-Save | Debounced auto-save 2 detik ke Neon PostgreSQL setiap kali teks diubah |
| ✏️ Fully Editable | Kategori, Judul, Konten, dan Sumber dapat diedit langsung di kanvas |
| 📸 Copy Image | Salin kanvas sebagai PNG ke clipboard (Clipboard API) |
| 💿 Save Image | Unduh kanvas sebagai file PNG (2× pixel ratio) |
| 📲 Share WA | Web Share API (mobile) dengan fallback download di desktop |
| 🗑️ Reset Editan | Hapus editan kustom dan kembalikan ke konten default |
| ⌨️ Keyboard Shortcut | Navigasi tanggal dengan tombol `←` `→` |
| 🎨 Transisi Halus | Fade-in/out 150ms pada seluruh kanvas saat berganti tanggal |
| 💀 Skeleton Loader | Animasi skeleton berdenyut saat AI sedang memproses |
| 🔔 Toast Notification | Notifikasi pop-up ringan di pojok layar menggantikan alert browser |

---

## 🏗️ Arsitektur Sistem

```mermaid
graph TB
    subgraph Client["🖥️ Browser (Client)"]
        HTML["index.html<br/>HTML + Vanilla JS + Tailwind CSS"]
    end

    subgraph Vercel["☁️ Vercel Serverless"]
        API["api/index.py<br/>FastAPI (Python)"]
        STATIC["public/<br/>Static Assets"]
        SQLITE["api/kalender.db<br/>SQLite (Read-only)"]
    end

    subgraph Neon["🐘 Neon PostgreSQL (Cloud)"]
        EDITS["sirah_edits<br/>Konten Edit User"]
        CACHE["sirah_ai_cache<br/>Cache Hasil AI"]
    end

    subgraph Google["🤖 Google AI"]
        GEMINI["Gemini API<br/>(Multi-model fallback)"]
    end

    HTML -->|"GET /api/date/{date}"| API
    HTML -->|"GET/POST/DELETE /api/sirah-simpan"| API
    HTML -->|"GET /api/sirah"| API

    API -->|"Query tanggal<br/>(Cache-Control: 1yr)"| SQLITE
    API -->|"CRUD konten edit"| EDITS
    API -->|"Read/Write cache AI"| CACHE
    API -->|"Jika tidak ada di cache"| GEMINI

    STATIC -->|"Serve langsung"| HTML
```

---

## 📁 Struktur Direktori

```
khgt/
│
├── 📄 README.md
├── 📄 vercel.json          # Konfigurasi routing Vercel
├── 📄 requirements.txt     # Dependensi Python
│
├── 📂 api/
│   ├── 🐍 index.py         # Backend FastAPI (semua endpoint)
│   └── 🗄️ kalender.db      # Database SQLite (data tanggal Hijriah)
│
└── 📂 public/
    ├── 🌐 index.html        # Frontend (HTML + CSS + JavaScript)
    └── 🖼️ back.png          # Background watermark kanvas
```

---

## 🗄️ Database Schema

### SQLite — `kalender.db` *(Read-only, Bundled)*

> Berisi data konversi tanggal Hijriah-Masehi yang telah dihitung sebelumnya untuk tahun 1940–2060.

```sql
-- Tabel utama data kalender
CREATE TABLE kalender_harian (
    gregorian_date_iso  TEXT PRIMARY KEY,   -- "2025-07-24"
    gregorian_day       INTEGER,            -- 24
    gregorian_month     INTEGER,            -- 7
    gregorian_year      INTEGER,            -- 2025
    hijri_day           INTEGER,            -- 28
    hijri_month         TEXT,               -- "Muharram"
    hijri_year          INTEGER,            -- 1447
    weekday_name_id     TEXT,               -- "Kamis"
    event_name          TEXT                -- "Hari Raya Idul Adha" / NULL
);
```

---

### Neon PostgreSQL — `sirah_edits` *(Read-Write, Cloud)*

> Menyimpan konten Sirah Nabawiyah yang telah diedit atau di-generate AI oleh pengguna.

```sql
CREATE TABLE IF NOT EXISTS sirah_edits (
    date_iso    TEXT PRIMARY KEY,                       -- "2025-07-24"
    kategori    TEXT DEFAULT 'Sirah Nabawiyah',         -- Badge kategori
    judul       TEXT,                                   -- Judul peristiwa
    konten_html TEXT,                                   -- Isi konten (HTML)
    sumber      TEXT,                                   -- Nama kitab rujukan
    updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- Timestamp terakhir disimpan
);
```

---

### Neon PostgreSQL — `sirah_ai_cache` *(Cache AI)*

> Menyimpan hasil generate AI Gemini berdasarkan tanggal Hijriah. Mencegah pemanggilan API berulang untuk tanggal yang sama.

```sql
CREATE TABLE IF NOT EXISTS sirah_ai_cache (
    hijri_key   TEXT PRIMARY KEY,                       -- "muharram_28" (bulan_tanggal)
    judul       TEXT,                                   -- Judul peristiwa dari AI
    konten_html TEXT,                                   -- Isi konten dari AI
    sumber      TEXT,                                   -- Kitab rujukan dari AI
    url_sumber  TEXT,                                   -- URL validasi sumber
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP     -- Kapan pertama kali di-generate
);
```

---

## 📡 API Reference

Base URL: `https://<your-domain>/api`

### `GET /api/date/{date_iso}`

Mengambil data konversi tanggal dari SQLite.

| Parameter | Tipe | Contoh | Keterangan |
|---|---|---|---|
| `date_iso` | `path` | `2025-07-24` | Format ISO 8601 (YYYY-MM-DD) |

**Response `200 OK`:**
```json
{
  "gregorian_date_iso": "2025-07-24",
  "gregorian_day": 24,
  "gregorian_month": 7,
  "gregorian_year": 2025,
  "hijri_day": 28,
  "hijri_month": "Muharram",
  "hijri_year": 1447,
  "weekday_name_id": "Kamis",
  "event_name": null
}
```

> **Cache:** `Cache-Control: public, max-age=31536000, immutable` (1 tahun)

---

### `GET /api/sirah-simpan?date={date_iso}`

Memuat konten Sirah yang telah disimpan pengguna untuk tanggal tertentu.

| Parameter | Tipe | Contoh |
|---|---|---|
| `date` | `query` | `2025-07-24` |

**Response `200 OK`:**
```json
{
  "date_iso": "2025-07-24",
  "kategori": "Sirah Nabawiyah",
  "judul": "Peristiwa Penting di Muharram",
  "konten_html": "<p>Penjelasan peristiwa...</p>",
  "sumber": "(Sirah Ibnu Hisyam)",
  "updated_at": "2025-07-24T06:00:00"
}
```

**Response `404`:** Belum ada konten tersimpan untuk tanggal ini.

---

### `POST /api/sirah-simpan`

Menyimpan atau memperbarui (upsert) konten Sirah untuk satu tanggal.

**Request Body:**
```json
{
  "date_iso": "2025-07-24",
  "kategori": "Sirah Nabawiyah",
  "judul": "Judul Peristiwa",
  "konten_html": "<p>Isi konten HTML...</p>",
  "sumber": "(Kitab Rujukan)"
}
```

**Response `200 OK`:**
```json
{ "success": true, "date_iso": "2025-07-24" }
```

---

### `DELETE /api/sirah-simpan?date={date_iso}`

Menghapus konten Sirah tersimpan untuk satu tanggal (reset ke default).

| Parameter | Tipe | Contoh |
|---|---|---|
| `date` | `query` | `2025-07-24` |

**Response `200 OK`:**
```json
{ "success": true }
```

---

### `GET /api/sirah?bulan={bulan}&tanggal={tanggal}`

Menghasilkan ringkasan Sirah Nabawiyah via AI Gemini dengan sistem cache berlapis.

| Parameter | Tipe | Contoh |
|---|---|---|
| `bulan` | `query` | `Muharram` |
| `tanggal` | `query` | `28` |

**Response `200 OK` (dari AI / cache):**
```json
{
  "Judul": "Peristiwa Penting di Bulan Muharram",
  "kontent": "Ringkasan peristiwa maksimal 75 kata...",
  "sumber": "Sirah Ibnu Hisyam",
  "url_sumber": "https://...",
  "_cached": true,
  "_model_used": "gemini-3.5-flash"
}
```

> `_cached: true` → Data berasal dari Neon DB cache (instan, 0 biaya API)  
> `_cached: false` → Data baru dari Gemini API (pertama kali di-generate)

**Response `429`:** Semua model Gemini kena rate-limit.

---

## 🔄 Alur Data

### Alur: Ganti Tanggal

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser UI
    participant SQLite as SQLite API
    participant NeonDB as Neon PostgreSQL

    User->>UI: Klik Prev / Next / Pilih Tanggal
    UI->>UI: Fade-out seluruh kanvas (150ms)
    
    par Fetch Paralel
        UI->>SQLite: GET /api/date/{date_iso}
        UI->>NeonDB: GET /api/sirah-simpan?date={date_iso}
    end
    
    SQLite-->>UI: Data tanggal Hijriah & Masehi
    NeonDB-->>UI: Konten Sirah tersimpan (atau 404)
    
    UI->>UI: Update semua elemen kanvas
    UI->>UI: Fade-in seluruh kanvas (150ms)
    UI-->>User: Kanvas tampil dengan data baru
```

---

### Alur: Generate AI Sirah

```mermaid
sequenceDiagram
    actor User
    participant UI as Browser UI
    participant API as FastAPI
    participant Cache as Neon AI Cache
    participant Gemini as Google Gemini

    User->>UI: Klik "Generate Sirah (AI)"
    UI->>UI: Tampilkan Skeleton Loader
    UI->>API: GET /api/sirah?bulan=Muharram&tanggal=28

    API->>Cache: SELECT * FROM sirah_ai_cache WHERE hijri_key = 'muharram_28'

    alt Cache HIT ✅
        Cache-->>API: Data tersimpan
        API-->>UI: { _cached: true, ... }
        UI->>UI: Tampilkan konten (instan ~50ms)
        UI->>UI: Toast: "⚡ Dimuat instan dari cache!"
    else Cache MISS ❌
        Cache-->>API: NULL
        API->>Gemini: POST generateContent (model fallback chain)
        Gemini-->>API: JSON peristiwa Sirah
        API->>Cache: INSERT INTO sirah_ai_cache (ON CONFLICT DO NOTHING)
        API-->>UI: { _cached: false, ... }
        UI->>UI: Tampilkan konten baru
        UI->>UI: Toast: "✨ AI sukses meracik Sirah!"
    end

    UI->>UI: Sembunyikan Skeleton, tampilkan konten
    UI->>API: POST /api/sirah-simpan (auto-save)
```

---

### Alur: Auto-Save

```mermaid
flowchart LR
    A[👤 User Mengetik] --> B{Debounce Timer\n2 detik}
    B -->|Reset timer| A
    B -->|Timer habis| C[POST /api/sirah-simpan]
    C --> D{Response?}
    D -->|✅ 200 OK| E[Toast: ☁️ Tersimpan!]
    D -->|❌ Error| F[Toast: ❌ Gagal!]
```

---

### Strategi Koneksi Neon DB (Warm Start Optimization)

```mermaid
flowchart TD
    A[Request Masuk ke Serverless Function] --> B{_db_conn == None\natau closed?}
    B -->|Ya| C[Buat koneksi baru\npsycopg2.connect]
    B -->|Tidak| D[Reuse koneksi existing]
    C --> E[Simpan ke _db_conn global]
    E --> F[Jalankan Query]
    D --> F
    F --> G[Tutup cursor, bukan koneksi]
    G --> H[Return Response]
    H --> I[Instance tetap hidup\nwarm start berikutnya]
    I -->|Request berikutnya| B
```

---

## 🛠️ Tech Stack

| Layer | Teknologi | Versi | Keterangan |
|---|---|---|---|
| **Frontend** | HTML5 + Vanilla JavaScript | ES2022 | Single-file SPA tanpa framework |
| **Styling** | Tailwind CSS | 3.x (CDN) | Utility-first CSS framework |
| **Fonts** | Google Fonts — Amiri, Inter | - | Tipografi Arab & Latin premium |
| **Export** | html-to-image | 1.11 | DOM-to-PNG renderer |
| **Backend** | FastAPI | 0.115+ | Python ASGI web framework |
| **ASGI Server** | Uvicorn | Latest | Untuk pengembangan lokal |
| **DB Lokal** | SQLite 3 | Bundled | Database kalender read-only |
| **DB Cloud** | Neon PostgreSQL | 16 | Serverless Postgres (konten & AI cache) |
| **AI** | Google Gemini API | v1beta | Multi-model fallback chain |
| **Hosting** | Vercel | - | Serverless deployment |
| **DB Driver** | psycopg2-binary | Latest | PostgreSQL adapter untuk Python |

---

## 🚀 Cara Deploy ke Vercel

### Prasyarat
- Akun [Vercel](https://vercel.com)
- Akun [Neon](https://neon.tech) (PostgreSQL serverless gratis)
- [Google Gemini API Key](https://aistudio.google.com/app/apikey)

### Langkah 1 — Clone Repository

```bash
git clone https://github.com/rssyid/khgt.git
cd khgt
```

### Langkah 2 — Setup Neon PostgreSQL

1. Buat project baru di [neon.tech](https://neon.tech)
2. Copy **Connection String** (format: `postgresql://...`)
3. Tabel akan dibuat **otomatis** saat endpoint pertama kali dipanggil

### Langkah 3 — Deploy ke Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login & deploy
vercel login
vercel --prod
```

### Langkah 4 — Set Environment Variables

Di Vercel Dashboard → **Settings → Environment Variables**:

| Variable | Contoh Nilai | Keterangan |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host/db?sslmode=require` | Connection string Neon PostgreSQL |
| `GEMINI_API_KEY` | `AIzaSy...` | API Key Google Gemini |

---

## 🔐 Environment Variables

```bash
# .env.local (untuk pengembangan lokal)

# Neon PostgreSQL Connection String
DATABASE_URL="postgresql://neondb_owner:password@ep-xxx.neon.tech/neondb?sslmode=require&channel_binding=require"

# Google Gemini API Key
GEMINI_API_KEY="AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
```

> ⚠️ **JANGAN** commit file `.env` atau `.env.local` ke repository. Tambahkan ke `.gitignore`.

---

## 💻 Pengembangan Lokal

### Prasyarat
- Python 3.10+
- pip

### Instalasi

```bash
# Clone repository
git clone https://github.com/rssyid/khgt.git
cd khgt

# Buat virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# Install dependensi
pip install -r requirements.txt
pip install python-dotenv       # Untuk membaca .env lokal

# Buat file .env.local
cp .env.example .env.local
# Edit .env.local dan isi DATABASE_URL & GEMINI_API_KEY
```

### Menjalankan Server

```bash
# Jalankan FastAPI dengan Uvicorn
uvicorn api.index:app --reload --port 8000
```

Buka browser di: `http://localhost:8000`

> **Catatan:** Untuk pengembangan lokal, file statis (`public/`) perlu di-serve terpisah atau akses langsung `public/index.html` via browser. Ubah base URL fetch di JS dari `/api/...` menjadi `http://localhost:8000/api/...` jika diperlukan.

---

## 🔁 Model Fallback Gemini

Sistem menggunakan fallback chain otomatis jika satu model kena rate-limit (`429`):

```python
MODEL_FALLBACK_LIST = [
    "gemini-3.5-flash-lite",   # Prioritas 1: Paling cepat & murah
    "gemini-3.5-flash",        # Prioritas 2: Seimbang
    "gemini-3.5-flash-lite",   # Prioritas 3: Retry lite
    "gemini-3.6-flash",        # Prioritas 4: Model terbaru
]
```

Jika semua model kena limit, API mengembalikan HTTP `429` dengan pesan error terakhir.

---

## 📊 Performa & Optimasi

| Aspek | Strategi | Dampak |
|---|---|---|
| **SQLite Query** | `Cache-Control: max-age=31536000, immutable` | CDN cache 1 tahun, 0ms latency |
| **Neon Connection** | Reuse `_db_conn` global antar warm start | Hemat ~100ms handshake per request |
| **AI Response** | Cache di `sirah_ai_cache` by Hijri key | 0 biaya API untuk tanggal yang sudah pernah di-generate |
| **Image Export** | `pixelRatio: 2` + `styleSheetsFilter` | Gambar HD bersih tanpa CORS error |
| **Date Navigation** | Parallel fetch SQLite + Neon | Data tersedia lebih cepat sebelum animasi selesai |
| **Auto-save** | Debounce 2 detik | Mencegah spam POST ke database |

---

## 🤝 Kontribusi

Kontribusi sangat diterima! Silakan:

1. Fork repository ini
2. Buat branch fitur: `git checkout -b fitur/nama-fitur`
3. Commit perubahan: `git commit -m 'feat: tambah fitur X'`
4. Push ke branch: `git push origin fitur/nama-fitur`
5. Buat Pull Request

---

## 📄 Lisensi

Proyek ini dilisensikan di bawah **MIT License**. Lihat file [LICENSE](LICENSE) untuk detail.

---

<div align="center">

Dibuat dengan ❤️ untuk komunitas Muslim Indonesia

</div>
