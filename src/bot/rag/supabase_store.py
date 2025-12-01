from typing import List, Dict, Any, Optional
import asyncio

from .supabase_client import get_supabase_client


class SupabaseStore:
    def __init__(self, url: str, key: str):
        self.client = get_supabase_client(url, key)

    async def insert_document(self, title: str, doc_type: str, source_path: str | None, metadata: Dict[str, Any]) -> str:
        payload = {
            "title": title,
            "doc_type": doc_type,
            "source_path": source_path,
            "metadata": metadata or {},
        }
        def _insert():
            res = self.client.table("rag_documents").insert(payload).execute()
            return res.data[0]["id"]
        return await asyncio.to_thread(_insert)

    async def insert_chunks(self, chunks: List[str], embeddings: List[List[float]], document_id: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        records = []
        for chunk, emb in zip(chunks, embeddings):
            records.append(
                {
                    "document_id": document_id,
                    "chunk": chunk,
                    "embedding": emb,
                    "metadata": metadata or {},
                }
            )
        def _insert():
            self.client.table("rag_chunks").insert(records).execute()
            return len(records)
        return await asyncio.to_thread(_insert)

    async def search(self, query_embedding: List[float], match_count: int, match_threshold: float) -> List[Dict[str, Any]]:
        payload = {
            "query_embedding": query_embedding,
            "match_count": match_count,
            "match_threshold": match_threshold,
        }
        def _rpc():
            res = self.client.rpc("rag_search_chunks", payload).execute()
            return res.data or []
        return await asyncio.to_thread(_rpc)

    async def stats(self) -> Dict[str, int]:
        def _count(table: str) -> int:
            res = self.client.table(table).select("id", count="exact").limit(1).execute()
            return res.count or 0
        return {
            "documents": await asyncio.to_thread(_count, "rag_documents"),
            "chunks": await asyncio.to_thread(_count, "rag_chunks"),
        }

    async def reset(self) -> None:
        def _truncate():
            self.client.table("rag_chunks").delete().neq("id", -1).execute()
            self.client.table("rag_documents").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
        await asyncio.to_thread(_truncate)
