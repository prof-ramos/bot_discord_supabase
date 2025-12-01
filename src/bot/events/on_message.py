import discord


async def setup(bot: discord.ext.commands.Bot):  # type: ignore[attr-defined]
    @bot.event
    async def on_message(message: discord.Message):
        # Ignora mensagens do próprio bot
        if message.author == bot.user:
            return
        await bot.process_commands(message)
