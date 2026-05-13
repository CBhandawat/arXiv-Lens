import streamlit as st
import os
import time
from dotenv import load_dotenv

load_dotenv()

from pipeline.scraper import scrape_recent, fetch_abstract
from pipeline.scriptwriter import generate_script
from pipeline.tts import synthesize_script
from pipeline.audio_merge import merge_audio
from pipeline.uploader import upload_to_s3, get_existing_url

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ArXiv Cast",
    page_icon="🎙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

:root {
    --bg: #f5f7fa;
    --surface: #ffffff;
    --border: #dde1ea;
    --accent: #5b4fcf;
    --text: #1a1a2e;
    --muted: #6b7280;
    --success: #059669;
}

html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }

.app-header {
    padding: 1.2rem 0 1rem 0;
    border-bottom: 2px solid var(--border);
    margin-bottom: 1.4rem;
}
.app-title {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    color: var(--text);
    letter-spacing: -1px;
    margin: 0;
}
.app-title span { color: var(--accent); }
.app-subtitle { font-size: 0.88rem; color: var(--muted); margin-top: 0.3rem; }

.paper-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
    border-left: 3px solid var(--accent);
}
.paper-title { font-size: 1rem; font-weight: 600; color: var(--text); margin: 0 0 4px; }
.paper-meta  { font-size: 0.75rem; color: var(--muted); font-family: 'Space Mono', monospace; }

.script-turn {
    padding: 0.7rem 1rem;
    border-radius: 8px;
    margin-bottom: 8px;
    font-size: 0.9rem;
    line-height: 1.6;
}
.turn-priya {
    background: #ede9fe;
    border-left: 3px solid #5b4fcf;
    color: #2e1d6e;
}
.turn-ravi {
    background: #f0fdf4;
    border-left: 3px solid #059669;
    color: #064e3b;
}
.host-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    width: 100% !important;
}
.stButton > button:hover { background: #4a3fb5 !important; }

.stProgress > div > div > div > div { background: var(--accent) !important; }
</style>
""", unsafe_allow_html=True)

# ── Categories ────────────────────────────────────────────────────────────────
CATEGORIES = {
    "cs.AI — Artificial Intelligence": "cs.AI",
    "cs.CV — Computer Vision":         "cs.CV",
    "cs.CL — Computation & Language":  "cs.CL",
    "cs.LG — Machine Learning":        "cs.LG",
}

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    input_mode = st.radio("Input mode", ["Browse recent papers", "Paste arXiv URL"])

    if input_mode == "Browse recent papers":
        cat_label = st.selectbox("Category", list(CATEGORIES.keys()))
        selected_cat = CATEGORIES[cat_label]
        num_papers = st.slider("Papers to load", 3, 15, 5)
        load_btn = st.button("📄 Load papers", use_container_width=True)
    else:
        arxiv_url_input = st.text_input("arXiv abstract URL", placeholder="https://arxiv.org/abs/2501.xxxxx")
        load_btn = st.button("📄 Fetch paper", use_container_width=True)

    st.markdown("---")
    st.markdown("**Hosts**")
    st.markdown("🎙 **Priya** — the expert")
    st.markdown("🎙 **Ravi** — the curious learner")
    st.markdown("---")
    st.caption("Audio stored in S3 · Generated via Lemonfox TTS")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <div class="app-title">ar<span>X</span>iv Cast</div>
    <div class="app-subtitle">Turn any research paper into a two-host podcast — powered by Lemonfox TTS</div>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "papers"         not in st.session_state: st.session_state.papers = []
if "selected_paper" not in st.session_state: st.session_state.selected_paper = None
if "script"         not in st.session_state: st.session_state.script = None
if "audio_url"      not in st.session_state: st.session_state.audio_url = None
if "audio_bytes"    not in st.session_state: st.session_state.audio_bytes = None

# ── Load papers ───────────────────────────────────────────────────────────────
if load_btn:
    st.session_state.selected_paper = None
    st.session_state.script = None
    st.session_state.audio_url = None
    st.session_state.audio_bytes = None

    if input_mode == "Browse recent papers":
        with st.spinner(f"Scraping arXiv for {selected_cat}…"):
            papers = scrape_recent(selected_cat, max_papers=num_papers)
        if papers:
            st.session_state.papers = papers
            st.success(f"Loaded {len(papers)} papers from {selected_cat}")
        else:
            st.error("Could not load papers. arXiv may be down or the category returned nothing.")

    else:
        if not arxiv_url_input.strip():
            st.warning("Please paste an arXiv URL first.")
        else:
            with st.spinner("Fetching abstract…"):
                # Extract arxiv_id from URL
                arxiv_id = arxiv_url_input.rstrip("/").split("/")[-1]
                abstract = fetch_abstract(arxiv_url_input.strip())
                if abstract:
                    # We don't have title from URL alone — fetch it
                    from bs4 import BeautifulSoup
                    import requests
                    try:
                        resp = requests.get(arxiv_url_input.strip(), timeout=10,
                                            headers={"User-Agent": "ArXivCast/1.0"})
                        soup = BeautifulSoup(resp.text, "html.parser")
                        title_tag = soup.find("h1", class_="title")
                        title = title_tag.text.replace("Title:", "").strip() if title_tag else arxiv_id
                    except Exception:
                        title = arxiv_id

                    st.session_state.papers = [{
                        "arxiv_id":  arxiv_id,
                        "arxiv_url": arxiv_url_input.strip(),
                        "title":     title,
                        "authors":   "",
                        "category":  "custom",
                    }]
                    st.session_state.selected_paper = st.session_state.papers[0]
                    st.session_state.selected_paper["abstract"] = abstract
                else:
                    st.error("Could not fetch abstract. Check the URL.")

# ── Paper list ────────────────────────────────────────────────────────────────
col_list, col_detail = st.columns([1, 1.8])

with col_list:
    if st.session_state.papers:
        st.markdown(f"#### {len(st.session_state.papers)} papers")
        for p in st.session_state.papers:
            is_selected = (
                st.session_state.selected_paper is not None
                and st.session_state.selected_paper["arxiv_id"] == p["arxiv_id"]
            )
            border_color = "#5b4fcf" if is_selected else "#dde1ea"
            st.markdown(f"""
            <div class="paper-card" style="border-left-color:{border_color}; cursor:pointer;">
                <div class="paper-title">{p["title"][:90]}{"…" if len(p["title"]) > 90 else ""}</div>
                <div class="paper-meta">{p["arxiv_id"]} · {p.get("category","")}</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("Select →", key=f"sel_{p['arxiv_id']}"):
                st.session_state.selected_paper = p
                st.session_state.script = None
                st.session_state.audio_url = None
                st.session_state.audio_bytes = None

                # Fetch abstract if not already loaded
                if "abstract" not in p or not p["abstract"]:
                    with st.spinner("Fetching abstract…"):
                        p["abstract"] = fetch_abstract(p["arxiv_url"])
                        st.session_state.selected_paper = p
                st.rerun()
    else:
        st.info("Load papers from the sidebar to get started.", icon="🔬")

# ── Detail panel ──────────────────────────────────────────────────────────────
with col_detail:
    paper = st.session_state.selected_paper

    if paper is None:
        st.info("Select a paper to generate its podcast episode.", icon="🎙")

    else:
        st.markdown(f"### {paper['title']}")
        if paper.get("authors"):
            st.caption(f"Authors: {paper['authors'][:150]}")
        st.markdown(f"[arXiv →]({paper['arxiv_url']})")

        abstract = paper.get("abstract", "")
        if abstract:
            with st.expander("Abstract"):
                st.write(abstract)

        st.markdown("---")

        # ── Step 1: Generate script ───────────────────────────────────────
        if st.session_state.script is None:
            if st.button("✍️ Write podcast script", use_container_width=True):
                if not abstract:
                    st.error("No abstract available for this paper.")
                else:
                    with st.spinner("Writing dialogue script with Groq/LLaMA…"):
                        try:
                            script = generate_script(paper["title"], abstract)
                            st.session_state.script = script
                            st.rerun()
                        except Exception as e:
                            st.error(f"Script generation failed: {e}")

        # ── Show script ───────────────────────────────────────────────────
        if st.session_state.script:
            script = st.session_state.script
            st.markdown(f"#### 📝 Episode: *{script.get('title', 'Untitled')}*")

            for turn in script["turns"]:
                css_class = "turn-priya" if turn["host"] == "Priya" else "turn-ravi"
                icon = "🔬" if turn["host"] == "Priya" else "🤔"
                st.markdown(f"""
                <div class="script-turn {css_class}">
                    <div class="host-label">{icon} {turn["host"].upper()}</div>
                    {turn["text"]}
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")

            # ── Step 2: Generate audio ────────────────────────────────────
            if st.session_state.audio_url is None and st.session_state.audio_bytes is None:

                use_s3 = all([
                    os.environ.get("AWS_ACCESS_KEY_ID"),
                    os.environ.get("S3_BUCKET_NAME"),
                ])

                # Check S3 cache first
                if use_s3:
                    cached_url = get_existing_url(paper["arxiv_id"])
                    if cached_url:
                        st.session_state.audio_url = cached_url
                        st.rerun()

                btn_label = "🎙 Generate podcast MP3" + (" + upload to S3" if use_s3 else " (local only)")
                if st.button(btn_label, use_container_width=True):
                    turns = script["turns"]
                    progress = st.progress(0, text="Starting TTS synthesis…")

                    try:
                        # Synthesize each turn
                        chunks = []
                        for i, turn in enumerate(turns):
                            progress.progress(
                                (i + 0.5) / len(turns),
                                text=f"Synthesizing {turn['host']} — turn {i+1}/{len(turns)}",
                            )
                            from pipeline.tts import synthesize_turn
                            chunk = synthesize_turn(turn["text"], turn["host"])
                            chunks.append(chunk)
                            time.sleep(0.3)  # small gap to avoid rate limits

                        progress.progress(0.9, text="Merging audio…")
                        mp3_bytes = merge_audio(chunks, turns)

                        if use_s3:
                            progress.progress(0.97, text="Uploading to S3…")
                            url = upload_to_s3(mp3_bytes, paper["arxiv_id"])
                            st.session_state.audio_url = url
                        else:
                            st.session_state.audio_bytes = mp3_bytes

                        progress.progress(1.0, text="Done!")
                        st.rerun()

                    except Exception as e:
                        st.error(f"Audio generation failed: {e}")

            # ── Audio player ──────────────────────────────────────────────
            if st.session_state.audio_url:
                st.success("Podcast ready! Stored in S3.")
                st.audio(st.session_state.audio_url)
                st.markdown(f"[Download MP3]({st.session_state.audio_url})")

            elif st.session_state.audio_bytes:
                st.success("Podcast ready!")
                st.audio(st.session_state.audio_bytes, format="audio/mp3")
                st.download_button(
                    "⬇️ Download MP3",
                    data=st.session_state.audio_bytes,
                    file_name=f"{paper['arxiv_id']}_podcast.mp3",
                    mime="audio/mpeg",
                )
