import os
import sqlite3
import json
import traceback
import urllib.request
import urllib.error
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "kalender.db")
NEON_URL = os.environ.get("DATABASE_URL")

# ============================================================
# OPTIMASI KINERJA: RE-USE KONEKSI NEON (Warm Starts)
# ============================================================
_db_conn = None
_sirah_table_ready = False
_cache_table_ready = False

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_neon_connection():
    global _db_conn
    if not NEON_URL:
        raise HTTPException(status_code=500, detail="DATABASE_URL belum disetel di Vercel")
    
    if _db_conn is None or _db_conn.closed != 0:
        _db_conn = psycopg2.connect(NEON_URL)
    return _db_conn

def ensure_sirah_table():
    global _sirah_table_ready
    if _sirah_table_ready:
        return
    conn = get_neon_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sirah_edits (
            date_iso TEXT PRIMARY KEY,
            kategori TEXT DEFAULT 'Sirah Nabawiyah',
            judul TEXT,
            konten_html TEXT,
            sumber TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cur.execute("ALTER TABLE sirah_edits ADD COLUMN IF NOT EXISTS kategori TEXT DEFAULT 'Sirah Nabawiyah'")
    conn.commit()
    cur.close()
    _sirah_table_ready = True

def ensure_cache_table():
    global _cache_table_ready
    if _cache_table_ready:
        return
    conn = get_neon_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sirah_ai_cache (
            hijri_key TEXT PRIMARY KEY,
            judul TEXT,
            konten_html TEXT,
            sumber TEXT,
            url_sumber TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    cur.close()
    _cache_table_ready = True

# ============================================================
# ENDPOINT TANGGAL (Dengan Cache-Control 1 Tahun)
# ============================================================
@app.get("/api/date/{date_iso}")
def get_by_gregorian(date_iso: str, response: Response):
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kalender_harian WHERE gregorian_date_iso = ?", (date_iso,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Data tanggal tidak ditemukan")
    return dict(row)

# =============================================
# ENDPOINT SIMPAN, MUAT, & HAPUS TEKS (NEON DB)
# =============================================

class SirahEdit(BaseModel):
    date_iso: str
    kategori: str = "Sirah Nabawiyah"
    judul: str
    konten_html: str
    sumber: str

@app.post("/api/sirah-simpan")
def simpan_sirah(data: SirahEdit):
    """Simpan atau update konten sirah untuk satu tanggal ke Neon PostgreSQL."""
    ensure_sirah_table()
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sirah_edits (date_iso, kategori, judul, konten_html, sumber, updated_at)
            VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (date_iso) DO UPDATE
            SET kategori     = EXCLUDED.kategori,
                judul        = EXCLUDED.judul,
                konten_html  = EXCLUDED.konten_html,
                sumber       = EXCLUDED.sumber,
                updated_at   = CURRENT_TIMESTAMP
        """, (data.date_iso, data.kategori, data.judul, data.konten_html, data.sumber))
        conn.commit()
        cur.close()
        return {"success": True, "date_iso": data.date_iso}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menyimpan ke database: {str(e)}")

@app.get("/api/sirah-simpan")
def load_sirah_tersimpan(date: str):
    """Muat konten sirah tersimpan untuk satu tanggal dari Neon PostgreSQL."""
    ensure_sirah_table()
    try:
        conn = get_neon_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM sirah_edits WHERE date_iso = %s", (date,))
        row = cur.fetchone()
        cur.close()
        if not row:
            raise HTTPException(status_code=404, detail="Tidak ada data tersimpan untuk tanggal ini")
        return dict(row)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal memuat dari database: {str(e)}")

@app.delete("/api/sirah-simpan")
def hapus_sirah_tersimpan(date: str):
    """Hapus editan sirah tersimpan untuk satu tanggal dari Neon PostgreSQL."""
    ensure_sirah_table()
    try:
        conn = get_neon_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM sirah_edits WHERE date_iso = %s", (date,))
        conn.commit()
        cur.close()
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal menghapus data: {str(e)}")

# =============================================
# ENDPOINT AI SIRAH (GEMINI DENGAN CACHE NEON)
# =============================================

MODEL_FALLBACK_LIST = [
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.6-flash",
]

def call_gemini(model: str, api_key: str, payload: dict):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        'Content-Type': 'application/json',
        'x-goog-api-key': api_key
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode('utf-8'))

@app.get("/api/sirah")
def get_sirah_ai(bulan: str, tanggal: str):
    ensure_cache_table()
    hijri_key = f"{bulan.strip()}_{tanggal.strip()}".lower()
    
    # 1. Coba ambil dari cache database Neon dulu (Sangat Cepat & Hemat API)
    try:
        conn = get_neon_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT * FROM sirah_ai_cache WHERE hijri_key = %s", (hijri_key,))
        cached = cur.fetchone()
        cur.close()
        if cached:
            return {
                "Judul": cached["judul"],
                "kontent": cached["konten_html"],
                "sumber": cached["sumber"],
                "url_sumber": cached["url_sumber"],
                "_cached": True
            }
    except Exception as e:
        print("Gagal membaca cache AI Neon:", e)
        # Jika cache gagal, lanjutkan panggil Gemini

    # 2. Panggil API Gemini jika belum ada di cache
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum disetel di Vercel")

    prompt = f"""Carikan satu peristiwa penting dari Sirah Nabawiyah yang terjadi di bulan {bulan} (untuk dikaitkan dengan tanggal {tanggal}). 
Berikan output HANYA dalam format JSON dengan struktur yang tepat seperti ini tanpa tambahan teks apapun di luar JSON:
{{
  "Judul": "Judul Peristiwa",
  "kontent": "Penjelasan inti maksimal 75 kata.",
  "sumber": "Nama Kitab Rujukan",
  "url_sumber": "URL validasi ke Google Books, Wikipedia, atau sumber terpercaya lainnya"
}}"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    last_error_msg = None

    for model in MODEL_FALLBACK_LIST:
        try:
            result = call_gemini(model, api_key, payload)
            text_response = result['candidates'][0]['content']['parts'][0]['text'].strip()

            # Pembersihan JSON
            if text_response.startswith("```json"):
                text_response = text_response[7:]
            elif text_response.startswith("```"):
                text_response = text_response[3:]
            if text_response.endswith("```"):
                text_response = text_response[:-3]
            text_response = text_response.strip()

            parsed_json = json.loads(text_response)

            required_fields = ["Judul", "kontent", "sumber", "url_sumber"]
            for field in required_fields:
                if field not in parsed_json:
                    raise ValueError(f"Format JSON AI tidak lengkap, field '{field}' hilang")

            parsed_json["_model_used"] = model
            
            # 3. Simpan hasil generate AI ke cache database Neon
            try:
                conn = get_neon_connection()
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO sirah_ai_cache (hijri_key, judul, konten_html, sumber, url_sumber)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (hijri_key) DO NOTHING
                """, (hijri_key, parsed_json["Judul"], parsed_json["kontent"], parsed_json["sumber"], parsed_json["url_sumber"]))
                conn.commit()
                cur.close()
            except Exception as cache_err:
                print("Gagal menyimpan cache AI Neon:", cache_err)

            return parsed_json

        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            print(f"[{model}] Google API Error:", error_body)

            try:
                error_json = json.loads(error_body)
                status = error_json.get("error", {}).get("status", "")
            except Exception:
                status = ""

            if e.code == 429 or status == "RESOURCE_EXHAUSTED":
                last_error_msg = error_body
                continue
            else:
                raise HTTPException(status_code=500, detail=f"Gagal dari Google ({model}): {error_body}")

        except json.JSONDecodeError:
            last_error_msg = f"[{model}] AI mengembalikan format teks biasa (bukan JSON)"
            print(last_error_msg)
            continue

        except Exception as e:
            last_error_msg = f"[{model}] {str(e)}"
            print(last_error_msg)
            continue

    raise HTTPException(
        status_code=429,
        detail=f"Semua model kena limit / gagal. Error terakhir: {last_error_msg}"
    )
