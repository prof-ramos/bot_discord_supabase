import os
import asyncio
from pathlib import Path
import discord
from discord import app_commands
from discord.ext import commands

from ..config import Settings
from ..rag.pipeline import RagPipeline
from ..utils.formatters import format_results_for_discord


class RagUser(commands.Cog):
    def __init__(self, bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
        self.bot = bot
        self.settings = settings
        self.pipeline = pipeline
        os.makedirs(self.settings.uploads_dir, exist_ok=True)

    @app_commands.command(name="add_doc", description="Adicionar documento ao RAG (upload de arquivo)")
    async def add_doc(self, interaction: discord.Interaction, title: str, file: discord.Attachment):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            dest = Path(self.settings.uploads_dir) / file.filename
            with open(dest, "wb") as f:
                f.write(await file.read())

            doc_id = await self.pipeline.add_document(title=title, path=dest, metadata={"uploaded_by": str(interaction.user.id)})
            await interaction.followup.send(f"✅ Documento adicionado! id={doc_id}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro ao adicionar documento: {e}", ephemeral=True)

    @app_commands.command(name="ask", description="Perguntar ao RAG")
    async def ask(self, interaction: discord.Interaction, query: str, results: int = 4, threshold: float = 0.72):
        await interaction.response.defer(thinking=True)
        results = max(1, min(10, results))
        threshold = max(0.0, min(1.0, threshold))
        try:
            hits = await self.pipeline.ask(query, match_count=results, match_threshold=threshold)
            formatted = format_results_for_discord(hits, query)
            await interaction.followup.send(formatted)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro na busca: {e}")


async def setup(bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
    await bot.add_cog(RagUser(bot, settings, pipeline))
