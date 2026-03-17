"""
Unit tests for pipeline/embedder.py

We test:
- create_embeddings: correct batching, output shape, retry on rate limit, failure after 3 attempts
- All OpenAI calls are mocked — no real API calls are made.
"""

import time
from unittest.mock import MagicMock, call, patch

import pytest

from pipeline.chunker import Chunk
from pipeline.embedder import BATCH_SIZE, EMBEDDING_DIMENSIONS, EmbeddedChunk, create_embeddings


def _make_chunks(n: int) -> list[Chunk]:
    return [
        Chunk(text=f"Rule text number {i}.", metadata={"source": "tow.whfb.app", "title": f"Rule {i}"})
        for i in range(n)
    ]


def _mock_openai_client(embedding_dim: int = EMBEDDING_DIMENSIONS):
    """Build a mock OpenAI client whose embeddings.create returns realistic-shaped data."""
    client = MagicMock()

    def fake_create(model, input):
        response = MagicMock()
        response.data = [
            MagicMock(embedding=[0.1] * embedding_dim)
            for _ in input
        ]
        return response

    client.embeddings.create.side_effect = fake_create
    return client


class TestCreateEmbeddings:
    def test_returns_one_embedded_chunk_per_input(self):
        chunks = _make_chunks(5)
        client = _mock_openai_client()
        result = create_embeddings(chunks, client=client)
        assert len(result) == 5

    def test_each_result_is_embedded_chunk(self):
        chunks = _make_chunks(3)
        client = _mock_openai_client()
        result = create_embeddings(chunks, client=client)
        for item in result:
            assert isinstance(item, EmbeddedChunk)

    def test_embedding_has_correct_dimension(self):
        chunks = _make_chunks(2)
        client = _mock_openai_client()
        result = create_embeddings(chunks, client=client)
        for item in result:
            assert len(item.embedding) == EMBEDDING_DIMENSIONS

    def test_text_and_metadata_are_preserved(self):
        chunks = _make_chunks(3)
        client = _mock_openai_client()
        result = create_embeddings(chunks, client=client)
        for original, embedded in zip(chunks, result):
            assert embedded.text == original.text
            assert embedded.metadata == original.metadata

    def test_batching_calls_api_correct_number_of_times(self):
        # 250 chunks with BATCH_SIZE=100 → 3 API calls
        n = BATCH_SIZE * 2 + 50
        chunks = _make_chunks(n)
        client = _mock_openai_client()
        create_embeddings(chunks, client=client)
        expected_calls = (n + BATCH_SIZE - 1) // BATCH_SIZE
        assert client.embeddings.create.call_count == expected_calls

    def test_empty_input_returns_empty_list(self):
        client = _mock_openai_client()
        result = create_embeddings([], client=client)
        assert result == []
        client.embeddings.create.assert_not_called()

    def test_retries_on_transient_error_then_succeeds(self):
        chunks = _make_chunks(1)
        client = MagicMock()
        call_count = 0

        def flaky_create(model, input):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Rate limit")
            response = MagicMock()
            response.data = [MagicMock(embedding=[0.0] * EMBEDDING_DIMENSIONS)]
            return response

        client.embeddings.create.side_effect = flaky_create

        with patch("pipeline.embedder.time.sleep"):  # don't actually sleep in tests
            result = create_embeddings(chunks, client=client)

        assert len(result) == 1
        assert call_count == 2

    def test_raises_after_three_failed_attempts(self):
        chunks = _make_chunks(1)
        client = MagicMock()
        client.embeddings.create.side_effect = Exception("Persistent error")

        with patch("pipeline.embedder.time.sleep"):
            with pytest.raises(Exception, match="Persistent error"):
                create_embeddings(chunks, client=client)

        assert client.embeddings.create.call_count == 3
