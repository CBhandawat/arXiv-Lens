"""
daily_runner.py — Entry point for the AWS Lambda / ECS scheduled task.

Triggered by EventBridge at 07:00 UTC daily.
Produces 5 podcast episodes and delivers them via WhatsApp + Email.
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
from pipeline.uploader import upload_to_s3, get_existing_url
from pipeline.whatsapp import send_whatsapp_digest
from pipeline.emailer import send_email_digest


# ── Config ────────────────────────────────────────────────────────────────────
CATEGORIES = ["cs.AI", "cs.LG", "cs.CL"]   # rotated through to get variety
PAPERS_PER_CATEGORY = 3                      # scrape more than needed, pick best
TARGET_EPISODES = 5


def run_daily():
    print(f"[runner] ArXiv Cast daily run — {date.today()}")
    episodes = []

    # ── Step 1: Scrape enough papers ─────────────────────────────────────────
    candidates = []
    for cat in CATEGORIES:
        papers = scrape_recent(cat, max_papers=PAPERS_PER_CATEGORY)
        candidates.extend(papers)
        print(f"[runner] Scraped {len(papers)} from {cat}")

    if not candidates:
        print("[runner] No papers scraped. Exiting.")
        return

    # ── Step 2: Process up to TARGET_EPISODES ────────────────────────────────
    for paper in candidates:
        if len(episodes) >= TARGET_EPISODES:
            break

        arxiv_id = paper["arxiv_id"]
        print(f"[runner] Processing: {paper['title'][:60]}")

        # Check S3 cache — skip if already done today
        cached = get_existing_url(arxiv_id)
        if cached:
            print(f"[runner] Cache hit for {arxiv_id} — reusing")
            episodes.append({
                "title":     paper["title"],
                "authors":   paper.get("authors", ""),
                "arxiv_url": paper["arxiv_url"],
                "audio_url": cached,
            })
            continue

        # Fetch abstract
        abstract = fetch_abstract(paper["arxiv_url"])
        if not abstract:
            print(f"[runner] No abstract for {arxiv_id}, skipping")
            continue

        # Generate script
        try:
            script = generate_script(paper["title"], abstract)
        except Exception as e:
            print(f"[runner] Script generation failed: {e}")
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
            print(f"[runner] Audio merge failed: {e}")
            continue

        # Upload to S3
        try:
            audio_url = upload_to_s3(mp3_bytes, arxiv_id)
        except Exception as e:
            print(f"[runner] S3 upload failed: {e}")
            continue

        episodes.append({
            "title":     paper["title"],
            "authors":   paper.get("authors", ""),
            "arxiv_url": paper["arxiv_url"],
            "audio_url": audio_url,
        })
        print(f"[runner] ✓ Episode {len(episodes)}/{TARGET_EPISODES} ready")

    if not episodes:
        print("[runner] No episodes generated. Nothing to send.")
        return

    print(f"[runner] Generated {len(episodes)} episodes. Sending digest...")

    # ── Step 3: Deliver ───────────────────────────────────────────────────────
    errors = []

    try:
        send_whatsapp_digest(episodes)
    except Exception as e:
        errors.append(f"WhatsApp: {e}")
        print(f"[runner] WhatsApp send failed: {e}")

    try:
        send_email_digest(episodes)
    except Exception as e:
        errors.append(f"Email: {e}")
        print(f"[runner] Email send failed: {e}")

    if errors:
        print(f"[runner] Completed with errors: {errors}")
    else:
        print(f"[runner] ✓ Daily digest delivered successfully ({len(episodes)} episodes)")

    # Return structured result (useful when Lambda captures the response)
    return {
        "date":     str(date.today()),
        "episodes": len(episodes),
        "errors":   errors,
    }


# ── Lambda handler ────────────────────────────────────────────────────────────
def lambda_handler(event, context):
    """AWS Lambda entry point."""
    result = run_daily()
    return {
        "statusCode": 200,
        "body": json.dumps(result),
    }


if __name__ == "__main__":
    run_daily()
