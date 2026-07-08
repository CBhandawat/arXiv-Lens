"""
arXiv-Lens Daily Email Digest
------------------------------
Scrapes new CS papers from arXiv, summarizes them in plain English using
Groq (LLaMA 3.3 70B), stores them in the same Supabase table your
Streamlit app uses, and emails a digest of today's new papers.

Run manually:
    python email_digest.py

Run daily via GitHub Actions (see .github/workflows/daily_email.yml)
"""

import os
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from bs4 import BeautifulSoup
from groq import Groq
from supabase import create_client

# ---------- config (all from env vars / GitHub Actions secrets) ----------

GROQ_API_KEY = os.environ["GROQ_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ["SMTP_USER"]          # your gmail address
SMTP_PASS = os.environ["SMTP_PASS"]          # gmail App Password, not your login password
EMAIL_TO = os.environ.get("EMAIL_TO", SMTP_USER)

CATEGORIES = os.environ.get("ARXIV_CATEGORIES", "cs.AI,cs.CL,cs.LG").split(",")
MAX_PAPERS_PER_CATEGORY = int(os.environ.get("MAX_PAPERS", 10))

groq_client = Groq(api_key=GROQ_API_KEY)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- scraping ----------

def fetch_recent_papers(category: str, max_papers: int):
    """Scrape arXiv's 'recent' listing page for a category."""
    url = f"https://arxiv.org/list/{category}/recent"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    papers = []
    dts = soup.select("dl#articles > dt")
    dds = soup.select("dl#articles > dd")

    for dt, dd in zip(dts, dds):
        if len(papers) >= max_papers:
            break

        id_link = dt.select_one("a[title='Abstract']")
        if not id_link:
            continue
        arxiv_id = id_link.text.strip().replace("arXiv:", "")

        title_el = dd.select_one("div.list-title")
        abstract_el = dd.select_one("p.mathjax")
        authors_el = dd.select_one("div.list-authors")

        title = title_el.text.replace("Title:", "").strip() if title_el else ""
        abstract = abstract_el.text.strip() if abstract_el else ""
        authors = authors_el.text.replace("Authors:", "").strip() if authors_el else ""

        papers.append({
            "arxiv_id": arxiv_id,
            "arxiv_url": f"https://arxiv.org/abs/{arxiv_id}",
            "title": title,
            "authors": authors,
            "category": category,
            "abstract": abstract,
        })

    return papers


def already_seen(arxiv_id: str) -> bool:
    result = supabase.table("papers").select("arxiv_id").eq("arxiv_id", arxiv_id).execute()
    return len(result.data) > 0


# ---------- summarization ----------

SUMMARY_PROMPT = """Explain this research paper abstract in plain, simple English,
as if to a smart friend who is not in this specific field. 3-4 sentences max.
No jargon, no bullet points, just a clear plain-language explanation of what
the paper does and why it matters.

Title: {title}
Abstract: {abstract}
"""

def summarize(title: str, abstract: str) -> str:
    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "user", "content": SUMMARY_PROMPT.format(title=title, abstract=abstract)}
        ],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()


# ---------- pipeline ----------

def collect_new_summaries():
    new_papers = []

    for category in CATEGORIES:
        category = category.strip()
        papers = fetch_recent_papers(category, MAX_PAPERS_PER_CATEGORY)

        for paper in papers:
            if already_seen(paper["arxiv_id"]):
                continue

            summary = summarize(paper["title"], paper["abstract"])
            paper["summary"] = summary

            # store in the same table your Streamlit app reads from
            supabase.table("papers").insert(paper).execute()

            new_papers.append(paper)
            time.sleep(0.5)  # stay under Groq free-tier rate limit

    return new_papers


# ---------- email ----------

def build_email_html(papers):
    if not papers:
        return "<p>No new papers today.</p>"

    blocks = []
    for p in papers:
        blocks.append(f"""
        <div style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #e0e0e0;">
            <h3 style="margin:0 0 6px 0;font-size:16px;">
                <a href="{p['arxiv_url']}" style="text-decoration:none;color:#1a0dab;">{p['title']}</a>
            </h3>
            <p style="margin:0 0 6px 0;color:#666;font-size:12px;">{p['category']} &middot; {p['authors']}</p>
            <p style="margin:0;font-size:14px;line-height:1.5;">{p['summary']}</p>
        </div>
        """)

    return f"""
    <html><body style="font-family:Arial,sans-serif;max-width:640px;margin:auto;">
        <h2>arXiv-Lens Daily Digest</h2>
        <p style="color:#666;">{len(papers)} new paper(s) today.</p>
        {''.join(blocks)}
    </body></html>
    """


def send_email(html_body: str, paper_count: int):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"arXiv-Lens Digest — {paper_count} new paper(s)"
    msg["From"] = SMTP_USER
    msg["To"] = EMAIL_TO
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())


# ---------- entrypoint ----------

def main():
    new_papers = collect_new_summaries()
    html = build_email_html(new_papers)
    send_email(html, len(new_papers))
    print(f"Done. Emailed {len(new_papers)} new paper summaries to {EMAIL_TO}.")


if __name__ == "__main__":
    main()
