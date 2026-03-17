"""
Unit tests for pipeline/chunker.py

We test:
- _token_split: correct window sizes, overlap, and edge cases
- chunk_tow_pages: section-aware splitting, fallback to full_text, short sections skipped
- chunk_army_docs: basic conversion, oversized docs split
- build_all_chunks: combination and count
"""

import pytest
from pipeline.chunker import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    ENCODER,
    Chunk,
    _token_split,
    build_all_chunks,
    chunk_army_docs,
    chunk_tow_pages,
)


# ── _token_split ──────────────────────────────────────────────────────────────

class TestTokenSplit:
    def test_short_text_returns_single_chunk(self):
        text = "This is a short sentence."
        result = _token_split(text, size=100, overlap=10)
        assert result == [text]

    def test_empty_text_returns_empty_list(self):
        result = _token_split("", size=100, overlap=10)
        assert result == []

    def test_splits_long_text_into_multiple_chunks(self):
        # Build a text that's definitely > 2 * CHUNK_SIZE tokens
        word = "rule " * (CHUNK_SIZE * 3)
        result = _token_split(word, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        assert len(result) > 1

    def test_each_chunk_is_within_size(self):
        word = "word " * (CHUNK_SIZE * 4)
        result = _token_split(word, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        for chunk in result:
            assert len(ENCODER.encode(chunk)) <= CHUNK_SIZE

    def test_overlap_means_adjacent_chunks_share_tokens(self):
        word = "token " * (CHUNK_SIZE * 3)
        result = _token_split(word, size=CHUNK_SIZE, overlap=CHUNK_OVERLAP)
        assert len(result) >= 2
        # The tail of chunk[0] and the head of chunk[1] share content
        tokens_0 = ENCODER.encode(result[0])
        tokens_1 = ENCODER.encode(result[1])
        shared = set(tokens_0[-CHUNK_OVERLAP:]) & set(tokens_1[:CHUNK_OVERLAP])
        assert len(shared) > 0

    def test_no_overlap_produces_non_overlapping_chunks(self):
        word = "x " * (CHUNK_SIZE * 2)
        result = _token_split(word, size=CHUNK_SIZE, overlap=0)
        total_tokens = sum(len(ENCODER.encode(c)) for c in result)
        original_tokens = len(ENCODER.encode(word))
        assert total_tokens == original_tokens


# ── chunk_tow_pages ───────────────────────────────────────────────────────────

class TestChunkTowPages:
    def _make_page(self, sections=None, full_text=None, title="Test Page", path="/test"):
        return {
            "url": f"https://tow.whfb.app{path}",
            "path": path,
            "title": title,
            "sections": sections,
            "full_text": full_text or "",
        }

    def test_basic_section_becomes_one_chunk(self):
        page = self._make_page(sections=[
            {"heading": "Movement", "text": "Units move a number of inches equal to their Move value."}
        ])
        chunks = chunk_tow_pages([page])
        assert len(chunks) == 1
        assert "Movement" in chunks[0].text
        assert chunks[0].metadata["url"] == "https://tow.whfb.app/test"
        assert chunks[0].metadata["section"] == "Movement"

    def test_short_section_under_30_chars_is_skipped(self):
        page = self._make_page(sections=[
            {"heading": "Note", "text": "See above."}  # < 30 chars
        ])
        chunks = chunk_tow_pages([page])
        assert len(chunks) == 0

    def test_oversized_section_is_split(self):
        long_text = "The unit moves. " * (CHUNK_SIZE * 2)
        page = self._make_page(sections=[
            {"heading": "Movement Rules", "text": long_text}
        ])
        chunks = chunk_tow_pages([page])
        assert len(chunks) > 1

    def test_falls_back_to_full_text_when_no_sections(self):
        page = self._make_page(sections=[], full_text="Fallback content for this rule page.")
        chunks = chunk_tow_pages([page])
        assert len(chunks) == 1
        assert "Fallback content" in chunks[0].text

    def test_empty_pages_produce_no_chunks(self):
        page = self._make_page(sections=[], full_text="")
        chunks = chunk_tow_pages([page])
        assert len(chunks) == 0

    def test_metadata_contains_required_keys(self):
        page = self._make_page(sections=[
            {"heading": "Combat", "text": "Roll to hit using your Weapon Skill (WS) value against the opponent."}
        ])
        chunks = chunk_tow_pages([page])
        assert len(chunks) == 1
        meta = chunks[0].metadata
        assert "source" in meta
        assert "url" in meta
        assert "title" in meta
        assert "section" in meta
        assert meta["source"] == "tow.whfb.app"

    def test_multiple_pages_accumulate_chunks(self):
        pages = [
            self._make_page(
                sections=[{"heading": f"Section {i}", "text": f"Content for section {i} with enough text."}],
                path=f"/section-{i}"
            )
            for i in range(5)
        ]
        chunks = chunk_tow_pages(pages)
        assert len(chunks) == 5


# ── chunk_army_docs ───────────────────────────────────────────────────────────

class TestChunkArmyDocs:
    def _make_doc(self, text, title="Swordsmen", army="Empire of Man", doc_type="unit"):
        return {"source": "old-world-builder", "type": doc_type, "title": title, "army": army, "text": text}

    def test_simple_unit_becomes_one_chunk(self):
        doc = self._make_doc("Unit: Swordsmen (Empire of Man)\nStats: WS: 3 | S: 3\nPoints: 60")
        chunks = chunk_army_docs([doc])
        assert len(chunks) == 1
        assert "Swordsmen" in chunks[0].text

    def test_metadata_includes_army_and_type(self):
        doc = self._make_doc("Unit: Handgunners\nStats: BS: 3")
        chunks = chunk_army_docs([doc])
        meta = chunks[0].metadata
        assert meta["army"] == "Empire of Man"
        assert meta["type"] == "unit"

    def test_very_short_text_is_skipped(self):
        doc = self._make_doc("Hi")  # < 20 chars
        chunks = chunk_army_docs([doc])
        assert len(chunks) == 0

    def test_oversized_doc_is_split(self):
        long_text = "rule description " * (CHUNK_SIZE * 2)
        doc = self._make_doc(long_text)
        chunks = chunk_army_docs([doc])
        assert len(chunks) > 1

    def test_empty_doc_list_returns_empty(self):
        assert chunk_army_docs([]) == []

    def test_url_defaults_to_old_world_builder(self):
        doc = self._make_doc("Unit: Knight\nPoints: 100")
        chunks = chunk_army_docs([doc])
        assert chunks[0].metadata["url"] == "https://old-world-builder.com"


# ── build_all_chunks ──────────────────────────────────────────────────────────

class TestBuildAllChunks:
    def test_combines_both_sources(self):
        tow_pages = [{
            "url": "https://tow.whfb.app/combat",
            "path": "/combat",
            "title": "Combat",
            "sections": [{"heading": "Combat", "text": "Roll to hit using WS against your opponent."}],
            "full_text": "",
        }]
        army_docs = [{"source": "old-world-builder", "type": "unit", "title": "Knight",
                      "army": "Bretonnia", "text": "Unit: Knight\nStats: WS: 4"}]
        chunks = build_all_chunks(tow_pages, army_docs)
        sources = {c.metadata["source"] for c in chunks}
        assert "tow.whfb.app" in sources
        assert "old-world-builder" in sources

    def test_empty_inputs_return_empty(self):
        assert build_all_chunks([], []) == []

    def test_chunk_count_is_sum_of_parts(self, capsys):
        tow_pages = [{
            "url": "https://tow.whfb.app/magic",
            "path": "/magic",
            "title": "Magic",
            "sections": [
                {"heading": "Casting", "text": "The wizard rolls two dice to cast a spell."},
                {"heading": "Dispelling", "text": "The opponent rolls two dice to dispel."},
            ],
            "full_text": "",
        }]
        army_docs = [
            {"source": "old-world-builder", "type": "spell", "title": "Fireball",
             "army": "Lore of Fire", "text": "Spell: Fireball\nCasting Value: 7\nEffect: Deals D6 hits."},
        ]
        chunks = build_all_chunks(tow_pages, army_docs)
        assert len(chunks) == 3
