from typing import Dict, Any
import asyncio

from .loaders import load_text_from_file
from .chunkers import chunk_text
from .embeddings import EmbeddingsProvider
from .supabase_store import SupabaseStore


class RagPipeline:
    def __init__(self, store: SupabaseStore, embedder: EmbeddingsProvider):
        self.store = store
        self.embedder = embedder

    async def add_document(self, title: str, path: str, metadata: Dict[str, Any] | None = None) -> str:
        text = load_text_from_file(path)
        chunks = chunk_text(text)
        embeddings = await self.embedder.embed_many(chunks)
        document_id = await self.store.insert_document(title=title, doc_type="upload", source_path=str(path), metadata=metadata or {})
        await self.store.insert_chunks(chunks, embeddings, document_id=document_id, metadata=metadata or {})
        return document_id

    async def ask(self, query: str, match_count: int = 5, match_threshold: float = 0.75) -> list[dict]:
        query_embedding = await self.embedder.embed_text(query)
        results = await self.store.search(query_embedding, match_count=match_count, match_threshold=match_threshold)
        return results

    async def stats(self) -> dict:
        return await self.store.stats()

    async def reset(self) -> None:
        await self.store.reset()
