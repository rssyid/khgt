from flask import Flask, jsonify, request, Response
import os as _os
from flask_cors import CORS
import requests
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

API_BASE = "https://api-khgt.muhammadiyah.or.id/api"
TIMEOUT = 60
CACHE = {}

MONTH_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}
HIJRI_MONTHS = {
    1: "Muharam", 2: "Safar", 3: "Rabiul Awal", 4: "Rabiul Akhir", 5: "Jumadil Awal", 6: "Jumadil Akhir",
    7: "Rajab", 8: "Syaban", 9: "Ramadan", 10: "Syawal", 11: "Zulkaidah", 12: "Zulhijah"
}
WEEKDAY_ID = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Ahad"}
PASARAN = ["Legi", "Pahing", "Pon", "Wage", "Kliwon"]
PASARAN_EPOCH = datetime(2026, 7, 21)  # dari contoh user: 2026-07-21 = Selasa Pon
PASARAN_EPOCH_NAME = "Pon"


def pasaran_for_date(dt: datetime) -> str:
    idx0 = PASARAN.index(PASARAN_EPOCH_NAME)
    delta = (dt.date() - PASARAN_EPOCH.date()).days
    return PASARAN[(idx0 + delta) % 5]


def weekday_info(iso_date: str):
    dt = datetime.strptime(iso_date, "%Y-%m-%d")
    n = dt.weekday() + 1
    return n, WEEKDAY_ID[n if n <= 7 else 7]


def fetch_calendar_year(year: int, year_type: str = "masehi"):
    key = (year, year_type)
    if key in CACHE:
        return CACHE[key]

    params = {}
    if year_type == "hijriah":
        url = f"{API_BASE}/calendar/{year}"
        params = {"type": "hijriah"}
    else:
        url = f"{API_BASE}/calendar/{year}"

    r = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    data = r.json()
    CACHE[key] = data
    return data


def flatten_calendar_payload(payload):
    items = []
    raw = payload.get("data", payload if isinstance(payload, list) else [])

    def walk(obj):
        if isinstance(obj, list):
            for x in obj:
                walk(x)
        elif isinstance(obj, dict):
            keys = {k.lower() for k in obj.keys()}
            if any(k in keys for k in ["gregorian_date", "gregorian_date_iso", "date", "masehi", "hijri", "hijri_year", "hijriyah"]):
                items.append(obj)
            else:
                for v in obj.values():
                    walk(v)

    walk(raw)
    return items


def pick(*vals):
    for v in vals:
        if v is not None and v != "":
            return v
    return None


def normalize_record(obj):
    g_iso = pick(obj.get("gregorian_date_iso"), obj.get("gregorian_date"), obj.get("date"), obj.get("masehi_date"))
    if isinstance(g_iso, dict):
        g_iso = pick(g_iso.get("iso"), g_iso.get("date"))
    if not g_iso:
        g = pick(obj.get("gregorian"), obj.get("masehi"))
        if isinstance(g, dict):
            g_iso = pick(g.get("date"), g.get("iso"), g.get("gregorian_date_iso"))
    if not g_iso:
        return None
    g_iso = str(g_iso)[:10]
    dt = datetime.strptime(g_iso, "%Y-%m-%d")

    hijri = pick(obj.get("hijri"), obj.get("hijriyah"), obj.get("hijriah"))
    hy = hm = hd = None
    hm_name = None
    if isinstance(hijri, dict):
        hy = pick(hijri.get("year"), hijri.get("h_year"), obj.get("hijri_year"))
        hm = pick(hijri.get("month"), hijri.get("month_num"), hijri.get("month_number"), obj.get("hijri_month_num"))
        hd = pick(hijri.get("day"), obj.get("hijri_day"))
        hm_name = pick(hijri.get("month_name"), obj.get("hijri_month"))

    hy = pick(hy, obj.get("hijri_year"))
    hm = pick(hm, obj.get("hijri_month_num"))
    hd = pick(hd, obj.get("hijri_day"))
    hm_name = pick(hm_name, obj.get("hijri_month"))

    if hm and not hm_name:
        hm_name = HIJRI_MONTHS.get(int(hm))

    weekday_num, weekday_name_id = weekday_info(g_iso)
    event_name = pick(obj.get("event_name"), obj.get("event"), obj.get("special_day"), obj.get("keterangan"), obj.get("description"))
    is_special_day = 1 if event_name else 0

    return {
        "hijri_year": int(hy) if hy else None,
        "hijri_month": hm_name,
        "hijri_month_num": int(hm) if hm else None,
        "hijri_day": int(hd) if hd else None,
        "gregorian_year": dt.year,
        "gregorian_month": dt.month,
        "gregorian_day": dt.day,
        "gregorian_date_iso": g_iso,
        "weekday_num": weekday_num,
        "weekday_name_id": weekday_name_id,
        "pasaran": pasaran_for_date(dt),
        "hijri_date_raw": f"{hd} {hm_name} {hy}" if hy and hm_name and hd else None,
        "event_name": event_name,
        "is_special_day": is_special_day,
    }


def get_record_for_date(iso_date: str):
    year = int(iso_date[:4])
    for y in [year - 1, year, year + 1]:
        try:
            payload = fetch_calendar_year(y, "masehi")
            for raw in flatten_calendar_payload(payload):
                rec = normalize_record(raw)
                if rec and rec["gregorian_date_iso"] == iso_date:
                    return rec
        except Exception:
            continue
    return None


@app.route("/")
def index():
    html_path = _os.path.join(_os.path.dirname(__file__), "kalender.html")
    with open(html_path, "r", encoding="utf-8") as f:
        return Response(f.read(), mimetype="text/html")


@app.route("/api/khgt")
def api_khgt():
    date_str = request.args.get("date") or datetime.today().strftime("%Y-%m-%d")
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Format tanggal harus YYYY-MM-DD"}), 400

    rec = get_record_for_date(date_str)
    if not rec:
        return jsonify({"error": f"Data untuk tanggal {date_str} tidak ditemukan dari API KHGT."}), 404
    return jsonify(rec)


@app.route("/api/debug/calendar/<int:year>")
def debug_calendar(year):
    t = request.args.get("type", "masehi")
    payload = fetch_calendar_year(year, t)
    flat = flatten_calendar_payload(payload)
    sample = [x for x in [normalize_record(o) for o in flat[:5]] if x]
    return jsonify({
        "top_keys": list(payload.keys()) if isinstance(payload, dict) else None,
        "flat_count": len(flat),
        "sample": sample,
    })


# Vercel serverless entrypoint: expose variable `app` directly
