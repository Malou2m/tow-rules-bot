"""
Unit tests for pipeline/ingest.py

We test:
- _chunk_id: deterministic, hex string, correct length
- get_or_create_index: creates index when missing, skips creation when present
- upsert_chunks: correct batching, metadata truncation, idempotent IDs
- All Pinecone calls are mocked — no real API calls are made.
"""

from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.embedder import EmbeddedChunk
from pipeline.ingest import UPSERT_BATCH_SIZE, _chunk_id, get_or_create_index, upsert_chunks


# ── _chunk_id ─────────────────────────────────────────────────────────────────

class TestChunkId:
    def test_returns_32_char_hex_string(self):
        cid = _chunk_id("some text")
        assert len(cid) == 32
        assert all(c in "0123456789abcdef" for c in cid)

    def test_deterministic_for_same_input(self):
        assert _chunk_id("hello") == _chunk_id("hello")

    def test_different_for_different_input(self):
        assert _chunk_id("text one") != _chunk_id("text two")


# ── get_or_create_index ───────────────────────────────────────────────────────

class TestGetOrCreateIndex:
    def _mock_pc(self, existing_indexes: list[str]):
        pc = MagicMock()
        # MagicMock(name=...) sets the mock's display name, NOT the .name attribute.
        # We must set .name explicitly after construction.
        mock_entries = []
        for n in existing_indexes:
            entry = MagicMock()
            entry.name = n
            mock_entries.append(entry)
        pc.list_indexes.return_value = mock_entries
        pc.Index.return_value = MagicMock()
        return pc

    def test_creates_index_when_not_present(self):
        pc = self._mock_pc([])
        get_or_create_index(pc, "tow-rules")
        pc.create_index.assert_called_once()
        call_kwargs = pc.create_index.call_args
        assert call_kwargs.kwargs["name"] == "tow-rules"

    def test_skips_creation_when_index_exists(self):
        pc = self._mock_pc(["tow-rules"])
        get_or_create_index(pc, "tow-rules")
        pc.create_index.assert_not_called()

    def test_returns_index_object(self):
        pc = self._mock_pc(["tow-rules"])
        idx = get_or_create_index(pc, "tow-rules")
        assert idx is pc.Index.return_value


# ── upsert_chunks ─────────────────────────────────────────────────────────────

def _make_embedded(n: int) -> list[EmbeddedChunk]:
    return [
        EmbeddedChunk(
            text=f"Rule content {i}",
            embedding=[float(i)] * 1536,
            metadata={"source": "tow.whfb.app", "title": f"Rule {i}", "url": f"https://tow.whfb.app/rule-{i}"},
        )
        for i in range(n)
    ]


class TestUpsertChunks:
    def _setup_env(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_API_KEY", "test-key")
        monkeypatch.setenv("PINECONE_INDEX_NAME", "tow-rules")

    def test_upserts_correct_number_of_vectors(self, monkeypatch):
        self._setup_env(monkeypatch)
        embedded = _make_embedded(5)
        mock_index = MagicMock()

        with patch("pipeline.ingest.Pinecone") as mock_pc_cls:
            mock_pc = MagicMock()
            existing = MagicMock(); existing.name = "tow-rules"
            mock_pc.list_indexes.return_value = [existing]
            mock_pc.Index.return_value = mock_index
            mock_pc_cls.return_value = mock_pc

            total = upsert_chunks(embedded)

        assert total == 5

    def test_batches_upsert_calls(self, monkeypatch):
        self._setup_env(monkeypatch)
        n = UPSERT_BATCH_SIZE + 10
        embedded = _make_embedded(n)
        mock_index = MagicMock()

        with patch("pipeline.ingest.Pinecone") as mock_pc_cls:
            mock_pc = MagicMock()
            existing = MagicMock(); existing.name = "tow-rules"
            mock_pc.list_indexes.return_value = [existing]
            mock_pc.Index.return_value = mock_index
            mock_pc_cls.return_value = mock_pc

            upsert_chunks(embedded)

        assert mock_index.upsert.call_count == 2  # two batches

    def test_vector_ids_are_deterministic(self, monkeypatch):
        self._setup_env(monkeypatch)
        embedded = _make_embedded(3)
        captured_vectors = []
        mock_index = MagicMock()
        mock_index.upsert.side_effect = lambda vectors: captured_vectors.extend(vectors)

        with patch("pipeline.ingest.Pinecone") as mock_pc_cls:
            mock_pc = MagicMock()
            existing = MagicMock(); existing.name = "tow-rules"
            mock_pc.list_indexes.return_value = [existing]
            mock_pc.Index.return_value = mock_index
            mock_pc_cls.return_value = mock_pc

            upsert_chunks(embedded)

        ids = [v["id"] for v in captured_vectors]
        # Re-running should produce the same IDs
        expected_ids = [_chunk_id(e.text) for e in embedded]
        assert ids == expected_ids

    def test_metadata_text_is_truncated_to_1000_chars(self, monkeypatch):
        self._setup_env(monkeypatch)
        long_text = "x" * 5000
        embedded = [EmbeddedChunk(text=long_text, embedding=[0.1] * 1536,
                                  metadata={"source": "tow.whfb.app", "title": "Rule"})]
        captured_vectors = []
        mock_index = MagicMock()
        mock_index.upsert.side_effect = lambda vectors: captured_vectors.extend(vectors)

        with patch("pipeline.ingest.Pinecone") as mock_pc_cls:
            mock_pc = MagicMock()
            existing = MagicMock(); existing.name = "tow-rules"
            mock_pc.list_indexes.return_value = [existing]
            mock_pc.Index.return_value = mock_pc.Index.return_value
            mock_pc.Index.return_value = mock_index
            mock_pc_cls.return_value = mock_pc

            upsert_chunks(embedded)

        stored_text = captured_vectors[0]["metadata"]["text"]
        assert len(stored_text) <= 1000

    def test_empty_input_returns_zero(self, monkeypatch):
        self._setup_env(monkeypatch)
        mock_index = MagicMock()

        with patch("pipeline.ingest.Pinecone") as mock_pc_cls:
            mock_pc = MagicMock()
            existing = MagicMock(); existing.name = "tow-rules"
            mock_pc.list_indexes.return_value = [existing]
            mock_pc.Index.return_value = mock_index
            mock_pc_cls.return_value = mock_pc

            total = upsert_chunks([])

        assert total == 0
        mock_index.upsert.assert_not_called()
