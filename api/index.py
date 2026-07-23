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

@app.get("/api/sirah")
def get_sirah_ai(bulan: str, tanggal: str):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum disetel di Vercel")

    prompt = f"""Carikan satu peristiwa penting dari Sirah Nabawiyah yang terjadi di bulan {bulan} (untuk dikaitkan dengan tanggal {tanggal}). 

Berikan output HANYA dalam format JSON dengan struktur yang tepat seperti ini tanpa tambahan teks apapun di luar JSON:
{{
  "Judul": "Judul Peristiwa",
  "kontent": "Penjelasan inti maksimal 50 kata.",
  "sumber": "Nama Kitab Rujukan"
}}"""

    # URL API Resmi Google Gemini 1.5 Flash
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}
    
    # Payload Request
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.4}
    }

    try:
        # Mengirim request HTTP secara langsung
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode('utf-8'))
            
        # Mengekstrak teks balasan dari AI
        text_response = result['candidates'][0]['content']['parts'][0]['text'].strip()
        
        # Membersihkan format Markdown JSON (```json ... ```)
        if text_response.startswith("```json"):
            text_response = text_response[7:]
        elif text_response.startswith("```"):
            text_response = text_response[3:]
            
        if text_response.endswith("```"):
            text_response = text_response[:-3]
            
        text_response = text_response.strip()
        
        # Parse text menjadi JSON asli
        parsed_json = json.loads(text_response)
        
        # Validasi struktur
        if "Judul" not in parsed_json or "kontent" not in parsed_json or "sumber" not in parsed_json:
             raise ValueError("Format JSON tidak memiliki key Judul/kontent/sumber")

        return parsed_json

    except urllib.error.HTTPError as e:
        # Menangkap error dari server Google
        error_msg = e.read().decode('utf-8')
        print("Google API Error:", error_msg)
        raise HTTPException(status_code=500, detail=f"Akses Gemini API Ditolak/Gagal (Cek API Key Anda)")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Gemini mengembalikan format yang bukan JSON")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace)
        raise HTTPException(status_code=500, detail=str(e))
