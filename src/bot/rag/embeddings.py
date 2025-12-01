import asyncio
import time
from typing import List
from openai import AsyncOpenAI
from ..utils.logger import logger


class EmbeddingsProvider:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um texto."""
        start_time = time.time()
        logger.info("Iniciando geração de embedding", text_length=len(text), model=self.model)

        try:
            resp = await self.client.embeddings.create(model=self.model, input=text)
            duration = time.time() - start_time
            logger.info("Embedding gerado com sucesso", duration=duration)
            return resp.data[0].embedding
        except Exception as e:
            duration = time.time() - start_time
            logger.log_error_with_traceback("Erro ao gerar embedding", e, text_preview=text[:50]+"..." if len(text) > 50 else text)
            raise

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds em lote (limita concorrência para free tier).

        IMPORTANTE: Usa asyncio.gather para preservar a ordem dos embeddings.
        A ordem deve corresponder à ordem dos textos de entrada.
        """
        start_time = time.time()
        logger.info("Iniciando geração de embeddings em lote", texts_count=len(texts), model=self.model)

        semaphore = asyncio.Semaphore(5)

        async def _embed_single(t: str):
            async with semaphore:
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
