import streamlit as st
import requests
from bs4 import BeautifulSoup
from groq import Groq
from supabase import create_client, Client
from datetime import datetime, date, timedelta, timezone
import os
from dotenv import load_dotenv
import time

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ArXiv Lens",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap');

:root {
    --bg:       #0a0a0f;
    --surface:  #13131a;
    --surface2: #1c1c28;
    --border:   #2a2a3d;
    --accent:   #7c6af7;
    --accent2:  #f7c948;
    --text:     #e8e8f0;
    --muted:    #6b6b8a;
    --success:  #3ecf8e;
    --danger:   #f56565;
    --star:     #f7c948;
}

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: var(--bg) !important;
    color: var(--text) !important;
}
.stApp { background-color: var(--bg) !important; }
#MainMenu, footer, header { visibility: hidden; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Header ── */
.app-header {
    padding: 1.6rem 0 1.2rem 0;
    border-bottom: 1px solid var(--border);
    margin-bottom: 1.6rem;
}
.app-title {
    font-family: 'Space Mono', monospace;
    font-size: 2.2rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -1px;
    margin: 0;
}
.app-title span { color: var(--accent); }
.app-subtitle { font-size: 0.9rem; color: var(--muted); margin-top: 0.3rem; }

/* ── Sidebar toggle button (top of main area) ── */
.sidebar-hint {
    font-size: 0.78rem;
    color: var(--muted);
    margin-bottom: 1rem;
    padding: 0.5rem 0.9rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    display: inline-block;
    font-family: 'Space Mono', monospace;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 600 !important;
    padding: 0.55rem 1.2rem !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}
.stButton > button:hover {
    background: #6a5ae0 !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 20px rgba(124,106,247,0.35) !important;
}

/* ── Category pills ── */
.cat-pill {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    font-family: 'Space Mono', monospace;
    margin-right: 5px;
}
.cat-cs-ai { background:rgba(124,106,247,0.18); color:#a89af9; border:1px solid rgba(124,106,247,0.3); }
.cat-cs-cv { background:rgba(247,201,72,0.13);  color:#f7c948; border:1px solid rgba(247,201,72,0.3); }
.cat-cs-cl { background:rgba(62,207,142,0.13);  color:#3ecf8e; border:1px solid rgba(62,207,142,0.3); }
.cat-cs-lg { background:rgba(245,101,101,0.13); color:#f56565; border:1px solid rgba(245,101,101,0.3); }
.cat-cs-se { background:rgba(99,179,237,0.13);  color:#63b3ed; border:1px solid rgba(99,179,237,0.3); }

/* ── Paper card ── */
.paper-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1rem;
    position: relative;
    transition: border-color 0.2s, box-shadow 0.2s;
    overflow: hidden;
}
.paper-card::before {
    content: '';
    position: absolute;
    top:0; left:0; width:3px; height:100%;
    background: var(--accent);
    border-radius: 14px 0 0 14px;
}
.paper-card.starred::before { background: var(--star); }
.paper-card:hover {
    border-color: var(--accent);
    box-shadow: 0 4px 28px rgba(124,106,247,0.12);
}
.paper-title {
    font-size: 1.05rem;
    font-weight: 600;
    color: var(--text);
    margin: 0.4rem 0 0.7rem 0;
    line-height: 1.4;
}
.paper-meta { font-size: 0.78rem; color: var(--muted); font-family:'Space Mono',monospace; margin-bottom:0.9rem; }
.paper-summary {
    font-size: 0.9rem;
    color: #c8c8e0;
    line-height: 1.78;
    border-top: 1px solid var(--border);
    padding-top: 0.9rem;
}
.paper-link {
    display:inline-flex; align-items:center; gap:5px;
    margin-top:0.9rem; font-size:0.8rem; color:var(--accent);
    font-weight:500; font-family:'Space Mono',monospace;
    text-decoration:none;
}
.star-badge {
    position:absolute; top:1rem; right:1rem;
    font-size:1rem;
}

/* ── Stats bar ── */
.stats-bar {
    display:flex; gap:1.2rem; flex-wrap:wrap;
    padding:0.9rem 1.2rem;
    background:var(--surface); border:1px solid var(--border);
    border-radius:10px; margin-bottom:1.4rem;
}
.stat-item { text-align:center; min-width:60px; }
.stat-num { font-family:'Space Mono',monospace; font-size:1.3rem; font-weight:700; color:var(--accent); }
.stat-label { font-size:0.72rem; color:var(--muted); margin-top:2px; }

/* ── Notification banners ── */
.notif {
    padding:0.75rem 1rem; border-radius:9px; font-size:0.88rem;
    margin-bottom:0.7rem; display:flex; align-items:center; gap:0.6rem;
}
.notif-success { background:rgba(62,207,142,0.12); border:1px solid rgba(62,207,142,0.3); color:#3ecf8e; }
.notif-warn    { background:rgba(247,201,72,0.12);  border:1px solid rgba(247,201,72,0.3);  color:#f7c948; }
.notif-error   { background:rgba(245,101,101,0.12); border:1px solid rgba(245,101,101,0.3); color:#f56565; }
.notif-info    { background:rgba(124,106,247,0.12); border:1px solid rgba(124,106,247,0.3); color:#a89af9; }

/* ── Progress ── */
.stProgress > div > div > div > div { background:var(--accent) !important; }

/* ── Form inputs ── */
[data-testid="stTextInput"] > div > div > input,
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"] > div,
[data-testid="stDateInput"] > div > div > input {
    background:var(--surface2) !important;
    border-color:var(--border) !important;
    color:var(--text) !important;
    border-radius:8px !important;
}
[data-testid="stDateInput"] { color: var(--text) !important; }

hr { border-color:var(--border) !important; }
::-webkit-scrollbar { width:5px; }
::-webkit-scrollbar-track { background:var(--bg); }
::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:var(--accent); }

/* ── Live fetch status box ── */
.fetch-status-box {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    margin-top: 1rem;
}
.fetch-status-title {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: var(--accent);
    margin-bottom: 0.8rem;
    letter-spacing: 0.5px;
}
.fetch-paper-name {
    font-size: 0.85rem;
    color: var(--text);
    font-style: italic;
    margin-top: 0.3rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
</style>
""", unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
CATEGORIES = {
    "cs.AI — Artificial Intelligence":              "cs.AI",
    "cs.CV — Computer Vision":                      "cs.CV",
    "cs.CL — Computation & Language (NLP)":         "cs.CL",
    "cs.LG — Machine Learning":                     "cs.LG",
    "cs.SE — Software Engineering":                 "cs.SE",
}
CAT_CSS = {
    "cs.AI": "cat-cs-ai",
    "cs.CV": "cat-cs-cv",
    "cs.CL": "cat-cs-cl",
    "cs.LG": "cat-cs-lg",
    "cs.SE": "cat-cs-se",
}
LEGEND = {
    "cs.AI": "Artificial Intelligence",
    "cs.CV": "Computer Vision",
    "cs.CL": "Computation & Language (NLP)",
    "cs.LG": "Machine Learning",
    "cs.SE": "Software Engineering",
}

# ── Clients ───────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_KEY", "")
    if not url or not key:
        st.error("⚠️ SUPABASE_URL and SUPABASE_KEY are missing. Add them to your .env file.")
        st.stop()
    return create_client(url, key)

@st.cache_resource
def get_groq() -> Groq:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        st.error("⚠️ GROQ_API_KEY is missing. Add it to your .env file.")
        st.stop()
    return Groq(api_key=api_key)

# ── Scraper ───────────────────────────────────────────────────────────────────
def scrape_arxiv(category: str) -> list[dict]:
    url = f"https://arxiv.org/list/{category}/recent"
    headers = {"User-Agent": "Mozilla/5.0 (ArXivLens/1.0)"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        notify("error", f"Timed out while reaching arXiv for **{category}**. Try again in a moment.")
        return []
    except requests.exceptions.ConnectionError:
        notify("error", f"Network error reaching arXiv. Check your connection.")
        return []
    except Exception as e:
        notify("error", f"Failed to fetch arXiv page for **{category}**: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    dl = soup.find("dl")
    if not dl:
        notify("warn", f"No papers found on arXiv for **{category}** — the page structure may have changed.")
        return []

    papers = []
    for dt, dd in zip(dl.find_all("dt"), dl.find_all("dd")):
        try:
            link_tag = dt.find("a", title="Abstract")
            if not link_tag:
                continue
            arxiv_id  = link_tag.text.strip().replace("arXiv:", "")
            arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
            title_tag = dd.find("div", class_="list-title")
            title     = title_tag.text.replace("Title:", "").strip() if title_tag else "Unknown Title"
            authors_tag = dd.find("div", class_="list-authors")
            authors   = authors_tag.text.replace("Authors:", "").strip() if authors_tag else ""
            papers.append({
                "arxiv_id":  arxiv_id,
                "arxiv_url": arxiv_url,
                "title":     title,
                "authors":   authors[:400],
                "category":  category,
            })
        except Exception:
            continue
    return papers


def fetch_abstract(arxiv_url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (ArXivLens/1.0)"}
    try:
        resp = requests.get(arxiv_url, headers=headers, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        block = soup.find("blockquote", class_="abstract")
        if block:
            return block.text.replace("Abstract:", "").strip()
    except Exception:
        pass
    return ""

# ── Summarizer ────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """You are a science communicator who explains research papers to complete beginners.
Given a paper title and abstract, write a clear explanation that:
1. Opens with one sentence on what problem this solves.
2. Explains the approach/method in plain language.
3. Defines every technical term or jargon inline in parentheses the FIRST time it appears — e.g. "LLM (Large Language Model — an AI trained on massive amounts of text)".
4. Ends with a short "Why this matters" paragraph of 2–3 sentences.
Write in flowing paragraphs. No bullet points. Simple English. Target: a curious non-technical reader."""

def summarize_paper(groq_client: Groq, title: str, abstract: str) -> tuple[str, str | None]:
    """Returns (summary_text, error_message). error_message is None on success."""
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": f"Title: {title}\n\nAbstract:\n{abstract}\n\nWrite the layman explanation."},
            ],
            temperature=0.6,
            max_tokens=900,
        )
        return completion.choices[0].message.content.strip(), None
    except Exception as e:
        err = str(e)
        if "rate_limit" in err.lower() or "429" in err:
            return "", "rate_limit"
        if "quota" in err.lower() or "billing" in err.lower():
            return "", "quota"
        return "", f"groq_error: {err}"

# ── Supabase helpers ──────────────────────────────────────────────────────────
def paper_exists(supabase: Client, arxiv_id: str) -> bool:
    try:
        res = supabase.table("papers").select("arxiv_id").eq("arxiv_id", arxiv_id).execute()
        return len(res.data) > 0
    except Exception:
        return False

def save_paper(supabase: Client, paper: dict) -> str | None:
    """Returns error string or None on success."""
    try:
        supabase.table("papers").insert(paper).execute()
        return None
    except Exception as e:
        err = str(e)
        if "relation" in err.lower() or "does not exist" in err.lower():
            return "table_missing"
        if "violates" in err.lower() or "unique" in err.lower():
            return "duplicate"
        return f"db_error: {err}"

def fetch_papers_from_db(
    supabase: Client,
    category_filter=None,
    search=None,
    date_from=None,
    date_to=None,
    starred_only=False,
    limit=150,
) -> list[dict]:
    try:
        query = supabase.table("papers").select("*").order("scraped_at", desc=True).limit(limit)
        if category_filter:
            query = query.eq("category", category_filter)
        if search:
            query = query.ilike("title", f"%{search}%")
        if date_from:
            query = query.gte("scraped_at", date_from.isoformat())
        if date_to:
            dt_to = datetime.combine(date_to, datetime.max.time())
            query = query.lte("scraped_at", dt_to.isoformat())
        if starred_only:
            query = query.eq("starred", True)
        res = query.execute()
        return res.data or []
    except Exception as e:
        notify("error", f"Database fetch failed: {e}")
        return []

def delete_paper(supabase: Client, paper_id: int) -> bool:
    try:
        supabase.table("papers").delete().eq("id", paper_id).execute()
        return True
    except Exception as e:
        notify("error", f"Could not delete paper: {e}")
        return False

def toggle_star(supabase: Client, paper_id: int, current: bool) -> bool:
    try:
        supabase.table("papers").update({"starred": not current}).eq("id", paper_id).execute()
        return True
    except Exception as e:
        notify("error", f"Could not update star: {e}")
        return False

def count_papers(supabase: Client) -> int:
    try:
        res = supabase.table("papers").select("id", count="exact").execute()
        return res.count or 0
    except Exception:
        return 0

# ── Notification helper ───────────────────────────────────────────────────────
def notify(kind: str, message: str):
    icons = {"success": "✅", "warn": "⚠️", "error": "❌", "info": "ℹ️"}
    css   = {"success": "notif-success", "warn": "notif-warn", "error": "notif-error", "info": "notif-info"}
    st.markdown(
        f'<div class="notif {css.get(kind,"notif-info")}">{icons.get(kind,"")} {message}</div>',
        unsafe_allow_html=True,
    )

# ── UI helpers ────────────────────────────────────────────────────────────────
def cat_pill(cat: str) -> str:
    css = CAT_CSS.get(cat, "cat-cs-ai")
    return f'<span class="cat-pill {css}">{cat}</span>'

def render_paper_card(supabase: Client, p: dict):
    paper_id = p.get("id")
    starred  = p.get("starred", False)

    date_str = ""
    if p.get("scraped_at"):
        try:
            dt = datetime.fromisoformat(p["scraped_at"].replace("Z", "+00:00"))
            date_str = dt.strftime("%d %b %Y")
        except Exception:
            date_str = str(p["scraped_at"])[:10]

    authors_txt = p.get("authors", "")
    if authors_txt and len(authors_txt) > 120:
        authors_txt = authors_txt[:120] + "…"

    star_icon   = "⭐" if starred else "☆"
    starred_cls = "starred" if starred else ""

    st.markdown(f"""
<div class="paper-card {starred_cls}">
    <span class="star-badge">{star_icon if starred else ""}</span>
    {cat_pill(p.get("category",""))}
    <div class="paper-title">{p.get("title","Untitled")}</div>
    <div class="paper-meta">
        {"👥 " + authors_txt if authors_txt else ""}
        {"&nbsp;·&nbsp;" if authors_txt and date_str else ""}
        {"📅 " + date_str if date_str else ""}
    </div>
    <div class="paper-summary">{p.get("summary","No summary available.")}</div>
    <a class="paper-link" href="{p.get("arxiv_url","#")}" target="_blank">→ Read on arXiv</a>
</div>
""", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        star_label = "⭐ Unstar" if starred else "☆ Star"
        if st.button(star_label, key=f"star_{paper_id}"):
            if toggle_star(supabase, paper_id, starred):
                st.rerun()
    with col2:
        if st.button("🗑️ Delete", key=f"del_{paper_id}"):
            if delete_paper(supabase, paper_id):
                notify("success", "Paper deleted.")
                st.rerun()

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    supabase     = get_supabase()
    groq_client  = get_groq()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### ⚙️ Fetch Settings")
        st.markdown("---")

        selected_labels = st.multiselect(
            "Categories to scrape",
            options=list(CATEGORIES.keys()),
            default=list(CATEGORIES.keys())[:2],
        )
        selected_cats = [CATEGORIES[lbl] for lbl in selected_labels]

        max_papers = st.slider("Max papers per category", 5, 50, 15)

        st.markdown("---")
        fetch_btn = st.button("🚀 Fetch & Summarize", use_container_width=True)

        st.markdown("---")
        st.markdown("#### 📋 Category Legend")
        for code, full in LEGEND.items():
            css = CAT_CSS[code]
            st.markdown(
                f'<span class="cat-pill {css}">{code}</span>&nbsp;{full}',
                unsafe_allow_html=True,
            )

        st.markdown("---")
        total_in_db = count_papers(supabase)
        st.markdown(f"**{total_in_db}** papers stored in database")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("""
<div class="app-header">
    <div class="app-title">ar<span>X</span>iv Lens</div>
    <div class="app-subtitle">Scrape · Summarize · Understand — CS research in plain English</div>
</div>
""", unsafe_allow_html=True)

    # Sidebar hint for mobile
    st.markdown(
        '<div class="sidebar-hint">☰ &nbsp;Use the top-left arrow to open the sidebar and fetch papers</div>',
        unsafe_allow_html=True,
    )

    # ── Live fetch section ────────────────────────────────────────────────────
    if fetch_btn:
        if not selected_cats:
            notify("warn", "Please select at least one category in the sidebar before fetching.")
        else:
            st.markdown("---")
            st.markdown("### 🔄 Fetching & Summarizing Papers")

            total_saved   = 0
            total_skipped = 0
            total_errors  = 0
            rate_limited  = False

            for cat in selected_cats:  # ← iterates ALL selected categories correctly
                st.markdown(f"#### Category: `{cat}`")
                with st.spinner(f"Scraping arXiv for {cat}…"):
                    papers_raw = scrape_arxiv(cat)

                if not papers_raw:
                    notify("warn", f"No papers returned for **{cat}**.")
                    continue

                papers_to_process = papers_raw[:max_papers]
                progress_bar = st.progress(0, text=f"Processing {cat} — 0 / {len(papers_to_process)}")
                current_paper_box = st.empty()

                for i, paper in enumerate(papers_to_process):
                    progress_pct  = (i + 1) / len(papers_to_process)
                    progress_bar.progress(progress_pct, text=f"Processing {cat} — {i+1} / {len(papers_to_process)}")
                    current_paper_box.markdown(
                        f'<div class="fetch-paper-name">⏳ {paper["title"][:90]}…</div>',
                        unsafe_allow_html=True,
                    )

                    # Duplicate check
                    if paper_exists(supabase, paper["arxiv_id"]):
                        total_skipped += 1
                        continue

                    # Fetch abstract
                    abstract = fetch_abstract(paper["arxiv_url"])
                    if not abstract:
                        total_skipped += 1
                        continue

                    # Summarize
                    summary, err = summarize_paper(groq_client, paper["title"], abstract)

                    if err == "rate_limit":
                        notify("warn", f"⏸️ Groq rate limit hit after {total_saved} papers. Wait ~60 seconds and fetch again — duplicates will be skipped automatically.")
                        rate_limited = True
                        break
                    elif err == "quota":
                        notify("error", "Your Groq quota is exhausted. Check your plan at console.groq.com.")
                        rate_limited = True
                        break
                    elif err:
                        notify("warn", f"Summarization failed for *{paper['title'][:60]}*: {err}")
                        total_errors += 1
                        continue

                    # Save to Supabase
                    record = {
                        **paper,
                        "abstract":   abstract,
                        "summary":    summary,
                        "starred":    False,
                        "scraped_at": datetime.now(timezone.utc).isoformat(),
                    }
                    db_err = save_paper(supabase, record)

                    if db_err == "table_missing":
                        notify("error", "The **papers** table doesn't exist in Supabase yet. Run the CREATE TABLE SQL from the README.")
                        st.stop()
                    elif db_err == "duplicate":
                        total_skipped += 1
                    elif db_err:
                        notify("warn", f"DB save failed for *{paper['title'][:50]}*: {db_err}")
                        total_errors += 1
                    else:
                        total_saved += 1

                    time.sleep(0.5)  # Groq free-tier rate limit buffer

                progress_bar.progress(1.0, text=f"✅ Done with {cat}")
                current_paper_box.empty()

                if rate_limited:
                    break

            # Summary notification
            parts = [f"**{total_saved}** saved"]
            if total_skipped: parts.append(f"**{total_skipped}** skipped (already in DB or no abstract)")
            if total_errors:  parts.append(f"**{total_errors}** errors")
            notify("success" if not total_errors else "warn", "Fetch complete — " + " · ".join(parts))
            if total_saved:
                st.balloons()

            st.markdown("---")

    # ── Dashboard ─────────────────────────────────────────────────────────────
    st.markdown("### 📰 Paper Dashboard")

    # Filters row
    fcol1, fcol2, fcol3, fcol4 = st.columns([2, 1.2, 1.2, 1])
    with fcol1:
        search_query = st.text_input("🔍 Search title", placeholder="e.g. diffusion, RAG, transformer…", label_visibility="collapsed")
    with fcol2:
        filter_cat = st.selectbox("Category", ["All"] + list(CATEGORIES.values()), label_visibility="collapsed")
    with fcol3:
        date_range = st.selectbox("Date range", ["All time", "Today", "Last 7 days", "Last 30 days", "Custom"], label_visibility="collapsed")
    with fcol4:
        starred_only = st.checkbox("⭐ Starred only")

    # Date range logic
    date_from = date_to = None
    if date_range == "Today":
        date_from = date_to = date.today()
    elif date_range == "Last 7 days":
        date_from = date.today() - timedelta(days=7)
        date_to   = date.today()
    elif date_range == "Last 30 days":
        date_from = date.today() - timedelta(days=30)
        date_to   = date.today()
    elif date_range == "Custom":
        cc1, cc2 = st.columns(2)
        with cc1:
            date_from = st.date_input("From", value=date.today() - timedelta(days=7))
        with cc2:
            date_to = st.date_input("To", value=date.today())

    papers = fetch_papers_from_db(
        supabase,
        category_filter=None if filter_cat == "All" else filter_cat,
        search=search_query or None,
        date_from=date_from,
        date_to=date_to,
        starred_only=starred_only,
    )

    # Stats
    if papers:
        starred_count = sum(1 for p in papers if p.get("starred"))
        st.markdown(f"""
<div class="stats-bar">
    <div class="stat-item"><div class="stat-num">{len(papers)}</div><div class="stat-label">shown</div></div>
    <div class="stat-item"><div class="stat-num">{total_in_db}</div><div class="stat-label">total in DB</div></div>
    <div class="stat-item"><div class="stat-num">{starred_count}</div><div class="stat-label">starred</div></div>
    <div class="stat-item"><div class="stat-num">{len(set(p["category"] for p in papers))}</div><div class="stat-label">categories</div></div>
</div>
""", unsafe_allow_html=True)

        for p in papers:
            render_paper_card(supabase, p)
    else:
        st.info("No papers match your filters. Fetch some papers using the sidebar!", icon="🔬")


if __name__ == "__main__":
    main()
