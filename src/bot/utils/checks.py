import discord
from discord.ext import commands


def is_rag_admin():
    async def predicate(ctx: commands.Context):
        # Permite admins do servidor ou quem tem "manage_guild"
        if isinstance(ctx.author, discord.Member):
            if ctx.author.guild_permissions.manage_guild or ctx.author.guild_permissions.administrator:
                return True
        await ctx.reply("❌ Você não tem permissão para ações de administração RAG.", mention_author=False)
        return False
    return commands.check(predicate)
