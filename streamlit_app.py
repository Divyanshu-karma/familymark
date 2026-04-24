import streamlit as st
import re
import requests

# --- Page Configuration ---
st.set_page_config(
    page_title="FamilyMark Lookup",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed"
)



# --- Normalization (ported from enforcement_repository.py) ---
LEGAL_SUFFIX_TOKENS = {
    "inc", "incorporated", "corp", "corporation",
    "company", "co", "llc", "l.l.c", "ltd", "limited",
    "plc", "gmbh", "sa", "ag", "bv", "nv", "lp", "llp",
    "pte", "pty", "sarl", "spa", "s.p.a",
    "delaware", "california", "new", "york", "usa", "us",
    "state", "states", "united",
    "liability", "partner", "partners", "general",
    "trust", "trustee", "association", "associates",
    "holdco", "parent", "subsidiary"
}

NON_DISTINCTIVE_TOKENS = {
    "THE", "A", "AN", "AND", "OR", "OF", "FOR", "BY", "IN", "ON", "AT", "TO",
    "WITH", "FROM", "INC", "LLC", "LTD", "CO", "CORP", "COMPANY",
}

def normalize_owner_name(owner_name: str) -> str:
    if not owner_name:
        return ""
    base_name = re.split(r"[,(/\[]", owner_name)[0]
    normalized = re.sub(r"[^0-9A-Za-z\s-]", " ", base_name).lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return ""
    tokens = normalized.split(" ")
    while tokens and tokens[-1] in LEGAL_SUFFIX_TOKENS:
        tokens.pop()
    return " ".join(tokens) if tokens else normalized

def normalize_owner_name_with_suffix(owner_name: str) -> str:
    if not owner_name:
        return ""
    base_name = re.split(r"[,(/\[]", owner_name)[0]
    normalized = re.sub(r"[^0-9A-Za-z\s-]", " ", base_name).lower()
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized if normalized else ""

# --- Parsers & Helpers ---
def parse_family_mark(family_mark_str: str) -> list:
    if not family_mark_str:
        return []
    parts = family_mark_str.split(" || ")
    results = []
    for part in parts:
        part = part.strip()
        match = re.match(r'^(.+?)\s*\{(\d+)\}$', part)
        if match:
            results.append((match.group(1).strip(), int(match.group(2))))
        elif part:
            results.append((part, 0))
    return results

def generate_fallback_slices(np_words):
    n = len(np_words)
    slices = []
    if n >= 5:
        slices = [" ".join(np_words[:2]), " ".join(np_words[:3]),
                  " ".join(np_words[-2:]), " ".join(np_words[-3:])]
    elif n == 4:
        slices = [" ".join(np_words[:2]), " ".join(np_words[:3]),
                  " ".join(np_words[-2:])]
    elif n == 3:
        slices = [" ".join(np_words[:2]), " ".join(np_words[-2:])]
    elif n == 2:
        slices = [" ".join(np_words[:2])]
    seen = set()
    return [s for s in slices if s not in seen and not seen.add(s)]

def build_result(petitioner_norm, family_mark_raw, applicant_mark):
    if not family_mark_raw:
        return {"petitioner_norm": petitioner_norm, "family_exists": False,
                "dominant_terms": [], "family_strength": "weak", "mark_count": 0,
                "applicant_mark_overlap": []}

    parsed = parse_family_mark(family_mark_raw)
    dominant_terms = [t[0] for t in parsed]
    freq_map = {t[0].upper(): t[1] for t in parsed}

    raw_tokens = set(re.findall(r'\b[A-Z0-9]+\b', applicant_mark.upper()))
    app_tokens = raw_tokens - NON_DISTINCTIVE_TOKENS
    overlap = list(app_tokens & set(t.upper() for t in dominant_terms))

    mark_count = max((freq_map.get(t, 0) for t in overlap), default=0)
    strength = "strong" if mark_count >= 10 else "moderate" if mark_count >= 3 else "weak"

    return {"petitioner_norm": petitioner_norm, "family_exists": True,
            "dominant_terms": dominant_terms, "family_strength": strength,
            "mark_count": mark_count, "applicant_mark_overlap": overlap}
API_URL = st.secrets["API_URL"]

def lookup_single(petitioner_name, applicant_mark):
    try:
        response = requests.post(
            API_URL,
            json={
                "petitioner_name": petitioner_name,
                "applicant_mark": applicant_mark
            },
            timeout=10
        )
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return []

# --- Custom CSS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    .stApp { background-color: #0B0E14; color: #E6EDF3; font-family: 'Inter', sans-serif; }
    .stTabs [data-baseweb="tab-list"] { gap: 0; border-bottom: 2px solid #30363D; }
    .stTabs [data-baseweb="tab"] { color: #8B949E; font-weight: 600; padding: 0.8rem 1.5rem; }
    .stTabs [aria-selected="true"] { color: #58A6FF !important; border-bottom: 2px solid #58A6FF; }
    .metric-card { background: #161B22; border: 1px solid #30363D; border-radius: 12px; padding: 1.2rem; }
    .badge-strong { background: rgba(35,134,54,0.3); color: #56D364; padding: 4px 12px; border-radius: 999px; font-weight:700; font-size:0.8rem; }
    .badge-moderate { background: rgba(240,136,62,0.3); color: #F0883E; padding: 4px 12px; border-radius: 999px; font-weight:700; font-size:0.8rem; }
    .badge-weak { background: rgba(248,81,73,0.2); color: #F85149; padding: 4px 12px; border-radius: 999px; font-weight:700; font-size:0.8rem; }
    .badge-notfound { background: rgba(139,148,158,0.2); color: #8B949E; padding: 4px 12px; border-radius: 999px; font-weight:700; font-size:0.8rem; }
    .dom-tag { background: rgba(188,140,242,0.15); color: #D2A8FF; padding: 2px 8px; border-radius: 4px; font-size:0.85rem; margin: 2px; display:inline-block; }
    .overlap-tag { background: rgba(88,166,255,0.2); color: #58A6FF; padding: 2px 8px; border-radius: 4px; font-size:0.85rem; margin: 2px; display:inline-block; }
    h1 { background: linear-gradient(90deg, #58A6FF, #BC8CF2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    div[data-testid="stTextInput"] input { background: #0D1117 !important; border: 1px solid #30363D !important; color: #E6EDF3 !important; }
</style>
""", unsafe_allow_html=True)

# --- Header ---
st.markdown("<h1 style='text-align:center; font-size:2.5rem;'>FamilyMark Explorer</h1>", unsafe_allow_html=True)

# --- Tabs ---
tab1, tab2 = st.tabs(["🔍 Single Lookup", "📦 Batch Lookup"])

# ==================== TAB 1: SINGLE LOOKUP ====================
with tab1:
    col1, col2 = st.columns(2)
    with col1:
        pet_name = st.text_input("Petitioner Name", placeholder="e.g. Apple Corps Limited, Nike Inc...", key="single_pet")
    with col2:
        app_mark = st.text_input("Applicant Mark", placeholder="e.g. APPLE MUSIC, SWOOSH...", key="single_mark")

    if st.button("⚡ Analyze Family Mark", type="primary", use_container_width=True):
        if not pet_name:
            st.warning("Please enter a Petitioner Name.")
        else:
            with st.spinner("Analyzing..."):
                results = lookup_single(pet_name, app_mark or "")

            if not results:
                st.info("No results returned.")
            else:
                for r in results:
                    with st.container():
                        st.markdown(f"<div class='metric-card'>", unsafe_allow_html=True)
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"### `{r['petitioner_norm']}`")
                        with c2:
                            if not r['family_exists']:
                                st.markdown("<span class='badge-notfound'>NOT FOUND</span>", unsafe_allow_html=True)
                            elif r['family_strength'] == 'strong':
                                st.markdown("<span class='badge-strong'>STRONG</span>", unsafe_allow_html=True)
                            elif r['family_strength'] == 'moderate':
                                st.markdown("<span class='badge-moderate'>MODERATE</span>", unsafe_allow_html=True)
                            else:
                                st.markdown("<span class='badge-weak'>WEAK</span>", unsafe_allow_html=True)

                        if r['family_exists']:
                            m1, m2, m3 = st.columns(3)
                            with m1:
                                st.markdown("**Dominant Terms**")
                                tags = "".join(f"<span class='dom-tag'>{t}</span>" for t in r['dominant_terms'])
                                st.markdown(tags, unsafe_allow_html=True)
                            with m2:
                                st.metric("Mark Count", r['mark_count'])
                            with m3:
                                st.markdown("**Applicant Mark Overlap**")
                                if r['applicant_mark_overlap']:
                                    otags = "".join(f"<span class='overlap-tag'>{t}</span>" for t in r['applicant_mark_overlap'])
                                    st.markdown(otags, unsafe_allow_html=True)
                                else:
                                    st.caption("None")
                        else:
                            st.caption("No family mark data found for this petitioner norm.")
                        st.markdown("</div>", unsafe_allow_html=True)
                        st.markdown("---")

# ==================== TAB 2: BATCH LOOKUP ====================
with tab2:
    st.markdown("**Paste JSON array of lookups** (max 50):")
    batch_json = st.text_area(
        "Batch Input",
        height=200,
        placeholder='[\n  {"id": "ref-001", "petitioner_name": "Apple Corps Limited", "applicant_mark": "APPLE MUSIC"},\n  {"id": "ref-002", "petitioner_name": "Nike Inc", "applicant_mark": "SWOOSH"}\n]',
        label_visibility="collapsed"
    )

    if st.button("🚀 Run Batch Lookup", type="primary", use_container_width=True):
        import json
        try:
            lookups = json.loads(batch_json)
            if not isinstance(lookups, list):
                st.error("Input must be a JSON array.")
            elif len(lookups) > 50:
                st.error("Batch cap exceeded: maximum 50 lookups.")
            elif not lookups:
                st.error("Lookups array must not be empty.")
            else:
                with st.spinner(f"Processing {len(lookups)} lookups..."):
                    batch_results = []
                    for item in lookups:
                        item_id = item.get("id", "")
                        pet = item.get("petitioner_name", "")
                        mark = item.get("applicant_mark", "")
                        try:
                            res_list = lookup_single(pet, mark)
                            found = [r for r in res_list if r["family_exists"]]
                            best = max(found, key=lambda r: r["mark_count"]) if found else (res_list[0] if res_list else {
                                "petitioner_norm": "", "family_exists": False, "dominant_terms": [],
                                "family_strength": "weak", "mark_count": 0, "applicant_mark_overlap": []
                            })
                            best["id"] = item_id
                            batch_results.append(best)
                        except Exception:
                            batch_results.append({"id": item_id, "petitioner_norm": pet,
                                "family_exists": False, "dominant_terms": [], "family_strength": "weak",
                                "mark_count": 0, "applicant_mark_overlap": []})

                st.success(f"Completed {len(batch_results)} lookups.")
                st.json({"results": batch_results})
        except json.JSONDecodeError as e:
            st.error(f"Invalid JSON: {e}")
