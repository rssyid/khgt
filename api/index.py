import os
import sqlite3
import json
import traceback
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
    # 1. Cek ketersediaan API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY belum disetel di Vercel Environment Variables")
    
    genai.configure(api_key=api_key)

    prompt = f"""Carikan satu peristiwa penting dari Sirah Nabawiyah yang terjadi di bulan {bulan} (untuk dikaitkan dengan tanggal {tanggal}). 

Berikan output HANYA dalam format JSON dengan struktur yang tepat seperti ini tanpa tambahan teks apapun di luar JSON:
{{
  "Judul": "Judul Peristiwa",
  "kontent": "Penjelasan inti maksimal 50 kata.",
  "sumber": "Nama Kitab Rujukan"
}}"""

    try:
        # 2. Gunakan model flash dan paksakan output sebagai plain text JSON
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Generation config agar output lebih stabil
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.4,
            )
        )
        
        text_response = response.text.strip()
        
        # 3. Pembersihan format markdown yang lebih agresif
        if text_response.startswith("```json"):
            text_response = text_response.replace("```json", "", 1)
        if text_response.startswith("```"):
            text_response = text_response.replace("```", "", 1)
        if text_response.endswith("```"):
            # Hapus dari belakang (reverse replace)
            text_response = text_response[::-1].replace("```", "", 1)[::-1]
            
        text_response = text_response.strip()
        
        # 4. Coba parsing JSON
        parsed_json = json.loads(text_response)
        
        # Validasi struktur wajib
        if "Judul" not in parsed_json or "kontent" not in parsed_json or "sumber" not in parsed_json:
             raise ValueError("Format JSON dari AI tidak memiliki atribut Judul, kontent, atau sumber")

        return parsed_json

    except json.JSONDecodeError as e:
        print("Raw AI response:", response.text)
        raise HTTPException(status_code=500, detail=f"Gagal mem-parsing output AI sebagai JSON: {str(e)}")
    except Exception as e:
        error_trace = traceback.format_exc()
        print(error_trace) # Log untuk dilihat di dashboard Vercel
        raise HTTPException(status_code=500, detail=str(e))
