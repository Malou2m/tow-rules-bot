"""
Main pipeline entry point.

Run with:
    uv run python -m pipeline.run_pipeline

Flags:
    --force-scrape   Re-scrape tow.whfb.app even if cache exists
    --force-army     Re-fetch army data even if cache exists
    --skip-tow       Skip tow.whfb.app scraping (army data only)
    --skip-army      Skip old-world-builder data (rules only)
    --dry-run        Chunk + embed but do NOT upsert to Pinecone
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Load .env before importing submodules that read env vars
load_dotenv()

from pipeline.army_data import fetch_army_data
from pipeline.chunker import build_all_chunks
from pipeline.embedder import create_embeddings
from pipeline.ingest import upsert_chunks
from pipeline.scraper import scrape_all


def parse_args():
    parser = argparse.ArgumentParser(description="TOW Rules Bot — data ingestion pipeline")
    parser.add_argument("--force-scrape", action="store_true", help="Re-scrape tow.whfb.app")
    parser.add_argument("--force-army",   action="store_true", help="Re-fetch army data")
    parser.add_argument("--skip-tow",     action="store_true", help="Skip tow.whfb.app")
    parser.add_argument("--skip-army",    action="store_true", help="Skip old-world-builder data")
    parser.add_argument("--dry-run",      action="store_true", help="Embed but don't upsert")
    return parser.parse_args()


def main():
    args = parse_args()

    # Validate required env vars up-front
    missing = [k for k in ("OPENAI_API_KEY", "PINECONE_API_KEY", "PINECONE_INDEX_NAME")
               if not os.environ.get(k)]
    if missing and not args.dry_run:
        print(f"ERROR: Missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your keys.")
        sys.exit(1)

    # ── Step 1: Collect raw data ──────────────────────────────────────────────
    tow_pages = []
    if not args.skip_tow:
        print("\n── Step 1a: Scraping tow.whfb.app ──")
        tow_pages = asyncio.run(scrape_all(force=args.force_scrape))

    army_docs = []
    if not args.skip_army:
        print("\n── Step 1b: Fetching army data (old-world-builder) ──")
        army_docs = fetch_army_data(force=args.force_army)

    # ── Step 2: Chunk ─────────────────────────────────────────────────────────
    print("\n── Step 2: Chunking ──")
    chunks = build_all_chunks(tow_pages, army_docs)
    if not chunks:
        print("No chunks produced — nothing to do.")
        sys.exit(0)

    # ── Step 3: Embed ─────────────────────────────────────────────────────────
    print("\n── Step 3: Embedding ──")
    embedded = create_embeddings(chunks)

    # ── Step 4: Upsert ───────────────────────────────────────────────────────
    if args.dry_run:
        print("\n── Dry run: skipping Pinecone upsert ──")
        print(f"Would upsert {len(embedded)} vectors.")
    else:
        print("\n── Step 4: Upserting to Pinecone ──")
        upsert_chunks(embedded)

    print("\n✓ Pipeline complete.")


if __name__ == "__main__":
    main()
