from typing import List, Dict, Any, Optional
import asyncio
from ..utils.logger import logger
from .supabase_client import get_supabase_client
from .models import Document, Chunk, SearchResult
from .exceptions import DatabaseError
from ..utils.decorators import async_log_execution_time, async_handle_errors

class SupabaseStore:
    def __init__(self, url: str, key: str):
        self.client = get_supabase_client(url, key)

    @async_log_execution_time
    @async_handle_errors(DatabaseError, "Erro ao inserir documento")
    async def insert_document(self, document: Document) -> str:
        payload = {
            "title": document.title,
            "doc_type": document.doc_type,
            "source_path": document.source_path,
            "metadata": document.metadata.model_dump(),
        }

        def _insert():
            res = self.client.table("rag_documents").insert(payload).execute()
            return res.data[0]["id"]

        result = await asyncio.to_thread(_insert)
        return result

    @async_log_execution_time
    @async_handle_errors(DatabaseError, "Erro ao inserir chunks")
    async def insert_chunks(self, chunks: List[Chunk]) -> int:
        records = []
        for chunk in chunks:
            records.append(
                {
                    "document_id": chunk.document_id,
                    "chunk": chunk.content,
                    "embedding": chunk.embedding,
                    "metadata": chunk.metadata,
                }
            )

        def _insert():
            self.client.table("rag_chunks").insert(records).execute()
            return len(records)

        result = await asyncio.to_thread(_insert)
        return result

    @async_log_execution_time
    @async_handle_errors(DatabaseError, "Erro na busca vetorial")
    async def search(self, query_embedding: List[float], match_count: int, match_threshold: float) -> List[SearchResult]:
        def _rpc():
            # Usa a função RPC com payload nomeado (evita PGRST102 de arrays posicionais)
            res = self.client.rpc("match_documents", {
                "query_embedding": query_embedding,
                "match_threshold": match_threshold,
                "match_count": match_count
            }).execute()

            results = []
            for row in res.data or []:
                # Normaliza para o pipeline esperar "chunk" em vez de "content"
                chunk_content = row.pop('content', '')
                similarity = float(row['similarity']) if 'similarity' in row and row['similarity'] is not None else 0.0

                results.append(SearchResult(
                    id=str(row.get('id', '')),
                    document_id=str(row.get('document_id', '')),
                    chunk=chunk_content,
                    similarity=similarity,
                    metadata=row.get('metadata', {})
                ))
            return results

        result = await asyncio.to_thread(_rpc)
        return result

    @async_log_execution_time
    @async_handle_errors(DatabaseError, "Erro ao coletar estatísticas")
    async def stats(self) -> Dict[str, int]:
        def _count(table: str) -> int:
            res = self.client.table(table).select("id", count="exact").limit(1).execute()
            return res.count or 0

        docs_count = await asyncio.to_thread(_count, "rag_documents")
        chunks_count = await asyncio.to_thread(_count, "rag_chunks")

        return {
            "documents": docs_count,
            "chunks": chunks_count,
        }

    @async_log_execution_time
    @async_handle_errors(DatabaseError, "Erro ao resetar banco de dados RAG")
    async def reset(self) -> None:
        def _truncate():
            self.client.table("rag_chunks").delete().neq("id", -1).execute()
            self.client.table("rag_documents").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()

        await asyncio.to_thread(_truncate)
