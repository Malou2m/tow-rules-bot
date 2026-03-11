"""
Uploads embedded chunks to Pinecone.

Design decisions:
- Creates the index automatically if it doesn't exist (serverless on AWS us-east-1).
- Upserts in batches of 100 — Pinecone's recommended batch size for throughput.
- Each vector ID is a stable hash of the text so re-running the pipeline is
  idempotent: identical chunks overwrite themselves rather than duplicating.
- Metadata stored alongside each vector enables filtered queries in the UI
  (e.g. "only search army rules for Empire").
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass

from pinecone import Pinecone, ServerlessSpec

from pipeline.embedder import EMBEDDING_DIMENSIONS, EmbeddedChunk

INDEX_DIMENSION = EMBEDDING_DIMENSIONS   # 1536 for text-embedding-3-small
INDEX_METRIC = "cosine"
UPSERT_BATCH_SIZE = 100


def _chunk_id(text: str) -> str:
    """Stable, deterministic ID derived from chunk text content."""
    return hashlib.sha256(text.encode()).hexdigest()[:32]


def get_or_create_index(pc: Pinecone, index_name: str):
    """Return existing index or create a new serverless one."""
    existing = [idx.name for idx in pc.list_indexes()]
    if index_name not in existing:
        print(f"Creating Pinecone index '{index_name}'...")
        pc.create_index(
            name=index_name,
            dimension=INDEX_DIMENSION,
            metric=INDEX_METRIC,
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        print("  Index created.")
    else:
        print(f"Using existing Pinecone index '{index_name}'.")
    return pc.Index(index_name)


def upsert_chunks(embedded_chunks: list[EmbeddedChunk], index_name: str | None = None) -> int:
    """
    Upsert all embedded chunks to Pinecone.
    Returns the total number of vectors upserted.
    """
    api_key = os.environ["PINECONE_API_KEY"]
    index_name = index_name or os.environ["PINECONE_INDEX_NAME"]

    pc = Pinecone(api_key=api_key)
    index = get_or_create_index(pc, index_name)

    total_upserted = 0
    print(f"Upserting {len(embedded_chunks)} vectors to '{index_name}'...")

    for i in range(0, len(embedded_chunks), UPSERT_BATCH_SIZE):
        batch = embedded_chunks[i : i + UPSERT_BATCH_SIZE]

        vectors = []
        for ec in batch:
            # Truncate metadata strings — Pinecone has a 40KB per-vector metadata limit
            meta = {k: str(v)[:500] for k, v in ec.metadata.items()}
            meta["text"] = ec.text[:1000]   # store snippet for display in UI
            vectors.append({
                "id": _chunk_id(ec.text),
                "values": ec.embedding,
                "metadata": meta,
            })

        index.upsert(vectors=vectors)
        total_upserted += len(vectors)

        if (i // UPSERT_BATCH_SIZE + 1) % 10 == 0:
            print(f"  Upserted {total_upserted}/{len(embedded_chunks)} vectors")

    print(f"Done. Total vectors upserted: {total_upserted}")
    return total_upserted
