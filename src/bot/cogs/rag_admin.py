import discord
from discord import app_commands
from discord.ext import commands

from ..config import Settings
from ..rag.pipeline import RagPipeline
from ..utils.checks import is_rag_admin


class RagAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
        self.bot = bot
        self.settings = settings
        self.pipeline = pipeline

    @app_commands.command(name="rag_stats", description="Estatísticas do RAG")
    @is_rag_admin()
    async def rag_stats(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        stats = await self.pipeline.stats()
        await interaction.followup.send(f"📊 Docs: {stats['documents']}, Chunks: {stats['chunks']}", ephemeral=True)

    @app_commands.command(name="rag_reset", description="Resetar tabelas do RAG (cuidado!)")
    @is_rag_admin()
    async def rag_reset(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.pipeline.reset()
        await interaction.followup.send("🧹 Tabelas rag_documents / rag_chunks limpas.", ephemeral=True)


async def setup(bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
    await bot.add_cog(RagAdmin(bot, settings, pipeline))
