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
        """
        Comando destrutivo: deleta todos os documentos e embeddings do RAG.
        Requer confirmação via botões para prevenir execuções acidentais.
        """
        # Cria view de confirmação
        class ConfirmView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=30)
                self.value = None

            @discord.ui.button(label="Confirmar Reset", style=discord.ButtonStyle.danger)
            async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = True
                self.stop()

            @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.secondary)
            async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
                self.value = False
                self.stop()

        view = ConfirmView()
        await interaction.response.send_message(
            "⚠️ **ATENÇÃO:** Isso irá deletar TODOS os documentos e embeddings do RAG.\n\n"
            "Esta operação é **irreversível**. Confirma?",
            view=view,
            ephemeral=True
        )

        # Aguarda resposta do usuário
        await view.wait()

        if view.value is None:
            # Timeout
            await interaction.edit_original_response(
                content="❌ Operação cancelada (timeout de 30s).",
                view=None
            )
        elif view.value:
            # Confirmado
            await interaction.edit_original_response(
                content="🔄 Processando reset...",
                view=None
            )
            await self.pipeline.reset()
            await interaction.edit_original_response(
                content="🧹 Tabelas rag_documents / rag_chunks limpas com sucesso."
            )
        else:
            # Cancelado
            await interaction.edit_original_response(
                content="❌ Operação cancelada.",
                view=None
            )


async def setup(bot: commands.Bot, settings: Settings, pipeline: RagPipeline):
    await bot.add_cog(RagAdmin(bot, settings, pipeline))
