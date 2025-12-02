from typing import Dict, Any, List, Optional
import time

from .loaders import load_text_from_file
from .chunkers import chunk_text
from .embeddings import EmbeddingsProvider
from .supabase_store import SupabaseStore
from .llm import LLMClient
from ..utils.logger import logger
from .models import Document, DocumentMetadata, Chunk, RAGResponse, SearchResult
from .exceptions import RAGBaseError
from ..utils.decorators import async_log_execution_time, async_handle_errors

class RagPipeline:
    def __init__(
        self,
        store: SupabaseStore,
        embedder: EmbeddingsProvider,
        llm: LLMClient | None = None,
        chunk_max_words: int = 500
    ):
        self.store = store
        self.embedder = embedder
        self.llm = llm
        self.chunk_max_words = chunk_max_words

    @async_log_execution_time
    @async_handle_errors(RAGBaseError, "Erro ao adicionar documento")
    async def add_document(self, title: str, path: str, metadata: Dict[str, Any] | None = None) -> str:
        logger.info("Iniciando adição de documento", title=title, path=str(path), metadata_keys=list(metadata.keys()) if metadata else [])

        load_start = time.time()
        text = load_text_from_file(path)
        load_duration = time.time() - load_start
        logger.info("Documento carregado", path=str(path), text_length=len(text), load_duration=load_duration)

        chunk_start = time.time()
        chunks_text = chunk_text(text, max_words=self.chunk_max_words)
        chunk_duration = time.time() - chunk_start
        logger.info("Documento chunkado", chunks_count=len(chunks_text), chunk_duration=chunk_duration)

        embed_start = time.time()
        embeddings = await self.embedder.embed_many(chunks_text)
        embed_duration = time.time() - embed_start
        logger.info("Embeddings gerados", embeddings_count=len(embeddings), embed_duration=embed_duration)

        doc_metadata = DocumentMetadata(
            source=str(path),
            extra=metadata or {}
        )

        document = Document(
            title=title,
            doc_type="upload",
            source_path=str(path),
            metadata=doc_metadata
        )

        document_id = await self.store.insert_document(document)
        logger.info("Documento inserido no banco", document_id=document_id)

        chunks_objs = []
        for chunk_content, embedding in zip(chunks_text, embeddings):
            chunks_objs.append(Chunk(
                document_id=document_id,
                content=chunk_content,
                embedding=embedding,
                metadata=metadata or {}
            ))

        await self.store.insert_chunks(chunks_objs)

        return document_id

    @async_log_execution_time
    @async_handle_errors(RAGBaseError, "Erro na busca de RAG")
    async def ask(self, query: str, match_count: int = 5, match_threshold: float = 0.75) -> List[SearchResult]:
        embed_start = time.time()
        query_embedding = await self.embedder.embed_text(query)
        embed_duration = time.time() - embed_start
        logger.info("Embedding da query gerado", embed_duration=embed_duration)

        results = await self.store.search(query_embedding, match_count=match_count, match_threshold=match_threshold)

        return results

    @async_log_execution_time
    @async_handle_errors(RAGBaseError, "Erro no pipeline RAG com LLM")
    async def ask_with_llm(self, query: str, match_count: int = 5, match_threshold: float = 0.75) -> RAGResponse:
        start_time = time.time()

        results = await self.ask(query, match_count, match_threshold)

        if not self.llm:
            logger.warning("LLM não configurado, retornando resposta padrão", results_count=len(results))
            return RAGResponse(
                answer="LLM não configurado.",
                sources=results,
                query=query,
                execution_time=time.time() - start_time
            )

        if not results:
            logger.info("Nenhum resultado encontrado, gerando resposta sem contexto", query_preview=query[:50]+"..." if len(query) > 50 else query)
            answer = await self.llm.generate_answer(query, [])
            return RAGResponse(
                answer=answer,
                sources=[],
                query=query,
                execution_time=time.time() - start_time
            )

        context_texts = [r.chunk for r in results]
        logger.info("Gerando resposta com contexto", context_chunks=len(context_texts), total_context_length=sum(len(ct) for ct in context_texts))

        answer = await self.llm.generate_answer(query, context_texts)

        return RAGResponse(
            answer=answer,
            sources=results,
            query=query,
            execution_time=time.time() - start_time
        )

    @async_log_execution_time
    @async_handle_errors(RAGBaseError, "Erro ao coletar estatísticas")
    async def stats(self) -> dict:
        return await self.store.stats()

    @async_log_execution_time
    @async_handle_errors(RAGBaseError, "Erro ao resetar RAG")
    async def reset(self) -> None:
        await self.store.reset()

        # Clear caches if present
        if hasattr(self.embedder, 'cache') and self.embedder.cache:
            self.embedder.cache.clear()

        if self.llm and hasattr(self.llm, 'cache') and self.llm.cache:
            self.llm.cache.clear()

        logger.info("RAG pipeline reset complete (including caches)")
