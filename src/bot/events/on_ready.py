import discord


async def setup(bot: discord.ext.commands.Bot):  # type: ignore[attr-defined]
    @bot.event
    async def on_ready():
        print(f"✅ Bot {bot.user} online!")
        try:
            synced = await bot.tree.sync()
            print(f"✅ {len(synced)} comandos slash sincronizados!")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")
