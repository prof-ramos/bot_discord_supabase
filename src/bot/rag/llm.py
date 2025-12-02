import hashlib
import time
from typing import Optional
from openai import AsyncOpenAI
from ..utils.logger import logger

class LLMClient:
    def __init__(
        self,
        api_key: str,
        model: str = "x-ai/grok-4.1-fast:free",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: str = "",
        cache: Optional['LLMResponseCache'] = None
    ):
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.system_prompt = system_prompt or (
            "Você é um assistente útil e preciso. "
            "Use as informações de contexto abaixo para responder à pergunta do usuário. "
            "Se a resposta não estiver no contexto, diga que não sabe, mas tente ser útil. "
            "Responda no mesmo idioma da pergunta (provavelmente Português)."
        )
        self.cache = cache

    async def generate_answer(self, query: str, context: list[str]) -> str:
        """Gera uma resposta baseada na query e no contexto fornecido (com suporte a cache)."""
        # Check cache first
        if self.cache:
            cached = self.cache.get(query, context)
            if cached:
                logger.info("LLM cache hit")
                return cached

        start_time = time.time()
        logger.info("Iniciando geração de resposta com LLM (cache miss)", model=self.model, context_count=len(context), query_hash=self._sanitize_query(query))

        context_str = "\n\n---\n\n".join(context)
        user_message = f"Contexto:\n{context_str}\n\nPergunta: {query}"

        try:
            response_start = time.time()
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens
            )
            api_duration = time.time() - response_start

            content = response.choices[0].message.content or "Desculpe, não consegui gerar uma resposta."
            total_duration = time.time() - start_time

            # Store in cache
            if self.cache:
                self.cache.set(query, context, content)

            logger.info("Resposta gerada com sucesso", content_length=len(content), api_duration=api_duration, total_duration=total_duration)

            return content
        except Exception as e:
            total_duration = time.time() - start_time
            logger.log_error_with_traceback(
                "Erro ao gerar resposta com LLM",
                e,
                model=self.model,
                query_hash=self._sanitize_query(query),
                total_duration=total_duration
            )
            raise

    def _sanitize_query(self, query: str) -> str:
        """Retorna um hash curto da query para logs, protegendo PII."""
        return hashlib.sha256(query.encode()).hexdigest()[:12]
