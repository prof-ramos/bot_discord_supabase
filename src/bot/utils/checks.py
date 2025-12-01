import discord
from discord import app_commands
from discord.ext import commands


def is_rag_admin():
    """
    Decorator para comandos de administração RAG.
    Verifica permissões de manage_guild ou administrator.

    IMPORTANTE: Use este decorator para app_commands (slash commands).
    Para comandos de texto tradicionais, use is_rag_admin_legacy().
    """
    async def predicate(interaction: discord.Interaction) -> bool:
        # Verifica se está em um servidor (não funciona em DMs)
        if not interaction.guild:
            await interaction.response.send_message(
                "❌ Comando apenas disponível em servidores",
                ephemeral=True
            )
            return False

        # Verifica permissões do usuário
        if isinstance(interaction.user, discord.Member):
            if (interaction.user.guild_permissions.manage_guild or
                interaction.user.guild_permissions.administrator):
                return True

        # Não tem permissão
        await interaction.response.send_message(
            "❌ Você não tem permissão para ações de administração RAG.",
            ephemeral=True
        )
        return False

    return app_commands.check(predicate)


def is_rag_admin_legacy():
    """
    Decorator para comandos de administração RAG (comandos de texto tradicionais).

    DEPRECATED: Use is_rag_admin() para slash commands modernos.
    """
    async def predicate(ctx: commands.Context):
        # Permite admins do servidor ou quem tem "manage_guild"
        if isinstance(ctx.author, discord.Member):
            if ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.administrator:
                return True
        await ctx.reply("❌ Você não tem permissão para ações de administração RAG.", mention_author=False)
        return False
    return commands.check(predicate)
