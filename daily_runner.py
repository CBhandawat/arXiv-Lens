"""
daily_runner.py — Entry point for GitHub Actions scheduled run.

Runs daily at 16:15 IST (10:45 UTC).

Produces 5 podcast episodes and delivers them via WhatsApp directly as audio
files using WASenderAPI. No S3 or cloud storage needed — audio is uploaded
to WASenderAPI's temporary media hosting and delivered as a voice note.
"""

import os
import time
import json
from datetime import date

from dotenv import load_dotenv
load_dotenv()

from pipeline.scraper import scrape_recent, fetch_abstract
from pipeline.scriptwriter import generate_script
from pipeline.tts import synthesize_turn
from pipeline.audio_merge import merge_audio
from pipeline.whatsapp import send_whatsapp_digest

# ── Config ────────────────────────────────────────────────────────────────────

CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]
PAPERS_PER_CAT = 3
TARGET_EPISODES = 5


def run_daily():
    print(f"[runner] ArXiv Cast daily run — {date.today()}")

    episodes = []

    # ── Step 1: Scrape candidates ─────────────────────────────────────────────
    candidates = []
    for cat in CATEGORIES:
        papers = scrape_recent(cat, max_papers=PAPERS_PER_CAT)
        candidates.extend(papers)
        print(f"[runner] Scraped {len(papers)} from {cat}")

    if not candidates:
        print("[runner] No papers scraped. Exiting.")
        return

    # ── Step 2: Generate + synthesize each episode ────────────────────────────
    for paper in candidates:
        if len(episodes) >= TARGET_EPISODES:
            break

        print(f"[runner] Processing: {paper['title'][:60]}")

        # Fetch abstract
        abstract = fetch_abstract(paper["arxiv_url"])
        if not abstract:
            print(f"[runner] No abstract, skipping")
            continue

        # Generate dialogue script
        try:
            script = generate_script(paper["title"], abstract)
        except Exception as e:
            print(f"[runner] Script failed: {type(e).__name__}: {e}")
            continue

        # TTS synthesis
        try:
            chunks = []
            for turn in script["turns"]:
                chunk = synthesize_turn(turn["text"], turn["host"])
                chunks.append(chunk)
                time.sleep(0.3)
        except Exception as e:
            print(f"[runner] TTS failed: {e}")
            continue

        # Merge audio
        try:
            mp3_bytes = merge_audio(chunks, script["turns"])
        except Exception as e:
            print(f"[runner] Merge failed: {e}")
            continue

        episodes.append({
            "title": paper["title"],
            "arxiv_url": paper["arxiv_url"],
            "mp3_bytes": mp3_bytes,  # uploaded to WASenderAPI in whatsapp.py
        })

        print(f"[runner] ✓ Episode {len(episodes)}/{TARGET_EPISODES} ready")

    if not episodes:
        print("[runner] No episodes generated.")
        return

    # ── Step 3: Send via WhatsApp (WASenderAPI) ───────────────────────────────
    print(f"[runner] Sending {len(episodes)} episodes via WhatsApp...")
    try:
        send_whatsapp_digest(episodes)
        print("[runner] ✓ Digest delivered successfully")
    except Exception as e:
        print(f"[runner] WhatsApp delivery failed: {e}")

    return {
        "date": str(date.today()),
        "episodes": len(episodes),
    }


# ── Lambda handler (kept for compatibility) ───────────────────────────────────

def lambda_handler(event, context):
    result = run_daily()
    return {"statusCode": 200, "body": json.dumps(result)}


if __name__ == "__main__":
    run_daily()
