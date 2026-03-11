"""
Splits scraped pages and army docs into token-limited chunks for embedding.
Each chunk carries metadata for retrieval (source, url, title, section, army).
"""

import re
from dataclasses import dataclass, field

import tiktoken

CHUNK_SIZE = 500       # target tokens per chunk
CHUNK_OVERLAP = 50     # token overlap between adjacent chunks
ENCODER = tiktoken.get_encoding("cl100k_base")


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)

    def token_count(self) -> int:
        return len(ENCODER.encode(self.text))


def _token_split(text: str, size: int, overlap: int) -> list[str]:
    """Split text into token-limited windows with overlap."""
    tokens = ENCODER.encode(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunks.append(ENCODER.decode(chunk_tokens))
        if end == len(tokens):
            break
        start += size - overlap
    return chunks


def chunk_tow_pages(pages: list[dict]) -> list[Chunk]:
    """
    Convert scraped tow.whfb.app pages into chunks.
    Uses section-aware splitting: each section heading stays with its content.
    """
    chunks = []

    for page in pages:
        base_meta = {
            "source": "tow.whfb.app",
            "url": page["url"],
            "title": page["title"],
        }

        sections = page.get("sections") or []

        if sections:
            for section in sections:
                heading = section.get("heading", page["title"])
                text = section.get("text", "").strip()
                if not text or len(text) < 30:
                    continue

                # Prefix text with heading for context
                full_text = f"{heading}\n{text}" if heading != text else text
                token_count = len(ENCODER.encode(full_text))

                if token_count <= CHUNK_SIZE:
                    chunks.append(Chunk(
                        text=full_text,
                        metadata={**base_meta, "section": heading},
                    ))
                else:
                    # Split large sections
                    for part in _token_split(full_text, CHUNK_SIZE, CHUNK_OVERLAP):
                        if part.strip():
                            chunks.append(Chunk(
                                text=part,
                                metadata={**base_meta, "section": heading},
                            ))
        else:
            # Fallback: use full_text
            text = page.get("full_text", "").strip()
            if not text:
                continue
            for part in _token_split(text, CHUNK_SIZE, CHUNK_OVERLAP):
                if part.strip():
                    chunks.append(Chunk(
                        text=part,
                        metadata={**base_meta, "section": page["title"]},
                    ))

    return chunks


def chunk_army_docs(docs: list[dict]) -> list[Chunk]:
    """
    Convert army/unit/spell docs from old-world-builder into chunks.
    Each doc is typically small (one unit), but we split if needed.
    """
    chunks = []

    for doc in docs:
        text = doc.get("text", "").strip()
        if not text or len(text) < 20:
            continue

        meta = {
            "source": doc.get("source", "old-world-builder"),
            "type": doc.get("type", "unit"),
            "title": doc.get("title", ""),
            "army": doc.get("army", ""),
            "url": "https://old-world-builder.com",
        }

        token_count = len(ENCODER.encode(text))
        if token_count <= CHUNK_SIZE:
            chunks.append(Chunk(text=text, metadata=meta))
        else:
            for part in _token_split(text, CHUNK_SIZE, CHUNK_OVERLAP):
                if part.strip():
                    chunks.append(Chunk(text=part, metadata=meta))

    return chunks


def build_all_chunks(tow_pages: list[dict], army_docs: list[dict]) -> list[Chunk]:
    """Combine and return all chunks from both data sources."""
    tow_chunks = chunk_tow_pages(tow_pages)
    army_chunks = chunk_army_docs(army_docs)
    all_chunks = tow_chunks + army_chunks
    print(f"Chunking: {len(tow_chunks)} rule chunks + {len(army_chunks)} army chunks = {len(all_chunks)} total")
    return all_chunks
