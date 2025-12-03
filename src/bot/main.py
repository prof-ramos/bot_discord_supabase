import asyncio
import discord
from discord.ext import commands


from .config import load_settings
from .rag.embeddings import EmbeddingsProvider
from .rag.supabase_store import SupabaseStore
from .rag.pipeline import RagPipeline
from .rag.llm import LLMClient
from .utils.logger import logger


async def load_extensions(bot: commands.Bot, settings, pipeline):
    from . import cogs, events  # noqa: F401

    await cogs.rag_user.setup(bot, settings, pipeline)
    await cogs.rag_admin.setup(bot, settings, pipeline)
    await events.on_ready.setup(bot)
    await events.on_message.setup(bot, pipeline)


def build_bot():
    settings = load_settings()
    logger.info("Carregando configurações do bot")

    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)
    logger.info("Bot Discord inicializado com intents configuradas")

    logger.info("Iniciando componentes do pipeline RAG")
    store = SupabaseStore(settings.supabase_url, settings.supabase_service_key)

    # Initialize embedder with config
    embedder = EmbeddingsProvider(
        api_key=settings.openai_api_key,
        model=settings.openai.embedding_model,
        max_concurrent=settings.openai.max_concurrent_requests,
        cache=None  # Cache will be initialized in Phase 3
    )

    # Initialize LLM with config
    llm = LLMClient(
        api_key=settings.openrouter_api_key,
        model=settings.llm.primary_model,
        temperature=settings.llm.temperature,
        max_tokens=settings.llm.max_tokens,
        system_prompt=settings.llm.system_prompt,
        cache=None  # Cache will be initialized in Phase 3
    )

    # Initialize pipeline with config
    pipeline = RagPipeline(
        store=store,
        embedder=embedder,
        llm=llm,
        chunk_max_words=settings.rag.chunk_max_words
    )
    logger.info("Pipeline RAG inicializado com sucesso")

    return bot, settings, pipeline


async def main():
    logger.info("Iniciando bot Discord RAG")
    bot, settings, pipeline = build_bot()

    logger.info("Carregando extensões do bot")
    await load_extensions(bot, settings, pipeline)
    logger.info("Extensões carregadas, iniciando bot")

    try:
        await bot.start(settings.discord_token)
    except KeyboardInterrupt:
        logger.info("Recebido sinal de interrupção, encerrando bot")
        await bot.close()
        raise
    except Exception as e:
        logger.log_error_with_traceback("Erro fatal ao executar bot", e)
        raise


if __name__ == "__main__":
    asyncio.run(main())
