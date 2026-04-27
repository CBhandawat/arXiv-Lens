import streamlit as st
from PIL import Image
import base64
import io
import os
import json
import requests
import httpx
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai import types as gtypes

# ── Load env ──────────────────────────────────────────────────────────────────
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SERP_API_KEY   = os.getenv("SERP_API_KEY")

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="VERA - Visual RAG",
    layout="centered"
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=IBM+Plex+Mono:wght@300;400;500&family=Lora:ital,wght@0,400;0,500;1,400&display=swap');

    html, body, [class*="css"] {
        font-family: 'Lora', Georgia, serif;
        background-color: #0d0d0d;
        color: #e8e0d5;
    }

    .block-container { max-width: 780px; padding-top: 2rem; }

    /* ── Header ── */
    .rose-masthead {
        border-top: 2px solid #c9a96e;
        border-bottom: 1px solid #2a2520;
        padding: 18px 0 14px;
        margin-bottom: 28px;
        display: flex;
        align-items: baseline;
        gap: 14px;
    }
    .rose-title {
        font-family: 'Syne', sans-serif;
        font-size: 32px;
        font-weight: 800;
        letter-spacing: -0.02em;
        color: #f0e6d3;
        margin: 0;
    }
    .rose-title span { color: #c9a96e; }
    .rose-sub {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        color: #7a6e60;
        letter-spacing: 0.14em;
        text-transform: uppercase;
        margin-top: 4px;
    }

    /* ── Pipeline tracker ── */
    .pipeline {
        display: flex;
        align-items: stretch;
        gap: 0;
        margin: 20px 0;
        border: 1px solid #1e1a16;
        border-radius: 6px;
        overflow: hidden;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }
    .p-step {
        flex: 1;
        padding: 10px 12px;
        background: #111;
        border-right: 1px solid #1e1a16;
        text-align: center;
        transition: all 0.3s;
    }
    .p-step:last-child { border-right: none; }
    .p-step .icon { font-size: 16px; display: block; margin-bottom: 4px; }
    .p-step .label { color: #3a3530; font-size: 9px; letter-spacing: 0.08em; text-transform: uppercase; }

    .p-step.done   { background: #0e1a12; }
    .p-step.done   .label { color: #4ade80; }
    .p-step.done   .icon  { filter: none; }

    .p-step.active { background: #1a1505; border-top: 2px solid #c9a96e; }
    .p-step.active .label { color: #c9a96e; }

    .p-step.idle   .icon { opacity: 0.2; }

    /* ── Section cards ── */
    .section-card {
        background: #111008;
        border: 1px solid #1e1a14;
        border-radius: 6px;
        padding: 16px 18px;
        margin: 14px 0;
    }
    .section-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.16em;
        text-transform: uppercase;
        color: #c9a96e;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .section-label::after {
        content: '';
        flex: 1;
        height: 1px;
        background: #1e1a14;
    }

    /* ── Ref images strip ── */
    .ref-strip {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-top: 8px;
    }
    .ref-img-wrap {
        position: relative;
        border: 1px solid #2a2418;
        border-radius: 4px;
        overflow: hidden;
        width: 110px;
        height: 80px;
    }
    .ref-img-wrap img {
        width: 100%;
        height: 100%;
        object-fit: cover;
    }
    .ref-img-label {
        position: absolute;
        bottom: 0;
        left: 0;
        right: 0;
        background: rgba(0,0,0,0.7);
        font-family: 'IBM Plex Mono', monospace;
        font-size: 8px;
        color: #c9a96e;
        padding: 2px 4px;
        text-align: center;
    }

    /* ── Answer ── */
    .answer-box {
        background: #0d1208;
        border: 1px solid #1e2818;
        border-left: 3px solid #c9a96e;
        border-radius: 6px;
        padding: 20px 22px;
        margin-top: 16px;
        font-size: 15px;
        line-height: 1.8;
        font-family: 'Lora', serif;
    }
    .answer-label {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        letter-spacing: 0.16em;
        color: #c9a96e;
        text-transform: uppercase;
        margin-bottom: 12px;
    }

    /* ── Websense badge ── */
    .ws-needed {
        display: inline-block;
        background: #1a1505;
        border: 1px solid #c9a96e55;
        color: #c9a96e;
        padding: 3px 10px;
        border-radius: 2px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
    }
    .ws-skip {
        display: inline-block;
        background: #0e1a12;
        border: 1px solid #4ade8055;
        color: #4ade80;
        padding: 3px 10px;
        border-radius: 2px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: 0.08em;
    }

    /* ── Entity chip ── */
    .entity-chip {
        display: inline-block;
        background: #1a1208;
        border: 1px solid #c9a96e44;
        color: #e8d5a0;
        padding: 4px 12px;
        border-radius: 20px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        margin: 4px 4px 4px 0;
    }

    /* ── Error ── */
    .error-box {
        background: #1a0808;
        border: 1px solid #ef444433;
        border-radius: 6px;
        padding: 14px 18px;
        color: #f87171;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
    }

    /* ── Misc ── */
    .divider { border: none; border-top: 1px solid #1e1a14; margin: 20px 0; }
    .stButton button {
        background: #c9a96e !important;
        color: #0d0d0d !important;
        font-family: 'Syne', sans-serif !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 10px 28px !important;
    }
    .stButton button:hover { background: #e0c080 !important; }
    .stFileUploader, .stTextInput input {
        background: #111 !important;
        border-color: #2a2520 !important;
        color: #e8e0d5 !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="rose-masthead">
    <div>
        <div class="rose-title"> <span>VERA</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    "<p style='color:#7a6e60;font-size:14px;margin-bottom:24px'>"
    "Upload an image. VERA searches the web visually — injecting reference images and live text context "
    "before asking Gemini 2.5 Flash Lite to reason from pixels, not descriptions."
    "</p>",
    unsafe_allow_html=True
)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("<p style='font-family:Syne,sans-serif;font-weight:700;font-size:16px;color:#c9a96e'>⚙ Configuration</p>", unsafe_allow_html=True)

    websense_enabled = st.toggle("WebSense Gate", value=True,
        help="Let Kimi decide if retrieval is needed. Disable to always retrieve.")
    num_ref_images = st.slider("Reference images (Visual Prompt Enhancer)", 1, 5, 3,
        help="How many Google Lens matches to inject into Kimi's context.")
    inject_wiki = st.toggle("Textual Prompt Enhancer (Wikipedia)", value=True,
        help="Fetch Wikipedia summary for found entity and inject as context.")

    st.divider()
    st.markdown("**VERA Pipeline**")
    st.markdown(
        "1. **WebSense** — decide if retrieval needed\n"
        "2. **Google Lens** — image→visual matches\n"
        "3. **Textual Enhancer** — Wikipedia context\n"
        "4. **Visual Enhancer** — reference images\n"
        "5. **Gemini 2.5 Flash Lite** — final answer from pixels"
    )
    st.divider()

    missing = []
    if not GOOGLE_API_KEY: missing.append("GOOGLE_API_KEY")
    if not SERP_API_KEY:  missing.append("SERP_API_KEY")
    if missing:
        st.error(f"⚠ Missing in .env: {', '.join(missing)}")
    else:
        st.success("✓ All API keys loaded")


# ── Kimi client ───────────────────────────────────────────────────────────────
@st.cache_resource
def configure_genai():
    genai.configure(api_key=GOOGLE_API_KEY)
    return True  # just a trigger so cache_resource works


# ── Helpers ───────────────────────────────────────────────────────────────────
def image_to_base64(img: Image.Image, max_size: int = 1024) -> str:
    """Resize and encode. Keeps quality for the query image but caps at 1024px
    so Kimi's context window isn't overwhelmed before we even add ref images."""
    w, h = img.size
    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def url_to_base64(url: str, max_size: int = 512) -> tuple[str | None, str | None]:
    """
    Download an image URL, resize to max_size on longest edge, return (base64, mime).
    Gemini 2.5 Flash Lite silently drops responses when total image payload is too large,
    so we aggressively resize reference images before injecting them.
    """
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True,
                      headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        ct = r.headers.get("content-type", "image/jpeg").split(";")[0]
        if "image" not in ct:
            return None, None

        # Resize to keep payload small — Kimi chokes on large multi-image context
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        w, h = img.size
        if max(w, h) > max_size:
            scale = max_size / max(w, h)
            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=75)
        return base64.b64encode(buf.getvalue()).decode(), "image/jpeg"
    except Exception:
        return None, None


# ── Step 1: WebSense — does this query need retrieval? ────────────────────────
def websense_gate(image: Image.Image, question: str) -> tuple[bool, str, str]:
    """
    Use Gemini Flash (fast + cheap) as the WebSense gate — it just decides
    whether retrieval is needed. Gemini 2.5 Flash Lite is reserved for the heavy final step.
    Returns (needs_retrieval, reason, search_hint)
    """
    configure_genai()
    img_b64 = image_to_base64(image)

    prompt = (
        "You are WebSense, a gating module. Look at the image and the user's question.\n"
        "Decide: does answering this question require retrieving up-to-date web information "
        "(e.g. identifying a specific person, product, brand, recent event, or entity "
        "you may not recognise)?\n\n"
        f"Question: {question}\n\n"
        "Respond ONLY with valid JSON, nothing else:\n"
        '{"needs_retrieval": true, "reason": "one sentence", "search_hint": "visual descriptors for Google Lens"}'
    )

    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction="You are a precise JSON-only gating module. Never output anything except valid JSON."
    )
    resp = model.generate_content([
        {"mime_type": "image/jpeg", "data": img_b64},
        prompt
    ])
    raw = (resp.text or "").strip().replace("```json", "").replace("```", "").strip()
    try:
        data = json.loads(raw)
        return bool(data.get("needs_retrieval", True)), data.get("reason", ""), data.get("search_hint", question)
    except Exception:
        return True, "Could not parse WebSense response — defaulting to retrieval.", question


# ── Step 2: Google Lens via SerpAPI ──────────────────────────────────────────
def upload_to_imgbb(image: Image.Image) -> str:
    """
    SerpAPI Google Lens requires a PUBLIC URL — it does NOT accept file uploads.
    We use ImgBB's free anonymous upload endpoint (no API key needed for base64 upload)
    to get a temporary public URL, then pass that to SerpAPI.
    Returns the public image URL.
    """
    buf = io.BytesIO()
    # Resize to max 1024px to keep upload fast
    w, h = image.size
    if max(w, h) > 1024:
        scale = 1024 / max(w, h)
        image = image.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    image.save(buf, format="JPEG", quality=88)
    b64 = base64.b64encode(buf.getvalue()).decode()

    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

    if IMGBB_API_KEY:
        # Use ImgBB API with key (more reliable, images persist longer)
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": IMGBB_API_KEY, "image": b64, "expiration": 600},
            timeout=20
        )
        resp.raise_for_status()
        return resp.json()["data"]["url"]
    else:
        # Fallback: use freeimage.host anonymous upload (no key needed)
        resp = requests.post(
            "https://freeimage.host/api/1/upload",
            data={"key": "6d207e02198a847aa98d0a2a901485a5", "action": "upload", "source": b64, "format": "json"},
            timeout=20
        )
        resp.raise_for_status()
        return resp.json()["image"]["url"]


def google_lens_search(image: Image.Image, num_results: int = 3) -> dict:
    """
    SerpAPI Google Lens only accepts a public image URL (not file uploads).
    Flow: PIL Image → upload to ImgBB → get public URL → pass to SerpAPI.
    """
    # Step 1: Get a public URL for the image
    public_url = upload_to_imgbb(image)

    # Step 2: Call SerpAPI with the URL
    params = {
        "engine": "google_lens",
        "url": public_url,
        "api_key": SERP_API_KEY,
    }
    resp = requests.get("https://serpapi.com/search", params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # Extract entity name from knowledge graph
    entity_name = ""
    kg = data.get("knowledge_graph", [])
    if isinstance(kg, list) and kg:
        entity_name = kg[0].get("title", "")
    elif isinstance(kg, dict):
        entity_name = kg.get("title", "")

    # Fall back to first visual match title if no knowledge graph
    if not entity_name:
        matches = data.get("visual_matches", [])
        if matches:
            entity_name = matches[0].get("title", "")

    visual_matches = data.get("visual_matches", [])[:num_results]

    return {
        "entity_name": entity_name,
        "visual_matches": visual_matches,
        "raw": data,
        "public_url": public_url,
    }


# ── Step 3: Textual Prompt Enhancer — Wikipedia summary ──────────────────────
def fetch_wikipedia_summary(entity_name: str) -> str:
    if not entity_name:
        return ""
    try:
        url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(entity_name)
        r = requests.get(url, timeout=8, headers={"User-Agent": "ROSE-App/1.0"})
        if r.status_code == 200:
            return r.json().get("extract", "")
    except Exception:
        pass
    return ""


# ── Step 3b: Live web search — SerpAPI Google Search ─────────────────────────
def fetch_web_search_context(entity_name: str, question: str) -> str:
    """
    After Google Lens identifies the entity, run a targeted Google Search
    combining entity_name + question to pull live reviews, pricing, news etc.
    This is the layer that Wikipedia cannot provide for new/recent products.
    Returns a concatenated string of top snippets.
    """
    if not entity_name or not SERP_API_KEY:
        return ""
    try:
        search_query = f"{entity_name} {question}"
        params = {
            "engine": "google",
            "q": search_query,
            "api_key": SERP_API_KEY,
            "num": 5,
        }
        resp = requests.get("https://serpapi.com/search", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        snippets = []

        # Featured snippet / answer box — always first if present
        if data.get("answer_box"):
            ab = data["answer_box"]
            ab_text = ab.get("answer") or ab.get("snippet") or ab.get("result") or ""
            if ab_text:
                snippets.append(f"[Featured] {ab_text}")

        # Top organic results
        for r in data.get("organic_results", [])[:5]:
            title   = r.get("title", "")
            snippet = r.get("snippet", "")
            if snippet:
                snippets.append(f"[{title}] {snippet}")

        return "\n\n".join(snippets)
    except Exception as e:
        return f"Web search failed: {e}"


# ── Step 4 + 5: Visual Prompt Enhancer + Gemini 2.5 Flash Lite final answer ────────────
def gemma_with_visual_context(
    original_image: Image.Image,
    question: str,
    entity_name: str,
    wiki_text: str,
    ref_image_urls: list[str],
    inject_wiki: bool,
    web_search_text: str = "",
) -> tuple[str, str]:
    """
    Gemini 2.5 Flash Lite via Google AI Studio (Gemini API).
    - Accepts up to 16 images per request natively.
    - We pass: original image + up to 3 resized ref images + text context.
    - Uses google-generativeai SDK (not OpenAI-compat layer, which is flaky for Gemma).
    Returns (answer, debug_info).
    """
    configure_genai()
    orig_b64 = image_to_base64(original_image)

    # ── Build system instruction ──────────────────────────────────────────────
    sys_parts = [
        "You are a multimodal vision assistant implementing the VERA framework "
        "You receive: (1) a query image, (2) reference images from Google Lens, "
        "(3) optional Wikipedia context. Use ALL of it to answer precisely.",
        "Never claim you cannot see the images. Be specific and factual.",
    ]
    if entity_name:
        sys_parts.append(f"Google Lens identified the entity as: {entity_name}")
    if inject_wiki and wiki_text:
        sys_parts.append(f"Wikipedia summary:\n{wiki_text[:1500]}")
    if web_search_text:
        sys_parts.append(
            f"LIVE WEB SEARCH RESULTS (retrieved now, use this for reviews, pricing, recent news):\n{web_search_text}"
        )
    system_instruction = "\n\n".join(sys_parts)

    # ── Download + resize reference images ────────────────────────────────────
    ref_parts = []
    for url in ref_image_urls:
        b64, ct = url_to_base64(url, max_size=512)
        if b64:
            ref_parts.append({"mime_type": ct or "image/jpeg", "data": b64})
    injected_count = len(ref_parts)

    # ── Build content list for Gemma ──────────────────────────────────────────
    # Gemma 3 handles interleaved text + image parts well.
    # Order: instruction text → query image → ref images → final question.
    content_parts = []

    intro = (
        f"The following is my query image. After it, I have provided {injected_count} "
        f"reference image(s) retrieved from Google Lens for visual context.\n\n"
        f"Question: {question}"
        if injected_count else
        f"Here is my query image.\n\nQuestion: {question}"
    )
    content_parts.append(intro)
    content_parts.append({"mime_type": "image/jpeg", "data": orig_b64})

    for rp in ref_parts:
        content_parts.append(rp)

    content_parts.append(
        "Using the query image, the reference images above, and the context in your system "
        "instructions — answer the question now. Be thorough and specific."
    )

    # ── Primary call: Gemini 2.5 Flash Lite ─────────────────────────────────────────────
    model = genai.GenerativeModel(
        model_name="gemini-2.5-flash-lite",
        system_instruction=system_instruction,
        generation_config=genai.types.GenerationConfig(
            max_output_tokens=1500,
            temperature=0.2,   # lower temp = more factual
        )
    )

    debug = f"model=gemini-2.5-flash-lite | ref_images={injected_count}"
    answer = ""

    try:
        resp = model.generate_content(content_parts)
        answer = (resp.text or "").strip()
        debug += f" | finish={resp.candidates[0].finish_reason if resp.candidates else 'unknown'}"
    except Exception as e:
        debug += f" | primary_error={e}"

    # ── Fallback 1: text-only if blank (ref images may have failed) ───────────
    if not answer:
        fallback_parts = [
            f"Reference images unavailable — using text context only.\n\n"
            f"Entity (Google Lens): {entity_name or 'unknown'}\n"
            f"Wikipedia: {wiki_text[:800] if wiki_text else 'N/A'}\n\n"
            f"Question: {question}",
            {"mime_type": "image/jpeg", "data": orig_b64},
            "Answer the question using the image and context above."
        ]
        try:
            fb = model.generate_content(fallback_parts)
            answer = (fb.text or "").strip()
            debug += " | ⚠ text-only fallback used"
        except Exception as e2:
            debug += f" | fallback_error={e2}"

    # ── Fallback 2: gemini-2.5-flash-lite if primary call fails ─────────────
    if not answer:
        try:
            flash = genai.GenerativeModel(
                model_name="gemini-2.5-flash-lite",
                system_instruction=system_instruction,
            )
            fb2_parts = [
                f"Entity: {entity_name or 'unknown'}. Wikipedia: {wiki_text[:600] if wiki_text else 'N/A'}.\n\nQuestion: {question}",
                {"mime_type": "image/jpeg", "data": orig_b64},
            ]
            fb2 = flash.generate_content(fb2_parts)
            answer = (fb2.text or "").strip()
            debug += " | ⚠ gemini-2.5-flash-lite emergency fallback"
        except Exception as e3:
            debug += f" | flash_fallback_error={e3}"

    if not answer:
        answer = (
            "⚠ All models returned empty responses. "
            "Check your GOOGLE_API_KEY and ensure gemini-2.5-flash-lite is available on your API key."
        )

    return answer, debug
# ── Pipeline UI ───────────────────────────────────────────────────────────────
STEPS = [
    ("🔍", "WebSense"),
    ("🌐", "Google Lens"),
    ("📖", "Text Enhance"),
    ("🖼", "Visual Inject"),
    ("🤖", "Gemini 2.5 Flash Lite"),
]

def render_pipeline(active: int = -1, done_up_to: int = -1):
    """Render the 5-step pipeline. done_up_to=-1 means all idle."""
    html = '<div class="pipeline">'
    for i, (icon, label) in enumerate(STEPS):
        if i < done_up_to:
            cls = "done"
        elif i == active:
            cls = "active"
        else:
            cls = "idle"
        html += f'<div class="p-step {cls}"><span class="icon">{icon}</span><span class="label">{label}</span></div>'
    html += '</div>'
    return html


# ── Main UI ───────────────────────────────────────────────────────────────────
uploaded_file = st.file_uploader(
    "Upload image",
    type=["jpg", "jpeg", "png", "webp"],
    label_visibility="collapsed"
)

if uploaded_file:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, use_container_width=True, caption="Query image")

question = st.text_input(
    "Your question",
    placeholder="Who is this person? What product is this? What brand is on this packaging?",
    disabled=not uploaded_file
)

col1, col2 = st.columns([1, 4])
with col1:
    ask_clicked = st.button(
        "Ask ↗",
        type="primary",
        disabled=not (uploaded_file and question and GOOGLE_API_KEY and SERP_API_KEY)
    )

if not GOOGLE_API_KEY or not SERP_API_KEY:
    missing = [k for k, v in {"GOOGLE_API_KEY": GOOGLE_API_KEY, "SERP_API_KEY": SERP_API_KEY}.items() if not v]
    st.markdown(
        f'<div class="error-box">⚠ Missing API keys: {", ".join(missing)}<br>'
        f'Add them to your .env file.</div>',
        unsafe_allow_html=True
    )

# ── On Ask ────────────────────────────────────────────────────────────────────
if ask_clicked and uploaded_file and question and GOOGLE_API_KEY and SERP_API_KEY:

    pipeline_slot = st.empty()

    try:
        # ── Step 1: WebSense ──────────────────────────────────────────────────
        pipeline_slot.markdown(render_pipeline(active=0, done_up_to=0), unsafe_allow_html=True)

        needs_retrieval = True
        ws_reason = ""
        search_hint = question

        if websense_enabled:
            with st.spinner("WebSense: analysing query…"):
                needs_retrieval, ws_reason, search_hint = websense_gate(image, question)

        pipeline_slot.markdown(render_pipeline(active=1, done_up_to=1), unsafe_allow_html=True)

        # Show WebSense decision
        ws_html = (
            f'<div class="section-card">'
            f'<div class="section-label">① WebSense Decision</div>'
        )
        if websense_enabled:
            badge = '<span class="ws-needed">⟳ Retrieval needed</span>' if needs_retrieval \
                    else '<span class="ws-skip">✓ No retrieval needed</span>'
            ws_html += f'{badge} &nbsp; <span style="color:#5a5048;font-size:12px;font-family:\'IBM Plex Mono\',monospace">{ws_reason}</span>'
        else:
            ws_html += '<span class="ws-needed">⟳ WebSense disabled — always retrieving</span>'
        ws_html += '</div>'
        st.markdown(ws_html, unsafe_allow_html=True)

        entity_name = ""
        wiki_text   = ""
        ref_urls    = []
        ref_display = []   # (url, title) for UI

        if needs_retrieval:
            # ── Step 2: Google Lens ───────────────────────────────────────────
            pipeline_slot.markdown(render_pipeline(active=1, done_up_to=1), unsafe_allow_html=True)
            with st.spinner("Google Lens: visual search…"):
                lens = google_lens_search(image, num_results=num_ref_images)

            entity_name = lens["entity_name"]
            visual_matches = lens["visual_matches"]
            ref_urls    = [m.get("thumbnail", m.get("image", "")) for m in visual_matches if m.get("thumbnail") or m.get("image")]
            ref_display = [(m.get("thumbnail", m.get("image", "")), m.get("title", "")[:30]) for m in visual_matches]

            pipeline_slot.markdown(render_pipeline(active=2, done_up_to=2), unsafe_allow_html=True)

            # Show Lens results
            lens_html = '<div class="section-card"><div class="section-label">② Google Lens — Visual Matches</div>'
            if entity_name:
                lens_html += f'<p style="margin:0 0 10px;color:#7a6e60;font-size:12px;font-family:\'IBM Plex Mono\',monospace">Identified entity:</p>'
                lens_html += f'<span class="entity-chip">🏷 {entity_name}</span>'
            lens_html += '</div>'
            st.markdown(lens_html, unsafe_allow_html=True)

            # Show reference image thumbnails
            if ref_display:
                img_cols = st.columns(min(len(ref_display), 5))
                for col, (url, title) in zip(img_cols, ref_display):
                    if url:
                        with col:
                            try:
                                st.image(url, caption=title, use_container_width=True)
                            except Exception:
                                pass

            # ── Step 3: Textual Prompt Enhancer ──────────────────────────────
            pipeline_slot.markdown(render_pipeline(active=2, done_up_to=2), unsafe_allow_html=True)
            if inject_wiki and entity_name:
                with st.spinner(f"Fetching Wikipedia: {entity_name}…"):
                    wiki_text = fetch_wikipedia_summary(entity_name)

            if wiki_text:
                st.markdown(
                    f'<div class="section-card">'
                    f'<div class="section-label">③ Textual Prompt Enhancer — Wikipedia</div>'
                    f'<p style="color:#7a6e60;font-size:13px;line-height:1.6;font-family:Lora,serif;margin:0">{wiki_text[:400]}…</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

            # ── Step 3b: Live Web Search using identified entity ──────────────
            web_search_text = ""
            if entity_name:
                with st.spinner(f"Live web search: '{entity_name} + {question[:40]}…'"):
                    web_search_text = fetch_web_search_context(entity_name, question)

            if web_search_text and "Web search failed" not in web_search_text:
                preview = web_search_text[:600] + "…" if len(web_search_text) > 600 else web_search_text
                st.markdown(
                    f'<div class="section-card">'
                    f'<div class="section-label">③b Live Web Search — Real-time Context</div>'
                    f'<p style="color:#7a6e60;font-size:12px;line-height:1.7;font-family:\'IBM Plex Mono\',monospace;margin:0;white-space:pre-wrap">{preview}</p>'
                    f'</div>',
                    unsafe_allow_html=True
                )

        # ── Step 4 + 5: Visual injection + Gemini ────────────────────────────
        pipeline_slot.markdown(render_pipeline(active=3, done_up_to=3), unsafe_allow_html=True)

        st.markdown(
            f'<div class="section-card">'
            f'<div class="section-label">④ Visual Prompt Enhancer</div>'
            f'<p style="color:#7a6e60;font-size:12px;font-family:\'IBM Plex Mono\',monospace;margin:0">'
            f'Injecting {len(ref_urls)} reference image(s) into Gemini 2.5 Flash Lite context…</p>'
            f'</div>',
            unsafe_allow_html=True
        )

        pipeline_slot.markdown(render_pipeline(active=4, done_up_to=4), unsafe_allow_html=True)

        with st.spinner("Gemini 2.5 Flash Lite reasoning from pixels…"):
            answer, debug_info = gemma_with_visual_context(
                original_image=image,
                question=question,
                entity_name=entity_name,
                wiki_text=wiki_text,
                ref_image_urls=ref_urls,
                inject_wiki=inject_wiki,
                web_search_text=web_search_text,
            )

        # All done
        pipeline_slot.markdown(render_pipeline(active=-1, done_up_to=5), unsafe_allow_html=True)

        # ── Final Answer ──────────────────────────────────────────────────────
        st.markdown(
            f'<div class="answer-box">'
            f'<div class="answer-label">✦ Gemini 2.5 Flash Lite — ROSE Answer</div>'
            f'{answer}'
            f'</div>',
            unsafe_allow_html=True
        )

        # ── Debug info (collapsible) ──────────────────────────────────────────
        with st.expander("🔧 Debug info", expanded=False):
            st.code(debug_info, language=None)

    except Exception as e:
        pipeline_slot.empty()
        st.markdown(
            f'<div class="error-box">⚠ {type(e).__name__}: {e}</div>',
            unsafe_allow_html=True
        )