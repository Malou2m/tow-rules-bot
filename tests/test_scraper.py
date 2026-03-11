"""
Unit tests for pipeline/scraper.py checkpoint mechanism.

We test only the pure Python helpers (load_checkpoint, append_checkpoint)
since the Playwright-dependent functions (collect_urls, scrape_page, scrape_all)
require a live browser and are covered by integration/manual testing.
"""

import asyncio
import json
from pathlib import Path

import pytest

from pipeline.scraper import append_checkpoint, load_checkpoint


# ── load_checkpoint ───────────────────────────────────────────────────────────

class TestLoadCheckpoint:
    def test_returns_empty_when_file_does_not_exist(self, tmp_path, monkeypatch):
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", tmp_path / "checkpoint.jsonl")
        paths, results = load_checkpoint()
        assert paths == set()
        assert results == []

    def test_returns_scraped_paths_and_pages(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        pages = [
            {"path": "/combat", "url": "https://tow.whfb.app/combat",
             "title": "Combat", "sections": [], "full_text": "Combat rules."},
            {"path": "/magic",  "url": "https://tow.whfb.app/magic",
             "title": "Magic",  "sections": [], "full_text": "Magic rules."},
        ]
        checkpoint.write_text("\n".join(json.dumps(p) for p in pages) + "\n")
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        paths, results = load_checkpoint()

        assert paths == {"/combat", "/magic"}
        assert len(results) == 2

    def test_skips_blank_lines(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        page = {"path": "/movement", "url": "https://tow.whfb.app/movement",
                "title": "Movement", "sections": [], "full_text": "Move rules."}
        checkpoint.write_text(f"\n{json.dumps(page)}\n\n")
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        paths, results = load_checkpoint()
        assert paths == {"/movement"}
        assert len(results) == 1

    def test_skips_corrupted_lines(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        page = {"path": "/shooting", "url": "https://tow.whfb.app/shooting",
                "title": "Shooting", "sections": [], "full_text": "Shoot rules."}
        # Simulate a crash mid-write: valid line, then a truncated line
        checkpoint.write_text(json.dumps(page) + "\n" + '{"path": "/broken", "url":')
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        paths, results = load_checkpoint()
        assert paths == {"/shooting"}
        assert len(results) == 1

    def test_deduplicates_by_path_keeping_last(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        page_v1 = {"path": "/combat", "url": "https://tow.whfb.app/combat",
                   "title": "Combat v1", "sections": [], "full_text": "Old text."}
        page_v2 = {"path": "/combat", "url": "https://tow.whfb.app/combat",
                   "title": "Combat v2", "sections": [], "full_text": "New text."}
        checkpoint.write_text(json.dumps(page_v1) + "\n" + json.dumps(page_v2) + "\n")
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        paths, results = load_checkpoint()
        assert len(paths) == 1
        assert len(results) == 1
        assert results[0]["title"] == "Combat v2"

    def test_handles_missing_path_key_gracefully(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        # A line that is valid JSON but missing the "path" key
        checkpoint.write_text('{"url": "https://tow.whfb.app/x", "title": "X"}\n')
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        paths, results = load_checkpoint()
        assert paths == set()
        assert results == []


# ── append_checkpoint ─────────────────────────────────────────────────────────

class TestAppendCheckpoint:
    async def test_creates_file_and_writes_page(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        page = {"path": "/combat", "url": "https://tow.whfb.app/combat",
                "title": "Combat", "sections": [], "full_text": "Rules."}
        await append_checkpoint(asyncio.Lock(), page)

        assert checkpoint.exists()
        lines = [l for l in checkpoint.read_text().splitlines() if l.strip()]
        assert len(lines) == 1
        assert json.loads(lines[0]) == page

    async def test_appends_multiple_pages(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        pages = [
            {"path": f"/rule-{i}", "url": f"https://tow.whfb.app/rule-{i}",
             "title": f"Rule {i}", "sections": [], "full_text": f"Text {i}."}
            for i in range(5)
        ]
        lock = asyncio.Lock()
        for page in pages:
            await append_checkpoint(lock, page)

        lines = [l for l in checkpoint.read_text().splitlines() if l.strip()]
        assert len(lines) == 5
        assert [json.loads(l)["path"] for l in lines] == [f"/rule-{i}" for i in range(5)]

    async def test_appended_page_is_readable_by_load_checkpoint(self, tmp_path, monkeypatch):
        checkpoint = tmp_path / "checkpoint.jsonl"
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        page = {"path": "/magic", "url": "https://tow.whfb.app/magic",
                "title": "Magic", "sections": [], "full_text": "Spell rules."}
        await append_checkpoint(asyncio.Lock(), page)

        paths, results = load_checkpoint()
        assert "/magic" in paths
        assert results[0]["title"] == "Magic"

    def test_concurrent_appends_all_written(self, tmp_path, monkeypatch):
        """All concurrent coroutines must write without interleaving or data loss."""
        checkpoint = tmp_path / "checkpoint.jsonl"
        monkeypatch.setattr("pipeline.scraper.CHECKPOINT_FILE", checkpoint)

        async def run_concurrent():
            lock = asyncio.Lock()
            pages = [
                {"path": f"/page-{i}", "url": f"https://tow.whfb.app/page-{i}",
                 "title": f"Page {i}", "sections": [], "full_text": f"Content {i}."}
                for i in range(20)
            ]
            await asyncio.gather(*[append_checkpoint(lock, p) for p in pages])

        asyncio.run(run_concurrent())

        lines = [l for l in checkpoint.read_text().splitlines() if l.strip()]
        assert len(lines) == 20
        # Every line must be valid JSON
        for line in lines:
            json.loads(line)
