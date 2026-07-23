import os
import sqlite3
import json
import traceback
import urllib.request
import urllib.error
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "kalender.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/api/date/{date_iso}")
def get_by_gregorian(date_iso: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kalender_harian WHERE gregorian_date_iso = ?", (date_iso,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Data tanggal tidak ditemukan")
    return dict(row)

# 🌟 Daftar model fallback, urut dari yang paling diutamakan ke cadangan
MODEL_FALLBACK_LIST = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
]

def call_gemini(model: str, api_key: str, payload: dict):
    """Panggil satu model tertentu. Return (result_dict, error_or_None)."""
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

            # Validasi field wajib (tambah url_sumber)
            required_fields = ["Judul", "kontent", "sumber", "url_sumber"]
            for field in required_fields:
                if field not in parsed_json:
                    raise ValueError(f"Format JSON AI tidak lengkap, field '{field}' hilang")

            parsed_json["_model_used"] = model
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
