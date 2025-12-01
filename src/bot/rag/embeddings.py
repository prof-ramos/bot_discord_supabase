import asyncio
from typing import List
from openai import AsyncOpenAI


class EmbeddingsProvider:
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed_text(self, text: str) -> List[float]:
        """Gera embedding para um texto."""
        resp = await self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding

    async def embed_many(self, texts: list[str]) -> list[list[float]]:
        """
        Embeds em lote (limita concorrência para free tier).

        IMPORTANTE: Usa asyncio.gather para preservar a ordem dos embeddings.
        A ordem deve corresponder à ordem dos textos de entrada.
        """
        semaphore = asyncio.Semaphore(5)

        async def _embed_single(t: str):
            async with semaphore:
                return await self.embed_text(t)

        coros = [_embed_single(t) for t in texts]
        # asyncio.gather preserva a ordem, asyncio.as_completed não!
        results = await asyncio.gather(*coros)
        return list(results)
