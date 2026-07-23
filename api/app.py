# app.py - Backend API KHGT (Flask)
# Menyajikan data kalender Hijriah harian dari khgt.muhammadiyah.or.id sebagai JSON
# untuk dikonsumsi oleh frontend kalender.html

import re
from datetime import datetime
from urllib.parse import urlencode

import requests
from bs4 import BeautifulSoup
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

BASE_URL = "https://khgt.muhammadiyah.or.id/kalendar-hijriah"

MONTH_MAP_ID = {
    "jan": 1, "januari": 1, "feb": 2, "februari": 2, "mar": 3, "maret": 3,
    "apr": 4, "april": 4, "mei": 5, "jun": 6, "juni": 6, "jul": 7, "juli": 7,
    "agu": 8, "agt": 8, "agustus": 8, "sep": 9, "sept": 9, "september": 9,
    "okt": 10, "oktober": 10, "nov": 11, "november": 11, "des": 12, "desember": 12,
}

HIJRI_MONTHS = [
    "Muharam", "Safar", "Rabiul Awal", "Rabiul Akhir", "Jumadil Awal",
    "Jumadil Akhir", "Rajab", "Syaban", "Ramadan", "Syawal", "Zulkaidah", "Zulhijah",
]
HIJRI_MONTH_NUM_MAP = {name: i for i, name in enumerate(HIJRI_MONTHS, start=1)}
HIJRI_MONTH_ALIAS_MAP = {
    "muharam": "Muharam", "safar": "Safar", "rabiulawal": "Rabiul Awal",
    "rabiulakhir": "Rabiul Akhir", "jumadilawal": "Jumadil Awal",
    "jumadilakhir": "Jumadil Akhir", "rajab": "Rajab", "syaban": "Syaban",
    "syakban": "Syaban", "ramadan": "Ramadan", "syawal": "Syawal",
    "zulkaidah": "Zulkaidah", "zulhijah": "Zulhijah",
}
WEEKDAY_ID_MAP = {1: "Senin", 2: "Selasa", 3: "Rabu", 4: "Kamis", 5: "Jumat", 6: "Sabtu", 7: "Ahad"}
PASARAN_SET = {"Wage", "Kliwon", "Legi", "Pahing", "Pon"}

GREG_LINE_PATTERN = re.compile(r"^(\d{1,2})\s+([A-Za-zA-y]+)(?:\s+(\d{4}))?$", re.I)
HIJRI_TITLE_PATTERN = re.compile(r"^(.+?)\s+(\d{4})\s*H$", re.I)
EVENT_PATTERN = re.compile(
    r"(\d{1,2})\s+(.+?)\s+(\d{4})\s*H\s*/\s*(\d{1,2})\s+([A-Za-zA-y]+)\s+(\d{4})\s+(.+)$", re.I
)
ARABIC_DIGIT_TRANS = str.maketrans({
    "\u0660": "0", "\u0661": "1", "\u0662": "2", "\u0663": "3", "\u0664": "4",
    "\u0665": "5", "\u0666": "6", "\u0667": "7", "\u0668": "8", "\u0669": "9",
})

def normalize_text(s):
    s = s.translate(ARABIC_DIGIT_TRANS)
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def normalize_hijri_month_name(raw_name):
    raw = normalize_text(raw_name).lower()
    key = re.sub(r"[^a-z]", "", raw)
    return HIJRI_MONTH_ALIAS_MAP.get(key)

def month_name_to_num(name):
    key = normalize_text(name).lower().strip(".")
    return MONTH_MAP_ID.get(key)

def parse_range_years(range_text):
    text = normalize_text(range_text)
    m = re.match(r"([A-Za-z]+)\s+(\d{4})\s*-\s*([A-Za-z]+)\s+(\d{4})$", text, re.I)
    if not m:
        return None
    sm, sy, em, ey = m.groups()
    smn, emn = month_name_to_num(sm), month_name_to_num(em)
    if not smn or not emn:
        return None
    return {"start_month": smn, "start_year": int(sy), "end_month": emn, "end_year": int(ey)}

def infer_gregorian_year(greg_month, range_info):
    if not range_info:
        return None
    if range_info["start_year"] == range_info["end_year"]:
        return range_info["start_year"]
    if greg_month >= range_info["start_month"]:
        return range_info["start_year"]
    return range_info["end_year"]

def fetch_html(year):
    params = {"year": year}
    url = f"{BASE_URL}?{urlencode(params)}"
    headers = {"User-Agent": "Mozilla/5.0", "Accept-Language": "id,en;q=0.9"}
    r = requests.get(url, timeout=60, headers=headers)
    r.raise_for_status()
    return r.text

def parse_hijri_title(title_text):
    text = normalize_text(title_text)
    m = HIJRI_TITLE_PATTERN.match(text)
    if not m:
        return None
    raw_month_name, hijri_year = m.groups()
    hijri_month = normalize_hijri_month_name(raw_month_name)
    if not hijri_month:
        return None
    return {"hijri_month": hijri_month, "hijri_month_num": HIJRI_MONTH_NUM_MAP[hijri_month], "hijri_year": int(hijri_year)}

def find_month_blocks(soup):
    blocks = []
    for block in soup.select("div.p-4.rounded.bg-gray.border"):
        month_info = None
        for h in block.find_all(["h1", "h2", "h3", "h4", "h5", "div"]):
            txt = normalize_text(h.get_text(" ", strip=True))
            parsed = parse_hijri_title(txt)
            if parsed:
                month_info = parsed
                break
        if not month_info:
            continue
        range_text = None
        for p in block.find_all(["p", "div", "span"]):
            txt = normalize_text(p.get_text(" ", strip=True))
            if re.match(r"[A-Za-z]+\s+\d{4}\s*-\s*[A-Za-z]+\s+\d{4}$", txt):
                range_text = txt
                break
        blocks.append({
            "container": block, "hijri_month": month_info["hijri_month"],
            "hijri_month_num": month_info["hijri_month_num"], "hijri_year": month_info["hijri_year"],
            "range_text": range_text,
            "range_info": parse_range_years(range_text) if range_text else None,
        })
    return blocks

def extract_hijri_day_from_card(card):
    texts = [normalize_text(x.get_text(" ", strip=True)) for x in card.find_all(["h1","h2","h3","h4","h5","div","span","p","small"])]
    texts = [t for t in texts if t]
    for t in texts:
        if re.fullmatch(r"\d{1,2}", t):
            val = int(t)
            if 1 <= val <= 30:
                return val
    for t in [normalize_text(s) for s in card.stripped_strings]:
        if re.fullmatch(r"\d{1,2}", t):
            val = int(t)
            if 1 <= val <= 30:
                return val
    return None

def extract_gregorian_from_card(card, range_info):
    texts = [normalize_text(s) for s in card.stripped_strings]
    for t in texts:
        m = GREG_LINE_PATTERN.match(t)
        if m:
            day, month_name, year = m.groups()
            month_num = month_name_to_num(month_name)
            if month_num:
                greg_year = int(year) if year else infer_gregorian_year(month_num, range_info)
                if greg_year:
                    return greg_year, month_num, int(day), t
    return None, None, None, None

def extract_pasaran_from_card(card):
    texts = [normalize_text(s) for s in card.stripped_strings]
    for t in texts:
        if t in PASARAN_SET:
            return t
    return None

def gregorian_to_weekday_info(gregorian_date_iso):
    dt = datetime.strptime(gregorian_date_iso, "%Y-%m-%d")
    py_weekday = dt.weekday()
    weekday_num = py_weekday + 1
    weekday_name_id = "Ahad" if weekday_num == 7 else WEEKDAY_ID_MAP[weekday_num]
    return weekday_num, weekday_name_id

def extract_records_from_block(block_info):
    container = block_info["container"]
    records, seen = [], set()
    cards = container.select("div.d-flex.align-items-center.flex-column.justify-content-start.rounded.p-1.bg-white")
    for card in cards:
        greg_year, greg_month, greg_day, _ = extract_gregorian_from_card(card, block_info["range_info"])
        hijri_day = extract_hijri_day_from_card(card)
        pasaran = extract_pasaran_from_card(card)
        if not greg_year or not greg_month or not greg_day or not hijri_day:
            continue
        gregorian_date_iso = f"{greg_year:04d}-{greg_month:02d}-{greg_day:02d}"
        weekday_num, weekday_name_id = gregorian_to_weekday_info(gregorian_date_iso)
        rec = {
            "hijri_year": block_info["hijri_year"], "hijri_month": block_info["hijri_month"],
            "hijri_month_num": block_info["hijri_month_num"], "hijri_day": hijri_day,
            "gregorian_year": greg_year, "gregorian_month": greg_month, "gregorian_day": greg_day,
            "gregorian_date_iso": gregorian_date_iso, "weekday_num": weekday_num,
            "weekday_name_id": weekday_name_id, "pasaran": pasaran,
            "hijri_date_raw": f"{hijri_day} {block_info['hijri_month']} {block_info['hijri_year']}",
            "event_name": None, "is_special_day": 0,
        }
        key = (rec["hijri_year"], rec["hijri_month_num"], rec["hijri_day"], rec["gregorian_date_iso"])
        if key in seen:
            continue
        seen.add(key)
        records.append(rec)
    return records

def extract_events_from_block(block_info):
    container = block_info["container"]
    events, seen = [], set()
    for tag in container.find_all(["div", "li", "p", "span", "small"]):
        txt = normalize_text(tag.get_text(" ", strip=True))
        if "/" not in txt:
            continue
        m = EVENT_PATTERN.match(txt)
        if not m:
            continue
        hijri_day, raw_hijri_month, hijri_year, greg_day, greg_month_name, greg_year, event_name = m.groups()
        hijri_month = normalize_hijri_month_name(raw_hijri_month)
        greg_month_num = month_name_to_num(greg_month_name)
        if not hijri_month or not greg_month_num:
            continue
        gregorian_date_iso = f"{int(greg_year):04d}-{greg_month_num:02d}-{int(greg_day):02d}"
        rec = {
            "hijri_year": int(hijri_year), "hijri_month": hijri_month,
            "hijri_month_num": HIJRI_MONTH_NUM_MAP[hijri_month], "hijri_day": int(hijri_day),
            "gregorian_date_iso": gregorian_date_iso, "event_name": normalize_text(event_name),
            "is_special_day": 1,
        }
        key = (rec["hijri_year"], rec["hijri_month_num"], rec["hijri_day"], rec["gregorian_date_iso"], rec["event_name"])
        if key in seen:
            continue
        seen.add(key)
        events.append(rec)
    return events

CACHE = {}

def scrape_khgt_hijri_year(year):
    if year in CACHE:
        return CACHE[year]
    html = fetch_html(year)
    soup = BeautifulSoup(html, "lxml")
    month_blocks = find_month_blocks(soup)
    if not month_blocks:
        raise ValueError("Blok bulan Hijriah tidak ditemukan.")
    all_records, all_events = [], []
    for b in month_blocks:
        all_records.extend(extract_records_from_block(b))
        all_events.extend(extract_events_from_block(b))
    events_by_key = {}
    for e in all_events:
        key = (e["hijri_year"], e["hijri_month_num"], e["hijri_day"], e["gregorian_date_iso"])
        if key not in events_by_key:
            events_by_key[key] = {"names": set(), "is_special": 0}
        events_by_key[key]["names"].add(e["event_name"])
        events_by_key[key]["is_special"] = max(events_by_key[key]["is_special"], e["is_special_day"])
    by_date = {}
    for r in all_records:
        key = (r["hijri_year"], r["hijri_month_num"], r["hijri_day"], r["gregorian_date_iso"])
        if key in events_by_key:
            r["event_name"] = " | ".join(sorted(events_by_key[key]["names"]))
            r["is_special_day"] = events_by_key[key]["is_special"]
        by_date[r["gregorian_date_iso"]] = r
    CACHE[year] = by_date
    return by_date

@app.route("/api/khgt")
def api_khgt():
    date_str = request.args.get("date")
    if not date_str:
        date_str = datetime.today().strftime("%Y-%m-%d")
    try:
        target_dt = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Format tanggal harus YYYY-MM-DD"}), 400

    found_year = None
    for hijri_year_guess in range(1440, 1460):
        try:
            data = scrape_khgt_hijri_year(hijri_year_guess)
        except Exception:
            continue
        if date_str in data:
            found_year = hijri_year_guess
            rec = data[date_str]
            return jsonify(rec)

    return jsonify({"error": f"Data untuk tanggal {date_str} tidak ditemukan di KHGT."}), 404

# Vercel serverless entrypoint: variabel "app" langsung diekspos, tidak perlu app.run()
