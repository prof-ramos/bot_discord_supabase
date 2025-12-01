import asyncio
import discord
from discord.ext import commands

from .config import load_settings
from .rag.embeddings import EmbeddingsProvider
from .rag.supabase_store import SupabaseStore
from .rag.pipeline import RagPipeline


async def load_extensions(bot: commands.Bot, settings, pipeline):
    from . import cogs, events  # noqa: F401

    await cogs.rag_user.setup(bot, settings, pipeline)
    await cogs.rag_admin.setup(bot, settings, pipeline)
    await events.on_ready.setup(bot)
    await events.on_message.setup(bot)


def build_bot():
    settings = load_settings()
    intents = discord.Intents.default()
    intents.messages = True
    intents.guilds = True

    bot = commands.Bot(command_prefix="!", intents=intents)

    store = SupabaseStore(settings.supabase_url, settings.supabase_service_key)
    embedder = EmbeddingsProvider(api_key=settings.openai_api_key)
    pipeline = RagPipeline(store=store, embedder=embedder)

    return bot, settings, pipeline


async def main():
    bot, settings, pipeline = build_bot()
    await load_extensions(bot, settings, pipeline)
    await bot.start(settings.discord_token)


if __name__ == "__main__":
    asyncio.run(main())
