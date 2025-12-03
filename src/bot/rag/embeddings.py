import asyncio
import time
from typing import List, Optional
from openai import AsyncOpenAI
from ..utils.logger import logger


class EmbeddingsProvider:
    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        max_concurrent: int = 5,
        cache: Optional['EmbeddingCache'] = None
    ):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.cache = cache

    async def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um texto (com suporte a cache)."""
        # Check cache first
        if self.cache:
            cached = self.cache.get(text)
            if cached:
                logger.info("Embedding cache hit")
                return cached

        start_time = time.time()
        logger.info("Iniciando geração de embedding (cache miss)", text_length=len(text), model=self.model)

        try:
            resp = await self.client.embeddings.create(model=self.model, input=text)
            embedding = resp.data[0].embedding
            duration = time.time() - start_time
            logger.info("Embedding gerado com sucesso", duration=duration)

            # Store in cache
            if self.cache:
                self.cache.set(text, embedding)

            return embedding
        except Exception as e:
            duration = time.time() - start_time
            logger.log_error_with_traceback("Erro ao gerar embedding", e, text_preview=text[:50]+"..." if len(text) > 50 else text)
            raise

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds em lote (limita concorrência configurável).

        IMPORTANTE: Usa asyncio.gather para preservar a ordem dos embeddings.
        A ordem deve corresponder à ordem dos textos de entrada.
        """
        start_time = time.time()
        logger.info("Iniciando geração de embeddings em lote", texts_count=len(texts), model=self.model)

        async def _embed_single(t: str):
            async with self.semaphore:
                return await self.embed_text(t)

        try:
            coros = [_embed_single(t) for t in texts]
            # asyncio.gather preserva a ordem, asyncio.as_completed não!
            results = await asyncio.gather(*coros)
            duration = time.time() - start_time
            logger.info("Embeddings em lote gerados com sucesso", embeddings_count=len(results), duration=duration)
            return results
        except Exception as e:
            duration = time.time() - start_time
            logger.log_error_with_traceback("Erro ao gerar embeddings em lote", e, texts_count=len(texts))
            raise
