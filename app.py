"""
Doctor Bangladesh Scraper — Streamlit App
==========================================
Run with:  streamlit run app.py

Deploy free at: https://streamlit.io/cloud
  1. Push this file to a GitHub repo
  2. Go to share.streamlit.io → "New app" → pick your repo
  3. Set Main file: app.py
  4. Deploy — no server needed!
"""

import csv
import io
import re
import time
import threading
import queue
from datetime import datetime
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
import streamlit as st

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Doctor BD Scraper",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Main background */
  .stApp { background: #f0f4f8; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #1a2744;
    color: #e8edf5;
  }
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {
    color: #e8edf5 !important;
  }
  [data-testid="stSidebar"] .stCheckbox label { color: #c8d4e8 !important; }

  /* Cards */
  .metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    border-left: 4px solid #2563eb;
    margin-bottom: 12px;
  }
  .metric-card .number { font-size: 2rem; font-weight: 700; color: #1e3a6e; }
  .metric-card .label  { font-size: 0.8rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em; }

  /* Status badges */
  .badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-green  { background: #d1fae5; color: #065f46; }
  .badge-yellow { background: #fef3c7; color: #92400e; }
  .badge-red    { background: #fee2e2; color: #991b1b; }
  .badge-blue   { background: #dbeafe; color: #1e40af; }

  /* Doctor row */
  .doc-row {
    background: white;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 6px 0;
    border-left: 3px solid #2563eb;
    font-size: 0.88rem;
  }
  .doc-name  { font-weight: 700; color: #1e3a6e; }
  .doc-meta  { color: #6b7280; margin-top: 2px; }

  /* Download button */
  .stDownloadButton > button {
    background: #2563eb !important;
    color: white !important;
    border-radius: 8px !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    border: none !important;
    width: 100%;
  }
  .stDownloadButton > button:hover { background: #1d4ed8 !important; }

  /* Progress area */
  .log-box {
    background: #0f172a;
    color: #a3e635;
    font-family: 'Courier New', monospace;
    font-size: 0.78rem;
    padding: 16px;
    border-radius: 8px;
    height: 260px;
    overflow-y: auto;
    line-height: 1.6;
  }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  Constants
# ─────────────────────────────────────────────────────────────────────────────
CITY_OPTIONS = {
    "Dhaka":        "https://www.doctorbangladesh.com/doctors-dhaka/",
    "Chittagong":   "https://www.doctorbangladesh.com/doctors-chittagong/",
    "Sylhet":       "https://www.doctorbangladesh.com/doctors-sylhet/",
    "Rajshahi":     "https://www.doctorbangladesh.com/doctors-rajshahi/",
    "Khulna":       "https://www.doctorbangladesh.com/doctors-khulna/",
    "Rangpur":      "https://www.doctorbangladesh.com/doctors-rangpur/",
    "Mymensingh":   "https://www.doctorbangladesh.com/doctors-mymensingh/",
    "Barisal":      "https://www.doctorbangladesh.com/doctors-barisal/",
    "Comilla":      "https://www.doctorbangladesh.com/doctors-cumilla/",
    "Bogra":        "https://www.doctorbangladesh.com/doctors-bogura/",
    "Narayanganj":  "https://www.doctorbangladesh.com/doctors-narayanganj/",
    "Pabna":        "https://www.doctorbangladesh.com/doctors-pabna/",
    "Kushtia":      "https://www.doctorbangladesh.com/doctors-kushtia/",
}

CITY_SLUG_MAP = {
    "Dhaka": "dhaka", "Chittagong": "chittagong", "Sylhet": "sylhet",
    "Rajshahi": "rajshahi", "Khulna": "khulna", "Rangpur": "rangpur",
    "Mymensingh": "mymensingh", "Barisal": "barisal", "Comilla": "comilla",
    "Bogra": "bogra", "Narayanganj": "narayanganj", "Pabna": "pabna",
    "Kushtia": "kushtia",
}

CITY_COORDS = {
    "dhaka":       (23.8103,  90.4125), "chittagong": (22.3569, 91.7832),
    "sylhet":      (24.8949,  91.8687), "rajshahi":   (24.3745, 88.6042),
    "khulna":      (22.8456,  89.5403), "rangpur":    (25.7439, 89.2752),
    "mymensingh":  (24.7471,  90.4203), "barisal":    (22.7010, 90.3535),
    "comilla":     (23.4607,  91.1809), "bogra":      (24.8465, 89.3777),
    "narayanganj": (23.6238,  90.5000), "pabna":      (24.0064, 89.2372),
    "kushtia":     (23.9014,  89.1226),
}

SPECIALTY_MAP = {
    "ent": "ent", "ear nose throat": "ent", "otolaryngologist": "ent",
    "cardiologist": "cardiology", "cardiology": "cardiology",
    "medicine": "medicine", "internal medicine": "medicine",
    "dermatologist": "dermatology", "dermatology": "dermatology",
    "orthopedic": "orthopedics", "gynecologist": "gynecology",
    "gynecology": "gynecology", "obstetrics": "gynecology",
    "pediatrician": "pediatrics", "pediatrics": "pediatrics",
    "neurology": "neurology", "neurologist": "neurology",
    "gastroenterology": "gastroenterology", "urology": "urology",
    "ophthalmology": "ophthalmology", "eye": "ophthalmology",
    "psychiatry": "psychiatry", "endocrinology": "endocrinology",
    "diabetes": "endocrinology", "oncology": "oncology",
    "nephrology": "nephrology", "kidney": "nephrology",
    "hepatology": "hepatology", "liver": "hepatology",
    "pulmonology": "pulmonology", "chest": "pulmonology",
    "dentist": "dentistry", "dental": "dentistry",
    "surgery": "surgery", "surgeon": "surgery",
    "general physician": "general-physician",
    "physiotherapy": "physiotherapy",
}

CSV_COLUMNS = [
    "Title", "Content", "Excerpt", "Ad Type", "Categories", "Locations",
    "Tags", "Images", "Video URL", "Post Date", "Post Author ID",
    "Author First name", "Author Last name", "Author Email", "Author Username",
    "Pricing Type", "Price Type", "Price", "Max Price", "Social Profiles",
    "Website", "Email", "Phone", "WhatsApp", "Address", "Zip Code",
    "Map Latitude", "Map Longitude", "Hide Map", "Never Expire", "Expiry Date",
    "Views", "Business Hours", "Status",
    "radio_axdl9k6wlb", "text_j456myldo8", "text_mu65ovg87y",
    "text_we3ui010yl", "text_10vmr6dbji6", "textarea_155974l42hu",
    "text_1wiw01ojiux", "text_2031eyb4gd7", "text_mp3lyhty",
    "rtcl_faqs", "rtcl_services", "radio_mf2jhq86", "rtcl_food_menu",
    "text_mfceq3o5", "text_mfceqtn7", "text_mfces0nu", "number_138jpa21fam",
    "text_mdr1nk2f", "text_mdr1nxgn", "text_mdr1o6nn", "text_mdr1oc0p",
    "text_mdr1oqi1", "text_mdr1p2rp", "text_mdr1pdly", "text_mdr1q17h",
    "text_mdr1qyud", "text_mdr1ruiv", "text_mdr1s7ch", "text_mdr1sojf",
    "text_mdr1t546", "text_mdr1tild",
]

EMPTY_ROW = {col: "" for col in CSV_COLUMNS}

# ─────────────────────────────────────────────────────────────────────────────
#  Scraping helpers
# ─────────────────────────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    })
    return s


def fetch(session, url, retries=3):
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            return BeautifulSoup(r.text, "html.parser")
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(2)
    return None


def clean(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def guess_gender(name, extra=""):
    low = (name + " " + extra).lower()
    if any(h in low for h in ["female", "mrs.", " ms.", "gynecol", "obstet"]):
        return "female"
    return "male"


def guess_category(text):
    low = text.lower()
    for kw, slug in SPECIALTY_MAP.items():
        if kw in low:
            return slug
    words = re.findall(r"[a-z]+", low)
    return words[0] if words else "general"


def get_doctor_urls(session, city_url, max_pages):
    urls = []
    base = city_url.rstrip("/")
    for page in range(1, (max_pages or 999) + 1):
        purl = base + "/" if page == 1 else f"{base}/page/{page}/"
        s = fetch(session, purl)
        if not s:
            break
        links = s.find_all("a", href=re.compile(r"/dr[-\w]+/?$"))
        new = list({a["href"] for a in links if a.get("href")})
        if not new:
            break
        urls.extend(new)
        nxt = s.find("a", class_=re.compile(r"next"), string=re.compile(r"next|›|»", re.I))
        if not nxt:
            break
        time.sleep(0.8)
    return list(dict.fromkeys(urls))


def parse_doctor(session, url, city_slug, wp_config):
    s = fetch(session, url)
    if not s:
        return None

    row = {**EMPTY_ROW}
    row.update({
        "Post Date":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Post Author ID": wp_config["author_id"],
        "Author Email":   wp_config["author_email"],
        "Author Username":wp_config["author_username"],
        "Pricing Type":   "price",
        "Price Type":     "regular",
        "Never Expire":   "1",
        "Expiry Date":    wp_config["expiry_date"],
        "Status":         "publish",
        "Locations":      city_slug,
    })

    # Name
    h1 = s.find("h1")
    name = clean(h1.get_text()) if h1 else ""
    row["Title"] = name

    # Photo
    img = s.find("img", alt=re.compile(re.escape(name[:8]), re.I)) if name else None
    if img and img.get("src"):
        row["Images"] = img["src"]

    # Bullet info
    bullets = []
    for li in s.select("h1 ~ ul li, h1 + ul li, article li")[:12]:
        t = clean(li.get_text())
        if t and len(t) < 250:
            bullets.append(t)

    degrees = designation = hospital = specialty = ""
    for b in bullets:
        low = b.lower()
        if re.match(r"(mbbs|bds|fcps|ms\b|md\b|mrcp|frcs|phd|dlo|mcps)", low):
            degrees = b
        elif re.search(r"\b(consultant|professor|registrar|associate|lecturer|fellow|senior)\b", low):
            designation = b
        elif re.search(r"\b(hospital|medical college|institute|cmh|bsmmu|dmch)\b", low):
            hospital = b
        elif re.search(r"\b(specialist|surgeon|physician|therapist)\b", low):
            specialty = b

    # BMDC
    page_text = s.get_text(" ", strip=True)
    bm = re.search(r"BMDC\s*Reg(?:istration)?\s*(?:No|#|:)?\s*[:\-]?\s*([A-Z0-9\-]+)", page_text, re.I)
    if bm:
        row["text_10vmr6dbji6"] = bm.group(1).strip()

    # Chamber section
    ch = s.find(lambda t: t.name in ("h2","h3","h4","strong","b")
                and re.search(r"chamber|appointment", t.get_text(), re.I))
    clinic = addr = hours = phone = ""
    if ch:
        container = ch.find_parent(["div","section","article"]) or ch
        bt = clean(container.get_text(" "))
        bold = ch.find_next(["strong","b","a"])
        if bold:
            clinic = clean(bold.get_text())
        am = re.search(r"[Aa]ddress\s*:\s*(.+?)(?:Visiting|Phone|Appointment|$)", bt)
        if am:
            addr = clean(am.group(1))
        vm = re.search(r"[Vv]isiting\s*[Hh]our[s]?\s*:\s*(.+?)(?:Phone|Appointment|Call|$)", bt)
        if vm:
            hours = clean(vm.group(1))
        pm = re.search(r"(?:Appointment|Phone|Call)\s*:\s*(\+?[\d\s\-\(\)]+)", bt)
        if pm:
            phone = clean(pm.group(1))
    if not phone:
        pm = re.search(r"(\+880[\d\s\-]{8,}|01[3-9]\d{8})", page_text)
        if pm:
            phone = clean(pm.group(1))

    # Bio
    ah = s.find(lambda t: t.name in ("h2","h3","h4") and re.search(r"about", t.get_text(), re.I))
    bio = ""
    if ah:
        parts = []
        for sib in ah.find_next_siblings():
            if sib.name in ("h2","h3","h4"):
                break
            parts.append(str(sib))
        bio = "".join(parts)
    if not bio:
        bio = f"<p><strong>{name}</strong>"
        if degrees:   bio += f" holds {degrees}."
        if specialty: bio += f" Specialist in {specialty}."
        if hospital:  bio += f" Based at {hospital}."
        bio += "</p>"

    excerpt = re.sub(r"<[^>]+>", " ", bio)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()[:300]

    dept_m = re.search(r"dept(?:artment)?\s+of\s+([A-Za-z &\-]+)", page_text, re.I)
    dept = clean(dept_m.group(1)) if dept_m else specialty

    lat, lng = CITY_COORDS.get(city_slug, ("", ""))

    row.update({
        "Content": bio, "Excerpt": excerpt,
        "Categories": guess_category(specialty or designation),
        "Phone": phone, "Address": addr,
        "Map Latitude": str(lat), "Map Longitude": str(lng),
        "radio_axdl9k6wlb": guess_gender(name, degrees + specialty),
        "text_j456myldo8": designation,
        "text_mu65ovg87y": hospital,
        "text_we3ui010yl": addr,
        "textarea_155974l42hu": degrees,
        "text_1wiw01ojiux": dept,
        "text_2031eyb4gd7": clinic,
        "text_mp3lyhty": hours,
    })
    return row


def rows_to_csv(rows):
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode("utf-8-sig")


# ─────────────────────────────────────────────────────────────────────────────
#  Session state init
# ─────────────────────────────────────────────────────────────────────────────
if "scraped_rows" not in st.session_state:
    st.session_state.scraped_rows = []
if "scraping" not in st.session_state:
    st.session_state.scraping = False
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []
if "stats" not in st.session_state:
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}

# ─────────────────────────────────────────────────────────────────────────────
#  Sidebar — settings
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🩺 Doctor BD Scraper")
    st.markdown("---")

    st.markdown("### 🌆 Select Cities")
    selected_cities = []
    col_a, col_b = st.columns(2)
    city_list = list(CITY_OPTIONS.keys())
    for i, city in enumerate(city_list):
        col = col_a if i % 2 == 0 else col_b
        if col.checkbox(city, value=(city == "Dhaka"), key=f"city_{city}"):
            selected_cities.append(city)

    st.markdown("---")
    st.markdown("### ⚙️ Scraper Settings")
    max_pages   = st.number_input("Max pages per city", min_value=1, max_value=50, value=2,
                                  help="Each page has ~10 doctors")
    max_doctors = st.number_input("Max doctors total (0 = unlimited)", min_value=0, value=50)
    delay       = st.slider("Delay between requests (sec)", 0.5, 3.0, 1.0, 0.5)

    st.markdown("---")
    st.markdown("### 🔧 WordPress Settings")
    author_id    = st.text_input("Post Author ID", value="1")
    author_email = st.text_input("Author Email", value="admin@yoursite.com")
    author_user  = st.text_input("Author Username", value="admin")
    expiry_date  = st.text_input("Expiry Date", value="2029-01-01 00:00:00")

    st.markdown("---")
    st.caption("Built for RTCL WordPress import format")

# ─────────────────────────────────────────────────────────────────────────────
#  Main area
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("# 🩺 Doctor Bangladesh Scraper")
st.markdown("Scrape doctor listings from **doctorbangladesh.com** and download a ready-to-import CSV for RTCL WordPress.")

st.markdown("---")

# ── Metrics row ───────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f"""<div class="metric-card">
        <div class="number">{len(st.session_state.scraped_rows)}</div>
        <div class="label">Doctors Scraped</div>
    </div>""", unsafe_allow_html=True)
with m2:
    st.markdown(f"""<div class="metric-card" style="border-color:#16a34a">
        <div class="number">{st.session_state.stats['success']}</div>
        <div class="label">Successful</div>
    </div>""", unsafe_allow_html=True)
with m3:
    st.markdown(f"""<div class="metric-card" style="border-color:#dc2626">
        <div class="number">{st.session_state.stats['failed']}</div>
        <div class="label">Failed</div>
    </div>""", unsafe_allow_html=True)
with m4:
    st.markdown(f"""<div class="metric-card" style="border-color:#d97706">
        <div class="number">{len(selected_cities)}</div>
        <div class="label">Cities Selected</div>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ── Control buttons ───────────────────────────────────────────────────────────
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 3])

with btn_col1:
    start_btn = st.button(
        "▶ Start Scraping",
        disabled=st.session_state.scraping or not selected_cities,
        use_container_width=True,
        type="primary",
    )

with btn_col2:
    clear_btn = st.button(
        "🗑 Clear Results",
        disabled=st.session_state.scraping,
        use_container_width=True,
    )

with btn_col3:
    if st.session_state.scraped_rows:
        csv_bytes = rows_to_csv(st.session_state.scraped_rows)
        fname = f"doctorbangladesh_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        st.download_button(
            label=f"⬇ Download CSV  ({len(st.session_state.scraped_rows)} doctors)",
            data=csv_bytes,
            file_name=fname,
            mime="text/csv",
            use_container_width=True,
        )
    else:
        st.button("⬇ Download CSV", disabled=True, use_container_width=True)

# ── Clear handler ─────────────────────────────────────────────────────────────
if clear_btn:
    st.session_state.scraped_rows = []
    st.session_state.log_lines = []
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}
    st.rerun()

# ── Live log + progress ───────────────────────────────────────────────────────
log_placeholder   = st.empty()
prog_placeholder  = st.empty()
status_placeholder = st.empty()

def render_log():
    lines = st.session_state.log_lines[-30:]
    html = "<br>".join(lines)
    log_placeholder.markdown(
        f'<div class="log-box">{html}</div>', unsafe_allow_html=True
    )

render_log()

# ─────────────────────────────────────────────────────────────────────────────
#  Scraping logic (runs synchronously so Streamlit can update UI)
# ─────────────────────────────────────────────────────────────────────────────
def add_log(msg, kind="info"):
    colors = {"info": "#a3e635", "ok": "#34d399", "err": "#f87171", "city": "#60a5fa", "warn": "#fbbf24"}
    color = colors.get(kind, "#a3e635")
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_lines.append(
        f'<span style="color:#6b7280">[{ts}]</span> <span style="color:{color}">{msg}</span>'
    )


if start_btn and selected_cities and not st.session_state.scraping:
    st.session_state.scraping = True
    st.session_state.scraped_rows = []
    st.session_state.log_lines = []
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}

    wp_config = {
        "author_id":    author_id,
        "author_email": author_email,
        "author_username": author_user,
        "expiry_date":  expiry_date,
    }

    cap = max_doctors if max_doctors > 0 else None
    session = make_session()
    total_done = 0
    all_urls_count = 0

    add_log("🚀 Scraper started!", "ok")
    add_log(f"Cities: {', '.join(selected_cities)}", "info")
    add_log(f"Max pages/city: {max_pages} | Max doctors: {cap or 'unlimited'}", "info")
    render_log()

    # Collect all doctor URLs first
    all_tasks = []  # list of (url, city_slug)
    for city in selected_cities:
        city_url  = CITY_OPTIONS[city]
        city_slug = CITY_SLUG_MAP[city]
        add_log(f"📍 Collecting URLs for {city}…", "city")
        render_log()
        urls = get_doctor_urls(session, city_url, max_pages)
        add_log(f"   Found {len(urls)} doctors in {city}", "info")
        render_log()
        for u in urls:
            all_tasks.append((u, city_slug))
        if cap and len(all_tasks) >= cap:
            all_tasks = all_tasks[:cap]
            break
        time.sleep(delay)

    total_count = len(all_tasks)
    add_log(f"✅ Total doctors to scrape: {total_count}", "ok")
    render_log()

    progress_bar = prog_placeholder.progress(0)

    for i, (doc_url, city_slug) in enumerate(all_tasks):
        pct = int((i / total_count) * 100) if total_count else 100
        progress_bar.progress(pct)
        status_placeholder.markdown(
            f'<span class="badge badge-blue">Scraping {i+1} / {total_count}</span>',
            unsafe_allow_html=True,
        )

        add_log(f"[{i+1}/{total_count}] {doc_url.split('/')[-2]}", "info")
        render_log()

        row = parse_doctor(session, doc_url, city_slug, wp_config)
        time.sleep(delay)

        if row and row.get("Title"):
            st.session_state.scraped_rows.append(row)
            st.session_state.stats["success"] += 1
            add_log(f"   ✓ {row['Title']} | {row['Categories']} | {row.get('text_mp3lyhty','')[:35]}", "ok")
        else:
            st.session_state.stats["failed"] += 1
            add_log(f"   ✗ Failed: {doc_url}", "err")

        render_log()

    progress_bar.progress(100)
    status_placeholder.markdown(
        f'<span class="badge badge-green">✅ Done — {len(st.session_state.scraped_rows)} doctors scraped</span>',
        unsafe_allow_html=True,
    )
    add_log(f"🎉 Scraping complete! {len(st.session_state.scraped_rows)} doctors saved.", "ok")
    render_log()
    st.session_state.scraping = False
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
#  Results table preview
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.scraped_rows:
    st.markdown("---")
    st.markdown(f"### 📋 Scraped Doctors ({len(st.session_state.scraped_rows)} total)")

    # Summary stats
    from collections import Counter
    cats  = Counter(r.get("Categories","?") for r in st.session_state.scraped_rows)
    cities_c = Counter(r.get("Locations","?") for r in st.session_state.scraped_rows)

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**By Specialty**")
        for cat, cnt in cats.most_common(8):
            pct = int(cnt / len(st.session_state.scraped_rows) * 100)
            st.markdown(
                f'<span class="badge badge-blue">{cat}</span> &nbsp; {cnt} &nbsp; '
                f'<span style="color:#9ca3af">({pct}%)</span>',
                unsafe_allow_html=True,
            )
    with sc2:
        st.markdown("**By City**")
        for city, cnt in cities_c.most_common():
            st.markdown(
                f'<span class="badge badge-green">{city}</span> &nbsp; {cnt}',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.markdown("**Recent entries:**")
    show_rows = st.session_state.scraped_rows[-20:][::-1]
    for r in show_rows:
        name  = r.get("Title", "—")
        cat   = r.get("Categories","—")
        loc   = r.get("Locations","—")
        hours = r.get("text_mp3lyhty","")[:45] or "—"
        phone = r.get("Phone","") or "—"
        img_ok = "📷" if r.get("Images") else "  "
        ph_ok  = "📞" if r.get("Phone") else "  "
        st.markdown(f"""<div class="doc-row">
            <div class="doc-name">{img_ok} {ph_ok} &nbsp; {name}</div>
            <div class="doc-meta">
                <span class="badge badge-blue">{cat}</span> &nbsp;
                <span class="badge badge-green">{loc}</span> &nbsp;
                🕐 {hours} &nbsp; | &nbsp; {phone}
            </div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")
    # Field coverage
    total = len(st.session_state.scraped_rows)
    fc1, fc2, fc3, fc4, fc5 = st.columns(5)
    def cov(field):
        c = sum(1 for r in st.session_state.scraped_rows if r.get(field,"").strip())
        return f"{c}/{total}"
    fc1.metric("📞 Phone",    cov("Phone"))
    fc2.metric("🕐 Hours",    cov("text_mp3lyhty"))
    fc3.metric("📷 Photo",    cov("Images"))
    fc4.metric("🎓 Degrees",  cov("textarea_155974l42hu"))
    fc5.metric("🏥 Hospital", cov("text_mu65ovg87y"))
