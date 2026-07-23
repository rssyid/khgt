import os
import sqlite3
import json
import google.generativeai as genai
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

# Konfigurasi Database
DB_PATH = os.path.join(os.path.dirname(__file__), "kalender.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Konfigurasi Gemini (API Key diambil dari Environment Variable Vercel)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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

# ENDPOINT BARU UNTUK AI SIRAH
@app.get("/api/sirah")
def get_sirah_ai(bulan: str, tanggal: str):
    prompt = f"""Carikan satu peristiwa penting dari Sirah Nabawiyah yang terjadi di bulan {bulan} (untuk dikaitkan dengan tanggal {tanggal}). 

Berikan output HANYA dalam format JSON dengan struktur berikut:
{{
  "Judul": "",
  "kontent": "",
  "sumber": ""
}}

Aturan ketat:
1. Seluruh teks harus dalam bahasa Indonesia.
2. Bagian "kontent" maksimal 50 kata, jelaskan inti peristiwanya secara padat.
3. Bagian "sumber" harus merujuk pada kitab Sirah Nabawiyah yang scientific dan teruji (seperti Ar-Rahiq Al-Makhtum atau Sirah Ibnu Hisyam)."""
    
    try:
        # Menggunakan model gemini-1.5-flash karena sangat cepat untuk output JSON
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        text_response = response.text
        
        # Membersihkan output jika AI memberikan format markdown ```json ... ```
        if "```json" in text_response:
            text_response = text_response.split("```json")[1].split("```")[0].strip()
        elif "```" in text_response:
            text_response = text_response.split("```")[1].strip()
            
        parsed_json = json.loads(text_response)
        return parsed_json
        
    except Exception as e:
        print("Error dari Gemini API:", e)
        raise HTTPException(status_code=500, detail="Gagal mengambil data AI")
