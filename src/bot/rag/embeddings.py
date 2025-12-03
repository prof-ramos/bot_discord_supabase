import asyncio
import time
from typing import List, Optional
from openai import AsyncOpenAI
from ..utils.logger import logger


class EmbeddingsProvider:
    """Provider para geração de embeddings usando OpenAI API com suporte a cache e controle de concorrência.

    Esta classe gerencia a geração de embeddings vetoriais a partir de textos usando a API da OpenAI.
    Implementa:
    - Cache opcional para evitar regenerar embeddings idênticos
    - Controle de concorrência com semáforo para respeitar rate limits
    - Processamento em lote com preservação de ordem

    Attributes:
        client: Cliente assíncrono da OpenAI
        model: Nome do modelo de embedding (ex: 'text-embedding-3-small')
        semaphore: Semáforo para limitar requisições concorrentes
        cache: Cache opcional para armazenar embeddings já gerados
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        max_concurrent: int = 5,
        cache: Optional['EmbeddingCache'] = None
    ):
        """Inicializa o provider de embeddings.

        Args:
            api_key: API key da OpenAI
            model: Modelo de embedding a usar (default: 'text-embedding-3-small')
            max_concurrent: Número máximo de requisições simultâneas (default: 5)
            cache: Instância de cache opcional para armazenar embeddings
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.cache = cache

    async def embed_text(self, text: str) -> List[float]:
        """Gera embedding vetorial para um texto único.

        Busca primeiro no cache (se disponível) antes de fazer requisição à API.
        Registra métricas de performance e cache hits/misses.

        Args:
            text: Texto para gerar embedding (qualquer tamanho, mas API tem limite ~8k tokens)

        Returns:
            Lista de floats representando o vetor de embedding (dimensão 1536 para text-embedding-3-small)

        Raises:
            Exception: Se a API da OpenAI retornar erro (auth, rate limit, etc)

        Example:
            >>> provider = EmbeddingsProvider(api_key="sk-...")
            >>> embedding = await provider.embed_text("Hello world")
            >>> len(embedding)
            1536
        """
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
        """Gera embeddings para múltiplos textos em paralelo com controle de concorrência.

        Processa lista de textos em paralelo respeitando o limite de max_concurrent.
        IMPORTANTE: Preserva a ordem dos embeddings correspondendo à ordem dos textos de entrada.
        Usa asyncio.gather() internamente para garantir ordenação.

        Args:
            texts: Lista de textos para gerar embeddings

        Returns:
            Lista de embeddings na mesma ordem dos textos de entrada.
            Cada embedding é uma lista de floats (dimensão 1536).

        Raises:
            Exception: Se qualquer requisição à API falhar

        Example:
            >>> provider = EmbeddingsProvider(api_key="sk-...", max_concurrent=3)
            >>> embeddings = await provider.embed_many(["text1", "text2", "text3"])
            >>> len(embeddings)
            3
            >>> len(embeddings[0])
            1536

        Note:
            - Usa semáforo para limitar concorrência e respeitar rate limits
            - Cache individual é aplicado por texto via embed_text()
            - Ordem é garantida mesmo com processamento paralelo
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
