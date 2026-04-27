import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
import time

load_dotenv()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ArXiv Lens",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* Root theme */
:root {
    --bg: #0a0a0f;
    --surface: #13131a;
    --surface2: #1c1c28;
    --border: #2a2a3d;
    --accent: #7c6af7;
    --accent2: #f7c948;
    --text: #e8e8f0;
    --muted: #6b6b8a;
    --success: #3ecf8e;
    --danger: #f56565;
}

/* Global */
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}

.stApp {
    background-color: var(--bg) !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header { visibility: hidden; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* Header */
.app-header {
    padding: 2rem 0 1.5rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 2rem;
}
.app-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.4rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -1px;
    margin: 0;
}
.app-title span { color: var(--accent); }
.app-subtitle {
    font-size: 0.95rem;
    color: var(--muted);
    margin-top: 0.4rem;
    font-weight: 300;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: var(--surface) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    border: 1px solid var(--border) !important;
    gap: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    background: transparent !important;
    border-radius: 7px !important;
    color: var(--muted) !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important;
    padding: 0.5rem 1.2rem !important;
    border: none !important;
}
.stTabs [aria-selected="true"] {
    background: var(--accent) !important;
    color: white !important;
}

/* Buttons */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.4rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #6a5ae0 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(124, 106, 247, 0.4) !important;
}

/* Category pills */
.cat-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
    font-family: 'Space Mono', monospace;
    letter-spacing: 0.5px;
    margin-right: 6px;
}
.cat-cs-ai  { background: rgba(124,106,247,0.2); color: #a89af9; border: 1px solid rgba(124,106,247,0.3); }
.cat-cs-cv  { background: rgba(247,201,72,0.15); color: #f7c948; border: 1px solid rgba(247,201,72,0.3); }
.cat-cs-cl  { background: rgba(62,207,142,0.15); color: #3ecf8e; border: 1px solid rgba(62,207,142,0.3); }
.cat-cs-lg  { background: rgba(245,101,101,0.15); color: #f56565; border: 1px solid rgba(245,101,101,0.3); }
.cat-cs-se  { background: rgba(99,179,237,0.15); color: #63b3ed; border: 1px solid rgba(99,179,237,0.3); }

/* Paper card */
.paper-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.2rem;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
    position: relative;
    overflow: hidden;
}
.paper-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0;
    width: 3px; height: 100%;
    background: var(--accent);
    border-radius: 14px 0 0 14px;
}
.paper-card:hover {
    border-color: var(--accent);
    box-shadow: 0 4px 30px rgba(124, 106, 247, 0.12);
}
.paper-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--text);
    margin: 0.4rem 0 0.8rem 0;
    line-height: 1.4;
}
.paper-meta {
    font-size: 0.8rem;
    color: var(--muted);
    margin-bottom: 1rem;
    font-family: 'Space Mono', monospace;
}
.paper-summary {
    font-size: 0.92rem;
    color: #c8c8e0;
    line-height: 1.75;
    border-top: 1px solid var(--border);
    padding-top: 1rem;
    margin-top: 0.5rem;
}
.paper-link {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 1rem;
    font-size: 0.82rem;
    color: var(--accent);
    text-decoration: none;
    font-weight: 500;
    font-family: 'Space Mono', monospace;
}

/* Stats bar */
.stats-bar {
    display: flex;
    gap: 1.5rem;
    padding: 1rem 1.4rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 10px;
    margin-bottom: 1.5rem;
}
.stat-item { text-align: center; }
.stat-num {
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--accent);
}
.stat-label { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }

/* Multiselect */
[data-testid="stMultiSelect"] > div {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    border-radius: 8px !important;
}

/* Search box */
[data-testid="stTextInput"] > div > div > input {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    color: var(--text) !important;
    border-radius: 8px !important;
}

/* Select box */
[data-testid="stSelectbox"] > div {
    background: var(--surface2) !important;
    border-color: var(--border) !important;
    border-radius: 8px !important;
}

/* Progress / spinner */
.stProgress > div > div > div > div {
    background: var(--accent) !important;
}

/* Info/warning/success boxes */
.stAlert {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
}

/* Divider */
hr { border-color: var(--border) !important; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CATEGORIES = {
    "cs.AI — Artificial Intelligence": "cs.AI",
    "cs.CV — Computer Vision": "cs.CV",
    "cs.CL — Computation & Language (NLP)": "cs.CL",
    "cs.LG — Machine Learning": "cs.LG",
    "cs.SE — Software Engineering": "cs.SE",
}

CAT_CSS = {
    "cs.AI": "cat-cs-ai",
    "cs.CV": "cat-cs-cv",
    "cs.CL": "cat-cs-cl",
    "cs.LG": "cat-cs-lg",
    "cs.SE": "cat-cs-se",
}

# ── Clients ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        st.error("⚠️ SUPABASE_URL and SUPABASE_KEY must be set in your .env file.")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY must be set in your .env file.")
        st.stop()
    return Groq(api_key=api_key)

# ── Scraper ───────────────────────────────────────────────────────────────────
def scrape_arxiv(category: str) -> list[dict]:
    """Scrape latest papers from arXiv for a given CS category."""
    url = f"https://arxiv.org/list/{category}/recent"
    headers = {"User-Agent": "Mozilla/5.0 (ArXivLens research tool)"}
    
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        st.error(f"Failed to fetch arXiv page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    papers = []

    # arXiv list page structure
    dl = soup.find("dl")
    if not dl:
        return []

    dts = dl.find_all("dt")
    dds = dl.find_all("dd")

    for dt, dd in zip(dts, dds):
        try:
            # Paper ID and link
            link_tag = dt.find("a", title="Abstract")
            if not link_tag:
                continue
            arxiv_id = link_tag.text.strip().replace("arXiv:", "")
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"

            # Title
            title_tag = dd.find("div", class_="list-title")
            title = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown Title"

            # Authors
            authors_tag = dd.find("div", class_="list-authors")
            authors = authors_tag.text.replace("Authors:", "").strip() if authors_tag else ""

            # Abstract — fetch from abstract page for full text
            papers.append({
                "arxiv_id": arxiv_id,
                "arxiv_url": arxiv_url,
                "title": title,
                "authors": authors[:400],  # trim very long author lists
                "category": category,
            })
        except Exception:
            continue

    return papers


def fetch_abstract(arxiv_url: str) -> str:
    """Fetch the full abstract from an arXiv abstract page."""
    headers = {"User-Agent": "Mozilla/5.0 (ArXivLens research tool)"}
    try:
        resp = requests.get(arxiv_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        abstract_div = soup.find("blockquote", class_="abstract")
        if abstract_div:
            return abstract_div.text.replace("Abstract:", "").strip()
    except Exception:
        pass
    return ""


# ── Summarizer ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a science communicator who specialises in explaining research papers to complete beginners.
When given a research paper's title and abstract, you write a clear, engaging explanation that:
1. Starts with a one-sentence "what problem this solves" hook.
2. Explains the approach/method used in plain language.
3. Defines every technical term or jargon inline in parentheses the first time it appears — e.g. "neural network (a system loosely inspired by how the brain connects neurons)".
4. Ends with a short "Why this matters" section of 2-3 sentences.

Use simple English. No bullet points — write flowing paragraphs. Target audience: a curious person with no technical background."""


def summarize_paper(groq_client, title: str, abstract: str) -> str:
    prompt = f"Paper title: {title}\n\nAbstract:\n{abstract}\n\nWrite a detailed layman explanation of this paper."
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.6,
            max_tokens=900,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"[Summarization failed: {e}]"


# ── Supabase helpers ──────────────────────────────────────────────────────────
def init_table(supabase: Client):
    """Check table exists — user must create it via Supabase dashboard."""
    pass  # Table creation is done via Supabase SQL editor (see README)


def paper_exists(supabase: Client, arxiv_id: str) -> bool:
    try:
        res = supabase.table("papers").select("arxiv_id").eq("arxiv_id", arxiv_id).execute()
        return len(res.data) > 0
    except Exception:
        return False


def save_paper(supabase: Client, paper: dict):
    try:
        supabase.table("papers").insert(paper).execute()
    except Exception as e:
        st.warning(f"DB save failed for {paper.get('arxiv_id')}: {e}")


def fetch_papers_from_db(supabase: Client, category_filter=None, search=None, limit=100) -> list[dict]:
    try:
        query = supabase.table("papers").select("*").order("scraped_at", desc=True).limit(limit)
        if category_filter:
            query = query.eq("category", category_filter)
        if search:
            query = query.ilike("title", f"%{search}%")
        res = query.execute()
        return res.data or []
    except Exception as e:
        st.error(f"Failed to fetch from DB: {e}")
        return []


def count_papers(supabase: Client) -> int:
    try:
        res = supabase.table("papers").select("id", count="exact").execute()
        return res.count or 0
    except Exception:
        return 0


# ── UI helpers ────────────────────────────────────────────────────────────────
def cat_pill(cat: str) -> str:
    css = CAT_CSS.get(cat, "cat-cs-ai")
    return f'<span class="cat-pill {css}">{cat}</span>'


def render_paper_card(p: dict):
    date_str = ""
    if p.get("scraped_at"):
        try:
            dt = datetime.fromisoformat(p["scraped_at"].replace("Z", "+00:00"))
            date_str = dt.strftime("%d %b %Y")
        except Exception:
            date_str = p["scraped_at"][:10]

    st.markdown(f"""
<div class="paper-card">
    {cat_pill(p.get('category', ''))}
    <div class="paper-title">{p.get('title', 'Untitled')}</div>
    <div class="paper-meta">
        {'👥 ' + p['authors'][:120] + ('…' if len(p.get('authors','')) > 120 else '') if p.get('authors') else ''}
        {'&nbsp;·&nbsp;' if p.get('authors') and date_str else ''}
        {'📅 ' + date_str if date_str else ''}
    </div>
    <div class="paper-summary">{p.get('summary', 'No summary available.')}</div>
    <a class="paper-link" href="{p.get('arxiv_url', '#')}" target="_blank">→ Read on arXiv</a>
</div>
""", unsafe_allow_html=True)


# ── Main app ──────────────────────────────────────────────────────────────────
def main():
    supabase = get_supabase()
    groq_client = get_groq()

    # Header
    st.markdown("""
<div class="app-header">
    <div class="app-title">ar<span>X</span>iv Lens</div>
    <div class="app-subtitle">Scrape · Summarize · Understand — CS papers in plain English</div>
</div>
""", unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.markdown("### ⚙️ Fetch Settings")
        st.markdown("---")

        selected_labels = st.multiselect(
            "Select categories to scrape",
            options=list(CATEGORIES.keys()),
            default=list(CATEGORIES.keys())[:2],
        )
        selected_cats = [CATEGORIES[l] for l in selected_labels]

        max_papers = st.slider("Max papers per category", 5, 50, 15)

        st.markdown("---")
        fetch_btn = st.button("🚀 Fetch & Summarize Papers", use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📋 Legend")
        for label, code in CATEGORIES.items():
            css = CAT_CSS[code]
            short = label.split("—")[0].strip()
            st.markdown(f'<span class="cat-pill {css}">{code}</span> {short}', unsafe_allow_html=True)

        st.markdown("---")
        total = count_papers(supabase)
        st.markdown(f"**{total}** papers in database")

    # Tabs
    tab1, tab2 = st.tabs(["📰 Dashboard", "➕ Fetch Log"])

    # ── TAB 1: Dashboard ──────────────────────────────────────────────────────
    with tab1:
        col1, col2 = st.columns([2, 1])
        with col1:
            search_query = st.text_input("🔍 Search by title", placeholder="e.g. diffusion, transformer, RAG…")
        with col2:
            filter_cat = st.selectbox(
                "Filter by category",
                ["All"] + list(CATEGORIES.values()),
            )

        cat_arg = None if filter_cat == "All" else filter_cat
        papers = fetch_papers_from_db(supabase, category_filter=cat_arg, search=search_query or None)

        # Stats
        if papers:
            cats_present = list(set(p["category"] for p in papers))
            st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item">
        <div class="stat-num">{len(papers)}</div>
        <div class="stat-label">papers shown</div>
    </div>
    <div class="stat-item">
        <div class="stat-num">{len(cats_present)}</div>
        <div class="stat-label">categories</div>
    </div>
    <div class="stat-item">
        <div class="stat-num">{total}</div>
        <div class="stat-label">total in DB</div>
    </div>
</div>
""", unsafe_allow_html=True)

            for p in papers:
                render_paper_card(p)
        else:
            st.info("No papers found. Use the sidebar to fetch and summarize papers.", icon="🔬")

    # ── TAB 2: Fetch Log ──────────────────────────────────────────────────────
    with tab2:
        if fetch_btn:
            if not selected_cats:
                st.warning("Please select at least one category in the sidebar.")
            else:
                st.markdown("### 🔄 Fetching in progress…")
                total_saved = 0
                total_skipped = 0

                for cat in selected_cats:
                    st.markdown(f"**Scraping `{cat}`…**")
                    papers_raw = scrape_arxiv(cat)

                    if not papers_raw:
                        st.warning(f"No papers found for {cat}.")
                        continue

                    papers_to_process = papers_raw[:max_papers]
                    progress_bar = st.progress(0)
                    status_box = st.empty()

                    for i, paper in enumerate(papers_to_process):
                        progress_bar.progress((i + 1) / len(papers_to_process))
                        status_box.markdown(f"⏳ `[{i+1}/{len(papers_to_process)}]` {paper['title'][:80]}…")

                        if paper_exists(supabase, paper["arxiv_id"]):
                            total_skipped += 1
                            continue

                        # Fetch abstract
                        abstract = fetch_abstract(paper["arxiv_url"])
                        if not abstract:
                            total_skipped += 1
                            continue

                        paper["abstract"] = abstract

                        # Summarize
                        summary = summarize_paper(groq_client, paper["title"], abstract)
                        paper["summary"] = summary
                        paper["scraped_at"] = datetime.utcnow().isoformat()

                        save_paper(supabase, paper)
                        total_saved += 1

                        # Respect rate limits
                        time.sleep(0.5)

                    progress_bar.progress(1.0)
                    status_box.markdown(f"✅ Done with `{cat}`")
                    st.markdown("---")

                st.success(f"🎉 Complete! **{total_saved}** papers saved, **{total_skipped}** skipped (already in DB or no abstract).")
                st.balloons()
        else:
            st.info("Configure your categories in the sidebar and click **Fetch & Summarize Papers** to start.", icon="👈")


if __name__ == "__main__":
    main()
