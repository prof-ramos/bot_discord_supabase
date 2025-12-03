import hashlib
import time
from typing import Optional
from openai import AsyncOpenAI
from ..utils.logger import logger

class LLMClient:
    """Cliente para geração de respostas usando LLM via OpenRouter API.

    Esta classe gerencia interações com modelos de linguagem via OpenRouter,
    suportando cache de respostas e parâmetros configuráveis de geração.

    Attributes:
        client: Cliente assíncrono OpenAI compatível configurado para OpenRouter
        model: Nome do modelo LLM (ex: 'x-ai/grok-4.1-fast:free')
        temperature: Temperatura de geração (0.0 = determinístico, 2.0 = criativo)
        max_tokens: Limite máximo de tokens na resposta
        system_prompt: Prompt de sistema que define comportamento do LLM
        cache: Cache opcional para armazenar respostas geradas
    """

    def __init__(
        self,
        api_key: str,
        model: str = "x-ai/grok-4.1-fast:free",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        system_prompt: str = "",
        cache: Optional['LLMResponseCache'] = None
    ):
        """Inicializa o cliente LLM.

        Args:
            api_key: API key do OpenRouter
            model: Modelo LLM a usar (default: 'x-ai/grok-4.1-fast:free')
            temperature: Temperatura de geração, 0.0-2.0 (default: 0.7)
            max_tokens: Máximo de tokens na resposta (default: 1000)
            system_prompt: Prompt de sistema customizado (usa padrão se vazio)
            cache: Instância de cache opcional para respostas

        Note:
            OpenRouter permite usar vários modelos (Grok, Claude, GPT, etc.)
            via API compatível com OpenAI.
        """
        # Validações de parâmetros
        if not 0.0 <= temperature <= 2.0:
            raise ValueError(f"Temperature deve estar entre 0.0 e 2.0, recebido: {temperature}")
        if max_tokens <= 0:
            raise ValueError(f"max_tokens deve ser positivo, recebido: {max_tokens}")
        if cache is not None:
            if not (hasattr(cache, 'get') and hasattr(cache, 'set')):
                raise TypeError("Cache deve implementar métodos get() e set()")

        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/prof-ramos/bot_discord_supabase",
                "X-Title": "Discord RAG Bot"
            }
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
        """Gera resposta em linguagem natural baseada em query e contexto RAG.

        Combina a query do usuário com chunks de contexto relevantes e gera
        uma resposta coerente usando o LLM. Busca cache antes de chamar API.

        Args:
            query: Pergunta do usuário
            context: Lista de chunks de texto relevantes do RAG (pode ser vazia)

        Returns:
            Resposta gerada pelo LLM em texto natural

        Raises:
            Exception: Se a API do OpenRouter falhar (auth, rate limit, timeout, etc)

        Example:
            >>> llm = LLMClient(api_key="sk-or-...")
            >>> context = ["Chunk 1 sobre Python", "Chunk 2 sobre FastAPI"]
            >>> answer = await llm.generate_answer("O que é FastAPI?", context)
            >>> print(answer)
            'FastAPI é um framework web moderno...'

        Note:
            - Query é hasheada nos logs para proteger PII
            - Cache usa tupla (query, context) como chave
            - Se context vazio, LLM tenta responder sem contexto RAG
            - Temperature e max_tokens são aplicados na geração
        """
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
        """Gera hash SHA-256 curto da query para logs sem expor PII.

        Args:
            query: Query original do usuário

        Returns:
            Hash SHA-256 truncado (12 caracteres) da query

        Example:
            >>> llm._sanitize_query("Como usar Python?")
            'a3f5b9c2e1d4'
        """
        return hashlib.sha256(query.encode()).hexdigest()[:12]
