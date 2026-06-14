"""
Doctor Bangladesh Scraper — Calibrated to your CSV Structure
"""

import csv
import io
import re
import time
import concurrent.futures
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import streamlit as st

# ── Configuration Constants (Matched to your CSV) ──────────────────────────────
CSV_COLUMNS = [
    'Title', 'Content', 'Excerpt', 'Ad Type', 'Categories', 'Locations', 'Tags', 
    'Images', 'Video URL', 'Post Date', 'Post Author ID', 'Author First name', 
    'Author Last name', 'Author Email', 'Author Username', 'Pricing Type', 
    'Price Type', 'Price', 'Max Price', 'Social Profiles', 'Website', 'Email', 
    'Phone', 'WhatsApp', 'Address', 'Zip Code', 'Map Latitude', 'Map Longitude', 
    'Hide Map', 'Never Expire', 'Expiry Date', 'Views', 'Business Hours', 'Status', 
    'radio_axdl9k6wlb', 'text_j456myldo8', 'text_mu65ovg87y', 'text_we3ui010yl', 
    'text_10vmr6dbji6', 'textarea_155974l42hu', 'text_1wiw01ojiux', 
    'text_2031eyb4gd7', 'text_mp3lyhty'
]

# Mapping dictionary for Categories - ensure these slugs exist in your WP taxonomy
SPECIALTY_MAP = {
    "ent": "ent", "ear nose throat": "ent", "otolaryngologist": "ent",
    "cardiologist": "cardiology", "cardiology": "cardiology",
    "medicine": "medicine", "internal medicine": "medicine",
    "dermatologist": "dermatology", "dermatology": "dermatology",
    "orthopedic": "orthopedics", "gynecologist": "gynecology",
    "gynecology": "gynecology", "pediatrician": "pediatrics",
    "neurology": "neurology", "neurologist": "neurology",
    "gastro": "gastroenterology", "urology": "urology",
    "eye": "ophthalmology", "ophthalmology": "ophthalmology",
    "psychiatry": "psychiatry", "diabetes": "endocrinology",
    "kidney": "nephrology", "nephrology": "nephrology",
    "liver": "hepatology", "pulmonology": "pulmonology",
    "dentist": "dentistry", "surgeon": "surgery",
    "physiotherapy": "physiotherapy"
}

# ── Scraping Helpers ──────────────────────────────────────────────────────────
def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"})
    return s

def fetch(session, url):
    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except: return None

def parse_doctor(session, url, city_slug, wp_config):
    s = fetch(session, url)
    if not s: return None

    row = {col: "" for col in CSV_COLUMNS}
    
    # --- Default Static Setup ---
    row.update({
        "Post Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Post Author ID": wp_config["author_id"],
        "Author Email": wp_config["author_email"],
        "Author Username": wp_config["author_username"],
        "Pricing Type": "price",
        "Price Type": "regular",
        "Never Expire": "1",
        "Expiry Date": wp_config["expiry_date"],
        "Status": "publish",
        "Locations": city_slug,
    })

    # 1. Title
    h1 = s.find("h1")
    name = h1.get_text().strip() if h1 else "Unknown Doctor"
    row["Title"] = name

    # 2. Extract Data using Label Mapping
    # We look for all list items and try to match labels
    profile_text = s.get_text(separator='|', strip=True)
    
    # Helper to find text after a label
    def extract_field(label):
        pattern = rf"{label}\s*[:\-]?\s*([^|]+)"
        match = re.search(pattern, profile_text, re.IGNORECASE)
        return match.group(1).strip() if match else ""

    # Mapping website structure to your CSV custom fields
    row["text_j456myldo8"] = extract_field("Designation") or extract_field("Designation:") # Designation
    row["text_mu65ovg87y"] = extract_field("Hospital") or extract_field("Institute") # Hospital
    row["text_1wiw01ojiux"] = extract_field("Department") # Department
    row["textarea_155974l42hu"] = extract_field("Qualifications") or extract_field("Degree") # Qualifications
    row["text_10vmr6dbji6"] = extract_field("BMDC") # BMDC
    
    # 3. Chamber Data
    row["text_2031eyb4gd7"] = extract_field("Chamber") or extract_field("Clinic") # Chamber Name
    row["text_we3ui010yl"] = extract_field("Address") # Chamber Address
    row["text_mp3lyhty"] = extract_field("Visiting Hours") # Visiting Hours
    
    # 4. Phone Extraction
    phone_match = re.search(r"(\+880\d{9,10}|01\d{9})", profile_text)
    row["Phone"] = phone_match.group(1) if phone_match else ""

    # 5. Content & Excerpt
    article = s.find("article")
    row["Content"] = str(article) if article else f"<p>{name}</p>"
    row["Excerpt"] = f"{name} - {row['text_j456myldo8']}"

    # 6. Categories (Logic)
    spec_text = (row["text_1wiw01ojiux"] + " " + row["Title"]).lower()
    for k, slug in SPECIALTY_MAP.items():
        if k in spec_text:
            row["Categories"] = slug
            break
    
    # 7. Gender
    row["radio_axdl9k6wlb"] = "female" if any(x in name.lower() for x in ["dr. ms.", "mrs", "dr. mrs"]) else "male"

    return row
# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Doctor BD Scraper Pro",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS styling ────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Main background */
  .stApp { background: #f8fafc; }

  /* Sidebar styling */
  [data-testid="stSidebar"] {
    background: #0f172a;
    color: #f1f5f9;
  }
  [data-testid="stSidebar"] label,
  [data-testid="stSidebar"] .stMarkdown p,
  [data-testid="stSidebar"] h1,
  [data-testid="stSidebar"] h2,
  [data-testid="stSidebar"] h3 {
    color: #f1f5f9 !important;
  }
  [data-testid="stSidebar"] .stCheckbox label { color: #cbd5e1 !important; }

  /* KPI Summary Cards */
  .metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.05);
    border-left: 5px solid #3b82f6;
    margin-bottom: 12px;
  }
  .metric-card .number { font-size: 2.2rem; font-weight: 700; color: #1e293b; }
  .metric-card .label  { font-size: 0.85rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 99px;
    font-size: 0.75rem;
    font-weight: 600;
  }
  .badge-green  { background: #dcfce7; color: #166534; }
  .badge-yellow { background: #fef9c3; color: #854d0e; }
  .badge-red    { background: #fee2e2; color: #991b1b; }
  .badge-blue   { background: #dbeafe; color: #1e40af; }

  /* Doctor Row Item */
  .doc-row {
    background: white;
    border-radius: 8px;
    padding: 14px 18px;
    margin: 8px 0;
    box-shadow: 0 1px 3px rgb(0 0 0 / 0.05);
    border-left: 4px solid #3b82f6;
    font-size: 0.9rem;
  }
  .doc-name  { font-weight: 700; color: #1e293b; font-size: 1rem; }
  .doc-meta  { color: #64748b; margin-top: 4px; }

  /* Interactive Terminal Logs */
  .log-box {
    background: #020617;
    color: #38bdf8;
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    padding: 16px;
    border-radius: 8px;
    height: 280px;
    overflow-y: auto;
    line-height: 1.6;
    border: 1px solid #334155;
  }
</style>
""", unsafe_allow_html=True)

# ── Configuration Constants ───────────────────────────────────────────────────
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

# ── Scraping Helpers ──────────────────────────────────────────────────────────
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
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1.5)
    return None

def clean(text):
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())

def guess_gender(name, extra=""):
    low = (name + " " + extra).lower()
    if any(h in low for h in ["female", "mrs.", " ms.", "gynecol", "obstet", "কানিজ", "ডাক্তার"]):
        return "female"
    return "male"

def guess_category(text):
    low = text.lower()
    for kw, slug in SPECIALTY_MAP.items():
        if kw in low:
            return slug
    words = re.findall(r"[a-z]+", low)
    return words[0] if words else "general"

# ── 3-Tier Parsing Mechanics ──────────────────────────────────────────────────
def get_specialty_urls(session, city_url, city_slug, keywords_filter):
    s = fetch(session, city_url)
    if not s:
        return []
    
    urls = []
    for a in s.find_all("a", href=True):
        href = a["href"].strip()
        if f"-{city_slug}" in href.lower() and not any(x in href.lower() for x in ["/doctors-", "/dr-", "/page/"]):
            # Keyword filter check
            if keywords_filter:
                if not any(k.strip().lower() in href.lower() for k in keywords_filter if k.strip()):
                    continue
            if href not in urls:
                urls.append(href)
    return urls

def get_doctor_urls_from_specialty(session, specialty_url, max_pages):
    urls = []
    base = specialty_url.rstrip("/")
    for page in range(1, (max_pages or 999) + 1):
        purl = base + "/" if page == 1 else f"{base}/page/{page}/"
        s = fetch(session, purl)
        if not s:
            break
        links = s.find_all("a", href=re.compile(r"/dr-[-\w]+/?$"))
        new = list({a["href"] for a in links if a.get("href")})
        if not new:
            break
        for u in new:
            if u not in urls:
                urls.append(u)
        nxt = s.find("a", class_=re.compile(r"next"), string=re.compile(r"next|›|»", re.I))
        if not nxt:
            break
    return urls

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

    # Title Name
    h1 = s.find("h1")
    name = clean(h1.get_text()) if h1 else ""
    row["Title"] = name

    # Image
    img = s.find("img", alt=re.compile(re.escape(name[:6]), re.I)) if name else None
    if img and img.get("src"):
        row["Images"] = img["src"]

    # Meta bullet listings
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
        elif any(k in low for k in ["consultant", "professor", "registrar", "associate", "fellow"]):
            designation = b
        elif any(k in low for k in ["hospital", "medical college", "institute", "cmh", "bsmmu"]):
            hospital = b
        elif any(k in low for k in ["specialist", "surgeon", "physician", "therapist"]):
            specialty = b

    # BMDC Reg number
    page_text = s.get_text(" ", strip=True)
    bm = re.search(r"BMDC\s*Reg(?:istration)?\s*(?:No|#|:)?\s*[:\-]?\s*([A-Z0-9\-]+)", page_text, re.I)
    if bm:
        row["text_10vmr6dbji6"] = bm.group(1).strip()

    # Chambers layout extraction
    ch = s.find(lambda t: t.name in ("h2","h3","h4","strong","b") and re.search(r"chamber|appointment", t.get_text(), re.I))
    clinic = addr = hours = phone = ""
    if ch:
        container = ch.find_parent(["div","section","article"]) or ch
        bt = clean(container.get_text(" "))
        bold = ch.find_next(["strong","b","a"])
        if bold:
            clinic = clean(bold.get_text())
        am = re.search(r"[Aa]ddress\s*:\s*(.+?)(?:Visiting|Phone|Appointment|$)", bt)
        if am: addr = clean(am.group(1))
        vm = re.search(r"[Vv]isiting\s*[Hh]our[s]?\s*:\s*(.+?)(?:Phone|Appointment|Call|$)", bt)
        if vm: hours = clean(vm.group(1))
        pm = re.search(r"(?:Appointment|Phone|Call)\s*:\s*(\+?[\d\s\-\(\)]+)", bt)
        if pm: phone = clean(pm.group(1))

    if not phone:
        pm = re.search(r"(\+880[\d\s\-]{8,}|01[3-9]\d{8})", page_text)
        if pm: phone = clean(pm.group(1))
        
    # Phone number cleaning to remove letters
    if phone:
        phone = re.sub(r"[A-Za-z]+", "", phone).strip()

    # Bio text blocks
    ah = s.find(lambda t: t.name in ("h2","h3","h4") and re.search(r"about", t.get_text(), re.I))
    bio = ""
    if ah:
        parts = []
        for sib in ah.find_next_siblings():
            if sib.name in ("h2","h3","h4"): break
            parts.append(str(sib))
        bio = "".join(parts)
    if not bio:
        bio = f"<p><strong>{name}</strong>"
        if degrees:   bio += f" holds {degrees}."
        if specialty: bio += f" Specialist in {specialty}."
        if hospital:  bio += f" Based at {hospital}."
        bio += "</p>"

    excerpt = re.sub(r"<[^>]+>", " ", bio)
    excerpt = re.sub(r"\s+", " ", excerpt).strip()[:280]

    dept_m = re.search(r"dept(?:artment)?\s+of\s+([A-Za-z &\-]+)", page_text, re.I)
    dept = clean(dept_m.group(1)) if dept_m else (specialty or "General")

    lat, lng = CITY_COORDS.get(city_slug, ("", ""))

    row.update({
        "Content": bio, "Excerpt": excerpt,
        "Categories": guess_category(specialty or designation or dept),
        "Phone": phone, "Address": addr,
        "Map Latitude": str(lat), "Map Longitude": str(lng),
        "radio_axdl9k6wlb": guess_gender(name, degrees + specialty),
        "text_j456myldo8": designation or "Consultant",
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

# ── Session State Initializers ────────────────────────────────────────────────
if "scraped_rows" not in st.session_state:
    st.session_state.scraped_rows = []
if "scraping" not in st.session_state:
    st.session_state.scraping = False
if "log_lines" not in st.session_state:
    st.session_state.log_lines = []
if "stats" not in st.session_state:
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}

# ── Sidebar View — Settings Panel ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🩺 Scraper Control Unit")
    st.markdown("---")

    st.markdown("### 🌆 Select Target Cities")
    selected_cities = []
    col_a, col_b = st.columns(2)
    city_list = list(CITY_OPTIONS.keys())
    for i, city in enumerate(city_list):
        col = col_a if i % 2 == 0 else col_b
        if col.checkbox(city, value=(city == "Dhaka"), key=f"city_{city}"):
            selected_cities.append(city)

    st.markdown("---")
    st.markdown("### 🔍 Specialty Filter")
    spec_filter_input = st.text_input("Filter Keyword (e.g. ent, cardiology)", value="", help="Leave blank to grab ALL departments")
    keywords_filter = [k.strip() for k in spec_filter_input.split(",") if k.strip()]

    st.markdown("---")
    st.markdown("### ⚙️ Crawler Strategy")
    max_pages   = st.number_input("Max pages per Specialty", min_value=1, max_value=50, value=2)
    max_doctors = st.number_input("Cap total profiles (0 = unlimited)", min_value=0, value=50)

    st.markdown("---")
    st.markdown("### 🔧 WordPress Mapping Defaults")
    author_id    = st.text_input("Post Author ID", value="1")
    author_email = st.text_input("Author Email", value="admin@yoursite.com")
    author_user  = st.text_input("Author Username", value="admin")
    expiry_date  = st.text_input("Expiry Date", value="2029-01-01 00:00:00")

# ── Main Dashboard Layout ─────────────────────────────────────────────────────
st.markdown("# 🩺 Live Doctor Bangladesh Scraper Engine")
st.markdown("Extract deep profiles and compile import-ready data mapping flawlessly to Classified Listing (RTCL) plugins.")
st.markdown("---")

# KPI Summary Status Row
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.markdown(f'<div class="metric-card"><div class="number">{len(st.session_state.scraped_rows)}</div><div class="label">Total Collected</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card" style="border-color:#10b981"><div class="number">{st.session_state.stats["success"]}</div><div class="label">Success Rows</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card" style="border-color:#ef4444"><div class="number">{st.session_state.stats["failed"]}</div><div class="label">Faulty Rows</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card" style="border-color:#f59e0b"><div class="number">{len(selected_cities)}</div><div class="label">Cities Active</div></div>', unsafe_allow_html=True)

st.markdown("---")

# Dashboard Action Control Matrix
btn_col1, btn_col2, btn_col3 = st.columns([2, 2, 3])
with btn_col1:
    start_btn = st.button("▶ Start Scraping Process", disabled=st.session_state.scraping or not selected_cities, use_container_width=True, type="primary")
with btn_col2:
    clear_btn = st.button("🗑 Reset Memory Cache", disabled=st.session_state.scraping, use_container_width=True)
with btn_col3:
    if st.session_state.scraped_rows:
        csv_bytes = rows_to_csv(st.session_state.scraped_rows)
        fname = f"doctorbangladesh_import_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
        st.download_button(label=f"⬇ Download Import CSV ({len(st.session_state.scraped_rows)} Rows)", data=csv_bytes, file_name=fname, mime="text/csv", use_container_width=True)
    else:
        st.button("⬇ No Data Available to Export", disabled=True, use_container_width=True)

if clear_btn:
    st.session_state.scraped_rows = []
    st.session_state.log_lines = []
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}
    st.rerun()

# Dynamic Status Components
log_placeholder = st.empty()
prog_placeholder = st.empty()
status_placeholder = st.empty()

def render_log():
    lines = st.session_state.log_lines[-20:]
    html = "<br>".join(lines)
    log_placeholder.markdown(f'<div class="log-box">{html}</div>', unsafe_allow_html=True)

def add_log(msg, kind="info"):
    colors = {"info": "#38bdf8", "ok": "#4ade80", "err": "#f87171", "city": "#a78bfa", "warn": "#fbbf24"}
    color = colors.get(kind, "#38bdf8")
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.log_lines.append(f'<span style="color:#475569">[{ts}]</span> <span style="color:{color}">{msg}</span>')

render_log()

# ── Core Operation Logic Pipeline ─────────────────────────────────────────────
if start_btn and selected_cities and not st.session_state.scraping:
    st.session_state.scraping = True
    st.session_state.scraped_rows = []
    st.session_state.log_lines = []
    st.session_state.stats = {"total": 0, "success": 0, "failed": 0, "cities_done": 0}

    wp_config = {
        "author_id": author_id, "author_email": author_email,
        "author_username": author_user, "expiry_date": expiry_date,
    }

    session = make_session()
    all_tasks = [] # List containing elements formatted as (doctor_profile_url, city_slug)
    scraped_urls_tracker = set()

    add_log("🚀 Initiating Crawling Engine...", "ok")
    render_log()

    # Step 1 & 2: Discover Specialty Sections & Identify Profile Links
    for city in selected_cities:
        city_url = CITY_OPTIONS[city]
        city_slug = CITY_SLUG_MAP[city]
        
        add_log(f"📍 Inspecting City: {city} index map...", "city")
        render_log()
        
        spec_urls = get_specialty_urls(session, city_url, city_slug, keywords_filter)
        add_log(f"   Found {len(spec_urls)} matching specialty sub-departments", "info")
        render_log()
        
        for idx, s_url in enumerate(spec_urls):
            add_log(f"   ({idx+1}/{len(spec_urls)}) Indexing doctor cards inside: {s_url.split('/')[-2]}", "info")
            render_log()
            doc_urls = get_doctor_urls_from_specialty(session, s_url, max_pages)
            
            for d_url in doc_urls:
                if d_url not in scraped_urls_tracker:
                    scraped_urls_tracker.add(d_url)
                    all_tasks.append((d_url, city_slug))
            
            if max_doctors > 0 and len(all_tasks) >= max_doctors:
                all_tasks = all_tasks[:max_doctors]
                break
        if max_doctors > 0 and len(all_tasks) >= max_doctors:
            break

    total_count = len(all_tasks)
    add_log(f"📊 Identification Stage Complete. Total Unique Profiles Found: {total_count}", "ok")
    render_log()

    # Step 3: Threaded Batch Execution Framework (Processing batches of 5)
    progress_bar = prog_placeholder.progress(0)
    batch_size = 5
    
    for i in range(0, total_count, batch_size):
        batch = all_tasks[i : i + batch_size]
        pct = int((i / total_count) * 100) if total_count else 100
        progress_bar.progress(pct)
        
        status_placeholder.markdown(f'<span class="badge badge-blue">Processing Batch entries {i+1} to {min(i+batch_size, total_count)} of {total_count}</span>', unsafe_allow_html=True)
        
        # Concurrent Multi-threaded parsing within current batch window
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(batch)) as executor:
            future_to_url = {executor.submit(parse_doctor, session, task[0], task[1], wp_config): task for task in batch}
            
            for future in concurrent.futures.as_completed(future_to_url):
                task_url, city_slug = future_to_url[future]
                try:
                    row = future.result()
                    if row and row.get("Title"):
                        st.session_state.scraped_rows.append(row)
                        st.session_state.stats["success"] += 1
                        add_log(f"   ✓ Extracted: {row['Title']} [{row['Categories']}]", "ok")
                    else:
                        st.session_state.stats["failed"] += 1
                        add_log(f"   ✗ Missing info structural profile: {task_url}", "err")
                except Exception as e:
                    st.session_state.stats["failed"] += 1
                    add_log(f"   ✗ Fatal Error parsing profile structural node: {str(e)}", "err")
        
        render_log()
        time.sleep(0.5) # Guard rail buffer time between concurrent window steps

    progress_bar.progress(100)
    status_placeholder.markdown(f'<span class="badge badge-green">✅ Completed — {len(st.session_state.scraped_rows)} Rows Extracted Successfully!</span>', unsafe_allow_html=True)
    add_log("🎉 Process terminated normally. Click the blue export button to acquire your file.", "ok")
    render_log()
    st.session_state.scraping = False
    st.rerun()

# ── Preview Analytics Interface ───────────────────────────────────────────────
if st.session_state.scraped_rows:
    st.markdown("---")
    st.markdown(f"### 📋 Real-Time Distribution Preview ({len(st.session_state.scraped_rows)} Total)")

    from collections import Counter
    cats = Counter(r.get("Categories","?") for r in st.session_state.scraped_rows)
    cities_c = Counter(r.get("Locations","?") for r in st.session_state.scraped_rows)

    sc1, sc2 = st.columns(2)
    with sc1:
        st.markdown("**Category Slugs Assigned**")
        for cat, cnt in cats.most_common(6):
            st.markdown(f'<span class="badge badge-blue">{cat}</span> &nbsp; <b>{cnt}</b> profiles', unsafe_allow_html=True)
    with sc2:
        st.markdown("**Location Spread**")
        for city, cnt in cities_c.most_common(6):
            st.markdown(f'<span class="badge badge-green">{city}</span> &nbsp; <b>{cnt}</b> listings', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**Recent Live Data Blocks Added:**")
    for r in st.session_state.scraped_rows[-10:][::-1]:
        st.markdown(f"""
        <div class="doc-row">
            <div class="doc-name">📋 {r.get('Title', '—')}</div>
            <div class="doc-meta">
                <span class="badge badge-blue">{r.get('Categories','—')}</span> &nbsp;
                <span class="badge badge-green">{r.get('Locations','—')}</span> &nbsp;&nbsp;|&nbsp;&nbsp;
                🏥 {r.get('text_2031eyb4gd7','—')} &nbsp;&nbsp;|&nbsp;&nbsp;
                📞 {r.get('Phone','—')}
            </div>
        </div>
        """, unsafe_allow_html=True)
