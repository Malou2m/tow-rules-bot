"""
Creates OpenAI embeddings for text chunks in batches.
Uses text-embedding-3-small (1536 dimensions, fast and cost-effective).
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import OpenAI
from tqdm import tqdm

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 100          # OpenAI allows up to 2048 inputs per request
RETRY_DELAY = 5           # seconds between retries on rate limit


@dataclass
class EmbeddedChunk:
    text: str
    embedding: list[float]
    metadata: dict


def create_embeddings(chunks, client: OpenAI | None = None) -> list[EmbeddedChunk]:
    """
    Embed all chunks using OpenAI text-embedding-3-small.
    Batches requests and handles rate limits with simple retry.
    """
    if client is None:
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    embedded = []
    total = len(chunks)
    print(f"Embedding {total} chunks with {EMBEDDING_MODEL}...")

    progress = tqdm(total=total, desc="Embedding chunks", unit="chunk", dynamic_ncols=True)

    for i in range(0, total, BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts = [c.text for c in batch]

        for attempt in range(3):
            try:
                response = client.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=texts,
                )
                for chunk, emb_obj in zip(batch, response.data):
                    embedded.append(EmbeddedChunk(
                        text=chunk.text,
                        embedding=emb_obj.embedding,
                        metadata=chunk.metadata,
                    ))
                break
            except Exception as e:
                if attempt == 2:
                    progress.close()
                    print(f"  Failed batch {i}-{i+len(batch)} after 3 attempts: {e}")
                    raise
                print(f"\n  Rate limit on batch {i}, retrying in {RETRY_DELAY}s: {e}")
                time.sleep(RETRY_DELAY * (attempt + 1))

        progress.update(len(batch))

    progress.close()
    print(f"Done embedding. Total vectors: {len(embedded)}")
    return embedded
